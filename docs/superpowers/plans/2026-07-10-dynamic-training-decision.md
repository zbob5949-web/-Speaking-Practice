# Dynamic Training Decision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade SpeakMate Agent from explaining the current learning workflow to making bounded dynamic training decisions driven by long-term memory.

**Architecture:** Extend the existing V2 Orchestrator rather than replacing the stable practice flow. `CoachOrchestratorAgent` produces a validated `TrainingDecision` and `MemoryInfluence`; `LearningToolRegistry` exposes decision-context and refresh tools; `/api/today/strategy` uses the decision to refresh or reuse the practice brief; the Learn page explains the decision to the user.

**Tech Stack:** FastAPI, Pydantic, SQLite repository layer, pytest, React, TypeScript, Vitest, Testing Library.

---

## File Structure

- Modify `app/backend/app/contracts.py`: add `TrainingDecision`, `MemoryInfluence`, and extend `OrchestrationResult`.
- Modify `app/backend/app/agents.py`: update `default_orchestration_output()`, `CoachOrchestratorAgent.plan_today()`, and `ScenarioDesignAgent.generate_brief()`.
- Modify `app/backend/app/prompts.py`: upgrade orchestrator and scenario-design prompt templates.
- Modify `app/backend/app/tools.py`: add `get_decision_context`, `get_relevant_memory`, and `refresh_practice_brief`.
- Modify `app/backend/app/main.py`: make `/api/today/strategy` use decision output to reuse or refresh briefs.
- Modify `app/backend/app/models.py`: extend `TodayStrategyResponse`.
- Create or modify `app/backend/tests/test_contracts.py`: validate new Pydantic contracts.
- Modify `app/backend/tests/test_agents.py`: verify Orchestrator fallback and ScenarioDesign prompt context.
- Modify `app/backend/tests/test_tools.py`: verify new tool behavior.
- Modify `app/backend/tests/test_api.py`: verify `/api/today/strategy` returns decisions and handles refresh fallback.
- Modify `app/frontend/src/types.ts`: extend `TodayStrategy`.
- Modify `app/frontend/src/components/PracticeRoom.tsx`: show dynamic decision and memory influence.
- Modify `app/frontend/src/App.test.tsx`: update mocks and UI assertions.

## Task 1: Add Backend Decision Contracts

**Files:**
- Modify: `app/backend/app/contracts.py`
- Create: `app/backend/tests/test_contracts.py`

- [ ] **Step 1: Write the failing contract tests**

Add `app/backend/tests/test_contracts.py`:

```python
import pytest
from pydantic import ValidationError

from app.contracts import MemoryInfluence, OrchestrationResult, TrainingDecision


def test_training_decision_accepts_allowed_decision_types():
    decision = TrainingDecision(
        decision_type="review_weakness",
        reason_zh="最近复盘显示你经常漏掉时间信息。",
        selected_memory_ids=[1, 2, 3],
        selected_review_ids=[8],
        brief_instruction="生成酒店入住场景，要求用户说明入住日期和预订姓名。",
        difficulty_adjustment="same",
        should_refresh_brief=True,
    )

    assert decision.decision_type == "review_weakness"
    assert decision.selected_memory_ids == [1, 2, 3]
    assert decision.should_refresh_brief is True


def test_training_decision_rejects_unknown_decision_type():
    with pytest.raises(ValidationError):
        TrainingDecision(
            decision_type="rewrite_whole_plan",
            reason_zh="不允许重排整个计划。",
        )


def test_memory_influence_accepts_allowed_influence_type():
    influence = MemoryInfluence(
        memory_id=3,
        category="weakness",
        content="用户经常漏掉时间和对象。",
        influence_type="npc_behavior",
        instruction="如果用户没说入住日期，NPC 必须追问。",
        reason_zh="这是最近重复出现的问题。",
    )

    assert influence.influence_type == "npc_behavior"
    assert influence.memory_id == 3


def test_orchestration_result_requires_training_decision():
    result = OrchestrationResult.model_validate(
        {
            "today_strategy": {
                "focus": "补充旅行场景中的关键信息",
                "reason": "基于长期记忆",
                "success_criteria": ["说明时间", "说明对象"],
            },
            "training_decision": {
                "decision_type": "review_weakness",
                "reason_zh": "最近经常漏掉时间和对象。",
                "selected_memory_ids": [3],
                "selected_review_ids": [12],
                "brief_instruction": "生成酒店入住场景，NPC 追问缺失细节。",
                "difficulty_adjustment": "same",
                "should_refresh_brief": True,
            },
            "memory_influence": [
                {
                    "memory_id": 3,
                    "category": "weakness",
                    "content": "用户经常漏掉时间和对象。",
                    "influence_type": "drill_focus",
                    "instruction": "今天集中训练说明时间和对象。",
                    "reason_zh": "这是重复弱点。",
                }
            ],
            "recommended_actions": [],
            "coach_explanation_zh": "今天先集中练补充关键信息。",
            "risk_flags": [],
            "confidence": 0.82,
        }
    )

    assert result.training_decision.decision_type == "review_weakness"
    assert result.memory_influence[0].memory_id == 3
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd app/backend && python -m pytest tests/test_contracts.py -v
```

