export type Profile = {
  id: number;
  learning_goal: string;
  total_days: number;
  daily_minutes: number;
  current_level: string;
};

export type PlanDay = {
  id: number;
  day_index: number;
  topic: string;
  scenario: string;
  objective: string;
  status: string;
};

export type OnboardingResponse = {
  profile: Profile;
  plan: PlanDay[];
};

export type ConversationTurn = {
  id: number;
  session_id: number;
  turn_index: number;
  speaker: "user" | "assistant";
  text: string;
};

export type InlineFeedback = {
  id: number;
  /** 对应对话中的用户回合 id，用于「点击纠错定位到对话」 */
  turn_id?: number | null;
  feedback_type: string;
  feedback_text: string;
  original_fragment?: string | null;
  better_expression?: string | null;
  reason_zh?: string | null;
  example_sentence?: string | null;
  severity?: string | null;
};

/** 单条错误报告条目（后端 error_aggregation 聚合后的 error 对象） */
export type ErrorReportItem = {
  error_type?: string | null;
  rule_id?: string | null;
  feedback_type?: string | null;
  original_fragment?: string | null;
  better_expression?: string | null;
  feedback_text?: string | null;
  reason_zh?: string | null;
  example_sentence?: string | null;
  severity?: "high" | "medium" | "low" | string | null;
  /** 同一错误出现的次数 */
  frequency?: number;
  examples?: string[];
  source?: string | null;
  source_url?: string | null;
};

/** 一轮对话结束后的错误报告（该轮或整个会话的聚合） */
export type ErrorReport = {
  total_errors: number;
  unique_errors: number;
  errors: ErrorReportItem[];
  by_error_type: Record<string, number>;
  has_errors: boolean;
  /** 对应哪一轮用户回合（会话级报告可能没有） */
  turn_id?: number | null;
};

export type TargetExpression = string | {
  expression: string;
  meaning_zh?: string;
  example?: string;
  when_to_use?: string;
};

export type CommonMistake = string | {
  mistake: string;
  better: string;
  reason_zh?: string;
};

export type PracticeBrief = {
  title?: string;
  user_visible_goal?: string;
  npc_role?: string;
  scenario_setup?: string;
  conversation_objective?: string;
  lesson_focus?: string;
  task_steps?: string[];
  target_expressions?: TargetExpression[];
  sentence_frames?: string[];
  model_dialogue?: string[];
  common_mistakes?: CommonMistake[];
  rubric?: string[];
  avoid_patterns?: string[];
  difficulty?: string;
  coach_notes?: string;
  stretch_goal?: string;
};

export type PracticeSession = {
  id: number;
  day_index: number;
  topic: string;
};

export type CompletionSummary = {
  status: string;
  completion_type: "manual" | "agent_suggested";
  summary_zh: string;
  strength_zh: string;
  next_focus_zh: string;
  reusable_sentences: string[];
  confidence: number;
  /** 100 分制结算得分（依据本轮表达/单词错误扣分） */
  score?: number;
  score_detail_zh?: string;
};

export type SessionCompletion = {
  status: "in_progress" | "completion_suggested" | "completed";
  can_suggest_completion: boolean;
  suggestion_reason_zh: string;
  completed_summary: CompletionSummary | null;
};

export type LanguageSupportMode = "explain" | "define" | "translate" | "expression";

export type LanguageSupportResult = {
  mode: LanguageSupportMode;
  text: string;
  meaning_zh?: string;
  translation_zh?: string;
  better_expression?: string;
  scene_note_zh?: string;
  example_sentence?: string;
};

export type DailyReview = {
  id?: number;
  review_date?: string;
  user_report?: {
    summary?: string;
    next_focus?: string;
  };
  structured_analysis?: {
    strengths?: string[];
    weaknesses?: string[];
  };
};

export type MemoryItem = {
  id: number;
  category: string;
  content: string;
  evidence?: string;
  confidence?: number;
};

export type PlanAdjustment = {
  id: number;
  title: string;
  rationale: string;
  instruction: string;
  priority?: string;
};

export type GrowthSummary = {
  latest_review: DailyReview | null;
  recent_reviews: DailyReview[];
  active_memory: MemoryItem[];
  active_adjustments: PlanAdjustment[];
};

export type TrainingDecision = {
  decision_type: "continue_plan" | "review_weakness" | "insert_micro_drill" | "adjust_difficulty" | "refresh_brief";
  reason_zh: string;
  selected_memory_ids?: number[];
  selected_review_ids?: number[];
  brief_instruction?: string;
  difficulty_adjustment?: "easier" | "same" | "harder";
  should_refresh_brief?: boolean;
};

export type MemoryInfluence = {
  memory_id: number;
  category: string;
  content: string;
  influence_type: "drill_focus" | "difficulty_control" | "npc_behavior" | "feedback_priority";
  instruction: string;
  reason_zh: string;
};

export type TodayStrategy = {
  today_strategy: {
    focus: string;
    reason: string;
    success_criteria?: string[];
  };
  training_decision?: TrainingDecision;
  memory_influence?: MemoryInfluence[];
  coach_explanation_zh: string;
  recommended_actions: Array<{
    action: string;
    rationale: string;
    priority?: string;
  }>;
  risk_flags: string[];
  practice_brief: PracticeBrief;
  agent_run_id: number;
};

export type ScenarioDifficulty = {
  level: string;
  vocabulary_range: string;
  sentence_complexity: string;
  target_functions: string[];
};

export type Scenario = {
  id: string;
  title: string;
  category: string;
  background: string;
  npc_role: string;
  learner_role: string;
  objective: string;
  bands: ScenarioDifficulty[];
  difficulty: ScenarioDifficulty;
  is_favorite?: boolean;
};

export type ScenarioTier = {
  id: "beginner" | "intermediate" | "advanced";
  label: string;
  levels: string[];
};

export type ScenarioCatalog = {
  scenarios: Scenario[];
  categories: string[];
  roles: string[];
  tiers: ScenarioTier[];
  derived_tier: ScenarioTier["id"] | null;
};

export type LearningPath = {
  tier: ScenarioTier["id"];
  level: string;
  levels: string[];
  path: Scenario[];
};

export type SessionHistoryItem = {
  id: number;
  plan_day_id: number | null;
  scenario_id: string | null;
  profile_id: number | null;
  day_index: number;
  topic: string;
  started_at: string;
  ended_at: string | null;
  summary: string | null;
  overall_score: number | null;
  turn_count: number;
  /** 本次练习得分（100 分制，旧数据可能没有） */
  score?: number | null;
  /** 难度等级（如 A2 / 自由） */
  difficulty?: string | null;
};
