# SpeakMate Agent V2 Architecture Design

## 背景

当前 SpeakMate Agent 已经具备多 Agent 学习闭环：目标规划、场景任务单、NPC 对话、即时反馈、语言支援、每日复盘、长期记忆和计划微调。但现有实现主要由 FastAPI endpoint 固定编排各个 LLM 节点，Agent 自身缺少工具抽象、运行轨迹、统一输出契约和可解释决策层。

下一版目标是把产品从“后端固定编排的多 LLM 节点”升级为“有工具能力、有运行记录、有输出校验的 Coach Orchestrator Agent”。本次升级不追求完全自主 tool calling，而是先建立可落地、可测试、可继续演进的 Agent 架构骨架。

## 目标

- 新增 `CoachOrchestratorAgent`，作为学习教练总控层，生成今日练习策略和可解释原因。
- 新增 Tools Registry，把现有 profile、plan、memory、review、adjustment、practice brief 等能力包装成可描述、可追踪、可测试的工具。
- 新增 `agent_runs` 运行轨迹，记录 Agent 输入、工具调用、输出、校验状态和错误。
- 强化 Prompt 契约，补齐 Orchestrator、DailyReview、Memory、PlanAdaptation、ScenarioDesign 的输出结构、决策边界和失败处理。
- 新增 `/api/today/strategy`，让前端进入 Today 时可以获取“今天为什么练这个”的策略解释。
- 在 PracticeRoom 的 Learn 页展示轻量 `今日练习依据`，让用户感知 Agent 根据复盘、记忆和计划调整在因材施教。

## 非目标

- 不重写所有现有 API，不让 Orchestrator 直接替代全部业务逻辑。
- 不引入外部向量库、后台队列、云调度或复杂权限系统。
- 不在第一版实现模型原生 function calling。
- 不做完整 Agent trace 前端调试台，只做用户可见的今日策略摘要。
- 不改变现有 SQLite 本地优先架构。

## 架构概览

当前流程：

```text
FastAPI endpoint
→ 固定调用某个 Agent
→ 保存结果
→ 返回页面数据
```

V2 流程：

```text
FastAPI endpoint
→ Tools Registry 读取学习状态
→ CoachOrchestratorAgent 生成今日策略
→ 必要时调用写工具或子 Agent
→ 保存 agent_run
→ 返回 today_strategy / practice_brief / agent_run_id
```

第一版 Orchestrator 是“决策与解释层”，不是完全自主执行层。数据库写入仍由后端显式控制，避免模型任意修改学习计划和长期记忆。

## CoachOrchestratorAgent

### 定位

`CoachOrchestratorAgent` 是学习教练总控层。它负责理解用户当前学习状态，决定今日练习重点，并解释为什么今天这样练。

它不直接扮演 NPC，不直接纠错，不直接写长期记忆，不生成完整 lesson pack。上述能力继续交给现有子 Agent 或工具。

### 输入

- `profile`：学习目标、当前水平、每日练习时长。
- `plan_day`：今日 topic、scenario、objective、skill_focus、success_criteria。
- `latest_review`：最近一次练后复盘。
- `active_memory`：长期记忆中的 active 弱点和学习特征。
- `active_adjustments`：对当前 plan day 生效的计划微调。
- `practice_brief`：已有或刚生成的今日 lesson pack。
- `session_state`：今日 session 是否已创建、是否已有用户发言。

### 输出

`CoachOrchestratorAgent` 必须输出合法 JSON 对象：

```json
{
  "today_strategy": {
    "focus": "Ask clear hotel check-in questions",
    "reason": "Recent reviews show vague reservation details.",
    "success_criteria": ["State reservation name", "Ask one practical question"]
  },
  "recommended_actions": [
    {
      "action": "use_existing_brief",
      "rationale": "Practice brief already matches active memory.",
      "priority": "medium"
    }
  ],
  "coach_explanation_zh": "今天重点练酒店入住时说明预订信息，因为你最近容易遗漏关键信息。",
  "risk_flags": [],
  "confidence": 0.8
}
```

### 输出规则

- `today_strategy.focus` 必须是一句话，说明今天练什么。
- `today_strategy.reason` 必须引用复盘、记忆、计划调整或今日计划中的至少一种依据。
- `recommended_actions` 只允许以下动作：
  - `run_due_reviews`
  - `generate_practice_brief`
  - `use_existing_brief`
  - `start_practice`
  - `review_lesson_material`
