"""固定表白名单及业务关系；不接受客户端提供的 SQL 标识符。"""
TABLES = {
    "users": "用户账号",
    "user_profile": "学习档案",
    "learning_plan": "学习计划",
    "daily_sessions": "练习会话",
    "conversation_turns": "对话记录",
    "inline_feedback": "即时纠错",
    "session_feedback": "会话报告",
    "error_bank": "错题库",
    "expression_bank": "表达库",
    "memory_snapshots": "记忆快照",
    "prompts": "提示词配置",
    "daily_reviews": "每日复盘",
    "memory_items": "长期记忆",
    "plan_adjustments": "计划调整",
    "practice_briefs": "练习简报",
    "favorites": "场景收藏",
    "agent_runs": "Agent 运行记录",
    "admin_audit_logs": "管理操作日志",
}
READ_ONLY = {"agent_runs", "admin_audit_logs"}
SYSTEM_FIELDS = {"created_at", "updated_at", "last_login", "last_login_ip"}
ENUMS = {
    ("users", "role"): ["user", "admin"],
    ("conversation_turns", "speaker"): ["user", "assistant", "system"],
    ("learning_plan", "status"): ["pending", "in_progress", "completed"],
}
# Includes logical references which the original database does not declare as FKs.
RELATIONS = [
    ("learning_plan", "profile_id", "user_profile", "id"),
    ("daily_sessions", "profile_id", "user_profile", "id"),
    ("daily_sessions", "plan_day_id", "learning_plan", "id"),
    ("conversation_turns", "session_id", "daily_sessions", "id"),
    ("inline_feedback", "session_id", "daily_sessions", "id"),
    ("inline_feedback", "turn_id", "conversation_turns", "id"),
    ("session_feedback", "session_id", "daily_sessions", "id"),
    ("error_bank", "source_session_id", "daily_sessions", "id"),
    ("expression_bank", "source_session_id", "daily_sessions", "id"),
    ("daily_reviews", "profile_id", "user_profile", "id"),
    ("memory_items", "profile_id", "user_profile", "id"),
    ("memory_items", "source_review_id", "daily_reviews", "id"),
    ("plan_adjustments", "target_plan_day_id", "learning_plan", "id"),
    ("plan_adjustments", "source_review_id", "daily_reviews", "id"),
    ("practice_briefs", "plan_day_id", "learning_plan", "id"),
    ("favorites", "profile_id", "user_profile", "id"),
    ("agent_runs", "profile_id", "user_profile", "id"),
    ("agent_runs", "plan_day_id", "learning_plan", "id"),
    ("agent_runs", "session_id", "daily_sessions", "id"),
]
