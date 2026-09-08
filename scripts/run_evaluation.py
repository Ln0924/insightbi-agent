from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agent.orchestrator import InsightBIOrchestrator
from app.core.models import UserContext
from app.db.bootstrap import bootstrap_database
from app.db.session import engine


def main() -> int:
    bootstrap_database(engine)
    service = InsightBIOrchestrator()
    cases = [json.loads(line) for line in (ROOT / "evals/golden_queries.jsonl").read_text(encoding="utf-8").splitlines() if line and "question" in line]
    passed = 0
    details = []
    user = UserContext(user_id="evaluator", tenant_id="demo")
    for case in cases:
        result = service.run(case["question"], user)
        ok = result.mode.value == case["expected_mode"]
        if "required_columns" in case:
            actual = {column for ev in result.evidence for column in ev.columns}
            ok = ok and set(case["required_columns"]).issubset(actual)
        if "min_evidence" in case:
            ok = ok and len(result.evidence) >= case["min_evidence"]
        passed += int(ok)
        details.append({"id": case["id"], "passed": ok, "trace_id": result.trace_id})
    report = {"total": len(cases), "passed": passed, "pass_rate": passed / len(cases), "details": details}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())

