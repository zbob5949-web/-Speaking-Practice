"""语音识别路由：上传音频文件（MP3/WAV/OGG）→ 返回识别文字。"""
from fastapi import APIRouter, HTTPException, UploadFile

from app.asr import AsrEngine

router = APIRouter()


@router.post("/api/asr")
def transcribe_audio(audio: UploadFile) -> dict:
    """上传音频文件（multipart 字段名 audio），返回识别文字。

    示例（curl）:
        curl -X POST http://localhost:8000/api/asr \\
             -F "audio=@hello.mp3;type=audio/mpeg"
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="缺少音频文件")
    audio_bytes = audio.file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="音频内容为空")

    engine = AsrEngine()
    try:
        result = engine.transcribe_audio(audio_bytes)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "text": result["text"],
        "provider": result["provider"],
        "confidence": result["confidence"],
        "filename": audio.filename,
    }
