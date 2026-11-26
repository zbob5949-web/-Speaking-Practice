import { useEffect, useRef, useState } from "react";
import { UNAUTHORIZED_EVENT, clearAuth, getCurrentLearningState, getTodayStrategy, hasAuth, runDueReviews, stopActiveAudio } from "./api";
import { AppShell } from "./components/AppShell";
import { DevicePreview } from "./components/DevicePreview";
import { GrowthPage } from "./components/GrowthPage";
import type { GrowthDetail } from "./components/GrowthPage";
import { HomePage } from "./components/HomePage";
import { LoginPage } from "./components/LoginPage";
import { PlanPage } from "./components/PlanPage";
import { PracticeRoom } from "./components/PracticeRoom";
import { ProfilePage } from "./components/ProfilePage";
import { SettingsPage } from "./components/SettingsPage";
import type { PlanDay, Profile, Scenario, TodayStrategy } from "./types";
import type { AppView } from "./components/AppShell";

type View = "loading" | "auth" | "home" | "today" | "scenes" | "practice" | "growth" | "me" | "settings";

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

function AppInner() {
  const [view, setView] = useState<View>("loading");
  const [authed, setAuthed] = useState(() => hasAuth());
  const [profile, setProfile] = useState<Profile | null>(null);
  const [plan, setPlan] = useState<PlanDay[]>([]);
  const [activeDay, setActiveDay] = useState<PlanDay | null>(null);
  const [activeScenario, setActiveScenario] = useState<Scenario | null>(null);
  const [learningPath, setLearningPath] = useState<Scenario[] | null>(null);
  const [todayStrategy, setTodayStrategy] = useState<TodayStrategy | null>(null);
  // 成长页的详情子页：null 表示显示入口列表
  const [growthDetail, setGrowthDetail] = useState<GrowthDetail>(null);
  // 返回栈：用于全局「返回上一页」
  const viewStackRef = useRef<View[]>([]);
  const [canBack, setCanBack] = useState(false);

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
      // 登录后统一进入主页面（Learn / Review），不再自动跳进上次的对话
      setActiveScenario(readLastScenario());
      setView("home");
    } catch {
      setView("home");
    }
  }

  useEffect(() => {
    if (!authed) {
      setView("auth");
      return;
    }
    void loadCurrentState();
  }, [authed]);

  // 令牌过期（任何接口返回 401）：api 层已清理本地登录态，这里把界面切回登录页，
  // 否则会出现「界面还在、但每次操作都报登录已过期」的卡死状态。
  useEffect(() => {
    function onUnauthorized() {
      handleLogout();
    }
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  function handleLogout() {
    stopActiveAudio();
    clearAuth();
    setAuthed(false);
    setLearningPath(null);
    viewStackRef.current = [];
    setCanBack(false);
    localStorage.removeItem(LAST_SCENARIO_KEY);
    localStorage.removeItem(LAST_PATH_KEY);
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
    // 离开成长页时收起详情子页，下次进入回到入口列表
    if (nextView !== "growth") {
      setGrowthDetail(null);
    }
    // 记录返回栈（同一页面不重复入栈）
    if (view !== nextView) {
      viewStackRef.current = [...viewStackRef.current, view as View].slice(-10);
      setCanBack(true);
    }
    setView(nextView);
    localStorage.setItem("speakmate-last-view", nextView);
  };

  /** 返回：统一回主页面（不做多级回跳） */
  const goBack = () => {
    stopActiveAudio();
    viewStackRef.current = [];
    setCanBack(false);
    setGrowthDetail(null);
    setView("home");
    localStorage.setItem("speakmate-last-view", "home");
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

  const today = activeDay ?? plan.find((day) => day.status === "pending") ?? plan[0] ?? null;

  let content: React.ReactNode;
  if (view === "home") {
    content = (
      <HomePage
        profileId={profile?.id}
        onStart={() => navigate("today")}
        onReview={() => navigate("growth")}
        onSettings={() => navigate("settings")}
      />
    );
  } else if (view === "today" || view === "practice") {
    // 今日 与 练习 统一渲染同一 PracticeRoom：切换视图不卸载，保留对话与语音条状态；
    // 用户选过的场景会话在两种视图下都按 scenario 恢复。
    content = (
      <PracticeRoom
        day={activeDay ?? today}
        scenario={activeScenario}
        todayStrategy={todayStrategy}
        profileId={profile?.id}
        learningPath={learningPath}
        onSelectScenario={selectScenario}
        onFreeTalk={handleFreeTalk}
      />
    );
  } else if (view === "scenes") {
    content = (
      <PlanPage
        profileId={profile?.id}
        activeScenarioId={activeScenario?.id ?? null}
        onStartScenario={selectScenario}
        onStartPath={startPathScenario}
        onLearningPathGenerated={handleLearningPathGenerated}
      />
    );
  } else if (view === "growth") {
    content = (
      <GrowthPage
        profileId={profile?.id}
        detail={growthDetail}
        onDetailChange={setGrowthDetail}
      />
    );
  } else if (view === "me") {
    content = (
      <ProfilePage
        profile={profile}
        onSelectScenario={selectScenario}
        onNavigate={(next) => navigate(next as AppView)}
      />
    );
  } else if (view === "settings") {
    content = <SettingsPage onLogout={handleLogout} />;
  } else if (today) {
    content = (
      <PracticeRoom
        day={today}
        todayStrategy={todayStrategy}
        profileId={profile?.id}
        learningPath={learningPath}
        onSelectScenario={selectScenario}
        onFreeTalk={handleFreeTalk}
      />
    );
  } else {
    // 没有任何计划兜底：直接展示场景选择页（不再弹「首次设置」）
    content = (
      <PlanPage
        profileId={profile?.id}
        activeScenarioId={null}
        onStartScenario={selectScenario}
        onStartPath={startPathScenario}
        onLearningPathGenerated={handleLearningPathGenerated}
      />
    );
  }

  return (
    <AppShell
      activeView={view as AppView}
      onNavigate={navigate}
      onLogout={handleLogout}
      onBack={goBack}
      canBack={canBack}
    >
      {content}
    </AppShell>
  );
}

/**
 * 外层只负责「电脑 / 手机」布局切换壳，业务逻辑仍在 AppInner。
 * 手机模式用 iframe（宽度 390px）承载同一个应用，@media 断点会真实命中。
 */
export default function App() {
  return (
    <DevicePreview>
      <AppInner />
    </DevicePreview>
  );
}
