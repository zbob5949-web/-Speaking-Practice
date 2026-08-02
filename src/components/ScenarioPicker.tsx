import { useEffect, useState } from "react";
import { getScenarios } from "../api";
import type { Scenario } from "../types";

type Props = {
  profileId?: number;
  activeScenarioId?: string | null;
  onSelect: (scenario: Scenario) => void;
  /** 对话已开始后，顶部标题区渐隐收起 */
  faded?: boolean;
};

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

export function ScenarioPicker({ profileId, activeScenarioId, onSelect, faded = false }: Props) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);

  useEffect(() => {
    let cancelled = false;
    getScenarios(profileId)
      .then((result) => {
        if (!cancelled) setScenarios(result.scenarios.slice(0, 6));
      })
      .catch(() => {
        if (!cancelled) setScenarios([]);
      });
    return () => {
      cancelled = true;
    };
  }, [profileId]);

  if (scenarios.length === 0) return null;

  return (
    <section className="scenario-picker" aria-label="练习场景选择">
      <div className={faded ? "scenario-picker-header scenario-picker-header-fade" : "scenario-picker-header"}>
        <div>
          <p className="section-label">今日练习</p>
          <h2>选择一个场景开始对话</h2>
          <p className="muted">不同生活场景轮换练习，避免重复单调。</p>
        </div>
      </div>
      <div className="scenario-card-list">
        {scenarios.map((scenario) => (
          <button
            className={scenario.id === activeScenarioId ? "scenario-card scenario-card-active" : "scenario-card"}
            key={scenario.id}
            type="button"
            onClick={() => onSelect(scenario)}
            aria-pressed={scenario.id === activeScenarioId}
          >
            <span
              className="scenario-card-media"
              aria-hidden="true"
              style={{ background: CATEGORY_TINTS[scenario.category] ?? undefined }}
            />
            <span className="scenario-card-index">{scenario.category} · {scenarioLevelRange(scenario)}</span>
            <strong>{scenario.title}</strong>
            <span>{scenario.npc_role}</span>
            <small>{scenario.background}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
