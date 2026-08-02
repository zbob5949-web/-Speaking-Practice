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
