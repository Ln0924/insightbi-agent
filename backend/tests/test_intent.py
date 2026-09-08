from app.core.models import QueryMode
from app.services.intent import IntentClassifier


def test_routes_complex_attribution():
    result = IntentClassifier().classify("最近三个月利润为什么下降")
    assert result.mode == QueryMode.ANALYSIS
    assert "利润" in result.metrics


def test_routes_simple_query():
    result = IntentClassifier().classify("最近三个月的收入是多少")
    assert result.mode == QueryMode.SIMPLE

