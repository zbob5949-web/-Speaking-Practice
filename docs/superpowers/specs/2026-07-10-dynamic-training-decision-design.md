# SpeakMate Agent Dynamic Training Decision Design

## 背景

SpeakMate Agent 当前已经完成 V2 Agent 架构骨架：`CoachOrchestratorAgent`、Tools Registry、`agent_runs`、`/api/today/strategy` 和前端 `今日练习依据`。这让产品从固定多 LLM 节点升级为可解释、可追踪的 Agentic Workflow。

但当前 Orchestrator 仍主要是在解释已有 `plan_day` 和已有 `practice_brief`，真正决定“今天练什么”的权力仍在后端固定流程中。长期记忆也更多作为上下文传入，而不是稳定地驱动训练选择和材料生成。因此产品仍更像工作流，而不是一个会根据学习状态主动调整训练的 AI 教练 Agent。

本次升级目标是优先补齐两个能力：

- 动态任务决策：Agent 可以在学习主线内决定今天继续原计划、复习弱点、插入微训练、调整难度或刷新材料。
- 记忆驱动训练：长期记忆不只是展示或上下文，而是被选中、解释，并转化为 practice brief 的生成约束。

## 目标

- 新增 `TrainingDecision` 契约，让 Orchestrator 必须先做今日训练决策，再输出 Today Strategy。
- 新增 `MemoryInfluence` 契约，让被选中的长期记忆转化为可执行训练指令。
- 扩展 `/api/today/strategy` 返回 `training_decision`、`memory_influence`、`selected_memory_ids`、`selected_review_ids`。
- 扩展 `ScenarioDesignAgent` 输入，使其接收 `brief_instruction` 和 `memory_influence`，生成更贴合弱点的 practice brief。
- 扩展 Tools Registry，支持读取决策上下文、筛选相关记忆、在后端受控地刷新 practice brief。
- 升级前端 `今日练习依据`，让用户看到“今天怎么练、为什么这样练、AI 教练基于哪些记忆做准备”。
- 保持现有练习流程稳定，Agent 决策失败时回退到 `continue_plan`，不阻塞用户练习。

## 非目标

- 不实现完全自主 tool-calling Agent。
- 不允许模型直接写数据库或任意重排长期计划。
- 不引入向量数据库、外部检索系统、后台队列或云调度。
- 不做记忆冲突合并、遗忘曲线、用户手动编辑记忆。
- 不做完整 Agent trace 前端调试台。
- 不重写现有 session start、turn stream、review pipeline。

## 产品原则

### Agent 决策权边界

本次采用“推荐决策”边界。Agent 可以选择今日训练动作，但必须符合学习主线。

允许的动作：

- `continue_plan`：继续当前计划，但可强调某个重点。
- `review_weakness`：基于长期弱点复习。
- `insert_micro_drill`：插入 3-5 分钟小训练，不替代整节课。
- `adjust_difficulty`：根据近期表现提高或降低难度。
- `refresh_brief`：当前材料与记忆不匹配时刷新 lesson pack。

不允许的动作：

- 直接删除或重排整个学习计划。
- 同时选择多个主决策导致训练目标发散。
- 根据单次偶然错误创建长期训练路线。
- 无证据地刷新 practice brief。

### 用户可感知价值

用户不需要看到内部 JSON 或完整工具轨迹，但应该清楚感受到：

- AI 教练看过我的近期表现。
- 今天的训练不是机械按天推进，而是针对我的弱点安排。
- 如果某条长期记忆影响了训练，产品会用自然语言解释原因。
- NPC 和材料会围绕这个弱点追问、练习和反馈。

## 契约设计

### TrainingDecision

新增 `TrainingDecision`：

```python
class TrainingDecision(BaseModel):
    decision_type: Literal[
        "continue_plan",
        "review_weakness",
        "insert_micro_drill",
        "adjust_difficulty",
        "refresh_brief",
    ]
    reason_zh: str
    selected_memory_ids: list[int] = Field(default_factory=list, max_length=3)
    selected_review_ids: list[int] = Field(default_factory=list)
    brief_instruction: str = ""
    difficulty_adjustment: Literal["easier", "same", "harder"] = "same"
    should_refresh_brief: bool = False
```

规则：

