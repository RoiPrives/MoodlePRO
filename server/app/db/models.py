import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class Transcript(Base):
    """Permanent dedup record, keyed by the SHA-256 hash of the extracted audio."""

    __tablename__ = "transcripts"

    audio_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    language: Mapped[str] = mapped_column(String(8), default="he")
    text: Mapped[str] = mapped_column(Text)
    srt: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Job(Base):
    __tablename__ = "jobs"

    # Stored as a plain string (not a Postgres-native UUID column) so the same
    # model works against SQLite in tests and Postgres in production.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    video_url: Mapped[str] = mapped_column(Text)
    moodle_video_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Dedup lookup key into Transcript.audio_hash, NOT a hard FK: a job records its
    # hash as soon as audio extraction finishes, before a matching transcript exists,
    # so a real FK would (and did) violate on insert. Indexed because _to_response /
    # dedup look transcripts up by it.
    audio_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserLecture(Base):
    """One row per distinct lecture a user has started — the per-user quota counter.
    Keyed by Moodle user id + a lecture key (moodle_video_id, else the video URL)."""

    __tablename__ = "user_lectures"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    lecture_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserReward(Base):
    """Tracks whether a user has claimed the review bonus (honor system)."""

    __tablename__ = "user_rewards"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    reviewed: Mapped[bool] = mapped_column(default=False)


class VideoHash(Base):
    """Maps a Moodle video id to its audio hash, so a previously-seen lecture can be
    served from the transcript cache without re-downloading — and for free."""

    __tablename__ = "video_hashes"

    moodle_video_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    audio_hash: Mapped[str] = mapped_column(String(64))
