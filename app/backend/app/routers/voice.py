"""语音对话闭环路由：上传语音 → AI 回复（含语音输出）。"""
from fastapi import APIRouter, HTTPException, UploadFile

from app.services import voice as voice_service

router = APIRouter()


@router.post("/api/voice/turn")
def voice_turn(session_id: int, audio: UploadFile, voice: str | None = None) -> dict:
    """上传一段语音（multipart 字段 audio），返回识别文本、AI 回复、纠错与回复语音。

    同步端点：FastAPI 在线程池中执行，便于内部 TTS(asyncio) 正常工作。

    示例（curl）:
        curl -X POST "http://localhost:8000/api/voice/turn?session_id=1" \\
             -F "audio=@hello.mp3;type=audio/mpeg"
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="缺少音频文件")
    audio_bytes = audio.file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="音频内容为空")
    return voice_service.voice_turn(session_id, audio_bytes, voice=voice)
