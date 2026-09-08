from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import BoundedSemaphore, Lock
from uuid import uuid4

from app.agent.orchestrator import InsightBIOrchestrator
from app.core.models import AsyncTaskView, QueryResponse, TaskStatus, UserContext


@dataclass
class TaskRecord:
    status: TaskStatus
    trace_id: str
    result: QueryResponse | None = None
    error: str | None = None


class QueueFullError(Exception):
    pass


class AsyncTaskManager:
    """有界异步队列，队列满时明确拒绝，避免无限积压。"""

    def __init__(self, orchestrator: InsightBIOrchestrator, workers: int = 4, capacity: int = 100):
        self.orchestrator = orchestrator
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="analysis-task")
        self.capacity = BoundedSemaphore(capacity)
        self.records: dict[str, TaskRecord] = {}
        self.lock = Lock()

    def submit(self, question: str, user: UserContext) -> AsyncTaskView:
        if not self.capacity.acquire(blocking=False):
            raise QueueFullError("分析任务队列已满")
        task_id, trace_id = f"task_{uuid4().hex[:16]}", f"tr_{uuid4().hex}"
        with self.lock:
            self.records[task_id] = TaskRecord(TaskStatus.PENDING, trace_id)
        self.pool.submit(self._run, task_id, trace_id, question, user)
        return self.get(task_id)

    def _run(self, task_id: str, trace_id: str, question: str, user: UserContext) -> None:
        try:
            with self.lock:
                self.records[task_id].status = TaskStatus.RUNNING
            result = self.orchestrator.run(question, user, trace_id)
            with self.lock:
                self.records[task_id].status = result.status
                self.records[task_id].result = result
        except Exception as exc:  # noqa: BLE001 - worker boundary must persist all failures
            with self.lock:
                self.records[task_id].status = TaskStatus.FAILED
                self.records[task_id].error = str(exc)
        finally:
            self.capacity.release()

    def get(self, task_id: str) -> AsyncTaskView:
        record = self.records[task_id]
        return AsyncTaskView(task_id=task_id, status=record.status, trace_id=record.trace_id, result=record.result, error=record.error)
