"""每日复盘。"""
from fastapi import APIRouter

from app.services import learning_loop

router = APIRouter()


@router.post("/api/daily-review/run-due")
def run_due_reviews() -> dict[str, object]:
    return learning_loop.run_due_reviews()
