"""会话业务：开启、完成、回合（同步/流式）与回合删除。"""
import concurrent.futures
import json
import threading

from fastapi import HTTPException

from app.agents import ConversationAgent, InlineFeedbackAgent, ScenarioDesignAgent, clean_plan_day
from app.completion import build_completion_status, build_completion_summary, is_early_farewell
from app import dependencies as deps
from app.models import CompleteSessionRequest, StartSessionRequest, UserTurnRequest
from app.scenarios import SCENARIO_EXPRESSIONS, SCENARIO_OPENERS, get_scenario, tier_for_level
from app.services.practice_brief import load_brief


def _scenario_brief(scenario: dict) -> dict:
    """由手工场景库构造 practice brief（不依赖 LLM，保证可靠）。"""
    band = scenario.get("difficulty") or {}
    return {
        "title": scenario.get("title", ""),
        "user_visible_goal": scenario.get("objective", ""),
        "npc_role": scenario.get("npc_role", ""),
        "scenario_setup": scenario.get("background", ""),
        "conversation_objective": scenario.get("objective", ""),
        "learner_role": scenario.get("learner_role", ""),
        "target_expressions": list(SCENARIO_EXPRESSIONS.get(scenario.get("id", ""), [])),
        "difficulty": band.get("level", ""),
        "lesson_focus": band.get("sentence_complexity", ""),
        "task_steps": list(band.get("target_functions", []) or []),
    }


def _load_session_context(repo, session_id: int) -> dict:
    """加载会话、画像、当前计划日与 practice brief 等回合所需上下文。"""
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    profile = repo.get_latest_profile()

    plan_day = None
    if session.get("plan_day_id"):
        plan_day = repo.get_plan_day_by_id(session["plan_day_id"])
    elif profile:
        # Fallback for older sessions without plan_day_id
        plan = repo.get_plan(profile["id"])
        for day in plan:
            if day["day_index"] == session["day_index"]:
                plan_day = day
                break

    objective = plan_day["objective"] if plan_day else "Practice speaking"
    user_level = profile["current_level"] if profile else "Intermediate"
    learning_goal = profile["learning_goal"] if profile else "Improve English"
    brief = load_brief(repo, plan_day["id"]) if plan_day else None
    if brief is None and session.get("scenario_id") == "free_talk":
        # 自由对话：使用专属语境，让对话与实时纠错都贴合自由聊天
        brief = _free_talk_brief(profile)
        objective = brief["conversation_objective"]
    elif brief is None and session.get("scenario_id"):
        scenario = get_scenario(session["scenario_id"])
        if scenario:
            brief = _scenario_brief(scenario)
            objective = brief["conversation_objective"]

    return {
        "session": session,
        "profile": profile,
        "plan_day": plan_day,
        "objective": objective,
        "user_level": user_level,
        "learning_goal": learning_goal,
        "brief": brief,
    }


def _user_level_for_session(repo, session: dict) -> str:
    """从会话归属的画像（或最新画像）取用户水平，用于按难度区分结束条件等。"""
    profile = None
    if session.get("profile_id"):
        profile = repo.get_profile(session["profile_id"])
    if profile is None:
        profile = repo.get_latest_profile()
    return profile["current_level"] if profile else "A2"


def _summary_score(raw_summary: object) -> int | None:
    """从会话 summary（JSON 字符串或 dict）中解析本次得分，旧数据无分数返回 None。"""
    if not raw_summary:
        return None
    if isinstance(raw_summary, dict):
        return raw_summary.get("score")
    try:
        data = json.loads(raw_summary)
        return data.get("score") if isinstance(data, dict) else None
    except (TypeError, json.JSONDecodeError):
        return None


def enrich_sessions(repo, sessions: list[dict]) -> list[dict]:
    """为练习记录附加「难度等级」与「本次得分（100 分制）」，供「我的」页展示。"""
    profile_cache: dict[int | None, dict | None] = {}

    def profile_for(session: dict) -> dict | None:
        pid = session.get("profile_id") or session.get("plan_profile_id")
        if pid not in profile_cache:
            profile_cache[pid] = repo.get_profile(pid) if pid else repo.get_latest_profile()
        return profile_cache[pid]

    enriched = []
    for session in sessions:
        item = dict(session)
        profile = profile_for(session)
        level = profile["current_level"] if profile else "A2"
        if session.get("scenario_id"):
            if session["scenario_id"] == "free_talk":
                item["difficulty"] = "自由"
            else:
                scenario = get_scenario(session["scenario_id"], level)
                band = (scenario or {}).get("difficulty") or {}
                item["difficulty"] = band.get("level") or level
        else:
            item["difficulty"] = level
        item["score"] = _summary_score(session.get("summary"))
        enriched.append(item)
    return enriched


