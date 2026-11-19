"""管理端公共层：统一响应、数据库连接、管理员鉴权、分页与字段工具。

设计参照「景区管理系统」的 app/routers/admin/common.py：
- 统一响应体 {code, msg, data}，与业务端点的裸 dict 区分开
- get_current_admin_user 作为所有管理接口的依赖
- 因 SpeakMate 的登录令牌统一是 role=user，管理员身份从数据库判定
  （users.role='admin' 或 users.is_super_admin=1）
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Iterator

from fastapi import Header, HTTPException

from app.config import load_settings
from app.db import connect
from app.security import decode_token

# 分页默认值
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


def ok(data: Any = None, msg: str = "success") -> dict:
    """统一成功响应。"""
    return {"code": 200, "msg": msg, "data": data}


def fail(msg: str, code: int = 400) -> dict:
    """统一失败响应（配合 HTTPException 使用时可不抛异常）。"""
    return {"code": code, "msg": msg, "data": None}


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    """打开一个 SQLite 连接，退出时自动提交/回滚并关闭。"""
    settings = load_settings()
    connection = connect(settings.database_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def rows_to_list(rows) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def one_or_none(row) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


# ====================== 管理员鉴权 ======================

def _load_admin(phone: str) -> dict[str, Any] | None:
    """按手机号查管理员账号：role='admin' 或 is_super_admin=1，且未被停用。"""
    with db() as conn:
        row = conn.execute(
            "SELECT id, phone, role, is_active, is_super_admin, last_login, created_at "
            "FROM users WHERE phone = ?",
            (phone,),
        ).fetchone()
    if row is None:
        return None
    user = dict(row)
    is_admin = user.get("role") == "admin" or user.get("is_super_admin") == 1
    if not is_admin or not user.get("is_active", 1):
        return None
    return user


def get_current_admin_user(authorization: str = Header(None)) -> dict[str, Any]:
    """【必须管理员】校验 JWT 并确认数据库里该账号具备管理员权限。

    - 无 token / token 失效  -> 401
    - 账号存在但非管理员或被停用 -> 403
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录管理后台")

    payload = decode_token(authorization)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="token 无效或已过期，请重新登录")

    phone = payload.get("sub")
    if not phone:
        raise HTTPException(status_code=401, detail="token 缺少用户标识")

    admin = _load_admin(phone)
    if admin is None:
        raise HTTPException(status_code=403, detail="当前账号没有管理权限")
    return admin


# ====================== 分页与参数工具 ======================

def clamp_page(page: int, page_size: int) -> tuple[int, int, int]:
    """规整分页参数，返回 (page, page_size, offset)。"""
    page = max(1, int(page or 1))
    page_size = min(max(1, int(page_size or DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
    return page, page_size, (page - 1) * page_size


def paged(items: list[dict[str, Any]], total: int, page: int, page_size: int) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
    }


def date_to_str(value: Any) -> Any:
    """把 date/datetime 转成 ISO 字符串，其余原样返回。"""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def like_pattern(keyword: str | None) -> str | None:
    """构造 LIKE 模式，空关键词返回 None。"""
    if not keyword:
        return None
    trimmed = keyword.strip()
    if not trimmed:
        return None
    return f"%{trimmed}%"


def build_filters(conditions: list[str], params: list[Any], keyword: str | None, columns: list[str]) -> None:
    """把关键词模糊查询按多列 OR 拼进 WHERE 条件（原地修改）。"""
    pattern = like_pattern(keyword)
    if pattern is None or not columns:
        return
    clause = " OR ".join(f"{column} LIKE ?" for column in columns)
    conditions.append(f"({clause})")
    params.extend([pattern] * len(columns))