- `coach_explanation_zh` 面向用户，必须短、清楚、不暴露内部系统提示词。
- `risk_flags` 用于记录缺失 profile、缺失 plan day、缺失 brief、LLM 输出低置信度等风险。
- `confidence` 范围为 `0.0` 到 `1.0`。

## Tools Registry

### 工具定义

新增统一工具定义：

```python
class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    side_effect: Literal["read_only", "write"]
```

工具执行结果统一包装为：

```python
class ToolCallRecord(BaseModel):
    tool_name: str
    input: dict[str, object]
    output: dict[str, object] | list[dict[str, object]] | None
    status: Literal["success", "failed"]
    error_message: str | None = None
```

### 第一批工具

- `get_profile`：读取当前或指定用户 profile。
- `get_current_plan_day`：读取当前应练习的 plan day。
- `get_active_memory`：读取长期 active memory。
- `get_latest_review`：读取最近完成的每日复盘。
- `get_active_adjustments`：读取当前 plan day 生效的计划调整。
- `get_or_create_practice_brief`：读取或生成今日 practice brief。
- `run_due_reviews`：运行未完成的复盘闭环。

### 工具边界

- 读工具可以在 Orchestrator service 中自动调用。
- 写工具必须由后端显式调用，并记录 `ToolCallRecord`。
- 模型第一版不能任意调用写工具，只能在输出中建议动作，最终由后端策略决定是否执行。

## Prompt 契约升级

### Orchestrator Prompt

新增 `orchestrator_agent_system` 和 `orchestrator_agent_user_template`。

Prompt 必须声明：

- 你是学习教练总控，不是 NPC，不直接纠错。
- 你的任务是基于用户状态生成今日练习策略。
- 必须输出合法 JSON 对象。
- 不要修改学习计划，不要生成完整 lesson pack，不要保存记忆。
- 输出必须包含 `today_strategy`、`recommended_actions`、`coach_explanation_zh`、`risk_flags`、`confidence`。

### DailyReview Prompt

补齐复盘结构：

- `user_report.summary`
- `user_report.next_focus`
- `user_report.encouragement`
- `structured_analysis.strengths`
- `structured_analysis.weaknesses`
- `structured_analysis.recurring_issues`
- `structured_analysis.evidence_turns`
- `structured_analysis.plan_adaptation_signals`

复盘必须引用用户原始发言或 session 证据，避免泛泛鼓励。

### Memory Prompt

补齐记忆规则：

- 只记录稳定、可复用、未来会影响教学策略的用户特征。
- 不记录一次性错误、临时场景事实、无证据判断。
- 每条记忆必须包含 `category`、`content`、`evidence`、`confidence`、`status`。
- `category` 使用枚举：`weakness`、`strength`、`preference`、`goal`、`learning_pattern`。
- 如果新证据只是支持已有记忆，应输出可 upsert 的同类内容，不制造重复记忆。

### PlanAdaptation Prompt

补齐计划调整策略：

- 轻量微调优先，不频繁推翻原计划。
- 每条 adjustment 必须引用 review 或 memory 中的依据。
- 只调整未来 pending plan day。
- 如果没有足够证据，返回 `{"adjustments": []}`。

### ScenarioDesign Prompt

补齐教学设计标准：

- `task_steps` 控制在 3-5 步。
- `target_expressions` 控制在 3-5 个对象。
- `sentence_frames` 控制在 2-4 个。
- `common_mistakes` 控制在 2-4 个。
- `rubric` 控制在 3-5 条可观察标准。
- 学习材料要高密度、实用，避免大段空泛解释。
- lesson pack 必须能被 ConversationAgent 用来推动角色扮演。

## 数据表

新增 `agent_runs`：

