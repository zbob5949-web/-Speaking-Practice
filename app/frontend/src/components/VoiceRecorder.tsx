import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import { transcribeAudio } from "../api";

type Props = {
  disabled?: boolean;
  /** 录音转文字：转换结果放入文本框 */
  onText: (text: string) => void;
  /** 长按录音：松手后输出音频（由对话页隐式转文字并触发 AI 回复） */
  onVoiceMessage?: (blob: Blob, durationMs: number) => void;
  /** 电话模式：为 true 时进入自动录音（静音自动停止），循环由父组件信号驱动 */
  autoMode?: boolean;
  /** 每次递增触发一次自动开始录音（父组件在 AI 说完后 +1） */
  autoRecordSignal?: number;
};

const BAR_COUNT = 24;
const IDLE_WAVEFORM = Array.from({ length: BAR_COUNT }, (_, index) => 18 + ((index * 7) % 13));
const CANCEL_SLIDE = 64;

type AudioContextWindow = Window & {
  webkitAudioContext?: typeof AudioContext;
};

type RecordMode = "hold" | "transcribe";

export function VoiceRecorder({ disabled = false, onText, onVoiceMessage, autoMode = false, autoRecordSignal = 0 }: Props) {
  const [mode, setMode] = useState<RecordMode>("hold");
  const [isRecording, setIsRecording] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [waveform, setWaveform] = useState(IDLE_WAVEFORM);
  const [error, setError] = useState("");
  const [hint, setHint] = useState("");

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startYRef = useRef<number | null>(null);
  const activeModeRef = useRef<RecordMode>("hold");
  const finishedRef = useRef(false);
  const startTimeRef = useRef(0);
  // 电话模式：自动录音相关
  const autoModeRef = useRef(false);
  const hasSpokenRef = useRef(false);
  const silenceStartRef = useRef<number | null>(null);
  const onTextRef = useRef(onText);
  const onVoiceMessageRef = useRef(onVoiceMessage);

  useEffect(() => {
    onTextRef.current = onText;
  }, [onText]);
  useEffect(() => {
    onVoiceMessageRef.current = onVoiceMessage;
  }, [onVoiceMessage]);

  // 进入/退出电话模式：退出时取消进行中的录音
  useEffect(() => {
    autoModeRef.current = autoMode;
    if (!autoMode) {
      hasSpokenRef.current = false;
      silenceStartRef.current = null;
      if (recorderRef.current && recorderRef.current.state === "recording") {
        stopRecording(true);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoMode]);

  // 父组件信号：AI 已说完，开始新一轮自动录音
  useEffect(() => {
    if (!autoMode || autoRecordSignal <= 0) return;
    hasSpokenRef.current = false;
    silenceStartRef.current = null;
    void startRecording("transcribe");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRecordSignal]);

  const stopWaveform = () => {
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    setWaveform(IDLE_WAVEFORM);
  };

  const cleanupAudio = () => {
    stopWaveform();
    analyserRef.current?.disconnect();
    analyserRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    const audioContext = audioContextRef.current;
    audioContextRef.current = null;
    if (audioContext && audioContext.state !== "closed") {
      void audioContext.close();
    }
  };

  const updateWaveform = () => {
    const analyser = analyserRef.current;
    if (!analyser) return;

    const timeData = new Uint8Array(analyser.fftSize);
    const frequencyData = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteTimeDomainData(timeData);
    analyser.getByteFrequencyData(frequencyData);

    let energy = 0;
    for (const value of timeData) {
      const normalized = (value - 128) / 128;
      energy += normalized * normalized;
    }
    let amplitude = Math.min(1, Math.sqrt(energy / timeData.length) * 3.2);
    // 电话模式：检测到说过话后，连续静音 1.2 秒自动停止并转写
    if (autoModeRef.current && recorderRef.current && recorderRef.current.state === "recording") {
      if (amplitude > 0.05) {
        hasSpokenRef.current = true;
        silenceStartRef.current = null;
      } else if (hasSpokenRef.current) {
        if (silenceStartRef.current === null) {
          silenceStartRef.current = performance.now();
        } else if (performance.now() - silenceStartRef.current > 1200) {
          silenceStartRef.current = null;
          hasSpokenRef.current = false;
          stopRecording(false);
        }
      }
    }
    const bars = Array.from({ length: BAR_COUNT }, (_, index) => {
      const start = Math.floor((index / BAR_COUNT) * frequencyData.length);
      const end = Math.max(start + 1, Math.floor(((index + 1) / BAR_COUNT) * frequencyData.length));
      let tone = 0;
      for (let cursor = start; cursor < end; cursor += 1) {
        tone += frequencyData[cursor] / 255;
      }
      tone /= end - start;
      return Math.round(18 + amplitude * 42 + tone * 44 + Math.abs(Math.sin(index * 1.7)) * amplitude * 12);
    });
    setWaveform(bars);
    animationFrameRef.current = requestAnimationFrame(updateWaveform);
  };

  const finishRecording = async (blob: Blob, filename: string) => {
    setIsTranscribing(true);
    setError("");
    setHint("识别中…");
    try {
      const result = await transcribeAudio(blob, filename);
      const text = result.text.trim();
      if (!text) {
        setError("没有识别到清晰语音，请再试一次");
      } else {
        onTextRef.current(text);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "语音识别失败，请再试一次");
    } finally {
      setIsTranscribing(false);
      setHint("");
    }
  };

  const stopRecording = (cancelled: boolean) => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    finishedRef.current = true;
    const mode = activeModeRef.current;
    const durationMs = Math.max(200, Date.now() - startTimeRef.current);
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      recorderRef.current = null;
      cleanupAudio();
      setIsRecording(false);
      setIsCancelling(false);
      startYRef.current = null;
      if (!cancelled && blob.size > 0) {
        if (mode === "hold" && onVoiceMessageRef.current) {
          // 语音条：直接把音频交给对话页，由对话页隐式转文字并触发 AI 回复
          onVoiceMessageRef.current(blob, durationMs);
        } else {
          void finishRecording(blob, "speakmate-recording.webm");
        }
      }
    };
    recorder.stop();
  };

  const startRecording = async (nextMode: RecordMode) => {
    if (disabled || isRecording || isTranscribing) return;
    setError("");
    setHint("");

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("当前浏览器不支持录音，请改用音频文件测试");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true, // 浏览器自动增益：小声说话也会被放大，提升识别灵敏度
        },
      });
      streamRef.current = stream;
      chunksRef.current = [];
      finishedRef.current = false;

      const mimeType = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/ogg"
      ].find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        setError("录音失败，请检查麦克风权限");
        setIsRecording(false);
        cleanupAudio();
      };

      const AudioContextCtor = window.AudioContext ?? (window as AudioContextWindow).webkitAudioContext;
      if (AudioContextCtor) {
        const audioContext = new AudioContextCtor();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        audioContextRef.current = audioContext;
        analyserRef.current = analyser;
        animationFrameRef.current = requestAnimationFrame(updateWaveform);
      }

      recorder.start();
      activeModeRef.current = nextMode;
      startTimeRef.current = Date.now();
      setIsRecording(true);
      setIsCancelling(false);
      startYRef.current = null;
    } catch (reason) {
      cleanupAudio();
      setError(reason instanceof DOMException && reason.name === "NotAllowedError"
        ? "请允许麦克风权限后再录音"
        : "无法打开麦克风，请检查设备");
    }
  };

  // 长按：按住开始录音
  const handleHoldStart = (event: React.PointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    startYRef.current = event.clientY;
    void startRecording("hold");
  };

  const handleHoldMove = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (!isRecording || activeModeRef.current !== "hold") return;
    if (startYRef.current !== null && startYRef.current - event.clientY > CANCEL_SLIDE) {
      setIsCancelling(true);
    } else {
      setIsCancelling(false);
    }
  };

  const handleHoldEnd = () => {
    if (!isRecording || activeModeRef.current !== "hold") return;
    stopRecording(isCancelling);
  };

  const handleHoldCancel = () => {
    if (!isRecording || activeModeRef.current !== "hold") return;
    stopRecording(true);
  };

  // 转文字：点击开始 / 再点停止
  const handleTranscribeClick = () => {
    if (disabled || isTranscribing) return;
    if (isRecording && activeModeRef.current === "transcribe") {
      stopRecording(false);
    } else {
      setMode("transcribe");
      void startRecording("transcribe");
    }
  };

  const handleFile = (file?: File) => {
    if (!file || disabled || isRecording || isTranscribing) return;
    const isAudio = file.type.startsWith("audio/") || /\.(mp3|m4a|wav|ogg|webm)$/i.test(file.name);
    if (!isAudio) {
      setError("请拖入 MP3 或其他音频文件");
      return;
    }
    void finishRecording(file, file.name);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    handleFile(event.dataTransfer.files[0]);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    handleFile(event.target.files?.[0]);
    event.target.value = "";
  };

  useEffect(() => () => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    cleanupAudio();
  }, []);

  return (
    <div className="voice-recorder" aria-live="polite">
      <div
        className={isDragging ? "voice-drop-zone voice-drop-zone-active" : "voice-drop-zone"}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (event.currentTarget === event.target) setIsDragging(false);
        }}
        onDrop={handleDrop}
      >
        <button
          className={isRecording && activeModeRef.current === "hold"
            ? "voice-hold-button voice-hold-button-active"
            : "voice-hold-button"}
          type="button"
          disabled={disabled || isTranscribing}
          aria-label={isRecording && activeModeRef.current === "hold" ? "录音中，松开发送，上滑取消" : "按住说话，松开发送，上滑取消"}
          onPointerDown={handleHoldStart}
          onPointerMove={handleHoldMove}
          onPointerUp={handleHoldEnd}
          onPointerCancel={handleHoldCancel}
          onPointerLeave={handleHoldMove}
        >
          <span className="voice-hold-icon" aria-hidden="true">●</span>
          <span>{isRecording && activeModeRef.current === "hold" ? "松开发送" : "按住说话"}</span>
        </button>
        <button
          className={isRecording && activeModeRef.current === "transcribe"
            ? "voice-transcribe-button voice-transcribe-button-active"
            : "voice-transcribe-button"}
          type="button"
          disabled={disabled || (isRecording && activeModeRef.current === "hold") || isTranscribing}
          aria-label="录音转文字"
          onClick={handleTranscribeClick}
        >
          <span className="voice-transcribe-icon" aria-hidden="true">文</span>
          <span>{isRecording && activeModeRef.current === "transcribe" ? "点击完成" : "录音转文字"}</span>
        </button>
        <label className="voice-file-button">
          <span>选择音频</span>
          <input
            type="file"
            accept=".mp3,audio/mpeg,audio/*"
            onChange={handleFileChange}
            disabled={disabled || isRecording || isTranscribing}
          />
        </label>
        <span className="voice-drop-hint">或把 MP3 拖到这里测试</span>
      </div>
      <div
        className={isRecording ? "voice-waveform voice-waveform-active" : "voice-waveform"}
        role="img"
        aria-label={isRecording ? "正在录音，音波会随声音变化" : "录音音波"}
      >
        {waveform.map((height, index) => (
          <span key={index} style={{ height: height + "%" }} />
        ))}
      </div>
      {isRecording && activeModeRef.current === "hold" ? (
        <span className={isCancelling ? "voice-cancel-hint voice-cancel-hint-active" : "voice-cancel-hint"}>
          {isCancelling ? "松开取消发送" : "松开发送 · 上滑取消"}
        </span>
      ) : null}
      {hint ? <span className="voice-hint">{hint}</span> : null}
      {error ? <span className="voice-recorder-error" role="alert">{error}</span> : null}
    </div>
  );
}