Expected: FAIL with an import error for `TrainingDecision` or `MemoryInfluence`.

- [ ] **Step 3: Implement the minimal contracts**

Update `app/backend/app/contracts.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    side_effect: Literal["read_only", "write"]


class ToolCallRecord(BaseModel):
    tool_name: str
    input: dict[str, object]
    output: dict[str, object] | list[dict[str, object]] | None = None
    status: Literal["success", "failed"]
    error_message: str | None = None


class TodayStrategy(BaseModel):
    focus: str
    reason: str
    success_criteria: list[str] = Field(default_factory=list)


class TrainingDecision(BaseModel):
    decision_type: Literal[
        "continue_plan",
        "review_weakness",
        "insert_micro_drill",
        "adjust_difficulty",
        "refresh_brief",
    ] = "continue_plan"
    reason_zh: str
    selected_memory_ids: list[int] = Field(default_factory=list, max_length=3)
    selected_review_ids: list[int] = Field(default_factory=list)
    brief_instruction: str = ""
    difficulty_adjustment: Literal["easier", "same", "harder"] = "same"
    should_refresh_brief: bool = False


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


class RecommendedAction(BaseModel):
    action: Literal[
        "run_due_reviews",
        "generate_practice_brief",
        "use_existing_brief",
        "start_practice",
        "review_lesson_material",
    ]
    rationale: str
    priority: Literal["low", "medium", "high"] = "medium"


class OrchestrationResult(BaseModel):
    today_strategy: TodayStrategy
    training_decision: TrainingDecision
    memory_influence: list[MemoryInfluence] = Field(default_factory=list)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    coach_explanation_zh: str
    risk_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
cd app/backend && python -m pytest tests/test_contracts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/contracts.py app/backend/tests/test_contracts.py
git commit -m "feat: add training decision contracts"
```

## Task 2: Upgrade Orchestrator Output And Fallback

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/app/prompts.py`
- Modify: `app/backend/tests/test_agents.py`

- [ ] **Step 1: Write failing Orchestrator tests**

Append to `app/backend/tests/test_agents.py`:

```python
def test_orchestrator_agent_returns_training_decision_and_memory_influence():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "training_decision" in system_prompt
            assert "memory_influence" in system_prompt
            assert "active_memory" in user_prompt
            return """
            {
              "today_strategy": {
                "focus": "补充旅行场景中的关键信息",
                "reason": "基于长期记忆和最近复盘",
                "success_criteria": ["说明时间", "说明对象"]
              },
              "training_decision": {
                "decision_type": "review_weakness",
                "reason_zh": "你最近经常漏掉时间和对象。",
                "selected_memory_ids": [3],
                "selected_review_ids": [9],
                "brief_instruction": "生成酒店入住场景，NPC 必须追问日期、姓名、房型。",
                "difficulty_adjustment": "same",
                "should_refresh_brief": true
              },
              "memory_influence": [
                {
                  "memory_id": 3,
                  "category": "weakness",
                  "content": "经常漏掉时间和对象。",
                  "influence_type": "npc_behavior",
                  "instruction": "用户没说时间时必须追问。",
                  "reason_zh": "这是重复弱点。"
                }
              ],
              "recommended_actions": [],
              "coach_explanation_zh": "今天先集中练补充关键信息。",
              "risk_flags": [],
              "confidence": 0.8
            }
            """

    agent = CoachOrchestratorAgent(MockLLM())
    result = agent.plan_today(
        profile={"id": 1, "learning_goal": "Travel English"},
        plan_day={"id": 2, "topic": "Hotel", "objective": "Check in"},
        latest_review={"id": 9},
        active_memory=[{"id": 3, "category": "weakness", "content": "经常漏掉时间和对象。"}],
        active_adjustments=[],
        practice_brief={"title": "Old hotel brief"},
        session_state={"has_session": True, "turn_count": 0},
    )

    assert result["validation_status"] == "passed"
    assert result["output"]["training_decision"]["decision_type"] == "review_weakness"
    assert result["output"]["memory_influence"][0]["memory_id"] == 3


