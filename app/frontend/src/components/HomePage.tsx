import { useEffect, useState } from "react";
import { getSessionHistory } from "../api";
import type { SessionHistoryItem } from "../types";

type Props = {
  profileId?: number;
  onStart: () => void;
  onReview: () => void;
};

/** 场景中文名（主页最近一次练习用） */
const SCENARIO_ZH: Record<string, string> = {
  "airport-check-in": "机场值机",
  "hotel-check-in": "酒店入住",
  "restaurant-order": "餐厅点餐",
  "job-interview": "面试沟通",
  "doctor-visit": "就医问诊",
  "shopping-return": "购物退换",
  free_talk: "自由对话",
};

export function HomePage({ profileId, onStart, onReview }: Props) {
  const [history, setHistory] = useState<SessionHistoryItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    getSessionHistory(profileId)
      .then((result) => {
        if (!cancelled) setHistory(result.sessions);
      })
      .catch(() => {
        if (!cancelled) setHistory([]);
      });
    return () => {
      cancelled = true;
    };
  }, [profileId]);

  const latest = history[0];
  const latestTitle = latest
    ? SCENARIO_ZH[latest.scenario_id ?? ""] ?? latest.topic
    : "还没有开始过";

  return (
    <main className="home-page">
      <header className="home-hero">
        <p className="home-eyebrow">场景口语陪练</p>
        <h1 className="home-title">SpeakMate</h1>
        <p className="home-sub">开口练一句，比背十句有用</p>
      </header>

      <section className="home-cards">
        <button type="button" className="home-card" onClick={onStart}>
          <span className="home-card-title">Chat</span>
          <span className="home-card-meta">
            {history.length > 0 ? `上次：${latestTitle}` : "开始第一次练习"}
          </span>
          <span className="home-card-badge home-card-badge-done" aria-hidden="true">✓</span>
        </button>

        <button type="button" className="home-card" onClick={onReview}>
          <span className="home-card-title">Profile</span>
          <span className="home-card-meta">
            {history.length > 0 ? `${history.length} 条练习记录` : "还没有练习记录"}
          </span>
          <span className="home-card-badge" aria-hidden="true">{history.length}</span>
        </button>
      </section>
    </main>
  );
}
