"""SpeakMate Agent 后端入口：应用装配。

路由与业务逻辑分别位于 app/routers 与 app/services，本文件只负责
创建应用、挂载中间件并 include_router。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 兼容导出：enhanced_main_v2 与外部脚本可能引用这些名字
from app.completion import build_completion_status, build_completion_summary  # noqa: F401
from app.config import load_settings  # noqa: F401
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
    voice,
)

app = FastAPI(title="SpeakMate Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
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
