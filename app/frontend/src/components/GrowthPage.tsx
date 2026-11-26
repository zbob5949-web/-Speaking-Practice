import { useEffect, useMemo, useState } from "react";
import { getGrowthSummary } from "../api";
import type { GrowthSummary } from "../types";

export type GrowthDetail = "review" | "focus" | "memory" | "signals" | null;

const DETAIL_TITLES: Record<Exclude<GrowthDetail, null>, string> = {
  review: "最近复盘",
  focus: "下一步重点",
  memory: "教练记忆",
  signals: "学习信号",
};

/** 教练记忆只展示这四类，其余类别（学习偏好、词汇缺口等）不进入成长页 */
const MEMORY_CATEGORIES = ["learning_pattern", "goal", "strength", "weakness"] as const;

const MEMORY_LABELS: Record<string, string> = {
  weakness: "薄弱点",
  strength: "优势",
  goal: "学习目标",
  learning_pattern: "学习习惯",
};

const ENTRY_ICONS: Record<EntryProps["tone"], string> = {
  review: "复",
  focus: "重",
  memory: "忆",
  signals: "信",
};

function memoryLabel(category: string): string {
  return MEMORY_LABELS[category] ?? "记忆";
}

function oneLine(value: string | undefined | null, fallback: string): string {
  const text = (value ?? "").trim();
  return text || fallback;
}

function formatDate(value?: string | null): string {
  return value ? value.replace("T", " ").slice(0, 10) : "";
}

/** 只取第一句，用于「下一步重点」每个子板块的一句话总结 */
function firstSentence(value: string | undefined | null): string {
  const text = (value ?? "").trim();
  if (!text) return "";
  const matched = text.match(/^[^。；;！!？?]+[。；;！!？?]?/);
  return (matched ? matched[0] : text).trim();
}

/** 词云里的词：截取句首若干字，点开看整句 */
function cloudWord(sentence: string): string {
  const text = sentence.trim();
  const head = text.replace(/[。；;，,！!？?].*$/, "");
  return head.length > 10 ? `${head.slice(0, 10)}…` : head || text.slice(0, 10);
}

type EntryProps = {
  tone: "review" | "focus" | "memory" | "signals";
  title: string;
  summary: string;
  onClick: () => void;
};

/** 成长页入口行：只展示小标题 + 一句摘要，点进去看完整内容 */
function GrowthEntry({ tone, title, summary, onClick }: EntryProps) {
  return (
    <button type="button" className="growth-entry" onClick={onClick}>
      <span className={`growth-entry-icon growth-entry-icon-${tone}`} aria-hidden="true">
        {ENTRY_ICONS[tone]}
      </span>
      <span className="growth-entry-main">
        <span className="growth-entry-title">{title}</span>
        <span className="growth-entry-sub">{summary}</span>
      </span>
      <span className="growth-entry-meta">
        <span className="m-row-chevron" aria-hidden="true">›</span>
      </span>
    </button>
  );
}

