"""Scenario favorites belong to the authenticated account, including guests."""
from fastapi import APIRouter, HTTPException
from app import dependencies as deps
from app.scenarios import get_scenario
from app.services import account
from app.services.auth_service import _connection

router = APIRouter()

@router.post("/api/favorites/{scenario_id}")
def add_favorite(scenario_id: str, profile_id: int | None = None):
    if get_scenario(scenario_id) is None:
        raise HTTPException(404, "Scenario not found")
    if profile_id is not None and deps.get_repository().get_profile(profile_id) is None:
        raise HTTPException(404, "Profile not found")
    with _connection() as conn:
        cursor = conn.execute("INSERT OR IGNORE INTO account_favorites(owner_key, profile_id, scenario_id) VALUES (?, ?, ?)", (account.owner(), profile_id, scenario_id))
        created = cursor.rowcount > 0
    return {"status": "success", "favorite": created}

@router.delete("/api/favorites/{scenario_id}")
def remove_favorite(scenario_id: str, profile_id: int | None = None):
    with _connection() as conn:
        removed = conn.execute("DELETE FROM account_favorites WHERE owner_key = ? AND scenario_id = ?", (account.owner(), scenario_id)).rowcount > 0
    return {"status": "success", "removed": removed}

@router.get("/api/favorites")
def list_favorites(profile_id: int | None = None):
    return {"favorites": [dict(item, is_favorite=True) for row in account.favorite_rows() if (item := get_scenario(row["scenario_id"]))]}
