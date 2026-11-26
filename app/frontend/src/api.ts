import { monitorAudio, prepareAudioMeter } from "./audioMeter";
import type { ConversationTurn, ErrorReport, GrowthSummary, InlineFeedback, LanguageSupportMode, LanguageSupportResult, LearningPath, OnboardingResponse, PlanDay, PracticeBrief, PracticeSession, Profile, Scenario, ScenarioCatalog, SessionCompletion, SessionHistoryItem, TodayStrategy } from "./types";

// 默认同源（页面与 API 同端口发布）：留空即用当前访问地址，
// 这样 localhost / 127.0.0.1 / 局域网 IP / 手机访问都能正常工作。
// 需要前后端分离时用 VITE_API_BASE 指定绝对地址。
const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

/** 登录态失效事件名：App 监听后自动回到登录页 */
export const UNAUTHORIZED_EVENT = "speakmate:unauthorized";

/**
 * 统一请求封装：自动附加登录 token；token 过期(401)时清理登录态。
 * 登录/注册/游客接口本身不需要 token，由后端自行处理。
 */
async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem("speakmate-token");
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await window.fetch(input, { ...init, headers });
  if (response.status === 401 && typeof input === "string" && ![/\/api\/auth\/(login|register|guest|refresh)$/].some(pattern => pattern.test(input))) {
    clearAuth();
    // 通知界面层：令牌已失效，立刻回到登录页，避免停留在“界面在但操作全失败”的状态
    if (typeof window !== "undefined" && typeof window.dispatchEvent === "function") {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    throw new Error("登录已过期，请重新登录");
  }
  return response;
}

export type AsrResult = {
  text: string;
  provider: string;
  confidence: number;
  filename: string;
};

export async function transcribeAudio(audio: Blob, filename?: string): Promise<AsrResult> {
  const formData = new FormData();
  const extension = audio.type.includes("mp4") ? "m4a" : "webm";
  formData.append("audio", audio, filename ?? "speakmate-recording." + extension);
  const response = await apiFetch(API_BASE + "/api/asr", {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    let detail = "语音识别失败";
    try {
      const payload = await response.json();
      if (payload?.detail) detail = payload.detail;
    } catch {
      // Keep a stable user-facing error when the server returns no JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function createOnboarding(input: {
  learning_goal: string;
  total_days: number;
  daily_minutes: number;
  current_level: string;
}): Promise<OnboardingResponse> {
  const response = await apiFetch(`${API_BASE}/api/onboarding`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  if (!response.ok) {
    throw new Error("Failed to create onboarding");
  }
  return response.json();
}

export async function getProfiles(): Promise<{ profiles: Profile[] }> {
  const response = await apiFetch(`${API_BASE}/api/profiles`);
  return response.json();
}

export async function deleteProfile(profileId: number): Promise<void> {
  const response = await apiFetch(`${API_BASE}/api/profiles/${profileId}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error("Failed to delete profile");
  }
}

export async function runDueReviews(): Promise<{ status: string; processed_days: number }> {
  const res = await apiFetch(`${API_BASE}/api/daily-review/run-due`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to run due reviews");
  return res.json();
}

export async function getCurrentLearningState(profileId?: number): Promise<OnboardingResponse> {
  const url = profileId ? `${API_BASE}/api/current?profile_id=${profileId}` : `${API_BASE}/api/current`;
  const response = await apiFetch(url);
  if (!response.ok) {
    throw new Error("No current learning state");
  }
  return response.json();
}

export async function getGrowthSummary(profileId?: number): Promise<GrowthSummary> {
  const url = profileId ? `${API_BASE}/api/growth/summary?profile_id=${profileId}` : `${API_BASE}/api/growth/summary`;
  const response = await apiFetch(url);
  if (!response.ok) {
    throw new Error("Failed to get growth summary");
  }
  return response.json();
}

export async function getTodayStrategy(profileId?: number): Promise<TodayStrategy> {
  const url = profileId ? `${API_BASE}/api/today/strategy?profile_id=${profileId}` : `${API_BASE}/api/today/strategy`;
  const response = await apiFetch(url);
  if (!response.ok) {
    throw new Error("Failed to get today strategy");
  }
  return response.json();
}

export async function startSession(planDayId: number): Promise<{
  session: PracticeSession;
  turns: ConversationTurn[];
  plan_day: PlanDay;
  feedback_history?: InlineFeedback[];
  practice_brief?: PracticeBrief;
  completion?: SessionCompletion;
}> {
  const response = await apiFetch(`${API_BASE}/api/sessions/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan_day_id: planDayId })
  });
  if (!response.ok) {
    throw new Error("Failed to start session");
  }
  return response.json();
}

