# Learning Loop Agents Core Logic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the core LLM integration and robust JSON parsing logic for DailyReviewAgent, MemoryAgent, PlanAdaptationAgent, and ScenarioDesignAgent.

**Architecture:** Each agent will be updated to format its inputs (sessions, memories, plans) into a specific prompt, call the LLM provider, and parse the response into the required JSON schema, handling markdown fences and parsing failures gracefully. Default prompt templates will be provided in the code.

**Tech Stack:** Python, Pytest

---

### Task 1: Implement DailyReviewAgent Core Logic

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/tests/test_agents.py`

- [x] **Step 1: Write the failing test**

```python
# In app/backend/tests/test_agents.py
def test_daily_review_agent_logic():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "Food" in user_prompt
            return '```json\n{"user_report": {"summary": "Great"}, "structured_analysis": {"signals": "positive"}}\n```'
    
    from app.agents import DailyReviewAgent
    agent = DailyReviewAgent(MockLLM(), lambda x: None)
    res = agent.generate_review({"current_level": "B1"}, [{"topic": "Food"}], {"goal": "Travel"})
    assert res["user_report"]["summary"] == "Great"
    assert res["structured_analysis"]["signals"] == "positive"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/backend/tests/test_agents.py::test_daily_review_agent_logic -v`
Expected: FAIL (because the mock currently ignores inputs and returns a hardcoded dict)

- [ ] **Step 3: Write minimal implementation**

```python
# In app/backend/app/agents.py, replace DailyReviewAgent:
class DailyReviewAgent:
    def __init__(self, llm_provider, get_prompt_fn):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn

    def generate_review(self, profile: dict, sessions: list, plan_context: dict) -> dict:
        system_prompt = self.get_prompt("daily_review_agent_system") or (
            "你是一个每日学习复盘 Agent。你的任务是分析当天的所有练习记录，生成结构化的日报。\n"
            "必须输出合法的 JSON 对象，包含两个顶级键：'user_report' 和 'structured_analysis'。"
        )
        user_template = self.get_prompt("daily_review_agent_user_template") or (
            "用户信息：{profile}\n今日练习记录：{sessions}\n当前计划上下文：{plan_context}\n请输出复盘 JSON："
        )
        import json
        user_prompt = user_template.format(
            profile=json.dumps(profile, ensure_ascii=False),
            sessions=json.dumps(sessions, ensure_ascii=False),
            plan_context=json.dumps(plan_context, ensure_ascii=False)
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        cleaned = response.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "user_report": {"title": "Today's Review", "summary": "Parse error, raw output saved.", "achievements": [], "key_issues": [], "suggested_focus": [], "encouragement": ""},
                "structured_analysis": {"performance_signals": {}, "recurring_issues": [], "memory_candidates": [], "plan_adaptation_signals": []}
            }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/backend/tests/test_agents.py::test_daily_review_agent_logic -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_agents.py
git commit -m "feat: implement DailyReviewAgent LLM logic"
```

### Task 2: Implement MemoryAgent Core Logic

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/tests/test_agents.py`

- [ ] **Step 1: Write the failing test**

```python
# In app/backend/tests/test_agents.py
def test_memory_agent_logic():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "positive" in user_prompt
            return '{"upserts": [{"category": "weakness", "content": "grammar"}]}'
            
    from app.agents import MemoryAgent
    agent = MemoryAgent(MockLLM(), lambda x: None)
    res = agent.extract_memory({"structured_analysis": {"signals": "positive"}}, [])
    assert res["upserts"][0]["content"] == "grammar"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/backend/tests/test_agents.py::test_memory_agent_logic -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# In app/backend/app/agents.py, replace MemoryAgent:
class MemoryAgent:
    def __init__(self, llm_provider, get_prompt_fn):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn

    def extract_memory(self, review: dict, active_memory: list) -> dict:
        system_prompt = self.get_prompt("memory_agent_system") or (
            "你是一个记忆提取 Agent。从日报中提取稳定的、需要长期记住的用户特征。\n"
            "必须输出合法的 JSON 对象，包含 'upserts' 数组。"
        )
        user_template = self.get_prompt("memory_agent_user_template") or (
            "今日复盘数据：{review}\n当前长期记忆：{active_memory}\n请输出记忆更新 JSON："
        )
        import json
        user_prompt = user_template.format(
            review=json.dumps(review, ensure_ascii=False),
            active_memory=json.dumps(active_memory, ensure_ascii=False)
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        cleaned = response.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"upserts": []}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/backend/tests/test_agents.py::test_memory_agent_logic -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_agents.py
git commit -m "feat: implement MemoryAgent LLM logic"
```

