from app.db import connect, init_db
from app.models import OnboardingRequest
from app.repositories import CoachRepository

def test_delete_profile(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    
    p1 = repo.save_profile(OnboardingRequest(learning_goal="Goal 1", total_days=7, daily_minutes=15, current_level="Level 1"))
    repo.save_plan(p1["id"], [{"day_index": 1, "topic": "T1", "scenario": "S1", "objective": "O1"}])
    
    repo.delete_profile(p1["id"])
    
    assert repo.get_profile(p1["id"]) is None
    assert len(repo.get_plan(p1["id"])) == 0

def test_get_all_profiles(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    
    p1 = repo.save_profile(OnboardingRequest(learning_goal="Goal 1", total_days=7, daily_minutes=15, current_level="Level 1"))
    p2 = repo.save_profile(OnboardingRequest(learning_goal="Goal 2", total_days=14, daily_minutes=20, current_level="Level 2"))
    
    profiles = repo.get_all_profiles()
    assert len(profiles) == 2
    assert profiles[0]["learning_goal"] == "Goal 2" # Newest first
    assert profiles[1]["learning_goal"] == "Goal 1"

def test_get_inline_feedback_for_session(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    
    repo.save_inline_feedback(1, 1, [{"feedback_type": "grammar", "feedback_text": "text1"}])
    repo.save_inline_feedback(1, 2, [{"feedback_type": "expression", "feedback_text": "text2"}])
    
    feedbacks = repo.get_inline_feedback_for_session(1)
    assert len(feedbacks) == 2
    assert feedbacks[0]["feedback_text"] == "text1"
    assert feedbacks[1]["feedback_text"] == "text2"


def test_save_plan_persists_rich_learning_material_fields(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel English",
            total_days=1,
            daily_minutes=15,
            current_level="A2",
        )
    )

    saved = repo.save_plan(
        profile["id"],
        [
            {
                "day_index": 1,
                "topic": "Airport delay",
                "scenario": "Explain a delayed flight at the hotel desk.",
                "objective": "Explain what happened and ask for late check-in.",
                "skill_focus": "Past-tense storytelling",
                "communicative_task": "Explain a travel problem and request help.",
                "target_functions": ["explain what happened", "ask for help"],
                "success_criteria": ["Use past tense", "Make a clear request"],
                "brief_seed": "Generate a hotel check-in role-play after a delayed flight.",
            }
        ],
    )

    assert saved[0]["skill_focus"] == "Past-tense storytelling"
    assert saved[0]["communicative_task"] == "Explain a travel problem and request help."
    assert saved[0]["target_functions"] == ["explain what happened", "ask for help"]
    assert saved[0]["success_criteria"] == ["Use past tense", "Make a clear request"]
    assert saved[0]["brief_seed"] == "Generate a hotel check-in role-play after a delayed flight."


def test_inline_feedback_preserves_structured_teaching_fields(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)

    repo.save_inline_feedback(1, 1, [{
        "feedback_type": "correction",
        "feedback_text": "I need -> I'd like to book: 订房场景更自然。",
        "original_fragment": "I need",
        "better_expression": "I'd like to book",
        "reason_zh": "订房场景里这样说更自然。",
        "example_sentence": "I'd like to book a non-smoking room for tonight.",
        "severity": "major",
    }])

    feedbacks = repo.get_inline_feedback_for_session(1)

    assert feedbacks[0]["original_fragment"] == "I need"
    assert feedbacks[0]["better_expression"] == "I'd like to book"
    assert feedbacks[0]["reason_zh"] == "订房场景里这样说更自然。"
    assert feedbacks[0]["example_sentence"] == "I'd like to book a non-smoking room for tonight."
    assert feedbacks[0]["severity"] == "major"


def test_repository_completes_session_and_plan_day(tmp_path):
    import json
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(learning_goal="Travel English", total_days=1, daily_minutes=15, current_level="A2")
    )
    plan = repo.save_plan(
        profile["id"],
        [{"day_index": 1, "topic": "Hotel", "scenario": "Check in", "objective": "Book a room"}],
    )
    session = repo.get_or_create_session(plan[0]["id"], 1, "Hotel")
    summary = {"status": "completed", "summary_zh": "今天完成了酒店入住练习。", "confidence": 0.7}

    completed = repo.complete_session(session["id"], summary, overall_score=4)

    assert completed["ended_at"]
    assert json.loads(completed["summary"])["summary_zh"] == "今天完成了酒店入住练习。"
    assert completed["overall_score"] == 4
    assert repo.get_plan_day_by_id(plan[0]["id"])["status"] == "completed"


def test_repository_complete_session_is_idempotent(tmp_path):
    import json
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(learning_goal="Travel English", total_days=1, daily_minutes=15, current_level="A2")
    )
    plan = repo.save_plan(
        profile["id"],
        [{"day_index": 1, "topic": "Hotel", "scenario": "Check in", "objective": "Book a room"}],
    )
    session = repo.get_or_create_session(plan[0]["id"], 1, "Hotel")
    first = repo.complete_session(session["id"], {"summary_zh": "第一次"}, overall_score=4)
    second = repo.complete_session(session["id"], {"summary_zh": "第二次"}, overall_score=2)

    assert first["ended_at"] == second["ended_at"]
    assert json.loads(second["summary"])["summary_zh"] == "第一次"
    assert second["overall_score"] == 4



    import json
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    
    # daily_review
    review = repo.save_daily_review(1, "2026-06-22", "completed", {"summary": "good"}, {"signals": "good"}, [1, 2], "raw")
    assert review["id"] is not None
    assert json.loads(review["user_report_json"])["summary"] == "good"
    
    # memory
    mem = repo.save_memory_item(1, "weakness", "bad grammar", "said X", 0.8, "active", review["id"])
    assert mem["id"] is not None
    assert mem["category"] == "weakness"
    
    # plan adjustment
    adj = repo.save_plan_adjustment(1, review["id"], "focus", "Title", "Reason", "Instruction", "high", "active", 3)
    assert adj["id"] is not None
    
    # brief
    brief = repo.save_practice_brief(1, {"role": "NPC"})
    assert brief["id"] is not None


