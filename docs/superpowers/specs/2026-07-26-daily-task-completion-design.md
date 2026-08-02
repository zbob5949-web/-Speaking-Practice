# SpeakMate Agent Daily Task Completion Design

## 背景

SpeakMate Agent 当前已经具备每日学习计划、练前材料、多轮对话、即时 feedback、语言解释、长期记忆和隔日复盘能力。但今天的练习没有明确终止点：用户可以一直聊下去，系统不会判断“今天这个任务已经完成”，也不会主动引导用户收束、总结和推进学习计划。

这会带来三个产品问题：

- 用户缺少完成感，不知道今天练到什么程度算够。
- 每日计划状态不完整，`PlanDay.status` 可以从 `pending` 进入 `in_progress`，但缺少自然变成 `completed` 的路径。
- Agent 更像无限聊天陪练，而不像真实教练；真实教练会在合适时机提醒“今天到这里就可以，接下来复盘”。

本次设计采用“软收束机制”：Agent 主动建议结束，但不强制结束；用户也可以随时手动结束并生成总结。

## 目标

- 增加今日任务完成概念，让每天的练习从“无限聊天”变成“有目标、有过程、有收束”的学习单元。
- 支持 Agent 主动建议结束：当练习已达到足够效果时，提示用户可以结束并复盘。
- 支持用户手动结束：用户随时可以点击“结束今日练习”，系统生成总结并标记完成。
- 完成后生成 Today Summary，沉淀今天的练习成果、亮点、下次重点和可复用表达。
- 将完成状态写入现有 `daily_sessions` 和 `learning_plan`，为后续 review、memory 和 plan adaptation 提供更清晰的数据基础。

## 非目标

- 不做强制考试制，不要求用户必须通过硬性关卡才能结束。
- 不禁止用户在完成后继续自由练习。
- 不引入复杂评分模型、语音识别质量评分或外部评测服务。
- 不重写现有 Daily Review、Memory Agent 和 Plan Adaptation Agent。
- 不用固定轮次替代教学判断；轮次只作为软提示的辅助信号。

## 产品原则

### 用户体感优先

结束权归用户。Agent 可以建议“今天可以收束”，但必须让用户确认。用户也可以在任何时候手动结束，不需要等待系统判定。

### 软目标而非考试

今日任务完成不是“通过考试”，而是“今天这段练习已经产生足够学习价值”。系统应该鼓励复盘和停止，而不是制造压力。

### Agent 像真实教练

真实教练不会无限陪聊，也不会突然强制停止。更合理的行为是：

- 观察练习过程。
- 判断目标是否基本覆盖。
- 在用户疲劳或练习收益递减时提醒收束。
- 用简短总结帮助用户带走今天的收获。

### 完成后仍可继续

完成状态不代表禁止继续使用。完成后用户可以进入“继续自由练习”，但产品表达上应把它与今日主任务区分开，避免每日计划无限拖长。

## 方案选择

### 方案一：软收束机制

Agent 在合适时机提示“今天目标基本达成，要不要结束并生成总结？”用户可以结束，也可以继续练。

优点：

- Agent 感最强，像教练主动管理练习节奏。
- 不强制用户停止，保留主观体感。
- 能自然接入 Today Summary、计划推进和长期记忆。

风险：

- 需要定义清楚“建议结束”的触发条件。
- 如果提示过早，会让用户觉得练得不够。
- 如果提示过晚，仍会接近无限聊天。

### 方案二：手动结束优先

页面始终提供“结束今日练习”按钮，用户点击后生成总结。

优点：

- 实现简单。
- 用户控制感强。

风险：

- Agent 主动性弱。
- 用户可能仍不知道什么时候该结束。

### 方案三：强完成机制

系统根据固定成功标准自动完成或要求达成所有条件后才能完成。

优点：

- 任务边界清晰。
- 完成感强。

风险：

- 容易变成考试。
- 破坏自然对话体验。
- 不符合当前“用户体感优先”的产品方向。

本次采用方案一，并保留方案二的手动入口。

## 核心体验

### 进入练习

用户进入当天练习后，状态为 `in_progress`。页面展示今日目标和练习材料，用户开始 role-play。

### 练习中

用户每完成一轮对话，系统继续给出 NPC 回复、即时 feedback 和 guidance。后端同时根据会话状态计算一个轻量 completion signal。

