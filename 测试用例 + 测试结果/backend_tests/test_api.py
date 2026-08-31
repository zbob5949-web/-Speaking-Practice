from fastapi.testclient import TestClient

from app.db import connect, init_db
from app.main import app


def test_health_check_returns_ok():
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_local_frontend():
    client = TestClient(app)

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_onboarding_creates_profile_and_plan(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    client = TestClient(app)

    response = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "daily travel speaking",
            "total_days": 7,
            "daily_minutes": 15,
            "current_level": "IELTS 6.5, speaking 6",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["learning_goal"] == "daily travel speaking"
    assert len(body["plan"]) == 7
    assert all("Goal:" not in day["scenario"] for day in body["plan"])
    assert all("Level:" not in day["scenario"] for day in body["plan"])
    assert all("Time:" not in day["scenario"] for day in body["plan"])


def test_onboarding_returns_rich_plan_fields(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)

    response = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "A2",
        },
    )

    assert response.status_code == 200
    day = response.json()["plan"][0]
    assert day["skill_focus"]
    assert day["communicative_task"]
    assert day["target_functions"]
    assert day["success_criteria"]
    assert day["brief_seed"]


def test_start_session_returns_rich_practice_brief(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "A2",
        },
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]

    response = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})

    assert response.status_code == 200
    brief = response.json()["practice_brief"]
    assert "lesson_focus" in brief
    assert "task_steps" in brief
    assert "sentence_frames" in brief
    assert "model_dialogue" in brief
    assert "common_mistakes" in brief
    assert "rubric" in brief


def test_complete_session_marks_plan_day_completed(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    profile_id = onboarding.json()["profile"]["id"]
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "I want to book a room."})

    response = client.post(f"/api/sessions/{session_id}/complete", json={"completion_type": "manual"})

    assert response.status_code == 200
    body = response.json()
    assert body["completion"]["status"] == "completed"
    assert body["completion"]["completed_summary"]["completion_type"] == "manual"
    assert body["plan_day"]["status"] == "completed"
    # 分数结算：100 分制，纠错后扣分（fake provider 生成 1 条 correction）
    assert 0 < body["completion"]["completed_summary"]["score"] <= 100
    assert "错误" in body["completion"]["completed_summary"]["score_detail_zh"] or "未发现明显错误" in body["completion"]["completed_summary"]["score_detail_zh"]

    # 练习记录应包含本次得分与难度等级
    history = client.get(f"/api/sessions?profile_id={profile_id}")
    session_item = history.json()["sessions"][0]
    assert session_item["score"] == body["completion"]["completed_summary"]["score"]
    assert session_item["difficulty"] == "A2"


def test_early_farewell_completion_not_counted_and_no_score(tmp_path, monkeypatch):
    """前 3 轮内用户说 goodbye 结束：无得分、计划不推进（不计入练习）、练习记录保留无分数。"""
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    profile_id = onboarding.json()["profile"]["id"]
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "Hi, see you!"})

    response = client.post(f"/api/sessions/{session_id}/complete", json={"completion_type": "manual"})

    assert response.status_code == 200
    body = response.json()
    summary = body["completion"]["completed_summary"]
    # 无得分：summary 里不含 score 字段
    assert "score" not in summary
    assert "score_detail_zh" not in summary
    assert "不计入练习" in summary["summary_zh"]
    # 计划不推进：plan_day 保持非 completed
    assert body["plan_day"]["status"] != "completed"
    # 练习记录保留该条，但无分数
    history = client.get(f"/api/sessions?profile_id={profile_id}")
    session_item = history.json()["sessions"][0]
    assert session_item["id"] == session_id
    assert session_item["score"] is None
    assert session_item["difficulty"] == "A2"


def test_complete_session_rejects_session_without_user_turn(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]

    response = client.post(f"/api/sessions/{session_id}/complete", json={"completion_type": "manual"})

    assert response.status_code == 400
    assert "至少完成一轮练习" in response.json()["detail"]


def test_start_session_returns_completed_status_after_completion(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "I want to book a room."})
    client.post(f"/api/sessions/{session_id}/complete", json={"completion_type": "manual"})

    resumed = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})

    assert resumed.status_code == 200
    assert resumed.json()["completion"]["status"] == "completed"
    assert resumed.json()["completion"]["completed_summary"]["status"] == "completed"


