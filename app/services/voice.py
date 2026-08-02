"""语音对话闭环：ASR 识别 → 增强回合（AI 回复+纠错+记忆）→ TTS 合成回复语音。"""
import base64

from fastapi import HTTPException

from app.asr import get_engine
from app import dependencies as deps
from app.services.enhanced_turn import enhanced_user_turn
from app.tts import synthesize_tts_audio


def voice_turn(session_id: int, audio_bytes: bytes) -> dict:
    """上传一段语音，返回识别文本、AI 回复、纠错报告与回复语音（MP3 base64）。"""
    result = get_engine().transcribe_audio(audio_bytes)
    user_text = result["text"].strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="未能识别到语音内容，请重新说一遍")

    repo = deps.get_repository()
    turn_result = enhanced_user_turn(repo, session_id, user_text)

    # 联动 TTS：把 AI 回复直接合成语音，省去 App 端二次请求。
    # 端点已在 FastAPI 线程池中执行，此处可直接 asyncio.run，无事件循环冲突。
    tts_audio = b""
    tts_error = None
    try:
        tts_audio = synthesize_tts_audio(turn_result["assistant_turn"]["text"])
        if not tts_audio:
            tts_error = "empty audio returned by edge-tts"
    except Exception as exc:
        # TTS 失败不阻断对话，返回 None 由客户端降级展示文字
        tts_error = f"{type(exc).__name__}: {exc}"
        tts_audio = b""

    return {
        "user_text": user_text,
        **turn_result,
        "tts_audio_b64": base64.b64encode(tts_audio).decode("ascii") if tts_audio else None,
        "tts_mime": "audio/mpeg",
        "tts_error": tts_error,
    }
