# Prompt 单一来源 + 删除 Review 死链路 + 死代码清理 设计文档

> 日期：2026-06-22
> 目标：消除 prompt 双写不一致（隐藏功能 bug），删除硬编码的 ReviewAgent 废弃链路，并清理迭代遗留的死代码，使代码库更简洁、行为更可预期。

## 背景与问题

复盘审计发现两个真问题和一批死代码：

1. **Prompt 双写不一致（隐藏功能 bug）**：每个 Agent 的默认 prompt 在 `agents.py`（内联 `or (...)` 兜底）和 `db.py`（`default_prompts` 字典）各写一份。运行时 `get_prompt` 优先读 DB，而 DB 用 `INSERT OR IGNORE` 播种，导致 `agents.py` 中更新过的默认值永远不生效。已知 4 处不一致会悄悄削弱刚做的 rich learning materials：
   - `goal_agent_system`：DB 只要求 3 个键，代码要求 8 个键 → rich plan 字段失效。
   - `conversation_agent_user_template`：DB 版缺 `{practice_brief_context}` 段 → lesson pack 注入被削弱。
   - `scenario_design_agent_system`：DB 版字段比代码简略 → lesson pack 质量被拉低。
   - `plan_adaptation_agent_system`：措辞不一致。

2. **ReviewAgent 硬编码假数据链路**：`ReviewAgent.generate_report` 不调用 LLM，返回写死的 AI PM 相关 errors/expressions。其整条链路（`/api/sessions/end`、`/api/sessions/turn` 非流式、`sendUserTurn`、`endSession`、`save_review`、`ReviewResult`）前端均不触达，已被 `DailyReviewAgent` 体系取代。

3. **其余死代码**：`DeveloperStudio()` 外壳函数、`types.ts` 重复未用的 `AppView`、`GrowthPage.tsx` 死 import、`App.tsx` 未用的 `review` state、`repositories.py` 的 `create_session`/`get_next_pending_plan_day`（仅测试用）。

## 设计决策（已与用户确认）

- **Prompt 架构**：单一来源 + 只存覆盖。
- **Review 链路**：直接删除整条废弃链路。

## 方案一：Prompt 单一来源（Single Source of Truth）

### 架构

- 新建 `app/backend/app/prompts.py`，导出 `DEFAULT_PROMPTS: dict[str, str]`，作为所有默认 prompt 的**唯一来源**，内容统一为各 Agent 当前最新版本（合并 4 处不一致，取功能最全的版本）。
- `db.py` 不再内联 prompt 字面量。`init_db` 不再无条件播种默认 prompt（移除 `INSERT OR IGNORE` 批量播种与 `inline_feedback_system` 的迁移 UPDATE），DB 的 `prompts` 表**只存用户在 Studio 手动编辑保存的覆盖版**。
- `agents.py` 各 Agent 删除内联 `or (...)` 大段默认字符串，改为统一通过注入的 `get_prompt` 取值。

### `get_prompt` 回退逻辑

`get_prompt(name)` 的语义变为：
1. 查 DB `prompts` 表，有用户覆盖 → 返回 DB 内容；
2. 否则 → 返回 `DEFAULT_PROMPTS[name]`；
3. name 不存在于两者 → 返回 `None`（理论上不应发生）。

实现位置：`CoachRepository.get_prompt`（`repositories.py`）改为读 DB 命中即返回，未命中回退 `DEFAULT_PROMPTS`。这样所有调用方（`main.py` 注入 `repo.get_prompt`）自动获得正确回退，Agent 内不再需要内联默认值。

### `get_all_prompts`（Studio 展示）

Studio 需要展示「全部 prompt 及其当前生效内容」。改为：以 `DEFAULT_PROMPTS` 的键全集为基准，对每个 key 返回「DB 覆盖版（若有）否则默认版」，并标注 `is_overridden` 布尔，方便 UI 显示是否被用户改过。

### 数据流

```
启动 init_db: 只建表，不再播种默认 prompt
Studio 读取:  get_all_prompts() -> 合并 DEFAULT_PROMPTS + DB 覆盖
Agent 运行:   get_prompt(name) -> DB 覆盖 ?? DEFAULT_PROMPTS[name]
用户编辑保存: update_prompt(name, content) -> INSERT OR REPLACE 进 DB
```