- `decision_type` 非法时回退为 `continue_plan`。
- `selected_memory_ids` 最多 3 条，超过时截断。
- `should_refresh_brief=True` 时必须提供非空 `brief_instruction`。
- `brief_instruction` 必须是面向 `ScenarioDesignAgent` 的明确教学指令，不是用户展示文案。
- `reason_zh` 必须引用 review、memory、adjustment 或 plan 中的证据。

### MemoryInfluence

新增 `MemoryInfluence`：

```python
class MemoryInfluence(BaseModel):
    memory_id: int
    category: str
    content: str
    influence_type: Literal[
        "drill_focus",
        "difficulty_control",
        "npc_behavior",
        "feedback_priority",
    ]
    instruction: str
    reason_zh: str
```

影响类型：

- `drill_focus`：把 weakness 变成今日重点训练目标。
- `difficulty_control`：根据 memory 调整输入复杂度或练习难度。
- `npc_behavior`：影响 NPC 追问方式，例如用户没说时间时必须追问。
- `feedback_priority`：影响反馈优先级，例如优先检查是否漏掉关键信息。

### OrchestrationResult 扩展

`OrchestrationResult` 增加：

```python
class OrchestrationResult(BaseModel):
    today_strategy: TodayStrategy
    training_decision: TrainingDecision
    memory_influence: list[MemoryInfluence] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    coach_explanation_zh: str
    risk_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
```

## Orchestrator Prompt 升级

`orchestrator_agent_system` 需要从“解释今日策略”升级为“先决策，再解释”。

核心要求：

- 你是 AI 口语教练总控，不是 NPC，不直接纠错。
- 你的第一任务是基于用户状态选择今日训练决策。
- 必须输出合法 JSON 对象。
- 顶层必须包含 `training_decision`、`memory_influence`、`today_strategy`、`recommended_actions`、`coach_explanation_zh`、`risk_flags`、`confidence`。
- `decision_type` 只能从允许枚举中选择。
- 每次最多选择一个主决策。
- 最多选择 1-3 条最相关 memory。
- 如果证据不足，选择 `continue_plan`。
- 只有当现有 brief 与当前弱点明显不匹配时，才设置 `should_refresh_brief=true`。
- 不要修改长期计划，不要写 memory，不要输出完整 lesson pack。

## Memory 驱动训练生成

当前 `ScenarioDesignAgent` 输入主要是：

```text
plan_day + adjustments + memory + review
```

升级后输入改为：

```text
plan_day + training_decision + memory_influence + review
```

关键变化：

- Orchestrator 先筛选 1-3 条最相关 memory。
- Orchestrator 将 memory 转换成明确教学指令。
- `ScenarioDesignAgent` 不再泛泛读取所有 memory，而是优先服从 `brief_instruction` 和 `memory_influence.instruction`。
- practice brief 必须体现这些指令，例如 task steps、NPC 追问、common mistakes、rubric。

示例：

```text
memory:
用户在旅行场景中经常能表达意图，但容易漏掉时间和对象。

brief_instruction:
生成一个酒店入住场景。NPC 必须在用户漏掉入住日期、预订姓名、房型时追问。任务步骤必须包含说明时间、说明对象、提出明确问题。
```

## Tools Registry 升级

新增或扩展工具：

- `get_decision_context`：一次性读取 profile、plan_day、latest_review、active_memory、active_adjustments、existing_brief。
- `get_relevant_memory`：第一版用规则筛选 active memory，不做向量检索；优先 weakness、learning_pattern 和最近更新的高 confidence memory。
- `refresh_practice_brief`：当 Orchestrator 判断 `should_refresh_brief=true` 时，由后端受控调用 `ScenarioDesignAgent` 生成新 brief 并保存。

工具边界：

- `get_decision_context` 和 `get_relevant_memory` 是 read-only。
- `refresh_practice_brief` 是 write，必须由后端显式执行。
- 模型只输出决策和建议，不直接执行写工具。
- 所有工具调用写入 `agent_runs.tool_calls_json`。

## API 设计

继续使用 `GET /api/today/strategy`，返回结构升级：

