"""用户画像与学习计划路由。"""
from typing import Optional

from fastapi import APIRouter

from app.models import GrowthSummaryResponse, OnboardingRequest
from app.services import profiles as profiles_service

router = APIRouter()


@router.post("/api/onboarding")
def onboard(request: OnboardingRequest) -> dict[str, object]:
    return profiles_service.onboard(request)


@router.get("/api/profiles")
def get_all_profiles() -> dict[str, object]:
    return profiles_service.get_all_profiles()


@router.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: int) -> dict[str, str]:
    return profiles_service.delete_profile(profile_id)


@router.get("/api/current")
def get_current_learning_state(profile_id: Optional[int] = None) -> dict[str, object]:
    return profiles_service.get_current_learning_state(profile_id)


@router.get("/api/growth/summary", response_model=GrowthSummaryResponse)
def get_growth_summary(profile_id: Optional[int] = None) -> dict[str, object]:
    return profiles_service.get_growth_summary(profile_id)
