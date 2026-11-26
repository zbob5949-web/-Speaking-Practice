"""管理端通用表管理：白名单驱动的 CRUD。

设计直接沿用「景区管理系统」的做法：
- TABLES 字典是唯一入口，未登记的表一律 404，杜绝任意表被读写
- 每个列用 col() 声明类型与界面元信息，前端据此动态渲染表单
- 写入前统一走 _clean_value() 做类型清洗，主键与创建时间不可写

接口：
    GET    /admin/tables
    GET    /admin/tables/{table}
    POST   /admin/tables/{table}
    GET    /admin/tables/{table}/{row_id}
    PUT    /admin/tables/{table}/{row_id}
    DELETE /admin/tables/{table}/{row_id}
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.admin.common import clamp_page, db, get_current_admin_user, ok, paged
from app.routers.admin.schemas import TableWriteForm

router = APIRouter(tags=["管理-通用表"])


def col(
    name: str,
    kind: str = "text",
    label: str | None = None,
    *,
    required: bool = False,
    readonly: bool = False,
    searchable: bool = False,
    textarea: bool = False,
    options: list[str] | None = None,
) -> dict[str, Any]:
    """声明一个列的元信息。"""
    return {
        "name": name,
        "kind": kind,
        "label": label or name,
        "required": required,
        "readonly": readonly,
        "searchable": searchable,
        "textarea": textarea,
        "options": options or [],
    }


# ====================== 白名单 ======================
# 说明：users 与 prompts 有独立的管理模块，不在通用表里开放，
# 避免两套写入逻辑互相覆盖。
TABLES: dict[str, dict[str, Any]] = {
    "user_profile": {
        "label": "学员档案",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("learning_goal", "text", "学习目标", required=True, searchable=True),
            col("total_days", "int", "计划天数", required=True),
            col("daily_minutes", "int", "每日分钟", required=True),
            col("current_level", "select", "当前水平", required=True, options=["A1", "A2", "B1", "B2", "C1"]),
            col("created_at", "datetime", "创建时间", readonly=True),
        ],
    },
    "learning_plan": {
        "label": "学习计划",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("profile_id", "int", "档案ID", required=True),
            col("day_index", "int", "第几天", required=True),
            col("topic", "text", "话题", required=True, searchable=True),
            col("scenario", "text", "场景", required=True),
            col("objective", "textarea", "学习目标", textarea=True),
            col("status", "select", "状态", options=["pending", "done", "skipped"]),
            col("skill_focus", "text", "技能重点"),
            col("communicative_task", "textarea", "交际任务", textarea=True),
            col("target_functions_json", "json", "目标功能(JSON)", textarea=True),
            col("success_criteria_json", "json", "达成标准(JSON)", textarea=True),
            col("brief_seed", "textarea", "简报种子", textarea=True),
        ],
    },
    "daily_sessions": {
        "label": "练习会话",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("plan_day_id", "int", "计划日ID"),
            col("scenario_id", "text", "场景ID", searchable=True),
            col("profile_id", "int", "档案ID"),
            col("day_index", "int", "第几天"),
            col("topic", "text", "话题", searchable=True),
            col("started_at", "datetime", "开始时间", readonly=True),
            col("ended_at", "datetime", "结束时间"),
            col("summary", "json", "总结(JSON)", textarea=True),
            col("overall_score", "int", "总分"),
        ],
    },
    "conversation_turns": {
        "label": "对话轮次",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("session_id", "int", "会话ID", required=True),
            col("turn_index", "int", "轮次序号", required=True),
            col("speaker", "select", "说话人", required=True, options=["user", "assistant"]),
            col("text", "textarea", "内容", required=True, searchable=True, textarea=True),
            col("created_at", "datetime", "创建时间", readonly=True),
        ],
    },
    "inline_feedback": {
        "label": "实时纠错",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("session_id", "int", "会话ID", required=True),
            col("turn_id", "int", "轮次ID"),
            col(
                "feedback_type",
                "select",
                "类型",
                required=True,
                options=["correction", "guidance", "language_help"],
            ),
            col("feedback_text", "textarea", "反馈内容", textarea=True),
            col("original_fragment", "text", "原句片段", searchable=True),
            col("better_expression", "text", "更好表达", searchable=True),
            col("reason_zh", "textarea", "中文解释", textarea=True),
            col("example_sentence", "text", "例句"),
            col("severity", "select", "严重程度", options=["major", "minor"]),
            col("created_at", "datetime", "创建时间", readonly=True),
        ],
    },
    "session_feedback": {
        "label": "会话复盘",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("session_id", "int", "会话ID", required=True),
            col("report", "textarea", "复盘报告", required=True, textarea=True),
            col("created_at", "datetime", "创建时间", readonly=True),
        ],
    },
    "error_bank": {
        "label": "错题本",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("original_sentence", "textarea", "原句", required=True, searchable=True, textarea=True),
            col("corrected_sentence", "textarea", "修正句", required=True, textarea=True),
            col("better_expression", "text", "更好表达"),
            col("error_type", "text", "错误类型", searchable=True),
            col("explanation", "textarea", "解释", textarea=True),
            col("source_session_id", "int", "来源会话"),
            col("review_count", "int", "复习次数"),
            col("last_reviewed_at", "datetime", "最近复习"),
        ],
    },
    "expression_bank": {
        "label": "表达库",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("expression", "text", "表达", required=True, searchable=True),
            col("meaning", "text", "含义", required=True, searchable=True),
            col("usage_context", "textarea", "使用场景", textarea=True),
            col("example_sentence", "textarea", "例句", textarea=True),
            col("source_session_id", "int", "来源会话"),
            col("review_count", "int", "复习次数"),
            col("last_reviewed_at", "datetime", "最近复习"),
        ],
    },
    "daily_reviews": {
        "label": "每日复盘",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("profile_id", "int", "档案ID", required=True),
            col("review_date", "text", "复盘日期", required=True, searchable=True),
            col("status", "select", "状态", options=["pending", "done", "failed"]),
            col("user_report_json", "json", "学员报告(JSON)", textarea=True),
            col("structured_analysis_json", "json", "结构化分析(JSON)", textarea=True),
            col("source_session_ids_json", "json", "来源会话(JSON)", textarea=True),
            col("raw_agent_output", "textarea", "Agent 原始输出", textarea=True),
            col("created_at", "datetime", "创建时间", readonly=True),
            col("updated_at", "datetime", "更新时间", readonly=True),
        ],
    },
    "memory_items": {
        "label": "长期记忆",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("profile_id", "int", "档案ID", required=True),
            col("category", "text", "类别", required=True, searchable=True),
            col("content", "textarea", "内容", required=True, searchable=True, textarea=True),
            col("evidence", "textarea", "证据", textarea=True),
            col("confidence", "text", "置信度"),
            col("status", "select", "状态", options=["active", "archived"]),
            col("source_review_id", "int", "来源复盘"),
            col("created_at", "datetime", "创建时间", readonly=True),
            col("updated_at", "datetime", "更新时间", readonly=True),
        ],
    },
    "plan_adjustments": {
        "label": "计划调整",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("target_plan_day_id", "int", "目标计划日", required=True),
            col("source_review_id", "int", "来源复盘", required=True),
            col("adjustment_type", "text", "调整类型", required=True),
            col("title", "text", "标题", required=True, searchable=True),
            col("rationale", "textarea", "原因", textarea=True),
            col("instruction", "textarea", "指令", textarea=True),
            col("priority", "select", "优先级", options=["high", "medium", "low"]),
            col("status", "select", "状态", options=["pending", "applied", "expired"]),
            col("expires_after_days", "int", "有效天数"),
            col("created_at", "datetime", "创建时间", readonly=True),
            col("updated_at", "datetime", "更新时间", readonly=True),
        ],
    },
    "practice_briefs": {
        "label": "开口前提示",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("plan_day_id", "int", "计划日ID", required=True),
            col("brief_json", "json", "简报(JSON)", required=True, textarea=True),
            col("created_at", "datetime", "创建时间", readonly=True),
        ],
    },
    "account_favorites": {
        "label": "账号场景收藏",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("owner_key", "text", "用户手机号 / 游客ID", required=True, searchable=True),
            col("scenario_id", "text", "场景ID", required=True, searchable=True),
            col("profile_id", "int", "档案ID"),
            col("created_at", "datetime", "收藏时间", readonly=True),
        ],
    },
    "favorites": {
        "label": "历史档案收藏",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("profile_id", "int", "档案ID", required=True),
            col("scenario_id", "text", "场景ID", required=True, searchable=True),
            col("created_at", "datetime", "创建时间", readonly=True),
        ],
    },
    "memory_snapshots": {
        "label": "记忆快照",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("snapshot", "textarea", "快照内容", required=True, textarea=True),
            col("created_at", "datetime", "创建时间", readonly=True),
        ],
    },
    "agent_runs": {
        "label": "Agent 运行记录",
        "columns": [
            col("id", "int", "ID", readonly=True),
            col("profile_id", "int", "档案ID"),
            col("plan_day_id", "int", "计划日ID"),
            col("session_id", "int", "会话ID"),
            col("agent_name", "text", "Agent 名称", searchable=True),
            col("trigger_source", "text", "触发来源"),
            col("input_json", "json", "输入(JSON)", textarea=True),
            col("tool_calls_json", "json", "工具调用(JSON)", textarea=True),
            col("output_json", "json", "输出(JSON)", textarea=True),
            col("validation_status", "text", "校验状态"),
            col("error_message", "textarea", "错误信息", textarea=True),
            col("created_at", "datetime", "创建时间", readonly=True),
        ],
    },
}


# ====================== 内部工具 ======================

def _table_meta(table: str) -> dict[str, Any]:
    meta = TABLES.get(table)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"不支持的表: {table}")
    return meta


def _column_map(meta: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {column["name"]: column for column in meta["columns"]}


def _writable_columns(meta: dict[str, Any]) -> list[dict[str, Any]]:
    return [column for column in meta["columns"] if not column["readonly"]]


def _searchable_columns(meta: dict[str, Any]) -> list[str]:
    return [column["name"] for column in meta["columns"] if column["searchable"]]


def _clean_value(column: dict[str, Any], value: Any) -> Any:
    """按列类型清洗写入值，类型不合法时抛 400。"""
    kind = column["kind"]
    name = column["label"]

    if value is None or (isinstance(value, str) and value.strip() == "" and kind != "text"):
        if column["required"]:
            raise HTTPException(status_code=400, detail=f"{name} 不能为空")
        return None

    if kind == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"{name} 必须是整数") from None

    if kind == "json":
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        text = str(value).strip()
        try:
            json.loads(text)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"{name} 必须是合法 JSON") from None
        return text

    if kind == "select":
        text = str(value).strip()
        if column["options"] and text not in column["options"]:
            raise HTTPException(
                status_code=400,
                detail=f"{name} 只能取: {', '.join(column['options'])}",
            )
        return text

    text = str(value)
    if column["required"] and not text.strip():
        raise HTTPException(status_code=400, detail=f"{name} 不能为空")
    return text


def _row_to_dict(meta: dict[str, Any], row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    for column in meta["columns"]:
        if column["kind"] == "json" and isinstance(data.get(column["name"]), str):
            try:
                data[column["name"]] = json.loads(data[column["name"]])
            except ValueError:
                pass
    return data


# ====================== 路由 ======================

@router.get("/api/admin/tables")
@router.get("/admin/tables")
def admin_list_tables(_: dict = Depends(get_current_admin_user)) -> dict:
    """返回所有可管理表的定义，供前端动态渲染列表与表单。"""
    items = [
        {
            "table": name,
            "label": meta["label"],
            "columns": meta["columns"],
        }
        for name, meta in TABLES.items()
    ]
    return ok({"items": items, "total": len(items)})


@router.get("/api/admin/tables/{table}")
@router.get("/admin/tables/{table}")
def admin_table_rows(
    table: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """指定表的分页数据，keyword 在可搜索列上做模糊匹配。"""
    meta = _table_meta(table)
    page, page_size, offset = clamp_page(page, page_size)

    conditions: list[str] = []
    params: list[object] = []
    if keyword and keyword.strip():
        columns = _searchable_columns(meta)
        if columns:
            clause = " OR ".join(f"{name} LIKE ?" for name in columns)
            conditions.append(f"({clause})")
            params.extend([f"%{keyword.strip()}%"] * len(columns))

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM {table} {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM {table} {where} ORDER BY rowid DESC LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()

    items = [_row_to_dict(meta, row) for row in rows]
    return ok(paged(items, total, page, page_size))


@router.post("/api/admin/tables/{table}")
@router.post("/admin/tables/{table}")
def admin_table_create(
    table: str,
    form: TableWriteForm,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """在指定表新增一行。"""
    meta = _table_meta(table)
    writable = {column["name"]: column for column in _writable_columns(meta)}

    payload: dict[str, Any] = {}
    for name, value in form.values.items():
        column = writable.get(name)
        if column is None:
            raise HTTPException(status_code=400, detail=f"{table} 不允许写入字段: {name}")
        cleaned = _clean_value(column, value)
        if cleaned is not None:
            payload[name] = cleaned

    for name, column in writable.items():
        if column["required"] and name not in payload:
            raise HTTPException(status_code=400, detail=f"{column['label']} 不能为空")

    if not payload:
        raise HTTPException(status_code=400, detail="没有可写入的字段")

    names = ", ".join(payload.keys())
    placeholders = ", ".join("?" for _ in payload)
    with db() as conn:
        try:
            cursor = conn.execute(
                f"INSERT INTO {table} ({names}) VALUES ({placeholders})", list(payload.values())
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail=f"写入失败：{exc}") from exc
        row_id = cursor.lastrowid
        row = conn.execute(f"SELECT * FROM {table} WHERE rowid = ?", (row_id,)).fetchone()

    return ok(_row_to_dict(meta, row), msg="创建成功")


@router.get("/api/admin/tables/{table}/{row_id}")
@router.get("/admin/tables/{table}/{row_id}")
def admin_table_row(table: str, row_id: int, _: dict = Depends(get_current_admin_user)) -> dict:
    meta = _table_meta(table)
    with db() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return ok(_row_to_dict(meta, row))


@router.put("/api/admin/tables/{table}/{row_id}")
@router.put("/admin/tables/{table}/{row_id}")
def admin_table_update(
    table: str,
    row_id: int,
    form: TableWriteForm,
    _: dict = Depends(get_current_admin_user),
) -> dict:
    """修改指定表的一行。"""
    meta = _table_meta(table)
    writable = {column["name"]: column for column in _writable_columns(meta)}

    updates: list[str] = []
    params: list[Any] = []
    for name, value in form.values.items():
        column = writable.get(name)
        if column is None:
            raise HTTPException(status_code=400, detail=f"{table} 不允许写入字段: {name}")
        updates.append(f"{name} = ?")
        params.append(_clean_value(column, value))

    if not updates:
        raise HTTPException(status_code=400, detail="没有需要修改的字段")

    with db() as conn:
        exists = conn.execute(f"SELECT id FROM {table} WHERE id = ?", (row_id,)).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="记录不存在")
        try:
            conn.execute(f"UPDATE {table} SET {', '.join(updates)} WHERE id = ?", [*params, row_id])
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail=f"更新失败：{exc}") from exc
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()

    return ok(_row_to_dict(meta, row), msg="更新成功")


@router.delete("/api/admin/tables/{table}/{row_id}")
@router.delete("/admin/tables/{table}/{row_id}")
def admin_table_delete(table: str, row_id: int, _: dict = Depends(get_current_admin_user)) -> dict:
    _table_meta(table)
    with db() as conn:
        exists = conn.execute(f"SELECT id FROM {table} WHERE id = ?", (row_id,)).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="记录不存在")
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))

    return ok({"table": table, "id": row_id}, msg="删除成功")
