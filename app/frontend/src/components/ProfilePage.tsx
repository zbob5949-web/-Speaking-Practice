import { useEffect, useState } from "react";
import { getFavorites, getSessionHistory, removeFavorite } from "../api";
import type { Profile, Scenario, SessionHistoryItem } from "../types";
import { AccountCard } from "./AccountCard";
import { SecondaryButton } from "./ui";

type Props = {
  profile: Profile | null;
  onSelectScenario: (scenario: Scenario) => void;
  onNavigate?: (view: "growth" | "settings") => void;
};

/** 折叠预览条数：收藏显示前 3 条、练习记录显示前 5 条，超出部分点击展开 */
const FAVORITES_PREVIEW = 3;
const HISTORY_PREVIEW = 5;

/** 场景中文名 */
const SCENARIO_ZH: Record<string, string> = {
  "airport-check-in": "机场值机",
  "hotel-check-in": "酒店入住",
  "restaurant-order": "餐厅点餐",
  "job-interview": "面试沟通",
  "doctor-visit": "就医问诊",
  "shopping-return": "购物退换",
  free_talk: "自由对话",
};

function formatTime(value: string) {
  return value ? value.replace("T", " ").slice(0, 16) : "";
}

export function ProfilePage({ profile, onSelectScenario, onNavigate }: Props) {
  const [favorites, setFavorites] = useState<Scenario[]>([]);
  const [history, setHistory] = useState<SessionHistoryItem[]>([]);
  const [favoritesExpanded, setFavoritesExpanded] = useState(false);
  const [historyExpanded, setHistoryExpanded] = useState(false);
  const [tab, setTab] = useState<"learn" | "pref">("learn");
  // 详情子页：列表只放一行入口，点进去才展开明细
  const [detail, setDetail] = useState<"history" | "favorites" | null>(null);

  useEffect(() => {
    let cancelled = false;
    getFavorites(profile?.id)
      .then((result) => {
        if (!cancelled) setFavorites(result.favorites);
      })
      .catch(() => {
        if (!cancelled) setFavorites([]);
      });
    (profile ? getSessionHistory(profile.id) : Promise.resolve({ sessions: [] }))
      .then((result) => {
        if (!cancelled) setHistory(result.sessions);
      })
      .catch(() => {
        if (!cancelled) setHistory([]);
      });
    return () => {
      cancelled = true;
    };
  }, [profile?.id]);

  const visibleFavorites = favoritesExpanded ? favorites : favorites.slice(0, FAVORITES_PREVIEW);
  const visibleHistory = historyExpanded ? history : history.slice(0, HISTORY_PREVIEW);

  return (
    <main className="page">
      <header className="m-profile-head">
        <div className="m-seg" role="tablist" aria-label="我的">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "learn"}
            className={tab === "learn" ? "m-seg-item m-seg-item-on" : "m-seg-item"}
            onClick={() => setTab("learn")}
          >
            我的学习
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "pref"}
            className={tab === "pref" ? "m-seg-item m-seg-item-on" : "m-seg-item"}
            onClick={() => setTab("pref")}
          >
            学习偏好
          </button>
        </div>
        <p className="m-profile-sub">{profile?.learning_goal ?? "开始你的口语练习"} · {profile?.current_level ?? ""}</p>
      </header>

      <AccountCard />
      {tab === "learn" ? (
        detail ? (
          <section className="profile-layout">
            <div className="profile-column">
              <section className="profile-card">
                <div className="profile-detail-head">
                  <button type="button" className="profile-detail-back" onClick={() => setDetail(null)}>
                    ← 返回
                  </button>
                  <strong>{detail === "history" ? "练习记录" : "收藏的场景"}</strong>
                </div>
                {detail === "history" ? (
                  history.length === 0 ? (
                    <p className="muted">还没有练习记录，开始第一次对话吧。</p>
                  ) : (
                    <ul className="profile-history-list">
                      {history.map((item) => (
                        <li key={item.id} className="profile-history-row">
                          <div>
                            <strong>{SCENARIO_ZH[item.scenario_id ?? ""] ?? item.topic}</strong>
                            <span>
                              {formatTime(item.started_at)} · {item.turn_count} 轮 · 难度 {item.difficulty ?? "—"}
                              {item.score != null ? (
                                <span className="profile-history-score"> · 得分 {item.score}/100</span>
                              ) : null}
                            </span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )
                ) : favorites.length === 0 ? (
                  <p className="muted">还没有收藏场景，去场景页点星标即可收藏。</p>
                ) : (
                  <ul className="profile-scenario-list">
                    {favorites.map((scenario) => (
                      <li key={scenario.id} className="profile-scenario-row">
                        <div>
                          <strong>{SCENARIO_ZH[scenario.id] ?? scenario.title}</strong>
                          <span>{scenario.category} · {scenario.difficulty?.level ?? "A2"}</span>
                        </div>
                        <SecondaryButton type="button" onClick={async () => {
                          try { await removeFavorite(scenario.id, profile?.id); setFavorites(items => items.filter(item => item.id !== scenario.id)); }
                          catch { window.alert("取消收藏失败，请重试"); }
                        }}>取消收藏</SecondaryButton>
                        <SecondaryButton type="button" onClick={() => onSelectScenario(scenario)}>
                          开始
                        </SecondaryButton>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </section>
        ) : (
          <section className="profile-layout">
            <div className="profile-column">
              <section className="profile-card" aria-label="我的学习">
                <ul className="m-list">
                  <li className="m-row">
                    <button type="button" className="m-row-btn" onClick={() => setDetail("history")}>
                      <span className="m-row-label">练习记录</span>
                      <span className="m-row-right">
                        <span className="m-row-value">{history.length} 条</span>
                        <span className="m-row-chevron" aria-hidden="true">›</span>
                      </span>
                    </button>
                  </li>
                  <li className="m-row">
                    <button type="button" className="m-row-btn" onClick={() => setDetail("favorites")}>
                      <span className="m-row-label">收藏的场景</span>
                      <span className="m-row-right">
                        <span className="m-row-value">{favorites.length} 个</span>
                        <span className="m-row-chevron" aria-hidden="true">›</span>
                      </span>
                    </button>
                  </li>
                </ul>
              </section>
            </div>
          </section>
        )
      ) : (
        <section className="profile-layout">
          <div className="profile-column">
            <section className="profile-card" aria-label="偏好">
              <ul className="m-list">
                <li className="m-row">
                  <span className="m-row-label">学习目标</span>
                  <span className="m-row-value">{profile?.learning_goal ?? "未设置"}</span>
                </li>
                <li className="m-row">
                  <span className="m-row-label">当前水平</span>
                  <span className="m-row-value">{profile?.current_level ?? "未设置"}</span>
                </li>
              </ul>
            </section>
          </div>
        </section>
      )}

      <section className="profile-layout">
        <div className="profile-column">
          <section className="profile-card" aria-label="更多">
            <ul className="m-list">
              <li className="m-row">
                <button type="button" className="m-row-btn" onClick={() => onNavigate?.("growth")}>
                  <span className="m-row-label">成长报告</span>
                  <span className="m-row-chevron" aria-hidden="true">›</span>
                </button>
              </li>
              <li className="m-row">
                <button type="button" className="m-row-btn" onClick={() => onNavigate?.("settings")}>
                  <span className="m-row-label">设置</span>
                  <span className="m-row-chevron" aria-hidden="true">›</span>
                </button>
              </li>
            </ul>
          </section>
        </div>
      </section>
    </main>
  );
}
