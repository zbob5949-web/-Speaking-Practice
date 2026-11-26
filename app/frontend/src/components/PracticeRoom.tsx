import { Fragment, useEffect, useRef, useState } from "react";
import { getAccount, clearSessionHistory, completeSession, deleteTurnPair, getSelectedVoice, getSessionHistory, getSessionTurns, playAudioFromUrl, sendUserTurnStream, startScenarioSession, startSession, playTTS, stopActiveAudio, transcribeAudio, translateText } from "../api";
import type { ConversationTurn, ErrorReport, ErrorReportItem, InlineFeedback, LanguageSupportResult, PlanDay, PracticeBrief, PracticeSession, Scenario, SessionCompletion, SessionHistoryItem, TargetExpression, TodayStrategy } from "../types";
import { PrimaryButton, SecondaryButton } from "./ui";
import { VoiceRecorder } from "./VoiceRecorder";
import type { VoiceRecorderHandle } from "./VoiceRecorder";
import { VoiceWaveform } from "./VoiceWaveform";
import { ScenarioPicker } from "./ScenarioPicker";
import { useIsMobile } from "../useIsMobile";

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

/** 合并多轮错误报告：按错误类型+改写去重，累加频率 */
function mergeRoundReports(reports: ErrorReport[]): ErrorReport {
  const byKey = new Map<string, ErrorReportItem>();
  let total = 0;
  for (const report of reports) {
    total += report.total_errors;
    for (const err of report.errors) {
      const key = `${err.error_type || err.rule_id || "general"}::${(err.better_expression || err.original_fragment || "").toLowerCase()}`;
      const prev = byKey.get(key);
      if (prev) {
        prev.frequency = (prev.frequency || 1) + (err.frequency || 1);
      } else {
        byKey.set(key, { ...err, frequency: err.frequency || 1 });
      }
    }
  }
  const errors = [...byKey.values()].sort((a, b) => (b.frequency || 0) - (a.frequency || 0));
  return {
    total_errors: total,
    unique_errors: errors.length,
    errors,
    by_error_type: {},
    has_errors: errors.length > 0,
  };
}