export type StartScenarioSessionResult = {
  session: PracticeSession;
  turns: ConversationTurn[];
  plan_day: PlanDay | null;
  feedback_history?: InlineFeedback[];
  practice_brief?: PracticeBrief;
  completion?: SessionCompletion;
};

export async function startScenarioSession(scenarioId: string, profileId?: number): Promise<StartScenarioSessionResult> {
  const response = await apiFetch(`${API_BASE}/api/sessions/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_id: scenarioId, profile_id: profileId })
  });
  if (!response.ok) {
    throw new Error("无法开始场景练习");
  }
  return response.json();
}

export async function getScenarios(
  profileId?: number,
  filters?: { category?: string; role?: string; tier?: string }
): Promise<ScenarioCatalog> {
  const params = new URLSearchParams();
  if (profileId) params.set("profile_id", String(profileId));
  if (filters?.category) params.set("category", filters.category);
  if (filters?.role) params.set("role", filters.role);
  if (filters?.tier) params.set("tier", filters.tier);
  const query = params.toString();
  const url = query ? `${API_BASE}/api/scenarios?${query}` : `${API_BASE}/api/scenarios`;
  const response = await apiFetch(url);
  if (!response.ok) {
    throw new Error("Failed to load scenarios");
  }
  return response.json();
}

export async function getLearningPath(tier?: string, profileId?: number): Promise<LearningPath> {
  const params = new URLSearchParams();
  if (tier) params.set("tier", tier);
  if (profileId) params.set("profile_id", String(profileId));
  const response = await apiFetch(`${API_BASE}/api/scenarios/learning-path?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Failed to load learning path");
  }
  return response.json();
}

export async function addFavorite(scenarioId: string, profileId?: number): Promise<{ status: string }> {
  const response = await apiFetch(`${API_BASE}/api/favorites/${scenarioId}${profileId ? `?profile_id=${profileId}` : ""}`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error("收藏失败");
  }
  return response.json();
}

export async function removeFavorite(scenarioId: string, profileId?: number): Promise<{ status: string; removed: boolean }> {
  const response = await apiFetch(`${API_BASE}/api/favorites/${scenarioId}${profileId ? `?profile_id=${profileId}` : ""}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error("取消收藏失败");
  }
  return response.json();
}

export async function getFavorites(profileId?: number): Promise<{ favorites: Scenario[] }> {
  const response = await apiFetch(`${API_BASE}/api/favorites${profileId ? `?profile_id=${profileId}` : ""}`);
  if (!response.ok) {
    throw new Error("Failed to load favorites");
  }
  return response.json();
}

export async function getSessionHistory(profileId?: number): Promise<{ sessions: SessionHistoryItem[] }> {
  const url = profileId ? `${API_BASE}/api/sessions?profile_id=${profileId}` : `${API_BASE}/api/sessions`;
  const response = await apiFetch(url);
  if (!response.ok) {
    throw new Error("Failed to load session history");
  }
  return response.json();
}

export async function translateText(text: string): Promise<{ text: string; translation_zh: string }> {
  const response = await apiFetch(`${API_BASE}/api/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  if (!response.ok) {
    throw new Error("翻译失败");
  }
  return response.json();
}

// ---------- 注册 / 登录 / 游客 ----------
export type AuthResult = {
  status: string;
  access_token?: string;
  refresh_token?: string;
  token?: string;
  guest_id?: string;
  type?: string;
  user?: { id: number; phone: string };
};

async function authPost(path: string, body: Record<string, unknown>): Promise<AuthResult> {
  const response = await apiFetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    let detail = "请求失败";
    try {
      const payload = await response.json();
      if (payload?.detail) detail = payload.detail;
    } catch {
      // keep default
    }
    throw new Error(detail);
  }
  return response.json();
}

export function authRegister(phone: string, password: string): Promise<AuthResult> {
  return authPost("/api/auth/register", { phone, password });
}

export function authLogin(phone: string, password: string): Promise<AuthResult> {
  return authPost("/api/auth/login", { phone, password });
}

export function authGuest(): Promise<AuthResult> {
  return authPost("/api/auth/guest", {});
}

export function storeAuth(result: AuthResult): void {
  if (result.access_token) {
    localStorage.setItem("speakmate-token", result.access_token);
  } else if (result.token) {
    localStorage.setItem("speakmate-token", result.token);
  }
  if (result.refresh_token) {
    localStorage.setItem("speakmate-refresh-token", result.refresh_token);
  }
}

