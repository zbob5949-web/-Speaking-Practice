import { useEffect, useState } from "react";
import { getFavorites, getSessionHistory } from "../api";
import type { Profile, Scenario, SessionHistoryItem } from "../types";
import { PageHeader, SecondaryButton } from "./ui";

type Props = {
  profile: Profile;
  onSelectScenario: (scenario: Scenario) => void;
};

/** 折叠预览条数：收藏显示前 3 条、练习记录显示前 5 条，超出部分点击展开 */
const FAVORITES_PREVIEW = 3;
const HISTORY_PREVIEW = 5;

function formatTime(value: string) {
  return value ? value.replace("T", " ").slice(0, 16) : "";
}

export function ProfilePage({ profile, onSelectScenario }: Props) {
  const [favorites, setFavorites] = useState<Scenario[]>([]);
  const [history, setHistory] = useState<SessionHistoryItem[]>([]);
  const [favoritesExpanded, setFavoritesExpanded] = useState(false);
  const [historyExpanded, setHistoryExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getFavorites(profile.id)
      .then((result) => {
        if (!cancelled) setFavorites(result.favorites);
      })
      .catch(() => {
        if (!cancelled) setFavorites([]);
      });
    getSessionHistory(profile.id)
      .then((result) => {
        if (!cancelled) setHistory(result.sessions);
      })
      .catch(() => {
        if (!cancelled) setHistory([]);
      });
    return () => {
      cancelled = true;
    };
  }, [profile.id]);

  const visibleFavorites = favoritesExpanded ? favorites : favorites.slice(0, FAVORITES_PREVIEW);
  const visibleHistory = historyExpanded ? history : history.slice(0, HISTORY_PREVIEW);

  return (
    <main className="page">
      <PageHeader
        eyebrow="个人中心"
        title="我的"
        description={`${profile.learning_goal} · ${profile.current_level}`}
      />

      <section className="profile-layout">
        <div className="profile-column">
          <section className="profile-card" aria-label="收藏">
            <div className="profile-card-header">
              <p className="section-label">收藏</p>
              <h2>收藏的场景</h2>
            </div>
            {favorites.length === 0 ? (
              <p className="muted">还没有收藏场景，去场景页点星标即可收藏。</p>
            ) : (
              <>
                <ul className="profile-scenario-list">
                  {visibleFavorites.map((scenario) => (
                    <li key={scenario.id} className="profile-scenario-row">
                      <div>
                        <strong>{scenario.title}</strong>
                        <span>{scenario.npc_role} · {scenario.difficulty?.level ?? "A2"}</span>
                      </div>
                      <SecondaryButton type="button" onClick={() => onSelectScenario(scenario)}>
                        开始
                      </SecondaryButton>
                    </li>
                  ))}
                </ul>
                {favorites.length > FAVORITES_PREVIEW ? (
                  <button
                    type="button"
                    className="profile-collapse-toggle"
                    aria-expanded={favoritesExpanded}
                    onClick={() => setFavoritesExpanded((value) => !value)}
                  >
                    {favoritesExpanded ? "收起" : `展开全部（${favorites.length}）`}
                  </button>
                ) : null}
              </>
            )}
          </section>

          <section className="profile-card" aria-label="历史对话场景">
            <div className="profile-card-header">
              <p className="section-label">历史对话场景</p>
              <h2>练习记录</h2>
            </div>
            {history.length === 0 ? (
              <p className="muted">还没有练习记录，开始第一次对话吧。</p>
            ) : (
              <>
                <ul className="profile-history-list">
                  {visibleHistory.map((item) => (
                    <li key={item.id} className="profile-history-row">
                      <div>
                        <strong>{item.topic}</strong>
                        <span>
                          {formatTime(item.started_at)} · {item.turn_count} 轮 · 难度 {item.difficulty ?? "—"}
                          {item.score != null ? (
                            <span className="profile-history-score"> · 得分 {item.score}/100</span>
                          ) : null}
                          {" · "}
                          {item.ended_at ? "已结束" : "进行中"}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
                {history.length > HISTORY_PREVIEW ? (
                  <button
                    type="button"
                    className="profile-collapse-toggle"
                    aria-expanded={historyExpanded}
                    onClick={() => setHistoryExpanded((value) => !value)}
                  >
                    {historyExpanded ? "收起" : `展开全部（${history.length}）`}
                  </button>
                ) : null}
              </>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}
