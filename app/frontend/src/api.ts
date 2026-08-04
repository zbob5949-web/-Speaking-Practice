import type { ConversationTurn, GrowthSummary, InlineFeedback, LanguageSupportMode, LanguageSupportResult, LearningPath, OnboardingResponse, PlanDay, PracticeBrief, PracticeSession, Profile, Scenario, ScenarioCatalog, SessionCompletion, SessionHistoryItem, TodayStrategy } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
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
  const response = await fetch(API_BASE + "/api/asr", {
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
  const response = await fetch(`${API_BASE}/api/onboarding`, {
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
  const response = await fetch(`${API_BASE}/api/profiles`);
  return response.json();
}

export async function deleteProfile(profileId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/api/profiles/${profileId}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error("Failed to delete profile");
  }
}

export async function runDueReviews(): Promise<{ status: string; processed_days: number }> {
  const res = await fetch(`${API_BASE}/api/daily-review/run-due`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to run due reviews");
  return res.json();
}

export async function getCurrentLearningState(profileId?: number): Promise<OnboardingResponse> {
  const url = profileId ? `${API_BASE}/api/current?profile_id=${profileId}` : `${API_BASE}/api/current`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("No current learning state");
  }
  return response.json();
}

export async function getGrowthSummary(profileId?: number): Promise<GrowthSummary> {
  const url = profileId ? `${API_BASE}/api/growth/summary?profile_id=${profileId}` : `${API_BASE}/api/growth/summary`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Failed to get growth summary");
  }
  return response.json();
}

export async function getTodayStrategy(profileId?: number): Promise<TodayStrategy> {
  const url = profileId ? `${API_BASE}/api/today/strategy?profile_id=${profileId}` : `${API_BASE}/api/today/strategy`;
  const response = await fetch(url);
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
  const response = await fetch(`${API_BASE}/api/sessions/start`, {
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
  const response = await fetch(`${API_BASE}/api/sessions/start`, {
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
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Failed to load scenarios");
  }
  return response.json();
}

export async function getLearningPath(tier?: string, profileId?: number): Promise<LearningPath> {
  const params = new URLSearchParams();
  if (tier) params.set("tier", tier);
  if (profileId) params.set("profile_id", String(profileId));
  const response = await fetch(`${API_BASE}/api/scenarios/learning-path?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Failed to load learning path");
  }
  return response.json();
}

export async function addFavorite(scenarioId: string, profileId: number): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/api/favorites/${scenarioId}?profile_id=${profileId}`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error("收藏失败");
  }
  return response.json();
}

export async function removeFavorite(scenarioId: string, profileId: number): Promise<{ status: string; removed: boolean }> {
  const response = await fetch(`${API_BASE}/api/favorites/${scenarioId}?profile_id=${profileId}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error("取消收藏失败");
  }
  return response.json();
}

export async function getFavorites(profileId: number): Promise<{ favorites: Scenario[] }> {
  const response = await fetch(`${API_BASE}/api/favorites?profile_id=${profileId}`);
  if (!response.ok) {
    throw new Error("Failed to load favorites");
  }
  return response.json();
}

export async function getSessionHistory(profileId?: number): Promise<{ sessions: SessionHistoryItem[] }> {
  const url = profileId ? `${API_BASE}/api/sessions?profile_id=${profileId}` : `${API_BASE}/api/sessions`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Failed to load session history");
  }
  return response.json();
}

export async function translateText(text: string): Promise<{ text: string; translation_zh: string }> {
  const response = await fetch(`${API_BASE}/api/translate`, {
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
  const response = await fetch(`${API_BASE}${path}`, {
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
}

export function hasAuth(): boolean {
  return Boolean(localStorage.getItem("speakmate-token"));
}

export async function sendUserTurnStream(
  sessionId: number,
  text: string,
  onTextChunk: (chunk: string) => void
): Promise<{
  user_turn: ConversationTurn;
  assistant_turn: ConversationTurn;
  inline_feedback: InlineFeedback[];
  hints: string[];
  completion?: SessionCompletion;
}> {
  const response = await fetch(`${API_BASE}/api/sessions/turn/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text }),
  });

  if (!response.ok || !response.body) {
    throw new Error("Failed to send turn");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let meta: any = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || ""; // Keep the last incomplete part in the buffer
    
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === "text") {
            onTextChunk(data.content);
          } else if (data.type === "meta") {
            meta = data;
          }
        } catch (e) {
          // ignore incomplete json
        }
      }
    }
  }
  
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
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/turn-pairs/${userTurnId}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error("Failed to delete turn pair");
  }
  return response.json();
}
export async function clearSessionHistory(sessionId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/history`, {
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
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/complete`, {
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
  const response = await fetch(`${API_BASE}/api/prompts`);
  if (!response.ok) {
    throw new Error("Failed to get prompts");
  }
  return response.json();
}

export async function updatePrompt(name: string, content: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/prompts/${name}`, {
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
  const response = await fetch(`${API_BASE}/api/language-support`, {
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
  const response = await fetch(`${API_BASE}/api/tts/voices`);
  if (!response.ok) {
    throw new Error("Failed to load voices");
  }
  return response.json();
}

/** 停止当前正在播放的任意音频（TTS / 语音条），用于切换界面时中断播放。 */
export function stopActiveAudio(): void {
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
  return new Promise((resolve) => {
    const finish = () => {
      if (activeAudio === audio) activeAudio = null;
      resolve();
    };
    audio.onended = finish;
    audio.onpause = finish;
    audio.onerror = finish;
    audio.play().catch(finish);
  });
}

export async function playTTS(text: string, voice?: string): Promise<void> {
  const body: { text: string; voice?: string } = { text };
  if (voice) body.voice = voice;
  const response = await fetch(`${API_BASE}/api/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error("Failed to synthesize speech");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  activeAudio = audio;

  return new Promise((resolve, reject) => {
    const finish = () => {
      if (activeAudio === audio) activeAudio = null;
      URL.revokeObjectURL(url);
      resolve();
    };
    audio.onended = finish;
    audio.onpause = finish;
    audio.onerror = (e) => {
      if (activeAudio === audio) activeAudio = null;
      URL.revokeObjectURL(url);
      reject(e);
    };
    audio.play().catch(reject);
  });
}

