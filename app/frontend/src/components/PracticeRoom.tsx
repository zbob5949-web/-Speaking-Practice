import { useEffect, useRef, useState } from "react";
import { clearSessionHistory, completeSession, deleteTurnPair, getSelectedVoice, playAudioFromUrl, sendUserTurnStream, startScenarioSession, startSession, playTTS, stopActiveAudio, transcribeAudio, translateText } from "../api";
import type { ConversationTurn, InlineFeedback, LanguageSupportResult, PlanDay, PracticeBrief, PracticeSession, Scenario, SessionCompletion, TargetExpression, TodayStrategy } from "../types";
import { PrimaryButton, SecondaryButton } from "./ui";
import { VoiceRecorder } from "./VoiceRecorder";
import { ScenarioPicker, SCENARIO_IMAGES } from "./ScenarioPicker";

type Props = {
  day?: PlanDay | null;
  scenario?: Scenario | null;
  todayStrategy?: TodayStrategy | null;
  profileId?: number;
  /** 当前学习路线（按水平生成的场景序列），用于完成后「继续下一张卡片」 */
  learningPath?: Scenario[] | null;
  onSelectScenario?: (scenario: Scenario) => void;
  /** 今日板块的自由对话入口 */
  onFreeTalk?: () => void;
};

const ASSISTANT_AVATAR = "A";
const USER_AVATAR = "我";
type LessonPhase = "learn" | "practice";

type CorrectionParts = {
  original: string;
  better: string;
  reason?: string;
  example?: string;
};

type FeedbackTimelineItem =
  | { kind: "feedback"; id: string; item: InlineFeedback }
  | { kind: "language"; id: string; result: LanguageSupportResult };

function feedbackTimelineItems(items: InlineFeedback[]): FeedbackTimelineItem[] {
  return items.map((item) => ({
    kind: "feedback",
    id: `feedback-${item.id}`,
    item,
  }));
}

function parseLegacyCorrection(text: string): CorrectionParts | null {
  const cleaned = text.replace(/^[💡✨]\s*/, "").trim();
  const match = cleaned.match(/^(.+?)\s*->\s*(.+?)(?:\s*[:：]\s*(.+))?$/);
  if (!match) return null;
  return {
    original: match[1].trim(),
    better: match[2].trim(),
    reason: match[3]?.trim(),
  };
}

function getCorrectionParts(item: InlineFeedback): CorrectionParts | null {
  if (item.original_fragment && item.better_expression) {
    return {
      original: item.original_fragment,
      better: item.better_expression,
      reason: item.reason_zh || item.feedback_text,
      example: item.example_sentence || undefined,
    };
  }
  return parseLegacyCorrection(item.feedback_text);
}

function FeedbackCard({ item, onLocate }: { item: InlineFeedback; onLocate?: (turnId: number) => void }) {
  const isGuidance = item.feedback_type === "guidance";
  const isLanguageHelp = item.feedback_type === "language_help";
  const correction = item.feedback_type === "correction" ? getCorrectionParts(item) : null;
  const locatable = Boolean(onLocate && item.turn_id);
  const locClass = locatable ? " feedback-card-locatable" : "";

  const handleLocate = () => {
    if (locatable && item.turn_id) onLocate?.(item.turn_id);
  };

  const locatableProps = locatable
    ? {
        onClick: handleLocate,
        tabIndex: 0,
        title: "点击定位到对应对话",
        "aria-label": "点击定位到对应对话",
        onKeyDown: (event: React.KeyboardEvent) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            handleLocate();
          }
        },
      }
    : {};

  if (correction) {
    return (
      <article className={"feedback-card feedback-card-correction" + locClass} {...locatableProps}>
        <div className="feedback-card-header">
          <p className="feedback-card-label">你这里的问题</p>
          {item.severity === "major" ? <span className="feedback-severity">主要问题</span> : null}
        </div>
        <div className="correction-swap">
          <div>
            <span>你说的是</span>
            <strong>{correction.original}</strong>
          </div>
          <div aria-hidden="true" className="correction-arrow">→</div>
          <div>
            <span>建议改成</span>
            <strong>{correction.better}</strong>
          </div>
        </div>
        {correction.reason ? (
          <p className="feedback-reason">
            <span>为什么：</span>{correction.reason}
          </p>
        ) : null}
        {correction.example ? (
          <p className="feedback-example">
            <span>下次直接说：</span>{correction.example}
          </p>
        ) : null}
      </article>
    );
  }

  if (isGuidance) {
    return (
      <article className={"feedback-card feedback-card-guidance" + locClass} {...locatableProps}>
        <p className="feedback-card-label">下一步可以这样说</p>
        <p>{item.reason_zh || item.feedback_text}</p>
        {item.example_sentence ? <p className="feedback-example">{item.example_sentence}</p> : null}
      </article>
    );
  }

  if (isLanguageHelp) {
    return (
      <article className={"feedback-card feedback-card-language" + locClass} {...locatableProps}>
        <p className="feedback-card-label">词义解答</p>
        {item.original_fragment ? <strong className="language-term">{item.original_fragment}</strong> : null}
        <p>{item.reason_zh || item.feedback_text}</p>
        {item.example_sentence ? <p className="feedback-example">{item.example_sentence}</p> : null}
      </article>
    );
  }

  return (
    <p className={"feedback-item" + locClass} {...locatableProps}>
      {item.feedback_text}
    </p>
  );
}

