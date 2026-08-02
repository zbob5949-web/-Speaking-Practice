"""JWT 令牌与密码工具（参照灵小游 core/security.py 的成熟方案改造）。

配置从 app.config.load_settings() 读取（JWT_SECRET 等环境变量）。
依赖：PyJWT、bcrypt。
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import load_settings

JWT_ALGORITHM = "HS256"
_JWT_LEEWAY = 10  # 10 秒时钟偏差容忍


def _jwt_secret() -> str:
    return load_settings().jwt_secret


# ====================== 密码工具 ======================

def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希值是否匹配"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ====================== JWT 令牌工具 ======================

def _create_jwt(payload: dict, expire_hours: int) -> str:
    """内部方法：生成 JWT 令牌（使用 UTC 时间）"""
    now = datetime.now(timezone.utc)
    payload.update({
        "iat": now,
        "exp": now + timedelta(hours=expire_hours),
        "jti": uuid.uuid4().hex[:12],  # 唯一令牌ID
    })
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def create_token(phone: str, expires_in: int | None = None, role: str = "user") -> str:
    """为已登录用户生成 access token"""
    hours = expires_in // 3600 if expires_in else load_settings().jwt_expire_hours
    return _create_jwt({
        "sub": phone,
        "type": "access",
        "role": role,
    }, expire_hours=hours)


def create_refresh_token(phone: str) -> str:
    """生成 refresh token（有效期更长，用于续期）"""
    settings = load_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": phone,
        "type": "refresh",
        "role": "user",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
        "jti": uuid.uuid4().hex[:12],
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def create_guest_token() -> tuple[str, str]:
    """为游客生成来宾令牌，返回 (token, guest_id)"""
    settings = load_settings()
    guest_id = f"guest_{uuid.uuid4().hex[:12]}"
    token = _create_jwt({
        "sub": guest_id,
        "type": "guest",
        "role": "guest",
    }, expire_hours=settings.guest_token_expire_hours)
    return token, guest_id


def refresh_access_token(refresh_token: str) -> str | None:
    """使用 refresh token 换取新的 access token，失败返回 None"""
    try:
        payload = jwt.decode(
            refresh_token, _jwt_secret(), algorithms=[JWT_ALGORITHM],
            leeway=_JWT_LEEWAY,
        )
        if payload.get("type") != "refresh":
            return None
        phone = payload.get("sub")
        if not phone:
            return None
        return create_token(phone)
    except jwt.PyJWTError:
        return None


# ====================== JWT 解码 ======================

def decode_token(authorization: str) -> dict | None:
    """从 Authorization header 解析 JWT，返回 payload；失败/过期返回 None"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    try:
        return jwt.decode(
            token, _jwt_secret(), algorithms=[JWT_ALGORITHM],
            leeway=_JWT_LEEWAY,
        )
    except jwt.PyJWTError:
        return None


def get_phone_from_token(authorization: str) -> str | None:
    """仅返回正式用户（role=user, type=access）的手机号，游客返回 None"""
    payload = decode_token(authorization)
    if not payload:
        return None
    if payload.get("type") != "access" or payload.get("role") != "user":
        return None
    return payload.get("sub")


def get_guest_id_from_token(authorization: str) -> str | None:
    """仅返回游客（role=guest）的 ID，正式用户返回 None"""
    payload = decode_token(authorization)
    if not payload:
        return None
    if payload.get("role") != "guest":
        return None
    return payload.get("sub")


def identify_user(authorization: str) -> dict:
    """识别身份，返回 {"type": "user"|"guest"|"anonymous", "id": str|None}"""
    payload = decode_token(authorization)
    if not payload:
        return {"type": "anonymous", "id": None}
    role = payload.get("role", "anonymous")
    sub = payload.get("sub")
    token_type = payload.get("type", "")
    if role == "user" and token_type == "access":
        return {"type": "user", "id": sub}
    if role == "guest":
        return {"type": "guest", "id": sub}
    return {"type": "anonymous", "id": None}