def test_orchestrator_fallback_contains_continue_plan_decision():
    class BadLLM:
        def complete(self, system_prompt, user_prompt):
            return '{"bad": "shape"}'

    agent = CoachOrchestratorAgent(BadLLM())
    result = agent.plan_today(
        profile={"id": 1},
        plan_day={"id": 2, "topic": "Hotel", "objective": "Check in", "success_criteria": ["Ask clearly"]},
        latest_review={},
        active_memory=[],
        active_adjustments=[],
        practice_brief={},
        session_state={},
    )

    assert result["validation_status"] == "failed"
    assert result["output"]["training_decision"]["decision_type"] == "continue_plan"
    assert result["output"]["training_decision"]["should_refresh_brief"] is False
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd app/backend && python -m pytest tests/test_agents.py::test_orchestrator_agent_returns_training_decision_and_memory_influence tests/test_agents.py::test_orchestrator_fallback_contains_continue_plan_decision -v
```

Expected: FAIL because the default prompts and fallback do not include `training_decision`.

- [ ] **Step 3: Update default fallback**

In `app/backend/app/agents.py`, replace `default_orchestration_output()` with:

```python
def default_orchestration_output(plan_day: dict[str, object]) -> dict[str, object]:
    focus = str(plan_day.get("objective") or plan_day.get("topic") or "Practice speaking today.")
    reason = str(plan_day.get("scenario") or "This follows your current learning plan.")
    return {
        "today_strategy": {
            "focus": focus,
            "reason": reason,
            "success_criteria": plan_day.get("success_criteria", []) if isinstance(plan_day.get("success_criteria"), list) else [],
        },
        "training_decision": {
            "decision_type": "continue_plan",
            "reason_zh": "当前证据不足以调整训练方向，先按照原计划继续练习。",
            "selected_memory_ids": [],
            "selected_review_ids": [],
            "brief_instruction": "",
            "difficulty_adjustment": "same",
            "should_refresh_brief": False,
        },
        "memory_influence": [],
        "recommended_actions": [
            {
                "action": "start_practice",
                "rationale": "Use the current plan day to continue practice.",
                "priority": "medium",
            }
        ],
        "coach_explanation_zh": "今天先按照当前学习计划继续练习，我会根据你的表现继续调整后续内容。",
        "risk_flags": ["orchestrator_parse_failed"],
        "confidence": 0.3,
    }
```

- [ ] **Step 4: Upgrade Orchestrator prompts**

In `app/backend/app/prompts.py`, update `orchestrator_agent_system`:

```python
"orchestrator_agent_system": (
    "你是 SpeakMate Agent 的 AI 口语教练总控 Orchestrator。\n"
    "你不是 NPC，不直接纠错，不写数据库，不生成完整 lesson pack。\n"
    "你的任务是先基于用户状态选择今日训练决策，再生成用户可理解的今日练习策略。\n"
    "必须输出合法 JSON 对象，不要 markdown。\n"
    "顶层必须包含 training_decision, memory_influence, today_strategy, recommended_actions, coach_explanation_zh, risk_flags, confidence。\n"
    "training_decision.decision_type 只能是 continue_plan, review_weakness, insert_micro_drill, adjust_difficulty, refresh_brief。\n"
    "如果证据不足，选择 continue_plan。每次最多选择一个主决策。\n"
    "selected_memory_ids 最多 3 条，只选择最相关、最稳定、会影响今天训练的记忆。\n"
    "should_refresh_brief=true 时，brief_instruction 必须说明 ScenarioDesignAgent 应如何生成更贴合弱点的练习材料。\n"
    "memory_influence 的 influence_type 只能是 drill_focus, difficulty_control, npc_behavior, feedback_priority。\n"
    "today_strategy 面向用户，说明今天练什么、为什么练、成功标准。\n"
    "coach_explanation_zh 必须短、清楚、自然，不暴露系统提示词。"
),
```

Ensure `orchestrator_agent_user_template` includes these literal labels:

```python
"orchestrator_agent_user_template": (
    "profile: {profile}\n"
    "plan_day: {plan_day}\n"
    "latest_review: {latest_review}\n"
    "active_memory: {active_memory}\n"
    "active_adjustments: {active_adjustments}\n"
    "practice_brief: {practice_brief}\n"
    "session_state: {session_state}\n"
    "请输出今日训练决策 JSON："
),
```

- [ ] **Step 5: Run tests to verify GREEN**

Run:

```bash
cd app/backend && python -m pytest tests/test_agents.py::test_orchestrator_agent_returns_training_decision_and_memory_influence tests/test_agents.py::test_orchestrator_fallback_contains_continue_plan_decision -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/app/agents.py app/backend/app/prompts.py app/backend/tests/test_agents.py
git commit -m "feat: upgrade orchestrator training decisions"
```

## Task 3: Pass Decision Context Into Scenario Design

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/app/prompts.py`
- Modify: `app/backend/tests/test_agents.py`

