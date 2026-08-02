"""对话双语展示：英文句子 → 中文翻译。"""
from app import dependencies as deps


def translate(text: str) -> dict[str, object]:
    settings = deps.load_settings()
    llm = deps.create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )
    try:
        translated = llm.complete(
            system_prompt=(
                "You are a concise English-to-Chinese translator for a speaking coach. "
                "Translate the user's English into natural, plain Chinese. "
                "Output ONLY the translation, no explanation."
            ),
            user_prompt=text,
        ).strip()
        translated = translated.replace("```", "").strip()
    except Exception:  # pragma: no cover - LLM 不可用时双语功能降级
        translated = ""
    return {"text": text, "translation_zh": translated}