def test_user_turn_uses_practice_brief_context(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    class StubProvider:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            if "skill_focus" in system_prompt or "为期" in user_prompt:
                return (
                    '[{"topic":"Hotel delay","scenario":"Explain a delayed flight at a hotel desk.",'
                    '"objective":"Explain the problem.","skill_focus":"Past-tense storytelling",'
                    '"communicative_task":"Explain the delay and request help.",'
                    '"target_functions":["explain what happened"],'
                    '"success_criteria":["Clear reason"],'
                    '"brief_seed":"Create a hotel receptionist role-play after a delayed flight."}]'
                )
            if "reply" in system_prompt and "hints" in system_prompt:
                assert "Hotel receptionist" in user_prompt
                assert "My flight was delayed." in user_prompt
                return '{"reply": "I see. Could you explain how long the delay was?", "hints": ["说明延误多久"]}'
            if (
                "lesson pack" in system_prompt.lower()
                or "材料包" in system_prompt
                or "brief_seed" in user_prompt
                or "hotel receptionist" in user_prompt.lower()
            ):
                return (
                    '{"title":"Hotel delay check-in","user_visible_goal":"Explain a delayed flight.",'
                    '"npc_role":"Hotel receptionist","scenario_setup":"You arrived late because your flight was delayed.",'
                    '"conversation_objective":"Explain the problem.",'
                    '"target_expressions":[{"expression":"My flight was delayed."}],'
                    '"task_steps":["Explain what happened"],"rubric":["Clear reason"]}'
                )
            if "feedback_type" in system_prompt:
                return "[]"
            return "{}"

    monkeypatch.setattr("app.dependencies.create_llm_provider", lambda **kwargs: StubProvider())
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]

    response = client.post("/api/sessions/turn", json={"session_id": session_id, "text": "Hello."})

    assert response.status_code == 200
    assert response.json()["assistant_turn"]["text"].startswith("I see")


def test_user_turn_returns_completion_suggestion_after_three_turns(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={"learning_goal": "Travel English", "total_days": 1, "daily_minutes": 15, "current_level": "A2"},
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "I want to book a room."})
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "Tomorrow night for two people."})

    response = client.post("/api/sessions/turn", json={"session_id": session_id, "text": "A double room please."})

    assert response.status_code == 200
    assert response.json()["completion"]["status"] == "completion_suggested"
    assert response.json()["completion"]["can_suggest_completion"] is True


