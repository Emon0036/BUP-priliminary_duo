from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _finite(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("must be finite")
    return value


def _strict_number(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("must be a JSON number")
    return value


def _strict_string(value: object) -> object:
    if not isinstance(value, str):
        raise ValueError("must be a string")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False, allow_inf_nan=False)


class HourInput(StrictModel):
    hour: int
    demand_kwh: float
    solar_kwh: float
    tariff_bdt_per_kwh: float

    @field_validator("hour", mode="before")
    @classmethod
    def strict_hour_input(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("hour must be an integer")
        return value

    @field_validator("demand_kwh", "solar_kwh", "tariff_bdt_per_kwh", mode="before")
    @classmethod
    def strict_numeric_input(cls, value: object) -> object:
        return _strict_number(value)

    @field_validator("hour")
    @classmethod
    def valid_hour_type(cls, value: int) -> int:
        if isinstance(value, bool):
            raise ValueError("hour must be an integer")
        return value

    @field_validator("demand_kwh", "solar_kwh", "tariff_bdt_per_kwh")
    @classmethod
    def valid_nonnegative_number(cls, value: float) -> float:
        _finite(value)
        if value < 0:
            raise ValueError("must be non-negative")
        return value


class BatteryInput(StrictModel):
    capacity_kwh: float
    initial_energy_kwh: float
    minimum_energy_kwh: float
    max_charge_kwh_per_hour: float
    max_discharge_kwh_per_hour: float

    @field_validator(
        "capacity_kwh",
        "initial_energy_kwh",
        "minimum_energy_kwh",
        "max_charge_kwh_per_hour",
        "max_discharge_kwh_per_hour",
        mode="before",
    )
    @classmethod
    def strict_numeric_input(cls, value: object) -> object:
        return _strict_number(value)

    @field_validator(
        "capacity_kwh",
        "initial_energy_kwh",
        "minimum_energy_kwh",
        "max_charge_kwh_per_hour",
        "max_discharge_kwh_per_hour",
    )
    @classmethod
    def valid_nonnegative_number(cls, value: float) -> float:
        _finite(value)
        if value < 0:
            raise ValueError("must be non-negative")
        return value

    @model_validator(mode="after")
    def valid_configuration(self) -> "BatteryInput":
        if self.minimum_energy_kwh > self.capacity_kwh:
            raise ValueError("minimum energy cannot exceed capacity")
        if not self.minimum_energy_kwh <= self.initial_energy_kwh <= self.capacity_kwh:
            raise ValueError("initial energy must be within battery bounds")
        return self


class OptimizeRequest(StrictModel):
    scenario_id: str
    operator_notes: list[str]
    hours: list[HourInput]
    battery: BatteryInput

    @field_validator("scenario_id", mode="before")
    @classmethod
    def valid_scenario_id_type(cls, value: object) -> object:
        return _strict_string(value)

    @field_validator("scenario_id")
    @classmethod
    def valid_scenario_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scenario_id must be non-empty")
        return value

    @field_validator("operator_notes", mode="before")
    @classmethod
    def valid_notes_type(cls, value: object) -> object:
        if not isinstance(value, list):
            raise ValueError("operator_notes must be an array")
        if any(not isinstance(note, str) for note in value):
            raise ValueError("operator notes must be strings")
        return value

    @field_validator("operator_notes")
    @classmethod
    def valid_notes(cls, value: list[str]) -> list[str]:
        if not 1 <= len(value) <= 3:
            raise ValueError("operator_notes must contain 1 to 3 notes")
        if any(not isinstance(note, str) or not note.strip() for note in value):
            raise ValueError("operator notes must be non-empty strings")
        return value

    @model_validator(mode="after")
    def valid_day(self) -> "OptimizeRequest":
        if len(self.hours) != 24:
            raise ValueError("exactly 24 hourly records are required")
        hour_values = [item.hour for item in self.hours]
        if sorted(hour_values) != list(range(24)):
            raise ValueError("hours must contain each integer from 0 through 23 exactly once")
        return self

    @field_validator("hours", mode="before")
    @classmethod
    def valid_hours_type(cls, value: object) -> object:
        if not isinstance(value, list):
            raise ValueError("hours must be an array")
        return value


DirectiveType = Literal[
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
]


class Interpretation(StrictModel):
    note_index: int
    applies: bool
    directive_type: DirectiveType
    structured_adjustment: dict[str, Any] | None
    explanation: str

    @field_validator("note_index", mode="before")
    @classmethod
    def strict_note_index(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("note_index must be an integer")
        return value

    @field_validator("applies", mode="before")
    @classmethod
    def strict_applies(cls, value: object) -> object:
        if not isinstance(value, bool):
            raise ValueError("applies must be a boolean")
        return value

    @field_validator("directive_type", mode="before")
    @classmethod
    def strict_directive_type(cls, value: object) -> object:
        return _strict_string(value)

    @field_validator("structured_adjustment", mode="before")
    @classmethod
    def strict_adjustment(cls, value: object) -> object:
        if value is not None and not isinstance(value, dict):
            raise ValueError("structured_adjustment must be an object or null")
        return value

    @field_validator("explanation", mode="before")
    @classmethod
    def strict_explanation(cls, value: object) -> object:
        return _strict_string(value)


class HourPlan(StrictModel):
    hour: int
    grid_kwh: float
    solar_used_kwh: float
    battery_action: Literal["charge", "discharge", "idle"]
    battery_kwh: float
    battery_energy_after_kwh: float


class OptimizeResponse(StrictModel):
    scenario_id: str
    directive_interpretation: list[Interpretation]
    hourly_plan: list[HourPlan]
    total_grid_kwh: float
    total_cost_bdt: float
    peak_grid_kwh: float
    plan_summary: str
