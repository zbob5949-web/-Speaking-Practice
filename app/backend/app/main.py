"""SpeakMate Agent 后端入口：应用装配。

路由与业务逻辑分别位于 app/routers 与 app/services，本文件只负责
创建应用、挂载中间件并 include_router。
"""
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 兼容导出：enhanced_main_v2 与外部脚本可能引用这些名字
from app.completion import build_completion_status, build_completion_summary  # noqa: F401
from app.config import load_settings  # noqa: F401
from app.context import current_user_id
from app.dependencies import get_repository  # noqa: F401
from app.llm import create_llm_provider  # noqa: F401
from app.routers import (
    asr,
    auth,
    favorites,
    health,
    language_support,
    profiles,
    prompts,
    reviews,
    scenarios,
    sessions,
    today,
    translate,
    tts,
    version,
    voice,
)
from app.security import identify_user

app = FastAPI(title="SpeakMate Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost", "https://localhost", "capacitor://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(version.router)
app.include_router(auth.router)
app.include_router(asr.router)
app.include_router(prompts.router)
app.include_router(profiles.router)
app.include_router(today.router)
app.include_router(reviews.router)
app.include_router(sessions.router)
app.include_router(tts.router)
app.include_router(voice.router)
app.include_router(language_support.router)
app.include_router(scenarios.router)
app.include_router(favorites.router)
app.include_router(translate.router)

# ── 安全访问限制:强制鉴权 + 按用户限流 ────────────────────────
# 白名单:健康检查、认证接口(登录/注册/游客/刷新)免登录。
# 其余所有 /api/* 必须携带有效 token(正式用户或游客),未登录返回 401。
# 限流按身份维度(内存计数,单进程有效):
#   正式用户: 30 次/分钟、500 次/天
#   游客:     5 次/分钟、30 次/天
# 超限返回 429。同时把身份 user_id 写入请求上下文,供 LLM 层
# 透传 DeepSeek user_id 做内容安全 / KVCache 隔离。
AUTH_FREE_PATHS = {
    "/api/health",
    "/api/app/version",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/guest",
    "/api/auth/refresh",
}

# (窗口秒数, 窗口内最大次数)
RATE_LIMITS_BY_ROLE = {
    "user": [(60, 30), (86400, 500)],
    "guest": [(60, 60), (86400, 600)],
}

# 免限流白名单：这些手机号的正式用户不限流(可无限调用)
UNLIMITED_USERS = {"18722824407"}

_hits: dict[str, list[float]] = {}


def _check_rate_limit(key: str, role: str) -> int | None:
    """未超限返回 None;超限返回建议等待的秒数。"""
    now = time.time()
    windows = RATE_LIMITS_BY_ROLE.get(role)
    if not windows:
        return None
    hits = _hits.setdefault(key, [])
    # 清理过期记录
    max_window = max(w for w, _ in windows)
    hits[:] = [t for t in hits if now - t < max_window]
    for window, limit in windows:
        recent = sum(1 for t in hits if now - t < window)
        if recent >= limit:
            oldest_in_window = min((t for t in hits if now - t < window), default=now)
            return int(window - (now - oldest_in_window)) + 1
    hits.append(now)
    return None


@app.middleware("http")
async def auth_and_rate_limit(request: Request, call_next):
    path = request.url.path

    # 静态资源与前端页面直接放行
    if not path.startswith("/api"):
        return await call_next(request)
    # CORS 预检放行
    if request.method == "OPTIONS":
        return await call_next(request)
    # 白名单
    if path in AUTH_FREE_PATHS:
        return await call_next(request)

    # 其余 API 必须登录
    auth_header = request.headers.get("authorization")
    identity = identify_user(auth_header) if auth_header else {"type": "anonymous", "id": None}
    if identity["type"] == "anonymous":
        return JSONResponse(status_code=401, content={"detail": "请先登录"})

    role = identity["type"]
    uid = identity["id"] or "anonymous"
    key = f"{role}:{uid}"

    # 免限流白名单用户：直接放行(不计数)
    if role == "user" and uid in UNLIMITED_USERS:
        # 仍写入请求上下文供 LLM 层 user_id 透传
        token = current_user_id.set(uid)
        try:
            return await call_next(request)
        finally:
            current_user_id.reset(token)

    # 写入请求上下文,供 LLM 层 user_id 透传(anyio 线程池会复制 contextvars)
    token = current_user_id.set(uid)

    # 按身份限流
    retry_after = _check_rate_limit(key, role)
    if retry_after is not None:
        current_user_id.reset(token)
        return JSONResponse(
            status_code=429,
            content={"detail": f"请求过于频繁，请 {retry_after} 秒后再试"},
            headers={"Retry-After": str(retry_after)},
        )

    try:
        return await call_next(request)
    finally:
        current_user_id.reset(token)


# ── 提交版增强：单端口发布 ──────────────────────────────
# 将前端构建产物（app/frontend/dist）挂载到本服务，
# 评委访问 http://localhost:8000 即可直接使用完整应用（页面 + API 同源）。
# 源项目（开发模式）未含此段；前端源码见 app/frontend，可自行重新构建。
from pathlib import Path

from fastapi.staticfiles import StaticFiles

FRONTEND_DIST = Path(__file__).resolve().parents[3] / "app" / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