### Agent 建议结束

当系统判断练习已经产生足够价值时，在输入区附近或右侧 panel 显示软提示：

```text
今天的核心目标已经基本练到了。
你已经完成了预订信息说明和一次追问回应。要不要现在结束，并生成今日总结？
```

用户可以选择：

- `结束并总结`
- `继续练一会儿`

如果用户选择继续，系统短时间内不重复打扰。

### 用户手动结束

输入区固定提供轻量按钮：

```text
结束今日练习
```

用户点击后显示确认：

```text
确定结束今天的练习吗？系统会生成今日总结，并把这一天标记为已完成。
```

确认后生成 Today Summary。

### 完成后

页面进入完成态：

- 显示 `今日已完成`。
- 展示 Today Summary。
- 输入框默认收起或禁用主任务提交。
- 提供 `复习材料`、`查看总结`、`继续自由练习` 三个入口。

如果用户选择继续自由练习，后续对话仍可进行，但不再改变今天主任务的完成状态。

## 完成判定

完成判定采用软信号，不做硬门槛。

### 输入信号

- `turn_count`：用户已经完成的发言轮次。
- `practice_brief.user_visible_goal`：今天对用户可见的练习目标。
- `practice_brief.conversation_objective`：本次 role-play 的交际目标。
- `practice_brief.rubric`：可观察的成功标准。
- `today_strategy.today_strategy.success_criteria`：今日策略中的成功标准。
- `inline_feedback`：最近 feedback 中是否仍存在主要阻塞。
- `conversation_turns`：用户是否已经覆盖核心任务信息。

### 推荐结束条件

第一版采用保守规则：

- 用户至少完成 3 个 user turns。
- 对话已经覆盖今日目标或至少完成一个核心交际动作。
- 最近一轮没有明显“无法继续任务”的阻塞。
- 当前 session 尚未完成。

满足后返回 `can_suggest_completion=true`。前端只展示一次主动提示，除非用户继续练习了多轮后再次满足条件。

### 手动结束条件

用户只要已经有至少 1 个 user turn，就可以手动结束。即使练得较短，也允许生成总结，但 summary 应明确写出：

```text
今天练习时间较短，建议下次继续加强同一目标。
```

## 数据设计

现有 `daily_sessions` 已有可复用字段：

- `ended_at`
- `summary`
- `overall_score`

现有 `learning_plan` 已有可复用字段：

- `status`

第一版不新增表，优先复用现有结构。

### Session Completion

完成后更新：

- `daily_sessions.ended_at = CURRENT_TIMESTAMP`
- `daily_sessions.summary = Today Summary 文本或 JSON 字符串`
- `daily_sessions.overall_score = 1-5 的轻量评分`
- `learning_plan.status = completed`

### Completion Summary

Today Summary 用 JSON 存储在 `daily_sessions.summary`，结构为：

```json
{
  "status": "completed",
  "completion_type": "agent_suggested",
  "summary_zh": "今天你完成了酒店预订场景中的基本信息说明。",
  "strength_zh": "你能主动提出预订需求，并保持对话推进。",
  "next_focus_zh": "下次继续练习补充时间、人数和房型等关键信息。",
  "reusable_sentences": [
    "I'd like to make a reservation for tomorrow night.",
    "Could you confirm the room type for me?"
  ],
  "confidence": 0.74
}
```

`completion_type` 支持：

- `manual`
- `agent_suggested`

## API 设计

### Completion Status

在 `start_session` 和 turn response 中返回 session completion 状态：

```json
{
  "completion": {
    "status": "in_progress",
    "can_suggest_completion": false,
    "suggestion_reason_zh": "",
    "completed_summary": null
  }
}
```

状态枚举：

- `in_progress`
- `completion_suggested`
- `completed`

### Turn Stream Meta

`/api/sessions/turn/stream` 的 final meta 增加：

```json
{
  "type": "meta",
  "completion": {
    "status": "completion_suggested",
    "can_suggest_completion": true,
    "suggestion_reason_zh": "今天的核心目标已经基本练到了。"
  }
}
```

### Complete Session

新增：

```text
POST /api/sessions/{session_id}/complete
```

Request：

```json
{
  "completion_type": "manual"
}
```

Response：

