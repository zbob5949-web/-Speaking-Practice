"""管理端提示词配置：查看全部提示词、查看单条、修改内容。

对应 SpeakMate 的 prompts 表（Agent 各阶段的系统提示词），
管理员可在后台直接调参，无需改代码。

接口：
    GET /admin/prompts
    GET /admin/prompts/{name}
    PUT /admin/prompts/{name}
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.admin.common import db, get_current_admin_user, ok
from app.routers.admin.schemas import PromptUpdateForm

router = APIRouter(tags=["管理-提示词"])


@router.get("/api/admin/prompts")
@router.get("/admin/prompts")
def admin_list_prompts(
    keyword: str | None = Query(None),
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """提示词列表（默认只返回名称与长度，避免一次吐出全部正文）。"""
    conditions: list[str] = []
    params: list[object] = []
    if keyword and keyword.strip():
        conditions.append("name LIKE ?")
        params.append(f"%{keyword.strip()}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with db() as conn:
        rows = conn.execute(
            f"SELECT name, length(content) AS content_length, updated_at "
            f"FROM prompts {where} ORDER BY name",
            params,
        ).fetchall()

    return ok({"items": [dict(row) for row in rows], "total": len(rows)})


@router.get("/api/admin/prompts/{name}")
@router.get("/admin/prompts/{name}")
def admin_get_prompt(name: str, _: dict = Depends(get_current_admin_user)) -> dict:
    with db() as conn:
        row = conn.execute(
            "SELECT name, content, updated_at FROM prompts WHERE name = ?", (name,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="提示词不存在")
    return ok(dict(row))


@router.put("/api/admin/prompts/{name}")
@router.put("/admin/prompts/{name}")
def admin_update_prompt(
    name: str,
    form: PromptUpdateForm,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """更新提示词正文；不存在时按给定名称创建。"""
    with db() as conn:
        row = conn.execute("SELECT name FROM prompts WHERE name = ?", (name,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO prompts (name, content) VALUES (?, ?)",
                (name, form.content),
            )
            action = "已创建"
        else:
            conn.execute(
                "UPDATE prompts SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
                (form.content, name),
            )
            action = "已更新"
        updated = conn.execute(
            "SELECT name, length(content) AS content_length, updated_at FROM prompts WHERE name = ?",
            (name,),
        ).fetchone()

    return ok(dict(updated), msg=action)