export function clearAuth(): void {
  localStorage.removeItem("speakmate-token");
  localStorage.removeItem("speakmate-refresh-token");
  try {
    Object.keys(sessionStorage).filter(key => key.startsWith("speakmate-chat:")).forEach(key => sessionStorage.removeItem(key));
  } catch { /* Storage may be unavailable. */ }
}

export function hasAuth(): boolean {
  return Boolean(localStorage.getItem("speakmate-token"));
}

export async function sendUserTurnStream(
  sessionId: number,
  text: string,
  onTextChunk: (chunk: string) => void,
  inputMode: "text" | "voice" = "text"
): Promise<{
  user_turn: ConversationTurn;
  assistant_turn: ConversationTurn;
  inline_feedback: InlineFeedback[];
  hints: string[];
  completion?: SessionCompletion;
  /** 本轮错误报告（后端每轮结束聚合输出） */
  round_error_report?: ErrorReport | null;
  /** 整个会话累计错误报告 */
  session_error_report?: ErrorReport | null;
}> {
  const response = await apiFetch(`${API_BASE}/api/sessions/turn/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text, input_mode: inputMode }),
  });

  if (!response.ok || !response.body) {
    if (response.status === 404) {
      throw new Error("会话已失效，请重新开始练习");
    }
    throw new Error("发送失败，请稍后再试");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let meta: any = null;

  function consumeEvent(event: string) {
    const payload = event.split("\n").filter(line => line.startsWith("data:")).map(line => line.slice(5).trimStart()).join("\n");
    if (!payload || payload === "[DONE]") return;
    let data;
    try { data = JSON.parse(payload); } catch { return; }
    if (data.type === "text") onTextChunk(data.content);
    else if (data.type === "meta") meta = data;
    else if (data.type === "error") throw new Error(data.message || "回复生成失败");
  }
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      // SSE supports LF and CRLF. Consume each complete event as it arrives.
      let boundary;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        consumeEvent(buffer.slice(0, boundary.index).replace(/\r\n/g, "\n"));
        buffer = buffer.slice(boundary.index + boundary[0].length);
      }
      if (done) {
        if (buffer.trim()) consumeEvent(buffer.replace(/\r\n/g, "\n"));
        break;
      }
    }
  } finally { reader.releaseLock(); }

  if (!meta) {
    // Resilience: If meta is missing (e.g. timeout on feedback generation), don't crash.
    // Return empty arrays so the text response is preserved.
    return {
      user_turn: null as any, // handled by caller if needed
      assistant_turn: null as any,
      inline_feedback: [],
      hints: []
    };
  }
  return meta;
}

export async function deleteTurnPair(sessionId: number, userTurnId: number): Promise<{
  turns: ConversationTurn[];
  feedback_history: InlineFeedback[];
}> {
  const response = await apiFetch(`${API_BASE}/api/sessions/${sessionId}/turn-pairs/${userTurnId}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error("Failed to delete turn pair");
  }
  return response.json();
}
export async function getSessionTurns(
  sessionId: number
): Promise<{ session: PracticeSession; turns: ConversationTurn[] }> {
  const response = await apiFetch(`${API_BASE}/api/sessions/${sessionId}/turns`);
  if (!response.ok) {
    throw new Error("加载历史对话失败");
  }
  return response.json();
}
export async function clearSessionHistory(sessionId: number): Promise<void> {
  const response = await apiFetch(`${API_BASE}/api/sessions/${sessionId}/history`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error("清空会话失败");
  }
}

export async function completeSession(
  sessionId: number,
  completionType: "manual" | "agent_suggested" = "manual"
): Promise<{
  session: PracticeSession;
  plan_day: PlanDay;
  completion: SessionCompletion;
}> {
  const response = await apiFetch(`${API_BASE}/api/sessions/${sessionId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ completion_type: completionType })
  });
  if (!response.ok) {
    throw new Error("Failed to complete session");
  }
  return response.json();
}

export async function getPrompts(): Promise<{ prompts: Array<{ name: string; content: string; updated_at: string }> }> {
  const response = await apiFetch(`${API_BASE}/api/prompts`);
  if (!response.ok) {
    throw new Error("Failed to get prompts");
  }
  return response.json();
}

export async function updatePrompt(name: string, content: string): Promise<void> {
  const response = await apiFetch(`${API_BASE}/api/prompts/${name}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content })
  });
  if (!response.ok) {
    throw new Error("Failed to update prompt");
  }
}

