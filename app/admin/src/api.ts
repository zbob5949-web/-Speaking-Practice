const TOKEN_KEY = "speakmate-admin-token";
const PHONE_KEY = "speakmate-admin-phone";

export type TableColumn = {
  name: string;
  kind: string;
  label: string;
  required: boolean;
  readonly: boolean;
  searchable: boolean;
  textarea: boolean;
  options: string[];
};

export type TableMeta = {
  table: string;
  label: string;
  columns: TableColumn[];
};

export type Paged<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type Row = Record<string, unknown>;

export type AdminUser = {
  username: string;
  avatar: string;
  id: number;
  phone: string;
  role: string;
  is_active: boolean;
  is_super_admin: boolean;
  last_login_ip?: string | null;
  last_login?: string | null;
  created_at?: string | null;
};

export type SessionRow = {
  id: number;
  plan_day_id?: number | null;
  scenario_id?: string | null;
  profile_id?: number | null;
  day_index?: number | null;
  topic?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  overall_score?: number | null;
  turn_count?: number;
  feedback_count?: number;
  finished?: boolean;
  summary?: unknown;
};

export type SessionDetail = SessionRow & {
  turns: Array<{ id: number; turn_index: number; speaker: string; text: string; created_at?: string }>;
  feedback: Array<{
    id: number;
    turn_id?: number | null;
    feedback_type: string;
    feedback_text?: string | null;
    original_fragment?: string | null;
    better_expression?: string | null;
    reason_zh?: string | null;
    example_sentence?: string | null;
    severity?: string | null;
  }>;
};

export type PromptItem = { name: string; content_length: number; updated_at?: string };

export type DashboardData = {
  users: { total: number; admin: number; active: number; new_today: number; logged_in_7d: number };
  sessions: { total: number; finished: number; in_progress: number; today: number; avg_score: number };
  conversations: { turns_total: number; turns_today: number; feedback_total: number };
  libraries: { error_bank: number; expression_bank: number; favorites: number };
  hot_scenarios: Array<{ scenario_id: string; count: number }>;
  recent_sessions: Array<{
    id: number;
    scenario_id: string | null;
    topic: string | null;
    started_at: string | null;
    ended_at: string | null;
    overall_score: number | null;
    turn_count: number;
  }>;
};

export type TrendPoint = {
  date: string;
  sessions: number;
  turns: number;
  feedback: number;
  new_users: number;
  avg_score: number | null;
};

export type TrendsData = {
  days: number;
  timeline: TrendPoint[];
  summary: {
    sessions_recent: number;
    sessions_previous: number;
    turns_recent: number;
    turns_previous: number;
    sessions_change_pct: number | null;
    turns_change_pct: number | null;
  };
};

export type ReportsData = {
  error_type_distribution: Array<{ error_type: string; count: number }>;
  feedback_type_distribution: Array<{ feedback_type: string; count: number }>;
  severity_distribution: Array<{ severity: string; count: number }>;
  hot_scenarios: Array<{ scenario_id: string; count: number; avg_score: number | null }>;
  level_distribution: Array<{ level: string | null; count: number }>;
  score_distribution: { excellent: number; good: number; pass: number; poor: number };
  review_coverage: { total_errors: number; reviewed_errors: number; review_rate: number };
};

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? "";
}

export function setAdminToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAdminToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function getAdminPhone(): string {
  return localStorage.getItem(PHONE_KEY) ?? "";
}

export function setAdminPhone(phone: string): void {
  localStorage.setItem(PHONE_KEY, phone);
}

export function clearAdminPhone(): void {
  localStorage.removeItem(PHONE_KEY);
}

function dispatchUnauthorized(): void {
  clearAdminToken();
  window.dispatchEvent(new Event("admin:unauthorized"));
}

async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  let payload: unknown = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = null;
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      dispatchUnauthorized();
    }
    const detail =
      (payload as { detail?: string; msg?: string } | null)?.detail ??
      (payload as { msg?: string } | null)?.msg;
    throw new Error(detail || `请求失败（${response.status}）`);
  }

  if (payload && typeof (payload as { code?: number }).code === "number") {
    const envelope = payload as { code: number; msg?: string; data: T };
    if (envelope.code !== 200) {
      throw new Error(envelope.msg || "请求失败");
    }
    return envelope.data;
  }
  return payload as T;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers });
  return parseResponse<T>(response);
}

export function adminGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function adminSend<T>(path: string, method: "POST" | "PUT" | "DELETE", body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export async function adminLogin(phone: string, password: string): Promise<{ access_token: string }> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, password }),
  });
  const data = await parseResponse<{ access_token?: string; token?: string }>(response);
  const token = data.access_token || data.token;
  if (!token) throw new Error("登录失败：没有返回 access_token");
  return { access_token: token };
}
