"""今日学习策略。"""
from typing import Optional

from fastapi import APIRouter

from app.models import TodayStrategyResponse
from app.services import learning_loop

router = APIRouter()


@router.get("/api/today/strategy", response_model=TodayStrategyResponse)
def get_today_strategy(profile_id: Optional[int] = None) -> dict[str, object]:
    return learning_loop.get_today_strategy(profile_id)
