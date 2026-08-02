import { useEffect, useRef, useState } from "react";
import { clearSessionHistory, completeSession, deleteTurnPair, playAudioFromUrl, requestLanguageSupport, sendUserTurnStream, startScenarioSession, startSession, playTTS, stopActiveAudio, transcribeAudio, translateText } from "../api";
import type { ConversationTurn, InlineFeedback, LanguageSupportMode, LanguageSupportResult, PlanDay, PracticeBrief, PracticeSession, Scenario, SessionCompletion, TargetExpression, TodayStrategy } from "../types";
import { PrimaryButton, SecondaryButton } from "./ui";
import { VoiceRecorder } from "./VoiceRecorder";
import { ScenarioPicker } from "./ScenarioPicker";

type Props = {
  day?: PlanDay | null;
  scenario?: Scenario | null;
  todayStrategy?: TodayStrategy | null;
  profileId?: number;
  onSelectScenario?: (scenario: Scenario) => void;
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

function FeedbackCard({ item }: { item: InlineFeedback }) {
  const isGuidance = item.feedback_type === "guidance";
  const isLanguageHelp = item.feedback_type === "language_help";
  const correction = item.feedback_type === "correction" ? getCorrectionParts(item) : null;

  if (correction) {
    return (
      <article className="feedback-card feedback-card-correction">
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
      <article className="feedback-card feedback-card-guidance">
        <p className="feedback-card-label">下一步可以这样说</p>
        <p>{item.reason_zh || item.feedback_text}</p>
        {item.example_sentence ? <p className="feedback-example">{item.example_sentence}</p> : null}
      </article>
    );
  }

  if (isLanguageHelp) {
    return (
      <article className="feedback-card feedback-card-language">
        <p className="feedback-card-label">词义解答</p>
        {item.original_fragment ? <strong className="language-term">{item.original_fragment}</strong> : null}
        <p>{item.reason_zh || item.feedback_text}</p>
        {item.example_sentence ? <p className="feedback-example">{item.example_sentence}</p> : null}
      </article>
    );
  }

  return <p className="feedback-item">{item.feedback_text}</p>;
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

export function PracticeRoom({ day, scenario, todayStrategy, profileId, onSelectScenario }: Props) {
  const [session, setSession] = useState<PracticeSession | null>(null);
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [feedbackTimeline, setFeedbackTimeline] = useState<FeedbackTimelineItem[]>([]);
  const [practiceBrief, setPracticeBrief] = useState<PracticeBrief | null>(null);
  const [completion, setCompletion] = useState<SessionCompletion | null>(null);
  const [lessonPhase, setLessonPhase] = useState<LessonPhase>("practice");
  const [hints, setHints] = useState<string[]>([]);
  const [typedText, setTypedText] = useState("");
  const [apiError, setApiError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [streamingReply, setStreamingReply] = useState<string | null>(null);
  const [deletingTurnId, setDeletingTurnId] = useState<number | null>(null);
  const [selectedText, setSelectedText] = useState("");
  const [languageSupport, setLanguageSupport] = useState<LanguageSupportResult | null>(null);
  const [latestLanguageSupportItemId, setLatestLanguageSupportItemId] = useState("");
  const [isLanguageSupportLoading, setIsLanguageSupportLoading] = useState(false);
  const [isCompletingSession, setIsCompletingSession] = useState(false);
  const [isClearingHistory, setIsClearingHistory] = useState(false);
  const [dismissedCompletionSuggestion, setDismissedCompletionSuggestion] = useState(false);
  const [bilingualEnabled, setBilingualEnabled] = useState(() => localStorage.getItem("speakmate-bilingual") !== "off");
  const [translations, setTranslations] = useState<Record<number, string>>({});
  const [voiceTurnIds, setVoiceTurnIds] = useState<Set<number>>(new Set());
  const [voiceMeta, setVoiceMeta] = useState<Map<number, { durationMs: number }>>(new Map());
  const [voiceFailedIds, setVoiceFailedIds] = useState<Set<number>>(new Set());
  const [voiceAudioUrls, setVoiceAudioUrls] = useState<Map<number, string>>(new Map());
  const [voiceTexts, setVoiceTexts] = useState<Map<number, string>>(new Map());
  const isSubmittingRef = useRef(false);
  const languageSupportIdRef = useRef(0);

  const feedbackEndRef = useRef<HTMLDivElement>(null);
  const languageSupportRef = useRef<HTMLDivElement>(null);
  const isFeedbackAtBottomRef = useRef(true);

  const isScenarioMode = Boolean(scenario);

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

  useEffect(() => {
    if (languageSupport && languageSupportRef.current) {
      languageSupportRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [languageSupport, latestLanguageSupportItemId]);

  // TTS 播放：合并相邻句子，减少句间停顿
  const audioBufferRef = useRef("");
  const audioFlushTimerRef = useRef<number | null>(null);
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingAudioRef = useRef(false);
  const processedTextLenRef = useRef(0);

  const playNextAudio = async () => {
    if (isPlayingAudioRef.current || audioQueueRef.current.length === 0) return;
    isPlayingAudioRef.current = true;
    const textToPlay = audioQueueRef.current.shift();
    if (textToPlay) {
      try {
        await playTTS(textToPlay);
      } catch (e) {
        console.warn("Chunk TTS failed", e);
      }
    }
    isPlayingAudioRef.current = false;
    void playNextAudio();
  };

  const queueAudioText = (text: string) => {
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
        setLanguageSupport(null);
        setLatestLanguageSupportItemId("");
        setPracticeBrief(result.practice_brief || null);
        setCompletion(result.completion || null);
        const hasUserTurns = result.turns.some((turn) => turn.speaker === "user");
        setLessonPhase(result.practice_brief && !hasUserTurns ? "learn" : "practice");
        setHints([]);
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

  // 双语展示：按需为 assistant 消息生成中文翻译（缓存）
  useEffect(() => {
    if (!bilingualEnabled) return;
    const pending = turns.filter(
      (turn) => turn.speaker === "assistant" && !(turn.id in translations)
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
    setHints([]); // clear old hints

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
      setTurns((current) => {
        const withoutTemp = current.filter(t => t.id !== tempUserTurn.id);

        // If meta was successfully received, use the backend's saved turns
        if (result.user_turn && result.assistant_turn) {
          return [...withoutTemp, result.user_turn, result.assistant_turn];
        }

        // Resilience: if meta failed (e.g. backend feedback generation timeout),
        // we synthesize a temporary assistant turn so the text isn't lost.
        const fallbackAssistantTurn: ConversationTurn = {
          id: Date.now() + 1,
          session_id: session.id,
          turn_index: tempUserTurn.turn_index + 1,
          speaker: "assistant",
          text: fullStreamedText.trim()
        };
        return [...withoutTemp, tempUserTurn, fallbackAssistantTurn];
      });

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
      setHints(result.hints || []);
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

  async function handleReplay(text: string) {
    queueAudioText(text);
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
    const shouldComplete = window.confirm(isScenarioMode ? "确定结束这次场景练习吗？系统会生成本次总结。" : "确定结束今天的练习吗？系统会生成今日总结，并把这一天标记为已完成。");
    if (!shouldComplete) return;

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

  function handleConversationSelection() {
    const selection = window.getSelection();
    const text = selection?.toString().trim() || "";
    if (text.length < 2) return;
    setSelectedText(text.slice(0, 240));
  }

  async function handleLanguageSupport(mode: LanguageSupportMode = "explain") {
    if (!selectedText) return;
    setIsLanguageSupportLoading(true);
    setApiError("");
    try {
      const context = turns.map((turn) => `${turn.speaker}: ${turn.text}`).join("\n").slice(-1200);
      const result = await requestLanguageSupport({ mode, text: selectedText, context });
      const itemId = `language-${Date.now()}-${languageSupportIdRef.current}`;
      languageSupportIdRef.current += 1;
      setLanguageSupport(result);
      setLatestLanguageSupportItemId(itemId);
      setFeedbackTimeline(current => [...current, { kind: "language", id: itemId, result }]);
      setSelectedText("");
      window.getSelection()?.removeAllRanges();
    } catch {
      setApiError("获取中文解释失败，请稍后再试。")
    } finally {
      setIsLanguageSupportLoading(false);
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
  const isCompleted = completion?.status === "completed";
  const showCompletionSuggestion =
    completion?.status === "completion_suggested" &&
    completion.can_suggest_completion &&
    !dismissedCompletionSuggestion &&
    !isCompleted;

  return (
    <main className="practice-page">
      {apiError ? <p className="error-message" role="alert">{apiError}</p> : null}
      <section className="practice-workspace">
        <div className="practice-main">
          {onSelectScenario ? (
            <ScenarioPicker
              profileId={profileId}
              activeScenarioId={scenario?.id ?? null}
              onSelect={onSelectScenario}
              faded={hasUserTurn}
            />
          ) : null}
          <section className="topic-strip" aria-label="今日场景">
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

          <section className="chat-card">
            <div className="chat-thread" aria-label="对话练习" onMouseUp={handleConversationSelection}>
              <div className="chat-scroll">
                {turns.map((turn) => {
                  const isUser = turn.speaker === "user";
                  const nextTurn = turns.find((item) => item.turn_index === turn.turn_index + 1);
                  const canDeletePair = isUser && nextTurn?.speaker === "assistant";
                  const translation = bilingualEnabled ? translations[turn.id] : undefined;
                  const isVoice = isUser && voiceTurnIds.has(turn.id);
                  const voiceDuration = voiceMeta.get(turn.id)?.durationMs ?? 0;
                  const voiceFailed = voiceFailedIds.has(turn.id);
                  return (
                    <article className={isUser ? "message-row message-row-user" : "message-row"} key={turn.id}>
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
                      <div className={isUser ? "message-bubble message-bubble-user" : "message-bubble message-bubble-assistant"}>
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
                          <p>{turn.text}</p>
                        )}
                        {isVoice && !voiceFailed && voiceTexts.get(turn.id) ? (
                          <p className="voice-bubble-text">{voiceTexts.get(turn.id)}</p>
                        ) : null}
                        {!isUser && translation ? <p className="message-translation">{translation}</p> : null}
                      </div>
                      {!isUser ? (
                        <div className="message-actions message-actions-assistant" role="group" aria-label="消息操作">
                          <button
                            className="message-action-button message-replay-button"
                            type="button"
                            aria-label="播放教练语音"
                            onClick={() => handleReplay(turn.text)}
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
              </div>
              {selectedText ? (
                <div className="language-inline-popover" role="group" aria-label="选中文本操作">
                  <span>选中：{selectedText}</span>
                  <button
                    type="button"
                    onClick={() => handleLanguageSupport("explain")}
                    disabled={isLanguageSupportLoading}
                  >
                    {isLanguageSupportLoading ? "解释中..." : "解释中文"}
                  </button>
                </div>
              ) : null}
            </div>

            <div className="chat-composer" aria-label="对话输入区">
              {completion?.status === "completed" && completion.completed_summary ? (
                <section className="feedback-card feedback-card-guidance" aria-label="今日总结">
                  <p className="feedback-card-label">练习已完成，但仍可继续对话</p>
                  <p>{completion.completed_summary.summary_zh}</p>
                  <p className="feedback-reason"><span>做得好的点：</span>{completion.completed_summary.strength_zh}</p>
                  <p className="feedback-reason"><span>下次重点：</span>{completion.completed_summary.next_focus_zh}</p>
                  {completion.completed_summary.reusable_sentences.length > 0 ? (
                    <p className="feedback-example">{completion.completed_summary.reusable_sentences[0]}</p>
                  ) : null}
                </section>
              ) : null}
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
              {hints.length > 0 && (
                <div className="hints-container">
                  {hints.map((hint, idx) => (
                    <span key={idx} className="hint-pill">{hint}</span>
                  ))}
                </div>
              )}
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
              <VoiceRecorder
                disabled={isSubmitting}
                onText={(text) => {
                  setTypedText((current) => current.trim() ? current.trim() + " " + text : text);
                }}
                onVoiceMessage={(blob, durationMs) => void handleVoiceMessage(blob, durationMs)}
              />
              <PrimaryButton disabled={isSubmitting || !typedText.trim()} onClick={() => submitTurn(typedText)}>
                {isSubmitting ? "发送中…" : "发送"}
              </PrimaryButton>
            </div>
          </section>
        </div>

        <aside className="feedback-sidebar" aria-label="实时纠错" onScroll={handleFeedbackScroll}>
          <p className="section-label">实时纠错</p>
          <div className="feedback-list">
            {feedbackTimeline.length > 0 ? (
              feedbackTimeline.map((item) => (
                item.kind === "feedback" ? (
                  <FeedbackCard item={item.item} key={item.id} />
                ) : (
                  <div
                    className="language-support-dock"
                    key={item.id}
                    ref={item.id === latestLanguageSupportItemId ? languageSupportRef : undefined}
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