/** 练习结束总结卡片内的错误小结：合并全程错误报告，简要展示 */
function SessionErrorSummary({ reports }: { reports: ErrorReport[] }) {
  const merged = mergeRoundReports(reports);
  if (!merged.has_errors) {
    return null;
  }
  const shown = merged.errors.slice(0, 5);
  const restCount = merged.errors.length - shown.length;
  return (
    <div className="session-error-summary" aria-label="练习错误小结">
      <p className="feedback-card-label">错误小结</p>
      <p className="round-report-stat">全程共 {merged.total_errors} 处错误 · {merged.unique_errors} 类</p>
      <ul className="round-report-list">
        {shown.map((err, index) => (
          <li className="round-report-item" key={index}>
            <div className="round-report-item-head">
              <strong>{err.error_type || err.rule_id || "一般问题"}</strong>
              {(err.frequency ?? 0) > 1 ? <span className="round-report-freq">×{err.frequency}</span> : null}
            </div>
            {err.original_fragment && err.better_expression ? (
              <div className="correction-swap">
                <div>
                  <span>你说的是</span>
                  <strong>{err.original_fragment}</strong>
                </div>
                <div aria-hidden="true" className="correction-arrow">→</div>
                <div>
                  <span>建议改成</span>
                  <strong>{err.better_expression}</strong>
                </div>
              </div>
            ) : err.reason_zh || err.feedback_text ? (
              <p className="feedback-reason"><span>说明：</span>{err.reason_zh || err.feedback_text}</p>
            ) : null}
          </li>
        ))}
      </ul>
      {restCount > 0 ? <p className="round-report-more">还有 {restCount} 类同类错误，已在对话中逐条指出</p> : null}
    </div>
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

/** 场景中文名：最近对话里不显示英文标题 */
const SCENARIO_ZH: Record<string, string> = {
  "airport-check-in": "机场值机",
  "hotel-check-in": "酒店入住",
  "restaurant-order": "餐厅点餐",
  "job-interview": "面试沟通",
  "doctor-visit": "就医问诊",
  "shopping-return": "购物退换",
  free_talk: "自由对话",
};

/** 纠错列表：桌面右侧栏与手机底部抽屉共用同一份渲染，避免两处维护。 */
function FeedbackList({
  items,
  onLocate,
}: {
  items: FeedbackTimelineItem[];
  onLocate?: (turnId: number) => void;
}) {
  if (items.length === 0) {
    return <p className="feedback-item">发送第一句后，这里会显示纠错和表达建议。</p>;
  }
  return (
    <>
      {items.map((item) =>
        item.kind === "feedback" ? (
          <FeedbackCard item={item.item} key={item.id} onLocate={onLocate} />
        ) : (
          <div className="language-support-dock" key={item.id}>
            <LanguageSupportCard result={item.result} />
          </div>
        ),
      )}
    </>
  );
}

export function PracticeRoom({ day, scenario, todayStrategy, profileId, learningPath, onSelectScenario, onFreeTalk }: Props) {
  const [session, setSession] = useState<PracticeSession | null>(null);
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [feedbackTimeline, setFeedbackTimeline] = useState<FeedbackTimelineItem[]>([]);
  // 每轮结束的总结板块数据：按轮次顺序追加该轮错误报告
  const [roundErrorReports, setRoundErrorReports] = useState<ErrorReport[]>([]);
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
  // 结束确认面板：null=关闭，"manual"=用户主动结束，"agent_suggested"=AI 建议结束
  const [completingChoice, setCompletingChoice] = useState<"manual" | "agent_suggested" | null>(null);
  // ---- 手机端对话界面（≤600px）：顶部栏 / 菜单抽屉 / 纠错抽屉 ----
  const isMobile = useIsMobile();
  const [menuOpen, setMenuOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [isStartingNew, setIsStartingNew] = useState(false);
  // 递增触发会话重新启动（「新建会话」）
  const [sessionEpoch, setSessionEpoch] = useState(0);
  // 最近对话（左上角入口）
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyItems, setHistoryItems] = useState<SessionHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  // 点击某一轮历史：回放该轮对话
  const [replayTitle, setReplayTitle] = useState("");
  const [replayTurns, setReplayTurns] = useState<ConversationTurn[] | null>(null);
  const [replayLoading, setReplayLoading] = useState(false);
  // 长按输入卡触发录音：VoiceRecorder 保持挂载但视觉隐藏，通过 ref 直接驱动
  const voiceWrapRef = useRef<HTMLDivElement | null>(null);
  const voiceRef = useRef<VoiceRecorderHandle | null>(null);
  const holdTimerRef = useRef<number | null>(null);
  const holdingRef = useRef(false);
  const holdStartYRef = useRef<number | null>(null);
  // 长按录音时的浮层提示
  const [recordingUi, setRecordingUi] = useState(false);
  // 录音相关错误提示（录音器在手机端是隐藏的，错误要在这里显示）
  const [voiceToast, setVoiceToast] = useState("");

  useEffect(() => {
    if (!voiceToast) return;
    const timer = window.setTimeout(() => setVoiceToast(""), 4000);
    return () => window.clearTimeout(timer);
  }, [voiceToast]);
  // 实时纠错悬浮窗位置（可拖动）
  const [feedbackPos, setFeedbackPos] = useState({ x: 12, y: 150 });
  const floatDragRef = useRef<{ dx: number; dy: number } | null>(null);
  // 提示页「可直接套用的表达」是否展开（默认收起，保持预览清爽）
  const [expressionsOpen, setExpressionsOpen] = useState(false);
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
  const [userAvatar, setUserAvatar] = useState(USER_AVATAR);
  useEffect(() => {
    let cancelled = false;
    getAccount().then(account => { if (!cancelled) setUserAvatar(account.avatars[account.avatar] ?? USER_AVATAR); }).catch(() => {});
    return () => { cancelled = true; };
  }, []);
  const typedFromVoiceRef = useRef(false);
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [translationChoices, setTranslationChoices] = useState<Record<number, boolean>>({});
  const [translations, setTranslations] = useState<Record<number, string>>({});
  const [translationLoading, setTranslationLoading] = useState<Record<number, boolean>>({});
  const [translationErrors, setTranslationErrors] = useState<Record<number, string>>({});
  const translationPending = useRef(new Set<number>());
  const translationGeneration = useRef(0);
  const restoredSession = useRef<number | null>(null);
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
    let cancelled = false;
    restoredSession.current = null;
    translationGeneration.current++;
    translationPending.current.clear();
    async function boot() {
      try {
        setApiError("");
        const result = scenario
          ? await startScenarioSession(scenario.id, profileId)
          : await startSession(day!.id);
        if (cancelled) return;
        let cached: { translations?: Record<number, string>; choices?: Record<number, boolean>; voiceTurns?: number[] } = {};
        try { cached = JSON.parse(sessionStorage.getItem(`speakmate-chat:${result.session.id}`) ?? "{}"); } catch { /* Use server data if storage is unavailable. */ }
        restoredSession.current = result.session.id;
        setSession(result.session);
        const voiceIds = new Set(cached.voiceTurns ?? []);
        setTurns(result.turns.map(turn => voiceIds.has(turn.id) ? { ...turn, input_mode: "voice" as const } : turn));
        const feedbackHistory = result.feedback_history || [];
        setFeedbackTimeline(feedbackTimelineItems(feedbackHistory));
        setRoundErrorReports([]);
        setPracticeBrief(result.practice_brief || null);
        setCompletion(result.completion || null);
        const hasUserTurns = result.turns.some((turn) => turn.speaker === "user");
        // 默认直接进入 AI 对话界面；「开口前提示」改为按需打开（顶部/输入卡的提示入口）
        setLessonPhase("practice");
        setTranslations(cached.translations ?? {});
        setTranslationChoices(cached.choices ?? {});
        setTranslationLoading({});
        setTranslationErrors({});
        typedFromVoiceRef.current = false;
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
    return () => { cancelled = true; translationGeneration.current++; };
  }, [scenario?.id, day?.id, sessionEpoch]);

  // Cache display state per session so returning through Home does not discard it.
  useEffect(() => {
    if (!session || restoredSession.current !== session.id) return;
    try {
      sessionStorage.setItem(`speakmate-chat:${session.id}`, JSON.stringify({
        translations, choices: translationChoices,
        voiceTurns: turns.filter(turn => turn.input_mode === "voice" || voiceTurnIds.has(turn.id)).map(turn => turn.id),
      }));
    } catch { /* A full or unavailable cache must not interrupt chat. */ }
  }, [session, turns, translations, translationChoices, voiceTurnIds]);

  async function requestTranslation(turn: ConversationTurn) {
    if (turn.speaker !== "assistant" || translations[turn.id] || translationPending.current.has(turn.id)) return;
    const generation = translationGeneration.current;
    translationPending.current.add(turn.id);
    setTranslationLoading(current => ({ ...current, [turn.id]: true }));
    setTranslationErrors(current => ({ ...current, [turn.id]: "" }));
    try {
      const result = await translateText(turn.text.slice(0, 2000));
      if (!result.translation_zh?.trim()) throw new Error("翻译暂不可用");
      if (generation === translationGeneration.current) setTranslations(current => ({ ...current, [turn.id]: result.translation_zh }));
    } catch {
      if (generation === translationGeneration.current) setTranslationErrors(current => ({ ...current, [turn.id]: "翻译失败，请重试" }));
    } finally {
      if (generation === translationGeneration.current) {
        translationPending.current.delete(turn.id);
        setTranslationLoading(current => ({ ...current, [turn.id]: false }));
      }
    }
  }

  useEffect(() => {
    for (const turn of turns) {
      if (turn.speaker === "assistant" && !translationErrors[turn.id] &&
          (translationChoices[turn.id] ?? (turn.input_mode !== "voice" && bilingualEnabled))) {
        void requestTranslation(turn);
      }
    }
  }, [turns, bilingualEnabled, translations, translationChoices, translationErrors]);

  function toggleTranslation(turn: ConversationTurn, shown: boolean) {
    if (translationErrors[turn.id]) {
      setTranslationChoices(current => ({ ...current, [turn.id]: true }));
      void requestTranslation(turn);
    } else {
      setTranslationChoices(current => ({ ...current, [turn.id]: !shown }));
      if (!shown) void requestTranslation(turn);
    }
  }

  async function submitTurn(text: string, voiceTempId?: number) {
    if (!session || !text.trim() || isSubmittingRef.current) return;

    const wasVoice = Boolean(voiceTempId) || typedFromVoiceRef.current;
    typedFromVoiceRef.current = false;
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
        },
        wasVoice ? "voice" : "text"
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
          input_mode: wasVoice ? "voice" : "text",
          text: fullStreamedText.trim()
        };
        return [...withoutTemp, tempUserTurn, fallbackAssistantTurn];
      });

      // 标记正在朗读的 AI 文字条：TTS 队列/缓冲仍有内容时显示波峰谷跳动样式
      const assistantId = result.assistant_turn ? result.assistant_turn.id : fallbackAssistantId;
      if (wasVoice) setTurns(current => current.map(turn => turn.id === assistantId || turn.id === (result.user_turn?.id ?? tempUserTurn.id) ? { ...turn, input_mode: "voice" } : turn));
      if ((isPlayingAudioRef.current || audioQueueRef.current.length > 0 || audioBufferRef.current) && !ttsMutedRef.current) {
        setTtsSpeakingTurnId(assistantId);
      }

      if (result.inline_feedback && result.inline_feedback.length > 0) {
        setFeedbackTimeline(current => [...current, ...feedbackTimelineItems(result.inline_feedback)]);
      }
      // 每轮结束：把该轮错误报告追加到总结板块
      if (result.round_error_report) {
        setRoundErrorReports(current => [...current, result.round_error_report as ErrorReport]);
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

    } catch (error) {
      // Only set error if the stream completely failed to start
      if (!fullStreamedText) {
        setApiError(error instanceof Error && error.message.includes("会话已失效") ? error.message : "发送失败，请稍后再试。")
      } else {
        // If we got some text but then it crashed, we still want to keep the text
        setTurns((current) => {
          const withoutTemp = current.filter(t => t.id !== tempUserTurn.id);
          const fallbackAssistantTurn: ConversationTurn = {
            id: Date.now() + 1,
            session_id: session.id,
            turn_index: tempUserTurn.turn_index + 1,
            speaker: "assistant",
            input_mode: wasVoice ? "voice" : "text",
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
    setTtsSpeakingTurnId(turnId);
    try {
      await playAudioFromUrl(url);
    } catch {
      setApiError("语音播放失败，请重试。");
    } finally {
      setTtsSpeakingTurnId(current => current === turnId ? null : current);
    }
  }

  async function replayVoice(text: string, turnId: number) {
    stopActiveAudio(); setTtsSpeakingTurnId(turnId);
    try { await playTTS(text, getSelectedVoice() ?? undefined); }
    catch { setApiError("语音播放失败，请重试。"); }
    finally { setTtsSpeakingTurnId(current => current === turnId ? null : current); }
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
      // 回合被删除，历史轮次报告与回合对应关系失效，重新清空（重新载入会话时恢复为空）
      setRoundErrorReports([]);
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
      setRoundErrorReports([]);
      setSession(null);
      setCompletion(null);
    } catch {
      setApiError("清空本次会话失败，请稍后再试。");
    } finally {
      setIsClearingHistory(false);
    }
  }
  /** 只负责真正执行结束（由确认面板触发），不再弹原生 confirm */
  async function performCompleteSession(completionType: "manual" | "agent_suggested" = "manual") {
    if (!session || isCompletingSession) return;
    setCompletingChoice(null);
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

  function toggleBilingual() {
    setBilingualEnabled((value) => {
      const next = !value;
      localStorage.setItem("speakmate-bilingual", next ? "on" : "off");
      return next;
    });
  }

  function toggleTts() {
    setTtsMuted((value) => {
      const next = !value;
      localStorage.setItem("speakmate-tts-muted", next ? "on" : "off");
      return next;
    });
  }

  /** 新建会话：清空当前会话记录后重新启动一次（手机端顶部胶囊的 ＋ 触发） */
  async function handleNewSession() {
    if (isStartingNew) return;
    if (!window.confirm("开始新的会话？当前对话与纠错记录会被清空。")) return;
    setIsStartingNew(true);
    try {
      if (session) await clearSessionHistory(session.id);
    } catch {
      // 清空失败也继续重启，保证按钮始终可用
    } finally {
      setIsStartingNew(false);
      setMenuOpen(false);
      setFeedbackOpen(false);
      setTypedText("");
      setSessionEpoch((value) => value + 1);
    }
  }

  /** 打开「最近对话」：直接复用后端 sessions 列表（每轮结束时的打分/总结就是一轮的基准） */
  async function openHistory() {
    setHistoryOpen(true);
    if (historyItems.length > 0 || isLoadingHistory) return;
    setIsLoadingHistory(true);
    try {
      const result = await getSessionHistory(profileId);
      setHistoryItems(result.sessions.slice(0, 8));
    } catch {
      setHistoryItems([]);
    } finally {
      setIsLoadingHistory(false);
    }
  }

  /** 一轮对话的中文一句话摘要：优先解析本轮结束时的 JSON 总结，其次退回结构化信息 */
  function historySummary(item: SessionHistoryItem): string {
    const raw = typeof item.summary === "string" ? item.summary.trim() : "";
    let parsed: Record<string, unknown> | null = null;
    if (raw.startsWith("{")) {
      try {
        parsed = JSON.parse(raw) as Record<string, unknown>;
      } catch {
        parsed = null;
      }
    }
    if (parsed) {
      for (const key of ["summary_zh", "score_detail_zh"]) {
        const value = parsed[key];
        if (typeof value === "string" && value.trim()) {
          const text = value.trim();
          return text.length > 40 ? `${text.slice(0, 40)}…` : text;
        }
      }
    } else if (raw && !raw.startsWith("{")) {
      return raw.length > 40 ? `${raw.slice(0, 40)}…` : raw;
    }
    const bits: string[] = [];
    if (item.turn_count) bits.push(`${item.turn_count} 轮`);
    if (item.difficulty) bits.push(item.difficulty);
    if (typeof item.score === "number") bits.push(`${item.score} 分`);
    return bits.length > 0 ? bits.join(" · ") : "已完成";
  }

  function scenarioZh(item: SessionHistoryItem): string {
    return SCENARIO_ZH[item.scenario_id ?? ""] ?? (item.topic || "练习");
  }

  /** 点击最近对话里的一轮：加载并回放那场对话 */
  async function openReplay(item: SessionHistoryItem) {
    setReplayTitle(scenarioZh(item));
    setReplayTurns(null);
    setReplayLoading(true);
    try {
      const result = await getSessionTurns(item.id);
      setReplayTurns(result.turns);
    } catch {
      setReplayTurns([]);
    } finally {
      setReplayLoading(false);
    }
  }

  // ---- 长按输入卡（含输入框本体）= 录音 ----
  function handleComposerPointerDown(event: React.PointerEvent<HTMLDivElement>) {
    if (!isMobile) return;
    const target = event.target as HTMLElement | null;
    // 只有按钮/加号/chips 不触发；输入框本身也属于「输入卡」，长按同样说话
    if (target?.closest("button, input, .m-chip")) return;
    holdStartYRef.current = event.clientY;
    holdingRef.current = false;
    if (holdTimerRef.current) window.clearTimeout(holdTimerRef.current);
    holdTimerRef.current = window.setTimeout(() => {
      holdTimerRef.current = null;
      holdingRef.current = true;
      // 收起软键盘，别让键盘占着屏幕
      (document.activeElement as HTMLElement | null)?.blur?.();
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
        setVoiceToast("当前环境无法录音：手机需要用 HTTPS 或 localhost 打开，并允许麦克风");
        return;
      }
      setRecordingUi(true);
      voiceRef.current?.startHold();
    }, 320);
  }

  function handleComposerPointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!holdingRef.current) return;
    // 上滑取消
    if (holdStartYRef.current !== null && holdStartYRef.current - event.clientY > 64) {
      endComposerHold(true);
    }
  }

  function endComposerHold(cancelled: boolean) {    if (holdTimerRef.current) {
      window.clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    if (!holdingRef.current) return;
    holdingRef.current = false;
    setRecordingUi(false);
    voiceRef.current?.endHold(cancelled);
  }

  // ---- 纠错悬浮窗拖动 ----
  function handleFloatDown(event: React.PointerEvent<HTMLElement>) {
    const panel = event.currentTarget.parentElement;
    if (!panel) return;
    const rect = panel.getBoundingClientRect();
    floatDragRef.current = { dx: event.clientX - rect.left, dy: event.clientY - rect.top };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function handleFloatMove(event: React.PointerEvent<HTMLElement>) {
    const drag = floatDragRef.current;
    if (!drag) return;
    const width = 264;
    const nextX = Math.min(Math.max(0, event.clientX - drag.dx), window.innerWidth - width - 6);
    const nextY = Math.min(Math.max(0, event.clientY - drag.dy), window.innerHeight - 140);
    setFeedbackPos({ x: nextX, y: nextY });
  }

  function handleFloatUp() {
    floatDragRef.current = null;
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
            {!isMobile ? (
              <PrimaryButton onClick={() => setLessonPhase("practice")}>开始对话练习</PrimaryButton>
            ) : null}
          </header>

          <div className="lesson-brief-grid">
            <section className="lesson-brief-card">
              <p className="section-label">场景设定</p>
              <h2>{practiceBrief.npc_role || "对话角色"}</h2>
              <p>{practiceBrief.scenario_setup || day?.scenario}</p>
            </section>

            <section className="lesson-brief-card lesson-brief-card-accent">
              <button
                type="button"
                className="lesson-collapse-head"
                aria-expanded={expressionsOpen}
                onClick={() => setExpressionsOpen((value) => !value)}
              >
                <span className="section-label">可直接套用的表达</span>
                <span className="lesson-collapse-toggle" aria-hidden="true">
                  {expressionsOpen ? "收起" : "展开"}
                </span>
              </button>
              {expressionsOpen ? (
                visibleExpressions.length > 0 ? (
                  <ul className="lesson-expression-list">
                    {visibleExpressions.map((expression) => (
                      <ExpressionCard expression={expression} key={expressionLabel(expression)} />
                    ))}
                  </ul>
                ) : (
                  <p className="muted">围绕场景目标组织你的第一句话。</p>
                )
              ) : (
                <p className="muted">{visibleExpressions.length} 条表达，点「展开」查看</p>
              )}
            </section>
          </div>
        </section>
        {isMobile ? (
          <div className="m-brief-bar">
            <PrimaryButton onClick={() => setLessonPhase("practice")}>开始对话练习</PrimaryButton>
          </div>
        ) : null}
      </main>
    );
  }

  const hasUserTurn = turns.some((turn) => turn.speaker === "user");
  // AI 第一句话下方给一行「可以直接说」的表达提示
  const firstAssistantTurnId = turns.find((turn) => turn.speaker === "assistant")?.id ?? -1;
  const hintExpressions = (practiceBrief?.target_expressions ?? [])
    .slice(0, 2)
    .map((item) => (typeof item === "string" ? item : item.expression));
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
      {isMobile ? (
        <header className="m-chat-top">
          <button
            type="button"
            className="m-circle-btn"
            aria-label="查看最近对话"
            title="最近对话"
            onClick={() => void openHistory()}
          >
            <span className="m-burger" aria-hidden="true"><i /><i /></span>
          </button>
          <div className="m-pill">
            <button
              type="button"
              className="m-pill-btn"
              aria-pressed={feedbackOpen}
              aria-label="实时纠错"
              title="实时纠错"
              onClick={() => setFeedbackOpen((value) => !value)}
            >
              <span aria-hidden="true">✎</span>
              {feedbackTimeline.length > 0 ? (
                <span className="m-pill-count">{feedbackTimeline.length}</span>
              ) : null}
            </button>
            <span className="m-pill-sep" aria-hidden="true" />
            <button
              type="button"
              className="m-pill-btn"
              aria-pressed={!ttsMuted}
              aria-label={ttsMuted ? "开启 AI 朗读" : "关闭 AI 朗读"}
              onClick={toggleTts}
            >
              <span aria-hidden="true">{ttsMuted ? "🔇" : "🔊"}</span>
            </button>
            <span className="m-pill-sep" aria-hidden="true" />
            <button
              type="button"
              className="m-pill-btn m-pill-btn-strong"
              aria-label="新建会话"
              title="新建会话"
              disabled={isStartingNew}
              onClick={() => void handleNewSession()}
            >
              <span aria-hidden="true">＋</span>
            </button>
          </div>
        </header>
      ) : null}
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
          <section className="topic-strip" aria-label={isScenarioMode ? "当前场景" : "今日场景"}>
            <div>
              <p>{isScenarioMode ? "当前场景" : "今日场景"}</p>
              <h1>{scenario?.title ?? day?.topic}</h1>
              <p className="topic-strip-context">{scenario?.background ?? day?.scenario}</p>
            </div>
            <div className="topic-strip-actions">
              {scenario?.id === "free_talk" ? <button type="button" className="bilingual-toggle" aria-expanded={knowledgeOpen} onClick={() => setKnowledgeOpen(value => !value)}>知识库</button> : null}
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
                <SecondaryButton type="button" onClick={() => setCompletingChoice("manual")} disabled={isCompletingSession}>
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

          {knowledgeOpen && scenario?.id === "free_talk" ? <aside className="knowledge-notice" role="status">知识库文件导入即将开放。<button type="button" className="voice-translation-toggle" onClick={() => setKnowledgeOpen(false)}>关闭</button></aside> : null}
          <section className="chat-card">
            <div className="chat-thread" aria-label="对话练习">
              <div className="chat-scroll" ref={chatScrollRef}>
                {turns.map((turn) => {
                  const isUser = turn.speaker === "user";
                  const nextTurn = turns.find((item) => item.turn_index === turn.turn_index + 1);
                  const canDeletePair = isUser && nextTurn?.speaker === "assistant";
                  const isVoice = turn.input_mode === "voice" || (isUser && voiceTurnIds.has(turn.id));
                  const showTranslation = !isUser && (translationChoices[turn.id] ?? (!isVoice && bilingualEnabled));
                  const translation = showTranslation ? translations[turn.id] : undefined;
                  const voiceDuration = voiceMeta.get(turn.id)?.durationMs ?? Math.max(1000, turn.text.split(/\s+/).length * 400);
                  const voiceFailed = voiceFailedIds.has(turn.id);
                  // 该消息对应的纠错（仅 correction 视为「存在错误」）
                  const turnFeedbackItems = isUser
                    ? feedbackTimeline.filter(
                        (tl): tl is Extract<FeedbackTimelineItem, { kind: "feedback" }> =>
                          tl.kind === "feedback" && tl.item.turn_id === turn.id && tl.item.feedback_type === "correction",
                      )
                    : [];
                  return (
                    <Fragment key={turn.id}>
                      <article
                        className={(isUser ? "message-row message-row-user" : "message-row") + (highlightedTurnId === turn.id ? " message-row-highlight" : "")}
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
                            onClick={() => void (isUser && voiceAudioUrls.has(turn.id) ? playVoiceTurn(turn.id) : replayVoice(turn.text, turn.id))}
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                void (isUser && voiceAudioUrls.has(turn.id) ? playVoiceTurn(turn.id) : replayVoice(turn.text, turn.id));
                              }
                            }}
                          >
                            <VoiceWaveform active={turn.id === ttsSpeakingTurnId} />
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
                        {isVoice && !voiceFailed ? (
                          <>
                            <p className="voice-bubble-text">{voiceTexts.get(turn.id) ?? turn.text}</p>
                            {!isUser ? <button type="button" className="voice-translation-toggle" aria-pressed={showTranslation} disabled={translationLoading[turn.id]} onClick={() => toggleTranslation(turn, showTranslation)}>{translationLoading[turn.id] ? "翻译中…" : translationErrors[turn.id] ? "重试翻译" : showTranslation ? "收起中文" : "翻译中文"}</button> : null}
                          </>
                        ) : null}
                        {!isUser && translationErrors[turn.id] ? <p className="translation-error" role="status">{translationErrors[turn.id]}</p> : null}
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
                          {userAvatar}
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
                      {!isUser && turn.id === firstAssistantTurnId && hintExpressions.length > 0 ? (
                        <p className="chat-hint-line">
                          <span className="chat-hint-label">可以直接说</span>
                          {hintExpressions.map((text) => (
                            <em className="chat-hint-chip" key={text}>{text}</em>
                          ))}
                        </p>
                      ) : null}
                    </Fragment>
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
                    {/* 全程错误小结：合并每一轮的错误报告，简要呈现在结束总结中 */}
                    {roundErrorReports.length > 0 ? <SessionErrorSummary reports={roundErrorReports} /> : null}
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

            <div
              className={isMobile ? "chat-composer chat-composer-mobile" : "chat-composer"}
              aria-label="对话输入区"
              onPointerDown={isMobile ? handleComposerPointerDown : undefined}
              onPointerMove={isMobile ? handleComposerPointerMove : undefined}
              onPointerUp={isMobile ? () => endComposerHold(false) : undefined}
              onPointerCancel={isMobile ? () => endComposerHold(true) : undefined}
              onPointerLeave={isMobile ? () => endComposerHold(true) : undefined}
              onContextMenu={isMobile ? (event) => event.preventDefault() : undefined}
            >
              {showCompletionSuggestion ? (
                <section className="feedback-card feedback-card-guidance" aria-label="结束建议">
                  <p className="feedback-card-label">今天可以收束了</p>
                  <p>{completion.suggestion_reason_zh || "今天的核心目标已经基本练到了。"}</p>
                  <div className="topic-strip-actions">
                    <PrimaryButton type="button" onClick={() => setCompletingChoice("agent_suggested")}>
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
                placeholder={isMobile ? "说一句英文，或长按这里说话" : "可以录音转文字，也可以直接输入英文。确认后点击发送。"}
                {...({ enterKeyHint: "send", autoCapitalize: "off", autoCorrect: "off" } as Record<string, string>)}
                value={typedText}
                onChange={(event) => { typedFromVoiceRef.current = false; setTypedText(event.target.value); }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault();
                    if (!isSubmitting) {
                      submitTurn(typedText);
                    }
                  }
                }}
              />
              {isMobile ? (
                <div className="m-composer-actions">
                  <div className="m-chips">
                    {scenario?.id === "free_talk" ? <button type="button" className="m-chip" aria-expanded={knowledgeOpen} onClick={() => setKnowledgeOpen(value => !value)}>知识库</button> : null}
                    <button
                      type="button"
                      className={bilingualEnabled ? "m-chip m-chip-on" : "m-chip"}
                      aria-pressed={bilingualEnabled}
                      onClick={toggleBilingual}
                    >
                      <span className="m-chip-icon" aria-hidden="true">🌐</span>
                      <span>双语</span>
                    </button>
                    {practiceBrief ? (
                      <button
                        type="button"
                        className="m-chip"
                        onClick={() => setLessonPhase("learn")}
                      >
                        <span className="m-chip-icon" aria-hidden="true">💡</span>
                        <span>提示</span>
                      </button>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    className="m-plus-btn"
                    aria-label="更多操作"
                    title="更多操作"
                    onClick={() => setMenuOpen(true)}
                  >
                    <span aria-hidden="true">＋</span>
                  </button>
                  <div className="m-voice-hidden" ref={voiceWrapRef}>
                    <VoiceRecorder
                      ref={voiceRef}
                      disabled={isSubmitting}
                      onError={(message) => {
                        setRecordingUi(false);
                        setVoiceToast(message);
                      }}
                      autoMode={phoneMode}
                      autoRecordSignal={autoRecordSignal}
                      onText={(text) => {
                        typedFromVoiceRef.current = true;
                        if (phoneModeRef.current) {
                          // 电话模式：识别即自动发送，无需手动点发送
                          void submitTurn(text);
                        } else {
                          setTypedText((current) => current.trim() ? current.trim() + " " + text : text);
                        }
                      }}
                      onVoiceMessage={(blob, durationMs) => void handleVoiceMessage(blob, durationMs)}
                    />
                  </div>
                </div>
              ) : (
                <div className="composer-toolbar">
                  <VoiceRecorder
                    disabled={isSubmitting}
                    autoMode={phoneMode}
                    autoRecordSignal={autoRecordSignal}
                    onText={(text) => {
                      typedFromVoiceRef.current = true;
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
              )}
            </div>
          </section>
        </div>

        <aside className="feedback-sidebar" aria-label="实时纠错" onScroll={handleFeedbackScroll}>
          <p className="section-label">实时纠错</p>
          <div className="feedback-list">
            <FeedbackList items={feedbackTimeline} onLocate={locateTurn} />
            <div ref={feedbackEndRef} />
          </div>
        </aside>
      </section>

      {isMobile && feedbackOpen ? (
        <section
          className="m-float"
          role="dialog"
          aria-label="实时纠错"
          style={{ left: `${feedbackPos.x}px`, top: `${feedbackPos.y}px` }}
        >
          <header
            className="m-float-head"
            onPointerDown={handleFloatDown}
            onPointerMove={handleFloatMove}
            onPointerUp={handleFloatUp}
            onPointerCancel={handleFloatUp}
          >
            <span className="m-float-grip" aria-hidden="true" />
            <strong>实时纠错</strong>
            <button
              type="button"
              className="m-float-close"
              aria-label="关闭"
              onPointerDown={(event) => event.stopPropagation()}
              onClick={() => setFeedbackOpen(false)}
            >
              ✕
            </button>
          </header>
          <div className="m-float-body">
            <FeedbackList items={feedbackTimeline} onLocate={locateTurn} />
          </div>
        </section>
      ) : null}

      {isMobile && voiceToast ? (
        <div className="m-voice-toast" role="alert" onClick={() => setVoiceToast("")}>
          {voiceToast}
        </div>
      ) : null}

      {isMobile && recordingUi ? (
        <div className="m-rec-overlay" role="status" aria-live="polite">
          <span className="m-rec-dot" aria-hidden="true" />
          <span className="m-rec-text">正在聆听</span>
          <span className="m-rec-hint">松开发送 · 上滑取消</span>
        </div>
      ) : null}

      {isMobile && historyOpen ? (
        <div className="m-sheet-backdrop" onClick={() => setHistoryOpen(false)}>
          <section
            className="m-sheet"
            role="dialog"
            aria-label="最近对话"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="m-sheet-head">
              <strong>{replayTurns || replayLoading ? `${replayTitle} · 回放` : "最近对话"}</strong>
              <button
                type="button"
                className="m-sheet-close"
                onClick={() => {
                  if (replayTurns || replayLoading) {
                    setReplayTurns(null);
                    setReplayLoading(false);
                    return;
                  }
                  setHistoryOpen(false);
                }}
              >
                {replayTurns || replayLoading ? "返回" : "关闭"}
              </button>
            </header>
            <div className="m-sheet-body">
              {replayLoading ? <p className="m-sheet-empty">加载中…</p> : null}
              {replayTurns ? (
                replayTurns.length === 0 ? (
                  <p className="m-sheet-empty">这一轮没有可回放的内容。</p>
                ) : (
                  <div className="m-replay">
                    {replayTurns.map((turn) => (
                      <p
                        key={turn.id}
                        className={turn.speaker === "user" ? "m-replay-line m-replay-line-user" : "m-replay-line"}
                      >
                        <span className="m-replay-who">{turn.speaker === "user" ? "我" : "AI"}</span>
                        {turn.text}
                      </p>
                    ))}
                  </div>
                )
              ) : null}
              {!replayTurns && !replayLoading ? (
                <>
                  {isLoadingHistory ? <p className="m-sheet-empty">加载中…</p> : null}
                  {!isLoadingHistory && historyItems.length === 0 ? (
                    <p className="m-sheet-empty">还没有练过的对话，先说一句试试。</p>
                  ) : null}
                  {historyItems.map((item) => (
                    <button
                      type="button"
                      className="m-history-item m-history-item-btn"
                      key={item.id}
                      onClick={() => void openReplay(item)}
                    >
                      <span className="m-history-head">
                        <strong>{scenarioZh(item)}</strong>
                        {typeof item.score === "number" ? (
                          <span className="m-history-score">{item.score} 分</span>
                        ) : null}
                      </span>
                      <span className="m-history-summary">{historySummary(item)}</span>
                      <span className="m-history-meta">
                        {(item.ended_at || item.started_at || "").slice(0, 16).replace("T", " ")}
                      </span>
                    </button>
                  ))}
                </>
              ) : null}
            </div>
          </section>
        </div>
      ) : null}

      {isMobile && menuOpen ? (
        <div className="m-sheet-backdrop" onClick={() => setMenuOpen(false)}>
          <section
            className="m-sheet"
            role="dialog"
            aria-label="菜单"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="m-sheet-head">
              <strong>菜单</strong>
              <button type="button" className="m-sheet-close" onClick={() => setMenuOpen(false)}>
                关闭
              </button>
            </header>
            <div className="m-sheet-body">
              <button
                type="button"
                className="m-sheet-item"
                onClick={() => {
                  setMenuOpen(false);
                  togglePhoneMode();
                }}
              >
                {phoneMode ? "退出电话模式" : "进入电话模式"}
              </button>
              {practiceBrief ? (
                <button
                  type="button"
                  className="m-sheet-item"
                  onClick={() => {
                    setMenuOpen(false);
                    setLessonPhase("learn");
                  }}
                >
                  查看场景提示
                </button>
              ) : null}
              {hasUserTurn && !isCompleted ? (
                <button
                  type="button"
                  className="m-sheet-item"
                  onClick={() => {
                    setMenuOpen(false);
                    setCompletingChoice("manual");
                  }}
                  disabled={isCompletingSession}
                >
                  {isCompletingSession ? "生成总结中…" : "结束练习并总结"}
                </button>
              ) : null}
              {session ? (
                <button
                  type="button"
                  className="m-sheet-item m-sheet-item-danger"
                  onClick={() => {
                    setMenuOpen(false);
                    void handleClearSessionHistory();
                  }}
                  disabled={isClearingHistory}
                >
                  {isClearingHistory ? "删除中…" : "删除本次会话"}
                </button>
              ) : null}
            </div>
          </section>
        </div>
      ) : null}

      {/* 结束确认面板：替代 window.confirm，手机 WebView 里原生弹窗可能不显示 */}
      {completingChoice ? (
        <div
          className="confirm-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
          onClick={(event) => {
            if (event.target === event.currentTarget) setCompletingChoice(null);
          }}
        >
          <div className="confirm-card">
            <h2 className="confirm-title" id="confirm-title">
              结束这次练习？
            </h2>
            <p className="confirm-text">
              {completingChoice === "agent_suggested"
                ? "AI 认为今天的核心目标已经练到了。结束后会生成总结，这一轮不能继续对话。"
                : "结束后会生成本次总结并计入练习记录，这一轮不能再继续说下去。"}
            </p>
            <div className="confirm-actions">
              <button
                type="button"
                className="confirm-btn confirm-btn-primary"
                disabled={isCompletingSession}
                onClick={() => void performCompleteSession(completingChoice)}
              >
                {isCompletingSession ? "生成总结中…" : "结束并生成总结"}
              </button>
              <button
                type="button"
                className="confirm-btn confirm-btn-ghost"
                onClick={() => setCompletingChoice(null)}
              >
                继续练习
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
