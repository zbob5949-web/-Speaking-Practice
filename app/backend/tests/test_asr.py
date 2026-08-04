"""ASR 音量归一化单元测试：小音量放大、大音量保持、静音不动。"""
import numpy as np

from app.asr import TARGET_PEAK, normalize_volume


def test_normalize_volume_amplifies_quiet_speech():
    # 峰值约 0.05 的轻声语音：应被放大到接近 TARGET_PEAK
    quiet = (np.sin(np.linspace(0, 40, 800)).astype(np.float32)) * 0.05
    out = normalize_volume(quiet)
    assert float(np.max(np.abs(out))) > 0.3
    assert float(np.max(np.abs(out))) <= TARGET_PEAK + 1e-6


def test_normalize_volume_keeps_loud_audio_unchanged():
    loud = np.full(200, 0.95, dtype=np.float32)
    out = normalize_volume(loud)
    assert np.array_equal(out, loud)


def test_normalize_volume_ignores_silence():
    silence = np.zeros(200, dtype=np.float32)
    out = normalize_volume(silence)
    assert np.array_equal(out, silence)


def test_normalize_volume_caps_extreme_gain_on_faint_noise():
    # 极微弱信号：增益被封顶，输出不会爆炸
    faint = np.full(200, 1e-3, dtype=np.float32)
    out = normalize_volume(faint)
    assert float(np.max(np.abs(out))) < 0.1


def test_normalize_volume_handles_empty_input():
    out = normalize_volume(np.array([], dtype=np.float32))
    assert len(out) == 0