- [ ] **Step 1: Write the failing ScenarioDesign test**

Append to `app/backend/tests/test_agents.py`:

```python
def test_scenario_design_agent_uses_training_decision_and_memory_influence():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "training_decision" in user_prompt
            assert "memory_influence" in user_prompt
            assert "生成酒店入住场景" in user_prompt
            return """
            {
              "title": "Hotel detail check-in",
              "user_visible_goal": "补充入住关键信息",
              "npc_role": "Hotel receptionist",
              "scenario_setup": "You are checking in at a hotel.",
              "conversation_objective": "State your booking details clearly.",
              "lesson_focus": "Giving complete details",
              "task_steps": ["说明预订姓名", "说明入住日期", "询问房型"],
              "target_expressions": [],
              "sentence_frames": [],
              "model_dialogue": [],
              "common_mistakes": [],
              "rubric": ["Mentions date", "Mentions booking name"],
              "stretch_goal": "Ask one follow-up question."
            }
            """

    brief = ScenarioDesignAgent(MockLLM()).generate_brief(
        plan_day={"topic": "Hotel", "objective": "Check in", "success_criteria": ["Ask clearly"]},
        adjustments=[],
        memory=[],
        review={},
        training_decision={
            "decision_type": "review_weakness",
            "brief_instruction": "生成酒店入住场景，NPC 必须追问日期、姓名、房型。",
        },
        memory_influence=[
            {
                "memory_id": 3,
                "instruction": "用户没说入住日期时，NPC 必须追问。",
            }
        ],
    )

    assert brief["title"] == "Hotel detail check-in"
    assert "说明入住日期" in brief["task_steps"]
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd app/backend && python -m pytest tests/test_agents.py::test_scenario_design_agent_uses_training_decision_and_memory_influence -v
```

Expected: FAIL with `TypeError: generate_brief() got an unexpected keyword argument 'training_decision'`.

- [ ] **Step 3: Extend `ScenarioDesignAgent.generate_brief()`**

Change the signature in `app/backend/app/agents.py`:

```python
def generate_brief(
    self,
    plan_day: dict,
    adjustments: list,
    memory: list,
    review: dict,
    training_decision: dict | None = None,
    memory_influence: list | None = None,
) -> dict:
```

Update the `user_template.format()` call:

```python
user_prompt = user_template.format(
    plan_day=json.dumps(plan_day, ensure_ascii=False),
    adjustments=json.dumps(adjustments, ensure_ascii=False),
    memory=json.dumps(memory, ensure_ascii=False),
    review=json.dumps(review, ensure_ascii=False),
    training_decision=json.dumps(training_decision or {}, ensure_ascii=False),
    memory_influence=json.dumps(memory_influence or [], ensure_ascii=False),
)
```

- [ ] **Step 4: Upgrade scenario prompt template**

In `app/backend/app/prompts.py`, update `scenario_design_agent_user_template`:

```python
"scenario_design_agent_user_template": (
    "今日计划：{plan_day}\n"
    "计划微调：{adjustments}\n"
    "长期记忆：{memory}\n"
    "近期复盘：{review}\n"
    "今日训练决策 training_decision：{training_decision}\n"
    "记忆影响 memory_influence：{memory_influence}\n"
    "如果 training_decision.brief_instruction 非空，必须优先服从该教学指令。\n"
    "如果 memory_influence 中包含 npc_behavior，task_steps、scenario_setup 或 rubric 必须体现 NPC 会追问缺失信息。\n"
    "请输出场景任务单 JSON："
),
```

- [ ] **Step 5: Run test to verify GREEN**

Run:

```bash
cd app/backend && python -m pytest tests/test_agents.py::test_scenario_design_agent_uses_training_decision_and_memory_influence -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/app/agents.py app/backend/app/prompts.py app/backend/tests/test_agents.py
git commit -m "feat: drive scenario briefs from training decisions"
```

