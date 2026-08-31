import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi, type Mock } from "vitest";
import { addFavorite, authGuest, authLogin, authRegister, clearAuth, completeSession, createOnboarding, deleteTurnPair, getCurrentLearningState, getFavorites, getGrowthSummary, getLearningPath, getProfiles, getPrompts, getScenarios, getSelectedVoice, getSessionHistory, getTTSVoices, getTodayStrategy, hasAuth, playAudioFromUrl, playTTS, removeFavorite, runDueReviews, requestLanguageSupport, sendUserTurnStream, setSelectedVoice, startScenarioSession, startSession, stopActiveAudio, storeAuth, transcribeAudio, translateText, updatePrompt } from "./api";
import App from "./App";

vi.mock("./api", () => ({
  addFavorite: vi.fn(),
  removeFavorite: vi.fn(),
  authLogin: vi.fn(),
  authRegister: vi.fn(),
  authGuest: vi.fn(),
  storeAuth: vi.fn(),
  clearAuth: vi.fn(),
  hasAuth: vi.fn(),
  createOnboarding: vi.fn(),
  getCurrentLearningState: vi.fn(),
  getGrowthSummary: vi.fn(),
  getTodayStrategy: vi.fn(),
  getProfiles: vi.fn(),
  getPrompts: vi.fn(),
  getScenarios: vi.fn(),
  getLearningPath: vi.fn(),
  getFavorites: vi.fn(),
  getSessionHistory: vi.fn(),
  startSession: vi.fn(),
  startScenarioSession: vi.fn(),
  completeSession: vi.fn(),
  deleteTurnPair: vi.fn(),
  sendUserTurnStream: vi.fn(),
  playTTS: vi.fn(),
  playAudioFromUrl: vi.fn(),
  stopActiveAudio: vi.fn(),
  transcribeAudio: vi.fn(),
  updatePrompt: vi.fn(),
  runDueReviews: vi.fn(),
  getTTSVoices: vi.fn(),
  getSelectedVoice: vi.fn(),
  setSelectedVoice: vi.fn(),
  requestLanguageSupport: vi.fn(),
  translateText: vi.fn(),
}));

const mockScenario = {
  id: "airport-check-in",
  title: "Airport check-in",
  category: "出行",
  background: "You are at the check-in counter at an international airport.",
  npc_role: "Airline check-in agent",
  learner_role: "Passenger",
  objective: "Complete check-in and confirm baggage details.",
  bands: [],
  difficulty: { level: "A2", vocabulary_range: "", sentence_complexity: "", target_functions: [] }
};

const mockCatalog = {
  scenarios: [mockScenario],
  categories: ["出行"],
  roles: ["Airline check-in agent"],
  tiers: [
    { id: "beginner", label: "小白", levels: ["A1", "A2"] },
    { id: "intermediate", label: "中级", levels: ["B1", "B2"] },
    { id: "advanced", label: "大神", levels: ["C1"] }
  ],
  derived_tier: "beginner"
};

