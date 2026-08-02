import { FormEvent, useEffect, useState } from "react";
import { getProfiles } from "../api";
import type { Profile } from "../types";
import { FormField, PrimaryButton } from "./ui";

type Props = {
  onComplete: (input: {
    learning_goal: string;
    total_days: number;
    daily_minutes: number;
    current_level: string;
  }) => Promise<void>;
  onSelectProfile: (id: number) => void;
};

export function Onboarding({ onComplete, onSelectProfile }: Props) {
  const [learningGoal, setLearningGoal] = useState("提升日常对话的口语流利度");
  const [totalDays, setTotalDays] = useState(14);
  const [dailyMinutes, setDailyMinutes] = useState(15);
  const [currentLevel, setCurrentLevel] = useState("中级（大学英语四级左右）");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [profiles, setProfiles] = useState<Profile[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const data = await getProfiles();
        setProfiles(data.profiles);
      } catch (e) {
        console.error("加载学习档案失败", e);
      }
    }
    void load();
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    await onComplete({
      learning_goal: learningGoal,
      total_days: totalDays,
      daily_minutes: dailyMinutes,
      current_level: currentLevel
    });
    setIsSubmitting(false);
  }

  return (
    <main className="onboarding-page">
      <div className="onboarding-card">
        <section className="hero-panel">
          <p className="hero-kicker">专属口语教练</p>
          <h1>SpeakMate 场景口语陪练</h1>
          <p className="muted">按场景对话 · 实时语法纠错 · 难度随水平自适应</p>
          
          <div className="project-list-container">
            <h2 className="project-list-title">我的学习目标</h2>
            {profiles.length > 0 ? (
              <div className="project-list">
                {profiles.map(p => (
                  <button 
                    key={p.id} 
                    className="project-list-item"
                    onClick={() => onSelectProfile(p.id)}
                  >
                    <strong>{p.learning_goal}</strong>
                    <span>{p.total_days} 天 • {p.current_level}</span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="project-list-empty">还没有学习目标。</p>
            )}
            
            <button 
              className="project-list-item" 
              style={{ marginTop: "12px", borderStyle: "dashed", alignItems: "center", background: "transparent" }}
              onClick={(e) => { e.preventDefault(); document.querySelector('textarea')?.focus(); }}
            >
              <strong>+ 新建学习计划</strong>
            </button>
          </div>
        </section>

        <form className="setup-form" onSubmit={handleSubmit} aria-label="首次设置表单">
          <div>
            <p className="eyebrow">首次设置</p>
            <h1>创建你的口语练习计划</h1>
            <p className="muted">这些选项只用于生成一次专属学习计划，之后可以随时修改。</p>
          </div>
          <FormField label="学习目标">
            <textarea value={learningGoal} onChange={(event) => setLearningGoal(event.target.value)} />
          </FormField>
          <div className="grid-two">
            <FormField label="计划天数">
              <select value={totalDays} onChange={(event) => setTotalDays(Number(event.target.value))}>
                <option value={7}>7 天</option>
                <option value={14}>14 天</option>
                <option value={30}>30 天</option>
              </select>
            </FormField>
            <FormField label="每天练习时长">
              <select value={dailyMinutes} onChange={(event) => setDailyMinutes(Number(event.target.value))}>
                <option value={10}>10 分钟</option>
                <option value={15}>15 分钟</option>
                <option value={20}>20 分钟</option>
              </select>
            </FormField>
          </div>
          <FormField label="当前英语水平">
            <input value={currentLevel} onChange={(event) => setCurrentLevel(event.target.value)} />
          </FormField>
          <PrimaryButton type="submit" disabled={isSubmitting}>
            {isSubmitting ? "生成中…" : "生成计划"}
          </PrimaryButton>
        </form>
      </div>
    </main>
  );
}