function LanguageSupportCard({ result }: { result: LanguageSupportResult }) {
  const mainText = result.meaning_zh || result.translation_zh || result.better_expression;

  return (
    <section className="language-support-result" aria-label="语言支援结果">
      <p className="coach-target-title">
        {result.mode === "expression" ? "表达支援" : "解释中文"}
      </p>
      <strong>{result.text}</strong>
      {mainText ? <p>{mainText}</p> : null}
      {result.scene_note_zh ? <p className="muted">{result.scene_note_zh}</p> : null}
      {result.example_sentence ? <p className="feedback-example">{result.example_sentence}</p> : null}
    </section>
  );
}

function expressionLabel(expression: TargetExpression) {
  return typeof expression === "string" ? expression : expression.expression;
}

function ExpressionCard({ expression }: { expression: TargetExpression }) {
  if (typeof expression === "string") {
    return <li>{expression}</li>;
  }

  return (
    <li className="lesson-expression-card">
      <strong>{expression.expression}</strong>
      {expression.meaning_zh ? <p>{expression.meaning_zh}</p> : null}
      {expression.example ? <p className="feedback-example">{expression.example}</p> : null}
      {expression.when_to_use ? <p className="muted">{expression.when_to_use}</p> : null}
    </li>
  );
}

export function PracticeRoom({ day, scenario, todayStrategy, profileId, learningPath, onSelectScenario, onFreeTalk }: Props) {
  const [session, setSession] = useState<PracticeSession | null>(null);
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [feedbackTimeline, setFeedbackTimeline] = useState<FeedbackTimelineItem[]>([]);
  const [practiceBrief, setPracticeBrief] = useState<PracticeBrief | null>(null);
  const [completion, setCompletion] = useState<SessionCompletion | null>(null);
  const [lessonPhase, setLessonPhase] = useState<LessonPhase>("practice");
  const [typedText, setTypedText] = useState("");
  const [apiError, setApiError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [streamingReply, setStreamingReply] = useState<string | null>(null);
  const [deletingTurnId, setDeletingTurnId] = useState<number | null>(null);
  const [isCompletingSession, setIsCompletingSession] = useState(false);
  const [isClearingHistory, setIsClearingHistory] = useState(false);
  const [dismissedCompletionSuggestion, setDismissedCompletionSuggestion] = useState(false);
  const [bilingualEnabled, setBilingualEnabled] = useState(() => localStorage.getItem("speakmate-bilingual") !== "off");
  // AI 回复自动朗读：默认开启，可一键静音（持久化到 localStorage）
  const [ttsMuted, setTtsMuted] = useState(() => localStorage.getItem("speakmate-tts-muted") === "on");
  const ttsMutedRef = useRef(ttsMuted);
  // 正在朗读的 AI 文字条 turn id：用于显示波峰谷跳动样式
  const [ttsSpeakingTurnId, setTtsSpeakingTurnId] = useState<number | null>(null);
  // 电话模式：自动录音循环对话，无需手动发消息
  const [phoneMode, setPhoneMode] = useState(false);
  const phoneModeRef = useRef(false);
  const [autoRecordSignal, setAutoRecordSignal] = useState(0);
  const nextRecordingTimerRef = useRef<number | null>(null);

  useEffect(() => {
    phoneModeRef.current = phoneMode;
  }, [phoneMode]);

  const triggerNextRecording = () => {
    if (!phoneModeRef.current) return;
    setAutoRecordSignal((n) => n + 1);
  };

  const scheduleNextRecording = () => {
    if (!phoneModeRef.current || isSubmittingRef.current) return;
    if (nextRecordingTimerRef.current !== null) return;
    nextRecordingTimerRef.current = window.setTimeout(() => {
      nextRecordingTimerRef.current = null;
      triggerNextRecording();
    }, 500);
  };

  const togglePhoneMode = () => {
    const next = !phoneMode;
    setPhoneMode(next);
    if (next) {
      // 进入电话模式：稍后开始第一轮自动录音
      nextRecordingTimerRef.current = window.setTimeout(() => {
        nextRecordingTimerRef.current = null;
        triggerNextRecording();
      }, 400);
    }
  };
  const [translations, setTranslations] = useState<Record<number, string>>({});
  const [voiceTurnIds, setVoiceTurnIds] = useState<Set<number>>(new Set());
  const [voiceMeta, setVoiceMeta] = useState<Map<number, { durationMs: number }>>(new Map());
  const [voiceFailedIds, setVoiceFailedIds] = useState<Set<number>>(new Set());
  const [voiceAudioUrls, setVoiceAudioUrls] = useState<Map<number, string>>(new Map());
  const [voiceTexts, setVoiceTexts] = useState<Map<number, string>>(new Map());
  const isSubmittingRef = useRef(false);
  const isCompleted = completion?.status === "completed";
  // 实时纠错定位：点击反馈卡片后高亮并滚动到对应对话回合
  const [highlightedTurnId, setHighlightedTurnId] = useState<number | null>(null);
  const highlightTimerRef = useRef<number | null>(null);

  const locateTurn = (turnId: number) => {
    setHighlightedTurnId(turnId);
    if (highlightTimerRef.current !== null) {
      window.clearTimeout(highlightTimerRef.current);
    }
    highlightTimerRef.current = window.setTimeout(() => setHighlightedTurnId(null), 1600);
    document
      .querySelector(`[data-turn-id="${turnId}"]`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  // 消息气泡纠错感叹号：展开该条消息对应的实时纠错
  const [openFeedbackTurnId, setOpenFeedbackTurnId] = useState<number | null>(null);

  useEffect(() => {
    if (openFeedbackTurnId === null) return;
    const handler = (event: PointerEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && !target.closest(".message-feedback-pop") && !target.closest(".feedback-alert")) {
        setOpenFeedbackTurnId(null);
      }
    };
    document.addEventListener("pointerdown", handler);
    return () => document.removeEventListener("pointerdown", handler);
  }, [openFeedbackTurnId]);

  const feedbackEndRef = useRef<HTMLDivElement>(null);
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const isFeedbackAtBottomRef = useRef(true);

  const isScenarioMode = Boolean(scenario);
  const isFreeTalk = scenario?.id === "free_talk";
  // 当前场景板块的背景图：有对应图片时显示为封面背景
  const topicImage = scenario ? SCENARIO_IMAGES[scenario.id] : undefined;

  const handleFeedbackScroll = (e: React.UIEvent<HTMLElement>) => {
    const target = e.currentTarget;
    const { scrollTop, scrollHeight, clientHeight } = target;
    // Keep it considered "at bottom" if within 20px
    isFeedbackAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 20;
  };

  useEffect(() => {
    if (isFeedbackAtBottomRef.current && feedbackEndRef.current) {
      feedbackEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [feedbackTimeline]);

  // 完成练习后：把对话区滚到底，让对话流末尾的总结卡片可见
  useEffect(() => {
    if (isCompleted && chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [isCompleted]);

  // TTS 播放：合并相邻句子，减少句间停顿
  const audioBufferRef = useRef("");
  const audioFlushTimerRef = useRef<number | null>(null);
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingAudioRef = useRef(false);
  const processedTextLenRef = useRef(0);

  const playNextAudio = async () => {
    if (isPlayingAudioRef.current) return;
    const textToPlay = audioQueueRef.current.shift();
    if (!textToPlay) {
      // 队列空：AI 已说完，电话模式下自动衔接下一轮录音
      if (phoneModeRef.current && !isSubmittingRef.current && !ttsMutedRef.current) {
        scheduleNextRecording();
      }
      if (!audioBufferRef.current) {
        // 缓冲也已清空：朗读结束，移除波峰谷跳动样式
        setTtsSpeakingTurnId(null);
      }
      return;
    }
    isPlayingAudioRef.current = true;
    try {
      // 使用设置中选择的陪练老师音色；未选择时后端使用默认音色
      await playTTS(textToPlay, getSelectedVoice() ?? undefined);
    } catch (e) {
      console.warn("Chunk TTS failed", e);
    }
    isPlayingAudioRef.current = false;
    void playNextAudio();
  };

  const queueAudioText = (text: string) => {
    if (ttsMutedRef.current) return; // 静音：AI 回复不再自动朗读
    const cleanText = text.trim();
    if (!cleanText) return;
    // 相邻句子合并到同一播放单元，缩短两句话之间的停顿
    audioBufferRef.current += (audioBufferRef.current ? " " : "") + cleanText;
    if (audioFlushTimerRef.current !== null) {
      window.clearTimeout(audioFlushTimerRef.current);
    }
    audioFlushTimerRef.current = window.setTimeout(() => {
      if (audioBufferRef.current) {
        audioQueueRef.current.push(audioBufferRef.current);
        audioBufferRef.current = "";
        void playNextAudio();
      }
    }, 450);
  };

  useEffect(() => () => {
    if (audioFlushTimerRef.current !== null) {
      window.clearTimeout(audioFlushTimerRef.current);
    }
    if (highlightTimerRef.current !== null) {
      window.clearTimeout(highlightTimerRef.current);
    }
    if (nextRecordingTimerRef.current !== null) {
      window.clearTimeout(nextRecordingTimerRef.current);
    }
    // 组件卸载：停止正在播放的音频并释放语音条 blob URL
    stopActiveAudio();
    audioQueueRef.current = [];
    audioBufferRef.current = "";
    setVoiceAudioUrls((current) => {
      for (const url of current.values()) URL.revokeObjectURL(url);
      return new Map();
    });
  }, []);

  useEffect(() => {
    ttsMutedRef.current = ttsMuted;
    if (ttsMuted) {
      // 一键静音：立刻停止正在播放的语音并清空待播队列
      stopActiveAudio();
      audioQueueRef.current = [];
      audioBufferRef.current = "";
      setTtsSpeakingTurnId(null);
    }
  }, [ttsMuted]);

  useEffect(() => {
    async function boot() {
      try {
        setApiError("");
        const result = scenario
          ? await startScenarioSession(scenario.id, profileId)
          : await startSession(day!.id);
        setSession(result.session);
        setTurns(result.turns);
        const feedbackHistory = result.feedback_history || [];
        setFeedbackTimeline(feedbackTimelineItems(feedbackHistory));
        setPracticeBrief(result.practice_brief || null);
        setCompletion(result.completion || null);
        const hasUserTurns = result.turns.some((turn) => turn.speaker === "user");
        // 自由对话直接进入对话，跳过课程简报
        setLessonPhase(result.practice_brief && !hasUserTurns && scenario?.id !== "free_talk" ? "learn" : "practice");
        setTranslations({});
        setVoiceTurnIds(new Set());
        setVoiceMeta(new Map());
        setVoiceFailedIds(new Set());
        setVoiceTexts(new Map());
        setVoiceAudioUrls((current) => {
          for (const url of current.values()) URL.revokeObjectURL(url);
          return new Map();
        });
      } catch {
        setApiError("无法开始练习会话，请稍后再试。");
      }
    }
    void boot();
  }, [scenario?.id, day?.id]);

  // 双语展示：按需为消息生成中文翻译（缓存；电话模式下双方消息都翻译）
  useEffect(() => {
    if (!bilingualEnabled) return;
    const pending = turns.filter(
      (turn) => !(turn.id in translations)
    );
    if (pending.length === 0) return;
    let cancelled = false;
    void (async () => {
      const next: Record<number, string> = {};
      for (const turn of pending.slice(0, 5)) {
        try {
          const result = await translateText(turn.text.slice(0, 1200));
          if (!cancelled && result.translation_zh) {
            next[turn.id] = result.translation_zh;
          }
        } catch {
          // 翻译失败静默，双语开关仍可用
        }
      }
      if (!cancelled && Object.keys(next).length > 0) {
        setTranslations((current) => ({ ...current, ...next }));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [turns, bilingualEnabled, translations]);

  async function submitTurn(text: string, voiceTempId?: number) {
    if (!session || !text.trim() || isSubmittingRef.current) return;

    isSubmittingRef.current = true;
    setIsSubmitting(true);
    setApiError("");

    // 语音条模式：复用已在对话里的语音条作为本轮用户消息（文字内容隐式携带）
    const existingVoiceTurn = voiceTempId ? turns.find((turn) => turn.id === voiceTempId) : undefined;
    const tempUserTurn: ConversationTurn = existingVoiceTurn
      ? { ...existingVoiceTurn, text: text.trim() }
      : {
          id: Date.now(),
          session_id: session.id,
          turn_index: turns.length + 1,
          speaker: "user",
          text: text.trim()
        };
    if (!existingVoiceTurn) {
      setTurns((current) => [...current, tempUserTurn]);
    }
    setTypedText("");
    setStreamingReply(""); // start stream

    processedTextLenRef.current = 0;
    audioQueueRef.current = [];
    let fullStreamedText = "";

    try {
      const result = await sendUserTurnStream(
        session.id,
        text.trim(),
        (chunk) => {
          fullStreamedText += chunk;
          setStreamingReply((prev) => (prev || "") + chunk);

          // TTS 句子匹配放在回调内（StrictMode 下 setState updater 会被调用两次，
          // 若在 updater 里入队会造成语音重复播放）
          const processedLen = processedTextLenRef.current;
          const unprocessed = fullStreamedText.slice(processedLen);
          const sentenceMatch = unprocessed.match(/([^.!?\n]+[.!?\n]+)/);
          if (sentenceMatch) {
            processedTextLenRef.current = processedLen + sentenceMatch[1].length;
            const cleanSentence = sentenceMatch[1].trim();
            if (cleanSentence.length > 0) {
              queueAudioText(cleanSentence);
            }
          }
        }
      );

      // End of stream, flush remaining text
      const remainingText = fullStreamedText.slice(processedTextLenRef.current).trim();
      if (remainingText.length > 0) {
        queueAudioText(remainingText);
      }
      setStreamingReply(null); // clear streaming reply

      // Stream done, replace temp turns with real ones
      const fallbackAssistantId = Date.now() + 1;
      setTurns((current) => {
        const withoutTemp = current.filter(t => t.id !== tempUserTurn.id);

        // If meta was successfully received, use the backend's saved turns
        if (result.user_turn && result.assistant_turn) {
          return [...withoutTemp, result.user_turn, result.assistant_turn];
        }

        // Resilience: if meta failed (e.g. backend feedback generation timeout),
        // we synthesize a temporary assistant turn so the text isn't lost.
        const fallbackAssistantTurn: ConversationTurn = {
          id: fallbackAssistantId,
          session_id: session.id,
          turn_index: tempUserTurn.turn_index + 1,
          speaker: "assistant",
          text: fullStreamedText.trim()
        };
        return [...withoutTemp, tempUserTurn, fallbackAssistantTurn];
      });

      // 标记正在朗读的 AI 文字条：TTS 队列/缓冲仍有内容时显示波峰谷跳动样式
      const assistantId = result.assistant_turn ? result.assistant_turn.id : fallbackAssistantId;
      if ((isPlayingAudioRef.current || audioQueueRef.current.length > 0 || audioBufferRef.current) && !ttsMutedRef.current) {
        setTtsSpeakingTurnId(assistantId);
      }

      if (result.inline_feedback && result.inline_feedback.length > 0) {
        setFeedbackTimeline(current => [...current, ...feedbackTimelineItems(result.inline_feedback)]);
      }
      // 语音条：把临时 id 迁移到后端返回的真实 user turn id，继续以语音条样式展示
      if (voiceTempId && result.user_turn) {
        setVoiceTurnIds((current) => {
          const next = new Set(current);
          next.delete(voiceTempId);
          next.add(result.user_turn.id);
          return next;
        });
        setVoiceMeta((current) => {
          const next = new Map(current);
          const meta = next.get(voiceTempId);
          next.delete(voiceTempId);
          if (meta) next.set(result.user_turn.id, meta);
          return next;
        });
        setVoiceAudioUrls((current) => {
          const next = new Map(current);
          const url = next.get(voiceTempId);
          next.delete(voiceTempId);
          if (url) next.set(result.user_turn.id, url);
          return next;
        });
        setVoiceTexts((current) => {
          const next = new Map(current);
          const text = next.get(voiceTempId);
          next.delete(voiceTempId);
          if (text) next.set(result.user_turn.id, text);
          return next;
        });
        setVoiceFailedIds((current) => {
          const next = new Set(current);
          next.delete(voiceTempId);
          return next;
        });
      }
      if (result.completion) {
        setCompletion(result.completion);
        if (result.completion.status === "completion_suggested") {
          setDismissedCompletionSuggestion(false);
        }
      }

    } catch {
      // Only set error if the stream completely failed to start
      if (!fullStreamedText) {
        setApiError("发送失败，请稍后再试。")
      } else {
        // If we got some text but then it crashed, we still want to keep the text
        setTurns((current) => {
          const withoutTemp = current.filter(t => t.id !== tempUserTurn.id);
          const fallbackAssistantTurn: ConversationTurn = {
            id: Date.now() + 1,
            session_id: session.id,
            turn_index: tempUserTurn.turn_index + 1,
            speaker: "assistant",
            text: fullStreamedText.trim()
          };
          return [...withoutTemp, tempUserTurn, fallbackAssistantTurn];
        });
      }
      setStreamingReply(null);
    } finally {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
      // 电话模式且已静音：AI 不播语音，文本显示即视为说完，直接衔接下一轮录音
      if (phoneModeRef.current && ttsMutedRef.current) {
        scheduleNextRecording();
      }
    }
  }

  // 语音条：先发送语音条（立即上屏），再隐式转文字触发 AI 回复，转换过程不可见
  async function handleVoiceMessage(blob: Blob, durationMs: number) {
    if (!session || isSubmittingRef.current) return;
    const voiceTempId = -Date.now();
    const voiceTurn: ConversationTurn = {
      id: voiceTempId,
      session_id: session.id,
      turn_index: turns.length + 1,
      speaker: "user",
      text: ""
    };
    const audioUrl = URL.createObjectURL(blob);
    setTurns((current) => [...current, voiceTurn]);
    setVoiceTurnIds((current) => new Set(current).add(voiceTempId));
    setVoiceMeta((current) => new Map(current).set(voiceTempId, { durationMs }));
    setVoiceAudioUrls((current) => new Map(current).set(voiceTempId, audioUrl));
    setApiError("");
    try {
      const result = await transcribeAudio(blob, "speakmate-recording.webm");
      const text = result.text.trim();
      if (!text) {
        setVoiceFailedIds((current) => new Set(current).add(voiceTempId));
        return;
      }
      setVoiceTexts((current) => new Map(current).set(voiceTempId, text));
      await submitTurn(text, voiceTempId);
    } catch {
      setVoiceFailedIds((current) => new Set(current).add(voiceTempId));
    }
  }

  async function playVoiceTurn(turnId: number) {
    const url = voiceAudioUrls.get(turnId);
    if (!url) return;
    try {
      await playAudioFromUrl(url);
    } catch {
      // 播放失败静默
    }
  }

  async function handleReplay(text: string, turnId?: number) {
    queueAudioText(text);
    // 重播时同样标记该文字条为正在朗读
    if (turnId != null && !ttsMutedRef.current) {
      setTtsSpeakingTurnId(turnId);
    }
  }

  async function handleDeleteTurnPair(userTurnId: number) {
    if (!session || deletingTurnId !== null) return;
    const shouldDelete = window.confirm("确定删除这一轮对话吗？删除后无法恢复。");
    if (!shouldDelete) return;

    setDeletingTurnId(userTurnId);
    setApiError("");
    try {
      const result = await deleteTurnPair(session.id, userTurnId);
      setTurns(result.turns);
      setFeedbackTimeline(feedbackTimelineItems(result.feedback_history));
    } catch {
      setApiError("删除失败，请稍后再试。")
    } finally {
      setDeletingTurnId(null);
    }
  }

  async function handleClearSessionHistory() {
    if (!session || isClearingHistory) return;
    const shouldClear = window.confirm("确定删除本次会话的全部对话与纠错记录吗？");
    if (!shouldClear) return;

    setIsClearingHistory(true);
    setApiError("");
    try {
      await clearSessionHistory(session.id);
      setTurns([]);
      setFeedbackTimeline([]);
      setSession(null);
      setCompletion(null);
    } catch {
      setApiError("清空本次会话失败，请稍后再试。");
    } finally {
      setIsClearingHistory(false);
    }
  }
  async function handleCompleteSession(completionType: "manual" | "agent_suggested" = "manual") {
    if (!session || isCompletingSession) return;
    // 直接结束并总结，不再弹二次确认
    setIsCompletingSession(true);
    setApiError("");
    try {
      const result = await completeSession(session.id, completionType);
      setSession(result.session);
      setCompletion(result.completion);
    } catch {
      setApiError("生成今日总结失败，请稍后再试。")
    } finally {
      setIsCompletingSession(false);
    }
  }

  if (lessonPhase === "learn" && practiceBrief) {
    const targetExpressions = practiceBrief.target_expressions || [];
    const taskSteps = practiceBrief.task_steps || [];
    const visibleExpressions = targetExpressions.slice(0, 6);

    return (
      <main className="practice-page">
        {apiError ? <p className="error-message" role="alert">{apiError}</p> : null}
        <section className="lesson-brief-shell lesson-brief-shell-compact" aria-label="课程简报">
          <header className="lesson-brief-header" aria-label="课程简报头部">
            <div>
              <p className="section-label">开口前先看一眼</p>
              <h1>{practiceBrief.title || day?.topic || scenario?.title}</h1>
            </div>
            <p>{practiceBrief.user_visible_goal || practiceBrief.conversation_objective || day?.objective}</p>
            <PrimaryButton onClick={() => setLessonPhase("practice")}>开始对话练习</PrimaryButton>
          </header>

          <div className="lesson-brief-grid">
            <section className="lesson-brief-card">
              <p className="section-label">场景设定</p>
              <h2>{practiceBrief.npc_role || "对话角色"}</h2>
              <p>{practiceBrief.scenario_setup || day?.scenario}</p>
            </section>

            {practiceBrief.lesson_focus || taskSteps.length > 0 ? (
              <section className="lesson-brief-card">
                <p className="section-label">练习方式</p>
                {practiceBrief.lesson_focus ? <p>{practiceBrief.lesson_focus}</p> : null}
                {taskSteps.length > 0 ? (
                  <ol className="lesson-watch-list">
                    {taskSteps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                ) : null}
              </section>
            ) : null}

            <section className="lesson-brief-card lesson-brief-card-accent">
              <p className="section-label">可直接套用的表达</p>
              {visibleExpressions.length > 0 ? (
                <ul className="lesson-expression-list">
                  {visibleExpressions.map((expression) => (
                    <ExpressionCard expression={expression} key={expressionLabel(expression)} />
                  ))}
                </ul>
              ) : (
                <p className="muted">围绕场景目标组织你的第一句话。</p>
              )}
            </section>
          </div>
        </section>
      </main>
    );
  }

  const hasUserTurn = turns.some((turn) => turn.speaker === "user");
  // 学习路线：当前场景在路线中的位置，用于完成后「继续下一张卡片」
  const pathIndex = learningPath && scenario ? learningPath.findIndex((item) => item.id === scenario.id) : -1;
  const nextPathItem =
    pathIndex >= 0 && pathIndex < (learningPath?.length ?? 0) - 1
      ? (learningPath?.[pathIndex + 1] ?? null)
      : null;
  const showCompletionSuggestion =
    !isFreeTalk &&
    completion?.status === "completion_suggested" &&
    completion.can_suggest_completion &&
    !dismissedCompletionSuggestion &&
    !isCompleted;

  return (
    <main className="practice-page">
      {apiError ? <p className="error-message" role="alert">{apiError}</p> : null}
      <section className="practice-workspace">
        <div className="practice-main">
          {onSelectScenario && !isScenarioMode ? (
            <ScenarioPicker
              profileId={profileId}
              activeScenarioId={scenario?.id ?? null}
              onSelect={onSelectScenario}
              faded={hasUserTurn}
            />
          ) : null}
          <section
            className={"topic-strip" + (topicImage ? " topic-strip-cover" : "")}
            aria-label={isScenarioMode ? "当前场景" : "今日场景"}
            style={topicImage ? { backgroundImage: `url("${topicImage}")` } : undefined}
          >
            <div>
              <p>{isScenarioMode ? "当前场景" : "今日场景"}</p>
              <h1>{scenario?.title ?? day?.topic}</h1>
              <p className="topic-strip-context">{scenario?.background ?? day?.scenario}</p>
            </div>
            <div className="topic-strip-actions">
              <button
                className={bilingualEnabled ? "bilingual-toggle bilingual-toggle-active" : "bilingual-toggle"}
                type="button"
                aria-pressed={bilingualEnabled}
                onClick={() => {
                  setBilingualEnabled((value) => {
                    const next = !value;
                    localStorage.setItem("speakmate-bilingual", next ? "on" : "off");
                    return next;
                  });
                }}
              >
                双语 {bilingualEnabled ? "开" : "关"}
              </button>
              <button
                className={ttsMuted ? "tts-toggle tts-toggle-muted" : "tts-toggle"}
                type="button"
                aria-pressed={!ttsMuted}
                aria-label={ttsMuted ? "语音已静音，点击开启自动朗读" : "AI 回复自动朗读中，点击静音"}
                onClick={() => {
                  setTtsMuted((value) => {
                    const next = !value;
                    localStorage.setItem("speakmate-tts-muted", next ? "on" : "off");
                    return next;
                  });
                }}
              >
                {ttsMuted ? "语音 关" : "语音 开"}
              </button>
              <button
                className={phoneMode ? "phone-mode-btn phone-mode-btn-active" : "phone-mode-btn"}
                type="button"
                aria-pressed={phoneMode}
                aria-label={phoneMode ? "挂断电话模式" : "开启电话模式"}
                onClick={togglePhoneMode}
              >
                {phoneMode ? "挂断" : "电话模式"}
              </button>
              {onFreeTalk ? (
                <SecondaryButton type="button" onClick={onFreeTalk}>
                  自由对话
                </SecondaryButton>
              ) : null}
              {practiceBrief ? (
                <SecondaryButton type="button" onClick={() => setLessonPhase("learn")}>
                  查看场景提示
                </SecondaryButton>
              ) : null}
              {hasUserTurn && !isCompleted ? (
                <SecondaryButton type="button" onClick={() => handleCompleteSession("manual")} disabled={isCompletingSession}>
                  {isCompletingSession ? "生成总结中…" : isScenarioMode ? "结束练习" : "结束今日练习"}
                </SecondaryButton>
              ) : null}
              {session ? (
                <SecondaryButton type="button" onClick={handleClearSessionHistory} disabled={isClearingHistory}>
                  {isClearingHistory ? "删除中…" : "删除本次会话"}
                </SecondaryButton>
              ) : null}
              <span className={session || isCompleted ? "session-dot session-dot-active" : "session-dot"} aria-label="会话状态">
                {isCompleted ? (isScenarioMode ? "已结束" : "今日已完成") : session ? "正在进行" : "准备中"}
              </span>
            </div>
          </section>

          {phoneMode ? (
            <div className="phone-mode-bar" role="status" aria-label="电话模式状态">
              <span className="phone-mode-pulse" aria-hidden="true" />
              <span>电话模式 · 正在聆听，说完请稍作停顿</span>
              <button type="button" className="phone-mode-hangup" onClick={() => setPhoneMode(false)}>
                挂断
              </button>
            </div>
          ) : null}

          <section className="chat-card">
            <div className="chat-thread" aria-label="对话练习">
              <div className="chat-scroll" ref={chatScrollRef}>
                {turns.map((turn) => {
                  const isUser = turn.speaker === "user";
                  const nextTurn = turns.find((item) => item.turn_index === turn.turn_index + 1);
                  const canDeletePair = isUser && nextTurn?.speaker === "assistant";
                  const translation = bilingualEnabled ? translations[turn.id] : undefined;
                  const isVoice = isUser && voiceTurnIds.has(turn.id);
                  const voiceDuration = voiceMeta.get(turn.id)?.durationMs ?? 0;
                  const voiceFailed = voiceFailedIds.has(turn.id);
                  // 该消息对应的纠错（仅 correction 视为「存在错误」）
                  const turnFeedbackItems = isUser
                    ? feedbackTimeline.filter(
                        (tl): tl is Extract<FeedbackTimelineItem, { kind: "feedback" }> =>
                          tl.kind === "feedback" && tl.item.turn_id === turn.id && tl.item.feedback_type === "correction",
                      )
                    : [];
                  return (
                    <article
                      className={(isUser ? "message-row message-row-user" : "message-row") + (highlightedTurnId === turn.id ? " message-row-highlight" : "")}
                      key={turn.id}
                      data-turn-id={turn.id}
                    >
                      {!isUser ? (
                        <div className="message-avatar message-avatar-assistant" aria-hidden="true">
                          {ASSISTANT_AVATAR}
                        </div>
                      ) : null}
                      {isUser && canDeletePair ? (
                        <div className="message-actions message-actions-user" role="group" aria-label="消息操作">
                          <button
                            className="message-action-button message-delete-button"
                            type="button"
                            aria-label="删除这一轮"
                            disabled={deletingTurnId === turn.id}
                            onClick={() => handleDeleteTurnPair(turn.id)}
                          >
                            删
                          </button>
                        </div>
                      ) : null}
                      <div className={(isUser ? "message-bubble message-bubble-user" : "message-bubble message-bubble-assistant") + (turn.id === ttsSpeakingTurnId ? " message-bubble-speaking" : "")}>
                        {isVoice ? (
                          <span
                            className="voice-bubble"
                            role="button"
                            tabIndex={0}
                            aria-label="点击播放语音"
                            onClick={() => void playVoiceTurn(turn.id)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                void playVoiceTurn(turn.id);
                              }
                            }}
                          >
                            <span className="voice-bubble-bars" aria-hidden="true">
                              <i /><i /><i /><i />
                            </span>
                            <span className="voice-bubble-duration">{Math.round(voiceDuration / 1000)}″</span>
                            {voiceFailed ? <span className="voice-bubble-failed">未识别</span> : null}
                          </span>
                        ) : (
                          <>
                            <p>{turn.text}</p>
                            {turn.id === ttsSpeakingTurnId ? (
                              <span className="speaking-wave" aria-hidden="true">
                                <i /><i /><i /><i />
                              </span>
                            ) : null}
                          </>
                        )}
                        {isVoice && !voiceFailed && voiceTexts.get(turn.id) ? (
                          <p className="voice-bubble-text">{voiceTexts.get(turn.id)}</p>
                        ) : null}
                        {translation ? <p className={"message-translation" + (isUser ? " message-translation-user" : "")}>{translation}</p> : null}
                        {isUser && turnFeedbackItems.length > 0 ? (
                          <button
                            type="button"
                            className={"feedback-alert" + (openFeedbackTurnId === turn.id ? " feedback-alert-active" : "")}
                            aria-label={openFeedbackTurnId === turn.id ? "收起实时纠错" : "查看这条消息的实时纠错"}
                            aria-expanded={openFeedbackTurnId === turn.id}
                            onClick={() => setOpenFeedbackTurnId(openFeedbackTurnId === turn.id ? null : turn.id)}
                          >
                            !
                          </button>
                        ) : null}
                      </div>
                      {!isUser ? (
                        <div className="message-actions message-actions-assistant" role="group" aria-label="消息操作">
                          <button
                            className="message-action-button message-replay-button"
                            type="button"
                            aria-label="播放教练语音"
                            onClick={() => handleReplay(turn.text, turn.id)}
                          >
                            播
                          </button>
                        </div>
                      ) : null}
                      {isUser ? (
                        <div className="message-avatar message-avatar-user" aria-hidden="true">
                          {USER_AVATAR}
                        </div>
                      ) : null}
                      {isUser && openFeedbackTurnId === turn.id && turnFeedbackItems.length > 0 ? (
                        <div className="message-feedback-pop" role="region" aria-label="实时纠错">
                          <div className="message-feedback-pop-head">
                            <span>实时纠错</span>
                            <button type="button" onClick={() => setOpenFeedbackTurnId(null)}>
                              收起
                            </button>
                          </div>
                          {turnFeedbackItems.map((tl) => (
                            <FeedbackCard item={tl.item} key={tl.id} />
                          ))}
                        </div>
                      ) : null}
                    </article>
                  );
                })}
                {streamingReply !== null && (
                  <article className="message-row" key="streaming-turn">
                    <div className="message-avatar message-avatar-assistant" aria-hidden="true">{ASSISTANT_AVATAR}</div>
                    <div className="message-bubble message-bubble-assistant">
                      <p>{streamingReply}<span className="typing-cursor">▋</span></p>
                    </div>
                  </article>
                )}
                {completion?.status === "completed" && completion.completed_summary ? (
                  <section className="feedback-card feedback-card-guidance completion-summary-card" aria-label="今日总结">
                    <p className="feedback-card-label">练习已完成，但仍可继续对话</p>
                    <p>{completion.completed_summary.summary_zh}</p>
                    {completion.completed_summary.score !== undefined ? (
                      <p className="completion-score">
                        本次练习得分：<strong>{completion.completed_summary.score} / 100</strong>
                        {completion.completed_summary.score_detail_zh ? (
                          <span className="completion-score-detail">{completion.completed_summary.score_detail_zh}</span>
                        ) : null}
                      </p>
                    ) : null}
                    <p className="feedback-reason"><span>做得好的点：</span>{completion.completed_summary.strength_zh}</p>
                    <p className="feedback-reason"><span>下次重点：</span>{completion.completed_summary.next_focus_zh}</p>
                    {completion.completed_summary.reusable_sentences.length > 0 ? (
                      <p className="feedback-example">{completion.completed_summary.reusable_sentences[0]}</p>
                    ) : null}
                    {nextPathItem || onFreeTalk ? (
                      <div className="topic-strip-actions continuation-actions">
                        {nextPathItem ? (
                          <PrimaryButton type="button" onClick={() => onSelectScenario?.(nextPathItem)}>
                            继续下一张卡片
                          </PrimaryButton>
                        ) : null}
                        {onFreeTalk ? (
                          <SecondaryButton type="button" onClick={onFreeTalk}>
                            自由对话
                          </SecondaryButton>
                        ) : null}
                      </div>
                    ) : null}
                  </section>
                ) : null}
              </div>
            </div>

            <div className="chat-composer" aria-label="对话输入区">
              {showCompletionSuggestion ? (
                <section className="feedback-card feedback-card-guidance" aria-label="结束建议">
                  <p className="feedback-card-label">今天可以收束了</p>
                  <p>{completion.suggestion_reason_zh || "今天的核心目标已经基本练到了。"}</p>
                  <div className="topic-strip-actions">
                    <PrimaryButton type="button" onClick={() => handleCompleteSession("agent_suggested")}>
                      结束并总结
                    </PrimaryButton>
                    <SecondaryButton type="button" onClick={() => setDismissedCompletionSuggestion(true)}>
                      继续练一会儿
                    </SecondaryButton>
                  </div>
                </section>
              ) : null}
              <textarea
                aria-label="输入你的回答"
                placeholder="可以录音转文字，也可以直接输入英文。确认后点击发送。"
                value={typedText}
                onChange={(event) => setTypedText(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault();
                    if (!isSubmitting) {
                      submitTurn(typedText);
                    }
                  }
                }}
              />
              <div className="composer-toolbar">
                <VoiceRecorder
                  disabled={isSubmitting}
                  autoMode={phoneMode}
                  autoRecordSignal={autoRecordSignal}
                  onText={(text) => {
                    if (phoneModeRef.current) {
                      // 电话模式：识别即自动发送，无需手动点发送
                      void submitTurn(text);
                    } else {
                      setTypedText((current) => current.trim() ? current.trim() + " " + text : text);
                    }
                  }}
                  onVoiceMessage={(blob, durationMs) => void handleVoiceMessage(blob, durationMs)}
                />
                <PrimaryButton disabled={isSubmitting || !typedText.trim()} onClick={() => submitTurn(typedText)}>
                  {isSubmitting ? "发送中…" : "发送"}
                </PrimaryButton>
              </div>
            </div>
          </section>
        </div>

        <aside className="feedback-sidebar" aria-label="实时纠错" onScroll={handleFeedbackScroll}>
          <p className="section-label">实时纠错</p>
          <div className="feedback-list">
            {feedbackTimeline.length > 0 ? (
              feedbackTimeline.map((item) => (
                item.kind === "feedback" ? (
                  <FeedbackCard item={item.item} key={item.id} onLocate={locateTurn} />
                ) : (
                  <div
                    className="language-support-dock"
                    key={item.id}
                  >
                    <LanguageSupportCard result={item.result} />
                  </div>
                )
              ))
            ) : (
              <p className="feedback-item">发送第一句后，这里会显示纠错和表达建议。</p>
            )}
            <div ref={feedbackEndRef} />
          </div>
        </aside>
      </section>
    </main>
  );
}
