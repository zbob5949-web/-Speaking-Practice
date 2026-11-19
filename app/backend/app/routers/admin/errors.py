"""管理端错题本：查看、修正、删除。

接口：
    GET    /admin/errors
    GET    /admin/errors/{error_id}
    PUT    /admin/errors/{error_id}
    DELETE /admin/errors/{error_id}
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.admin.common import build_filters, clamp_page, db, get_current_admin_user, ok, paged
from app.routers.admin.schemas import ErrorUpdateForm

router = APIRouter(tags=["管理-错题本"])

_FIELDS = (
    "id, original_sentence, corrected_sentence, better_expression, error_type, "
    "explanation, source_session_id, review_count, last_reviewed_at"
)


@router.get("/api/admin/errors")
@router.get("/admin/errors")
def admin_list_errors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    error_type: str | None = None,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """错题列表，支持原句/修正句关键词与错误类型过滤。"""
    page, page_size, offset = clamp_page(page, page_size)
    conditions: list[str] = []
    params: list[object] = []

    build_filters(conditions, params, keyword, ["original_sentence", "corrected_sentence", "better_expression"])
    if error_type:
        conditions.append("error_type = ?")
        params.append(error_type)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM error_bank {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT {_FIELDS} FROM error_bank {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()

    return ok(paged([dict(row) for row in rows], total, page, page_size))


@router.get("/api/admin/errors/{error_id}")
@router.get("/admin/errors/{error_id}")
def admin_get_error(error_id: int, _: dict = Depends(get_current_admin_user)) -> dict:
    with db() as conn:
        row = conn.execute(f"SELECT {_FIELDS} FROM error_bank WHERE id = ?", (error_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="错题不存在")
    return ok(dict(row))


@router.put("/api/admin/errors/{error_id}")
@router.put("/admin/errors/{error_id}")
def admin_update_error(
    error_id: int,
    form: ErrorUpdateForm,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """修正错题内容（用于纠正 AI 误判的条目）。"""
    updates: list[str] = []
    params: list[object] = []
    for field in ("corrected_sentence", "better_expression", "explanation", "error_type"):
        value = getattr(form, field)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)

    if not updates:
        raise HTTPException(status_code=400, detail="没有需要修改的字段")

    with db() as conn:
        row = conn.execute("SELECT id FROM error_bank WHERE id = ?", (error_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="错题不存在")
        conn.execute(f"UPDATE error_bank SET {', '.join(updates)} WHERE id = ?", [*params, error_id])
        updated = conn.execute(f"SELECT {_FIELDS} FROM error_bank WHERE id = ?", (error_id,)).fetchone()

    return ok(dict(updated), msg="更新成功")


@router.delete("/api/admin/errors/{error_id}")
@router.delete("/admin/errors/{error_id}")
def admin_delete_error(error_id: int, _: dict = Depends(get_current_admin_user)) -> dict:
    with db() as conn:
        row = conn.execute("SELECT id FROM error_bank WHERE id = ?", (error_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="错题不存在")
        conn.execute("DELETE FROM error_bank WHERE id = ?", (error_id,))
    return ok({"id": error_id}, msg="删除成功")
