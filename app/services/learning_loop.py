"""学习循环编排：今日策略与每日复盘。"""
import json
from datetime import date

from fastapi import HTTPException

from app.agents import (
    CoachOrchestratorAgent,
    DailyReviewAgent,
    MemoryAgent,
    PlanAdaptationAgent,
    ScenarioDesignAgent,
    clean_plan,
    clean_plan_day,
)
from app import dependencies as deps
from app.services.practice_brief import load_brief
from app.tools import LearningToolRegistry


def _make_practice_brief_factory(repo, settings, active_adjustments, active_memory, latest_review):
    """构造 practice brief 生成工厂（LearningToolRegistry 回调签名）。"""

    def make_practice_brief(
        source_plan_day: dict[str, object],
        training_decision: dict[str, object] | None = None,
        memory_influence: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        brief_llm = deps.create_llm_provider(
            provider_name=settings.llm_provider,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.chat_model,
        )
        return ScenarioDesignAgent(brief_llm, repo.get_prompt).generate_brief(
            clean_plan_day(source_plan_day),
            active_adjustments,
            active_memory,
            latest_review or {},
            training_decision=training_decision or {},
            memory_influence=memory_influence or [],
        )

    return make_practice_brief


def run_due_reviews() -> dict[str, object]:
    repo = deps.get_repository()
    profile = repo.get_latest_profile()
    if not profile:
        return {"status": "success", "processed_days": 0}

    settings = deps.load_settings()
    llm = deps.create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.planner_model,
    )
    review_dates = repo.get_unreviewed_session_dates(profile["id"], today=date.today().isoformat())
    processed_days = 0
    processed = []

    for review_date in review_dates:
        sessions = repo.get_review_sessions_for_date(profile["id"], review_date)
        review_sessions = [
            session
            for session in sessions
            if any(turn["speaker"] == "user" for turn in session.get("turns", []))
        ]
        if not review_sessions or repo.get_daily_review(profile["id"], review_date):
            continue

        plan = clean_plan(repo.get_plan(profile["id"]))
        plan_context = {
            "learning_goal": profile["learning_goal"],
            "current_level": profile["current_level"],
            "review_date": review_date,
            "plan": plan,
        }
        review_result = DailyReviewAgent(llm, repo.get_prompt).generate_review(profile, review_sessions, plan_context)
        daily_review = repo.save_daily_review(
            profile["id"],
            review_date,
            "completed",
            review_result.get("user_report", {}),
            review_result.get("structured_analysis", {}),
            [session["id"] for session in review_sessions],
            json.dumps(review_result, ensure_ascii=False),
        )

        active_memory = repo.get_active_memory_items(profile["id"])
        memory_result = MemoryAgent(llm, repo.get_prompt).extract_memory(review_result, active_memory)
        for item in memory_result.get("upserts", []):
            repo.upsert_memory_item(
                profile["id"],
                item.get("category", "general"),
                item.get("content", ""),
                item.get("evidence", ""),
                float(item.get("confidence", 0.5)),
                daily_review["id"],
            )

        active_memory = repo.get_active_memory_items(profile["id"])
        upcoming_days = [day for day in plan if day.get("status") == "pending"]
        adjustment_result = PlanAdaptationAgent(llm, repo.get_prompt).propose_adjustments(
            review_result,
            active_memory,
            upcoming_days,
        )
        for item in adjustment_result.get("adjustments", []):
            target_day = next(
                (day for day in upcoming_days if day.get("day_index") == item.get("target_day_index")),
                None,
            )
            if not target_day:
                continue
            repo.save_plan_adjustment(
                target_day["id"],
                daily_review["id"],
                item.get("adjustment_type", "focus"),
                item.get("title", ""),
                item.get("rationale", ""),
                item.get("instruction", ""),
                item.get("priority", "medium"),
                item.get("status", "active"),
                int(item.get("expires_after_days", 3)),
            )

        reviewed_plan_day_ids = {session.get("plan_day_id") for session in review_sessions}
        next_day = next(
            (day for day in upcoming_days if day.get("id") not in reviewed_plan_day_ids),
            None,
        )
        if next_day:
            brief = ScenarioDesignAgent(llm, repo.get_prompt).generate_brief(
                clean_plan_day(next_day),
                repo.get_active_plan_adjustments(next_day["id"]),
                active_memory,
                repo.get_latest_completed_daily_review(profile["id"]) or daily_review,
            )
            repo.save_practice_brief(next_day["id"], brief)

        processed_days += 1
        processed.append({"review_date": review_date, "review_id": daily_review["id"]})

    return {"status": "success", "processed_days": processed_days, "processed": processed}