## Task 4: Add Decision Tools

**Files:**
- Modify: `app/backend/app/tools.py`
- Modify: `app/backend/tests/test_tools.py`

- [ ] **Step 1: Write failing tool tests**

Add to `app/backend/tests/test_tools.py`:

```python
from app.tools import LearningToolRegistry


def test_get_relevant_memory_prioritizes_weakness_and_confidence(tmp_path):
    class Repo:
        def get_active_memory_items(self, profile_id):
            return [
                {"id": 1, "category": "preference", "content": "Likes travel topics", "confidence": 0.9},
                {"id": 2, "category": "weakness", "content": "Often misses dates", "confidence": 0.8},
                {"id": 3, "category": "learning_pattern", "content": "Needs detail prompts", "confidence": 0.7},
                {"id": 4, "category": "weakness", "content": "Forgets object details", "confidence": 0.95},
            ]

    registry = LearningToolRegistry(Repo())
    call = registry.call("get_relevant_memory", {"profile_id": 1, "limit": 2})

    assert call.status == "success"
    assert [item["id"] for item in call.output] == [4, 2]


def test_refresh_practice_brief_uses_factory_and_saves_result():
    saved = {}

    class Repo:
        def save_practice_brief(self, plan_day_id, brief):
            saved["plan_day_id"] = plan_day_id
            saved["brief"] = brief
            return {"id": 10, "plan_day_id": plan_day_id, "brief_json": "{}", **brief}

    def factory(plan_day, training_decision=None, memory_influence=None):
        assert training_decision["brief_instruction"] == "生成酒店入住场景。"
        assert memory_influence[0]["memory_id"] == 3
        return {"title": "Refreshed hotel brief"}

    registry = LearningToolRegistry(Repo(), practice_brief_factory=factory)
    call = registry.call(
        "refresh_practice_brief",
        {
            "plan_day": {"id": 5, "topic": "Hotel"},
            "training_decision": {"brief_instruction": "生成酒店入住场景。"},
            "memory_influence": [{"memory_id": 3}],
        },
    )

    assert call.status == "success"
    assert saved["plan_day_id"] == 5
    assert call.output["title"] == "Refreshed hotel brief"
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd app/backend && python -m pytest tests/test_tools.py::test_get_relevant_memory_prioritizes_weakness_and_confidence tests/test_tools.py::test_refresh_practice_brief_uses_factory_and_saves_result -v
```

Expected: FAIL with `Unknown tool`.

- [ ] **Step 3: Update factory type and tool definitions**

In `app/backend/app/tools.py`, change the factory type:

```python
PracticeBriefFactory = Callable[[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]] | None], dict[str, Any]]
```

Add definitions in `self.definitions`:

```python
"get_relevant_memory": ToolDefinition(
    name="get_relevant_memory",
    description="Select the most relevant active memory items for today's training decision.",
    input_schema={"profile_id": "int", "limit": "int"},
    output_schema={"memory": "list"},
    side_effect="read_only",
),
"refresh_practice_brief": ToolDefinition(
    name="refresh_practice_brief",
    description="Create and save a new practice brief using a backend-controlled factory.",
    input_schema={"plan_day": "dict", "training_decision": "dict", "memory_influence": "list"},
    output_schema={"practice_brief": "dict"},
    side_effect="write",
),
```

- [ ] **Step 4: Implement tool handlers**

Add branches in `_call()`:

```python
if name == "get_relevant_memory":
    profile_id = int(input_data["profile_id"])
    limit = int(input_data.get("limit", 3))
    memory = self.repo.get_active_memory_items(profile_id)
    priority = {"weakness": 0, "learning_pattern": 1, "preference": 2, "strength": 3, "goal": 4}
    sorted_memory = sorted(
        memory,
        key=lambda item: (
            priority.get(str(item.get("category")), 9),
            -float(item.get("confidence") or 0),
            -int(item.get("id") or 0),
        ),
    )
    return sorted_memory[:limit]

if name == "refresh_practice_brief":
    plan_day = input_data["plan_day"]
    if not isinstance(plan_day, dict):
        raise ValueError("plan_day must be a dict")
    if self.practice_brief_factory is None:
        raise ValueError("practice_brief_factory is required to refresh a brief")
    training_decision = input_data.get("training_decision")
    memory_influence = input_data.get("memory_influence")
    brief = self.practice_brief_factory(
        plan_day,
        training_decision if isinstance(training_decision, dict) else {},
        memory_influence if isinstance(memory_influence, list) else [],
    )
    saved = self.repo.save_practice_brief(int(plan_day["id"]), brief)
    return saved if isinstance(saved, dict) else brief
```

