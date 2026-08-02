import { useEffect, useMemo, useState } from "react";
import { addFavorite, getLearningPath, getScenarios, removeFavorite } from "../api";
import type { LearningPath, Scenario, ScenarioTier } from "../types";
import { PageHeader, PrimaryButton, SecondaryButton } from "./ui";

/** 分类主题色：让卡片视觉区分更明显 */
const CATEGORY_TINTS: Record<string, string> = {
  "出行": "linear-gradient(135deg, #dbeafe 0%, #eef4ff 100%)",
  "餐饮": "linear-gradient(135deg, #fde8d7 0%, #fff4ea 100%)",
  "职场": "linear-gradient(135deg, #e6e0fa 0%, #f3efff 100%)",
  "医疗": "linear-gradient(135deg, #d9f2e6 0%, #edfaf3 100%)",
  "购物": "linear-gradient(135deg, #fdf3d0 0%, #fff8e8 100%)",
};

function scenarioLevelRange(scenario: Scenario): string {
  const levels = (scenario.bands ?? []).map((band) => band.level).filter(Boolean);
  if (levels.length === 0) return scenario.difficulty?.level ?? "";
  return `${levels[0]}–${levels[levels.length - 1]}`;
}

type Props = {
  profileId?: number;
  activeScenarioId?: string | null;
  onStartScenario: (scenario: Scenario) => void;
};

