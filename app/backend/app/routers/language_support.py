"""语言支持（解释/定义/翻译/地道表达）。"""
from fastapi import APIRouter

from app.models import LanguageSupportRequest
from app.services import language_support as language_support_service

router = APIRouter()


@router.post("/api/language-support")
def language_support(request: LanguageSupportRequest) -> dict[str, object]:
    return language_support_service.explain(request)