```sql
CREATE TABLE IF NOT EXISTS agent_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER,
  plan_day_id INTEGER,
  session_id INTEGER,
  agent_name TEXT NOT NULL,
  trigger_source TEXT NOT NULL,
  input_json TEXT NOT NULL,
  tool_calls_json TEXT NOT NULL,
  output_json TEXT NOT NULL,
  validation_status TEXT NOT NULL,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

第一版只保存 Orchestrator 运行。后续可扩展到 Feedback、Memory、PlanAdaptation。

## API

新增：

```text
GET /api/today/strategy?profile_id=...
```

返回：

```json
{
  "today_strategy": {
    "focus": "Ask clear hotel check-in questions",
    "reason": "Recent reviews show vague reservation details.",
    "success_criteria": ["State reservation name", "Ask one practical question"]
  },
  "coach_explanation_zh": "今天重点练酒店入住时说明预订信息，因为你最近容易遗漏关键信息。",
  "recommended_actions": [],
  "risk_flags": [],
  "practice_brief": {},
  "agent_run_id": 1
}
```

该接口负责：

1. 运行 due review 检查。
2. 读取当前 profile 和今日 plan day。
3. 读取 memory、latest review、active adjustments、practice brief。
4. 如缺少 practice brief，则创建 practice brief。
5. 调用 `CoachOrchestratorAgent` 生成今日策略。
6. 保存 `agent_runs`。
7. 返回策略和 practice brief。

现有 `/api/sessions/start` 保留，PracticeRoom 仍通过它创建/恢复练习 session。

## 前端展示

在 PracticeRoom Learn 页顶部新增 `今日练习依据` 区块：

- `今天重点`：展示 `today_strategy.focus`。
- `为什么练这个`：展示 `coach_explanation_zh` 或 `today_strategy.reason`。
- `AI 教练准备`：展示系统已基于复盘、记忆或计划调整准备今日任务。

如果 `/api/today/strategy` 失败，不阻塞练习，隐藏该区块或显示安全默认文案。

## 校验与失败处理

新增 Pydantic 合约：

- `OrchestrationResult`
- `DailyReviewResult`
- `MemoryExtractionResult`
- `PlanAdaptationResult`
- `PracticeBriefResult`

失败策略：

- Orchestrator 输出解析失败：返回安全默认策略，保存 `agent_runs.validation_status = failed`。
- PracticeBrief 输出不合格：使用现有 fallback。
- Memory 输出不合格：返回 `{"upserts": []}`。
- PlanAdaptation 输出不合格：返回 `{"adjustments": []}`。
- 所有失败都不阻塞用户进入练习。

## 测试策略

### 后端

- Repository：
  - `save_agent_run` 能保存完整轨迹。
  - `get_agent_runs` 能按 profile 查询最近运行记录。
- Tools：
  - `get_profile` 返回 profile。
  - `get_current_plan_day` 返回可练习 plan day。
  - `get_active_memory` 返回 active memory。
  - `get_or_create_practice_brief` 能复用已有 brief 或生成新 brief。
- Orchestrator：
  - Mock LLM 返回合法策略 JSON 时，解析为 `OrchestrationResult`。
  - Mock LLM 返回坏 JSON 时，返回安全默认策略。
- API：
  - `/api/today/strategy` 返回 `today_strategy`、`coach_explanation_zh`、`practice_brief`、`agent_run_id`。
  - 接口失败时不破坏原有 `/api/sessions/start`。

### 前端

- API client：
  - `getTodayStrategy` 能请求 `/api/today/strategy`。
- PracticeRoom：
  - Mock `todayStrategy` 时展示 `今日练习依据`。
  - `todayStrategy` 缺失时仍能进入 Learn/Practice。
- 回归：
  - `npm run test -- src/App.test.tsx`
  - `npm run build`

## 分阶段实施

### Phase 1: Contracts And Persistence

- 新增 Pydantic contract。
- 新增 `agent_runs` 表。
- 新增 repository 方法。
- 补充 repository 测试。

### Phase 2: Tools Registry

- 新增 `app/backend/app/tools.py`。
- 包装第一批 read/write tools。
- 补充 tool 单测。

### Phase 3: Orchestrator

- 新增 `CoachOrchestratorAgent`。
- 新增 orchestrator prompt。
- 新增 output validation 和 fallback。
- 补充 agent 单测。

### Phase 4: Today Strategy API

- 新增 `/api/today/strategy`。
- 串联 tools、orchestrator、agent_run 保存。
- 补充 API 测试。

### Phase 5: Frontend Exposure

- 新增 `TodayStrategy` 类型和 API client。
- App 进入 Today 时加载 strategy。
- PracticeRoom 展示 `今日练习依据`。
- 补充前端测试。

## 验收标准

- 进入 Today 时，系统能返回今日练习策略和解释。
- 练习页面能展示“今天为什么练这个”。
- 每次 Today strategy 生成都会写入 `agent_runs`。
- Prompt 输出坏结构时不会阻塞练习。
- 现有练习、反馈、复盘、Growth 功能保持可用。
- 后端测试和前端测试全部通过。
