# Prompt 单一来源 + 删除 Review 死链路 + 死代码清理 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把所有默认 prompt 收敛到单一来源 `prompts.py`，让代码默认值立即生效，并删除硬编码的 ReviewAgent 死链路与其余已确认死代码。

**Architecture:** 新建 `app/backend/app/prompts.py` 导出 `DEFAULT_PROMPTS`，`CoachRepository.get_prompt` 在 DB 未命中时回退到 `DEFAULT_PROMPTS`；`db.py` 停止播种、`update_prompt` 改 upsert；`agents.py` 删除内联默认值。随后删除 ReviewAgent 及其链路与零散死代码。

**Tech Stack:** Python 3 / FastAPI / SQLite / pytest（后端）；React / TypeScript / vitest（前端）。

---

## 文件结构

- `app/backend/app/prompts.py`（新建）：唯一的默认 prompt 来源 `DEFAULT_PROMPTS: dict[str, str]`。
- `app/backend/app/repositories.py`（改）：`get_prompt` 回退、`update_prompt` upsert；删除 `save_review`、`create_session`、`get_next_pending_plan_day`。
- `app/backend/app/db.py`（改）：移除 `default_prompts` 内联与播种逻辑、移除 inline_feedback 一次性 UPDATE。
- `app/backend/app/agents.py`（改）：各 Agent 改用 `DEFAULT_PROMPTS` 兜底，删除内联默认串与 `ReviewAgent`。
- `app/backend/app/main.py`（改）：删除 `/api/sessions/end`、相关 import。
- `app/backend/app/models.py`（改）：删除 `EndSessionRequest`。
- 前端 `app/frontend/src/api.ts`、`types.ts`、`App.tsx`、`App.test.tsx`、`components/DeveloperStudio.tsx`、`components/GrowthPage.tsx`（改）。
- 测试：`app/backend/tests/test_repositories.py`、`test_api.py`、`test_agents.py`（改）。

---

### Task 1: 创建 prompts.py 单一来源 + get_prompt 回退

**Files:**
- Create: `app/backend/app/prompts.py`
- Modify: `app/backend/app/repositories.py:238-241`
- Test: `app/backend/tests/test_repositories.py`

- [ ] **Step 1: 写失败测试**

在 `app/backend/tests/test_repositories.py` 末尾追加：

```python
def test_get_prompt_falls_back_to_default_prompts(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    from app.prompts import DEFAULT_PROMPTS
    # 无用户覆盖时，返回代码默认值（而不是 None 或旧 DB 值）
    assert repo.get_prompt("goal_agent_system") == DEFAULT_PROMPTS["goal_agent_system"]
    # 未知 name 返回 None
    assert repo.get_prompt("nonexistent_prompt_name") is None


def test_get_prompt_prefers_user_override(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    repo.update_prompt("goal_agent_system", "用户自定义内容")
    assert repo.get_prompt("goal_agent_system") == "用户自定义内容"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd app/backend && python -m pytest tests/test_repositories.py::test_get_prompt_falls_back_to_default_prompts -v`
Expected: FAIL（`ModuleNotFoundError: app.prompts` 或断言不等）

- [ ] **Step 3: 创建 prompts.py**

创建 `app/backend/app/prompts.py`，内容为 `DEFAULT_PROMPTS = { ... }`，**逐字复制 `app/backend/app/agents.py` 当前各 Agent 内联默认串的最新版本**作为取值，键名与下列一致（这些键名来自 `db.py` 的 `default_prompts` 与 `agents.py` 的 `get_prompt(...)` 调用）：

```python
# app/backend/app/prompts.py
DEFAULT_PROMPTS: dict[str, str] = {
    "goal_agent_system": (
        # 复制 agents.py GoalAgent 内 8 键版本（含 skill_focus/communicative_task/
        # target_functions/success_criteria/brief_seed），不要用 db.py 的 3 键旧版
        ...
    ),
    "goal_agent_user_template": (...),
    "conversation_agent_system": (...),
    "conversation_agent_user_template": (
        # 复制 agents.py 含 {practice_brief_context} 段的版本
        ...
    ),
    "inline_feedback_system": (
        # 复制 agents.py InlineFeedbackAgent 内含 correction/guidance/language_help 的最新版
        ...
    ),
    "inline_feedback_user_template": (...),
    "language_support_system": (...),
    "daily_review_agent_system": (...),
    "daily_review_agent_user_template": (...),
    "memory_agent_system": (...),
    "memory_agent_user_template": (...),
    "plan_adaptation_agent_system": (
        # 统一为 agents.py 版本（"未来练习计划"），措辞与 db.py 二选一，取 agents.py
        ...
    ),
    "plan_adaptation_agent_user_template": (...),
    "scenario_design_agent_system": (
        # 复制 agents.py 完整 lesson pack 字段版本，不要用 db.py 简略版
        ...
    ),
    "scenario_design_agent_user_template": (...),
}
```