```json
{
  "session": {},
  "plan_day": {},
  "completion": {
    "status": "completed",
    "completed_summary": {}
  }
}
```

后端行为：

- 校验 session 是否存在。
- 校验是否至少有 1 个 user turn。
- 调用 Completion Summary 生成逻辑。
- 更新 `daily_sessions`。
- 将对应 `learning_plan.status` 标记为 `completed`。
- 返回 summary 和更新后的 plan day。

## Agent 与 Prompt 设计

第一版不新增复杂 Agent，新增轻量 `CompletionAgent` 或 `SessionCompletionEvaluator`。

### Completion Evaluator

职责：

- 根据当前 session、practice brief、feedback 和 strategy 判断是否建议结束。
- 输出结构化 completion signal。
- 失败时返回 `in_progress`，不影响对话。

输出：

```json
{
  "status": "completion_suggested",
  "can_suggest_completion": true,
  "suggestion_reason_zh": "今天的核心目标已经基本练到了。",
  "confidence": 0.72
}
```

### Summary Generator

职责：

- 在用户确认结束时生成 Today Summary。
- 总结必须短、清楚、面向学习者。
- 不暴露内部 rubric、prompt 或工具信息。

第一版可以复用现有 LLM provider，失败时用规则 fallback 生成基础总结。

## 前端设计

### 输入区

输入区增加 `结束今日练习` 次级按钮。按钮在有至少 1 个 user turn 后可用。

### 软提示卡

当后端返回 `completion_suggested`，在输入区上方或右侧 feedback timeline 中追加一张提示卡：

```text
今天可以收束了
你已经完成了今天的核心练习目标。要不要生成今日总结？
```

按钮：

- `结束并总结`
- `继续练一会儿`

### 完成态

完成后显示 summary card：

- 今天完成了什么
- 做得好的点
- 下次重点
- 可复用表达

输入区主按钮从 `Send` 变为 `今日已完成` 或隐藏。提供 `继续自由练习` 作为弱入口。

## 错误处理

- Completion evaluator 失败：不展示结束建议，用户仍可继续练习。
- Summary generator 失败：使用 fallback summary，仍允许标记完成。
- 完成接口重复调用：返回已有 completed summary，保持幂等。
- 没有 user turn 时调用完成接口：返回 400，并提示至少完成一轮练习后再结束。
- 已完成 session 收到普通 turn：第一版允许继续自由练习，但不改变 completed 状态。

## 测试策略

### 后端测试

- `SessionCompletionEvaluator` 在少于 3 个 user turns 时不建议结束。
- 达到软条件时返回 `completion_suggested`。
- `POST /api/sessions/{session_id}/complete` 会更新 `daily_sessions.ended_at` 和 `learning_plan.status=completed`。
- 完成接口重复调用保持幂等。
- 没有 user turn 时完成接口返回 400。
- Summary 生成失败时使用 fallback summary。

### 前端测试

- 有 user turn 后展示 `结束今日练习` 按钮。
- 点击手动结束后展示确认，再展示 Today Summary。
- turn stream 返回 `completion_suggested` 后展示软提示卡。
- 点击 `继续练一会儿` 后不再立即重复提示。
- 完成后输入区进入完成态，并提供 `继续自由练习`。

### 回归测试

- 原有对话流、feedback、语言解释不受影响。
- Daily Review 仍能处理 completed session。
- `get_current_learning_state` 能看到已完成 plan day。

## 分阶段实施

### Phase 1：手动结束闭环

- 新增 complete session API。
- 复用现有 `daily_sessions` 字段保存 summary。
- 前端加入 `结束今日练习` 按钮和完成态。

### Phase 2：Agent 软建议结束

- 新增 completion evaluator。
- turn stream meta 返回 completion suggestion。
- 前端展示软提示卡。

### Phase 3：复盘与计划联动优化

- Daily Review 优先读取 completed sessions。
- Orchestrator 在 today strategy 中识别前一天是否 completed。
- Growth Summary 展示最近完成情况。

## 成功标准

- 用户不会再进入无限对话而不知道何时结束。
- 用户可以主动结束当天任务，并看到清晰总结。
- Agent 能在合适时机建议结束，但不会强制停止。
- `learning_plan.status` 能稳定从 `in_progress` 推进到 `completed`。
- 完成后的 summary 能为后续 review、memory 和 plan adaptation 提供更明确的证据。