- [ ] **Step 5: Preserve existing factory compatibility**

Update existing `get_or_create_practice_brief` branch:

```python
brief = self.practice_brief_factory(plan_day, None, None)
```

- [ ] **Step 6: Run tests to verify GREEN**

Run:

```bash
cd app/backend && python -m pytest tests/test_tools.py::test_get_relevant_memory_prioritizes_weakness_and_confidence tests/test_tools.py::test_refresh_practice_brief_uses_factory_and_saves_result -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/backend/app/tools.py app/backend/tests/test_tools.py
git commit -m "feat: add decision memory tools"
```

## Task 5: Use Training Decision In `/api/today/strategy`

**Files:**
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/app/models.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing API test for response shape**

Add to `app/backend/tests/test_api.py`:

```python
def test_today_strategy_returns_training_decision_and_memory_influence(client, monkeypatch):
    class MockOrchestrator:
        def __init__(self, llm, get_prompt_fn=None):
            pass

        def plan_today(self, **kwargs):
            return {
                "output": {
                    "today_strategy": {
                        "focus": "补充旅行场景中的关键信息",
                        "reason": "基于长期记忆",
                        "success_criteria": ["说明时间"],
                    },
                    "training_decision": {
                        "decision_type": "review_weakness",
                        "reason_zh": "最近经常漏掉时间。",
                        "selected_memory_ids": [1],
                        "selected_review_ids": [],
                        "brief_instruction": "生成酒店入住场景。",
                        "difficulty_adjustment": "same",
                        "should_refresh_brief": False,
                    },
                    "memory_influence": [
                        {
                            "memory_id": 1,
                            "category": "weakness",
                            "content": "经常漏掉时间。",
                            "influence_type": "drill_focus",
                            "instruction": "今天训练说明时间。",
                            "reason_zh": "这是重复弱点。",
                        }
                    ],
                    "recommended_actions": [],
                    "coach_explanation_zh": "今天先练补充时间信息。",
                    "risk_flags": [],
                    "confidence": 0.8,
                },
                "validation_status": "passed",
                "error_message": None,
                "raw_output": "{}",
            }

    monkeypatch.setattr("app.main.CoachOrchestratorAgent", MockOrchestrator)

    response = client.get("/api/today/strategy")

    assert response.status_code == 200
    data = response.json()
    assert data["training_decision"]["decision_type"] == "review_weakness"
    assert data["memory_influence"][0]["memory_id"] == 1
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd app/backend && python -m pytest tests/test_api.py::test_today_strategy_returns_training_decision_and_memory_influence -v
```

Expected: FAIL because the response does not include `training_decision` or `memory_influence`.

- [ ] **Step 3: Extend response model**

Update `app/backend/app/models.py`:

```python
class TodayStrategyResponse(BaseModel):
    today_strategy: dict
    training_decision: dict
    memory_influence: list[dict]
    coach_explanation_zh: str
    recommended_actions: list[dict]
    risk_flags: list[str]
    practice_brief: dict
    agent_run_id: int
```

- [ ] **Step 4: Return decision fields from route**

In `app/backend/app/main.py`, update the return object in `get_today_strategy()`:

```python
return {
    "today_strategy": output["today_strategy"],
    "training_decision": output.get("training_decision", {}),
    "memory_influence": output.get("memory_influence", []),
    "coach_explanation_zh": output["coach_explanation_zh"],
    "recommended_actions": output.get("recommended_actions", []),
    "risk_flags": output.get("risk_flags", []),
    "practice_brief": brief,
    "agent_run_id": agent_run["id"],
}
```

- [ ] **Step 5: Run test to verify GREEN**

Run:

```bash
cd app/backend && python -m pytest tests/test_api.py::test_today_strategy_returns_training_decision_and_memory_influence -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/app/main.py app/backend/app/models.py app/backend/tests/test_api.py
git commit -m "feat: expose training decision in today strategy"
```

## Task 6: Refresh Practice Brief When Decision Requires It

**Files:**
- Modify: `app/backend/app/main.py`
- Modify: `app/backend/tests/test_api.py`

- [ ] **Step 1: Write failing refresh test**

Add to `app/backend/tests/test_api.py`:

```python
def test_today_strategy_refreshes_brief_when_decision_requires_it(client, monkeypatch):
    class MockOrchestrator:
        def __init__(self, llm, get_prompt_fn=None):
            pass

        def plan_today(self, **kwargs):
            return {
                "output": {
                    "today_strategy": {
                        "focus": "补充酒店入住细节",
                        "reason": "基于长期记忆",
                        "success_criteria": ["说明入住日期"],
                    },
                    "training_decision": {
                        "decision_type": "refresh_brief",
                        "reason_zh": "旧材料没有覆盖细节遗漏问题。",
                        "selected_memory_ids": [1],
                        "selected_review_ids": [],
                        "brief_instruction": "生成新的酒店入住任务，NPC 追问入住日期。",
                        "difficulty_adjustment": "same",
                        "should_refresh_brief": True,
                    },
                    "memory_influence": [
                        {
                            "memory_id": 1,
                            "category": "weakness",
                            "content": "经常漏掉入住日期。",
                            "influence_type": "npc_behavior",
                            "instruction": "用户没说入住日期时必须追问。",
                            "reason_zh": "这是重复弱点。",
                        }
                    ],
                    "recommended_actions": [],
                    "coach_explanation_zh": "今天刷新材料来练细节补充。",
                    "risk_flags": [],
                    "confidence": 0.8,
                },
                "validation_status": "passed",
                "error_message": None,
                "raw_output": "{}",
            }

    class MockScenarioAgent:
        def __init__(self, llm, get_prompt_fn=None):
            pass

        def generate_brief(self, plan_day, adjustments, memory, review, training_decision=None, memory_influence=None):
            assert training_decision["brief_instruction"] == "生成新的酒店入住任务，NPC 追问入住日期。"
            assert memory_influence[0]["memory_id"] == 1
            return {"title": "Refreshed detail hotel brief", "task_steps": ["说明入住日期"]}

    monkeypatch.setattr("app.main.CoachOrchestratorAgent", MockOrchestrator)
    monkeypatch.setattr("app.main.ScenarioDesignAgent", MockScenarioAgent)

    response = client.get("/api/today/strategy")

    assert response.status_code == 200
    assert response.json()["practice_brief"]["title"] == "Refreshed detail hotel brief"
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd app/backend && python -m pytest tests/test_api.py::test_today_strategy_refreshes_brief_when_decision_requires_it -v
```

Expected: FAIL because the route does not refresh after Orchestrator decision.

- [ ] **Step 3: Add a local brief factory in `get_today_strategy()`**

In `app/backend/app/main.py`, create a helper inside `get_today_strategy()` after settings are loaded:

```python
def make_practice_brief(
    source_plan_day: dict[str, object],
    training_decision: dict[str, object] | None = None,
    memory_influence: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    brief_llm = create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )
    return ScenarioDesignAgent(brief_llm, repo.get_prompt).generate_brief(
        clean_plan_day(source_plan_day),
        active_adjustments,
        active_memory,
        latest_review or {},
        training_decision=training_decision or {},
        memory_influence=memory_influence or [],
    )
```

- [ ] **Step 4: Refresh after Orchestrator output**

After `output = orchestration["output"]`, add:

```python
decision = output.get("training_decision", {})
memory_influence = output.get("memory_influence", [])
should_refresh = bool(decision.get("should_refresh_brief")) and bool(decision.get("brief_instruction"))
if should_refresh:
    refresh_tools = LearningToolRegistry(repo, practice_brief_factory=make_practice_brief)
    refresh_call = refresh_tools.call(
        "refresh_practice_brief",
        {
            "plan_day": plan_day,
            "training_decision": decision,
            "memory_influence": memory_influence,
        },
    )
    tool_calls.append(refresh_call.model_dump())
    if refresh_call.status == "success" and isinstance(refresh_call.output, dict):
        brief = refresh_call.output
    else:
        output.setdefault("risk_flags", []).append("practice_brief_refresh_failed")
```

- [ ] **Step 5: Ensure initial brief creation passes empty decision**

Where the route currently creates a missing brief, call:

```python
brief = make_practice_brief(plan_day, training_decision={}, memory_influence=[])
```

- [ ] **Step 6: Run test to verify GREEN**

Run:

```bash
cd app/backend && python -m pytest tests/test_api.py::test_today_strategy_refreshes_brief_when_decision_requires_it -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/backend/app/main.py app/backend/tests/test_api.py
git commit -m "feat: refresh practice brief from training decision"
```

## Task 7: Upgrade Frontend Today Strategy Display

**Files:**
- Modify: `app/frontend/src/types.ts`
- Modify: `app/frontend/src/components/PracticeRoom.tsx`
- Modify: `app/frontend/src/App.test.tsx`

