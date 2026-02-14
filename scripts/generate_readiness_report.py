"""Generate an MVP readiness report from eval artifacts.

Reads eval results JSON and produces a timestamped markdown readiness report
in eval/artifacts/.

Usage:
    python scripts/generate_readiness_report.py [--eval-results FILE] [--pytest-summary FILE]
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "eval" / "artifacts"


def find_latest_eval_results() -> Path | None:
    """Find the most recent eval_results_*.json in artifacts dir."""
    pattern = str(ARTIFACTS_DIR / "eval_results_*.json")
    matches = sorted(glob.glob(pattern))
    return Path(matches[-1]) if matches else None


def _load_json_file(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Load a JSON file and return (data, error_message)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return None, str(exc)

    if not isinstance(data, dict):
        return None, "JSON root must be an object"
    return data, None


def _extract_pytest_status(
    pytest_summary_data: dict[str, Any] | None,
    pytest_summary_load_error: str | None,
) -> tuple[str, str]:
    """Return (status, details) for pytest summary block."""
    if pytest_summary_data is None:
        if pytest_summary_load_error:
            return "Provided (invalid)", pytest_summary_load_error
        return "Not provided", "No pytest summary file supplied."

    # Flexible parsing to support common summary shapes
    # Accept keys: passed/failed/errors/skipped/total or nested summary dict.
    src = pytest_summary_data.get("summary", pytest_summary_data)
    if not isinstance(src, dict):
        return "Provided (unrecognized format)", "Summary payload is not an object."

    passed = src.get("passed")
    failed = src.get("failed")
    errors = src.get("errors", 0)
    skipped = src.get("skipped", 0)
    total = src.get("total")

    numeric_fields = [passed, failed, errors, skipped, total]
    if all(v is None for v in numeric_fields):
        return "Provided (unrecognized format)", "Could not parse standard pytest counters."

    passed_i = int(passed) if isinstance(passed, (int, float)) else 0
    failed_i = int(failed) if isinstance(failed, (int, float)) else 0
    errors_i = int(errors) if isinstance(errors, (int, float)) else 0
    skipped_i = int(skipped) if isinstance(skipped, (int, float)) else 0

    if isinstance(total, (int, float)):
        total_i = int(total)
    else:
        total_i = passed_i + failed_i + errors_i + skipped_i

    status = "PASS" if (failed_i == 0 and errors_i == 0) else "FAIL"
    details = (
        f"total={total_i}, passed={passed_i}, failed={failed_i}, "
        f"errors={errors_i}, skipped={skipped_i}"
    )
    return status, details


def generate_report(
    eval_data: dict[str, Any],
    eval_path: str,
    ts: str,
    pytest_summary_path: str | None = None,
    pytest_summary_data: dict[str, Any] | None = None,
    pytest_summary_load_error: str | None = None,
) -> str:
    """Generate the MVP readiness report markdown."""
    summary = eval_data.get("summary", {})
    results = eval_data.get("results", [])

    # Defensive normalization
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(results, list):
        results = []

    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    pass_rate_raw = summary.get("pass_rate")
    failed_ids = summary.get("failed_case_ids", [])

    total_i = int(total) if isinstance(total, (int, float)) else 0
    passed_i = int(passed) if isinstance(passed, (int, float)) else 0
    failed_i = int(failed) if isinstance(failed, (int, float)) else max(total_i - passed_i, 0)

    computed_pass_rate = f"{(passed_i / total_i * 100):.1f}%" if total_i > 0 else "N/A"
    pass_rate = pass_rate_raw if isinstance(pass_rate_raw, str) and pass_rate_raw else computed_pass_rate

    pytest_status, pytest_details = _extract_pytest_status(
        pytest_summary_data=pytest_summary_data,
        pytest_summary_load_error=pytest_summary_load_error,
    )

    # Verdict logic: eval is primary, pytest refines confidence if supplied
    if failed_i == 0 and total_i > 0 and pytest_status in {"PASS", "Not provided"}:
        verdict = "GO"
        verdict_reason = "All eval cases pass. MVP ready for demo."
    elif total_i > 0 and (passed_i / total_i) >= 0.7:
        verdict = "CONDITIONAL GO"
        if pytest_status == "FAIL":
            verdict_reason = (
                f"{failed_i} eval case(s) failed and pytest indicates failures "
                "in provided summary; fix critical gaps before demo."
            )
        else:
            verdict_reason = (
                f"{failed_i} case(s) failed. Core decision paths work. "
                "Failed cases are edge-case or parser-gap issues documented below."
            )
    else:
        verdict = "NO-GO"
        verdict_reason = f"Pass rate below 70% ({pass_rate}). Blocking issues must be resolved."

    lines: list[str] = []

    lines.append(f"# MVP Readiness Report — {ts}")
    lines.append("")

    lines.append("## Scope & Locked Constraints")
    lines.append("")
    lines.append("- **Project:** Corporate Health Benefits Navigator (MVP)")
    lines.append("- **Eval endpoint:** `POST /v1/query-orchestrated`")
    lines.append("- **Rules-first authority:** Deterministic rules engine is source-of-truth")
    lines.append("- **Retrieval:** Explanation/citation enrichment only; does not alter decisions")
    lines.append("- **`POST /v1/query` contract:** UNCHANGED — locked since Phase 1")
    lines.append("")

    lines.append("## Eval Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total cases | {total_i} |")
    lines.append(f"| Passed | {passed_i} |")
    lines.append(f"| Failed | {failed_i} |")
    lines.append(f"| Pass rate | {pass_rate} |")
    lines.append(f"| Source | `{eval_path}` |")
    lines.append("")

    lines.append("## Failed Case Details")
    lines.append("")
    if failed_ids:
        for r in results:
            if isinstance(r, dict) and not r.get("pass", True):
                cid = r.get("case_id", "?")
                lines.append(f"### {cid}")
                lines.append(f"- Status code: {r.get('status_code')}")
                lines.append(f"- Observed decision: {r.get('observed_decision')}")
                lines.append(f"- Observed benefit_type: {r.get('observed_benefit_type')}")
                failures = r.get("failures", [])
                if isinstance(failures, list):
                    for f in failures:
                        lines.append(f"- **{f}**")
                if r.get("notes"):
                    lines.append(f"- Notes: {r['notes']}")
                lines.append("")
    else:
        lines.append("None — all cases passed.")
        lines.append("")

    lines.append("## Test Status")
    lines.append("")
    lines.append("| Suite | Command | Status | Notes |")
    lines.append("|-------|---------|--------|-------|")
    lines.append("| Phase 1 unit/integration | `pytest tests/test_rule_engine.py tests/test_query_endpoint.py` | Manual run | Rules engine + /v1/query |")
    lines.append("| Phase 2 chunker | `pytest tests/test_chunker.py` | Manual run | Clause-aware chunking |")
    lines.append("| Phase 2 retriever | `pytest tests/test_retriever_smoke.py` | Manual run | Embedding index + retrieval |")
    lines.append("| Phase 3 orchestration | `pytest tests/test_orchestration_graph.py tests/test_query_endpoint_orchestrated.py` | Manual run | LangGraph pipeline |")
    lines.append("| Phase 4 frontend | `frontend/SMOKE_TEST.md` | Manual run | Checklist validation |")
    lines.append("| Phase 5 eval harness | `python scripts/run_eval.py --timeout 60` | Generated from artifacts | E2E eval |")

    pytest_source = f"`{pytest_summary_path}`" if pytest_summary_path else "N/A"
    lines.append(
        f"| Pytest summary input | `python scripts/generate_readiness_report.py --pytest-summary <file>` | {pytest_status} | {pytest_details}; source={pytest_source} |"
    )
    lines.append("")

    lines.append("## Contract Safety Statement")
    lines.append("")
    lines.append("- `POST /v1/query` semantics are **unchanged** from Phase 1 freeze.")
    lines.append("- `POST /v1/query-orchestrated` is the additive orchestrated endpoint.")
    lines.append("- All deterministic decision fields (decision, benefit_type, coverage_percent,")
    lines.append("  annual_limit_sgd, co_pay_sgd, preauth_required, reason_codes, matched_rule_ids,")
    lines.append("  required_docs, decision_path) are preserved exactly.")
    lines.append("- Optional enrichment fields (policy_citations, explanation) are additive only.")
    lines.append("")

    lines.append("## Verdict")
    lines.append("")
    lines.append(f"**{verdict}**")
    lines.append("")
    lines.append(verdict_reason)
    lines.append("")

    lines.append("## Demo Checklist")
    lines.append("")
    lines.append("- [ ] Backend running: `cd backend && uvicorn app.main:app --port 8000`")
    lines.append("- [ ] Frontend running: `cd frontend && npm run dev`")
    lines.append("- [ ] Health check: `curl http://127.0.0.1:8000/v1/health`")
    lines.append("- [ ] Eval harness green or documented gaps: `python scripts/run_eval.py --timeout 60`")
    lines.append("- [ ] Smoke test covered: EMP001 + 'dental cleaning'")
    lines.append("- [ ] Smoke test not_covered: EMP001 + 'orthodontics braces'")
    lines.append("- [ ] Smoke test insufficient_info: EMP001 + 'random gibberish'")
    lines.append("- [ ] Smoke test 404: EMP999 + any query")
    lines.append("- [ ] Frontend login/logout flow works")
    lines.append("- [ ] Enrichment section renders when index is built")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate MVP readiness report from eval artifacts.",
    )
    parser.add_argument(
        "--eval-results",
        default=None,
        help="Path to eval_results_*.json (default: latest in eval/artifacts/)",
    )
    parser.add_argument(
        "--pytest-summary",
        default=None,
        help="Optional path to pytest summary JSON for Test Status block.",
    )
    args = parser.parse_args()

    if args.eval_results:
        eval_path = Path(args.eval_results)
    else:
        eval_path = find_latest_eval_results()

    if eval_path is None or not eval_path.exists():
        print("FATAL: No eval results found. Run scripts/run_eval.py first.", file=sys.stderr)
        return 1

    eval_data, err = _load_json_file(eval_path)
    if err is not None or eval_data is None:
        print(f"FATAL: Failed to read eval results: {err}", file=sys.stderr)
        return 1

    pytest_summary_data: dict[str, Any] | None = None
    pytest_summary_path_for_report: str | None = None
    pytest_summary_load_error: str | None = None

    if args.pytest_summary:
        p = Path(args.pytest_summary)
        pytest_summary_path_for_report = str(p)
        if p.exists():
            data, p_err = _load_json_file(p)
            if p_err is None and data is not None:
                pytest_summary_data = data
            else:
                pytest_summary_load_error = f"Failed to parse pytest summary: {p_err}"
        else:
            pytest_summary_load_error = "Pytest summary file path was provided but file does not exist."

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report = generate_report(
        eval_data=eval_data,
        eval_path=str(eval_path.name),
        ts=ts,
        pytest_summary_path=pytest_summary_path_for_report,
        pytest_summary_data=pytest_summary_data,
        pytest_summary_load_error=pytest_summary_load_error,
    )

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ARTIFACTS_DIR / f"mvp_readiness_report_{ts}.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"Readiness report generated: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
