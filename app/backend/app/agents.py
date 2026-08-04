import re
import json
from typing import Iterator
from pydantic import ValidationError
from app.contracts import OrchestrationResult
from app.llm import LLMProvider
from app.prompts import DEFAULT_PROMPTS


class GoalAgent:
    def __init__(self, llm: LLMProvider, get_prompt_fn=None):
        self.llm = llm
        self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))

    def generate_plan(
        self,
        learning_goal: str,
        total_days: int,
        daily_minutes: int,
        current_level: str,
    ) -> list[dict[str, object]]:
        system_prompt = self.get_prompt("goal_agent_system")
        user_template = self.get_prompt("goal_agent_user_template")
        user_prompt = user_template.format(
            total_days=total_days, 
            current_level=current_level, 
            learning_goal=learning_goal, 
            daily_minutes=daily_minutes
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        
        # Clean potential markdown fences
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        
        try:
            import json
            generated_items = json.loads(cleaned_response)
        except json.JSONDecodeError:
            # Fallback for catastrophic failure
            generated_items = [{"topic": "General Practice", "scenario": "Practice English", "objective": "Speak fluently"}] * total_days

        plan: list[dict[str, object]] = []
        for index in range(total_days):
            item = generated_items[index] if index < len(generated_items) else generated_items[-1]
            plan.append(
                {
                    "day_index": index + 1,
                    "topic": item.get("topic", "Practice"),
                    "scenario": item.get("scenario", "Daily practice"),
                    "objective": item.get("objective", "Improve fluency"),
                    "status": "pending",
                    "skill_focus": item.get("skill_focus", "Functional speaking"),
                    "communicative_task": item.get(
                        "communicative_task",
                        item.get("objective", "Complete the speaking task"),
                    ),
                    "target_functions": item.get("target_functions", []),
                    "success_criteria": item.get("success_criteria", []),
                    "brief_seed": item.get(
                        "brief_seed",
                        item.get("scenario", "Generate a practical role-play lesson pack"),
                    ),
                }
            )
        return plan


def remove_configuration_summary(text: str) -> str:
    cleaned = re.sub(r"\s*Goal:\s*.*?\.?\s*Level:\s*.*?\.?\s*Time:\s*\d+\s*minutes\.?", "", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def clean_plan_day(day: dict[str, object]) -> dict[str, object]:
    cleaned = dict(day)
    scenario = cleaned.get("scenario")
    if isinstance(scenario, str):
        cleaned["scenario"] = remove_configuration_summary(scenario)
    return cleaned


def clean_plan(days: list[dict[str, object]]) -> list[dict[str, object]]:
    return [clean_plan_day(day) for day in days]


def first_balanced_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None


def normalize_json_object(parsed: object, fallback: dict[str, object]) -> dict[str, object]:
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        return parsed[0]
    return fallback


def parse_json_object(text: str, fallback: dict[str, object]) -> dict[str, object]:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE).strip()
    candidates = [cleaned]
    extracted = first_balanced_json_object(cleaned)
    if extracted and extracted not in candidates:
        candidates.append(extracted)
    for candidate in candidates:
        try:
            return normalize_json_object(json.loads(candidate), fallback)
        except json.JSONDecodeError:
            continue
    return fallback


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


def normalize_orchestration_payload(payload: dict[str, object]) -> dict[str, object]:
    normalized = dict(payload)
    actions = normalized.get("recommended_actions")
    if isinstance(actions, list):
        normalized["recommended_actions"] = [
            {
                "action": action,
                "rationale": f"Recommended action: {action}",
                "priority": "medium",
            }
            if isinstance(action, str)
            else action
            for action in actions
        ]
    return normalized



from typing import Iterator

from app.scenarios import tier_for_level


def _conversation_level_guidance(user_level: str) -> str:
    """按用户水平生成对话难度与长度的显式指令，让小白/中级/大神的对话明显区分。

    小白：简短高频词、一次一个问题、慢节奏；
    中级：复合句、自然追问、中等长度；
    大神：复杂句、习语、多轮追问，制造更长的深度对话。
    """
    tier = tier_for_level(user_level or "")
    if tier == "advanced":
        return (
            "5. 台词长度与难度（大神级 C1）：每轮输出 3-4 句地道英文台词，使用复杂句、条件句、"
            "习语与自然的口语表达；在回应后主动追问细节、提出假设或反例，模拟真实的高强度对话，"
            "每轮总长 15 词以上。"
        )
    if tier == "intermediate":
        return (
            "5. 台词长度与难度（中级 B1/B2）：每轮输出 2-3 句英文台词，使用常见复合句和连接词，"
            "在回应后自然追加一个细节问题，句长 8-15 词。"
        )
    return (
        "5. 台词长度与难度（小白 A1/A2）：每轮输出 1-2 句简短英文台词，只使用高频简单词汇，"
        "句长不超过 8 个词，一次只问一个问题，放慢节奏、多给用户开口时间。"
    )


def _conversation_offtopic_rule() -> str:
    """追加在 system prompt 最末尾的通用规则：必须接住用户场景外/闲聊内容。

    放在 level guidance 之后、所有规则的最后，优先级最高，
    即使数据库里覆盖了对话模板也能生效。
    """
    return (
        "\n9. 接住用户最新一句：用户最新一句话如果与当前场景无关或超出剧本"
        "（例如饿了、累了、抱怨、问别的问题、突然聊别的话题），NPC 必须先自然回应该内容——"
        "表达关心、接一句相关的话或回应对方的问题——然后再在合适时机引导回场景；"
        "绝对不允许无视用户刚说的话，继续机械推进场景脚本。"
    )


def _last_user_line(conversation: list[dict[str, str]]) -> str:
    """取对话历史中用户最新一句，让 NPC 明确知道要接住什么。"""
    for turn in reversed(conversation):
        if turn.get("speaker") == "user":
            return turn.get("text", "")
    return ""


def format_roleplay_history(conversation: list[dict[str, str]]) -> str:
    lines = []
    for turn in conversation:
        speaker = turn.get("speaker")
        text = turn.get("text", "")
        if speaker == "assistant" and text.startswith("Today we will practice:"):
            continue
        role = "Learner" if speaker == "user" else "NPC"
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


def format_practice_brief_context(practice_brief: dict[str, object] | None) -> str:
    if not practice_brief:
        return ""
    return json.dumps(
        {
            "npc_role": practice_brief.get("npc_role"),
            "conversation_objective": practice_brief.get("conversation_objective"),
            "task_steps": practice_brief.get("task_steps", []),
            "target_expressions": practice_brief.get("target_expressions", []),
            "avoid_patterns": practice_brief.get("avoid_patterns", []),
            "rubric": practice_brief.get("rubric", []),
        },
        ensure_ascii=False,
    )


class CoachOrchestratorAgent:
    def __init__(self, llm: LLMProvider, get_prompt_fn=None):
        self.llm = llm
        self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))

    def plan_today(
        self,
        profile: dict[str, object],
        plan_day: dict[str, object],
        latest_review: dict[str, object] | None,
        active_memory: list[dict[str, object]],
        active_adjustments: list[dict[str, object]],
        practice_brief: dict[str, object] | None,
        session_state: dict[str, object],
    ) -> dict[str, object]:
        system_prompt = self.get_prompt("orchestrator_agent_system")
        user_template = self.get_prompt("orchestrator_agent_user_template")
        user_prompt = user_template.format(
            profile=json.dumps(profile, ensure_ascii=False),
            plan_day=json.dumps(plan_day, ensure_ascii=False),
            latest_review=json.dumps(latest_review or {}, ensure_ascii=False),
            active_memory=json.dumps(active_memory, ensure_ascii=False),
            active_adjustments=json.dumps(active_adjustments, ensure_ascii=False),
            practice_brief=json.dumps(practice_brief or {}, ensure_ascii=False),
            session_state=json.dumps(session_state, ensure_ascii=False),
        )
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        parsed = normalize_orchestration_payload(parse_json_object(response, {}))
        try:
            validated = OrchestrationResult.model_validate(parsed)
            return {
                "output": validated.model_dump(),
                "validation_status": "passed",
                "error_message": None,
                "raw_output": response,
            }
        except ValidationError as exc:
            return {
                "output": default_orchestration_output(plan_day),
                "validation_status": "failed",
                "error_message": str(exc),
                "raw_output": response,
            }


