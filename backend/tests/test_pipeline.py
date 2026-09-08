from sqlalchemy import create_engine

from app.agent.orchestrator import InsightBIOrchestrator
from app.core.config import Settings
from app.core.models import QueryMode, TaskStatus, UserContext
from app.db.bootstrap import bootstrap_database
from app.sql.executor import ReadOnlyExecutor


def build_orchestrator(tmp_path):
    url = f"sqlite:///{tmp_path / 'pipeline.db'}"
    test_engine = create_engine(url, connect_args={"check_same_thread": False})
    bootstrap_database(test_engine)
    service = InsightBIOrchestrator(Settings(app_env="test", database_url=url))
    service.executor = ReadOnlyExecutor(test_engine)
    return service


def test_simple_query(tmp_path):
    service = build_orchestrator(tmp_path)
    response = service.run("最近四个月毛利润趋势", UserContext(user_id="u", tenant_id="t"))
    assert response.status == TaskStatus.SUCCEEDED
    assert response.mode == QueryMode.SIMPLE
    assert response.evidence


def test_complex_analysis_has_multiple_evidence(tmp_path):
    service = build_orchestrator(tmp_path)
    response = service.run("最近三个月利润为什么下降", UserContext(user_id="u", tenant_id="t"))
    assert response.status == TaskStatus.SUCCEEDED
    assert response.mode == QueryMode.ANALYSIS
    assert len(response.evidence) == 3
    assert "毛利润" in response.answer

