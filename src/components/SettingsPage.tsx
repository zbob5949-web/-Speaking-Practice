import { useEffect, useState } from "react";
import { getFavorites, getSessionHistory } from "../api";
import type { Profile, Scenario, SessionHistoryItem } from "../types";
import { PageHeader, SecondaryButton } from "./ui";

type Props = {
  profile: Profile;
  onSelectScenario: (scenario: Scenario) => void;
};

function formatTime(value: string) {
  return value ? value.replace("T", " ").slice(0, 16) : "";
}

export function SettingsPage({ profile, onSelectScenario }: Props) {
  const [favorites, setFavorites] = useState<Scenario[]>([]);
  const [history, setHistory] = useState<SessionHistoryItem[]>([]);
  const [bilingualEnabled, setBilingualEnabled] = useState(
    () => localStorage.getItem("speakmate-bilingual") !== "off"
  );

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

  function toggleBilingual() {
    const next = !bilingualEnabled;
    setBilingualEnabled(next);
    localStorage.setItem("speakmate-bilingual", next ? "on" : "off");
  }

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
              <ul className="profile-scenario-list">
                {favorites.map((scenario) => (
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
              <ul className="profile-history-list">
                {history.slice(0, 30).map((item) => (
                  <li key={item.id} className="profile-history-row">
                    <div>
                      <strong>{item.topic}</strong>
                      <span>
                        {formatTime(item.started_at)} · {item.turn_count} 轮 ·{" "}
                        {item.ended_at ? "已结束" : "进行中"}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <aside className="profile-column profile-column-aside">
          <section className="profile-card" aria-label="设置">
            <div className="profile-card-header">
              <p className="section-label">设置</p>
              <h2>显示与朗读</h2>
            </div>
            <div className="profile-setting-row">
              <div>
                <strong>双语展示</strong>
                <span>对话中显示中文翻译</span>
              </div>
              <button
                className={bilingualEnabled ? "bilingual-toggle bilingual-toggle-active" : "bilingual-toggle"}
                type="button"
                aria-pressed={bilingualEnabled}
                onClick={toggleBilingual}
              >
                {bilingualEnabled ? "开" : "关"}
              </button>
            </div>
          </section>

          <section className="profile-card" aria-label="关于">
            <div className="profile-card-header">
              <p className="section-label">关于</p>
              <h2>SpeakMate</h2>
            </div>
            <p className="muted">场景口语陪练 · 按场景对话、实时语法纠错、难度随水平自适应。</p>
          </section>
        </aside>
      </section>
    </main>
  );
}
