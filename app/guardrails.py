from __future__ import annotations

import math
from typing import Any

from pydantic import ValidationError

from app.errors import GuardrailError
from app.models import Interpretation

ALLOWED = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise GuardrailError(f"{label} must be a finite number")
    return float(value)


def _hours(value: Any) -> list[int]:
    if not isinstance(value, list):
        raise GuardrailError("hours must be an array")
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise GuardrailError("hours must contain integers only")
    if any(item < 0 or item > 23 for item in value):
        raise GuardrailError("hours must be in the range 0..23")
    if value != sorted(value) or len(value) != len(set(value)):
        raise GuardrailError("hours must be unique and ascending")
    return value


def validate_interpretations(raw: Any, note_count: int, capacity_kwh: float) -> list[Interpretation]:
    if not isinstance(raw, list) or len(raw) != note_count:
        raise GuardrailError("one interpretation is required for every note")
    try:
        parsed = [Interpretation.model_validate(item) for item in raw]
    except ValidationError as exc:
        raise GuardrailError("model output did not match the interpretation schema") from exc
    if [item.note_index for item in parsed] != list(range(note_count)):
        raise GuardrailError("note indices must be complete and ordered")
    for item in parsed:
        adjustment = item.structured_adjustment
        if item.directive_type == "no_op":
            if item.applies is not False or adjustment is not None:
                raise GuardrailError("no_op must have applies=false and null adjustment")
            continue
        if item.applies is not True or adjustment is None:
            raise GuardrailError("active directives must have applies=true and an adjustment")
        if item.directive_type == "solar_reduction":
            if set(adjustment) != {"hours", "factor"}:
                raise GuardrailError("invalid solar reduction fields")
            _hours(adjustment["hours"])
            factor = _finite_number(adjustment["factor"], "solar factor")
            if not 0 <= factor <= 1:
                raise GuardrailError("solar factor must be between 0 and 1")
        elif item.directive_type == "minimum_battery_reserve":
            if set(adjustment) != {"hours", "minimum_energy_kwh"}:
                raise GuardrailError("invalid reserve fields")
            _hours(adjustment["hours"])
            reserve = _finite_number(adjustment["minimum_energy_kwh"], "minimum reserve")
            if reserve < 0 or reserve > capacity_kwh:
                raise GuardrailError("minimum reserve is outside battery capacity")
        elif item.directive_type in {"no_charge_window", "no_discharge_window"}:
            if set(adjustment) != {"hours"}:
                raise GuardrailError("invalid battery window fields")
            _hours(adjustment["hours"])
        elif item.directive_type == "max_grid_window":
            if set(adjustment) != {"hours", "max_grid_kwh"}:
                raise GuardrailError("invalid grid window fields")
            _hours(adjustment["hours"])
            cap = _finite_number(adjustment["max_grid_kwh"], "grid cap")
            if cap < 0:
                raise GuardrailError("grid cap must be non-negative")
        elif item.directive_type not in ALLOWED:
            raise GuardrailError("unsupported directive")
    return parsed