export function PlanPage({ profileId, activeScenarioId, onStartScenario }: Props) {
  const [catalog, setCatalog] = useState<{ scenarios: Scenario[]; categories: string[]; roles: string[]; tiers: ScenarioTier[]; derivedTier: ScenarioTier["id"] | null } | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [category, setCategory] = useState("");
  const [role, setRole] = useState("");
  const [tier, setTier] = useState("");
  const [learningPath, setLearningPath] = useState<LearningPath | null>(null);
  const [pathLoading, setPathLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getScenarios(profileId)
      .then((result) => {
        if (!cancelled) {
          setCatalog({
            scenarios: result.scenarios,
            categories: result.categories,
            roles: result.roles,
            tiers: result.tiers,
            derivedTier: result.derived_tier,
          });
          setStatus("ready");
        }
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [profileId]);

  const filtered = useMemo(() => {
    const items = catalog?.scenarios ?? [];
    return items.filter((scenario) => {
      if (category && scenario.category !== category) return false;
      if (role && scenario.npc_role !== role) return false;
      if (tier) {
        const levels = catalog?.tiers.find((item) => item.id === tier)?.levels ?? [];
        if (!levels.includes(scenario.difficulty?.level ?? "")) return false;
      }
      return true;
    });
  }, [catalog, category, role, tier]);

  async function generatePath(selectedTier: ScenarioTier["id"]) {
    setPathLoading(true);
    setLearningPath(null);
    try {
      const result = await getLearningPath(selectedTier, profileId);
      setLearningPath(result);
    } catch {
      // 路线加载失败保持空
    } finally {
      setPathLoading(false);
    }
  }

  async function toggleFavorite(scenario: Scenario) {
    if (!profileId) return;
    try {
      if (scenario.is_favorite) {
        await removeFavorite(scenario.id, profileId);
      } else {
        await addFavorite(scenario.id, profileId);
      }
      setCatalog((current) =>
        current
          ? {
              ...current,
              scenarios: current.scenarios.map((item) =>
                item.id === scenario.id ? { ...item, is_favorite: !item.is_favorite } : item
              ),
            }
          : current
      );
    } catch {
      // 收藏失败保持原状
    }
  }

  function startRandom() {
    if (filtered.length === 0) return;
    const candidates = filtered.filter((item) => item.id !== activeScenarioId);
    const pool = candidates.length > 0 ? candidates : filtered;
    onStartScenario(pool[Math.floor(Math.random() * pool.length)]);
  }

  const activeTier = catalog?.tiers.find((item) => item.id === tier);

  return (
    <main className="page">
      <PageHeader
        eyebrow="场景库"
        title="选择练习场景"
        description="涵盖出行、餐饮、职场、医疗与购物等真实生活场景，难度随你的水平自适应。"
        action={
          <PrimaryButton type="button" onClick={startRandom} disabled={filtered.length === 0}>
            随机一个场景
          </PrimaryButton>
        }
      />

      {status === "loading" ? <p className="muted">正在加载场景…</p> : null}
      {status === "error" ? <p className="muted">场景加载失败，请稍后再试。</p> : null}

      {status === "ready" && catalog ? (
        <>
          <section className="scenario-filters" aria-label="场景筛选">
            <label className="scenario-filter">
              <span>背景设定</span>
              <select value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="">全部</option>
                {catalog.categories.map((item) => (
                  <option value={item} key={item}>{item}</option>
                ))}
              </select>
            </label>
            <label className="scenario-filter">
              <span>角色描述</span>
              <select value={role} onChange={(event) => setRole(event.target.value)}>
                <option value="">全部</option>
                {catalog.roles.map((item) => (
                  <option value={item} key={item}>{item}</option>
                ))}
              </select>
            </label>
            <label className="scenario-filter">
              <span>难度分级</span>
              <select value={tier} onChange={(event) => setTier(event.target.value)}>
                <option value="">全部</option>
                {catalog.tiers.map((item) => (
                  <option value={item.id} key={item.id}>{item.label}（{item.levels.join("/")}）</option>
                ))}
              </select>
            </label>
          </section>

          <section className="learning-path-block" aria-label="学习路线">
            <div className="learning-path-header">
              <div>
                <p className="section-label">没有明确想法？</p>
                <h2>按水平生成学习路线</h2>
                <p className="muted">选择你的水平，为你排好由易到难的练习顺序。</p>
              </div>
            </div>
            <div className="learning-path-tiers">
              {catalog.tiers.map((item) => (
                <button
                  className={learningPath?.tier === item.id ? "path-tier path-tier-active" : "path-tier"}
                  key={item.id}
                  type="button"
                  disabled={pathLoading}
                  onClick={() => void generatePath(item.id)}
                >
                  {item.label}
                  <small>{item.levels.join(" / ")}</small>
                </button>
              ))}
            </div>
            {learningPath ? (
              <div className="learning-path-cards">
                {learningPath.path.map((scenario, index) => (
                  <button
                    className="path-card"
                    key={scenario.id}
                    type="button"
                    onClick={() => onStartScenario(scenario)}
                  >
                    <span className="path-card-index">{index + 1}</span>
                    <span className="scenario-card-media" aria-hidden="true" />
                    <span className="scenario-level">{scenario.difficulty?.level ?? ""}</span>
                    <strong>{scenario.title}</strong>
                    <small>{scenario.category} · {scenario.npc_role}</small>
                  </button>
                ))}
              </div>
            ) : null}
          </section>

          <div className="scenario-grid">
            {filtered.map((scenario) => (
              <button
                className={scenario.id === activeScenarioId ? "scenario-tile scenario-tile-active" : "scenario-tile"}
                key={scenario.id}
                type="button"
                onClick={() => onStartScenario(scenario)}
                aria-pressed={scenario.id === activeScenarioId}
              >
                <div
                  className="scenario-tile-media"
                  aria-hidden="true"
                  style={{ background: CATEGORY_TINTS[scenario.category] ?? undefined }}
                />
                <span
                  className={scenario.is_favorite ? "scenario-favorite-btn scenario-favorite-btn-active" : "scenario-favorite-btn"}
                  role="button"
                  tabIndex={0}
                  aria-label={scenario.is_favorite ? "取消收藏" : "收藏"}
                  onClick={(event) => {
                    event.stopPropagation();
                    void toggleFavorite(scenario);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      event.stopPropagation();
                      void toggleFavorite(scenario);
                    }
                  }}
                >
                  {scenario.is_favorite ? "已收藏" : "收藏"}
                </span>
                <div className="scenario-tile-body">
                  <div className="scenario-tile-meta">
                    <span className="scenario-level">{scenario.difficulty?.level ?? "A2"}</span>
                    <span className="scenario-level-range">全难度 {scenarioLevelRange(scenario)}</span>
                    <span className="scenario-tile-role">{scenario.category} · {scenario.npc_role}</span>
                  </div>
                  <strong>{scenario.title}</strong>
                  <p>{scenario.background}</p>
                  <small>{scenario.objective}</small>
                </div>
              </button>
            ))}
            {filtered.length === 0 ? (
              <p className="muted scenario-empty">没有符合筛选条件的场景，试试放宽条件。</p>
            ) : null}
          </div>
          <p className="muted scenario-grid-note">
            {activeTier ? `当前按「${activeTier.label}」难度过滤。` : ""}
            完成后系统会生成纠错报告与当日复盘，成长板块随之更新。
          </p>
        </>
      ) : null}
    </main>
  );
}
