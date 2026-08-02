# Prompt 单一来源 + 删除 Review 死链路 + 死代码清理 设计文档

> 日期：2026-06-22
> 目标：消除 prompt 双写不一致（隐藏功能性 bug），删除硬编码的 ReviewAgent 废弃链路，并清理已确认的死代码，让代码库更简洁、行为与代码意图一致。

## 背景与问题

复盘审计发现三类问题：

1. **Prompt 双写不一致（功能性 bug）**：每个 Agent 的默认 prompt 在 `agents.py` 内联和 `db.py` 的 `default_prompts` 各写一份。运行时 `get_prompt` 先读 DB，而 `db.py` 用 `INSERT OR IGNORE` 播种，导致一旦 DB 中存在旧版本，`agents.py` 中更新过的内联默认值永远不生效。已发现 4 处不一致（`goal_agent_system` 3 键 vs 8 键、`conversation_agent_user_template` 缺 `{practice_brief_context}`、`scenario_design_agent_system` 字段简略、`plan_adaptation_agent_system` 措辞），使刚做的 rich materials 在运行时被旧 prompt 悄悄削弱。

2. **ReviewAgent 硬编码废弃链路**：`ReviewAgent.generate_report` 完全是写死假数据（固定 report 字符串 + 半硬编码 errors + 完全硬编码 expressions），不调用任何 LLM。其链路（`/api/sessions/end`、前端 `endSession`、`save_review`、`ReviewResult` 类型）前端已不再触达，已被 `DailyReviewAgent` 体系取代。前端 `sendUserTurn`（非流式 `/api/sessions/turn` 的封装）也无前端调用。

3. **其余死代码**：`DeveloperStudio()` 外壳函数、`types.ts` 重复未用的 `AppView`、`GrowthPage.tsx` 死 import、`repositories.py` 仅测试用的 `create_session`/`get_next_pending_plan_day`、`ConversationAgent` 内重复的 prompt 模板。

## 设计目标

- Prompt 有且只有一个默认来源（代码），DB 只存"用户改过的覆盖版"。
- 更新代码里的默认 prompt 立即生效（无用户覆盖时），用户自定义不丢失。
- 彻底移除硬编码假数据 ReviewAgent 链路。
- 删除已确认的死代码，且不破坏现有测试与运行行为。

## 架构方案

### 1. Prompt 单一来源（`prompts.py`）

新建 `app/backend/app/prompts.py`，导出 `DEFAULT_PROMPTS: dict[str, str]`，集中存放全部默认 prompt 字面量，作为**唯一来源**，统一采用最新版本（goal 8 键、conversation user template 带 `{practice_brief_context}`、scenario design 完整字段、plan adaptation 措辞统一）。

**`get_prompt` 兜底改造**：在 `CoachRepository.get_prompt` 中，DB 没有该 name 时回退到 `DEFAULT_PROMPTS.get(name)`。语义变为「DB 有用户覆盖 → 用 DB；否则 → 用 `DEFAULT_PROMPTS`」。

**DB 播种策略改造**：`db.py` 不再内联 prompt 字面量，也不再无条件 `INSERT OR IGNORE` 播种默认 prompt。`prompts` 表只在用户通过 Studio 编辑保存时写入（`update_prompt` 改为 upsert）。移除 `db.py` 中针对 `inline_feedback_system` 的一次性 UPDATE 迁移逻辑（不再需要，因为默认值已是唯一来源）。

**`agents.py` 改造**：每个 Agent 删除内联大段 `or (...)` 默认字符串，改为 `self.get_prompt("name")`；`get_prompt_fn` 默认值改为始终能取到 `DEFAULT_PROMPTS`（构造器默认 `lambda name: DEFAULT_PROMPTS.get(name)`），保证即使没有传 repo 也能拿到默认 prompt。这样 `ConversationAgent` 的 `reply`/`reply_stream` 两份重复模板自然消除。

**`update_prompt` 改为 upsert**：因为 DB 不再预先播种所有 prompt 行，用户首次编辑某 prompt 时该行可能不存在，故 `update_prompt` 需 `INSERT ... ON CONFLICT(name) DO UPDATE`。

### 2. 删除 ReviewAgent 死链路

删除：
- `agents.py`：`ReviewAgent` 类
- `main.py`：`/api/sessions/end` 端点、对应 import（`ReviewAgent`、`EndSessionRequest`）
- `repositories.py`：`save_review` 方法
- `models.py`：`EndSessionRequest`
- 前端 `api.ts`：`sendUserTurn`、`endSession`、`ReviewResult` import
- 前端 `types.ts`：`ReviewResult` 类型
- 前端 `App.tsx`：`review`/`setReview` 状态及 `ReviewResult` import
- `App.test.tsx`：`endSession` mock
- 后端测试 `test_api.py`：引用 `/api/sessions/end` 的断言（如有）

**保留**：`/api/sessions/turn`（非流式 `add_user_turn`）端点及 `UserTurnRequest`。该端点本身不硬编码、仍是真实 LLM 调用，且被 `test_api.py` 多处用于构造测试数据，删除收益低、风险高，本次保留。前端虽不再调用它，但保留 API 不影响目标。死链路删除聚焦在真正硬编码假数据的 `ReviewAgent` + `/api/sessions/end` + `save_review` + `ReviewResult` 部分。

### 3. 清理其余死代码

- `DeveloperStudio.tsx`：删除无引用的 `DeveloperStudio()` 外壳函数，保留 `DeveloperTools`。
- `types.ts`：删除重复且未使用的 `AppView`（成员已过时）。
- `GrowthPage.tsx`：删除未使用的 `useEffect/useState` import。
- `repositories.py`：删除 `create_session`、`get_next_pending_plan_day`，并同步删除/调整其仅有的测试引用（`test_repositories.py` 中 `create_session` 用于构造数据的，改用 `get_or_create_session`）。

## 数据流

Prompt 解析新流程：
```
Agent.get_prompt(name)
  -> repo.get_prompt(name)
       -> DB 查询 prompts 表
            命中(用户覆盖) -> 返回 DB content
            未命中        -> 返回 DEFAULT_PROMPTS[name]
```

## 错误处理

- `get_prompt` 对未知 name 返回 `None`（`DEFAULT_PROMPTS.get` 自然返回 None），Agent 行为与现状一致。
- `update_prompt` upsert 保证用户编辑任意 prompt 都能落库。

## 测试策略

- **回归保险测试（核心）**：验证「无用户覆盖时，`get_prompt` 返回 `DEFAULT_PROMPTS` 的值」与「`DEFAULT_PROMPTS` 更新后立即生效」，这是当前 bug 的反向保险。
- **覆盖测试**：`update_prompt` 后 `get_prompt` 返回用户值（upsert 生效，即使该行原本不存在）。
- **Agent 默认 prompt 测试**：不传 repo 时 Agent 仍能从 `DEFAULT_PROMPTS` 取到 prompt。
- **删除链路测试**：移除 `/api/sessions/end` 相关测试断言，确保套件全绿。
- **前端测试**：`App.test.tsx` 移除 `endSession` mock 后仍通过。

## 执行方式

写实施计划（writing-plans）后，按子 Agent 驱动逐任务 TDD 执行，每个任务只提交相关 hunks，不触碰工作区无关改动。
