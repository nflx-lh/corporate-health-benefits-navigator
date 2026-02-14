"""Deterministic eval harness for POST /v1/query-orchestrated.

Executes eval cases against the orchestrated endpoint, produces
timestamped JSON + markdown artifacts with per-case PASS/FAIL.

Usage:
    python scripts/run_eval.py [--base-url URL] [--cases FILE] [--timeout SEC]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# ------------------------------------------------------------------ #
#  Constants                                                          #
# ------------------------------------------------------------------ #

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "eval" / "artifacts"

# Decision-critical keys that MUST be present in every 200 response.
REQUIRED_KEYS: set[str] = {
    "query_id",
    "employee_id",
    "decision",
    "benefit_type",
    "service_category",
    "reason_summary",
    "reason_codes",
    "matched_rule_ids",
    "required_docs",
    "preauth_required",
    "coverage_percent",
    "decision_path",
}

# Financial alias sets — at least one key from each set must be present.
FINANCIAL_ALIAS_SETS: list[tuple[str, ...]] = [
    ("annual_limit_sgd", "annual_limit"),
    ("co_pay_sgd", "estimated_payout"),
]

# Required fields in each eval case.
CASE_REQUIRED_FIELDS: set[str] = {
    "case_id",
    "employee_id",
    "question",
    "expected_decision",
    "expected_benefit_type",
}


# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #


def utc_ts() -> str:
    """Return deterministic UTC timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _schema_failures(details: list[str]) -> list[str]:
    """Return schema failures with required machine-checkable token first."""
    return ["INVALID_CASE_SCHEMA", *details]


def build_result_stub(
    case_id: str,
    failures: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Build a normalized per-case result record."""
    return {
        "case_id": case_id,
        "pass": False,
        "failures": failures or [],
        "status_code": None,
        "observed_decision": None,
        "observed_benefit_type": None,
        "observed_required_docs_count": None,
        "observed_citations_count": None,
        "notes": notes,
    }


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build deterministic summary from case results."""
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    failed = total - passed
    pass_rate = f"{(passed / total * 100):.1f}%" if total > 0 else "N/A"
    failed_case_ids = [r["case_id"] for r in results if not r["pass"]]

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "failed_case_ids": failed_case_ids,
    }