> 实施者注意：以上每个 `...` 必须替换为 agents.py 中对应的真实字符串字面量；4 处不一致项一律采用 agents.py 的较新/较全版本。

- [ ] **Step 4: 修改 get_prompt 回退**

把 `app/backend/app/repositories.py` 中 `get_prompt` 改为：

```python
    def get_prompt(self, name: str) -> str | None:
        from app.prompts import DEFAULT_PROMPTS
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT content FROM prompts WHERE name = ?", (name,)).fetchone()
            if row:
                return row["content"]
        return DEFAULT_PROMPTS.get(name)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd app/backend && python -m pytest tests/test_repositories.py::test_get_prompt_falls_back_to_default_prompts tests/test_repositories.py::test_get_prompt_prefers_user_override -v`
Expected: PASS（注意此时 `update_prompt` 尚未 upsert，第二个测试依赖现有 DB 行；若失败留待 Task 2 修复并在此标记）

> 若 `test_get_prompt_prefers_user_override` 因 `update_prompt` 对不存在行返回 False 而失败，先在本任务把该断言改为依赖 Task 2 的 upsert，或将该测试移动到 Task 2。推荐：本任务只提交 fallback 测试，override 测试放入 Task 2。

- [ ] **Step 6: Commit**

```bash
git add app/backend/app/prompts.py app/backend/app/repositories.py app/backend/tests/test_repositories.py
git commit -m "feat: add single-source default prompts with repo fallback"
```

---

### Task 2: db.py 停止播种 + update_prompt upsert

**Files:**
- Modify: `app/backend/app/db.py:200-313`
- Modify: `app/backend/app/repositories.py:243-250`
- Test: `app/backend/tests/test_repositories.py`

- [ ] **Step 1: 写失败测试**

在 `test_repositories.py` 追加（若 Task 1 未加 override 测试，这里加）：

```python
def test_update_prompt_upserts_when_row_absent(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    # init_db 不再播种，prompts 表初始为空
    assert repo.update_prompt("goal_agent_system", "覆盖内容") is True
    assert repo.get_prompt("goal_agent_system") == "覆盖内容"


def test_init_db_does_not_seed_prompts(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    from app.db import connect
    with connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM prompts").fetchone()["c"]
    assert count == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd app/backend && python -m pytest tests/test_repositories.py::test_init_db_does_not_seed_prompts tests/test_repositories.py::test_update_prompt_upserts_when_row_absent -v`
Expected: FAIL（当前 init_db 会播种、update_prompt 对缺失行返回 False）

- [ ] **Step 3: 修改 db.py**

删除 `app/backend/app/db.py` 中 `default_prompts = { ... }` 整段字典定义、其后的 `for name, content in default_prompts.items(): INSERT OR IGNORE ...` 循环，以及针对 `inline_feedback_system` 的 `UPDATE prompts ...` 一次性迁移块。保留 `prompts` 表的 `CREATE TABLE`（schema 不动）和其余 ALTER 迁移。`init_db` 结尾保留 `connection.commit()`。

- [ ] **Step 4: 修改 update_prompt 为 upsert**

```python
    def update_prompt(self, name: str, content: str) -> bool:
        with connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO prompts (name, content, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    content = excluded.content,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (name, content),
            )
            connection.commit()
            return True
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd app/backend && python -m pytest tests/test_repositories.py -v`
Expected: PASS（全部 repository 测试通过）

- [ ] **Step 6: Commit**

```bash
git add app/backend/app/db.py app/backend/app/repositories.py app/backend/tests/test_repositories.py
git commit -m "refactor: stop seeding prompts and make update_prompt upsert"
```

---

### Task 3: agents.py 改用 DEFAULT_PROMPTS 兜底

**Files:**
- Modify: `app/backend/app/agents.py`（GoalAgent / ConversationAgent / InlineFeedbackAgent / LanguageSupportAgent / DailyReviewAgent / MemoryAgent / PlanAdaptationAgent / ScenarioDesignAgent）
- Test: `app/backend/tests/test_agents.py`

- [ ] **Step 1: 写失败测试**

在 `app/backend/tests/test_agents.py` 追加：

