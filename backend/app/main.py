import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis import Redis
from redis.exceptions import RedisError

from app.agent.orchestrator import InsightBIOrchestrator
from app.api.routes.query import router as query_router
from app.api.routes.tasks import router as task_router
from app.api.routes.traces import router as trace_router
from app.core.config import get_settings
from app.core.errors import ClarificationRequired, InsightBIError, PermissionDenied, UnsafeSqlError
from app.db.bootstrap import bootstrap_database
from app.db.session import engine
from app.services.security import RedisSlidingWindowRateLimiter, SlidingWindowRateLimiter
from app.services.tasks import AsyncTaskManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    bootstrap_database(engine)
    app.state.orchestrator = InsightBIOrchestrator(settings)
    try:
        redis_client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
            decode_responses=True,
        )
        redis_client.ping()
        app.state.rate_limiter = RedisSlidingWindowRateLimiter(
            redis_client, settings.rate_limit_per_minute
        )
    except RedisError:
        logging.getLogger(__name__).warning(
            "Redis unavailable; rate limiting falls back to a single-instance window"
        )
        app.state.rate_limiter = SlidingWindowRateLimiter(settings.rate_limit_per_minute)
    app.state.task_manager = AsyncTaskManager(app.state.orchestrator)
    yield


app = FastAPI(title="InsightBI Agent API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.include_router(query_router)
app.include_router(trace_router)
app.include_router(task_router)


@app.exception_handler(InsightBIError)
async def business_error(_: Request, exc: InsightBIError):
    status_code = 400
    if isinstance(exc, PermissionDenied):
        status_code = 403
    elif isinstance(exc, ClarificationRequired):
        status_code = 422
    elif isinstance(exc, UnsafeSqlError):
        status_code = 400
    return JSONResponse(status_code=status_code, content={"code": exc.code, "message": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok", "service": "insightbi-agent"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
