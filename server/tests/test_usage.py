from app.core.config import settings
from app.services import audio_extract


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

    assert (await _post_job(client, "user-C", "l2")).status_code == 200  # bonus unlocked


async def test_usage_endpoint_and_ungated_without_user(client, monkeypatch):
    monkeypatch.setattr(audio_extract, "hash_audio", lambda _p: "hash-ungated")

    # no user_id -> not gated at all
    resp = await client.post("/jobs", json={"video_url": "https://example.com/x.mp4"})
    assert resp.status_code == 200

    usage = await client.get("/users/fresh-user/usage")
    assert usage.json() == {"used": 0, "limit": settings.base_lecture_quota, "reviewed": False}
