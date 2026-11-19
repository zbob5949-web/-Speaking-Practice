"""管理端请求体校验模型（Pydantic）。

对应各路由的写入接口；与业务端的 app/models.py 分开，
避免管理表单字段混进学员端契约。
"""
from typing import Optional

from pydantic import BaseModel, Field


class UserUpdateForm(BaseModel):
    """管理员修改用户信息：启用状态与角色。"""

    is_active: Optional[bool] = None
    role: Optional[str] = Field(None, pattern="^(user|admin)$")
    is_super_admin: Optional[bool] = None


class UserCreateForm(BaseModel):
    """管理员直接新建账号。"""

    phone: str = Field(..., min_length=6, max_length=20)
    password: str = Field(..., min_length=6, max_length=64)
    role: str = Field("user", pattern="^(user|admin)$")


class PasswordResetForm(BaseModel):
    """管理员重置用户密码。"""

    password: str = Field(..., min_length=6, max_length=64)


class ErrorUpdateForm(BaseModel):
    """错题本条目修正。"""

    corrected_sentence: Optional[str] = Field(None, min_length=1)
    better_expression: Optional[str] = Field(None, min_length=1)
    explanation: Optional[str] = Field(None, min_length=1)
    error_type: Optional[str] = Field(None, max_length=50)


class ExpressionUpdateForm(BaseModel):
    """表达库条目修正。"""

    expression: Optional[str] = Field(None, min_length=1)
    meaning: Optional[str] = Field(None, min_length=1)
    usage_context: Optional[str] = Field(None, min_length=1)
    example_sentence: Optional[str] = Field(None, min_length=1)


class PromptUpdateForm(BaseModel):
    """提示词配置更新。"""

    content: str = Field(..., min_length=1)


class TableWriteForm(BaseModel):
    """通用表写入：字段名 -> 值，字段合法性由 tables.py 白名单校验。"""

    values: dict[str, object] = Field(default_factory=dict)