export function GrowthPage({
  profileId,
  detail,
  onDetailChange,
}: {
  profileId?: number;
  detail: GrowthDetail;
  onDetailChange: (detail: GrowthDetail) => void;
}) {
  const [summary, setSummary] = useState<GrowthSummary | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [reloadKey, setReloadKey] = useState(0);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [activeSignal, setActiveSignal] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    getGrowthSummary(profileId)
      .then((result) => {
        if (!cancelled) {
          setSummary(result);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [profileId, reloadKey]);

  const latestReview = summary?.latest_review ?? null;
  const memory = useMemo(
    () => (summary?.active_memory ?? []).filter((item) => MEMORY_CATEGORIES.includes(item.category as never)),
    [summary],
  );
  const adjustments = summary?.active_adjustments ?? [];
  const strengths = latestReview?.structured_analysis?.strengths ?? [];
  const weaknesses = latestReview?.structured_analysis?.weaknesses ?? [];
  const previousReviews = (summary?.recent_reviews ?? []).slice(1);

  const reviewSummary = latestReview?.user_report?.summary ?? "";
  const signalTotal = strengths.length + weaknesses.length;

  // 词云：优势和待改进混排，字号按序号递减，点击后展示整句
  const cloudItems = useMemo(
    () => [
      ...strengths.map((text, index) => ({ text, tone: "strength" as const, order: index })),
      ...weaknesses.map((text, index) => ({ text, tone: "weakness" as const, order: strengths.length + index })),
    ],
    [strengths, weaknesses],
  );

  function renderDetail() {
    if (!detail || !summary) return null;

    if (detail === "review") {
      if (!latestReview) {
        return (
          <p className="growth-empty">
            还没有复盘记录。完成一次练习后，系统会在当天结束时生成复盘与下一步建议。
          </p>
        );
      }
      return (
        <>
          <p className="section-label">复盘摘要</p>
          <h2>{oneLine(reviewSummary, "本次复盘已生成")}</h2>

          {previousReviews.length > 0 ? (
            <div className="growth-detail-section">
              <button
                type="button"
                className="growth-collapse-toggle"
                aria-expanded={historyOpen}
                onClick={() => setHistoryOpen((open) => !open)}
              >
                <span>历史复盘 · {previousReviews.length}</span>
                <span className="growth-collapse-arrow" aria-hidden="true">{historyOpen ? "收起" : "展开"}</span>
              </button>
              {historyOpen
                ? previousReviews.map((review, index) => (
                    <div className="growth-detail-item" key={`${review.id ?? review.review_date ?? "review"}-${index}`}>
                      <div className="growth-detail-row">
                        <strong>{formatDate(review.review_date) || "复盘"}</strong>
                      </div>
                      <p>{oneLine(review.user_report?.summary, "暂无摘要")}</p>
                    </div>
                  ))
                : null}
            </div>
          ) : null}
        </>
      );
    }

    if (detail === "focus") {
      if (adjustments.length === 0) {
        return <p className="growth-empty">还没有自适应计划调整，完成练习后会自动生成。</p>;
      }
      return adjustments.map((item) => (
        <div className="growth-detail-item" key={item.id}>
          <div className="growth-detail-row">
            <strong>{item.title}</strong>
          </div>
          <p>{firstSentence(item.instruction)}</p>
        </div>
      ));
    }

    if (detail === "memory") {
      if (memory.length === 0) {
        return <p className="growth-empty">还没有长期教练记忆，多练几次后这里会记录你的常错点。</p>;
      }
      return memory.map((item) => (
        <div className="growth-detail-item" key={item.id}>
          <div className="growth-detail-row">
            <strong>{memoryLabel(item.category)}</strong>
          </div>
          <p>{item.content}</p>
        </div>
      ));
    }

    if (cloudItems.length === 0) {
      return <p className="growth-empty">完成每日复盘后会生成学习信号。</p>;
    }

    const selected = cloudItems.find((item) => item.text === activeSignal) ?? null;

    return (
      <>
        <div className="growth-cloud" role="list">
          {cloudItems.map((item, index) => (
            <button
              key={`${item.tone}-${index}`}
              type="button"
              role="listitem"
              className={`growth-cloud-word growth-cloud-${item.tone}${activeSignal === item.text ? " growth-cloud-active" : ""}`}
              style={{ fontSize: `${index === 0 ? 1.05 : index < 3 ? 0.98 : index < 6 ? 0.9 : 0.83}rem` }}
              onClick={() => setActiveSignal(activeSignal === item.text ? null : item.text)}
            >
              {cloudWord(item.text)}
            </button>
          ))}
        </div>
        {selected ? (
          <div className="growth-cloud-detail">
            <span className={`growth-cloud-tag growth-cloud-${selected.tone}`}>
              {selected.tone === "strength" ? "优势" : "待改进"}
            </span>
            <p>{selected.text}</p>
          </div>
        ) : (
          <p className="growth-empty">点一下词语看具体内容。</p>
        )}
      </>
    );
  }

  return (
    <main className="growth-page">
      <header className="page-header">
        <h1>成长</h1>
        <p className="muted">复盘、教练记忆与下一步训练重点。</p>
      </header>

      <div className="growth-content">
        {status === "loading" ? <p className="growth-state muted">正在加载教练记忆…</p> : null}

        {status === "error" ? (
          <div className="growth-state">
            <p className="muted">暂时无法加载成长总结。</p>
            <button type="button" className="profile-detail-back" onClick={() => setReloadKey((key) => key + 1)}>
              重新加载
            </button>
          </div>
        ) : null}

        {status === "ready" && !detail ? (
          <div className="growth-hub growth-group">
            <GrowthEntry
              tone="review"
              title="最近复盘"
              summary={oneLine(reviewSummary, "完成一次练习后生成复盘")}
              onClick={() => onDetailChange("review")}
            />
            <GrowthEntry
              tone="focus"
              title="下一步重点"
              summary={firstSentence(adjustments[0]?.instruction) || "还没有自适应调整"}
              onClick={() => onDetailChange("focus")}
            />
            <GrowthEntry
              tone="memory"
              title="教练记忆"
              summary={memory.length > 0 ? `${memoryLabel(memory[0].category)}：${memory[0].content}` : "还没有长期教练记忆"}
              onClick={() => onDetailChange("memory")}
            />
            <GrowthEntry
              tone="signals"
              title="学习信号"
              summary={signalTotal > 0 ? `优势 ${strengths.length} 项 · 待改进 ${weaknesses.length} 项` : "完成每日复盘后生成"}
              onClick={() => onDetailChange("signals")}
            />
          </div>
        ) : null}

        {status === "ready" && detail ? (
          <div className="growth-hub">
            <div className="profile-detail-head growth-detail-head">
              <button type="button" className="profile-detail-back" onClick={() => onDetailChange(null)}>
                ← 返回
              </button>
              <strong>{DETAIL_TITLES[detail]}</strong>
            </div>
            <section className="growth-detail-card">{renderDetail()}</section>
          </div>
        ) : null}
      </div>
    </main>
  );
}