_start_lock = threading.Lock()


def start_session(request: StartSessionRequest) -> dict[str, object]:
    repo = deps.get_repository()

    # 会话启动加锁：避免并发（如 StrictMode 双挂载）同时读到空回合、重复写入欢迎词
    with _start_lock:
        if request.scenario_id:
            return _start_scenario_session(repo, request)

        plan_day = repo.get_plan_day_by_id(request.plan_day_id)
        if plan_day is None:
            raise HTTPException(status_code=404, detail="Plan day not found")
        plan_day = clean_plan_day(plan_day)
        if plan_day.get("status") == "pending":
            repo.mark_plan_day_status(plan_day["id"], "in_progress")
            plan_day["status"] = "in_progress"

        session = repo.get_or_create_session(plan_day_id=plan_day["id"], day_index=plan_day["day_index"], topic=plan_day["topic"])
        turns = repo.get_turns(session["id"])
        feedback_history = repo.get_inline_feedback_for_session(session["id"])

        brief = load_brief(repo, plan_day["id"])
        if brief is None:
            settings = deps.load_settings()
            llm = deps.create_llm_provider(
                provider_name=settings.llm_provider,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                model=settings.chat_model,
            )
            profile = repo.get_profile(plan_day["profile_id"])
            memory = repo.get_active_memory_items(profile["id"]) if profile else []
            adjustments = repo.get_active_plan_adjustments(plan_day["id"])
            latest_review = repo.get_latest_completed_daily_review(profile["id"]) if profile else {}
            brief = ScenarioDesignAgent(llm, repo.get_prompt).generate_brief(
                plan_day,
                adjustments,
                memory,
                latest_review or {},
            )
            repo.save_practice_brief(plan_day["id"], brief)

        if not turns:
            assistant_text = (
                f"Today we will practice: {plan_day['topic']}. "
                f"{plan_day['scenario']} Let's start with your first answer."
            )
            assistant_turn = repo.add_turn(session["id"], "assistant", assistant_text)
            turns = [assistant_turn]

        completion = build_completion_status(session, turns, feedback_history, brief, user_level=_user_level_for_session(repo, session))
        return {
            "session": session,
            "turns": turns,
            "plan_day": plan_day,
            "feedback_history": feedback_history,
            "practice_brief": brief,
        "completion": completion,
    }


def _scenario_opener(scenario: dict, level: str) -> str:
    """按难度三档取该场景的差异化开场白，避免所有卡片雷同。"""
    openers = SCENARIO_OPENERS.get(scenario.get("id", ""), {})
    tier = tier_for_level(level or "")
    return openers.get(tier, openers.get("intermediate", ""))


def _start_scenario_session(repo, request: StartSessionRequest) -> dict[str, object]:
    """按手工场景启动独立会话（不占学习计划进度）。

    - 启动前自动删除该画像下其他场景未结束的会话（任务：切换场景即清空上次对话）。
    - 支持内置自由对话场景 free_talk，不依赖场景库。
    """
    profile = repo.get_profile(request.profile_id) if request.profile_id else repo.get_latest_profile()
    level = profile["current_level"] if profile else "A2"
    if request.scenario_id == "free_talk":
        return _start_free_talk(repo, profile)

    scenario = get_scenario(request.scenario_id, level)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    profile_id = profile["id"] if profile else None
    # 选择新场景：先清掉上次场景未结束的对话，避免再次进入时残留旧内容
    repo.delete_open_scenario_sessions(profile_id, keep_scenario_id=scenario["id"])
    session = repo.get_or_create_session(
        plan_day_id=None,
        day_index=0,
        topic=scenario["title"],
        scenario_id=scenario["id"],
        profile_id=profile_id,
    )
    turns = repo.get_turns(session["id"])
    feedback_history = repo.get_inline_feedback_for_session(session["id"])
    brief = _scenario_brief(scenario)

    if not turns:
        assistant_text = _scenario_opener(scenario, level) or (
            f"Let's practice: {scenario['title']}. "
            f"{scenario['background']} Start with your first answer."
        )
        turns = [repo.add_turn(session["id"], "assistant", assistant_text)]

    completion = build_completion_status(session, turns, feedback_history, brief, user_level=profile["current_level"] if profile else "A2")
    return {
        "session": session,
        "turns": turns,
        "plan_day": None,
        "feedback_history": feedback_history,
        "practice_brief": brief,
        "completion": completion,
    }


