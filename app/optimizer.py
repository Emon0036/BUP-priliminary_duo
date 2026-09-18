from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog

from app.directives import Constraints
from app.errors import OptimizationError
from app.models import BatteryInput, HourInput


@dataclass(frozen=True)
class SolvedHour:
    hour: int
    grid_kwh: float
    solar_used_kwh: float
    battery_change_kwh: float
    battery_energy_after_kwh: float


def solve_lp(hours: list[HourInput], battery: BatteryInput, constraints: Constraints) -> list[SolvedHour]:
    ordered = sorted(hours, key=lambda item: item.hour)
    n = 24
    # Variable blocks: grid [0,n), solar [n,2n), signed battery change [2n,3n), SOC [3n,4n).
    def idx(block: int, hour: int) -> int:
        return block * n + hour

    c = np.zeros(4 * n)
    for hour in range(n):
        c[idx(0, hour)] = ordered[hour].tariff_bdt_per_kwh
    bounds: list[tuple[float, float | None]] = []
    for hour in range(n):
        bounds.append((0.0, constraints.max_grid[hour]))
    for hour in range(n):
        bounds.append((0.0, constraints.effective_solar[hour]))
    for hour in range(n):
        lower = -battery.max_discharge_kwh_per_hour if constraints.can_discharge[hour] else 0.0
        upper = battery.max_charge_kwh_per_hour if constraints.can_charge[hour] else 0.0
        bounds.append((lower, upper))
    for hour in range(n):
        bounds.append((constraints.minimum_reserve[hour], battery.capacity_kwh))

    a_eq: list[list[float]] = []
    b_eq: list[float] = []
    for hour in range(n):
        row = np.zeros(4 * n)
        row[idx(0, hour)] = 1
        row[idx(1, hour)] = 1
        row[idx(2, hour)] = -1
        a_eq.append(row.tolist())
        b_eq.append(ordered[hour].demand_kwh)
        state = np.zeros(4 * n)
        state[idx(3, hour)] = 1
        state[idx(2, hour)] = -1
        if hour == 0:
            rhs = battery.initial_energy_kwh
        else:
            state[idx(3, hour - 1)] = -1
            rhs = 0.0
        a_eq.append(state.tolist())
        b_eq.append(rhs)
    end = np.zeros(4 * n)
    end[idx(3, 23)] = 1
    a_eq.append(end.tolist())
    b_eq.append(battery.initial_energy_kwh)
    try:
        result = linprog(c, A_eq=np.array(a_eq), b_eq=np.array(b_eq), bounds=bounds, method="highs")
    except Exception as exc:
        raise OptimizationError("optimizer failed") from exc
    if not result.success or result.x is None:
        raise OptimizationError("scenario is infeasible")
    values = result.x
    solved: list[SolvedHour] = []
    for hour in range(n):
        row = SolvedHour(
            hour=hour,
            grid_kwh=float(values[idx(0, hour)]),
            solar_used_kwh=float(values[idx(1, hour)]),
            battery_change_kwh=float(values[idx(2, hour)]),
            battery_energy_after_kwh=float(values[idx(3, hour)]),
        )
        if not all(math.isfinite(value) for value in row.__dict__.values()):
            raise OptimizationError("optimizer returned non-finite values")
        solved.append(row)
    return solved