def test_repository_finds_unreviewed_session_dates(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel English",
            total_days=2,
            daily_minutes=15,
            current_level="A2",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [
            {"day_index": 1, "topic": "Airport", "scenario": "Check in", "objective": "Ask for boarding pass"},
            {"day_index": 2, "topic": "Hotel", "scenario": "Check in", "objective": "Ask for room"},
        ],
    )
    session = repo.get_or_create_session(plan[0]["id"], 1, "Airport")
    repo.add_turn(session["id"], "assistant", "Welcome.")
    repo.add_turn(session["id"], "user", "I need check in.")
    with connect(db_path) as connection:
        connection.execute("UPDATE daily_sessions SET started_at = ? WHERE id = ?", ("2026-06-20 10:00:00", session["id"]))

    dates = repo.get_unreviewed_session_dates(profile["id"], today="2026-06-22")

    assert dates == ["2026-06-20"]


def test_repository_skips_already_reviewed_session_dates(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel English",
            total_days=1,
            daily_minutes=15,
            current_level="A2",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [{"day_index": 1, "topic": "Airport", "scenario": "Check in", "objective": "Ask for boarding pass"}],
    )
    session = repo.get_or_create_session(plan[0]["id"], 1, "Airport")
    repo.add_turn(session["id"], "user", "I need check in.")
    with connect(db_path) as connection:
        connection.execute("UPDATE daily_sessions SET started_at = ? WHERE id = ?", ("2026-06-20 10:00:00", session["id"]))
    repo.save_daily_review(profile["id"], "2026-06-20", "completed", {"summary": "Done"}, {}, [session["id"]], "")

    dates = repo.get_unreviewed_session_dates(profile["id"], today="2026-06-22")

    assert dates == []


