from __future__ import annotations

import random

from app.directives import compile_constraints
from app.guardrails import validate_interpretations
from app.models import BatteryInput, HourPlan, HourInput
from app.optimizer import solve_lp
from app.validator import replay_validate


def test_one_hundred_randomized_feasible_scenarios_replay():
    rng = random.Random(20260918)
    no_op = validate_interpretations([{"note_index": 0, "applies": False, "directive_type": "no_op", "structured_adjustment": None, "explanation": "x"}], 1, 100)
    for _ in range(100):
        hours = [HourInput(hour=h, demand_kwh=rng.uniform(0.1, 30), solar_kwh=rng.uniform(0, 10), tariff_bdt_per_kwh=rng.uniform(0, 20)) for h in range(24)]
        battery = BatteryInput(capacity_kwh=100, initial_energy_kwh=50, minimum_energy_kwh=5, max_charge_kwh_per_hour=50, max_discharge_kwh_per_hour=50)
        constraints = compile_constraints(hours, battery, no_op)
        solved = solve_lp(hours, battery, constraints)
        plan = []
        for row in solved:
            if row.battery_change_kwh > 1e-8:
                action, amount = "charge", row.battery_change_kwh
            elif row.battery_change_kwh < -1e-8:
                action, amount = "discharge", -row.battery_change_kwh
            else:
                action, amount = "idle", 0
            plan.append(HourPlan(hour=row.hour, grid_kwh=round(row.grid_kwh, 8), solar_used_kwh=round(row.solar_used_kwh, 8), battery_action=action, battery_kwh=round(amount, 8), battery_energy_after_kwh=round(row.battery_energy_after_kwh, 8)))
        replay_validate(plan, hours, battery, constraints)