```python
def test_agent_uses_default_prompts_without_repo():
    from app.agents import GoalAgent
    from app.prompts import DEFAULT_PROMPTS

    class CapturingLLM:
        def __init__(self):
            self.system_prompt = None
        def complete(self, system_prompt, user_prompt):
            self.system_prompt = system_prompt
            return "[]"

    llm = CapturingLLM()
    GoalAgent(llm).generate_plan("Travel", 1, 15, "Beginner")
    assert llm.system_prompt == DEFAULT_PROMPTS["goal_agent_system"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd app/backend && python -m pytest tests/test_agents.py::test_agent_uses_default_prompts_without_repo -v`
Expected: FAIL（当前默认 `get_prompt` 为 `lambda x: None`，system_prompt 走内联串而非 DEFAULT_PROMPTS；两者目前文本相同则可能 PASS——若 PASS，仍继续 Step 3 完成去重）

- [ ] **Step 3: 修改 agents.py 各 Agent 构造器与取值**

在文件顶部加 `from app.prompts import DEFAULT_PROMPTS`。把每个 Agent 的：

```python
        self.get_prompt = get_prompt_fn or (lambda x: None)
```

改为：

```python
        self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))
```

并把每个方法里的：

```python
        system_prompt = self.get_prompt("xxx") or ("……内联默认串……")
```

改为：

```python
        system_prompt = self.get_prompt("xxx")
```

对 `user_template`、`conversation_agent_*`、`inline_feedback_*`、`language_support_system`、`daily_review_*`、`memory_*`、`plan_adaptation_*`、`scenario_design_*` 全部同样处理，删除 `or (...)` 内联默认串。`ConversationAgent.reply` 与 `reply_stream` 的两份重复模板随之消除（都改为 `self.get_prompt(...)`）。

> 注意：`DailyReviewAgent/MemoryAgent/PlanAdaptationAgent/ScenarioDesignAgent` 的 `__init__(self, llm_provider, get_prompt_fn)` 当前 `get_prompt_fn` 为必填位置参数。为支持"不传 repo 也能用默认"，把它们改为 `def __init__(self, llm_provider, get_prompt_fn=None): self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))`，与其它 Agent 一致。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd app/backend && python -m pytest tests/test_agents.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_agents.py
git commit -m "refactor: agents use single-source default prompts"
```

---

### Task 4: 删除 ReviewAgent 死链路（后端）

**Files:**
- Modify: `app/backend/app/agents.py:416-454`（删除 `ReviewAgent`）
- Modify: `app/backend/app/main.py:17,25,440-447`
- Modify: `app/backend/app/repositories.py:265-...`（删除 `save_review`）
- Modify: `app/backend/app/models.py:28`（删除 `EndSessionRequest`）
- Test: `app/backend/tests/test_api.py`, `app/backend/tests/test_agents.py`

- [ ] **Step 1: 写失败测试**

在 `test_api.py` 追加（断言端点已不存在）：

```python
def test_sessions_end_endpoint_removed(client):
    resp = client.post("/api/sessions/end", json={"session_id": 1})
    assert resp.status_code == 404
```

> `client` fixture 若不存在，参照 `test_api.py` 既有用例的 client 构造方式编写。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd app/backend && python -m pytest tests/test_api.py::test_sessions_end_endpoint_removed -v`
Expected: FAIL（端点当前返回 200）

- [ ] **Step 3: 删除后端代码**

1. `agents.py`：删除整个 `class ReviewAgent:`（约 416-454 行）。
2. `main.py`：从 import 块删除 `ReviewAgent`（第 17 行）；从 `from app.models import ...` 删除 `EndSessionRequest`（第 25 行）；删除 `@app.post("/api/sessions/end")` 的 `end_session` 函数（440-447 行）。
3. `repositories.py`：删除 `save_review` 方法整段。
4. `models.py`：删除 `class EndSessionRequest(BaseModel): ...`。
5. 检查并删除 `test_agents.py` 中对 `ReviewAgent` 的任何 import/用例（如有）。
6. `test_api.py`：若有调用 `/api/sessions/end` 的旧断言，删除或改写（保留 `/api/sessions/turn` 相关用例不动）。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd app/backend && python -m pytest tests/test_api.py tests/test_agents.py tests/test_repositories.py -v`
Expected: PASS（含新增的 removed 测试）

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/app/main.py app/backend/app/repositories.py app/backend/app/models.py app/backend/tests/test_api.py app/backend/tests/test_agents.py
git commit -m "refactor: remove hardcoded ReviewAgent dead chain"
```

---

