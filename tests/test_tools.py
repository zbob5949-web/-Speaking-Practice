from app.db import init_db
from app.models import OnboardingRequest
from app.repositories import CoachRepository
from app.tools import LearningToolRegistry


def test_learning_tools_read_core_learning_state(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel speaking",
            total_days=3,
            daily_minutes=15,
            current_level="B1",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [
            {
                "day_index": 1,
                "topic": "Hotel check-in",
                "scenario": "Ask about room details.",
                "objective": "Ask one clear room question.",
                "status": "pending",
            }
        ],
    )
    review = repo.save_daily_review(
        profile["id"],
        "2026-07-18",
        "completed",
        {"summary": "You practiced hotel details.", "next_focus": "Add reservation name."},
        {"weaknesses": ["vague reservation details"]},
        [],
        "{}",
    )
    repo.upsert_memory_item(
        profile["id"],
        "weakness",
        "Often gives vague travel details",
        "Review evidence",
        0.8,
        review["id"],
    )
    repo.save_plan_adjustment(
        plan[0]["id"],
        review["id"],
        "focus",
        "Practice reservation details",
        "Recent review showed missing details.",
        "Ask for reservation name and room type.",
        "high",
        "active",
        3,
    )

    tools = LearningToolRegistry(repo)

    profile_result = tools.call("get_profile", {"profile_id": profile["id"]})
    plan_day_result = tools.call("get_current_plan_day", {"profile_id": profile["id"]})
    memory_result = tools.call("get_active_memory", {"profile_id": profile["id"]})
    review_result = tools.call("get_latest_review", {"profile_id": profile["id"]})
    adjustment_result = tools.call("get_active_adjustments", {"plan_day_id": plan[0]["id"]})

    assert profile_result.status == "success"
    assert profile_result.output["learning_goal"] == "Travel speaking"
    assert plan_day_result.status == "success"
    assert plan_day_result.output["topic"] == "Hotel check-in"
    assert memory_result.output[0]["content"] == "Often gives vague travel details"
    assert review_result.output["id"] == review["id"]
    assert adjustment_result.output[0]["title"] == "Practice reservation details"


def test_learning_tools_report_unknown_tool_failure(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    tools = LearningToolRegistry(CoachRepository(db_path))

    result = tools.call("missing_tool", {})

    assert result.status == "failed"
    assert result.error_message


def test_get_relevant_memory_prioritizes_weakness_and_confidence(tmp_path):
    class Repo:
        def get_active_memory_items(self, profile_id):
            return [
                {"id": 1, "category": "preference", "content": "Likes travel topics", "confidence": 0.9},
                {"id": 2, "category": "weakness", "content": "Often misses dates", "confidence": 0.8},
                {"id": 3, "category": "learning_pattern", "content": "Needs detail prompts", "confidence": 0.7},
                {"id": 4, "category": "weakness", "content": "Forgets object details", "confidence": 0.95},
            ]

    registry = LearningToolRegistry(Repo())
    call = registry.call("get_relevant_memory", {"profile_id": 1, "limit": 2})

    assert call.status == "success"
    assert [item["id"] for item in call.output] == [4, 2]


def test_refresh_practice_brief_uses_factory_and_saves_result():
    saved = {}

    class Repo:
        def save_practice_brief(self, plan_day_id, brief):
            saved["plan_day_id"] = plan_day_id
            saved["brief"] = brief
            return {"id": 10, "plan_day_id": plan_day_id, "brief_json": "{}", **brief}

    def factory(plan_day, training_decision=None, memory_influence=None):
        assert training_decision["brief_instruction"] == "生成酒店入住场景。"
        assert memory_influence[0]["memory_id"] == 3
        return {"title": "Refreshed hotel brief"}

    registry = LearningToolRegistry(Repo(), practice_brief_factory=factory)
    call = registry.call(
        "refresh_practice_brief",
        {
            "plan_day": {"id": 5, "topic": "Hotel"},
            "training_decision": {"brief_instruction": "生成酒店入住场景。"},
            "memory_influence": [{"memory_id": 3}],
        },
    )

    assert call.status == "success"
    assert saved["plan_day_id"] == 5
    assert call.output["title"] == "Refreshed hotel brief"