beforeEach(() => {
  vi.resetAllMocks();
  localStorage.setItem("speakmate-token", "test-token");
  localStorage.removeItem("speakmate-last-scenario");
  localStorage.removeItem("speakmate-last-path");
  localStorage.removeItem("speakmate-last-view");
  localStorage.removeItem("speakmate-tts-muted");
  localStorage.removeItem("speakmate-voice");
  (getTTSVoices as Mock).mockResolvedValue({ voices: [], default_voice: "en-US-JennyNeural" });
  (getSelectedVoice as Mock).mockReturnValue(null);
  (setSelectedVoice as Mock).mockImplementation(() => undefined);
  (hasAuth as Mock).mockImplementation(() => Boolean(localStorage.getItem("speakmate-token")));
  (clearAuth as Mock).mockImplementation(() => {
    localStorage.removeItem("speakmate-token");
    localStorage.removeItem("speakmate-refresh-token");
  });
  (storeAuth as Mock).mockImplementation(() => undefined);
  (authLogin as Mock).mockResolvedValue({ status: "success", access_token: "test-token", refresh_token: "test-refresh" });
  (authRegister as Mock).mockResolvedValue({ status: "success", access_token: "test-token", refresh_token: "test-refresh" });
  (authGuest as Mock).mockResolvedValue({ status: "success", token: "guest-token", guest_id: "guest-1", type: "guest" });
  Element.prototype.scrollIntoView = vi.fn();
  (runDueReviews as Mock).mockResolvedValue({ status: "success", processed_days: 0 });
  (getScenarios as Mock).mockResolvedValue(mockCatalog);
  (getLearningPath as Mock).mockResolvedValue({
    tier: "intermediate",
    level: "B1",
    levels: ["B1", "B2"],
    path: [mockScenario]
  });
  (stopActiveAudio as Mock).mockImplementation(() => undefined);
  (playAudioFromUrl as Mock).mockResolvedValue(undefined);
  (transcribeAudio as Mock).mockResolvedValue({ text: "I want to check in, please.", provider: "mock", confidence: 1, filename: "mock.webm" });
  (getFavorites as Mock).mockResolvedValue({ favorites: [] });
  (getSessionHistory as Mock).mockResolvedValue({ sessions: [] });
  (translateText as Mock).mockResolvedValue({ text: "Today we will practice your self-introduction.", translation_zh: "今天我们将练习自我介绍。" });
  (startScenarioSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 0, topic: "Airport check-in" },
    turns: [{
      id: 1,
      session_id: 1,
      turn_index: 1,
      speaker: "assistant",
      text: "Let's practice: Airport check-in. You are at the check-in counter at an international airport. Start with your first answer."
    }],
    plan_day: null,
    practice_brief: {
      title: "Airport check-in",
      user_visible_goal: "Complete check-in and confirm baggage details.",
      npc_role: "Airline check-in agent",
      scenario_setup: "You are at the check-in counter at an international airport.",
      objective: "Complete check-in and confirm baggage details.",
      difficulty: "A2"
    }
  });
  (getGrowthSummary as Mock).mockResolvedValue({
    latest_review: null,
    recent_reviews: [],
    active_memory: [],
    active_adjustments: []
  });
  (getTodayStrategy as Mock).mockResolvedValue({
    today_strategy: {
      focus: "补充旅行场景中的关键信息",
      reason: "基于长期记忆和最近复盘",
      success_criteria: ["说明时间", "说明对象"]
    },
    training_decision: {
      decision_type: "review_weakness",
      reason_zh: "你最近经常漏掉时间和对象。",
      selected_memory_ids: [3],
      selected_review_ids: [12],
      brief_instruction: "生成酒店入住场景，NPC 必须追问日期、姓名、房型。",
      difficulty_adjustment: "same",
      should_refresh_brief: true
    },
    memory_influence: [
      {
        memory_id: 3,
        category: "weakness",
        content: "用户经常漏掉时间和对象。",
        influence_type: "npc_behavior",
        instruction: "用户没说入住日期时，NPC 必须追问。",
        reason_zh: "这是最近重复出现的细节遗漏问题。"
      }
    ],
    coach_explanation_zh: "今天先集中练补充关键信息。",
    recommended_actions: [],
    risk_flags: [],
    practice_brief: practiceBrief,
    agent_run_id: 1
  });
  (getPrompts as Mock).mockResolvedValue({ prompts: [] });
  (requestLanguageSupport as Mock).mockResolvedValue({
    mode: "define",
    text: "expiry",
    meaning_zh: "有效期，到期日",
    scene_note_zh: "在支付或酒店场景里，通常指信用卡有效期。",
    example_sentence: "What is the expiry date on your card?"
  });
  (completeSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "Self-introduction" },
    plan_day: { ...onboardingResult.plan[0], status: "completed" },
    completion: {
      status: "completed",
      can_suggest_completion: false,
      suggestion_reason_zh: "",
      completed_summary: {
        status: "completed",
        completion_type: "manual",
        summary_zh: "今天你完成了酒店入住练习。",
        strength_zh: "你能保持对话推进。",
        next_focus_zh: "下次继续补充时间和对象。",
        reusable_sentences: ["I'd like to book a room."],
        confidence: 0.75,
        score: 95,
        score_detail_zh: "本轮共发现 2 处表达或单词错误，扣除 5 分。"
      }
    }
  });
});

afterEach(() => {
  cleanup();
});

const onboardingResult = {
  profile: {
    id: 1,
    learning_goal: "Improve speaking fluency for daily conversations",
    total_days: 14,
    daily_minutes: 15,
    current_level: "IELTS 6.5, speaking 6"
  },
  plan: [
    {
      id: 1,
      day_index: 1,
      topic: "Self-introduction",
      scenario: "Introduce yourself to a hotel receptionist.",
      objective: "Give a concise travel self-introduction.",
      status: "pending"
    },
    {
      id: 2,
      day_index: 2,
      topic: "Hotel check-in",
      scenario: "Ask about room details at a hotel front desk.",
      objective: "Ask focused travel check-in questions.",
      status: "pending"
    }
  ]
};

const startedSession = {
  session: { id: 1, day_index: 1, topic: "Self-introduction" },
  turns: [{
    id: 1,
    session_id: 1,
    turn_index: 1,
    speaker: "assistant",
    text: "Today we will practice your self-introduction."
  }]
};

const practiceBrief = {
  title: "Speak about travel plans",
  user_visible_goal: "Use one clear travel-plan sentence before the roleplay ends.",
  npc_role: "Hotel receptionist",
  scenario_setup: "You are checking in at a hotel after a long trip.",
  conversation_objective: "Explain your reservation and ask one practical question.",
  target_expressions: ["I'm here to check in.", "Could you help me with...?"],
  avoid_patterns: ["I am responsible for make"],
  difficulty: "B1",
  coach_notes: "Push the learner to give concrete travel details."
};

const sentTurnResult = {
  user_turn: {
    id: 2,
    session_id: 1,
    turn_index: 2,
    speaker: "user",
    text: "I want to check in, please."
  },
  assistant_turn: {
    id: 3,
    session_id: 1,
    turn_index: 3,
    speaker: "assistant",
    text: "Great. Could you add your reservation name?"
  },
  inline_feedback: []
};

test("starts a new lesson in Learn mode before opening the chat", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    practice_brief: practiceBrief
  });

  render(<App />);

  expect(await screen.findByText("Speak about travel plans")).toBeTruthy();
  expect(screen.getByLabelText("课程简报头部")).toBeTruthy();
  expect(screen.queryByText("今日练习依据")).toBeNull();
  expect(screen.getAllByText("Use one clear travel-plan sentence before the roleplay ends.")).toHaveLength(1);
  expect(screen.getByText("Hotel receptionist")).toBeTruthy();
  expect(screen.getByText("You are checking in at a hotel after a long trip.")).toBeTruthy();
  expect(screen.getByText("可直接套用的表达")).toBeTruthy();
  expect(screen.getByText("I'm here to check in.")).toBeTruthy();
  expect(screen.queryByLabelText("对话练习")).toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "开始对话练习" }));

  expect(await screen.findByLabelText("对话练习")).toBeTruthy();
  expect(screen.getByLabelText("实时纠错")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "查看场景提示" }));

  expect(await screen.findByLabelText("课程简报")).toBeTruthy();
  expect(screen.getByText("Speak about travel plans")).toBeTruthy();
  expect(screen.queryByLabelText("对话练习")).toBeNull();
});