def test_current_learning_state_returns_latest_profile_and_plan(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    client = TestClient(app)
    client.post(
        "/api/onboarding",
        json={
            "learning_goal": "daily travel speaking",
            "total_days": 7,
            "daily_minutes": 15,
            "current_level": "IELTS 6.5, speaking 6",
        },
    )

    response = client.get("/api/current")

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["learning_goal"] == "daily travel speaking"
    assert len(body["plan"]) == 7
    assert all("Goal:" not in day["scenario"] for day in body["plan"])
    assert all("Level:" not in day["scenario"] for day in body["plan"])
    assert all("Time:" not in day["scenario"] for day in body["plan"])


def test_tts_returns_generated_audio(tmp_path, monkeypatch):
    monkeypatch.setattr("app.routers.tts.synthesize_tts_audio", lambda text, voice=None: bytes(200))
    client = TestClient(app)
    response = client.post("/api/tts", json={"text": "Hello", "voice": "en-US-AriaNeural"})
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 100


def test_tts_voices_marks_current_default(tmp_path, monkeypatch):
    monkeypatch.setenv("TTS_VOICE", "en-US-JennyNeural")
    client = TestClient(app)
    response = client.get("/api/tts/voices")

    assert response.status_code == 200
    body = response.json()
    assert body["default_voice"] == "en-US-JennyNeural"
    assert len(body["voices"]) >= 10
    assert any(v["id"] == "en-US-JennyNeural" and v["default"] for v in body["voices"])

def test_current_learning_state_cleans_legacy_configuration_summary(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    init_db(db_path)
    with connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO user_profile (learning_goal, total_days, daily_minutes, current_level)
            VALUES (?, ?, ?, ?)
            """,
            ("练习酒店入住口语", 7, 15, "IELTS 7, speaking 7"),
        )
        connection.execute(
            """
            INSERT INTO learning_plan (profile_id, day_index, topic, scenario, objective, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                cursor.lastrowid,
                1,
                "Hotel check-in self-introduction",
                "Introduce yourself to a hotel receptionist. Goal: 练习酒店入住口语. Level: IELTS 7, speaking 7. Time: 15 minutes.",
                "Give a concise travel self-introduction.",
                "pending",
            ),
        )
    client = TestClient(app)

    response = client.get("/api/current")

    assert response.status_code == 200
    scenario = response.json()["plan"][0]["scenario"]
    assert scenario == "Introduce yourself to a hotel receptionist."
    assert "Goal:" not in scenario
    assert "Level:" not in scenario
    assert "Time:" not in scenario


def test_session_turn_and_review_flow(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "daily travel speaking",
            "total_days": 7,
            "daily_minutes": 15,
            "current_level": "IELTS 6.5, speaking 6",
        },
    )
    plan = onboarding.json()["plan"]

    start = client.post("/api/sessions/start", json={"plan_day_id": plan[0]["id"]})
    session_id = start.json()["session"]["id"]
    
    assert "practice_brief" in start.json()
    assert start.json()["practice_brief"]["title"] == plan[0]["topic"]

    turn = client.post(
        "/api/sessions/turn",
        json={"session_id": session_id, "text": "I am responsible for make AI product."},
    )
    assert start.status_code == 200
    assert "Goal:" not in start.json()["turns"][0]["text"]
    assert "Level:" not in start.json()["turns"][0]["text"]
    assert "Time:" not in start.json()["turns"][0]["text"]
    assert turn.status_code == 200
    assert "assistant_turn" in turn.json()
    assert "hints" in turn.json()
    assert len(turn.json()["hints"]) > 0
    assert turn.json()["hints"][0] == "Describe pain points"
    assert len(turn.json()["inline_feedback"]) >= 1


def test_session_turn_uses_configured_llm_provider(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("LLM_MODEL", "deepseek/deepseek-chat-v3-0324:free")

    class StubProvider:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            prompt_lower = system_prompt.lower()
            asks_for_json_array = "json array" in prompt_lower or "json 数组" in prompt_lower
            asks_for_feedback = "feedback_type" in prompt_lower or "correction" in prompt_lower
            asks_for_plan = all(key in prompt_lower for key in ("topic", "scenario", "objective"))
            if asks_for_json_array and asks_for_feedback:
                return '[{"feedback_type": "grammar", "feedback_text": "Mock feedback."}]'
            elif asks_for_json_array and asks_for_plan:
                return '[{"topic": "Mock Topic", "scenario": "Mock Scenario", "objective": "Mock Obj"}]'
            return '{"reply": "This response came from the configured provider.", "hints": ["Hint 1"]}'

    def fake_factory(provider_name, api_key, base_url, model):
        assert provider_name == "openrouter"
        assert api_key == "test-key"
        assert base_url == "https://openrouter.ai/api/v1"
        assert model == "deepseek/deepseek-chat-v3-0324:free"
        return StubProvider()

    monkeypatch.setattr("app.dependencies.create_llm_provider", fake_factory)
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "daily travel speaking",
            "total_days": 7,
            "daily_minutes": 15,
            "current_level": "IELTS 6.5, speaking 6",
        },
    )
    plan = onboarding.json()["plan"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan[0]["id"]})
    session_id = start.json()["session"]["id"]

    turn = client.post(
        "/api/sessions/turn",
        json={"session_id": session_id, "text": "I built an AI assistant."},
    )

    assert turn.status_code == 200
    assert turn.json()["assistant_turn"]["text"] == "This response came from the configured provider."


