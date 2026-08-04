"""用户画像与学习计划业务。"""
from fastapi import HTTPException

from app.agents import GoalAgent, clean_plan
from app import dependencies as deps
from app.models import OnboardingRequest


def onboard(request: OnboardingRequest) -> dict[str, object]:
    repo = deps.get_repository()
    settings = deps.load_settings()
    llm = deps.create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.planner_model,
    )
    profile = repo.save_profile(request)
    plan_days = GoalAgent(llm, repo.get_prompt).generate_plan(
        learning_goal=request.learning_goal,
        total_days=request.total_days,
        daily_minutes=request.daily_minutes,
        current_level=request.current_level,
    )
    plan = clean_plan(repo.save_plan(profile_id=profile["id"], days=plan_days))
    return {"profile": profile, "plan": plan}


def get_all_profiles() -> dict[str, object]:
    return {"profiles": deps.get_repository().get_all_profiles()}


def delete_profile(profile_id: int) -> dict[str, str]:
    repo = deps.get_repository()
    profile = repo.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    repo.delete_profile(profile_id)
    return {"status": "success"}


def get_current_learning_state(profile_id: int | None = None) -> dict[str, object]:
    repo = deps.get_repository()
    profile = repo.get_profile(profile_id) if profile_id else repo.get_latest_profile()
    if profile is None:
        raise HTTPException(status_code=404, detail="No learning plan found")
    plan = clean_plan(repo.get_plan(profile_id=profile["id"]))
    return {"profile": profile, "plan": plan}


def get_growth_summary(profile_id: int | None = None) -> dict[str, object]:
    repo = deps.get_repository()
    profile = repo.get_profile(profile_id) if profile_id else repo.get_latest_profile()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile found")
    summary = repo.get_growth_summary(profile["id"])
    # 「下一步重点」：有自适应计划调整时展示调整；否则根据近期复盘、
    # 长期记忆与最近一次完成练习生成推荐，避免成长板块始终为空。
    if not summary["active_adjustments"]:
        summary["active_adjustments"] = _fallback_next_focus(repo, profile["id"])
    return summary


def _fallback_next_focus(repo, profile_id: int) -> list[dict[str, object]]:
    """基于已有学习数据生成「下一步重点」推荐（无计划调整时的兜底）。"""
    recommendations: list[dict[str, object]] = []
    reviews = repo.get_daily_reviews(profile_id, limit=3)
    latest_review = reviews[0] if reviews else None
    memory = repo.get_memory_items(profile_id)

    if latest_review:
        user_report = latest_review.get("user_report") or {}
        next_focus = user_report.get("next_focus")
        if next_focus:
            recommendations.append({
                "id": -1,
                "title": "复盘建议：继续夯实本次目标",
                "rationale": f"来自 {latest_review.get('review_date')} 的每日复盘",
                "instruction": next_focus,
                "priority": "high",
            })
        structured = latest_review.get("structured_analysis") or {}
        weaknesses = structured.get("weaknesses") or []
        if weaknesses:
            recommendations.append({
                "id": -2,
                "title": "待改进项",
                "rationale": "最近一次复盘中标记的薄弱点",
                "instruction": "；".join(str(item) for item in weaknesses[:3]),
                "priority": "medium",
            })

    # 长期记忆里的高置信度弱点/语法问题，作为下一次练习的侧重
    for index, item in enumerate(memory[:3]):
        category = item.get("category", "")
        if category not in ("weakness", "grammar_issue", "vocabulary_gap"):
            continue
        recommendations.append({
            "id": -(3 + index),
            "title": f"教练记忆：{category}",
            "rationale": f"置信度 {round(float(item.get('confidence', 0)) * 100)}%",
            "instruction": item.get("content", ""),
            "priority": "medium",
        })

    if not recommendations:
        completed = repo.get_sessions(profile_id=profile_id, limit=5)
        recent_summary_focus = None
        for session in completed:
            if session.get("ended_at") and session.get("summary"):
                summary_text = session["summary"]
                if isinstance(summary_text, str):
                    try:
                        import json
                        summary_text = json.loads(summary_text)
                    except (TypeError, json.JSONDecodeError):
                        pass
                if isinstance(summary_text, dict) and summary_text.get("next_focus_zh"):
                    recent_summary_focus = summary_text["next_focus_zh"]
                    break
        if recent_summary_focus:
            recommendations.append({
                "id": -10,
                "title": "承接上次练习的下一步",
                "rationale": "根据最近一次完成的练习生成",
                "instruction": recent_summary_focus,
                "priority": "medium",
            })

    if not recommendations:
        recommendations.append({
            "id": -99,
            "title": "先完成一次场景对话",
            "rationale": "练习数据还不多，先积累一轮真实对话",
            "instruction": "从今日板块选择一个场景开始练习，系统会根据你的表现生成个性化的下一步重点。",
            "priority": "medium",
        })
    return recommendations
