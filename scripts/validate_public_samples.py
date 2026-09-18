"""Validate the organizer's public sample file without embedding its cases.

Usage: python scripts/validate_public_samples.py path/to/public_samples.json
The endpoint defaults to http://127.0.0.1:8000/optimize-energy.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import httpx

# Running a script puts its own directory first on sys.path. Pin imports to
# this checkout so a user's unrelated installed ``app`` package cannot win.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.directives import compile_constraints
from app.guardrails import validate_interpretations
from app.models import OptimizeRequest, OptimizeResponse
from app.validator import recompute_totals, replay_validate


def _directive_semantics(entries: list[dict]) -> list[dict]:
    fields = ("note_index", "applies", "directive_type", "structured_adjustment")
    return [{field: entry.get(field) for field in fields} for entry in entries]


def _close(left: float, right: float, tolerance: float = 0.01) -> bool:
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance


def _validate_case(request: dict, expected: dict, actual: dict) -> tuple[bool, str]:
    request_model = OptimizeRequest.model_validate(request)
    response_model = OptimizeResponse.model_validate(actual)
    if response_model.scenario_id != request_model.scenario_id:
        return False, "scenario_id was not echoed"
    interpretations = validate_interpretations(
        [entry.model_dump() for entry in response_model.directive_interpretation],
        len(request_model.operator_notes),
        request_model.battery.capacity_kwh,
    )
    constraints = compile_constraints(request_model.hours, request_model.battery, interpretations)
    replay_validate(response_model.hourly_plan, request_model.hours, request_model.battery, constraints)
    totals = recompute_totals(response_model.hourly_plan, request_model.hours)
    actual_totals = (
        response_model.total_grid_kwh,
        response_model.total_cost_bdt,
        response_model.peak_grid_kwh,
    )
    if not all(_close(actual_value, recomputed) for actual_value, recomputed in zip(actual_totals, totals)):
        return False, "response totals do not match the replayed plan"

    expected_directives = expected.get("directive_interpretation")
    if not isinstance(expected_directives, list):
        return False, "expected output has no directive interpretation"
    actual_semantics = _directive_semantics([entry.model_dump() for entry in interpretations])
    if actual_semantics != _directive_semantics(expected_directives):
        return False, "directive semantics differed"
    expected_cost = expected.get("total_cost_bdt")
    if expected_cost is not None and not _close(response_model.total_cost_bdt, float(expected_cost)):
        return False, "cost differs from the public optimum beyond tolerance"
    return True, "schema, directives, replay, totals, and cost matched"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sample_file")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    with open(args.sample_file, encoding="utf-8") as handle:
        cases = json.load(handle)
    if isinstance(cases, dict) and isinstance(cases.get("cases"), list):
        cases = cases["cases"]
    if not isinstance(cases, list):
        raise SystemExit("public sample JSON must be an array or an object with a cases array")
    failures = 0
    with httpx.Client(timeout=30) as client:
        for index, case in enumerate(cases, 1):
            case_id = case.get("id", f"case-{index:02d}") if isinstance(case, dict) else f"case-{index:02d}"
            request = case.get("input", case.get("request", case))
            expected = case.get("expected_output", {})
            try:
                response = client.post(args.base_url.rstrip("/") + "/optimize-energy", json=request)
                if response.status_code != 200:
                    ok, detail = False, "HTTP " + str(response.status_code)
                elif not isinstance(expected, dict):
                    ok, detail = False, "case has no expected_output object"
                else:
                    ok, detail = _validate_case(request, expected, response.json())
            except Exception as exc:
                ok, detail = False, f"validation error: {type(exc).__name__}"
            print(f"{case_id}: {'PASS' if ok else 'FAIL'} - {detail}")
            failures += not ok
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
