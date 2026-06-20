from pathlib import Path

import pytest

from app.core.config import settings
from app.db.session import SessionLocal
from app.services import audio_extract, dedup, video_fetch


@pytest.fixture(autouse=True)
def fake_pipeline(monkeypatch):
    """Stub download + extraction so create_job reaches the cache/quota logic."""

    async def fake_download(video_url, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "source.mp4"
        path.write_bytes(b"fake")
        return path

    def fake_extract(video_path, dest_path):
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(b"fake audio")
        return dest_path

    monkeypatch.setattr(video_fetch, "download_video", fake_download)
    monkeypatch.setattr(audio_extract, "extract_audio", fake_extract)


async def _post_job(client, user_id, video_id):
    return await client.post(
        "/jobs",
        json={
            "video_url": f"https://example.com/{video_id}.mp4",
            "moodle_video_id": video_id,
            "user_id": user_id,
        },
    )


async def test_quota_blocks_after_base_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "base_lecture_quota", 3)
    # each job gets a distinct audio hash so nothing is treated as a cache hit
    counter = {"n": 0}

    def fake_hash(_path):
        counter["n"] += 1
        return f"hash-{counter['n']}"

    monkeypatch.setattr(audio_extract, "hash_audio", fake_hash)

    for i in range(3):
        resp = await _post_job(client, "user-A", f"lec-{i}")
        assert resp.status_code == 200

    blocked = await _post_job(client, "user-A", "lec-3")
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "lecture_quota_reached"


async def test_rewatch_does_not_consume_quota(client, monkeypatch):
    monkeypatch.setattr(settings, "base_lecture_quota", 1)
    monkeypatch.setattr(audio_extract, "hash_audio", lambda _p: "hash-rewatch")

    first = await _post_job(client, "user-B", "lec-X")
    assert first.status_code == 200
    # same lecture again — allowed, no new slot used
    again = await _post_job(client, "user-B", "lec-X")
    assert again.status_code == 200
    # a different lecture is now over the limit of 1
    other = await _post_job(client, "user-B", "lec-Y")
    assert other.status_code == 403


async def test_review_grants_bonus(client, monkeypatch):
    monkeypatch.setattr(settings, "base_lecture_quota", 2)
    monkeypatch.setattr(settings, "review_bonus_lectures", 2)
    counter = {"n": 0}
    monkeypatch.setattr(audio_extract, "hash_audio", lambda _p: f"h{(counter.__setitem__('n', counter['n'] + 1) or counter['n'])}")

    assert (await _post_job(client, "user-C", "l0")).status_code == 200
    assert (await _post_job(client, "user-C", "l1")).status_code == 200
    assert (await _post_job(client, "user-C", "l2")).status_code == 403  # base limit hit

    review = await client.post("/users/user-C/review")
    assert review.status_code == 200
    assert review.json() == {"used": 2, "limit": 4, "reviewed": True}

    # Reviewing again must NOT stack — the bonus is granted only once.
    again = await client.post("/users/user-C/review")
    assert again.json()["limit"] == 4

    assert (await _post_job(client, "user-C", "l2")).status_code == 200  # bonus unlocked


async def test_cache_hit_is_free_and_flagged(client, monkeypatch):
    monkeypatch.setattr(settings, "base_lecture_quota", 1)
    monkeypatch.setattr(audio_extract, "hash_audio", lambda _p: "cached-hash")

    # Pre-seed the shared cache as if another student already transcribed this audio.
    async with SessionLocal() as session:
        await dedup.save_transcript(session, "cached-hash", "txt", "srt", "he")
        await session.commit()

    resp = await _post_job(client, "user-D", "popular-lecture")
    assert resp.status_code == 200
    assert resp.json()["from_cache"] is True

    # It did not cost a credit, so the user can still transcribe a real (new) lecture.
    usage = (await client.get("/users/user-D/usage")).json()
    assert usage["used"] == 0


async def test_usage_endpoint_and_ungated_without_user(client, monkeypatch):
    monkeypatch.setattr(audio_extract, "hash_audio", lambda _p: "hash-ungated")

    # no user_id -> not gated at all
    resp = await client.post("/jobs", json={"video_url": "https://example.com/x.mp4"})
    assert resp.status_code == 200

    usage = await client.get("/users/fresh-user/usage")
    assert usage.json() == {"used": 0, "limit": settings.base_lecture_quota, "reviewed": False}
