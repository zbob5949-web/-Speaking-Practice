"""账号业务：users 表操作（注册、登录、查询）。"""
from app.config import load_settings
from app.db import connect, init_db
from app.security import hash_password, verify_password


def _connection():
    settings = load_settings()
    init_db(settings.database_path)  # 确保 users 表已建
    return connect(settings.database_path)


def register_user(phone: str, password: str) -> dict:
    with _connection() as connection:
        existing = connection.execute("SELECT id FROM users WHERE phone = ?", (phone,)).fetchone()
        if existing:
            raise ValueError("该手机号已注册")
        cursor = connection.execute(
            "INSERT INTO users (phone, password) VALUES (?, ?)",
            (phone, hash_password(password)),
        )
        connection.commit()
        return {"id": cursor.lastrowid, "phone": phone}


def login_user(phone: str, password: str) -> dict:
    with _connection() as connection:
        row = connection.execute(
            "SELECT id, phone, password, is_active FROM users WHERE phone = ?",
            (phone,),
        ).fetchone()
    if not row or not verify_password(password, row["password"]):
        raise ValueError("手机号或密码错误")
    if not row["is_active"]:
        raise ValueError("账号已被停用")
    return {"id": row["id"], "phone": row["phone"]}


def find_user(phone: str) -> dict | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT id, phone, role, is_active, is_super_admin FROM users WHERE phone = ?",
            (phone,),
        ).fetchone()
    return dict(row) if row else None