注意：`update_prompt` 当前用 `UPDATE ... WHERE name=?`，在「DB 不再预先播种」后，第一次保存某 prompt 时该行不存在，`UPDATE` 会失败（rowcount=0）。需改为 `INSERT INTO prompts(name, content) ... ON CONFLICT(name) DO UPDATE`（upsert），保证首次覆盖也能写入。

### 兼容性

- 旧 DB 里已有 `INSERT OR IGNORE` 播种的 prompt 行：这些行会被 `get_prompt` 当作「用户覆盖」继续返回，可能是旧内容。为避免旧播种行继续掩盖新默认值，`init_db` 增加一次性清理：删除 `prompts` 表中与对应 `DEFAULT_PROMPTS` 旧版本完全相同（即从未被用户真正改动、仅是历史播种）的行。**风险**：无法 100% 区分「用户手动改成恰好等于某旧默认值」与「历史播种」。鉴于本产品为单人自用且用户明确要默认值生效，采用保守策略：仅当 DB 行内容能在一组「已知历史默认值快照」中找到匹配时才删除；找不到匹配（说明是用户自定义）则保留。已知历史默认值快照内联在 `db.py` 的一次性迁移逻辑中。

## 方案二：删除 ReviewAgent 死链路

删除以下内容及其测试引用：

- `agents.py`：`ReviewAgent` 类（`generate_report`）。
- `main.py`：`/api/sessions/end` 端点（`end_session`）、`/api/sessions/turn` 非流式端点（`add_user_turn`）、`ReviewAgent` import。
- `models.py`：`EndSessionRequest`（若无其他引用）。
- `repositories.py`：`save_review`（仅服务该链路）。
- `api.ts`：`sendUserTurn`、`endSession`、`ReviewResult` import。
- `types.ts`：`ReviewResult` 类型。
- `App.tsx`：未使用的 `review`/`setReview` state 及 `ReviewResult` import。
- 后端测试：`test_api.py` 中调用 `/api/sessions/turn`（非流式）和 `/api/sessions/end` 的用例改为使用 `/api/sessions/turn/stream`，或删除针对已删端点的断言。

保留：`/api/sessions/turn/stream`（前端实际使用）、`DailyReviewAgent` 全链路、`UserTurnRequest`（stream 端点仍用）。

## 方案三：清理其余死代码

- `DeveloperStudio.tsx`：删除无引用的 `DeveloperStudio()` 外壳函数，保留 `DeveloperTools`。
- `types.ts`：删除重复且未用的 `AppView`（实际使用的是 `AppShell.tsx` 的 `AppView`）。
- `GrowthPage.tsx`：删除未使用的 `import { useEffect, useState }`。
- `repositories.py`：删除 `create_session`、`get_next_pending_plan_day`（仅测试引用），同步删除/调整 `test_repositories.py` 中对应用例。

## 测试策略

核心回归测试（针对本次 bug 的反向保险）：

1. **prompt 默认值即时生效**：`DEFAULT_PROMPTS` 更新后，无 DB 覆盖时 `repo.get_prompt(name)` 返回 `DEFAULT_PROMPTS[name]`。
2. **用户覆盖优先**：写入 DB 覆盖后，`get_prompt` 返回覆盖值；删除覆盖后回退默认值。
3. **首次保存可写入**：对从未播种的 prompt 调用 `update_prompt` 能成功 upsert（rowcount>0 且 `get_prompt` 返回新值）。
4. **get_all_prompts 完整性**：返回覆盖 `DEFAULT_PROMPTS` 全部键，并正确标注 `is_overridden`。
5. **删除链路回归**：`/api/sessions/end`、`/api/sessions/turn`（非流式）返回 404；`/api/sessions/turn/stream` 仍正常。
6. 既有 45 后端 + 21 前端测试在调整后保持通过。

## 非目标（YAGNI）

- 不重构 `ConversationAgent` 的 `reply`/`reply_stream` 结构（重复 prompt 模板随 prompts.py 抽取自然消除即可，不额外抽函数）。
- 不实现 GrowthPage 的真实功能（仅清理死 import）。
- 不动 docs 历史文档（仅本次新增 spec/plan）。
- 不改 Onboarding 输入字段。