def _free_talk_brief(profile: dict | None) -> dict:
    """自由对话的 practice brief：回合与纠错共用同一语境。"""
    return {
        "title": "自由对话",
        "user_visible_goal": "和教练自由聊天，想聊什么都可以",
        "npc_role": "英语口语陪练教练",
        "scenario_setup": "没有固定剧本，聊你感兴趣的话题：今天发生了什么、最近的热点、你的想法……",
        "conversation_objective": "在真实聊天中自然开口，练习流利度与表达准确性",
        "learner_role": "自由交谈者",
        "lesson_focus": "流利度与自然表达，教练会像朋友一样接话并适时给出表达建议",
        "target_expressions": [],
        "task_steps": [],
        "difficulty": profile["current_level"] if profile else "A2",
    }


def _start_free_talk(repo, profile: dict | None) -> dict[str, object]:
    """自由对话会话：无固定剧本，随时可从今日板块进入，并在切换场景时一并清空。"""
    profile_id = profile["id"] if profile else None
    repo.delete_open_scenario_sessions(profile_id, keep_scenario_id="free_talk")
    session = repo.get_or_create_session(
        plan_day_id=None,
        day_index=0,
        topic="自由对话",
        scenario_id="free_talk",
        profile_id=profile_id,
    )
    turns = repo.get_turns(session["id"])
    feedback_history = repo.get_inline_feedback_for_session(session["id"])
    brief = _free_talk_brief(profile)

    if not turns:
        turns = [
            repo.add_turn(
                session["id"],
                "assistant",
                "Hi! Let's have a free chat. Tell me about your day, or ask me anything you'd like to talk about.",
            )
        ]

    completion = build_completion_status(session, turns, feedback_history, brief, user_level=profile["current_level"] if profile else "A2")
    return {
        "session": session,
        "turns": turns,
        "plan_day": None,
        "feedback_history": feedback_history,
        "practice_brief": brief,
        "completion": completion,
    }



def complete_session(session_id: int, request: CompleteSessionRequest) -> dict[str, object]:
    repo = deps.get_repository()
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    turns = repo.get_turns(session_id)
    if not any(turn["speaker"] == "user" for turn in turns):
        raise HTTPException(status_code=400, detail="至少完成一轮练习后再结束今天的任务。")

    plan_day = repo.get_plan_day_by_id(session["plan_day_id"]) if session.get("plan_day_id") else None
    brief = load_brief(repo, plan_day["id"]) if plan_day else {}

    feedback = repo.get_inline_feedback_for_session(session_id)
    user_level = _user_level_for_session(repo, session)
    existing_completion = build_completion_status(session, turns, feedback, brief, user_level=user_level)
    if existing_completion["status"] == "completed":
        completed_plan_day = repo.get_plan_day_by_id(session["plan_day_id"]) if session.get("plan_day_id") else plan_day
        return {"session": session, "plan_day": completed_plan_day or {}, "completion": existing_completion}

    # 分数结算：依据本轮纠错（feedback）按 100 分制扣分
    summary = build_completion_summary(request.completion_type, turns, brief, feedback)
    early_farewell = is_early_farewell(turns)
    if early_farewell:
        # 前 3 轮内用户主动道别结束：本次不计入练习（计划不推进）、无得分、不生成复盘
        summary.pop("score", None)
        summary.pop("score_detail_zh", None)
        summary["summary_zh"] = "这次对话提前结束，本次不计入练习。"
    completed_session = repo.complete_session(session_id, summary, overall_score=4, mark_plan_completed=not early_farewell)
    if not completed_session:
        raise HTTPException(status_code=404, detail="Session not found")

    completed_plan_day = repo.get_plan_day_by_id(session["plan_day_id"]) if session.get("plan_day_id") else plan_day
    completion = build_completion_status(completed_session, turns, feedback, brief, user_level=user_level)
    if not early_farewell:
        _schedule_due_reviews()
    return {"session": completed_session, "plan_day": completed_plan_day or {}, "completion": completion}


def _schedule_due_reviews() -> None:
    """完成练习后异步生成当日复盘，让成长板块及时更新（失败静默，下次挂载/策略请求会补跑）。"""
    import threading

    def _run() -> None:
        try:
            from app.services import learning_loop
            learning_loop.run_due_reviews()
        except Exception:  # pragma: no cover - 后台补跑失败不影响主流程
            pass

    threading.Thread(target=_run, daemon=True).start()


