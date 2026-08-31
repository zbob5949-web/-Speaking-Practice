"""会话路由。"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app import dependencies as deps
from app.models import CompleteSessionRequest, StartSessionRequest, UserTurnRequest
from app.services import sessions as sessions_service

router = APIRouter()


@router.post("/api/sessions/start")
def start_session(request: StartSessionRequest) -> dict[str, object]:
    return sessions_service.start_session(request)


@router.post("/api/sessions/{session_id}/complete")
def complete_session(session_id: int, request: CompleteSessionRequest) -> dict[str, object]:
    return sessions_service.complete_session(session_id, request)


@router.post("/api/sessions/turn")
def add_user_turn(request: UserTurnRequest) -> dict[str, object]:
    return sessions_service.add_user_turn(request)


@router.post("/api/sessions/turn/stream")
def add_user_turn_stream(request: UserTurnRequest) -> StreamingResponse:
    # 路由层先校验会话存在：会话被删除/失效时直接返回 404，
    # 避免在 SSE 生成器内部抛异常导致响应头已发出、流中断成空流
    repo = deps.get_repository()
    if repo.get_session(request.session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return StreamingResponse(
        sessions_service.stream_user_turn(request),
        media_type="text/event-stream",
    )


@router.delete("/api/sessions/{session_id}/turn-pairs/{user_turn_id}")
def delete_turn_pair(session_id: int, user_turn_id: int) -> dict[str, object]:
    return sessions_service.delete_turn_pair(session_id, user_turn_id)


@router.get("/api/sessions")
def list_sessions(profile_id: int | None = None, limit: int = 60) -> dict[str, object]:
    """历史对话场景列表：包含 topic、场景、开始/结束时间、完成状态、回合数与本次得分/难度。"""
    repo = deps.get_repository()
    sessions = sessions_service.enrich_sessions(repo, repo.get_sessions(profile_id=profile_id, limit=limit))
    return {"sessions": sessions}


@router.delete("/api/sessions/{session_id}/history")
def clear_session_history(session_id: int) -> dict[str, object]:
    return sessions_service.clear_session_history(session_id)
