"""手工场景库接口：供前端场景卡片、分类筛选与学习路线使用。"""
from fastapi import APIRouter, HTTPException

from app import dependencies as deps
from app.scenarios import TIER_LEVELS, get_scenario, learning_path, list_categories, list_roles, list_scenarios, tier_for_level

router = APIRouter()


@router.get("/api/scenarios")
def scenarios(
    profile_id: int | None = None,
    level: str | None = None,
    category: str | None = None,
    role: str | None = None,
    tier: str | None = None,
) -> dict[str, object]:
    """返回全部手工场景（含完整难度分级 bands），支持 背景设定/角色/难度分级 过滤。

    - category: 背景设定（出行/餐饮/职场/医疗/购物…）
    - role: 角色描述（NPC 角色名）
    - tier: 难度分级（beginner 小白 / intermediate 中级 / advanced 大神）
    - level: 显式 CEFR 等级，仅在传入时把 difficulty 压缩到该等级

    不传过滤时返回每个场景的完整难度分级（bands），让"全部"状态下一次展出所有内容，
    而不是按用户水平默认压缩成单一等级。
    """
    profile_level: str | None = None
    if profile_id:
        repo = deps.get_repository()
        profile = repo.get_profile(profile_id)
        if profile:
            profile_level = profile["current_level"]
    items = list_scenarios(level)
    if category:
        items = [item for item in items if item["category"] == category]
    if role:
        items = [item for item in items if item["npc_role"] == role]
    if tier:
        codes = TIER_LEVELS.get(tier, ())
        for item in items:
            band = next((b for b in item["bands"] if b["level"] in codes), None)
            if band:
                item["difficulty"] = band
    if profile_id:
        repo = deps.get_repository()
        favorites = {item["scenario_id"] for item in repo.list_favorites(profile_id)}
        for item in items:
            item["is_favorite"] = item["id"] in favorites
    derived_tier = tier or (tier_for_level(profile_level) if profile_level else None)
    return {
        "scenarios": items,
        "categories": list_categories(),
        "roles": list_roles(),
        "tiers": [
            {"id": "beginner", "label": "小白", "levels": list(TIER_LEVELS["beginner"])},
            {"id": "intermediate", "label": "中级", "levels": list(TIER_LEVELS["intermediate"])},
            {"id": "advanced", "label": "大神", "levels": list(TIER_LEVELS["advanced"])},
        ],
        "derived_tier": derived_tier,
    }


@router.get("/api/scenarios/learning-path")
def scenario_learning_path(tier: str | None = None, profile_id: int | None = None) -> dict[str, object]:
    """按 小白/中级/大神 生成学习路线：该难度带内全部场景，由易到难。"""
    if not tier and profile_id:
        repo = deps.get_repository()
        profile = repo.get_profile(profile_id)
        if profile:
            tier = tier_for_level(profile["current_level"])
    return learning_path(tier or "intermediate")


@router.get("/api/scenarios/{scenario_id}")
def scenario_detail(scenario_id: str, level: str | None = None) -> dict[str, object]:
    item = get_scenario(scenario_id, level)
    if item is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return item