def get_today_strategy(profile_id: int | None = None) -> dict[str, object]:
    run_due_reviews()
    repo = deps.get_repository()
    tools = LearningToolRegistry(repo)
    tool_calls = []

    profile_call = tools.call("get_profile", {"profile_id": profile_id})
    tool_calls.append(profile_call.model_dump())
    profile = profile_call.output if profile_call.status == "success" else None
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile found")

    plan_day_call = tools.call("get_current_plan_day", {"profile_id": profile["id"]})
    tool_calls.append(plan_day_call.model_dump())
    plan_day = plan_day_call.output if plan_day_call.status == "success" else None
    if plan_day is None:
        raise HTTPException(status_code=404, detail="No plan day found")

    memory_call = tools.call("get_active_memory", {"profile_id": profile["id"]})
    review_call = tools.call("get_latest_review", {"profile_id": profile["id"]})
    adjustment_call = tools.call("get_active_adjustments", {"plan_day_id": plan_day["id"]})
    tool_calls.extend([memory_call.model_dump(), review_call.model_dump(), adjustment_call.model_dump()])
    active_memory = memory_call.output if memory_call.status == "success" else []
    latest_review = review_call.output if review_call.status == "success" else {}
    active_adjustments = adjustment_call.output if adjustment_call.status == "success" else []
    settings = deps.load_settings()

    make_practice_brief = _make_practice_brief_factory(
        repo, settings, active_adjustments, active_memory, latest_review
    )

    brief_row = repo.get_practice_brief(plan_day["id"])
    if brief_row:
        brief = json.loads(brief_row["brief_json"])
    else:
        brief = make_practice_brief(plan_day, training_decision={}, memory_influence=[])
        repo.save_practice_brief(plan_day["id"], brief)
        tool_calls.append(
            {
                "tool_name": "get_or_create_practice_brief",
                "input": {"plan_day_id": plan_day["id"]},
                "output": brief,
                "status": "success",
                "error_message": None,
            }
        )

    orchestrator_llm = deps.create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.planner_model,
    )
    session = repo.get_or_create_session(plan_day_id=plan_day["id"], day_index=plan_day["day_index"], topic=plan_day["topic"])
    turns = repo.get_turns(session["id"])
    orchestration = CoachOrchestratorAgent(orchestrator_llm, repo.get_prompt).plan_today(
        profile=profile,
        plan_day=plan_day,
        latest_review=latest_review or {},
        active_memory=active_memory,
        active_adjustments=active_adjustments,
        practice_brief=brief,
        session_state={"session_id": session["id"], "has_session": True, "turn_count": len(turns)},
    )
    output = orchestration["output"]
    decision = output.get("training_decision", {})
    memory_influence = output.get("memory_influence", [])
    should_refresh = bool(decision.get("should_refresh_brief")) and bool(decision.get("brief_instruction"))
    if should_refresh:
        refresh_tools = LearningToolRegistry(repo, practice_brief_factory=make_practice_brief)
        refresh_call = refresh_tools.call(
            "refresh_practice_brief",
            {
                "plan_day": plan_day,
                "training_decision": decision,
                "memory_influence": memory_influence,
            },
        )
        tool_calls.append(refresh_call.model_dump())
        if refresh_call.status == "success" and isinstance(refresh_call.output, dict):
            brief_json = refresh_call.output.get("brief_json")
            if isinstance(brief_json, str):
                brief = json.loads(brief_json)
            else:
                brief = refresh_call.output
        else:
            output.setdefault("risk_flags", []).append("practice_brief_refresh_failed")
    agent_run = repo.save_agent_run(
        profile_id=profile["id"],
        plan_day_id=plan_day["id"],
        session_id=session["id"],
        agent_name="CoachOrchestratorAgent",
        trigger_source="today_entry",
        input_data={
            "profile": profile,
            "plan_day": plan_day,
            "latest_review": latest_review or {},
            "active_memory": active_memory,
            "active_adjustments": active_adjustments,
            "practice_brief": brief,
        },
        tool_calls=tool_calls,
        output_data=output,
        validation_status=orchestration["validation_status"],
        error_message=orchestration["error_message"],
    )
    return {
        "today_strategy": output["today_strategy"],
        "training_decision": output.get("training_decision", {}),
        "memory_influence": output.get("memory_influence", []),
        "coach_explanation_zh": output["coach_explanation_zh"],
        "recommended_actions": output.get("recommended_actions", []),
        "risk_flags": output.get("risk_flags", []),
        "practice_brief": brief,
        "agent_run_id": agent_run["id"],
    }
