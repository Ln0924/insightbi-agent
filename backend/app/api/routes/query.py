from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import current_user
from app.core.models import QueryRequest, QueryResponse, UserContext
from app.services.idempotency import idempotency_store
from app.services.security import make_idempotency_key

router = APIRouter(prefix="/api/v1", tags=["智能问数"])


def _sse(response: QueryResponse):
    for event, data in (
        ("status", {"status": "running", "trace_id": response.trace_id}),
        ("answer", {"answer": response.answer}),
        ("evidence", {"evidence": [e.model_dump(mode="json") for e in response.evidence]}),
        ("chart", {"charts": [c.model_dump(mode="json") for c in response.charts]}),
        ("done", response.model_dump(mode="json")),
    ):
        yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/query", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    request: Request,
    user: Annotated[UserContext, Depends(current_user)],
):
    allowed, retry_after = request.app.state.rate_limiter.allow(f"{user.tenant_id}:{user.user_id}")
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="请求过于频繁", headers={"Retry-After": str(retry_after)})
    key = payload.idempotency_key or make_idempotency_key(payload.question, user, payload.session_id)
    state = idempotency_store.begin(key)
    if state == "completed":
        return idempotency_store.get(key)
    if state == "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"message": "相同任务正在执行", "idempotency_key": key})
    try:
        response = request.app.state.orchestrator.run(payload.question, user)
        idempotency_store.complete(key, response)
    except Exception:
        idempotency_store.fail(key)
        raise
    if payload.stream:
        return StreamingResponse(_sse(response), media_type="text/event-stream")
    return response
