"""语音合成。"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.models import TTSRequest
from app.tts import synthesize_tts_audio

router = APIRouter()


@router.post("/api/tts")
def generate_tts(request: TTSRequest) -> Response:
    try:
        audio_bytes = synthesize_tts_audio(request.text)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=audio_bytes, media_type="audio/mpeg")