test("renders rich lesson pack materials in practice room", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "Hotel delay" },
    turns: [{ id: 1, session_id: 1, turn_index: 1, speaker: "assistant", text: "Good evening." }],
    practice_brief: {
      title: "Hotel delay check-in",
      user_visible_goal: "Explain a delayed flight.",
      npc_role: "Hotel receptionist",
      scenario_setup: "You arrived late because your flight was delayed.",
      conversation_objective: "Explain the problem and ask whether your room is still available.",
      lesson_focus: "Past-tense storytelling plus polite requests",
      task_steps: ["Explain what happened", "Ask about the room"],
      target_expressions: [
        {
          expression: "My flight was delayed.",
          meaning_zh: "我的航班延误了。",
          example: "My flight was delayed by two hours.",
          when_to_use: "explaining why you arrived late"
        }
      ],
      sentence_frames: ["I arrived late because..."],
      model_dialogue: ["NPC: Good evening. How can I help?", "Learner: My flight was delayed."],
      common_mistakes: [{ mistake: "I am arrive late.", better: "I arrived late.", reason_zh: "用过去式 arrived。" }],
      rubric: ["Clear reason", "Polite request"],
      stretch_goal: "Add one detail about the delay.",
      avoid_patterns: ["I am arrive"],
      difficulty: "normal",
      coach_notes: "Push past tense."
    },
  });

  render(<App />);

  expect(await screen.findByText("Past-tense storytelling plus polite requests")).toBeTruthy();
  expect(screen.getByText("Explain what happened")).toBeTruthy();
  expect(screen.getByText("My flight was delayed.")).toBeTruthy();
  expect(screen.getByText("我的航班延误了。")).toBeTruthy();
  expect(screen.queryByText("NPC: Good evening. How can I help?")).toBeNull();
  expect(screen.queryByText("I am arrive late.")).toBeNull();
  expect(screen.queryByText("Clear reason")).toBeNull();
});

test("calls runDueReviews on mount", async () => {
  (getCurrentLearningState as Mock).mockRejectedValue(new Error("No learning plan"));
  (getProfiles as Mock).mockResolvedValue({ profiles: [] });

  render(<App />);

  await waitFor(() => {
    expect(runDueReviews).toHaveBeenCalled();
  });
});

test("shows growth summary from teacher memory", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    practice_brief: practiceBrief
  });
  (getGrowthSummary as Mock).mockResolvedValue({
    latest_review: {
      id: 1,
      review_date: "2026-06-22",
      user_report: {
          summary: "You practiced travel check-in questions.",
          next_focus: "Use clearer reservation details."
      },
      structured_analysis: {
              weaknesses: ["unclear reservation details"],
        strengths: ["kept speaking"]
      }
    },
    recent_reviews: [],
    active_memory: [
      {
        id: 1,
        category: "weakness",
          content: "Often gives vague travel details",
        confidence: 0.88
      }
    ],
    active_adjustments: [
      {
        id: 1,
          title: "Practice structured travel answers",
          rationale: "Recent answers lack clear details",
          instruction: "Start with greeting, reservation name, request."
      }
    ]
  });

  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "成长" }));

  expect(await screen.findByText("You practiced travel check-in questions.")).toBeTruthy();
  expect(screen.getByText("Use clearer reservation details.")).toBeTruthy();
  expect(screen.getByText("Often gives vague travel details")).toBeTruthy();
  expect(screen.getByText("Practice structured travel answers")).toBeTruthy();
  expect(screen.getByText("Start with greeting, reservation name, request.")).toBeTruthy();
});

test("renders guided onboarding form first", async () => {
  (getCurrentLearningState as Mock).mockRejectedValue(new Error("No learning plan"));
  (getProfiles as Mock).mockResolvedValue({ profiles: [] });

  render(<App />);

  expect(await screen.findByText("SpeakMate 场景口语陪练")).toBeTruthy();
  expect(screen.getByText("创建你的口语练习计划")).toBeTruthy();
  expect(screen.getByText("按场景对话 · 实时语法纠错 · 难度随水平自适应")).toBeTruthy();
  expect(screen.getByLabelText("首次设置表单")).toBeTruthy();
});

test("starts the daily practice immediately after onboarding", async () => {
  (getCurrentLearningState as Mock).mockRejectedValue(new Error("No learning plan"));
  (getProfiles as Mock).mockResolvedValue({ profiles: [] });
  (createOnboarding as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "Self-introduction" },
    turns: [{
      id: 1,
      session_id: 1,
      turn_index: 1,
      speaker: "assistant",
      text: "Today we will practice your self-introduction."
    }]
  });

  render(<App />);
  fireEvent.click(await screen.findByText("生成计划"));

  expect(await screen.findByText("今日场景")).toBeTruthy();
  expect(screen.getByText("Today we will practice your self-introduction.")).toBeTruthy();
  expect(screen.getByLabelText("对话练习")).toBeTruthy();
  expect(screen.queryByText("Current goal")).toBeNull();
  expect(screen.queryByText("Practice Setup")).toBeNull();
  expect(screen.queryByText("Recent Feedback")).toBeNull();
  expect(screen.queryByText("IELTS 6.5, speaking 6")).toBeNull();
  expect(screen.queryByText("Next practice blocks")).toBeNull();
  expect(screen.queryByText(/Goal:/)).toBeNull();
  expect(screen.queryByText(/Level:/)).toBeNull();
  expect(screen.queryByText(/Time:/)).toBeNull();
  expect(screen.queryByText("Resume today")).toBeNull();
  expect(screen.getByRole("button", { name: "我的" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "成长" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Review" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Memory" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Studio" })).toBeNull();
  expect(screen.queryByText("Learning Configuration")).toBeNull();
});

test("loads existing learning state directly into practice", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "Self-introduction" },
    turns: [{
      id: 1,
      session_id: 1,
      turn_index: 1,
      speaker: "assistant",
      text: "Today we will practice your self-introduction."
    }]
  });

  render(<App />);

  expect(await screen.findByText("今日场景")).toBeTruthy();
  expect(screen.queryByText("Set up your local English coaching plan")).toBeNull();
  expect(screen.queryByText("Improve speaking fluency for daily conversations")).toBeNull();
  expect(screen.queryByText("IELTS 6.5, speaking 6")).toBeNull();
});

