import { useEffect, useState } from "react";
import { clearAuth, getAppVersion, getCurrentLearningState, getTodayStrategy, hasAuth, runDueReviews, stopActiveAudio } from "./api";
import type { AppVersionInfo } from "./api";
import { APP_VERSION_CODE } from "./appVersion";
import { AppShell } from "./components/AppShell";
import { GrowthPage } from "./components/GrowthPage";
import { LoginPage } from "./components/LoginPage";
import { PlanPage } from "./components/PlanPage";
import { PracticeRoom } from "./components/PracticeRoom";
import { ProfilePage } from "./components/ProfilePage";
import { SettingsPage } from "./components/SettingsPage";
import type { PlanDay, Profile, Scenario, TodayStrategy } from "./types";
import type { AppView } from "./components/AppShell";

type View = "loading" | "auth" | "today" | "scenes" | "practice" | "growth" | "me" | "settings";

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
  // App 更新提示：发现新版本时展示
  const [updateInfo, setUpdateInfo] = useState<AppVersionInfo | null>(null);

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
      // 没有可用计划时不弹「首次设置」：直接进场景页，用户可以选场景开练
      setView(nextDay ? "today" : "scenes");
    } catch {
      setView("scenes");
    }
  }

  useEffect(() => {
    if (!authed) {
      setView("auth");
      return;
    }
    void loadCurrentState();
  }, [authed]);

  // 检查 App 更新：必须在所有条件 return 之前注册（React hooks 规则）
  useEffect(() => {
    if (authed) {
      void checkAppUpdate();
    }
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

  /** 检查 App 新版本：发现新版本时弹更新横幅 */
  async function checkAppUpdate() {
    try {
      const info = await getAppVersion();
      if (info.version_code > APP_VERSION_CODE) {
        setUpdateInfo(info);
      }
    } catch {
      // 检查失败静默，不影响使用
    }
  }

  /** 打开下载页（原生 App 用系统浏览器；网页直接新窗口） */
  async function downloadUpdate(url: string) {
    try {
      const { Browser } = await import("@capacitor/browser");
      await Browser.open({ url });
    } catch {
      window.open(url, "_blank");
    }
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
    content = <GrowthPage profileId={profile?.id} />;
  } else if (view === "me") {
    content = profile ? (
      <ProfilePage profile={profile} onSelectScenario={selectScenario} />
    ) : (
      <PlanPage profileId={undefined} activeScenarioId={null} onStartScenario={selectScenario} onStartPath={startPathScenario} onLearningPathGenerated={handleLearningPathGenerated} />
    );
  } else if (view === "settings") {
    content = <SettingsPage />;
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
    <AppShell activeView={view as AppView} onNavigate={navigate} onLogout={handleLogout}>
      {updateInfo ? (
        <div className="update-banner" role="status" aria-label="发现新版本">
          <span className="update-banner-text">发现新版本 v{updateInfo.version_name}，更新内容：{updateInfo.changelog || "修复与优化"}</span>
          <button type="button" className="update-banner-action" onClick={() => void downloadUpdate(updateInfo.apk_url)}>立即更新</button>
          <button type="button" className="update-banner-dismiss" onClick={() => setUpdateInfo(null)}>稍后</button>
        </div>
      ) : null}
      {content}
    </AppShell>
  );
}
