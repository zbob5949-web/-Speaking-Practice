"""语言支持（解释/定义/翻译/地道表达）。"""
from app.agents import LanguageSupportAgent
from app import dependencies as deps
from app.models import LanguageSupportRequest


def explain(request: LanguageSupportRequest) -> dict[str, object]:
    repo = deps.get_repository()
    settings = deps.load_settings()
    llm = deps.create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )
    return LanguageSupportAgent(llm, repo.get_prompt).explain(
        mode=request.mode,
        text=request.text.strip(),
        context=request.context,
    )
