from typing import Literal

from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    learning_goal: str = Field(min_length=1)
    total_days: int = Field(ge=1, le=60)
    daily_minutes: int = Field(ge=5, le=60)
    current_level: str = Field(min_length=1)


class PlanDay(BaseModel):
    day_index: int
    topic: str
    scenario: str
    objective: str
    status: str = "pending"


class StartSessionRequest(BaseModel):
    plan_day_id: int | None = Field(default=None, ge=1)
    scenario_id: str | None = None
    profile_id: int | None = None


class UserTurnRequest(BaseModel):
    session_id: int
    text: str = Field(min_length=1)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)

class SwitchProfileRequest(BaseModel):
    profile_id: int


class LanguageSupportRequest(BaseModel):
    mode: str = Field(pattern="^(explain|define|translate|expression)$")
    text: str = Field(min_length=1, max_length=1200)
    context: str = ""


class CompleteSessionRequest(BaseModel):
    completion_type: Literal["manual", "agent_suggested"] = "manual"


class RegisterRequest(BaseModel):
    phone: str = Field(pattern=r"^[a-zA-Z0-9_]{3,20}$")
    password: str = Field(min_length=6, max_length=64)


class LoginRequest(BaseModel):
    phone: str = Field(pattern=r"^[a-zA-Z0-9_]{3,20}$")
    password: str = Field(min_length=6, max_length=64)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class CompletionSummary(BaseModel):
    status: str = "completed"
    completion_type: str
    summary_zh: str
    strength_zh: str
    next_focus_zh: str
    reusable_sentences: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class SessionCompletionStatus(BaseModel):
    status: Literal["in_progress", "completion_suggested", "completed"]
    can_suggest_completion: bool = False
    suggestion_reason_zh: str = ""
    completed_summary: dict | None = None


class GrowthSummaryResponse(BaseModel):
    latest_review: dict | None
    recent_reviews: list[dict]
    active_memory: list[dict]
    active_adjustments: list[dict]


class TodayStrategyResponse(BaseModel):
    today_strategy: dict
    training_decision: dict
    memory_influence: list[dict]
    coach_explanation_zh: str
    recommended_actions: list[dict]
    risk_flags: list[str]
    practice_brief: dict
    agent_run_id: int
