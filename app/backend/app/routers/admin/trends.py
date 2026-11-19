"""管理端趋势分析：按日统计练习量、对话量、纠错量与新用户。

接口：
    GET /admin/trends/daily?days=14
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from app.routers.admin.common import db, get_current_admin_user, ok

router = APIRouter(tags=["管理-趋势"])


def _series(conn, sql: str, offset: str) -> dict[str, int]:
    """把「按日期分组」的查询结果整理成 {日期: 数量} 字典。offset 形如 '-13 day'。"""
    rows = conn.execute(sql, (offset,)).fetchall()
    return {row["day"]: row["cnt"] for row in rows}


def _build_days(days: int) -> list[str]:
    today = date.today()
    return [(today - timedelta(days=offset)).isoformat() for offset in range(days - 1, -1, -1)]


def _pct_change(current: int, previous: int) -> float | None:
    """环比变化百分比；上一周期为 0 时返回 None，避免除零。"""
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


@router.get("/api/admin/trends/daily")
@router.get("/admin/trends/daily")
def daily_trends(
    days: int = Query(14, ge=1, le=90),
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """近 N 天的经营/学习趋势。"""
    with db() as conn:
        sessions = _series(
            conn,
            "SELECT date(started_at) AS day, COUNT(*) AS cnt FROM daily_sessions "
            "WHERE date(started_at) >= date('now', ?) GROUP BY day",
            f"-{days - 1} day",
        )
        turns = _series(
            conn,
            "SELECT date(created_at) AS day, COUNT(*) AS cnt FROM conversation_turns "
            "WHERE date(created_at) >= date('now', ?) GROUP BY day",
            f"-{days - 1} day",
        )
        feedback = _series(
            conn,
            "SELECT date(created_at) AS day, COUNT(*) AS cnt FROM inline_feedback "
            "WHERE date(created_at) >= date('now', ?) GROUP BY day",
            f"-{days - 1} day",
        )
        new_users = _series(
            conn,
            "SELECT date(created_at) AS day, COUNT(*) AS cnt FROM users "
            "WHERE date(created_at) >= date('now', ?) GROUP BY day",
            f"-{days - 1} day",
        )
        score_rows = conn.execute(
            "SELECT date(started_at) AS day, AVG(overall_score) AS avg_score FROM daily_sessions "
            "WHERE overall_score IS NOT NULL AND date(started_at) >= date('now', ?) GROUP BY day",
            (f"-{days - 1} day",),
        ).fetchall()
        avg_scores = {row["day"]: round(float(row["avg_score"]), 1) for row in score_rows if row["avg_score"] is not None}

    timeline = []
    for day in _build_days(days):
        timeline.append({
            "date": day,
            "sessions": sessions.get(day, 0),
            "turns": turns.get(day, 0),
            "feedback": feedback.get(day, 0),
            "new_users": new_users.get(day, 0),
            "avg_score": avg_scores.get(day),
        })

    # 最近 7 天 vs 前 7 天环比
    recent = timeline[-7:]
    previous = timeline[-14:-7] if len(timeline) >= 14 else []
    summary = {
        "sessions_recent": sum(item["sessions"] for item in recent),
        "sessions_previous": sum(item["sessions"] for item in previous),
        "turns_recent": sum(item["turns"] for item in recent),
        "turns_previous": sum(item["turns"] for item in previous),
    }
    summary["sessions_change_pct"] = _pct_change(summary["sessions_recent"], summary["sessions_previous"])
    summary["turns_change_pct"] = _pct_change(summary["turns_recent"], summary["turns_previous"])

    return ok({"days": days, "timeline": timeline, "summary": summary})
