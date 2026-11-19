"""管理端概览：用户、练习、对话、纠错的核心指标。

接口：
    GET /admin/dashboard/overview
    GET /api/admin/dashboard/overview
"""
from fastapi import APIRouter, Depends

from app.routers.admin.common import db, get_current_admin_user, ok

router = APIRouter(tags=["管理-概览"])


def _scalar(conn, sql: str, params: tuple = ()) -> int | float:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return 0
    value = row[0]
    return value if value is not None else 0


@router.get("/api/admin/dashboard/overview")
@router.get("/admin/dashboard/overview")
def dashboard_overview(_: dict = Depends(get_current_admin_user)) -> dict:
    """管理后台首页概览数据。"""
    with db() as conn:
        total_users = _scalar(conn, "SELECT COUNT(*) FROM users")
        admin_users = _scalar(conn, "SELECT COUNT(*) FROM users WHERE role = 'admin' OR is_super_admin = 1")
        active_users = _scalar(conn, "SELECT COUNT(*) FROM users WHERE is_active = 1")
        new_users_today = _scalar(conn, "SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')")
        logged_in_7d = _scalar(
            conn, "SELECT COUNT(*) FROM users WHERE last_login IS NOT NULL AND date(last_login) >= date('now','-7 day')"
        )

        total_sessions = _scalar(conn, "SELECT COUNT(*) FROM daily_sessions")
        finished_sessions = _scalar(conn, "SELECT COUNT(*) FROM daily_sessions WHERE ended_at IS NOT NULL")
        sessions_today = _scalar(conn, "SELECT COUNT(*) FROM daily_sessions WHERE date(started_at) = date('now')")
        avg_score_row = conn.execute(
            "SELECT AVG(overall_score) FROM daily_sessions WHERE overall_score IS NOT NULL"
        ).fetchone()
        avg_score = round(float(avg_score_row[0]), 1) if avg_score_row and avg_score_row[0] is not None else 0

        total_turns = _scalar(conn, "SELECT COUNT(*) FROM conversation_turns")
        turns_today = _scalar(conn, "SELECT COUNT(*) FROM conversation_turns WHERE date(created_at) = date('now')")
        total_feedback = _scalar(conn, "SELECT COUNT(*) FROM inline_feedback")
        error_items = _scalar(conn, "SELECT COUNT(*) FROM error_bank")
        expression_items = _scalar(conn, "SELECT COUNT(*) FROM expression_bank")
        favorites = _scalar(conn, "SELECT COUNT(*) FROM favorites")

        hot_scenarios = conn.execute(
            "SELECT scenario_id, COUNT(*) AS cnt "
            "FROM daily_sessions WHERE scenario_id IS NOT NULL AND scenario_id <> '' "
            "GROUP BY scenario_id ORDER BY cnt DESC LIMIT 5"
        ).fetchall()

        recent_sessions = conn.execute(
            "SELECT s.id, s.scenario_id, s.topic, s.started_at, s.ended_at, s.overall_score, "
            "       (SELECT COUNT(*) FROM conversation_turns t WHERE t.session_id = s.id) AS turn_count "
            "FROM daily_sessions s ORDER BY s.id DESC LIMIT 8"
        ).fetchall()

    return ok({
        "users": {
            "total": total_users,
            "admin": admin_users,
            "active": active_users,
            "new_today": new_users_today,
            "logged_in_7d": logged_in_7d,
        },
        "sessions": {
            "total": total_sessions,
            "finished": finished_sessions,
            "in_progress": total_sessions - finished_sessions,
            "today": sessions_today,
            "avg_score": avg_score,
        },
        "conversations": {
            "turns_total": total_turns,
            "turns_today": turns_today,
            "feedback_total": total_feedback,
        },
        "libraries": {
            "error_bank": error_items,
            "expression_bank": expression_items,
            "favorites": favorites,
        },
        "hot_scenarios": [{"scenario_id": row["scenario_id"], "count": row["cnt"]} for row in hot_scenarios],
        "recent_sessions": [
            {
                "id": row["id"],
                "scenario_id": row["scenario_id"],
                "topic": row["topic"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "overall_score": row["overall_score"],
                "turn_count": row["turn_count"],
            }
            for row in recent_sessions
        ],
    })