class ConversationAgent:
    def __init__(self, llm: LLMProvider, get_prompt_fn=None):
        self.llm = llm
        self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))

    def reply_stream(
        self,
        topic: str,
        objective: str,
        user_level: str,
        learning_goal: str,
        conversation: list[dict[str, str]],
        practice_brief: dict[str, object] | None = None,
    ) -> Iterator[str | list[str]]:
        recent_turns = conversation[-20:] if len(conversation) > 20 else conversation
        user_prompt_turns = format_roleplay_history(recent_turns)
        practice_brief_context = format_practice_brief_context(practice_brief)
        
        system_template = self.get_prompt("conversation_agent_system")
        system_prompt = system_template.format(user_level=user_level, learning_goal=learning_goal)
        system_prompt = f"{system_prompt}\n{_conversation_level_guidance(user_level)}\n{_conversation_offtopic_rule()}"
        
        user_template = self.get_prompt("conversation_agent_user_template")
        user_prompt = user_template.format(
            topic=topic,
            objective=objective,
            practice_brief_context=practice_brief_context,
            user_prompt_turns=user_prompt_turns,
            last_user_line=_last_user_line(recent_turns),
        )
        if practice_brief_context and "{practice_brief_context}" not in user_template:
            user_prompt = (
                f"{user_prompt}\n"
                "--- 今日材料包（供 NPC 设计下一句时使用，不要逐字朗读）---\n"
                f"{practice_brief_context}\n"
            )
        
        stream = self.llm.stream_complete(system_prompt=system_prompt, user_prompt=user_prompt)
        
        buffer = ""
        in_reply = False
        full_json_str = ""
        is_json = None
        
        import re
        reply_pattern = re.compile(r'"reply"\s*:\s*"')
        match_found = False
        
        for chunk in stream:
            buffer += chunk
            full_json_str += chunk
            
            if is_json is None:
                stripped = buffer.strip()
                if len(stripped) > 0:
                    if stripped.startswith("{") or stripped.startswith("```"):
                        is_json = True
                    else:
                        is_json = False
            
            if is_json is False:
                yield chunk
                continue
                
            if not in_reply and not match_found:
                match = reply_pattern.search(buffer)
                if match:
                    match_found = True
                    in_reply = True
                    buffer = buffer[match.end():]
            
            if in_reply:
                i = 0
                while i < len(buffer):
                    if buffer[i] == '\\':
                        i += 2
                        continue
                    if buffer[i] == '"':
                        yield buffer[:i].replace('\\"', '"').replace('\\n', '\n')
                        buffer = buffer[i:]
                        in_reply = False
                        break
                    i += 1
                
                if in_reply and len(buffer) > 2:
                    yield buffer[:-2].replace('\\"', '"').replace('\\n', '\n')
                    buffer = buffer[-2:]
                    
        # Fallback if "reply" was never found in JSON
        if is_json and not match_found:
            try:
                import json
                cleaned = full_json_str.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        if k != "hints" and isinstance(v, str):
                            yield v
                            break
            except Exception:
                yield full_json_str
                        
        hints = []
        try:
            import json
            cleaned = full_json_str.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "hints" in parsed:
                hints = parsed["hints"]
        except Exception:
            pass
            
        yield hints

    def reply(
        self,
        topic: str,
        objective: str,
        user_level: str,
        learning_goal: str,
        conversation: list[dict[str, str]],
        practice_brief: dict[str, object] | None = None,
    ) -> dict[str, object]:
        recent_turns = conversation[-20:] if len(conversation) > 20 else conversation
        user_prompt_turns = format_roleplay_history(recent_turns)
        practice_brief_context = format_practice_brief_context(practice_brief)
        
        system_template = self.get_prompt("conversation_agent_system")
        system_prompt = system_template.format(user_level=user_level, learning_goal=learning_goal)
        system_prompt = f"{system_prompt}\n{_conversation_level_guidance(user_level)}\n{_conversation_offtopic_rule()}"
        
        user_template = self.get_prompt("conversation_agent_user_template")
        user_prompt = user_template.format(
            topic=topic,
            objective=objective,
            practice_brief_context=practice_brief_context,
            user_prompt_turns=user_prompt_turns,
            last_user_line=_last_user_line(recent_turns),
        )
        if practice_brief_context and "{practice_brief_context}" not in user_template:
            user_prompt = (
                f"{user_prompt}\n"
                "--- 今日材料包（供 NPC 设计下一句时使用，不要逐字朗读）---\n"
                f"{practice_brief_context}\n"
            )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        
        try:
            import json
            data = json.loads(cleaned_response)
            return {
                "reply": data.get("reply", "Let's continue."),
                "hints": data.get("hints", [])
            }
        except json.JSONDecodeError:
            return {
                "reply": cleaned_response,
                "hints": []
            }


