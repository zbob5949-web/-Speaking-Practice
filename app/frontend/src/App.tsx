import { useEffect, useState } from "react";
import { clearAuth, createOnboarding, getCurrentLearningState, getTodayStrategy, hasAuth, runDueReviews, stopActiveAudio } from "./api";
import { AppShell } from "./components/AppShell";
import { GrowthPage } from "./components/GrowthPage";
import { LoginPage } from "./components/LoginPage";
import { Onboarding } from "./components/Onboarding";
import { PlanPage } from "./components/PlanPage";
import { PracticeRoom } from "./components/PracticeRoom";
import { SettingsPage } from "./components/SettingsPage";
import type { PlanDay, Profile, Scenario, TodayStrategy } from "./types";
import type { AppView } from "./components/AppShell";

type View = "loading" | "auth" | "onboarding" | "today" | "scenes" | "practice" | "growth" | "settings";

export default function App() {
  const [view, setView] = useState<View>("loading");
  const [authed, setAuthed] = useState(() => hasAuth());
  const [profile, setProfile] = useState<Profile | null>(null);
  const [plan, setPlan] = useState<PlanDay[]>([]);
  const [activeDay, setActiveDay] = useState<PlanDay | null>(null);
  const [activeScenario, setActiveScenario] = useState<Scenario | null>(null);
  const [todayStrategy, setTodayStrategy] = useState<TodayStrategy | null>(null);

  async function loadCurrentState(profileId?: number) {
    try {
      setView("loading");
      await runDueReviews().catch(console.error);
      const result = await getCurrentLearningState(profileId);
      const nextDay = result.plan.find((day) => day.status === "pending") ?? result.plan[0] ?? null;
      setProfile(result.profile);
      setPlan(result.plan);
      setActiveDay(nextDay);
      if (nextDay) {
        getTodayStrategy(result.profile.id).then(setTodayStrategy).catch(() => setTodayStrategy(null));
      } else {
        setTodayStrategy(null);
      }
      setView(nextDay ? "today" : "onboarding");
    } catch {
      setView("onboarding");
    }
  }

  useEffect(() => {
    if (!authed) {
      setView("auth");
      return;
    }
    void loadCurrentState();
  }, [authed]);

  function handleLogout() {
    stopActiveAudio();
    clearAuth();
    setAuthed(false);
    setProfile(null);
    setPlan([]);
    setActiveDay(null);
    setActiveScenario(null);
    setTodayStrategy(null);
    setView("auth");
  }

  function handleAuthed() {
    setAuthed(true);
    void loadCurrentState();
  }

  async function handleOnboarding(input: {
    learning_goal: string;
    total_days: number;
    daily_minutes: number;
    current_level: string;
  }) {
    const result = await createOnboarding(input);
    const nextDay = result.plan.find((day) => day.status === "pending") ?? result.plan[0] ?? null;
    setProfile(result.profile);
    setPlan(result.plan);
    setActiveDay(nextDay);
    setActiveScenario(null);
    if (nextDay) {
      getTodayStrategy(result.profile.id).then(setTodayStrategy).catch(() => setTodayStrategy(null));
    }
    setView("today");
  }

  const selectDay = (day: PlanDay) => {
    setActiveDay(day);
    setActiveScenario(null);
    setView("practice");
  };

  const selectScenario = (scenario: Scenario) => {
    setActiveScenario(scenario);
    setView("practice");
  };

  const navigate = (nextView: AppView) => {
    // 切换界面时中断正在播放的音频（TTS / 语音条）
    stopActiveAudio();
    setView(nextView);
  };

  if (view === "loading") {
    return (
      <main className="onboarding-page">
        <p className="muted">正在加载你的练习…</p>
      </main>
    );
  }

  if (view === "auth" || !authed) {
    return <LoginPage onAuthed={handleAuthed} />;
  }

  if (view === "onboarding" || !profile) {
    return <Onboarding onComplete={handleOnboarding} onSelectProfile={loadCurrentState} />;
  }

  const today = activeDay ?? plan.find((day) => day.status === "pending") ?? plan[0] ?? null;

  let content: React.ReactNode;
  if (view === "today" || view === "practice") {
    // 今日 与 练习 统一渲染同一 PracticeRoom：切换视图不卸载，保留对话与语音条状态；
    // 用户选过的场景会话在两种视图下都按 scenario 恢复。
    content = (
      <PracticeRoom
        day={activeDay ?? today}
        scenario={activeScenario}
        todayStrategy={todayStrategy}
        profileId={profile.id}
        onSelectScenario={selectScenario}
      />
    );
  } else if (view === "scenes") {
    content = (
      <PlanPage
        profileId={profile.id}
        activeScenarioId={activeScenario?.id ?? null}
        onStartScenario={selectScenario}
      />
    );
  } else if (view === "growth") {
    content = <GrowthPage profileId={profile.id} />;
  } else if (view === "settings") {
    content = <SettingsPage profile={profile} onSelectScenario={selectScenario} />;
  } else if (today) {
    content = (
      <PracticeRoom
        day={today}
        todayStrategy={todayStrategy}
        profileId={profile.id}
        onSelectScenario={selectScenario}
      />
    );
  } else {
    content = <Onboarding onComplete={handleOnboarding} onSelectProfile={loadCurrentState} />;
  }

  return (
    <AppShell activeView={view as AppView} onNavigate={navigate} onLogout={handleLogout}>
      {content}
    </AppShell>
  );
}
