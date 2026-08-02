"""本地 ASR：基于 sherpa-onnx 的英文语音识别（免 key、离线）。

- 模型目录由环境变量 ASR_MODEL_DIR 指定，默认 <项目根>/data/asr_model/ 下优先 whisper 模型
- 音频解码用 miniaudio（支持 MP3/WAV/OGG → 16kHz 单声道 float32）
- 支持三种模型形态：流式 zipformer（OnlineRecognizer）、非流式 zipformer（OfflineRecognizer）、whisper（OfflineRecognizer）
"""
import os
from pathlib import Path

import miniaudio

try:
    import numpy as np
    import sherpa_onnx
except ImportError:  # pragma: no cover - 仅保证模块在未安装依赖时可导入
    np = None
    sherpa_onnx = None


def _default_model_dir() -> Path:
    env = os.getenv("ASR_MODEL_DIR")
    if env:
        return Path(env)
    project_root = Path(__file__).resolve().parents[3]
    base = project_root / "data" / "asr_model"
    candidates = [child for child in sorted(base.iterdir()) if child.is_dir() and list(child.glob("*.onnx"))]
    if not candidates:
        return base
    # whisper 优先（对整句文件识别质量最好），其次非流式 zipformer，最后任意
    def rank(child: Path) -> int:
        name = child.name.lower()
        if "whisper" in name:
            return 0
        if "streaming" not in name:
            return 1
        return 2
    return min(candidates, key=rank)


class AsrEngine:
    """sherpa-onnx 识别引擎封装。"""

    def __init__(self, model_dir: Path | None = None):
        if sherpa_onnx is None:
            raise RuntimeError("sherpa-onnx 未安装，请先 pip install sherpa-onnx")
        self.model_dir = Path(model_dir) if model_dir else _default_model_dir()
        if not self.model_dir.is_dir() or not list(self.model_dir.glob("*.onnx")):
            raise RuntimeError(
                f"ASR 模型缺失: {self.model_dir}。请下载模型并设置 ASR_MODEL_DIR。"
            )
        self.recognizer = self._build_recognizer()
        self.sample_rate = 16000

    def _files(self) -> dict[str, Path]:
        found: dict[str, Path] = {}
        for path in self.model_dir.glob("*.onnx"):
            name = path.stem.lower()
            is_int8 = ".int8" in name
            for key in ("encoder", "decoder", "joiner"):
                if key in name and (key not in found or (is_int8 and ".int8" not in found[key].stem)):
                    found[key] = path
        return found

    def _build_recognizer(self):
        files = self._files()
        tokens = self.model_dir / "tokens.txt"
        for maybe in self.model_dir.glob("*tokens.txt"):
            tokens = maybe
            break
        encoder, decoder, joiner = files.get("encoder"), files.get("decoder"), files.get("joiner")
        is_streaming = "streaming" in self.model_dir.name.lower()

        if encoder and decoder and joiner:
            if is_streaming:
                # 流式 zipformer 转写模型
                return sherpa_onnx.OnlineRecognizer.from_transducer(
                    tokens=str(tokens),
                    encoder=str(encoder),
                    decoder=str(decoder),
                    joiner=str(joiner),
                    num_threads=2,
                    sample_rate=16000,
                    feature_dim=80,
                    enable_endpoint_detection=False,
                )
            # 非流式 zipformer 模型
            return sherpa_onnx.OfflineRecognizer.from_zipformer(
                tokens=str(tokens),
                encoder=str(encoder),
                decoder=str(decoder),
                joiner=str(joiner),
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
            )
        if encoder and decoder:
            # whisper 模型（固定 16kHz，无需 sample_rate）
            return sherpa_onnx.OfflineRecognizer.from_whisper(
                tokens=str(tokens),
                encoder=str(encoder),
                decoder=str(decoder),
                num_threads=2,
                language="en",
                task="transcribe",
            )
        raise RuntimeError(f"无法识别模型形态: {sorted(files)}")

    def transcribe_audio(self, audio_bytes: bytes) -> dict:
        """解码音频并识别，返回 {"text": str, "provider": "local-sherpa-onnx", "confidence": float}"""
        samples = decode_audio_to_float32(audio_bytes, self.sample_rate)
        if len(samples) == 0:
            return {"text": "", "provider": "local-sherpa-onnx", "confidence": 0.0}

        recognizer = self.recognizer
        if isinstance(recognizer, sherpa_onnx.OnlineRecognizer):
            stream = recognizer.create_stream()
            samples_list = samples.tolist()
            chunk = self.sample_rate // 10  # 0.1s 一块
            for i in range(0, len(samples_list), chunk):
                stream.accept_waveform(self.sample_rate, samples_list[i : i + chunk])
                while recognizer.is_ready(stream):
                    recognizer.decode_stream(stream)
            while recognizer.is_ready(stream):
                recognizer.decode_stream(stream)
            text = recognizer.get_result(stream).strip()
        else:
            stream = recognizer.create_stream()
            stream.accept_waveform(self.sample_rate, samples.tolist())
            recognizer.decode_streams([stream])
            text = stream.result.text.strip()

        return {"text": text, "provider": "local-sherpa-onnx", "confidence": 1.0}


def decode_audio_to_float32(audio_bytes: bytes, sample_rate: int = 16000) -> "np.ndarray":
    """用 miniaudio 解码任意受支持格式（MP3/WAV/OGG…）到 16kHz 单声道 float32。"""
    if np is None:
        raise RuntimeError("numpy 未安装，请先 pip install numpy")
    decoded = miniaudio.decode(
        audio_bytes,
        output_format=miniaudio.SampleFormat.FLOAT32,
        nchannels=1,
        sample_rate=sample_rate,
    )
    return np.frombuffer(decoded.samples, dtype=np.float32)


_engine: AsrEngine | None = None


def get_engine() -> AsrEngine:
    """全局单例：模型加载一次复用。"""
    global _engine
    if _engine is None:
        _engine = AsrEngine()
    return _engine