```json
{
  "today_strategy": {
    "focus": "补充旅行场景中的关键信息",
    "reason": "基于长期记忆和最近复盘",
    "success_criteria": ["说明时间", "说明对象", "提出明确问题"]
  },
  "training_decision": {
    "decision_type": "review_weakness",
    "reason_zh": "你最近经常漏掉时间和对象，所以今天先集中练这个。",
    "selected_memory_ids": [3],
    "selected_review_ids": [12],
    "brief_instruction": "生成酒店入住场景，NPC 必须追问日期、姓名、房型。",
    "difficulty_adjustment": "same",
    "should_refresh_brief": true
  },
  "memory_influence": [
    {
      "memory_id": 3,
      "category": "weakness",
      "content": "用户在旅行场景中经常漏掉时间和对象。",
      "influence_type": "npc_behavior",
      "instruction": "用户没说入住日期时，NPC 必须追问。",
      "reason_zh": "这是最近重复出现的细节遗漏问题。"
    }
  ],
  "coach_explanation_zh": "今天我会先帮你解决旅行对话中漏掉关键信息的问题。",
  "recommended_actions": [],
  "risk_flags": [],
  "practice_brief": {},
  "agent_run_id": 18
}
```

## Practice Brief 刷新策略

- 没有 existing brief：按 `training_decision + memory_influence` 生成新 brief。
- 已有 brief 且 `should_refresh_brief=false`：沿用 existing brief，只更新 Today Strategy。
- 已有 brief 且 `should_refresh_brief=true`：刷新 brief，并在 agent run 中记录原因。
- refresh 失败：回退 existing brief；如果没有 existing brief，使用当前 ScenarioDesign fallback。
- 决策失败：回退 `continue_plan`，不刷新 brief。

## 前端展示

`PracticeRoom` Learn 页顶部的 `今日练习依据` 升级为三个小块：

- `今天怎么练`：展示 `today_strategy.focus`。
- `为什么这样练`：展示 `coach_explanation_zh`。
- `AI 教练准备`：展示 `memory_influence.reason_zh` 或 `memory_influence.instruction` 的用户友好摘要。

示例文案：

```text
今天怎么练：补充旅行场景中的关键信息
为什么这样练：我发现你最近经常漏掉时间、对象和数量，所以今天先用酒店入住场景集中练这个。
AI 教练准备：如果你没说清楚入住日期、预订姓名或房型，NPC 会追问你补充。
```

不展示：

- 完整 JSON。
- 内部工具调用轨迹。
- selected memory 原始证据全文。

## 测试策略

### 后端

- `TrainingDecision` 能校验合法 `decision_type`。
- 非法 Orchestrator 输出 fallback 到 `continue_plan`。
- `selected_memory_ids` 超过 3 条时被归一化。
- `should_refresh_brief=true` 且 `brief_instruction` 为空时回退为不刷新。
- `MemoryInfluence` 只接受允许的 `influence_type`。
- `ScenarioDesignAgent` 的 user prompt 包含 `training_decision` 和 `memory_influence`。
- `/api/today/strategy` 返回 `training_decision` 和 `memory_influence`。
- `should_refresh_brief=true` 时调用 `refresh_practice_brief`。
- `refresh_practice_brief` 失败时 API 仍返回 existing brief 或 fallback brief。

### 前端

- `TodayStrategy` 类型包含 `training_decision` 和 `memory_influence`。
- Mock `getTodayStrategy` 返回 memory influence 时，Learn 页展示 `今天怎么练`、`为什么这样练`、`AI 教练准备`。
- 没有 `memory_influence` 时仍展示基础 today strategy，不阻塞进入练习。

### 回归

- 后端全量：`cd app/backend && python -m pytest tests/ -v`。
- 前端测试：`cd app/frontend && npm run test -- src/App.test.tsx`。
- 前端构建：`cd app/frontend && npm run build`。

## 实施顺序

1. 扩展契约：`TrainingDecision`、`MemoryInfluence`、`OrchestrationResult`。
2. 升级 Orchestrator Prompt 和解析 fallback。
3. 扩展 Tools Registry：decision context、relevant memory、refresh brief。
4. 扩展 ScenarioDesignAgent 输入，接入 `brief_instruction` 和 `memory_influence`。
5. 升级 `/api/today/strategy`，让决策结果影响 brief 刷新。
6. 升级前端 `TodayStrategy` 类型和 Learn 页展示。
7. 补齐后端、前端和回归测试。

## 成功标准

- 用户进入 Today 时，系统返回明确的 `training_decision`。
- Today 页能解释今天为什么这样练，并能体现至少一条 memory influence。
- 当长期记忆显示重复弱点时，Agent 可以选择 `review_weakness` 或 `refresh_brief`。
- 刷新后的 practice brief 能体现 memory influence 的教学指令。
- Orchestrator 输出异常时，用户仍能进入练习。
- 所有新增行为有测试覆盖，现有练习流程不回退。
