from app.completion import SessionCompletionEvaluator, build_completion_summary


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
