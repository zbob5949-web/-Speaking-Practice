"""管理端用户管理：列表、详情、新建、改状态、重置密码、删除。

接口：
    GET    /admin/users
    GET    /admin/users/{user_id}
    POST   /admin/users
    PUT    /admin/users/{user_id}
    PUT    /admin/users/{user_id}/password
    DELETE /admin/users/{user_id}
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.admin.common import (
    build_filters,
    clamp_page,
    db,
    get_current_admin_user,
    one_or_none,
    ok,
    paged,
    rows_to_list,
)
from app.routers.admin.schemas import PasswordResetForm, UserCreateForm, UserUpdateForm
from app.security import hash_password

router = APIRouter(tags=["管理-用户"])

_USER_FIELDS = "id, phone, role, is_active, is_super_admin, last_login_ip, last_login, created_at"


def _user_row(row) -> dict:
    data = dict(row)
    data["is_active"] = bool(data.get("is_active"))
    data["is_super_admin"] = bool(data.get("is_super_admin"))
    return data


@router.get("/api/admin/users")
@router.get("/admin/users")
def admin_list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """分页查询用户，支持手机号模糊搜索、角色与启用状态过滤。"""
    page, page_size, offset = clamp_page(page, page_size)
    conditions: list[str] = []
    params: list[object] = []

    build_filters(conditions, params, keyword, ["phone"])
    if role:
        conditions.append("role = ?")
        params.append(role)
    if is_active is not None:
        conditions.append("is_active = ?")
        params.append(1 if is_active else 0)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM users {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT {_USER_FIELDS} FROM users {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()

    return ok(paged([_user_row(row) for row in rows], total, page, page_size))


@router.get("/api/admin/users/{user_id}")
@router.get("/admin/users/{user_id}")
def admin_get_user(user_id: int, _: dict = Depends(get_current_admin_user)) -> dict:
    """用户详情。

    说明：SpeakMate 的 user_profile / daily_sessions 未与 users 建外键关联，
    因此这里只返回账号本身的信息，学习数据在「练习会话」模块按 session 维度查看。
    """
    with db() as conn:
        row = conn.execute(f"SELECT {_USER_FIELDS} FROM users WHERE id = ?", (user_id,)).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return ok(_user_row(row))


@router.post("/api/admin/users")
@router.post("/admin/users")
def admin_create_user(form: UserCreateForm, _: dict = Depends(get_current_admin_user)) -> dict:
    """新建账号（可直接创建管理员）。"""
    with db() as conn:
        exists = conn.execute("SELECT id FROM users WHERE phone = ?", (form.phone,)).fetchone()
        if exists is not None:
            raise HTTPException(status_code=400, detail="该手机号已存在")
        cursor = conn.execute(
            "INSERT INTO users (phone, password, role, is_active, is_super_admin) VALUES (?, ?, ?, 1, ?)",
            (form.phone, hash_password(form.password), form.role, 1 if form.role == "admin" else 0),
        )
        user_id = cursor.lastrowid
        row = conn.execute(f"SELECT {_USER_FIELDS} FROM users WHERE id = ?", (user_id,)).fetchone()

    return ok(_user_row(row), msg="创建成功")


@router.put("/api/admin/users/{user_id}")
@router.put("/admin/users/{user_id}")
def admin_update_user(
    user_id: int,
    form: UserUpdateForm,
    admin: dict = Depends(get_current_admin_user),
) -> dict:
    """修改用户的启用状态或角色。"""
    if form.is_active is None and form.role is None and form.is_super_admin is None:
        raise HTTPException(status_code=400, detail="没有需要修改的字段")
    if user_id == admin["id"] and form.is_active is False:
        raise HTTPException(status_code=400, detail="不能停用当前登录的管理员账号")

    updates: list[str] = []
    params: list[object] = []
    if form.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if form.is_active else 0)
    if form.role is not None:
        updates.append("role = ?")
        params.append(form.role)
    if form.is_super_admin is not None:
        updates.append("is_super_admin = ?")
        params.append(1 if form.is_super_admin else 0)

    with db() as conn:
        exists = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", [*params, user_id])
        row = conn.execute(f"SELECT {_USER_FIELDS} FROM users WHERE id = ?", (user_id,)).fetchone()

    return ok(_user_row(row), msg="更新成功")


@router.put("/api/admin/users/{user_id}/password")
@router.put("/admin/users/{user_id}/password")
def admin_reset_password(
    user_id: int,
    form: PasswordResetForm,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """重置指定账号的密码。"""
    with db() as conn:
        exists = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        conn.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(form.password), user_id))

    return ok({"id": user_id}, msg="密码已重置")


@router.delete("/api/admin/users/{user_id}")
@router.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin: dict = Depends(get_current_admin_user)) -> dict:
    """删除账号（不允许删除自己）。"""
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")

    with db() as conn:
        row = one_or_none(conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone())
        if row is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    return ok({"id": user_id}, msg="删除成功")
