"""语音合成：生成 AI 回复语音，并提供可用陪练老师音色列表。"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import load_settings
from app.models import TTSRequest
from app.tts import synthesize_tts_audio
from app.tts_voices import TTS_VOICES

router = APIRouter()


@router.post("/api/tts")
def generate_tts(request: TTSRequest) -> Response:
    try:
        audio_bytes = synthesize_tts_audio(request.text, voice=request.voice)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.get("/api/tts/voices")
def list_voices() -> dict:
    """返回可选陪练老师音色列表；default 标记后端当前默认音色。"""
    settings = load_settings()
    default_voice = settings.tts_voice
    voices = [
        {**voice, "default": voice["id"] == default_voice}
        for voice in TTS_VOICES
    ]
    return {"voices": voices, "default_voice": default_voice}