def test_repository_aggregates_review_sessions_with_turns(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel English",
            total_days=1,
            daily_minutes=15,
            current_level="A2",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [{"day_index": 1, "topic": "Airport", "scenario": "Check in", "objective": "Ask for boarding pass"}],
    )
    session = repo.get_or_create_session(plan[0]["id"], 1, "Airport")
    repo.add_turn(session["id"], "assistant", "Welcome.")
    repo.add_turn(session["id"], "user", "I need check in.")
    with connect(db_path) as connection:
        connection.execute("UPDATE daily_sessions SET started_at = ? WHERE id = ?", ("2026-06-20 10:00:00", session["id"]))

    sessions = repo.get_review_sessions_for_date(profile["id"], "2026-06-20")

    assert sessions[0]["id"] == session["id"]
    assert sessions[0]["topic"] == "Airport"
    assert sessions[0]["turns"][1]["speaker"] == "user"


def test_repository_reads_loop_state_for_next_practice(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel English",
            total_days=2,
            daily_minutes=15,
            current_level="A2",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [
            {"day_index": 1, "topic": "Airport", "scenario": "Check in", "objective": "Ask for boarding pass", "status": "completed"},
            {"day_index": 2, "topic": "Hotel", "scenario": "Check in", "objective": "Ask for room", "status": "pending"},
        ],
    )
    review = repo.save_daily_review(profile["id"], "2026-06-20", "completed", {"summary": "Done"}, {"issue": "grammar"}, [], "")
    memory = repo.save_memory_item(profile["id"], "weakness", "grammar", "daily review", 0.8, "active", review["id"])
    adjustment = repo.save_plan_adjustment(plan[1]["id"], review["id"], "focus", "Grammar focus", "Repeated issue", "Practice past tense", "high", "active", 3)

    assert repo.get_active_memory_items(profile["id"])[0]["id"] == memory["id"]
    assert repo.get_active_plan_adjustments(plan[1]["id"])[0]["id"] == adjustment["id"]
    assert repo.get_latest_completed_daily_review(profile["id"])["id"] == review["id"]