test("renders practice as a minimal chat workspace", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    turns: [
      ...startedSession.turns,
      {
        id: 2,
        session_id: 1,
        turn_index: 2,
        speaker: "user",
        text: "I want to check in, please."
      }
    ]
  });

  const { container } = render(<App />);

  expect(await screen.findByText("今日场景")).toBeTruthy();
  expect(screen.getAllByText("Self-introduction").length).toBeGreaterThan(0);
  expect(screen.getByLabelText("对话练习")).toBeTruthy();
  expect(screen.getByLabelText("对话输入区")).toBeTruthy();
  expect(screen.getByLabelText("实时纠错")).toBeTruthy();
  expect(container.querySelector(".message-bubble-assistant")).toBeTruthy();
  expect(container.querySelector(".message-avatar-assistant")).toBeTruthy();
  expect(container.querySelector(".message-avatar-assistant")?.textContent).toContain("A");
  expect(container.querySelector(".message-avatar-user")?.textContent).toContain("我");
  expect(container.querySelectorAll(".message-actions").length).toBeGreaterThan(0);
  expect(container.querySelector(".message-row > .message-icon-button")).toBeNull();
  expect(screen.getByRole("button", { name: "发送" })).toBeTruthy();
  expect(screen.queryByText("Coach")).toBeNull();
  expect(screen.queryByRole("heading", { name: "Practice Room" })).toBeNull();
  expect(screen.queryByText("Give a concise travel self-introduction.")).toBeNull();
  expect(screen.queryByText("Use WeChat voice input or type directly, then confirm the text before sending.")).toBeNull();
});

test("shows the recording composer without legacy voice controls", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue(startedSession);

  render(<App />);

  await screen.findByText("今日场景");
  expect(screen.queryByRole("button", { name: "Start Recording" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Stop Recording" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Replay AI Voice" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Test Voice" })).toBeNull();
  expect(screen.queryByRole("button", { name: "End Session" })).toBeNull();
  expect(screen.getByPlaceholderText("可以录音转文字，也可以直接输入英文。确认后点击发送。")).toBeTruthy();
});

test("shows goal and level only inside profile page", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (getProfiles as Mock).mockResolvedValue({ profiles: [onboardingResult.profile] });
  (startSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "Self-introduction" },
    turns: [{
      id: 1,
      session_id: 1,
      turn_index: 1,
      speaker: "assistant",
      text: "Today we will practice your self-introduction."
    }]
  });

  render(<App />);

  await screen.findByText("今日场景");
  expect(screen.queryByText(/Improve speaking fluency for daily conversations/)).toBeNull();
  expect(screen.queryByText("IELTS 6.5, speaking 6")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "我的" }));

  expect(await screen.findByText(/Improve speaking fluency for daily conversations/)).toBeTruthy();
  expect(screen.getByText(/IELTS 6.5, speaking 6/)).toBeTruthy();
});

test("renders profile page with favorites, history and settings", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (getProfiles as Mock).mockResolvedValue({ profiles: [onboardingResult.profile] });
  (startSession as Mock).mockResolvedValue(startedSession);

  const { container } = render(<App />);

  await screen.findByText("今日场景");
  fireEvent.click(screen.getByRole("button", { name: "我的" }));

  expect(await screen.findByText("收藏的场景")).toBeTruthy();
  expect(screen.getByText("练习记录")).toBeTruthy();
  expect(screen.queryByText("Advanced")).toBeNull();
  expect(screen.queryByText("Voice")).toBeNull();
  expect(screen.queryByText("Local Data")).toBeNull();
  expect(container.querySelector(".profile-card")).toBeTruthy();
  expect(container.querySelector(".profile-layout")).toBeTruthy();

  // 设置已从「我的」独立出来，放在导航「我的」下面
  fireEvent.click(screen.getByRole("button", { name: "设置" }));
  expect(await screen.findByText("双语展示")).toBeTruthy();
});

test("profile page no longer exposes developer or learning-goal tools", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (getProfiles as Mock).mockResolvedValue({ profiles: [onboardingResult.profile] });
  (startSession as Mock).mockResolvedValue(startedSession);

  render(<App />);

  await screen.findByText("今日场景");
  fireEvent.click(screen.getByRole("button", { name: "我的" }));

  expect(await screen.findByText("收藏的场景")).toBeTruthy();
  expect(screen.queryByText("AI Model")).toBeNull();
  expect(screen.queryByText("Input")).toBeNull();
  expect(screen.queryByRole("button", { name: "Save Settings" })).toBeNull();
  expect(screen.queryByText("Prompt 管理")).toBeNull();
  expect(screen.queryByText("产品流程图")).toBeNull();
  expect(screen.queryByText("conversation_agent_system")).toBeNull();
  expect(screen.queryByText("学习目标")).toBeNull();
  expect(screen.queryByText("新建学习目标")).toBeNull();
  expect(screen.queryByText("Advanced")).toBeNull();
});

test("profile page collapses long favorites/history and shows score with difficulty", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  const favs = Array.from({ length: 5 }, (_, i) => ({
    ...mockScenario,
    id: `fav-${i}`,
    title: `Favorite ${i}`,
    difficulty: { level: i % 2 ? "B1" : "A2", vocabulary_range: "", sentence_complexity: "", target_functions: [] }
  }));
  (getFavorites as Mock).mockResolvedValue({ favorites: favs });
  (getSessionHistory as Mock).mockResolvedValue({
    sessions: [
      {
        id: 1, plan_day_id: null, scenario_id: "airport-check-in", profile_id: 1, day_index: 0,
        topic: "Airport check-in", started_at: "2026-07-01T10:00:00", ended_at: "2026-07-01T10:05:00",
        summary: "{}", overall_score: 4, turn_count: 6, score: 95, difficulty: "B1"
      },
      {
        id: 2, plan_day_id: 1, scenario_id: null, profile_id: 1, day_index: 1,
        topic: "Self-introduction", started_at: "2026-07-02T10:00:00", ended_at: null,
        summary: null, overall_score: null, turn_count: 2, score: null, difficulty: "A2"
      }
    ]
  });

  render(<App />);
  await screen.findByText("今日场景");
  fireEvent.click(screen.getByRole("button", { name: "我的" }));

  expect(await screen.findByText("收藏的场景")).toBeTruthy();
  // 收藏默认折叠：只显示前 3 条，其余收起
  expect(screen.getByText("Favorite 0")).toBeTruthy();
  expect(screen.getByText("Favorite 2")).toBeTruthy();
  expect(screen.queryByText("Favorite 3")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "展开全部（5）" }));
  expect(screen.getByText("Favorite 3")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "收起" }));
  expect(screen.queryByText("Favorite 3")).toBeNull();

  // 练习记录：显示难度等级与本次得分
  expect(screen.getByText(/难度 B1/)).toBeTruthy();
  expect(screen.getByText(/得分 95\/100/)).toBeTruthy();
  expect(screen.getByText(/难度 A2/)).toBeTruthy();
});

test("opens the learning plan from navigation after onboarding", async () => {
  (getCurrentLearningState as Mock).mockRejectedValue(new Error("No learning plan"));
  (getProfiles as Mock).mockResolvedValue({ profiles: [] });
  (createOnboarding as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "Travel self-introduction" },
    turns: [{
      id: 1,
      session_id: 1,
      turn_index: 1,
      speaker: "assistant",
      text: "Today we will practice your self-introduction."
    }]
  });

  render(<App />);
  fireEvent.click(await screen.findByText("生成计划"));
  await screen.findByText("今日场景");
  fireEvent.click(screen.getByRole("button", { name: "场景" }));

  expect(screen.getByText("选择练习场景")).toBeTruthy();
  expect(await screen.findByText("Airport check-in")).toBeTruthy();
});

test("returns to practice from growth", async () => {
  (getCurrentLearningState as Mock).mockRejectedValue(new Error("No learning plan"));
  (getProfiles as Mock).mockResolvedValue({ profiles: [] });
  (createOnboarding as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "Travel self-introduction" },
    turns: [{
      id: 1,
      session_id: 1,
      turn_index: 1,
      speaker: "assistant",
      text: "Today we will practice your self-introduction."
    }]
  });

  render(<App />);
  fireEvent.click(await screen.findByText("生成计划"));

  await waitFor(() => {
    expect(screen.getByText("今日场景")).toBeTruthy();
  });
  expect(screen.getByText("Today we will practice your self-introduction.")).toBeTruthy();
  expect(screen.getByLabelText("对话练习")).toBeTruthy();
});

test("ignores duplicate send clicks while a response is pending", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue(startedSession);
  (sendUserTurnStream as Mock).mockReturnValue(new Promise(() => undefined));

  render(<App />);
  const response = await screen.findByLabelText("输入你的回答");
  fireEvent.change(response, { target: { value: "I want to check in, please." } });

  const sendButton = screen.getByRole("button", { name: "发送" });
  fireEvent.click(sendButton);
  fireEvent.click(sendButton);

  expect(sendUserTurnStream).toHaveBeenCalledTimes(1);
  expect((sendButton as HTMLButtonElement).disabled).toBe(true);
});

test("sends typed text and shows the assistant reply as text and plays audio", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue(startedSession);
  (sendUserTurnStream as Mock).mockImplementation(async (_sessionId: number, _text: string, onTextChunk: (chunk: string) => void) => {
    onTextChunk("Great. Could you add your reservation name?");
    return sentTurnResult;
  });
  (playTTS as Mock).mockResolvedValue(undefined);

  const { container } = render(<App />);
  const response = await screen.findByLabelText("输入你的回答");
  fireEvent.change(response, { target: { value: "I want to check in, please." } });
  fireEvent.click(await screen.findByRole("button", { name: "发送" }));

  await waitFor(() => {
    expect(sendUserTurnStream).toHaveBeenCalledTimes(1);
  });
  expect(screen.getByText("Great. Could you add your reservation name?")).toBeTruthy();
  expect(container.querySelector(".message-avatar-user")).toBeTruthy();
  expect(screen.queryByText("You")).toBeNull();
  
  // Streaming TTS 合并相邻句子后播放，减少句间停顿。
  await waitFor(() => {
    expect(playTTS).toHaveBeenCalledWith("Great. Could you add your reservation name?", undefined);
  });
});

