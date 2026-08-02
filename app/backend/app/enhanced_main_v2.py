"""Mobile-ready backend entry point for the rule-first learning loop."""

from typing import Optional

from fastapi import HTTPException

from app import dependencies as deps
from app.error_aggregation import aggregate_errors
from app.grammar_rag import GRAMMAR_KNOWLEDGE
from app.grammar_rules import RULES
from app.grammar_service import GrammarAnalysisService
from app.enhanced_models import GrammarCheckRequest
from app.main import app
from app.models import UserTurnRequest
from app.scenarios import get_scenario, list_scenarios
from app.services.enhanced_turn import _get_round_reports, _learning_signals, enhanced_user_turn


def _remove_post_route(path: str) -> None:
    app.router.routes[:] = [route for route in app.router.routes if not (getattr(route, "path", None) == path and "POST" in (getattr(route, "methods", set()) or set()))]


_remove_post_route("/api/sessions/turn")


@app.get("/api/scenarios")
def get_scenarios(level: Optional[str] = None) -> dict[str, object]:
    return {"scenarios": list_scenarios(level)}


@app.get("/api/scenarios/{scenario_id}")
def get_scenario_detail(scenario_id: str, level: Optional[str] = None) -> dict[str, object]:
    scenario = get_scenario(scenario_id, level)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"scenario": scenario}


@app.get("/api/grammar/rules")
def get_grammar_rules() -> dict[str, object]:
    return {"rules": [{"rule_id": r.rule_id, "error_type": r.error_type, "title": r.title, "explanation_zh": r.explanation_zh, "source_key": r.source_key} for r in RULES], "knowledge_documents": len(GRAMMAR_KNOWLEDGE)}


@app.post("/api/grammar/check")
def check_grammar(request: GrammarCheckRequest) -> dict[str, object]:
    settings = deps.load_settings()
    llm = deps.create_llm_provider(provider_name=settings.llm_provider, api_key=settings.llm_api_key, base_url=settings.llm_base_url, model=settings.chat_model)
    feedback = GrammarAnalysisService().analyze(request.text, request.level, llm, request.context)
    return {"feedback": feedback, "report": aggregate_errors(feedback), "pipeline": ["rule_match", "rag_retrieve", "llm_deep_analysis"]}


@app.post("/api/sessions/turn")
def add_user_turn_enhanced(request: UserTurnRequest) -> dict[str, object]:
    repo = deps.get_repository()
    return enhanced_user_turn(repo, request.session_id, request.text)


@app.get("/api/sessions/{session_id}/learning-report")
def get_learning_report(session_id: int) -> dict[str, object]:
    repo = deps.get_repository()
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    feedback = repo.get_inline_feedback_for_session(session_id)
    return {
        "session_id": session_id,
        "round_reports": _get_round_reports(deps.load_settings().database_path, session_id),
        "session_error_report": aggregate_errors(feedback),
        "learning_signals": _learning_signals(repo, repo.get_latest_profile(), session_id, feedback),
    }