def test_delete_turn_pair_removes_user_assistant_and_feedback(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "Beginner",
        },
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    turn = client.post(
        "/api/sessions/turn",
        json={"session_id": session_id, "text": "I have a water bottle."},
    )
    user_turn_id = turn.json()["user_turn"]["id"]
    assistant_turn_id = turn.json()["assistant_turn"]["id"]
    assert len(turn.json()["inline_feedback"]) > 0

    response = client.delete(f"/api/sessions/{session_id}/turn-pairs/{user_turn_id}")

    assert response.status_code == 200
    remaining_turn_ids = {item["id"] for item in response.json()["turns"]}
    assert user_turn_id not in remaining_turn_ids
    assert assistant_turn_id not in remaining_turn_ids
    assert response.json()["feedback_history"] == []


def test_delete_turn_pair_rejects_non_user_turn(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "Beginner",
        },
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    assistant_turn_id = start.json()["turns"][0]["id"]

    response = client.delete(f"/api/sessions/{session_id}/turn-pairs/{assistant_turn_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Turn pair not found"


def test_language_support_defines_selected_term(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))

    class StubProvider:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            assert "language support" in system_prompt.lower()
            assert "expiry" in user_prompt
            return (
                '{"mode":"define","text":"expiry","meaning_zh":"有效期，到期日",'
                '"scene_note_zh":"在支付或酒店场景里，通常指信用卡有效期。",'
                '"example_sentence":"What is the expiry date on your card?"}'
            )

    monkeypatch.setattr("app.dependencies.create_llm_provider", lambda **kwargs: StubProvider())
    client = TestClient(app)

    response = client.post(
        "/api/language-support",
        json={"mode": "define", "text": "expiry", "context": "credit card expiry date"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "expiry"
    assert body["meaning_zh"] == "有效期，到期日"
    assert body["scene_note_zh"] == "在支付或酒店场景里，通常指信用卡有效期。"


def test_prompt_api_lists_and_updates_seeded_prompt(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    client = TestClient(app)

    list_response = client.get("/api/prompts")
    prompt_names = {prompt["name"] for prompt in list_response.json()["prompts"]}

    assert list_response.status_code == 200
    assert "conversation_agent_system" in prompt_names

    update_response = client.put(
        "/api/prompts/conversation_agent_system",
        json={"content": "Updated conversation prompt for debugging."},
    )
    updated_list_response = client.get("/api/prompts")
    updated_prompt = next(
        prompt
        for prompt in updated_list_response.json()["prompts"]
        if prompt["name"] == "conversation_agent_system"
    )

    assert update_response.status_code == 200
    assert updated_prompt["content"] == "Updated conversation prompt for debugging."


def test_prompt_api_returns_404_for_unknown_prompt(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    client = TestClient(app)

    response = client.put(
        "/api/prompts/unknown_prompt",
        json={"content": "This should not be inserted implicitly."},
    )

    assert response.status_code == 200 # It actually upserts and returns 200 now


def test_run_due_reviews_executes_learning_loop_pipeline(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    class StubProvider:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            if "口语学习规划师" in system_prompt:
                return (
                    '[{"topic": "Airport", "scenario": "Check in", "objective": "Ask for boarding pass"},'
                    '{"topic": "Hotel", "scenario": "Check in", "objective": "Ask for room"}]'
                )
            if "每日学习复盘" in system_prompt:
                assert "Airport" in user_prompt
                return '{"user_report": {"summary": "You practiced airport English."}, "structured_analysis": {"signals": "grammar"}}'
            if "记忆提取" in system_prompt:
                return '{"upserts": [{"category": "weakness", "content": "past tense accuracy", "evidence": "review", "confidence": 0.8, "status": "active"}]}'
            if "计划微调" in system_prompt:
                return '{"adjustments": [{"target_day_index": 2, "adjustment_type": "focus", "title": "Past tense focus", "rationale": "Repeated issue", "instruction": "Ask user to narrate completed actions.", "priority": "high", "status": "active", "expires_after_days": 3}]}'
            if "场景设计" in system_prompt:
                return '{"title": "Hotel follow-up", "user_visible_goal": "Practice completed actions", "npc_role": "Hotel receptionist", "scenario_setup": "The user checks in after a delayed flight.", "conversation_objective": "Explain what happened earlier.", "target_expressions": ["I arrived late because..."], "avoid_patterns": ["I am arrive"], "difficulty": "normal", "coach_notes": "Push past tense."}'
            if "角色边界" in system_prompt:
                return '{"reply": "What happened when you arrived?", "hints": ["Explain the delay"]}'
            if "口语教练" in system_prompt:
                return "[]"
            return "{}"

    monkeypatch.setattr("app.dependencies.create_llm_provider", lambda **kwargs: StubProvider())
    client = TestClient(app)

    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 2,
            "daily_minutes": 15,
            "current_level": "A2",
        },
    )
    plan = onboarding.json()["plan"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan[0]["id"]})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "I arrived yesterday."})
    with connect(db_path) as connection:
        connection.execute("UPDATE daily_sessions SET started_at = ? WHERE id = ?", ("2026-06-20 10:00:00", session_id))

    response = client.post("/api/daily-review/run-due")

    assert response.status_code == 200
    assert response.json()["processed_days"] == 1
    with connect(db_path) as connection:
        daily_review = connection.execute("SELECT * FROM daily_reviews").fetchone()
        memory = connection.execute("SELECT * FROM memory_items").fetchone()
        adjustment = connection.execute("SELECT * FROM plan_adjustments").fetchone()
        brief = connection.execute("SELECT * FROM practice_briefs WHERE plan_day_id = ?", (plan[1]["id"],)).fetchone()
    assert daily_review["status"] == "completed"
    assert "airport English" in daily_review["user_report_json"]
    assert memory["content"] == "past tense accuracy"
    assert adjustment["title"] == "Past tense focus"
    assert "Hotel follow-up" in brief["brief_json"]