test("renders structured correction feedback as a clear teaching card", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    feedback_history: [{
      id: 10,
      feedback_type: "correction",
      feedback_text: "I need -> I'd like to book: 订酒店场景更自然。",
      original_fragment: "I need",
      better_expression: "I'd like to book",
      reason_zh: "订酒店场景里，用 I'd like to book 更自然。",
      example_sentence: "I'd like to book a non-smoking room for tonight.",
      severity: "major"
    }]
  });

  render(<App />);

  expect(await screen.findByText("你这里的问题")).toBeTruthy();
  expect(screen.getByText("I need")).toBeTruthy();
  expect(screen.getByText("I'd like to book")).toBeTruthy();
  expect(screen.getByText("订酒店场景里，用 I'd like to book 更自然。")).toBeTruthy();
  expect(screen.getByText("I'd like to book a non-smoking room for tonight.")).toBeTruthy();
});

test("no longer shows the inline explain popover on text selection", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    turns: [{
      id: 1,
      session_id: 1,
      turn_index: 1,
      speaker: "assistant",
      text: "I need your credit card expiry date."
    }]
  });
  const selection = {
    toString: () => "expiry",
    rangeCount: 1,
    removeAllRanges: vi.fn()
  };
  vi.spyOn(window, "getSelection").mockReturnValue(selection as unknown as Selection);

  render(<App />);

  expect(await screen.findByText("I need your credit card expiry date.")).toBeTruthy();
  fireEvent.mouseUp(screen.getByLabelText("对话练习"));
  // 内置选中解释插件已移除：选中文本不再弹出「解释中文」
  expect(screen.queryByText(/选中：/)).toBeNull();
  expect(screen.queryByRole("button", { name: "解释中文" })).toBeNull();
  expect(requestLanguageSupport).not.toHaveBeenCalled();
});


test("lets the user manually complete today's practice and shows summary", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    turns: [
      ...startedSession.turns,
      { id: 2, session_id: 1, turn_index: 2, speaker: "user", text: "I want to book a room." }
    ],
    completion: {
      status: "in_progress",
      can_suggest_completion: false,
      suggestion_reason_zh: "",
      completed_summary: null
    }
  });

  render(<App />);

  expect(await screen.findByText("I want to book a room.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "结束今日练习" }));

  expect(await screen.findByLabelText("今日总结")).toBeTruthy();
  expect(screen.getAllByText("今日已完成").length).toBeGreaterThan(0);
  expect(screen.getByText("今天你完成了酒店入住练习。")).toBeTruthy();
  expect(screen.getByText("I'd like to book a room.")).toBeTruthy();
  // 总结卡片展示 100 分制得分与扣分说明
  expect(screen.getByText("95 / 100")).toBeTruthy();
  expect(screen.getByText("本次练习得分：")).toBeTruthy();
  expect(screen.getByText("本轮共发现 2 处表达或单词错误，扣除 5 分。")).toBeTruthy();
  expect(completeSession).toHaveBeenCalledWith(1, "manual");
});

test("shows agent completion suggestion after a turn and allows continuing", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    completion: {
      status: "in_progress",
      can_suggest_completion: false,
      suggestion_reason_zh: "",
      completed_summary: null
    }
  });
  (sendUserTurnStream as Mock).mockImplementation(async (_sessionId: number, _text: string, onTextChunk: (chunk: string) => void) => {
    onTextChunk("Great, you covered the key details.");
    return {
      ...sentTurnResult,
      inline_feedback: [],
      hints: [],
      completion: {
        status: "completion_suggested",
        can_suggest_completion: true,
        suggestion_reason_zh: "今天的核心目标已经基本练到了。",
        completed_summary: null
      }
    };
  });

  render(<App />);

  expect(await screen.findByLabelText("输入你的回答")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("输入你的回答"), { target: { value: "I want to book a room." } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  expect(await screen.findByText("今天可以收束了")).toBeTruthy();
  expect(screen.getByText("今天的核心目标已经基本练到了。")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "继续练一会儿" }));
  expect(screen.queryByText("今天可以收束了")).toBeNull();
});

test("renders vocabulary help feedback when the user asks what a word means", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    feedback_history: [{
      id: 11,
      feedback_type: "language_help",
      feedback_text: "expiry 是有效期、到期日。",
      original_fragment: "expiry",
      reason_zh: "有效期，到期日；在支付场景里常指信用卡有效期。",
      example_sentence: "The expiry date is 08/27."
    }]
  });

  render(<App />);

  expect(await screen.findByText("词义解答")).toBeTruthy();
  expect(screen.getByText("expiry")).toBeTruthy();
  expect(screen.getByText("有效期，到期日；在支付场景里常指信用卡有效期。")).toBeTruthy();
  expect(screen.getByText("The expiry date is 08/27.")).toBeTruthy();
});

test("replays an assistant message from its speaker button", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "Self-introduction" },
    turns: [
      {
        id: 1,
        session_id: 1,
        turn_index: 1,
        speaker: "assistant",
        text: "Welcome to practice."
      }
    ]
  });
  (playTTS as Mock).mockResolvedValue(undefined);

  render(<App />);
  await screen.findByText("Welcome to practice.");
  fireEvent.click(screen.getByRole("button", { name: "播放教练语音" }));

  await waitFor(() => {
    expect(playTTS).toHaveBeenCalledWith("Welcome to practice.", undefined);
  });
});

