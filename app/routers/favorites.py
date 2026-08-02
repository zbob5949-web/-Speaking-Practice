"""收藏：用户收藏的对话场景（参照灵小游 favorites 接口模式，绑定本地 profile）。"""
from fastapi import APIRouter, HTTPException, Query

from app import dependencies as deps
from app.scenarios import get_scenario

router = APIRouter()


@router.post("/api/favorites/{scenario_id}")
def add_favorite(scenario_id: str, profile_id: int = Query(...)) -> dict[str, object]:
    repo = deps.get_repository()
    if repo.get_profile(profile_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    if get_scenario(scenario_id) is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    created = repo.add_favorite(profile_id, scenario_id)
    return {"status": "success", "favorite": created}


@router.delete("/api/favorites/{scenario_id}")
def remove_favorite(scenario_id: str, profile_id: int = Query(...)) -> dict[str, object]:
    repo = deps.get_repository()
    removed = repo.remove_favorite(profile_id, scenario_id)
    return {"status": "success" if removed else "not_found", "removed": removed}


@router.get("/api/favorites")
def list_favorites(profile_id: int = Query(...)) -> dict[str, object]:
    """返回收藏的场景详情列表（含难度分级）。"""
    repo = deps.get_repository()
    rows = repo.list_favorites(profile_id)
    items = []
    for row in rows:
        scenario = get_scenario(row["scenario_id"])
        if scenario:
            items.append(scenario)
    return {"favorites": items}
