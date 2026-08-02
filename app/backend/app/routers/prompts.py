"""Prompt 管理。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import dependencies as deps

router = APIRouter()


class PromptUpdateRequest(BaseModel):
    content: str


@router.get("/api/prompts")
def get_prompts() -> dict[str, object]:
    return {"prompts": deps.get_repository().get_all_prompts()}


@router.put("/api/prompts/{name}")
def update_prompt(name: str, request: PromptUpdateRequest) -> dict[str, str]:
    repo = deps.get_repository()
    if not repo.update_prompt(name, request.content):
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"status": "success"}
