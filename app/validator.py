from __future__ import annotations

import math

from app.directives import Constraints
from app.errors import ReplayValidationError
from app.models import BatteryInput, HourInput, HourPlan


EPS = 1e-6


def replay_validate(plan: list[HourPlan], hours: list[HourInput], battery: BatteryInput, constraints: Constraints) -> None:
    if len(plan) != 24 or [row.hour for row in plan] != list(range(24)):
        raise ReplayValidationError("plan must contain hours 0 through 23 in order")
    ordered = sorted(hours, key=lambda item: item.hour)
    energy = battery.initial_energy_kwh
    for hour, row in enumerate(plan):
        values = [row.grid_kwh, row.solar_used_kwh, row.battery_kwh, row.battery_energy_after_kwh]
        if not all(math.isfinite(value) for value in values):
            raise ReplayValidationError("plan contains non-finite values")
        if row.grid_kwh < -EPS or row.solar_used_kwh < -EPS or row.battery_kwh < -EPS:
            raise ReplayValidationError("plan contains negative values")
        if row.solar_used_kwh > constraints.effective_solar[hour] + EPS:
            raise ReplayValidationError("solar use exceeds effective solar")
        if row.battery_action == "idle":
            if abs(row.battery_kwh) > EPS:
                raise ReplayValidationError("idle action must have zero battery energy")
            change = 0.0
        elif row.battery_action == "charge":
            if not constraints.can_charge[hour] or row.battery_kwh > battery.max_charge_kwh_per_hour + EPS:
                raise ReplayValidationError("charge constraint violated")
            change = row.battery_kwh
        elif row.battery_action == "discharge":
            if not constraints.can_discharge[hour] or row.battery_kwh > battery.max_discharge_kwh_per_hour + EPS:
                raise ReplayValidationError("discharge constraint violated")
            change = -row.battery_kwh
        else:
            raise ReplayValidationError("unknown battery action")
        cap = constraints.max_grid[hour]
        if cap is not None and row.grid_kwh > cap + EPS:
            raise ReplayValidationError("grid cap violated")
        expected_energy = energy + change
        if abs(row.battery_energy_after_kwh - expected_energy) > EPS:
            raise ReplayValidationError("battery state transition violated")
        if row.battery_energy_after_kwh < constraints.minimum_reserve[hour] - EPS:
            raise ReplayValidationError("battery reserve violated")
        if row.battery_energy_after_kwh > battery.capacity_kwh + EPS:
            raise ReplayValidationError("battery capacity violated")
        if abs(row.grid_kwh + row.solar_used_kwh + max(-change, 0.0) - (ordered[hour].demand_kwh + max(change, 0.0))) > EPS:
            raise ReplayValidationError("energy balance violated")
        energy = row.battery_energy_after_kwh
    if abs(energy - battery.initial_energy_kwh) > EPS:
        raise ReplayValidationError("end-of-day battery neutrality violated")


def recompute_totals(plan: list[HourPlan], hours: list[HourInput]) -> tuple[float, float, float]:
    """Recompute response totals from the finalized plan, never solver state."""
    if len(plan) != 24 or [row.hour for row in plan] != list(range(24)):
        raise ReplayValidationError("cannot total an incomplete plan")
    ordered = {item.hour: item for item in hours}
    try:
        total_grid = sum(row.grid_kwh for row in plan)
        total_cost = sum(row.grid_kwh * ordered[row.hour].tariff_bdt_per_kwh for row in plan)
        peak_grid = max(row.grid_kwh for row in plan)
    except (KeyError, TypeError, ValueError) as exc:
        raise ReplayValidationError("cannot recompute plan totals") from exc
    values = (float(total_grid), float(total_cost), float(peak_grid))
    if not all(math.isfinite(value) and value >= 0 for value in values):
        raise ReplayValidationError("plan totals are not finite and non-negative")
    return values