### Task 3: Implement PlanAdaptationAgent Core Logic

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/tests/test_agents.py`

- [ ] **Step 1: Write the failing test**

```python
# In app/backend/tests/test_agents.py
def test_plan_adaptation_agent_logic():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "upcoming" in user_prompt
            return '{"adjustments": [{"adjustment_type": "focus", "title": "Grammar"}]}'
            
    from app.agents import PlanAdaptationAgent
    agent = PlanAdaptationAgent(MockLLM(), lambda x: None)
    res = agent.propose_adjustments({}, [], [{"day": "upcoming"}])
    assert res["adjustments"][0]["title"] == "Grammar"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest app/backend/tests/test_agents.py::test_plan_adaptation_agent_logic -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# In app/backend/app/agents.py, replace PlanAdaptationAgent:
class PlanAdaptationAgent:
    def __init__(self, llm_provider, get_prompt_fn):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn

    def propose_adjustments(self, review: dict, active_memory: list, upcoming_days: list) -> dict:
        system_prompt = self.get_prompt("plan_adaptation_agent_system") or (
            "你是一个计划微调 Agent。基于日报和记忆，对未来练习计划提出微调建议。\n"
            "必须输出合法的 JSON 对象，包含 'adjustments' 数组。"
        )
        user_template = self.get_prompt("plan_adaptation_agent_user_template") or (
            "最新复盘：{review}\n长期记忆：{active_memory}\n未来计划：{upcoming_days}\n请输出计划微调 JSON："
        )
        import json
        user_prompt = user_template.format(
            review=json.dumps(review, ensure_ascii=False),
            active_memory=json.dumps(active_memory, ensure_ascii=False),
            upcoming_days=json.dumps(upcoming_days, ensure_ascii=False)
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        cleaned = response.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"adjustments": []}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest app/backend/tests/test_agents.py::test_plan_adaptation_agent_logic -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_agents.py
git commit -m "feat: implement PlanAdaptationAgent LLM logic"
```

### Task 4: Implement ScenarioDesignAgent Core Logic

**Files:**
- Modify: `app/backend/app/agents.py`
- Modify: `app/backend/tests/test_agents.py`

- [x] **Step 1: Write the failing test**

```python
# In app/backend/tests/test_agents.py
def test_scenario_design_agent_logic():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "Meeting" in user_prompt
            return '{"title": "Designed Scenario", "npc_role": "Manager"}'
            
    from app.agents import ScenarioDesignAgent
    agent = ScenarioDesignAgent(MockLLM(), lambda x: None)
    res = agent.generate_brief({"topic": "Meeting"}, [], [], {})
    assert res["title"] == "Designed Scenario"
    assert res["npc_role"] == "Manager"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest app/backend/tests/test_agents.py::test_scenario_design_agent_logic -v`
Expected: FAIL

- [x] **Step 3: Write minimal implementation**

```python
# In app/backend/app/agents.py, replace ScenarioDesignAgent:
class ScenarioDesignAgent:
    def __init__(self, llm_provider, get_prompt_fn):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn

    def generate_brief(self, plan_day: dict, adjustments: list, memory: list, review: dict) -> dict:
        system_prompt = self.get_prompt("scenario_design_agent_system") or (
            "你是一个场景设计 Agent。根据学习计划和近期的微调建议，生成下一次练习的具体场景任务单。\n"
            "必须输出合法的 JSON 对象，包含 'title', 'npc_role', 'target_expressions' 等键。"
        )
        user_template = self.get_prompt("scenario_design_agent_user_template") or (
            "今日计划：{plan_day}\n计划微调：{adjustments}\n长期记忆：{memory}\n近期复盘：{review}\n请输出场景任务单 JSON："
        )
        import json
        user_prompt = user_template.format(
            plan_day=json.dumps(plan_day, ensure_ascii=False),
            adjustments=json.dumps(adjustments, ensure_ascii=False),
            memory=json.dumps(memory, ensure_ascii=False),
            review=json.dumps(review, ensure_ascii=False)
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        cleaned = response.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {
                "title": plan_day.get("topic", "Practice"),
                "user_visible_goal": "Practice speaking",
                "npc_role": "NPC",
                "scenario_setup": plan_day.get("scenario", "Setup"),
                "conversation_objective": plan_day.get("objective", "Objective"),
                "target_expressions": [],
                "avoid_patterns": [],
                "difficulty": "normal",
                "coach_notes": ""
            }
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest app/backend/tests/test_agents.py::test_scenario_design_agent_logic -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add app/backend/app/agents.py app/backend/tests/test_agents.py
git commit -m "feat: implement ScenarioDesignAgent LLM logic"
```
