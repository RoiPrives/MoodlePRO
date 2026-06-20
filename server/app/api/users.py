from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas import UsageResponse
from app.services import usage

router = APIRouter(prefix="/users")


@router.get("/{user_id}/usage", response_model=UsageResponse)
async def get_user_usage(
    user_id: str, session: AsyncSession = Depends(get_session)
) -> UsageResponse:
    return UsageResponse(**await usage.get_usage(session, user_id))


@router.post("/{user_id}/review", response_model=UsageResponse)
async def claim_review_bonus(
    user_id: str, session: AsyncSession = Depends(get_session)
) -> UsageResponse:
    """Honor system: grant the review bonus, then return the updated usage."""
    await usage.grant_review_bonus(session, user_id)
    return UsageResponse(**await usage.get_usage(session, user_id))
