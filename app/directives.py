from __future__ import annotations

from dataclasses import dataclass

from app.models import BatteryInput, HourInput, Interpretation


@dataclass(frozen=True)
class Constraints:
    effective_solar: list[float]
    minimum_reserve: list[float]
    can_charge: list[bool]
    can_discharge: list[bool]
    max_grid: list[float | None]


def compile_constraints(hours: list[HourInput], battery: BatteryInput, interpretations: list[Interpretation]) -> Constraints:
    ordered = sorted(hours, key=lambda item: item.hour)
    effective_solar = [item.solar_kwh for item in ordered]
    minimum_reserve = [battery.minimum_energy_kwh] * 24
    can_charge = [True] * 24
    can_discharge = [True] * 24
    max_grid: list[float | None] = [None] * 24
    for interpretation in interpretations:
        if not interpretation.applies or interpretation.structured_adjustment is None:
            continue
        adjustment = interpretation.structured_adjustment
        target_hours = adjustment["hours"]
        if interpretation.directive_type == "solar_reduction":
            factor = float(adjustment["factor"])
            for hour in target_hours:
                effective_solar[hour] = ordered[hour].solar_kwh * factor
        elif interpretation.directive_type == "minimum_battery_reserve":
            reserve = float(adjustment["minimum_energy_kwh"])
            for hour in target_hours:
                minimum_reserve[hour] = max(minimum_reserve[hour], reserve)
        elif interpretation.directive_type == "no_charge_window":
            for hour in target_hours:
                can_charge[hour] = False
        elif interpretation.directive_type == "no_discharge_window":
            for hour in target_hours:
                can_discharge[hour] = False
        elif interpretation.directive_type == "max_grid_window":
            cap = float(adjustment["max_grid_kwh"])
            for hour in target_hours:
                max_grid[hour] = cap if max_grid[hour] is None else min(max_grid[hour], cap)
    return Constraints(effective_solar, minimum_reserve, can_charge, can_discharge, max_grid)
