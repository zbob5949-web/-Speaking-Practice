"""请求上下文:把当前身份 user_id 传给 LLM 层(DeepSeek user_id 隔离)。"""
import contextvars

current_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_user_id", default=None
)