class InlineFeedbackAgent:
    def __init__(self, llm: LLMProvider, get_prompt_fn=None):
        self.llm = llm
        self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))

    def generate(self, user_text: str, topic: str, objective: str, conversation: list[dict[str, str]], practice_brief: dict[str, object] | None = None) -> list[dict[str, str]]:
        recent_turns = conversation[-10:]
        history_str = "\n".join(f"{t['speaker']}: {t['text']}" for t in recent_turns)
        
        system_prompt = self.get_prompt("inline_feedback_system")
        
        target_expressions = practice_brief.get("target_expressions", []) if practice_brief else []
        target_expr_str = json.dumps(target_expressions, ensure_ascii=False) if target_expressions else "无"
        
        user_template = self.get_prompt("inline_feedback_user_template")
        user_prompt = user_template.format(
            topic=topic, 
            objective=objective, 
            target_expressions=target_expr_str,
            history_str=history_str, 
            user_text=user_text
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        
        try:
            feedback = json.loads(cleaned_response)
            if not isinstance(feedback, list):
                return []
            return feedback
        except json.JSONDecodeError:
            return []


class LanguageSupportAgent:
    def __init__(self, llm: LLMProvider, get_prompt_fn=None):
        self.llm = llm
        self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))

    def explain(self, mode: str, text: str, context: str = "") -> dict[str, str]:
        system_prompt = self.get_prompt("language_support_system")
        user_prompt = (
            f"mode: {mode}\n"
            f"text: {text}\n"
            f"context: {context}\n"
            "请输出 JSON："
        )
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        cleaned = response.replace("```json", "").replace("```", "").strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                parsed.setdefault("mode", mode)
                parsed.setdefault("text", text)
                return parsed
        except json.JSONDecodeError:
            pass
        if mode == "translate":
            return {"mode": mode, "text": text, "translation_zh": cleaned}
        return {"mode": mode, "text": text, "meaning_zh": cleaned}


