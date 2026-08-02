"""账号体系路由：注册、登录、刷新、游客、状态查询。"""
from fastapi import APIRouter, Depends, HTTPException

from app import dependencies as deps
from app.models import LoginRequest, RefreshTokenRequest, RegisterRequest
from app.security import create_guest_token, create_refresh_token, create_token, refresh_access_token
from app.services import auth_service

router = APIRouter()


@router.post("/api/auth/register")
def register(request: RegisterRequest) -> dict:
    try:
        user = auth_service.register_user(request.phone, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "success",
        "user": {"id": user["id"], "phone": user["phone"]},
        "access_token": create_token(request.phone),
        "refresh_token": create_refresh_token(request.phone),
    }


@router.post("/api/auth/login")
def login(request: LoginRequest) -> dict:
    try:
        user = auth_service.login_user(request.phone, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {
        "status": "success",
        "user": {"id": user["id"], "phone": user["phone"]},
        "access_token": create_token(request.phone),
        "refresh_token": create_refresh_token(request.phone),
    }


@router.post("/api/auth/refresh")
def refresh(request: RefreshTokenRequest) -> dict:
    new_token = refresh_access_token(request.refresh_token)
    if not new_token:
        raise HTTPException(status_code=401, detail="refresh_token无效或已过期")
    return {"status": "success", "access_token": new_token}


@router.post("/api/auth/guest")
def guest() -> dict:
    token, guest_id = create_guest_token()
    return {"status": "success", "token": token, "guest_id": guest_id, "type": "guest"}


@router.get("/api/auth/status")
def status(identity: dict = Depends(deps.get_user_identity)) -> dict:
    return {"status": "success", "identity": identity}
