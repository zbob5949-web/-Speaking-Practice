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
    return repo.get_growth_summary(profile["id"])
