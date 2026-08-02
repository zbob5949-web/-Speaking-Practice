"""翻译接口：对话双语展示。"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services import translate as translate_service

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/api/translate")
def translate(request: TranslateRequest) -> dict[str, object]:
    return translate_service.translate(request.text.strip())