def test_get_prompt_falls_back_to_default_prompts(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    from app.prompts import DEFAULT_PROMPTS
    from app.db import connect
    # 清空可能被播种的行，构造"无用户覆盖"场景
    with connect(db_path) as conn:
        conn.execute("DELETE FROM prompts")
        conn.commit()
    assert repo.get_prompt("goal_agent_system") == DEFAULT_PROMPTS["goal_agent_system"]
    assert repo.get_prompt("nonexistent_prompt_name") is None


def test_update_prompt_upserts_when_row_absent(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    assert repo.update_prompt("goal_agent_system", "覆盖内容") is True
    assert repo.get_prompt("goal_agent_system") == "覆盖内容"


def test_init_db_does_not_seed_prompts(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    from app.db import connect
    with connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM prompts").fetchone()["c"]
    assert count == 0


def test_get_growth_summary_decodes_review_memory_and_adjustments(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="hotel check-in speaking",
            total_days=7,
            daily_minutes=20,
            current_level="B1",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [
            {
                "day_index": 1,
                "topic": "Hotel check-in",
                "scenario": "Asking hotel front desk questions",
                "objective": "Explain travel needs clearly",
                "status": "pending",
            }
        ],
    )
    review = repo.save_daily_review(
        profile_id=profile["id"],
        review_date="2026-06-22",
        status="completed",
        user_report={
            "summary": "You practiced tradeoff explanations.",
            "next_focus": "Use clearer structure.",
        },
        structured_analysis={
            "weaknesses": ["unclear structure"],
            "strengths": ["kept speaking"],
        },
        source_session_ids=[1],
        raw_agent_output="{}",
    )
    repo.save_memory_item(
        profile["id"],
        "weakness",
        "Often misses structured answers",
        "Review 1",
        0.85,
        "active",
        review["id"],
    )
    repo.save_plan_adjustment(
        plan[0]["id"],
        review["id"],
        "focus_shift",
        "Practice STAR structure",
        "Weak structure",
        "Start with context-impact-action",
        "high",
        "active",
        3,
    )

    summary = repo.get_growth_summary(profile["id"])

    assert summary["latest_review"]["user_report"]["summary"] == "You practiced tradeoff explanations."
    assert summary["latest_review"]["structured_analysis"]["weaknesses"] == ["unclear structure"]
    assert summary["latest_review"]["source_session_ids"] == [1]
    assert summary["active_memory"][0]["content"] == "Often misses structured answers"
    assert summary["active_adjustments"][0]["title"] == "Practice STAR structure"


def test_upsert_memory_item_merges_same_category_content(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="PM interview",
            total_days=7,
            daily_minutes=20,
            current_level="B1",
        )
    )

    first = repo.upsert_memory_item(
        profile["id"],
        "weakness",
        "Uses vague product language",
        "Day 1",
        0.6,
        None,
    )
    second = repo.upsert_memory_item(
        profile["id"],
        "weakness",
        "Uses vague product language",
        "Day 2",
        0.9,
        None,
    )
    items = repo.get_memory_items(profile["id"])

    assert first["id"] == second["id"]
    assert len(items) == 1
    assert items[0]["confidence"] == 0.9
    assert "Day 1" in items[0]["evidence"]
    assert "Day 2" in items[0]["evidence"]


def test_active_plan_adjustments_exclude_expired_items(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="PM interview",
            total_days=7,
            daily_minutes=20,
            current_level="B1",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [{"day_index": 1, "topic": "A", "scenario": "B", "objective": "C"}],
    )
    review = repo.save_daily_review(profile["id"], "2026-06-01", "completed", {}, {}, [], "{}")
    adjustment = repo.save_plan_adjustment(
        plan[0]["id"],
        review["id"],
        "focus_shift",
        "Old adjustment",
        "Old",
        "Old",
        "low",
        "active",
        1,
    )
    with connect(db_path) as connection:
        connection.execute(
            "UPDATE plan_adjustments SET created_at = ? WHERE id = ?",
            ("2026-06-01 08:00:00", adjustment["id"]),
        )

    active = repo.get_active_plan_adjustments(plan[0]["id"], today="2026-06-23")

    assert active == []


def test_mark_plan_day_status_updates_learning_plan(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="PM interview",
            total_days=7,
            daily_minutes=20,
            current_level="B1",
        )
    )
    plan = repo.save_plan(
        profile["id"],
        [{"day_index": 1, "topic": "A", "scenario": "B", "objective": "C"}],
    )

    repo.mark_plan_day_status(plan[0]["id"], "in_progress")
    current = repo.get_plan(profile["id"])[0]

    assert current["status"] == "in_progress"


def test_save_and_get_agent_runs(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Travel speaking",
            total_days=3,
            daily_minutes=15,
            current_level="B1",
        )
    )

    saved = repo.save_agent_run(
        profile_id=profile["id"],
        plan_day_id=None,
        session_id=None,
        agent_name="CoachOrchestratorAgent",
        trigger_source="today_entry",
        input_data={"profile_id": profile["id"]},
        tool_calls=[],
        output_data={"coach_explanation_zh": "今天先练酒店入住。"},
        validation_status="passed",
        error_message=None,
    )
    runs = repo.get_agent_runs(profile["id"])

    assert saved["id"] == runs[0]["id"]
    assert runs[0]["agent_name"] == "CoachOrchestratorAgent"
    assert runs[0]["input"]["profile_id"] == profile["id"]
    assert runs[0]["output"]["coach_explanation_zh"] == "今天先练酒店入住。"
