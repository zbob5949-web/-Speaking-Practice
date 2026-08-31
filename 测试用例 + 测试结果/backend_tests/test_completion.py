from app.completion import SessionCompletionEvaluator, build_completion_summary, is_early_farewell


def user_turn(turn_index: int, text: str) -> dict:
    return {
        "id": turn_index,
        "session_id": 1,
        "turn_index": turn_index,
        "speaker": "user",
        "text": text,
    }


def assistant_turn(turn_index: int, text: str) -> dict:
    return {
        "id": turn_index,
        "session_id": 1,
        "turn_index": turn_index,
        "speaker": "assistant",
        "text": text,
    }


def test_completion_evaluator_does_not_suggest_before_three_user_turns():
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": None},
        turns=[
            assistant_turn(1, "Welcome."),
            user_turn(2, "I want to book a room."),
            assistant_turn(3, "For what date?"),
            user_turn(4, "Tomorrow night."),
        ],
        feedback=[],
        practice_brief={"user_visible_goal": "Book a hotel room."},
    )

    assert result["status"] == "in_progress"
    assert result["can_suggest_completion"] is False


def test_completion_evaluator_suggests_after_three_user_turns_without_major_blockers():
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": None},
        turns=[
            assistant_turn(1, "Welcome."),
            user_turn(2, "I want to book a room."),
            assistant_turn(3, "For what date?"),
            user_turn(4, "Tomorrow night for two people."),
            assistant_turn(5, "What room type?"),
            user_turn(6, "A non-smoking double room, please."),
        ],
        feedback=[{"feedback_type": "guidance", "severity": None}],
        practice_brief={"user_visible_goal": "Book a hotel room."},
    )

    assert result["status"] == "completion_suggested"
    assert result["can_suggest_completion"] is True
    assert "核心目标" in result["suggestion_reason_zh"]


def test_completion_evaluator_returns_completed_when_session_has_ended_at():
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": "2026-07-26 10:00:00", "summary": '{"summary_zh":"完成"}'},
        turns=[user_turn(1, "Hello.")],
        feedback=[],
        practice_brief={},
    )

    assert result["status"] == "completed"
    assert result["can_suggest_completion"] is False
    assert result["completed_summary"]["summary_zh"] == "完成"


def test_free_talk_never_suggests_completion_even_after_many_turns():
    """自由对话无回合数限制：无论聊多少轮都不建议收束/弹总结。"""
    evaluator = SessionCompletionEvaluator()
    turns = []
    for index in range(1, 9):
        turns.append(assistant_turn(index * 2 - 1, "Tell me more."))
        turns.append(user_turn(index * 2, f"Thought number {index}."))
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": None, "scenario_id": "free_talk"},
        turns=turns,
        feedback=[{"feedback_type": "guidance", "severity": None}],
        practice_brief={"user_visible_goal": "自由聊天"},
    )

    assert result["status"] == "in_progress"
    assert result["can_suggest_completion"] is False
    assert result["suggestion_reason_zh"] == ""
    assert result["completed_summary"] is None


def test_plan_session_still_suggests_completion():
    """普通计划会话（非自由对话）仍保留原收束建议逻辑。"""
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": None, "scenario_id": None},
        turns=[
            assistant_turn(1, "Welcome."),
            user_turn(2, "I want to book a room."),
            assistant_turn(3, "For what date?"),
            user_turn(4, "Tomorrow night for two people."),
            assistant_turn(5, "What room type?"),
            user_turn(6, "A non-smoking double room, please."),
        ],
        feedback=[{"feedback_type": "guidance", "severity": None}],
        practice_brief={"user_visible_goal": "Book a hotel room."},
    )

    assert result["status"] == "completion_suggested"
    assert result["can_suggest_completion"] is True


def test_farewell_from_user_suggests_completion_even_with_few_turns():
    """告别句检测：用户回合出现 goodbye，即使轮数不足也提示结束并总结。"""
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": None, "scenario_id": "hotel-check-in"},
        turns=[
            assistant_turn(1, "Welcome. How can I help you?"),
            user_turn(2, "Thank you for your help. Goodbye!"),
        ],
        feedback=[],
        practice_brief={"user_visible_goal": "Book a hotel room."},
    )

    assert result["status"] == "completion_suggested"
    assert result["can_suggest_completion"] is True
    assert "道别" in result["suggestion_reason_zh"]