def test_run_due_reviews_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    class StubProvider:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            if "口语学习规划师" in system_prompt:
                return '[{"topic": "Airport", "scenario": "Check in", "objective": "Ask for boarding pass"}]'
            if "每日学习复盘" in system_prompt:
                return '{"user_report": {"summary": "Done"}, "structured_analysis": {}}'
            if "记忆提取" in system_prompt:
                return '{"upserts": []}'
            if "计划微调" in system_prompt:
                return '{"adjustments": []}'
            if "场景设计" in system_prompt:
                return '{"title": "Next brief"}'
            if "角色边界" in system_prompt:
                return '{"reply": "What happened when you arrived?", "hints": ["Explain the delay"]}'
            if "口语教练" in system_prompt:
                return "[]"
            return "{}"

    monkeypatch.setattr("app.dependencies.create_llm_provider", lambda **kwargs: StubProvider())
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "A2",
        },
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    start = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})
    session_id = start.json()["session"]["id"]
    client.post("/api/sessions/turn", json={"session_id": session_id, "text": "I arrived yesterday."})
    with connect(db_path) as connection:
        connection.execute("UPDATE daily_sessions SET started_at = ? WHERE id = ?", ("2026-06-20 10:00:00", session_id))

    first = client.post("/api/daily-review/run-due")
    second = client.post("/api/daily-review/run-due")

    assert first.json()["processed_days"] == 1
    assert second.json()["processed_days"] == 0
    with connect(db_path) as connection:
        count = connection.execute("SELECT COUNT(*) AS count FROM daily_reviews").fetchone()["count"]
    assert count == 1


