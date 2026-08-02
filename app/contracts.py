from typing import Literal

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    side_effect: Literal["read_only", "write"]


class ToolCallRecord(BaseModel):
    tool_name: str
    input: dict[str, object]
    output: dict[str, object] | list[dict[str, object]] | None = None
    status: Literal["success", "failed"]
    error_message: str | None = None


class TodayStrategy(BaseModel):
    focus: str
    reason: str
    success_criteria: list[str] = Field(default_factory=list)


class TrainingDecision(BaseModel):
    decision_type: Literal[
        "continue_plan",
        "review_weakness",
        "insert_micro_drill",
        "adjust_difficulty",
        "refresh_brief",
    ] = "continue_plan"
    reason_zh: str
    selected_memory_ids: list[int] = Field(default_factory=list, max_length=3)
    selected_review_ids: list[int] = Field(default_factory=list)
    brief_instruction: str = ""
    difficulty_adjustment: Literal["easier", "same", "harder"] = "same"
    should_refresh_brief: bool = False


class MemoryInfluence(BaseModel):
    memory_id: int
    category: str
    content: str
    influence_type: Literal[
        "drill_focus",
        "difficulty_control",
        "npc_behavior",
        "feedback_priority",
    ]
    instruction: str
    reason_zh: str


class RecommendedAction(BaseModel):
    action: Literal[
        "run_due_reviews",
        "generate_practice_brief",
        "use_existing_brief",
        "start_practice",
        "review_lesson_material",
    ]
    rationale: str
    priority: Literal["low", "medium", "high"] = "medium"


class OrchestrationResult(BaseModel):
    today_strategy: TodayStrategy
    training_decision: TrainingDecision
    memory_influence: list[MemoryInfluence] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    coach_explanation_zh: str
    risk_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
