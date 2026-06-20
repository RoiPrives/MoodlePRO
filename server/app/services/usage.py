from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import UserLecture, UserReward


async def _count_lectures(session: AsyncSession, user_id: str) -> int:
    return await session.scalar(
        select(func.count()).select_from(UserLecture).where(UserLecture.user_id == user_id)
    ) or 0


async def _limit_for(session: AsyncSession, user_id: str) -> int:
    reward = await session.get(UserReward, user_id)
    bonus = settings.review_bonus_lectures if (reward and reward.reviewed) else 0
    return settings.base_lecture_quota + bonus


async def check_and_reserve(session: AsyncSession, user_id: str, lecture_key: str) -> bool:
    """Reserve a quota slot for (user, lecture). Returns True if allowed.

    Re-watching an already-counted lecture is always allowed and doesn't consume a new
    slot. A brand-new lecture consumes a slot only if the user is under their limit.
    """
    existing = await session.get(UserLecture, {"user_id": user_id, "lecture_key": lecture_key})
    if existing is not None:
        return True  # already counted — re-watch is free

    if await _count_lectures(session, user_id) >= await _limit_for(session, user_id):
        return False

    session.add(UserLecture(user_id=user_id, lecture_key=lecture_key))
    await session.commit()
    return True


async def grant_review_bonus(session: AsyncSession, user_id: str) -> None:
    """Mark the user as having reviewed (honor system), unlocking the bonus lectures."""
    reward = await session.get(UserReward, user_id)
    if reward is None:
        session.add(UserReward(user_id=user_id, reviewed=True))
    else:
        reward.reviewed = True
    await session.commit()


async def get_usage(session: AsyncSession, user_id: str) -> dict:
    reward = await session.get(UserReward, user_id)
    return {
        "used": await _count_lectures(session, user_id),
        "limit": await _limit_for(session, user_id),
        "reviewed": bool(reward and reward.reviewed),
    }
