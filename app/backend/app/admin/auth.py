"""管理权限必须从数据库实时确认，撤权、停用、改密立即生效。"""
import hashlib

from fastapi import Depends, Header, HTTPException

from app.admin.database import database
from app.security import decode_token


def password_stamp(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()


def require_admin(authorization: str | None = Header(default=None)) -> dict:
    payload = decode_token(authorization or "")
    if not payload or payload.get("type") != "access":
        raise HTTPException(401, "请先使用管理员账号登录")
    if payload.get("role") != "admin":
        raise HTTPException(403, "需要管理员权限")
    with database() as connection:
        row = connection.execute("SELECT * FROM users WHERE phone = ?", (payload.get("sub"),)).fetchone()
    if not row or not row["is_active"] or row["role"] != "admin":
        raise HTTPException(403, "管理员已停用或权限已撤销")
    if payload.get("admin_password_stamp") != password_stamp(row["password"]):
        raise HTTPException(401, "密码已变更，请重新登录")
    return {key: row[key] for key in ("id", "phone", "role", "is_super_admin")}


def require_super_admin(actor: dict = Depends(require_admin)) -> dict:
    if not actor["is_super_admin"]:
        raise HTTPException(403, "此操作需要超级管理员权限")
    return actor
