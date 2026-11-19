"""管理端表达库：查看、修正、删除。

接口：
    GET    /admin/expressions
    GET    /admin/expressions/{expression_id}
    PUT    /admin/expressions/{expression_id}
    DELETE /admin/expressions/{expression_id}
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.admin.common import build_filters, clamp_page, db, get_current_admin_user, ok, paged
from app.routers.admin.schemas import ExpressionUpdateForm

router = APIRouter(tags=["管理-表达库"])

_FIELDS = (
    "id, expression, meaning, usage_context, example_sentence, "
    "source_session_id, review_count, last_reviewed_at"
)


@router.get("/api/admin/expressions")
@router.get("/admin/expressions")
def admin_list_expressions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """表达库列表，支持表达/释义/例句关键词搜索。"""
    page, page_size, offset = clamp_page(page, page_size)
    conditions: list[str] = []
    params: list[object] = []
    build_filters(conditions, params, keyword, ["expression", "meaning", "example_sentence"])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM expression_bank {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT {_FIELDS} FROM expression_bank {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()

    return ok(paged([dict(row) for row in rows], total, page, page_size))


@router.get("/api/admin/expressions/{expression_id}")
@router.get("/admin/expressions/{expression_id}")
def admin_get_expression(expression_id: int, _: dict = Depends(get_current_admin_user)) -> dict:
    with db() as conn:
        row = conn.execute(f"SELECT {_FIELDS} FROM expression_bank WHERE id = ?", (expression_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="表达不存在")
    return ok(dict(row))


@router.put("/api/admin/expressions/{expression_id}")
@router.put("/admin/expressions/{expression_id}")
def admin_update_expression(
    expression_id: int,
    form: ExpressionUpdateForm,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    updates: list[str] = []
    params: list[object] = []
    for field in ("expression", "meaning", "usage_context", "example_sentence"):
        value = getattr(form, field)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)

    if not updates:
        raise HTTPException(status_code=400, detail="没有需要修改的字段")

    with db() as conn:
        row = conn.execute("SELECT id FROM expression_bank WHERE id = ?", (expression_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="表达不存在")
        conn.execute(
            f"UPDATE expression_bank SET {', '.join(updates)} WHERE id = ?", [*params, expression_id]
        )
        updated = conn.execute(
            f"SELECT {_FIELDS} FROM expression_bank WHERE id = ?", (expression_id,)
        ).fetchone()

    return ok(dict(updated), msg="更新成功")


@router.delete("/api/admin/expressions/{expression_id}")
@router.delete("/admin/expressions/{expression_id}")
def admin_delete_expression(expression_id: int, _: dict = Depends(get_current_admin_user)) -> dict:
    with db() as conn:
        row = conn.execute("SELECT id FROM expression_bank WHERE id = ?", (expression_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="表达不存在")
        conn.execute("DELETE FROM expression_bank WHERE id = ?", (expression_id,))
    return ok({"id": expression_id}, msg="删除成功")
