"""管理端路由汇总。

所有子路由同时注册 `/admin/...` 与 `/api/admin/...` 两个前缀，
前端（管理后台页面）可任选其一访问。

结构参照「景区管理系统」的管理端实现：
    __init__.py  汇总
    common.py    统一响应 / 数据库连接 / 管理员鉴权 / 分页
    schemas.py   请求体校验
    dashboard.py 概览
    users.py     用户管理
    sessions.py  练习会话
    errors.py    错题本
    expressions.py 表达库
    prompts.py   提示词配置
    tables.py    通用表管理（白名单）
    trends.py    趋势分析
    reports.py   学习报告
"""
from fastapi import APIRouter

from app.routers.admin import (
    dashboard,
    errors,
    expressions,
    prompts,
    reports,
    sessions,
    tables,
    trends,
    users,
)

router = APIRouter()
router.include_router(dashboard.router)
router.include_router(users.router)
router.include_router(sessions.router)
router.include_router(errors.router)
router.include_router(expressions.router)
router.include_router(prompts.router)
router.include_router(tables.router)
router.include_router(trends.router)
router.include_router(reports.router)