- [ ] **Step 1: Update failing frontend test expectation**

In `app/frontend/src/App.test.tsx`, update the default `getTodayStrategy` mock to include:

```typescript
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
```

Add assertions to the test that currently checks `今日练习依据`:

```typescript
expect(await screen.findByText("今天怎么练")).toBeTruthy();
expect(screen.getByText("为什么这样练")).toBeTruthy();
expect(screen.getByText("AI 教练准备")).toBeTruthy();
expect(screen.getByText("这是最近重复出现的细节遗漏问题。")).toBeTruthy();
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd app/frontend && npm run test -- src/App.test.tsx
```

Expected: FAIL because `今天怎么练` and `AI 教练准备` are not rendered.

- [ ] **Step 3: Extend frontend types**

Update `app/frontend/src/types.ts`:

```typescript
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
```

Update `TodayStrategy`:

```typescript
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
```

- [ ] **Step 4: Render three blocks in `PracticeRoom`**

Replace the existing `todayStrategy` card body in `app/frontend/src/components/PracticeRoom.tsx` with:

```tsx
{todayStrategy ? (
  <section className="lesson-card today-strategy-card">
    <p className="section-label">今日练习依据</p>
    <div className="strategy-grid">
      <div>
        <p className="strategy-label">今天怎么练</p>
        <h2>{todayStrategy.today_strategy.focus}</h2>
      </div>
      <div>
        <p className="strategy-label">为什么这样练</p>
        <p>{todayStrategy.coach_explanation_zh || todayStrategy.today_strategy.reason}</p>
      </div>
      <div>
        <p className="strategy-label">AI 教练准备</p>
        <p>
          {todayStrategy.memory_influence && todayStrategy.memory_influence.length > 0
            ? todayStrategy.memory_influence[0].reason_zh || todayStrategy.memory_influence[0].instruction
            : todayStrategy.training_decision?.reason_zh || "我会根据今天的练习表现继续调整后续训练。"}
        </p>
      </div>
    </div>
    {todayStrategy.today_strategy.success_criteria && todayStrategy.today_strategy.success_criteria.length > 0 ? (
      <ul className="compact-list">
        {todayStrategy.today_strategy.success_criteria.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    ) : null}
  </section>
) : null}
```

- [ ] **Step 5: Add minimal CSS**

In `app/frontend/src/styles.css`, add:

```css
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.strategy-label {
  margin: 0 0 6px;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
}
```

- [ ] **Step 6: Run frontend test to verify GREEN**

Run:

```bash
cd app/frontend && npm run test -- src/App.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/frontend/src/types.ts app/frontend/src/components/PracticeRoom.tsx app/frontend/src/styles.css app/frontend/src/App.test.tsx
git commit -m "feat: show memory-driven training rationale"
```

## Task 8: Full Regression

**Files:**
- Verify all modified files from Tasks 1-7.

- [ ] **Step 1: Run backend tests**

Run:

```bash
cd app/backend && python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests**

Run:

```bash
cd app/frontend && npm run test -- src/App.test.tsx
```

Expected: all tests pass.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd app/frontend && npm run build
```

Expected: build completes without TypeScript or Vite errors.

- [ ] **Step 4: Inspect git diff**

Run:

```bash
git status --short
git diff -- app/backend/app/contracts.py app/backend/app/agents.py app/backend/app/prompts.py app/backend/app/tools.py app/backend/app/main.py app/backend/app/models.py app/frontend/src/types.ts app/frontend/src/components/PracticeRoom.tsx app/frontend/src/styles.css app/frontend/src/App.test.tsx
```

Expected: only intentional implementation changes are present.

- [ ] **Step 5: Final commit if any regression fixes were needed**

If Task 8 required fixes, commit only those files:

```bash
git add app/backend app/frontend
git commit -m "fix: stabilize dynamic training decision flow"
```

If no fixes were needed, do not create an empty commit.

## Self-Review

- Spec coverage: the plan covers `TrainingDecision`, `MemoryInfluence`, Prompt upgrades, Tools Registry upgrades, `/api/today/strategy`, brief refresh, frontend display, and regression tests.
- Placeholder scan: the plan contains no unfinished markers or incomplete task descriptions.
- Type consistency: backend names match the spec and current code: `TrainingDecision`, `MemoryInfluence`, `OrchestrationResult`, `LearningToolRegistry`, `refresh_practice_brief`, `TodayStrategyResponse`, and frontend `TodayStrategy`.
