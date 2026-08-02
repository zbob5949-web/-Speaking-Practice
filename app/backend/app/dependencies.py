"""依赖装配：仓库、配置、LLM 工厂与鉴权依赖的统一出口。

路由层与业务层都从这里获取依赖；测试通过替换本模块的
create_llm_provider 属性即可完成 LLM 打桩。
鉴权部分参照灵小游 core/security.py 的 JWT 方案。
"""
from fastapi import Header, HTTPException

from app.config import load_settings
from app.db import init_db
from app.llm import create_llm_provider
from app.repositories import CoachRepository
from app.security import get_phone_from_token, identify_user


def get_repository() -> CoachRepository:
    settings = load_settings()
    init_db(settings.database_path)
    return CoachRepository(settings.database_path)


def get_current_user(authorization: str = Header(None)) -> str:
    """【必须登录】获取当前正式用户的手机号；游客或无 token 返回 401。"""
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录")
    phone = get_phone_from_token(authorization)
    if not phone:
        raise HTTPException(status_code=401, detail="token无效或过期，请重新登录")
    return phone


def get_current_user_optional(authorization: str = Header(None)) -> str | None:
    """【可选登录】已登录返回手机号，游客/未登录返回 None。"""
    return get_phone_from_token(authorization) if authorization else None


def get_user_identity(authorization: str = Header(None)) -> dict:
    """【身份识别】返回 {"type": "user"|"guest"|"anonymous", "id": str|None}。"""
    return identify_user(authorization) if authorization else {"type": "anonymous", "id": None}