def add_user_turn(request: UserTurnRequest) -> dict[str, object]:
    repo = deps.get_repository()

    # 1. Save user turn
    user_turn = repo.add_turn(request.session_id, "user", request.text)
    turns = repo.get_turns(request.session_id)

    # 2. Fetch context
    ctx = _load_session_context(repo, request.session_id)
    session = ctx["session"]
    objective = ctx["objective"]
    user_level = ctx["user_level"]
    learning_goal = ctx["learning_goal"]
    brief = ctx["brief"]

    # 3. Call LLM
    settings = deps.load_settings()
    llm = deps.create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )

    agent_response = ConversationAgent(llm, repo.get_prompt).reply(
        topic=session["topic"],
        objective=objective,
        user_level=user_level,
        learning_goal=learning_goal,
        conversation=turns,
        practice_brief=brief,
    )

    assistant_text = agent_response["reply"]
    hints = agent_response["hints"]

    assistant_turn = repo.add_turn(request.session_id, "assistant", assistant_text)

    # 4. Feedback
    feedback = InlineFeedbackAgent(llm, repo.get_prompt).generate(
        request.text,
        session["topic"],
        objective,
        turns,
        practice_brief=brief,
    )

    saved_feedback = repo.save_inline_feedback(request.session_id, user_turn["id"], feedback)
    completion = build_completion_status(
        repo.get_session(request.session_id) or session,
        repo.get_turns(request.session_id),
        repo.get_inline_feedback_for_session(request.session_id),
        brief or {},
        user_level=ctx["user_level"],
    )

    return {
        "user_turn": user_turn,
        "assistant_turn": assistant_turn,
        "inline_feedback": saved_feedback,
        "hints": hints,
        "completion": completion,
    }


def stream_user_turn(request: UserTurnRequest):
    """SSE 流式回合：边生成边推送，反馈并行计算。"""
    repo = deps.get_repository()

    # 1. Save user turn
    user_turn = repo.add_turn(request.session_id, "user", request.text)
    turns = repo.get_turns(request.session_id)

    # 2. Fetch context
    ctx = _load_session_context(repo, request.session_id)
    session = ctx["session"]
    objective = ctx["objective"]
    user_level = ctx["user_level"]
    learning_goal = ctx["learning_goal"]
    brief = ctx["brief"]

    settings = deps.load_settings()
    llm = deps.create_llm_provider(
        provider_name=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.chat_model,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # 3. Start Feedback Generation concurrently in the background
        future_feedback = executor.submit(
            InlineFeedbackAgent(llm, repo.get_prompt).generate,
            request.text,
            session["topic"],
            objective,
            turns,
            brief,
        )

        # 4. Stream LLM reply
        generator = ConversationAgent(llm, repo.get_prompt).reply_stream(
            topic=session["topic"],
            objective=objective,
            user_level=user_level,
            learning_goal=learning_goal,
            conversation=turns,
            practice_brief=brief,
        )

        full_reply = ""
        hints = []
        for item in generator:
            if isinstance(item, str):
                full_reply += item
                yield f"data: {json.dumps({'type': 'text', 'content': item})}\n\n"
            elif isinstance(item, list):
                hints = item

        # 5. Save assistant turn
        assistant_turn = repo.add_turn(request.session_id, "assistant", full_reply.strip())

        # 6. Wait for feedback to complete (it should be ready by now)
        try:
            # We give it a generous timeout, but usually it finishes before the text stream does
            feedback = future_feedback.result(timeout=10)
        except Exception as e:
            print(f"Concurrent feedback generation failed: {e}")
            feedback = []

        saved_feedback = repo.save_inline_feedback(request.session_id, user_turn["id"], feedback)
        completion = build_completion_status(
            repo.get_session(request.session_id) or session,
            repo.get_turns(request.session_id),
            repo.get_inline_feedback_for_session(request.session_id),
            brief or {},
            user_level=ctx["user_level"],
        )

        # 7. Yield final metadata
        meta = {
            "type": "meta",
            "hints": hints,
            "inline_feedback": saved_feedback,
            "user_turn": user_turn,
            "assistant_turn": assistant_turn,
            "completion": completion,
        }
        yield f"data: {json.dumps(meta)}\n\n"


def delete_turn_pair(session_id: int, user_turn_id: int) -> dict[str, object]:
    repo = deps.get_repository()
    if not repo.delete_turn_pair(session_id, user_turn_id):
        raise HTTPException(status_code=404, detail="Turn pair not found")
    return {
        "turns": repo.get_turns(session_id),
        "feedback_history": repo.get_inline_feedback_for_session(session_id),
    }

def clear_session_history(session_id: int) -> dict[str, object]:
    repo = deps.get_repository()
    if not repo.clear_session_history(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "cleared", "session_id": session_id}