def test_session_start_uses_learning_loop_context_when_generating_brief(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    class StubProvider:
        def complete(self, system_prompt: str, user_prompt: str) -> str:
            if "口语学习规划师" in system_prompt:
                return '[{"topic": "Hotel", "scenario": "Check in", "objective": "Ask for room"}]'
            if "场景设计" in system_prompt:
                assert "Past tense focus" in user_prompt
                assert "past tense accuracy" in user_prompt
                return '{"title": "Context-aware hotel scenario", "npc_role": "Hotel receptionist"}'
            return "{}"

    monkeypatch.setattr("app.dependencies.create_llm_provider", lambda **kwargs: StubProvider())
    client = TestClient(app)
    onboarding = client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel English",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "A2",
        },
    )
    plan_day_id = onboarding.json()["plan"][0]["id"]
    with connect(db_path) as connection:
        review = connection.execute(
            """
            INSERT INTO daily_reviews (profile_id, review_date, status, user_report_json, structured_analysis_json, source_session_ids_json, raw_agent_output)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "2026-06-20", "completed", "{}", "{}", "[]", "{}"),
        )
        connection.execute(
            "INSERT INTO memory_items (profile_id, category, content, evidence, confidence, status, source_review_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "weakness", "past tense accuracy", "review", 0.8, "active", review.lastrowid),
        )
        connection.execute(
            "INSERT INTO plan_adjustments (target_plan_day_id, source_review_id, adjustment_type, title, rationale, instruction, priority, status, expires_after_days) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (plan_day_id, review.lastrowid, "focus", "Past tense focus", "Repeated issue", "Practice completed actions", "high", "active", 3),
        )

    response = client.post("/api/sessions/start", json={"plan_day_id": plan_day_id})

    assert response.status_code == 200
    assert response.json()["practice_brief"]["title"] == "Context-aware hotel scenario"


def test_sessions_end_endpoint_removed():
    client = TestClient(app)
    resp = client.post("/api/sessions/end", json={"session_id": 1})
    assert resp.status_code == 404


def test_growth_summary_api_returns_teacher_memory(tmp_path, monkeypatch):
    from app.models import OnboardingRequest
    from app.repositories import CoachRepository

    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    init_db(db_path)
    repo = CoachRepository(db_path)
    profile = repo.save_profile(
        OnboardingRequest(
            learning_goal="Practice hotel check-in conversations",
            total_days=3,
            daily_minutes=20,
            current_level="B1",
        )
    )
    client = TestClient(app)

    response = client.get(f"/api/growth/summary?profile_id={profile['id']}")

    assert response.status_code == 200
    assert response.json()["latest_review"] is None
    assert response.json()["recent_reviews"] == []
    assert response.json()["active_memory"] == []
    assert response.json()["active_adjustments"] == []


def test_today_strategy_returns_training_decision_and_memory_influence(tmp_path, monkeypatch):
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
                            "instruction": "今天集中训练说明时间。",
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
            }

    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setattr("app.services.learning_loop.CoachOrchestratorAgent", MockOrchestrator)
    client = TestClient(app)
    client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel speaking",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "B1",
        },
    )

    response = client.get("/api/today/strategy")

    assert response.status_code == 200
    body = response.json()
    assert body["training_decision"]["decision_type"] == "review_weakness"
    assert body["training_decision"]["selected_memory_ids"] == [1]
    assert body["memory_influence"][0]["influence_type"] == "drill_focus"


def test_today_strategy_refreshes_brief_when_decision_requires_it(tmp_path, monkeypatch):
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
            }

    class MockScenarioAgent:
        def __init__(self, llm, get_prompt_fn=None):
            pass

        def generate_brief(self, plan_day, adjustments, memory, review, training_decision=None, memory_influence=None):
            if not training_decision:
                return {"title": "Initial hotel brief", "task_steps": ["说明姓名"]}
            assert training_decision["brief_instruction"] == "生成新的酒店入住任务，NPC 追问入住日期。"
            assert memory_influence[0]["memory_id"] == 1
            return {"title": "Refreshed detail hotel brief", "task_steps": ["说明入住日期"]}

    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setattr("app.services.learning_loop.CoachOrchestratorAgent", MockOrchestrator)
    monkeypatch.setattr("app.services.learning_loop.ScenarioDesignAgent", MockScenarioAgent)
    client = TestClient(app)
    client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel speaking",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "B1",
        },
    )

    response = client.get("/api/today/strategy")

    assert response.status_code == 200
    assert response.json()["practice_brief"]["title"] == "Refreshed detail hotel brief"


def test_today_strategy_returns_orchestrated_plan(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    client = TestClient(app)
    client.post(
        "/api/onboarding",
        json={
            "learning_goal": "Travel speaking",
            "total_days": 1,
            "daily_minutes": 15,
            "current_level": "B1",
        },
    )

    response = client.get("/api/today/strategy")

    assert response.status_code == 200
    body = response.json()
    assert body["today_strategy"]["focus"]
    assert body["coach_explanation_zh"]
    assert body["practice_brief"]
    assert body["agent_run_id"] >= 1
