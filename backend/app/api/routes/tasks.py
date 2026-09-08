from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import current_user
from app.core.models import AsyncTaskView, QueryRequest, UserContext
from app.services.tasks import QueueFullError

router = APIRouter(prefix="/api/v1/tasks", tags=["异步分析任务"])


@router.post("", response_model=AsyncTaskView, status_code=202)
def create_task(
    payload: QueryRequest,
    request: Request,
    user: Annotated[UserContext, Depends(current_user)],
):
    try:
        return request.app.state.task_manager.submit(payload.question, user)
    except QueueFullError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc), headers={"Retry-After": "5"}) from exc


@router.get("/{task_id}", response_model=AsyncTaskView)
def get_task(
    task_id: str,
    request: Request,
    _: Annotated[UserContext, Depends(current_user)],
):
    try:
        return request.app.state.task_manager.get(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc
