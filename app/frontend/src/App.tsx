import { useEffect, useState } from "react";
import { clearAuth, createOnboarding, getCurrentLearningState, getTodayStrategy, hasAuth, runDueReviews, stopActiveAudio } from "./api";
import { AppShell } from "./components/AppShell";
import { GrowthPage } from "./components/GrowthPage";
import { LoginPage } from "./components/LoginPage";
import { Onboarding } from "./components/Onboarding";
import { PlanPage } from "./components/PlanPage";
import { PracticeRoom } from "./components/PracticeRoom";
import { ProfilePage } from "./components/ProfilePage";
import { SettingsPage } from "./components/SettingsPage";
import type { PlanDay, Profile, Scenario, TodayStrategy } from "./types";
import type { AppView } from "./components/AppShell";

type View = "loading" | "auth" | "onboarding" | "today" | "scenes" | "practice" | "growth" | "me" | "settings";

/** 内置自由对话场景（不来自场景库，后端按 free_talk 特判处理） */
const FREE_TALK_SCENARIO: Scenario = {
  id: "free_talk",
  title: "自由对话",
  category: "自由",
  background: "没有固定剧本，和教练自由聊天，想聊什么都可以。",
  npc_role: "英语口语陪练教练",
  learner_role: "自由交谈者",
  objective: "在真实聊天中自然开口，练习流利度与表达准确性",
  bands: [],
  difficulty: { level: "A2", vocabulary_range: "", sentence_complexity: "", target_functions: [] },
};

const LAST_SCENARIO_KEY = "speakmate-last-scenario";
const LAST_PATH_KEY = "speakmate-last-path";

function readLastScenario(): Scenario | null {
  try {
    const raw = localStorage.getItem(LAST_SCENARIO_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw);
    return saved && typeof saved.id === "string" ? (saved as Scenario) : null;
  } catch {
    return null;
  }
}

function readLastPath(): Scenario[] | null {
  try {
    const raw = localStorage.getItem(LAST_PATH_KEY);
    if (!raw) return null;
    const saved = JSON.parse(raw);
    return Array.isArray(saved) && saved.length > 0 ? (saved as Scenario[]) : null;
  } catch {
    return null;
  }
}

export default function App() {
  const [view, setView] = useState<View>("loading");
  const [authed, setAuthed] = useState(() => hasAuth());
  const [profile, setProfile] = useState<Profile | null>(null);
  const [plan, setPlan] = useState<PlanDay[]>([]);
  const [activeDay, setActiveDay] = useState<PlanDay | null>(null);
  const [activeScenario, setActiveScenario] = useState<Scenario | null>(null);
  const [learningPath, setLearningPath] = useState<Scenario[] | null>(null);
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
      setLearningPath(readLastPath());
      if (nextDay) {
        getTodayStrategy(result.profile.id).then(setTodayStrategy).catch(() => setTodayStrategy(null));
      } else {
        setTodayStrategy(null);
      }
      // 恢复上次对话界面：登出再登入时回到上次的场景/自由对话，而不是回到刚注册的样子
      const lastScenario = readLastScenario();
      if (lastScenario) {
        setActiveScenario(lastScenario);
        setView("practice");
        return;
      }
      setActiveScenario(null);
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
    // 保留 last-scenario / last-path：重新登入同一账号后恢复上次对话界面
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
    setLearningPath(null);
    // 新学习计划从第一天重新开始，清除上次场景与路线的缓存
    localStorage.removeItem(LAST_SCENARIO_KEY);
    localStorage.removeItem(LAST_PATH_KEY);
    if (nextDay) {
      getTodayStrategy(result.profile.id).then(setTodayStrategy).catch(() => setTodayStrategy(null));
    }
    setView("today");
  }

  const selectDay = (day: PlanDay) => {
    setActiveDay(day);
    setActiveScenario(null);
    localStorage.removeItem(LAST_SCENARIO_KEY);
    localStorage.setItem("speakmate-last-view", "today");
    setView("practice");
  };

  const selectScenario = (scenario: Scenario) => {
    setActiveScenario(scenario);
    setView("practice");
    localStorage.setItem(LAST_SCENARIO_KEY, JSON.stringify(scenario));
    localStorage.setItem("speakmate-last-view", "practice");
  };

  /** 学习路线：选择路线后跳转到今日板块开始第一张卡片练习 */
  const startPathScenario = (scenario: Scenario) => {
    setActiveScenario(scenario);
    setView("today");
    localStorage.setItem(LAST_SCENARIO_KEY, JSON.stringify(scenario));
    localStorage.setItem("speakmate-last-view", "today");
  };

  const handleFreeTalk = () => {
    setActiveScenario(FREE_TALK_SCENARIO);
    setView("practice");
    localStorage.setItem(LAST_SCENARIO_KEY, JSON.stringify(FREE_TALK_SCENARIO));
    localStorage.setItem("speakmate-last-view", "practice");
  };

  const handleLearningPathGenerated = (path: Scenario[] | null) => {
    setLearningPath(path);
    if (path && path.length > 0) {
      localStorage.setItem(LAST_PATH_KEY, JSON.stringify(path));
    } else {
      localStorage.removeItem(LAST_PATH_KEY);
    }
  };

  const navigate = (nextView: AppView) => {
    // 切换界面时中断正在播放的音频（TTS / 语音条）
    stopActiveAudio();
    setView(nextView);
    localStorage.setItem("speakmate-last-view", nextView);
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
        learningPath={learningPath}
        onSelectScenario={selectScenario}
        onFreeTalk={handleFreeTalk}
      />
    );
  } else if (view === "scenes") {
    content = (
      <PlanPage
        profileId={profile.id}
        activeScenarioId={activeScenario?.id ?? null}
        onStartScenario={selectScenario}
        onStartPath={startPathScenario}
        onLearningPathGenerated={handleLearningPathGenerated}
      />
    );
  } else if (view === "growth") {
    content = <GrowthPage profileId={profile.id} />;
  } else if (view === "me") {
    content = <ProfilePage profile={profile} onSelectScenario={selectScenario} />;
  } else if (view === "settings") {
    content = <SettingsPage />;
  } else if (today) {
    content = (
      <PracticeRoom
        day={today}
        todayStrategy={todayStrategy}
        profileId={profile.id}
        learningPath={learningPath}
        onSelectScenario={selectScenario}
        onFreeTalk={handleFreeTalk}
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