export async function requestLanguageSupport(input: {
  mode: LanguageSupportMode;
  text: string;
  context?: string;
}): Promise<LanguageSupportResult> {
  const response = await apiFetch(`${API_BASE}/api/language-support`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, context: input.context || "" })
  });
  if (!response.ok) {
    throw new Error("Failed to get language support");
  }
  return response.json();
}

let activeAudio: HTMLAudioElement | null = null;
let audioGeneration = 0;
let stopAudioMeter: (() => void) | null = null;

export type TTSVoice = {
  id: string;
  name: string;
  gender: string;
  accent: string;
  description: string;
  default?: boolean;
};

const VOICE_STORAGE_KEY = "speakmate-voice";

/** 读取用户在设置中选择的陪练老师音色（无选择时返回 null，用后端默认音色）。 */
export function getSelectedVoice(): string | null {
  return localStorage.getItem(VOICE_STORAGE_KEY);
}

/** 保存用户选择的陪练老师音色。 */
export function setSelectedVoice(voiceId: string): void {
  localStorage.setItem(VOICE_STORAGE_KEY, voiceId);
}

/** 获取可选陪练老师音色列表（含后端当前默认音色）。 */
export async function getTTSVoices(): Promise<{ voices: TTSVoice[]; default_voice: string }> {
  const response = await apiFetch(`${API_BASE}/api/tts/voices`);
  if (!response.ok) {
    throw new Error("Failed to load voices");
  }
  return response.json();
}

/** 停止当前正在播放的任意音频（TTS / 语音条），用于切换界面时中断播放。 */
export function stopActiveAudio(): void {
  audioGeneration++;
  stopAudioMeter?.(); stopAudioMeter = null;
  if (activeAudio) {
    activeAudio.pause();
    activeAudio = null;
  }
}

/** 播放一段已生成的音频 URL（语音条），与 TTS 共用同一全局播放句柄。 */
export function playAudioFromUrl(url: string): Promise<void> {
  stopActiveAudio();
  const audio = new Audio(url);
  activeAudio = audio;
  const stopMeter = monitorAudio(audio);
  stopAudioMeter = stopMeter;
  return new Promise((resolve) => {
    const finish = () => {
      stopMeter();
      if (activeAudio === audio) { activeAudio = null; stopAudioMeter = null; }
      resolve();
    };
    audio.onended = finish;
    audio.onpause = finish;
    audio.onerror = finish;
    audio.play().catch(finish);
  });
}

export async function playTTS(text: string, voice?: string): Promise<void> {
  prepareAudioMeter();
  stopActiveAudio();
  const generation = audioGeneration;
  const body: { text: string; voice?: string } = { text };
  if (voice) body.voice = voice;
  const response = await apiFetch(`${API_BASE}/api/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error("Failed to synthesize speech");
  }
  const blob = await response.blob();
  if (generation !== audioGeneration) return;
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  activeAudio = audio;
  const stopMeter = monitorAudio(audio);
  stopAudioMeter = stopMeter;

  return new Promise((resolve, reject) => {
    const finish = () => {
      stopMeter();
      if (activeAudio === audio) { activeAudio = null; stopAudioMeter = null; }
      URL.revokeObjectURL(url);
      resolve();
    };
    audio.onended = finish;
    audio.onpause = finish;
    audio.onerror = (e) => {
      stopMeter();
      if (activeAudio === audio) { activeAudio = null; stopAudioMeter = null; }
      URL.revokeObjectURL(url);
      reject(e);
    };
    audio.play().catch(error => { reject(error); finish(); });
  });
}


// ── App 版本检查（供「检查更新」使用） ──────────────────────────
export type AppVersionInfo = {
  version_code: number;
  version_name: string;
  apk_url: string;
  changelog?: string;
  updated_at?: string;
};

export async function getAppVersion(): Promise<AppVersionInfo> {
  const response = await apiFetch(`${API_BASE}/api/app/version`);
  if (!response.ok) throw new Error("检查更新失败");
  return response.json();
}

export type Account = { username: string; avatar: string; is_guest: boolean; avatars: Record<string, string> };
export async function getAccount(): Promise<Account> {
  const response = await apiFetch(`${API_BASE}/api/auth/me`);
  if (!response.ok) {
    if (response.status === 404) throw new Error("账号接口尚未更新，请重启后端后重试");
    if (response.status === 429) throw new Error("请求较多，请稍后点击重新加载");
    throw new Error("账号信息加载失败，请重试");
  }
  return response.json();
}
export async function saveAccount(username: string, avatar: string): Promise<Account> {
  const response = await apiFetch(`${API_BASE}/api/auth/me`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, avatar }),
  });
  if (!response.ok) throw new Error("保存失败，请稍后重试");
  return response.json();
}
