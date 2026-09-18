from app.directives import compile_constraints
from app.models import BatteryInput, HourInput
from app.optimizer import solve_lp
from app.validator import replay_validate
from tests.helpers import no_op_output
from app.guardrails import validate_interpretations


def test_lp_is_feasible_and_neutral():
    hours = [HourInput(hour=i, demand_kwh=10, solar_kwh=0, tariff_bdt_per_kwh=1 + i) for i in range(24)]
    battery = BatteryInput(capacity_kwh=100, initial_energy_kwh=50, minimum_energy_kwh=0, max_charge_kwh_per_hour=20, max_discharge_kwh_per_hour=20)
    interpretations = validate_interpretations(no_op_output(), 1, 100)
    constraints = compile_constraints(hours, battery, interpretations)
    solved = solve_lp(hours, battery, constraints)
    assert len(solved) == 24
    assert abs(solved[-1].battery_energy_after_kwh - battery.initial_energy_kwh) < 1e-7
    assert any(row.battery_change_kwh < -1e-7 for row in solved)
    from app.models import HourPlan
    plan = [HourPlan(hour=row.hour, grid_kwh=round(row.grid_kwh, 8), solar_used_kwh=round(row.solar_used_kwh, 8), battery_action="charge" if row.battery_change_kwh > 1e-8 else "discharge" if row.battery_change_kwh < -1e-8 else "idle", battery_kwh=round(abs(row.battery_change_kwh), 8), battery_energy_after_kwh=round(row.battery_energy_after_kwh, 8)) for row in solved]
    replay_validate(plan, hours, battery, constraints)


def test_no_charge_and_no_discharge_bind():
    hours = [HourInput(hour=i, demand_kwh=5, solar_kwh=5 if i == 0 else 0, tariff_bdt_per_kwh=1) for i in range(24)]
    battery = BatteryInput(capacity_kwh=20, initial_energy_kwh=10, minimum_energy_kwh=0, max_charge_kwh_per_hour=10, max_discharge_kwh_per_hour=10)
    entries = [
        {"note_index": 0, "applies": True, "directive_type": "no_charge_window", "structured_adjustment": {"hours": [0]}, "explanation": "x"},
        {"note_index": 1, "applies": True, "directive_type": "no_discharge_window", "structured_adjustment": {"hours": [23]}, "explanation": "x"},
    ]
    directives = validate_interpretations(entries, 2, 20)
    constraints = compile_constraints(hours, battery, directives)
    solved = solve_lp(hours, battery, constraints)
    assert solved[0].battery_change_kwh <= 1e-7
    assert solved[23].battery_change_kwh >= -1e-7
