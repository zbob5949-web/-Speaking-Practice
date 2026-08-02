"""跨平台 TTS：edge-tts 生成 MP3。

替代原 macOS 专属的 say/afconvert 方案，可在任意平台运行。
音色与语速通过环境变量配置：TTS_VOICE / TTS_RATE。
"""
import asyncio

import edge_tts

from app.config import load_settings


async def _synthesize(text: str, voice: str, rate: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    buffer = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.extend(chunk["data"])
    return bytes(buffer)


def synthesize_tts_audio(text: str) -> bytes:
    """生成 MP3 音频字节。失败时抛出 RuntimeError（由路由层转 502）。"""
    settings = load_settings()
    try:
        return asyncio.run(
            asyncio.wait_for(
                _synthesize(text, voice=settings.tts_voice, rate=settings.tts_rate),
                timeout=30,
            )
        )
    except Exception as exc:
        raise RuntimeError(f"TTS synthesis failed: {exc}") from exc
