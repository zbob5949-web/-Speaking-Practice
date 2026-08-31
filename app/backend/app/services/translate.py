"""对话双语展示：英文句子 → 中文翻译。"""
from app import dependencies as deps

# 翻译是轻量请求：短超时(10s) + 一次重试，避免 DeepSeek 偶发慢请求
# 拖住前端双语展示几 10 秒甚至 30 秒超时。
_TRANSLATE_TIMEOUT = 10.0


def translate(text: str) -> dict[str, object]:
    settings = deps.load_settings()
    llm = deps.create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )
    translated = ""
    for attempt in range(2):
        try:
            translated = llm.complete(
                system_prompt=(
                    "You are a concise English-to-Chinese translator for a speaking coach. "
                    "Translate the user's English into natural, plain Chinese. "
                    "Output ONLY the translation, no explanation."
                ),
                user_prompt=text,
                timeout=_TRANSLATE_TIMEOUT,
            ).strip()
            translated = translated.replace("```", "").strip()
            if translated:
                break
        except Exception:  # pragma: no cover - LLM 不可用时双语功能降级
            translated = ""
    return {"text": text, "translation_zh": translated}
