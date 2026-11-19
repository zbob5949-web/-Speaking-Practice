"""管理端练习会话：会话列表、会话详情（含对话轮次与纠错）。

接口：
    GET    /admin/sessions
    GET    /admin/sessions/{session_id}
    DELETE /admin/sessions/{session_id}
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.admin.common import clamp_page, db, get_current_admin_user, ok, paged

router = APIRouter(tags=["管理-会话"])

_SESSION_FIELDS = (
    "id, plan_day_id, scenario_id, profile_id, day_index, topic, "
    "started_at, ended_at, overall_score"
)


def _decode_summary(raw):
    """summary 字段是 JSON 字符串时解析成对象，便于后台直接展示。"""
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def _session_row(row) -> dict:
    data = dict(row)
    data["finished"] = bool(data.get("ended_at"))
    data["summary"] = _decode_summary(data.get("summary")) if "summary" in data else None
    return data


@router.get("/api/admin/sessions")
@router.get("/admin/sessions")
def admin_list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    scenario_id: str | None = None,
    finished: bool | None = None,
    keyword: str | None = None,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """会话列表，支持场景、是否已完成、话题关键词过滤。"""
    page, page_size, offset = clamp_page(page, page_size)
    conditions: list[str] = []
    params: list[object] = []

    if scenario_id:
        conditions.append("scenario_id = ?")
        params.append(scenario_id)
    if finished is True:
        conditions.append("ended_at IS NOT NULL")
    elif finished is False:
        conditions.append("ended_at IS NULL")
    if keyword:
        conditions.append("topic LIKE ?")
        params.append(f"%{keyword.strip()}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM daily_sessions {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT {_SESSION_FIELDS}, "
            f"  (SELECT COUNT(*) FROM conversation_turns t WHERE t.session_id = daily_sessions.id) AS turn_count, "
            f"  (SELECT COUNT(*) FROM inline_feedback f WHERE f.session_id = daily_sessions.id) AS feedback_count "
            f"FROM daily_sessions {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()

    return ok(paged([_session_row(row) for row in rows], total, page, page_size))


@router.get("/api/admin/sessions/{session_id}")
@router.get("/admin/sessions/{session_id}")
def admin_session_detail(session_id: int, _: dict = Depends(get_current_admin_user)) -> dict:
    """会话详情：基本信息 + 全部对话轮次 + 本轮纠错明细。"""
    with db() as conn:
        row = conn.execute(
            f"SELECT {_SESSION_FIELDS}, summary FROM daily_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="会话不存在")

        turns = conn.execute(
            "SELECT id, turn_index, speaker, text, created_at FROM conversation_turns "
            "WHERE session_id = ? ORDER BY turn_index",
            (session_id,),
        ).fetchall()
        feedback = conn.execute(
            "SELECT id, turn_id, feedback_type, feedback_text, original_fragment, "
            "       better_expression, reason_zh, example_sentence, severity, created_at "
            "FROM inline_feedback WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()

    detail = _session_row(row)
    detail["turns"] = [dict(item) for item in turns]
    detail["feedback"] = [dict(item) for item in feedback]
    detail["turn_count"] = len(turns)
    detail["feedback_count"] = len(feedback)
    return ok(detail)


@router.delete("/api/admin/sessions/{session_id}")
@router.delete("/admin/sessions/{session_id}")
def admin_delete_session(session_id: int, _: dict = Depends(get_current_admin_user)) -> dict:
    """删除一次会话及其轮次、纠错记录（用于清理脏数据）。"""
    with db() as conn:
        row = conn.execute("SELECT id FROM daily_sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        conn.execute("DELETE FROM inline_feedback WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM session_feedback WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM conversation_turns WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM daily_sessions WHERE id = ?", (session_id,))

    return ok({"id": session_id}, msg="删除成功")
