"""practice brief 的公共存取。"""
import json

from app.repositories import CoachRepository


def load_brief(repo: CoachRepository, plan_day_id: int) -> dict | None:
    """读取已生成的 practice brief；不存在时返回 None。"""
    brief_row = repo.get_practice_brief(plan_day_id)
    if not brief_row:
        return None
    return json.loads(brief_row["brief_json"])
