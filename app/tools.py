from collections.abc import Callable
from typing import Any

from app.contracts import ToolCallRecord, ToolDefinition
from app.repositories import CoachRepository


PracticeBriefFactory = Callable[
    [dict[str, Any], dict[str, Any] | None, list[dict[str, Any]] | None],
    dict[str, Any],
]


class LearningToolRegistry:
    def __init__(self, repo: CoachRepository, practice_brief_factory: PracticeBriefFactory | None = None):
        self.repo = repo
        self.practice_brief_factory = practice_brief_factory
        self.definitions = {
            "get_profile": ToolDefinition(
                name="get_profile",
                description="Read the current or selected learner profile.",
                input_schema={"profile_id": "int | null"},
                output_schema={"profile": "dict | null"},
                side_effect="read_only",
            ),
            "get_current_plan_day": ToolDefinition(
                name="get_current_plan_day",
                description="Read the next pending plan day for a learner.",
                input_schema={"profile_id": "int"},
                output_schema={"plan_day": "dict | null"},
                side_effect="read_only",
            ),
            "get_active_memory": ToolDefinition(
                name="get_active_memory",
                description="Read active long-term memory items for a learner.",
                input_schema={"profile_id": "int"},
                output_schema={"memory": "list"},
                side_effect="read_only",
            ),
            "get_relevant_memory": ToolDefinition(
                name="get_relevant_memory",
                description="Select the most relevant active memory items for today's training decision.",
                input_schema={"profile_id": "int", "limit": "int"},
                output_schema={"memory": "list"},
                side_effect="read_only",
            ),
            "get_latest_review": ToolDefinition(
                name="get_latest_review",
                description="Read the latest completed daily review for a learner.",
                input_schema={"profile_id": "int"},
                output_schema={"review": "dict | null"},
                side_effect="read_only",
            ),
            "get_active_adjustments": ToolDefinition(
                name="get_active_adjustments",
                description="Read active plan adjustments for a plan day.",
                input_schema={"plan_day_id": "int"},
                output_schema={"adjustments": "list"},
                side_effect="read_only",
            ),
            "get_or_create_practice_brief": ToolDefinition(
                name="get_or_create_practice_brief",
                description="Read an existing practice brief or create one through a backend-controlled factory.",
                input_schema={"plan_day": "dict"},
                output_schema={"practice_brief": "dict"},
                side_effect="write",
            ),
            "refresh_practice_brief": ToolDefinition(
                name="refresh_practice_brief",
                description="Create and save a new practice brief using a backend-controlled factory.",
                input_schema={"plan_day": "dict", "training_decision": "dict", "memory_influence": "list"},
                output_schema={"practice_brief": "dict"},
                side_effect="write",
            ),
        }

    def call(self, name: str, input_data: dict[str, object]) -> ToolCallRecord:
        try:
            output = self._call(name, input_data)
            return ToolCallRecord(tool_name=name, input=input_data, output=output, status="success")
        except Exception as exc:
            return ToolCallRecord(
                tool_name=name,
                input=input_data,
                output=None,
                status="failed",
                error_message=str(exc),
            )

    def _call(self, name: str, input_data: dict[str, object]) -> Any:
        if name == "get_profile":
            profile_id = input_data.get("profile_id")
            return self.repo.get_profile(int(profile_id)) if profile_id else self.repo.get_latest_profile()
        if name == "get_current_plan_day":
            profile_id = int(input_data["profile_id"])
            plan = self.repo.get_plan(profile_id)
            return next((day for day in plan if day.get("status") == "pending"), plan[0] if plan else None)
        if name == "get_active_memory":
            return self.repo.get_active_memory_items(int(input_data["profile_id"]))
        if name == "get_relevant_memory":
            profile_id = int(input_data["profile_id"])
            limit = int(input_data.get("limit", 3))
            memory = self.repo.get_active_memory_items(profile_id)
            priority = {"weakness": 0, "learning_pattern": 1, "preference": 2, "strength": 3, "goal": 4}
            sorted_memory = sorted(
                memory,
                key=lambda item: (
                    priority.get(str(item.get("category")), 9),
                    -float(item.get("confidence") or 0),
                    -int(item.get("id") or 0),
                ),
            )
            return sorted_memory[:limit]
        if name == "get_latest_review":
            return self.repo.get_latest_completed_daily_review(int(input_data["profile_id"]))
        if name == "get_active_adjustments":
            return self.repo.get_active_plan_adjustments(int(input_data["plan_day_id"]))
        if name == "get_or_create_practice_brief":
            plan_day = input_data["plan_day"]
            if not isinstance(plan_day, dict):
                raise ValueError("plan_day must be a dict")
            existing = self.repo.get_practice_brief(int(plan_day["id"]))
            if existing:
                return existing
            if self.practice_brief_factory is None:
                raise ValueError("practice_brief_factory is required to create a brief")
            brief = self.practice_brief_factory(plan_day, None, None)
            return self.repo.save_practice_brief(int(plan_day["id"]), brief)
        if name == "refresh_practice_brief":
            plan_day = input_data["plan_day"]
            if not isinstance(plan_day, dict):
                raise ValueError("plan_day must be a dict")
            if self.practice_brief_factory is None:
                raise ValueError("practice_brief_factory is required to refresh a brief")
            training_decision = input_data.get("training_decision")
            memory_influence = input_data.get("memory_influence")
            brief = self.practice_brief_factory(
                plan_day,
                training_decision if isinstance(training_decision, dict) else {},
                memory_influence if isinstance(memory_influence, list) else [],
            )
            saved = self.repo.save_practice_brief(int(plan_day["id"]), brief)
            return saved if isinstance(saved, dict) else brief
        raise ValueError(f"Unknown tool: {name}")