test("deletes a user and assistant turn pair from the trash icon", async () => {
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    session: { id: 1, day_index: 1, topic: "Self-introduction" },
    turns: [
      {
        id: 1,
        session_id: 1,
        turn_index: 1,
        speaker: "assistant",
        text: "Welcome to practice."
      },
      {
        id: 2,
        session_id: 1,
        turn_index: 2,
        speaker: "user",
        text: "Polluted user message."
      },
      {
        id: 3,
        session_id: 1,
        turn_index: 3,
        speaker: "assistant",
        text: "Polluted assistant message."
      }
    ],
    feedback_history: [{ id: 1, feedback_type: "guidance", feedback_text: "Old feedback" }]
  });
  (deleteTurnPair as Mock).mockResolvedValue({
    turns: [
      {
        id: 1,
        session_id: 1,
        turn_index: 1,
        speaker: "assistant",
        text: "Welcome to practice."
      }
    ],
    feedback_history: []
  });

  render(<App />);
  await screen.findByText("Polluted user message.");
  fireEvent.click(screen.getByRole("button", { name: "删除这一轮" }));

  await waitFor(() => {
    expect(deleteTurnPair).toHaveBeenCalledWith(1, 2);
  });
  expect(screen.queryByText("Polluted user message.")).toBeNull();
  expect(screen.queryByText("Polluted assistant message.")).toBeNull();
  expect(screen.queryByText("Old feedback")).toBeNull();
  confirmSpy.mockRestore();
});

test("does not expose standalone studio navigation", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue(startedSession);

  render(<App />);

  await screen.findByText("今日场景");
  expect(screen.queryByRole("button", { name: "Studio" })).toBeNull();
});

test("shows login page when signed out", async () => {
  localStorage.removeItem("speakmate-token");
  (getCurrentLearningState as Mock).mockRejectedValue(new Error("no auth"));

  render(<App />);

  expect(await screen.findByRole("tab", { name: "登录" })).toBeTruthy();
  expect(screen.getByRole("tab", { name: "注册" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "以游客身份进入" })).toBeTruthy();
  expect(screen.getByLabelText("登录注册表单")).toBeTruthy();
});

test("logs in with phone and password and enters the app", async () => {
  localStorage.removeItem("speakmate-token");
  (getCurrentLearningState as Mock).mockRejectedValue(new Error("no plan yet"));

  render(<App />);

  fireEvent.change(await screen.findByLabelText("用户名 / 手机号"), { target: { value: "13800138000" } });
  fireEvent.change(screen.getByLabelText("密码"), { target: { value: "secret123" } });
  fireEvent.click(screen.getByRole("button", { name: "登录" }));

  await waitFor(() => {
    expect(authLogin).toHaveBeenCalledWith("13800138000", "secret123");
  });
  expect(await screen.findByText("创建你的口语练习计划")).toBeTruthy();
});

test("logs out from the sidebar and returns to login", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue(startedSession);

  render(<App />);

  await screen.findByText("今日场景");
  fireEvent.click(screen.getByRole("button", { name: "登出" }));

  expect(clearAuth).toHaveBeenCalled();
  expect(await screen.findByRole("tab", { name: "登录" })).toBeTruthy();
});

test("hides the today picker cards after selecting a scenario", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startScenarioSession as Mock).mockResolvedValue({
    session: { id: 2, day_index: 0, topic: "Airport check-in" },
    turns: [{ id: 1, session_id: 2, turn_index: 1, speaker: "assistant", text: "Let's practice: Airport check-in." }],
    plan_day: null,
    practice_brief: { title: "Airport check-in", target_expressions: [] }
  });

  render(<App />);

  await screen.findByText("今日场景");
  // 选择场景前：显示「今日练习」与场景卡片
  expect(screen.getByText("今日练习")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /Airport check-in/ }));

  // 选择场景后：今日练习标题与六卡片选择器隐藏，进入该场景对话
  expect(await screen.findByText("当前场景")).toBeTruthy();
  expect(screen.queryByText("今日练习")).toBeNull();
  expect(startScenarioSession).toHaveBeenCalledWith("airport-check-in", onboardingResult.profile.id);
});

test("resumes the last scenario conversation after logout and login", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startScenarioSession as Mock).mockResolvedValue({
    session: { id: 2, day_index: 0, topic: "Airport check-in" },
    turns: [{ id: 1, session_id: 2, turn_index: 1, speaker: "assistant", text: "Let's practice: Airport check-in." }],
    plan_day: null,
    practice_brief: { title: "Airport check-in", target_expressions: [] }
  });

  render(<App />);

  await screen.findByText("今日场景");
  fireEvent.click(screen.getByRole("button", { name: /Airport check-in/ }));
  await screen.findByText("当前场景");

  // 登出
  fireEvent.click(screen.getByRole("button", { name: "登出" }));
  await screen.findByRole("tab", { name: "登录" });

  // 重新登录同一账号
  fireEvent.change(screen.getByLabelText("用户名 / 手机号"), { target: { value: "13800138000" } });
  fireEvent.change(screen.getByLabelText("密码"), { target: { value: "secret123" } });
  fireEvent.click(screen.getByRole("button", { name: "登录" }));

  // 恢复上次的场景对话界面，而不是回到刚注册的样子
  expect(await screen.findByText("当前场景")).toBeTruthy();
  expect(startScenarioSession).toHaveBeenCalledWith("airport-check-in", onboardingResult.profile.id);
});