def test_farewell_from_assistant_suggests_completion():
    """告别句检测：助手回合出现告别语同样触发（对话双方任一）。"""
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": None, "scenario_id": "restaurant-order"},
        turns=[
            assistant_turn(1, "Welcome."),
            user_turn(2, "I would like a coffee."),
            assistant_turn(3, "Sure. See you tomorrow!"),
        ],
        feedback=[],
        practice_brief={"user_visible_goal": "Order food."},
    )

    assert result["status"] == "completion_suggested"
    assert result["can_suggest_completion"] is True


def test_farewell_does_not_apply_to_free_talk():
    """自由对话不受告别句检测影响：仍保持无限制、不弹收束建议。"""
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": None, "scenario_id": "free_talk"},
        turns=[
            assistant_turn(1, "Hi! Let's chat."),
            user_turn(2, "This was fun, goodbye!"),
            assistant_turn(3, "Goodbye, take care!"),
        ],
        feedback=[],
        practice_brief={},
    )

    assert result["status"] == "in_progress"
    assert result["can_suggest_completion"] is False


def test_no_farewell_keeps_original_threshold_behavior():
    """无告别句时保持原行为：轮数不足不提示收束。"""
    evaluator = SessionCompletionEvaluator()
    result = evaluator.evaluate(
        session={"id": 1, "ended_at": None, "scenario_id": "doctor-visit"},
        turns=[
            assistant_turn(1, "Welcome."),
            user_turn(2, "I feel sick."),
            assistant_turn(3, "Where does it hurt?"),
            user_turn(4, "My head, since this morning."),
        ],
        feedback=[],
        practice_brief={"user_visible_goal": "Describe symptoms."},
    )

    assert result["status"] == "in_progress"
    assert result["can_suggest_completion"] is False


def test_is_early_farewell_true_within_three_user_turns():
    """前 3 轮内用户主动道别：视为提前结束（不计入练习、无得分）。"""
    turns = [
        assistant_turn(1, "Welcome."),
        user_turn(2, "Hi, thanks. See you!"),
    ]
    assert is_early_farewell(turns) is True


def test_is_early_farewell_false_after_three_user_turns():
    """超过 3 轮（用户第 4 句）才道别：不算提前结束。"""
    turns = [
        assistant_turn(1, "Welcome."),
        user_turn(2, "I want to book a room."),
        assistant_turn(3, "For what date?"),
        user_turn(4, "Tomorrow night."),
        assistant_turn(5, "What room type?"),
        user_turn(6, "A non-smoking room, please."),
        assistant_turn(7, "Sure."),
        user_turn(8, "That is all, goodbye."),
    ]
    assert is_early_farewell(turns) is False


def test_is_early_farewell_ignores_assistant_goodbye():
    """AI 说告别但用户没说：不算用户提前道别。"""
    turns = [
        assistant_turn(1, "Goodbye, take care!"),
        user_turn(2, "Thanks."),
    ]
    assert is_early_farewell(turns) is False


def test_build_completion_summary_short_practice_mentions_short_duration():
    summary = build_completion_summary(
        completion_type="manual",
        turns=[assistant_turn(1, "Welcome."), user_turn(2, "I want a room.")],
        practice_brief={"user_visible_goal": "Book a hotel room."},
    )

    assert summary["status"] == "completed"
    assert summary["completion_type"] == "manual"
    assert "练习时间较短" in summary["next_focus_zh"]
    assert summary["reusable_sentences"]
    # 无纠错信息时按满分结算
    assert summary["score"] == 100
    assert "未发现明显错误" in summary["score_detail_zh"]


def test_build_completion_summary_deducts_two_or_three_points_per_error():
    feedback = [
        {"feedback_type": "correction", "severity": None},      # 普通错误扣 2
        {"feedback_type": "correction", "severity": "major"},   # 主要错误扣 3
        {"feedback_type": "guidance", "severity": None},        # 建议不算错误
        {"feedback_type": "language_help", "severity": None},   # 词义解答不算错误
    ]
    summary = build_completion_summary(
        completion_type="manual",
        turns=[user_turn(1, "I am go to hotel.")],
        feedback=feedback,
    )

    assert summary["score"] == 95  # 100 - 2 - 3
    assert "2 处" in summary["score_detail_zh"]


def test_build_completion_summary_score_floor_is_sixty():
    many_errors = [{"feedback_type": "correction", "severity": "major"}] * 30
    summary = build_completion_summary(
        completion_type="manual",
        turns=[user_turn(1, "Hello.")],
        feedback=many_errors,
    )

    assert summary["score"] == 60
    assert "错误" in summary["score_detail_zh"]
