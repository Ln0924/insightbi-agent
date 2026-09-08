from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import current_user
from app.core.models import TraceEvent, UserContext
from app.observability.tracing import trace_store

router = APIRouter(prefix="/api/v1", tags=["可观测性"])


@router.get("/traces/{trace_id}", response_model=list[TraceEvent])
def get_trace(trace_id: str, _: Annotated[UserContext, Depends(current_user)]):
    events = trace_store.get(trace_id)
    if not events:
        raise HTTPException(status_code=404, detail="Trace 不存在")
    return events