class DailyReviewAgent:
    def __init__(self, llm_provider, get_prompt_fn=None):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))

    def generate_review(self, profile: dict, sessions: list, plan_context: dict) -> dict:
        system_prompt = self.get_prompt("daily_review_agent_system")
        user_template = self.get_prompt("daily_review_agent_user_template")
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

class MemoryAgent:
    def __init__(self, llm_provider, get_prompt_fn=None):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))

    def extract_memory(self, review: dict, active_memory: list) -> dict:
        system_prompt = self.get_prompt("memory_agent_system")
        user_template = self.get_prompt("memory_agent_user_template")
        import json
        user_prompt = user_template.format(
            review=json.dumps(review, ensure_ascii=False),
            active_memory=json.dumps(active_memory, ensure_ascii=False)
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        data = parse_json_object(response, {"upserts": []})
        upserts = data.get("upserts")
        return {"upserts": upserts if isinstance(upserts, list) else []}

class PlanAdaptationAgent:
    def __init__(self, llm_provider, get_prompt_fn=None):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))

    def propose_adjustments(self, review: dict, active_memory: list, upcoming_days: list) -> dict:
        system_prompt = self.get_prompt("plan_adaptation_agent_system")
        user_template = self.get_prompt("plan_adaptation_agent_user_template")
        import json
        user_prompt = user_template.format(
            review=json.dumps(review, ensure_ascii=False),
            active_memory=json.dumps(active_memory, ensure_ascii=False),
            upcoming_days=json.dumps(upcoming_days, ensure_ascii=False)
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        data = parse_json_object(response, {"adjustments": []})
        adjustments = data.get("adjustments")
        return {"adjustments": adjustments if isinstance(adjustments, list) else []}

class ScenarioDesignAgent:
    def __init__(self, llm_provider, get_prompt_fn=None):
        self.llm = llm_provider
        self.get_prompt = get_prompt_fn or (lambda name: DEFAULT_PROMPTS.get(name))

    def generate_brief(
        self,
        plan_day: dict,
        adjustments: list,
        memory: list,
        review: dict,
        training_decision: dict | None = None,
        memory_influence: list | None = None,
    ) -> dict:
        system_prompt = self.get_prompt("scenario_design_agent_system")
        user_template = self.get_prompt("scenario_design_agent_user_template")
        import json
        user_prompt = user_template.format(
            plan_day=json.dumps(plan_day, ensure_ascii=False),
            adjustments=json.dumps(adjustments, ensure_ascii=False),
            memory=json.dumps(memory, ensure_ascii=False),
            review=json.dumps(review, ensure_ascii=False),
            training_decision=json.dumps(training_decision or {}, ensure_ascii=False),
            memory_influence=json.dumps(memory_influence or [], ensure_ascii=False),
        )
        
        response = self.llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        defaults = {
            "title": plan_day.get("topic", "Practice"),
            "user_visible_goal": plan_day.get("objective", "Practice speaking"),
            "npc_role": "NPC",
            "scenario_setup": plan_day.get("scenario", "Setup"),
            "conversation_objective": plan_day.get("objective", "Objective"),
            "lesson_focus": plan_day.get("skill_focus", "Functional speaking"),
            "task_steps": [],
            "target_expressions": [],
            "sentence_frames": [],
            "model_dialogue": [],
            "common_mistakes": [],
            "rubric": plan_day.get("success_criteria", []),
            "avoid_patterns": [],
            "difficulty": "normal",
            "coach_notes": "",
            "stretch_goal": "",
        }

        parsed = parse_json_object(response, {})
        defaults.update(parsed)
        for key in ("task_steps", "target_expressions", "sentence_frames", "model_dialogue", "common_mistakes", "rubric", "avoid_patterns"):
            if not isinstance(defaults.get(key), list):
                defaults[key] = []
        return defaults