test("starts the first card in today view when a learning path is chosen", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (getScenarios as Mock).mockResolvedValue(mockCatalog);
  (getLearningPath as Mock).mockResolvedValue({
    tier: "beginner",
    level: "A1",
    levels: ["A1", "A2"],
    path: [mockScenario]
  });
  (startScenarioSession as Mock).mockResolvedValue({
    session: { id: 2, day_index: 0, topic: "Airport check-in" },
    turns: [{ id: 1, session_id: 2, turn_index: 1, speaker: "assistant", text: "Let's practice: Airport check-in." }],
    plan_day: null,
    practice_brief: { title: "Airport check-in", target_expressions: [] }
  });

  render(<App />);
  await screen.findByText("今日场景");
  fireEvent.click(screen.getByRole("button", { name: "场景" }));
  await screen.findByText("选择练习场景");

  // 选择一条路线（小白）
  fireEvent.click(screen.getByRole("button", { name: /小白/ }));

  // 自动跳转今日板块并开始第一张卡片练习（先展示该卡片的课程简报）
  await waitFor(() => {
    expect(startScenarioSession).toHaveBeenCalledWith("airport-check-in", onboardingResult.profile.id);
  });
  expect(await screen.findByText("开口前先看一眼")).toBeTruthy();
});

test("offers a free-talk entry in today view", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startScenarioSession as Mock).mockResolvedValue({
    session: { id: 3, day_index: 0, topic: "自由对话" },
    turns: [{ id: 1, session_id: 3, turn_index: 1, speaker: "assistant", text: "Hi! Let's have a free chat." }],
    plan_day: null,
    practice_brief: { title: "自由对话", npc_role: "英语口语陪练教练", target_expressions: [] }
  });

  render(<App />);

  await screen.findByText("今日场景");
  fireEvent.click(screen.getByRole("button", { name: "自由对话" }));

  await waitFor(() => {
    expect(startScenarioSession).toHaveBeenCalledWith("free_talk", onboardingResult.profile.id);
  });
  expect(await screen.findByText("Hi! Let's have a free chat.")).toBeTruthy();
});

test("refetches scenarios with the selected difficulty tier", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  render(<App />);
  await screen.findByText("今日场景");
  fireEvent.click(screen.getByRole("button", { name: "场景" }));
  await screen.findByText("选择练习场景");

  // 切换难度分级下拉：应携带 tier 参数重新请求后端，而非本地错误过滤
  fireEvent.change(screen.getByLabelText("难度分级"), { target: { value: "advanced" } });
  await waitFor(() => {
    expect(getScenarios).toHaveBeenCalledWith(
      onboardingResult.profile.id,
      expect.objectContaining({ tier: "advanced" })
    );
  });
});

test("locates the conversation turn when a feedback card is clicked", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue({
    ...startedSession,
    turns: [
      { id: 1, session_id: 1, turn_index: 1, speaker: "assistant", text: "Today we will practice your self-introduction." },
      { id: 2, session_id: 1, turn_index: 2, speaker: "user", text: "I want to book a room." },
      { id: 3, session_id: 1, turn_index: 3, speaker: "assistant", text: "Great, keep going." }
    ],
    feedback_history: [{
      id: 10,
      turn_id: 2,
      feedback_type: "correction",
      feedback_text: "I need -> I'd like to book: 更自然。",
      original_fragment: "I need",
      better_expression: "I'd like to book",
      reason_zh: "更自然。",
      example_sentence: "I'd like to book a non-smoking room."
    }]
  });

  render(<App />);

  // 纠错卡片可点击定位到对应对话回合
  const card = await screen.findByText("更自然。");
  fireEvent.click(card);

  const targetRow = document.querySelector('[data-turn-id="2"]');
  expect(targetRow).toBeTruthy();
  expect(targetRow?.classList.contains("message-row-highlight")).toBe(true);
  expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
});

test("enters and exits phone mode", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue(startedSession);

  render(<App />);

  await screen.findByText("今日场景");
  fireEvent.click(screen.getByRole("button", { name: "开启电话模式" }));

  // 进入电话模式：显示通话状态条，按钮变为挂断
  expect(await screen.findByLabelText("电话模式状态")).toBeTruthy();
  expect(screen.getByText(/电话模式 · 正在聆听/)).toBeTruthy();

  // 挂断：状态条消失
  fireEvent.click(screen.getByRole("button", { name: "挂断电话模式" }));
  expect(screen.queryByLabelText("电话模式状态")).toBeNull();
  expect(screen.getByRole("button", { name: "开启电话模式" })).toBeTruthy();
});

test("mutes auto-play of AI replies with one click", async () => {
  (getCurrentLearningState as Mock).mockResolvedValue(onboardingResult);
  (startSession as Mock).mockResolvedValue(startedSession);
  (sendUserTurnStream as Mock).mockImplementation(async (_sessionId: number, _text: string, onTextChunk: (chunk: string) => void) => {
    onTextChunk("Great. Could you add your reservation name?");
    return sentTurnResult;
  });
  (playTTS as Mock).mockResolvedValue(undefined);

  render(<App />);

  // 默认自动朗读开启
  expect(await screen.findByRole("button", { name: "AI 回复自动朗读中，点击静音" })).toBeTruthy();

  // 一键静音
  fireEvent.click(screen.getByRole("button", { name: "AI 回复自动朗读中，点击静音" }));
  expect(screen.getByRole("button", { name: "语音已静音，点击开启自动朗读" })).toBeTruthy();

  const response = await screen.findByLabelText("输入你的回答");
  fireEvent.change(response, { target: { value: "I want to check in, please." } });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  await waitFor(() => {
    expect(sendUserTurnStream).toHaveBeenCalledTimes(1);
  });
  expect(screen.getByText("Great. Could you add your reservation name?")).toBeTruthy();

  // 静音后 AI 回复不再自动朗读
  await new Promise((resolve) => setTimeout(resolve, 120));
  expect(playTTS).not.toHaveBeenCalled();
});