### Task 5: 删除前端 Review 残留 + 零散死代码

**Files:**
- Modify: `app/frontend/src/api.ts:1,69-84,161-171`
- Modify: `app/frontend/src/types.ts:92-107,109`
- Modify: `app/frontend/src/App.tsx:9,18`
- Modify: `app/frontend/src/App.test.tsx:15`
- Modify: `app/frontend/src/components/DeveloperStudio.tsx:250-256`
- Modify: `app/frontend/src/components/GrowthPage.tsx:1`
- Test: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: 删除前端死代码**

1. `api.ts`：删除 `sendUserTurn` 函数（69-84）、`endSession` 函数（161-171）；从第 1 行 import 删除 `ReviewResult`。
2. `types.ts`：删除 `ReviewResult` 类型（92-107）、删除重复未用的 `AppView`（109）。
3. `App.tsx`：第 9 行 import 删除 `ReviewResult`；删除 `const [review, setReview] = useState<ReviewResult | null>(null);`（18）及其全部引用（确认 `review`/`setReview` 在 App.tsx 其余处未被使用——前面 grep 仅命中第 18 行）。
4. `App.test.tsx`：删除 `endSession: vi.fn(),`（15）。
5. `DeveloperStudio.tsx`：删除无引用的 `export function DeveloperStudio()` 外壳（250-256），保留 `DeveloperTools`。
6. `GrowthPage.tsx`：删除第 1 行未使用的 `import { useEffect, useState } from "react";`。

- [ ] **Step 2: 运行前端测试 + 类型检查**

Run: `cd app/frontend && PATH=/usr/local/bin:$PATH npx vitest run src/App.test.tsx`
Expected: PASS

Run: `cd app/frontend && PATH=/usr/local/bin:$PATH npx tsc --noEmit`
Expected: 无报错（确认删除后无悬挂引用）

- [ ] **Step 3: Commit**

```bash
git add app/frontend/src/api.ts app/frontend/src/types.ts app/frontend/src/App.tsx app/frontend/src/App.test.tsx app/frontend/src/components/DeveloperStudio.tsx app/frontend/src/components/GrowthPage.tsx
git commit -m "refactor: remove review remnants and dead frontend code"
```

---

### Task 6: 删除 repositories.py 仅测试用方法

**Files:**
- Modify: `app/backend/app/repositories.py:118-125`（`create_session`）、`402-413`（`get_next_pending_plan_day`）
- Test: `app/backend/tests/test_repositories.py:149,176,203,216-240`

- [ ] **Step 1: 调整测试改用 get_or_create_session**

把 `test_repositories.py` 中 3 处 `repo.create_session(plan[0]["id"], 1, "Airport")` 改为 `repo.get_or_create_session(plan[0]["id"], 1, "Airport")`（签名相同）。删除 `test_repository_reads_loop_state_for_next_practice` 中对 `get_next_pending_plan_day` 的断言行（240），若该测试删除后无剩余断言则整体删除该测试函数。

- [ ] **Step 2: 运行测试确认仍通过（用替代方法）**

Run: `cd app/backend && python -m pytest tests/test_repositories.py -v`
Expected: PASS

- [ ] **Step 3: 删除生产死方法**

删除 `repositories.py` 的 `create_session`（118-125）与 `get_next_pending_plan_day`（402-413）。

- [ ] **Step 4: 运行全部后端测试确认通过**

Run: `cd app/backend && python -m pytest -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/repositories.py app/backend/tests/test_repositories.py
git commit -m "refactor: remove test-only repository methods"
```

---

## Self-Review

**Spec coverage:**
- Prompt 单一来源 → Task 1/2/3 ✓
- get_prompt 回退 → Task 1 ✓
- DB 停止播种 + upsert → Task 2 ✓
- agents 去内联默认 → Task 3 ✓
- 删除 ReviewAgent 链路 → Task 4（后端）+ Task 5（前端）✓
- 其余死代码（DeveloperStudio/AppView/GrowthPage import）→ Task 5 ✓
- create_session/get_next_pending_plan_day → Task 6 ✓
- 回归保险测试 → Task 1（fallback）+ Task 2（不播种 & upsert）✓

**Type consistency:** `DEFAULT_PROMPTS` 键名在所有任务统一；`get_prompt` 签名不变（`str | None`）；`update_prompt` 返回 `bool` 不变；Agent 构造器统一 `get_prompt_fn=None` 兜底。

**Placeholder scan:** prompts.py 的 `...` 是"复制现有字面量"的明确指令而非待办，已标注实施者注意；其余步骤均含可执行代码与命令。
