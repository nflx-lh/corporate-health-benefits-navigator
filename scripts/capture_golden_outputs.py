"""One-time script to capture golden outputs from the current CSV-based API.

Run from repo root:
    python scripts/capture_golden_outputs.py
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

CASES = [
    {"label": "mri_covered", "input": {"employee_id": "EMP007", "question": "I need an MRI"}},
    {"label": "root_canal_covered", "input": {"employee_id": "EMP014", "question": "root canal treatment"}},
    {"label": "dental_cleaning_covered", "input": {"employee_id": "EMP001", "question": "dental cleaning"}},
    {"label": "orthodontics_exclusion", "input": {"employee_id": "EMP002", "question": "orthodontics braces"}},
    {"label": "inactive_employee", "input": {"employee_id": "EMP026", "question": "dental cleaning"}},
    {"label": "insufficient_info", "input": {"employee_id": "EMP025", "question": "dental cleaning"}},
    {"label": "ambiguous_query", "input": {"employee_id": "EMP001", "question": "something random"}},
]

OUTPUT_PATH = pathlib.Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "query_golden_outputs.json"


def main() -> None:
    results = []
    for case in CASES:
        resp = client.post("/v1/query", json=case["input"])
        assert resp.status_code == 200, f"Unexpected status {resp.status_code} for {case['label']}"
        body = resp.json()
        body["query_id"] = "QUERY_ID_STATIC"
        results.append({
            "label": case["label"],
            "input": case["input"],
            "expected": body,
        })
        print(f"  {case['label']}: decision={body['decision']}, matched_rule_ids={body.get('matched_rule_ids')}")

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nWrote {len(results)} golden outputs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
