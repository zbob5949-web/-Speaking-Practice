from app.agents import CoachOrchestratorAgent, ConversationAgent, GoalAgent, InlineFeedbackAgent
from app.llm import FakeLLMProvider
import json

class MockPlannerProvider(FakeLLMProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return '''
        [
            {"topic": "Mock Topic", "scenario": "Mock Scenario", "objective": "Mock Obj"}
        ]
        '''

def test_goal_agent_uses_llm():
    agent = GoalAgent(MockPlannerProvider())
    plan = agent.generate_plan("Test Goal", 1, 15, "Level 1")
    assert len(plan) == 1
    assert plan[0]["topic"] == "Mock Topic"


def test_goal_agent_generates_rich_plan_fields():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "skill_focus" in system_prompt
            return """
            [
              {
                "topic": "Airport delay",
                "scenario": "Explain a delayed flight at a hotel desk.",
                "objective": "Ask for late check-in.",
                "skill_focus": "Past-tense storytelling",
                "communicative_task": "Explain the delay and request help.",
                "target_functions": ["explain what happened", "make a request"],
                "success_criteria": ["Use past tense", "Ask one clear question"],
                "brief_seed": "Create a hotel receptionist role-play after a delayed flight."
              }
            ]
            """

    plan = GoalAgent(MockLLM()).generate_plan(
        learning_goal="Travel English",
        total_days=1,
        daily_minutes=15,
        current_level="A2",
    )

    assert plan[0]["skill_focus"] == "Past-tense storytelling"
    assert plan[0]["target_functions"] == ["explain what happened", "make a request"]
    assert plan[0]["success_criteria"] == ["Use past tense", "Ask one clear question"]
    assert plan[0]["brief_seed"].startswith("Create a hotel receptionist")

class MockFeedbackProvider(FakeLLMProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps([
            {
                "feedback_type": "grammar",
                "feedback_text": "Use the past tense."
            }
        ])

def test_inline_feedback_agent_uses_llm():
    agent = InlineFeedbackAgent(MockFeedbackProvider())
    feedback = agent.generate("I go to store yesterday.", "Shopping", "Buy an item", [])
    assert len(feedback) == 1
    assert feedback[0]["feedback_type"] == "grammar"
    assert feedback[0]["feedback_text"] == "Use the past tense."

class MockChinglishFeedbackProvider(FakeLLMProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        assert "Chinglish" in system_prompt
        return json.dumps([
            {
                "feedback_type": "expression",
                "feedback_text": "Here is the full English expression."
            }
        ])

def test_inline_feedback_agent_handles_chinglish():
    agent = InlineFeedbackAgent(MockChinglishFeedbackProvider())
    feedback = agent.generate("I want to 靠窗的 seat.", "Airport", "Ask for a seat", [])
    assert len(feedback) == 1


class PromptPolicyFeedbackProvider(FakeLLMProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        assert "original_fragment" in system_prompt
        assert "better_expression" in system_prompt
        assert "reason_zh" in system_prompt
        assert "example_sentence" in system_prompt
        assert "Do not focus on politeness" in system_prompt
        assert "one short sentence" in system_prompt
        assert "max 2 feedback items" in system_prompt
        assert "语音转文字" in system_prompt
        assert "标点" in system_prompt
        return json.dumps([
            {
                "feedback_type": "correction",
                "feedback_text": "show me -> could you show me: 用疑问句请求更自然。",
                "original_fragment": "show me",
                "better_expression": "could you show me",
                "reason_zh": "用疑问句请求更自然。",
                "example_sentence": "Could you show me a travel-themed keychain?"
            },
            {
                "feedback_type": "guidance",
                "feedback_text": "下一句练习询问价格或库存，不要只结束对话。",
                "reason_zh": "下一句练习询问价格或库存。",
                "example_sentence": "How much is it?"
            }
        ])


def test_inline_feedback_prompt_requires_specific_replacements_and_concise_guidance():
    agent = InlineFeedbackAgent(PromptPolicyFeedbackProvider())
    feedback = agent.generate(
        "Show me a travel themed keychain.",
        "Souvenir shop",
        "Ask about a product",
        [{"speaker": "user", "text": "Show me a travel themed keychain."}],
    )
    assert len(feedback) == 2
    assert feedback[0]["original_fragment"] == "show me"
    assert feedback[0]["better_expression"] == "could you show me"
    assert feedback[0]["reason_zh"] == "用疑问句请求更自然。"
    assert feedback[0]["example_sentence"] == "Could you show me a travel-themed keychain?"

from app.agents import DailyReviewAgent, MemoryAgent

def test_daily_review_agent_logic():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "Food" in user_prompt
            return '```json\n{"user_report": {"summary": "Great"}, "structured_analysis": {"signals": "positive"}}\n```'
    
    from app.agents import DailyReviewAgent
    agent = DailyReviewAgent(MockLLM())
    res = agent.generate_review({"current_level": "B1"}, [{"topic": "Food"}], {"goal": "Travel"})
    assert res["user_report"]["summary"] == "Great"
    assert res["structured_analysis"]["signals"] == "positive"

def test_memory_agent_logic():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "positive" in user_prompt
            return '{"upserts": [{"category": "weakness", "content": "grammar"}]}'
            
    from app.agents import MemoryAgent
    agent = MemoryAgent(MockLLM())
    res = agent.extract_memory({"structured_analysis": {"signals": "positive"}}, [])
    assert res["upserts"][0]["content"] == "grammar"

from app.agents import PlanAdaptationAgent, ScenarioDesignAgent

def test_plan_adaptation_agent_logic():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "upcoming" in user_prompt
            return '{"adjustments": [{"adjustment_type": "focus", "title": "Grammar"}]}'
            
    from app.agents import PlanAdaptationAgent
    agent = PlanAdaptationAgent(MockLLM())
    res = agent.propose_adjustments({}, [], [{"day": "upcoming"}])
    assert res["adjustments"][0]["title"] == "Grammar"

def test_scenario_design_agent_logic():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "Meeting" in user_prompt
            return '{"title": "Designed Scenario", "npc_role": "Manager"}'
            
    from app.agents import ScenarioDesignAgent
    agent = ScenarioDesignAgent(MockLLM())
    res = agent.generate_brief({"topic": "Meeting"}, [], [], {})
    assert res["title"] == "Designed Scenario"
    assert res["npc_role"] == "Manager"


def test_scenario_design_agent_generates_rich_lesson_pack():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "lesson pack" in system_prompt.lower() or "材料包" in system_prompt
            assert "brief_seed" in user_prompt
            return """
            {
              "title": "Hotel delay check-in",
              "user_visible_goal": "Explain a delayed flight and request late check-in.",
              "npc_role": "Hotel receptionist",
              "scenario_setup": "You arrived late because your flight was delayed.",
              "conversation_objective": "Explain the problem and ask whether your room is still available.",
              "lesson_focus": "Past-tense storytelling plus polite requests",
              "task_steps": ["Explain what happened", "Ask about the room", "Confirm the next step"],
              "target_expressions": [
                {"expression": "My flight was delayed.", "meaning_zh": "我的航班延误了。", "example": "My flight was delayed by two hours.", "when_to_use": "explaining the reason you arrived late"}
              ],
              "sentence_frames": ["I arrived late because...", "Could you still...?"],
              "model_dialogue": ["NPC: Good evening. How can I help?", "Learner: My flight was delayed by two hours."],
              "common_mistakes": [{"mistake": "I am arrive late.", "better": "I arrived late.", "reason_zh": "arrive 要用过去式 arrived。"}],
              "rubric": ["Clear reason", "Polite request"],
              "stretch_goal": "Add one detail about the delay."
            }
            """

    agent = ScenarioDesignAgent(MockLLM())
    brief = agent.generate_brief(
        {"topic": "Hotel", "brief_seed": "Generate a hotel delay lesson pack."},
        [],
        [],
        {},
    )

    assert brief["lesson_focus"] == "Past-tense storytelling plus polite requests"
    assert brief["task_steps"][0] == "Explain what happened"
    assert brief["target_expressions"][0]["meaning_zh"] == "我的航班延误了。"
    assert brief["common_mistakes"][0]["better"] == "I arrived late."


def test_memory_agent_normalizes_missing_upserts_to_empty_list():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            return '{"bad": "shape"}'

    agent = MemoryAgent(MockLLM())
    result = agent.extract_memory({"summary": "x"}, [])

    assert result == {"upserts": []}


def test_plan_adaptation_agent_normalizes_bad_adjustments_to_empty_list():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            return '{"adjustments": "wrong"}'

    agent = PlanAdaptationAgent(MockLLM())
    result = agent.propose_adjustments({}, [], [])

    assert result == {"adjustments": []}


def test_scenario_design_agent_keeps_array_fields_as_arrays():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            return '{"title": "Bad arrays", "task_steps": "wrong", "target_expressions": {"bad": true}, "common_mistakes": "wrong"}'

    agent = ScenarioDesignAgent(MockLLM())
    brief = agent.generate_brief({"topic": "Meeting"}, [], [], {})

    assert brief["title"] == "Bad arrays"
    assert brief["task_steps"] == []
    assert brief["target_expressions"] == []
    assert brief["common_mistakes"] == []


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


def test_conversation_agent_includes_practice_brief_context():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "Hotel receptionist" in user_prompt
            assert "My flight was delayed." in user_prompt
            assert "Explain what happened" in user_prompt
            return '{"reply": "Good evening. Could you tell me what happened with your flight?", "hints": ["说明航班延误"]}'

    agent = ConversationAgent(MockLLM())
    response = agent.reply(
        topic="Hotel delay",
        objective="Explain the problem.",
        user_level="A2",
        learning_goal="Travel English",
        conversation=[{"speaker": "user", "text": "Hello."}],
        practice_brief={
            "npc_role": "Hotel receptionist",
            "task_steps": ["Explain what happened"],
            "target_expressions": [{"expression": "My flight was delayed."}],
            "rubric": ["Clear reason"],
        },
    )

    assert response["reply"].startswith("Good evening")


def test_agent_uses_default_prompts_without_repo():
    from app.agents import GoalAgent
    from app.prompts import DEFAULT_PROMPTS

    class CapturingLLM:
        def __init__(self):
            self.system_prompt = None
        def complete(self, system_prompt, user_prompt):
            self.system_prompt = system_prompt
            return "[{}]"

    llm = CapturingLLM()
    GoalAgent(llm).generate_plan("Travel", 1, 15, "Beginner")
    assert llm.system_prompt == DEFAULT_PROMPTS["goal_agent_system"]


def test_orchestrator_agent_returns_valid_strategy():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "学习教练总控" in system_prompt
            assert "Travel speaking" in user_prompt
            return json.dumps(
                {
                    "today_strategy": {
                        "focus": "Practice hotel check-in details.",
                        "reason": "Recent memory says the learner gives vague travel details.",
                        "success_criteria": ["State reservation name", "Ask one room question"],
                    },
                    "training_decision": {
                        "decision_type": "continue_plan",
                        "reason_zh": "当前材料已经匹配今日练习重点，继续原计划。",
                        "selected_memory_ids": [],
                        "selected_review_ids": [],
                        "brief_instruction": "",
                        "difficulty_adjustment": "same",
                        "should_refresh_brief": False,
                    },
                    "memory_influence": [],
                    "recommended_actions": [
                        {
                            "action": "use_existing_brief",
                            "rationale": "The brief matches today's focus.",
                            "priority": "medium",
                        }
                    ],
                    "coach_explanation_zh": "今天重点练酒店入住细节，因为你最近容易遗漏关键信息。",
                    "risk_flags": [],
                    "confidence": 0.82,
                }
            )

    result = CoachOrchestratorAgent(MockLLM()).plan_today(
        profile={"learning_goal": "Travel speaking"},
        plan_day={"topic": "Hotel check-in", "objective": "Ask room questions"},
        latest_review={},
        active_memory=[{"content": "Often gives vague travel details"}],
        active_adjustments=[],
        practice_brief={"title": "Hotel check-in"},
        session_state={"has_session": False},
    )

    assert result["validation_status"] == "passed"
    assert result["output"]["today_strategy"]["focus"] == "Practice hotel check-in details."
    assert result["output"]["recommended_actions"][0]["action"] == "use_existing_brief"


def test_orchestrator_agent_falls_back_on_bad_json():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            return "not-json"

    result = CoachOrchestratorAgent(MockLLM()).plan_today(
        profile={"learning_goal": "Travel speaking"},
        plan_day={"topic": "Hotel check-in", "objective": "Ask room questions"},
        latest_review={},
        active_memory=[],
        active_adjustments=[],
        practice_brief={},
        session_state={},
    )

    assert result["validation_status"] == "failed"
    assert result["output"]["today_strategy"]["focus"]
    assert result["output"]["risk_flags"] == ["orchestrator_parse_failed"]


def test_orchestrator_agent_returns_training_decision_and_memory_influence():
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            assert "training_decision" in system_prompt
            assert "memory_influence" in system_prompt
            assert "第一个字符必须是 {" in system_prompt
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


def orchestration_payload() -> dict:
    return {
        "today_strategy": {
            "focus": "补充旅行场景中的关键信息",
            "reason": "基于长期记忆和最近复盘",
            "success_criteria": ["说明时间", "说明对象"],
        },
        "training_decision": {
            "decision_type": "review_weakness",
            "reason_zh": "你最近经常漏掉时间和对象。",
            "selected_memory_ids": [3],
            "selected_review_ids": [9],
            "brief_instruction": "生成酒店入住场景，NPC 必须追问日期、姓名、房型。",
            "difficulty_adjustment": "same",
            "should_refresh_brief": True,
        },
        "memory_influence": [
            {
                "memory_id": 3,
                "category": "weakness",
                "content": "经常漏掉时间和对象。",
                "influence_type": "npc_behavior",
                "instruction": "用户没说时间时必须追问。",
                "reason_zh": "这是重复弱点。",
            }
        ],
        "recommended_actions": [],
        "coach_explanation_zh": "今天先集中练补充关键信息。",
        "risk_flags": [],
        "confidence": 0.8,
    }


def run_orchestrator_with_response(response: str) -> dict:
    class MockLLM:
        def complete(self, system_prompt, user_prompt):
            return response

    return CoachOrchestratorAgent(MockLLM()).plan_today(
        profile={"id": 1, "learning_goal": "Travel English"},
        plan_day={"id": 2, "topic": "Hotel", "objective": "Check in"},
        latest_review={"id": 9},
        active_memory=[{"id": 3, "category": "weakness", "content": "经常漏掉时间和对象。"}],
        active_adjustments=[],
        practice_brief={"title": "Old hotel brief"},
        session_state={"has_session": True, "turn_count": 0},
    )


def test_orchestrator_parses_json_object_surrounded_by_model_text():
    response = "当然可以，以下是 JSON：\n```json\n" + json.dumps(orchestration_payload(), ensure_ascii=False) + "\n```\n希望有帮助。"

    result = run_orchestrator_with_response(response)

    assert result["validation_status"] == "passed"
    assert result["output"]["training_decision"]["decision_type"] == "review_weakness"


def test_orchestrator_parses_first_object_from_top_level_array():
    response = json.dumps([orchestration_payload()], ensure_ascii=False)

    result = run_orchestrator_with_response(response)

    assert result["validation_status"] == "passed"
    assert result["output"]["memory_influence"][0]["memory_id"] == 3


def test_orchestrator_normalizes_string_recommended_actions():
    payload = orchestration_payload()
    payload["recommended_actions"] = ["use_existing_brief", "start_practice"]
    response = json.dumps(payload, ensure_ascii=False)

    result = run_orchestrator_with_response(response)

    assert result["validation_status"] == "passed"
    assert result["output"]["recommended_actions"][0]["action"] == "use_existing_brief"
    assert result["output"]["recommended_actions"][1]["action"] == "start_practice"


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