def write_artifacts(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    ts: str,
    fatal_error: str | None = None,
) -> tuple[Path, Path]:
    """Write JSON + markdown artifacts."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = ARTIFACTS_DIR / f"eval_results_{ts}.json"
    md_path = ARTIFACTS_DIR / f"eval_summary_{ts}.md"

    artifact: dict[str, Any] = {"summary": summary, "results": results}
    if fatal_error:
        artifact["fatal_error"] = fatal_error

    json_path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    md_path.write_text(
        generate_summary_md(results=results, summary=summary, ts=ts, fatal_error=fatal_error),
        encoding="utf-8",
    )

    return json_path, md_path


def write_fatal_run_artifacts(fatal_error: str) -> tuple[Path, Path]:
    """Write minimal artifacts for run-level fatal errors."""
    ts = utc_ts()
    results = [
        build_result_stub(
            case_id="__RUN_FATAL__",
            failures=["RUN_FATAL", fatal_error],
            notes="Harness terminated before normal case execution.",
        )
    ]
    summary = build_summary(results)
    # Force failed_case_ids token explicitly as requested.
    summary["failed_case_ids"] = ["__RUN_FATAL__"]
    return write_artifacts(summary=summary, results=results, ts=ts, fatal_error=fatal_error)


# ------------------------------------------------------------------ #
#  Case validation                                                    #
# ------------------------------------------------------------------ #


def validate_case(case: Any, index: int) -> tuple[dict[str, Any], list[str]]:
    """Validate and normalize an eval case dict.

    Returns (normalized_case, failures). If failures is non-empty the
    case is malformed but still has a usable case_id for reporting.
    """
    detail_failures: list[str] = []

    if not isinstance(case, dict):
        case_id = f"__index_{index}"
        return {"case_id": case_id}, _schema_failures(["case is not a dict"])

    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        case_id = f"__index_{index}"
        detail_failures.append("missing or invalid case_id")

    normalized: dict[str, Any] = {"case_id": case_id}

    # Fields that must be non-null strings.
    strict_non_null = {"employee_id", "question", "expected_decision"}

    for field in CASE_REQUIRED_FIELDS - {"case_id"}:
        if field not in case:
            detail_failures.append(f"missing required field '{field}'")
            continue

        val = case.get(field)
        if field in strict_non_null:
            if val is None or not isinstance(val, str) or not val.strip():
                detail_failures.append(f"missing/invalid required string field '{field}'")
                continue

        normalized[field] = val

    # Optional fields with defaults.
    expected_required_docs = case.get("expected_required_docs", [])
    if not isinstance(expected_required_docs, list):
        detail_failures.append("expected_required_docs must be a list")
        expected_required_docs = []
    normalized["expected_required_docs"] = expected_required_docs

    expected_min_citations = case.get("expected_min_citations", None)
    if expected_min_citations is not None and not isinstance(expected_min_citations, int):
        detail_failures.append("expected_min_citations must be int or null")
        expected_min_citations = None
    normalized["expected_min_citations"] = expected_min_citations

    normalized["notes"] = case.get("notes", "")

    if detail_failures:
        return normalized, _schema_failures(detail_failures)
    return normalized, []


# ------------------------------------------------------------------ #
#  Per-case evaluation                                                #
# ------------------------------------------------------------------ #


def check_required_keys(body: dict[str, Any]) -> list[str]:
    """Check that all decision-critical keys are present."""
    failures: list[str] = []

    missing = REQUIRED_KEYS - set(body.keys())
    if missing:
        failures.append(f"MISSING_REQUIRED_KEYS: {sorted(missing)}")

    for alias_set in FINANCIAL_ALIAS_SETS:
        if not any(k in body for k in alias_set):
            failures.append(f"MISSING_FINANCIAL_KEY: need one of {alias_set}")

    return failures


def evaluate_case(
    case: dict[str, Any],
    base_url: str,
    timeout: int,
) -> dict[str, Any]:
    """Execute and evaluate a single eval case."""
    case_id: str = case["case_id"]
    result = build_result_stub(case_id=case_id, notes=str(case.get("notes", "")))

    # Build request payload.
    employee_id = case.get("employee_id")
    question = case.get("question")
    if not employee_id or not question:
        result["failures"].append("MISSING_INPUT_FIELDS")
        return result

    url = f"{base_url.rstrip('/')}/v1/query-orchestrated"
    payload = {"employee_id": employee_id, "question": question}

    # Execute request.
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        result["failures"].append(f"REQUEST_ERROR: {exc}")
        return result

    result["status_code"] = resp.status_code

    # Parse response.
    try:
        body = resp.json()
    except (ValueError, TypeError):
        result["failures"].append("INVALID_RESPONSE_JSON")
        return result

    if not isinstance(body, dict):
        result["failures"].append("INVALID_RESPONSE_JSON")
        return result

    # Check a) HTTP 200.
    if resp.status_code != 200:
        result["failures"].append(f"HTTP_{resp.status_code}")
        return result

    # Populate observed fields.
    result["observed_decision"] = body.get("decision")
    result["observed_benefit_type"] = body.get("benefit_type")
    result["observed_required_docs_count"] = len(body.get("required_docs") or [])
    result["observed_citations_count"] = len(body.get("policy_citations") or [])

    # Check f) required keys.
    result["failures"].extend(check_required_keys(body))

    # Check b) decision.
    if body.get("decision") != case.get("expected_decision"):
        result["failures"].append(
            f"DECISION_MISMATCH: expected={case.get('expected_decision')}, "
            f"observed={body.get('decision')}"
        )

    # Check c) benefit_type.
    if body.get("benefit_type") != case.get("expected_benefit_type"):
        result["failures"].append(
            f"BENEFIT_TYPE_MISMATCH: expected={case.get('expected_benefit_type')}, "
            f"observed={body.get('benefit_type')}"
        )

    # Check d) required_docs subset.
    expected_docs = set(case.get("expected_required_docs", []))
    observed_docs = set(body.get("required_docs") or [])
    if expected_docs and not expected_docs.issubset(observed_docs):
        missing_docs = sorted(expected_docs - observed_docs)
        result["failures"].append(f"REQUIRED_DOCS_MISSING: {missing_docs}")

    # Check e) citation threshold (conditional).
    min_cit = case.get("expected_min_citations")
    if min_cit is not None:
        actual_cit = len(body.get("policy_citations") or [])
        if actual_cit < min_cit:
            result["failures"].append(
                f"CITATION_THRESHOLD: expected>={min_cit}, observed={actual_cit}"
            )

    result["pass"] = len(result["failures"]) == 0
    return result


# ------------------------------------------------------------------ #
#  Artifact generation                                                #
# ------------------------------------------------------------------ #


def generate_summary_md(
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    ts: str,
    fatal_error: str | None = None,
) -> str:
    """Generate the markdown summary report."""
    lines: list[str] = []
    lines.append(f"# Eval Summary — {ts}")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total | {summary['total']} |")
    lines.append(f"| Passed | {summary['passed']} |")
    lines.append(f"| Failed | {summary['failed']} |")
    lines.append(f"| Pass Rate | {summary['pass_rate']} |")
    lines.append("")

    if fatal_error:
        lines.append("## Run Fatal Error")
        lines.append("")
        lines.append(f"- **{fatal_error}**")
        lines.append("")

    if summary["failed_case_ids"]:
        lines.append("## Failed Cases")
        lines.append("")
        for r in results:
            if not r["pass"]:
                lines.append(f"### {r['case_id']}")
                lines.append(f"- Status code: {r['status_code']}")
                lines.append(f"- Observed decision: {r['observed_decision']}")
                lines.append(f"- Observed benefit_type: {r['observed_benefit_type']}")
                for f in r["failures"]:
                    lines.append(f"- **{f}**")
                if r.get("notes"):
                    lines.append(f"- Notes: {r['notes']}")
                lines.append("")
    else:
        lines.append("All cases passed.")
        lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------------ #
#  Main                                                               #
# ------------------------------------------------------------------ #


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run eval cases against POST /v1/query-orchestrated.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--cases",
        default="eval/eval_cases.json",
        help="Path to eval cases JSON (default: eval/eval_cases.json)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Per-request timeout in seconds (default: 20)",
    )
    args = parser.parse_args()

    # Load cases.
    cases_path = Path(args.cases)
    if not cases_path.exists():
        fatal_msg = f"FATAL_CASES_FILE_NOT_FOUND: {cases_path}"
        print(fatal_msg, file=sys.stderr)
        json_path, md_path = write_fatal_run_artifacts(fatal_msg)
        print(f"Artifacts:\n  {json_path}\n  {md_path}")
        return 1

    try:
        raw = json.loads(cases_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        fatal_msg = f"FATAL_CASES_PARSE_ERROR: {exc}"
        print(fatal_msg, file=sys.stderr)
        json_path, md_path = write_fatal_run_artifacts(fatal_msg)
        print(f"Artifacts:\n  {json_path}\n  {md_path}")
        return 1

    if not isinstance(raw, list):
        fatal_msg = "FATAL_CASES_SCHEMA_ERROR: cases file must contain a JSON array"
        print(fatal_msg, file=sys.stderr)
        json_path, md_path = write_fatal_run_artifacts(fatal_msg)
        print(f"Artifacts:\n  {json_path}\n  {md_path}")
        return 1

    # Validate and run.
    results: list[dict[str, Any]] = []
    for i, raw_case in enumerate(raw):
        case, schema_failures = validate_case(raw_case, i)
        if schema_failures:
            results.append(
                build_result_stub(
                    case_id=case["case_id"],
                    failures=schema_failures,
                    notes=str(case.get("notes", "")),
                )
            )
            continue

        results.append(evaluate_case(case, args.base_url, args.timeout))

    # Build summary.
    summary = build_summary(results)

    # Timestamp for artifacts.
    ts = utc_ts()

    # Write artifacts.
    json_path, md_path = write_artifacts(summary=summary, results=results, ts=ts)

    # Console output.
    print(f"Eval complete: {summary['passed']}/{summary['total']} passed ({summary['pass_rate']})")
    if summary["failed_case_ids"]:
        print(f"Failed: {summary['failed_case_ids']}")
    print("Artifacts:")
    print(f"  {json_path}")
    print(f"  {md_path}")

    # Strict exit code policy.
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
