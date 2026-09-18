import pytest

from app.directives import compile_constraints
from app.errors import ReplayValidationError
from app.guardrails import validate_interpretations
from app.models import BatteryInput, HourInput, HourPlan
from app.validator import recompute_totals, replay_validate


def test_replay_rejects_energy_mismatch():
    hours = [HourInput(hour=i, demand_kwh=1, solar_kwh=0, tariff_bdt_per_kwh=1) for i in range(24)]
    battery = BatteryInput(capacity_kwh=10, initial_energy_kwh=5, minimum_energy_kwh=0, max_charge_kwh_per_hour=2, max_discharge_kwh_per_hour=2)
    constraints = compile_constraints(hours, battery, validate_interpretations([{"note_index": 0, "applies": False, "directive_type": "no_op", "structured_adjustment": None, "explanation": "x"}], 1, 10))
    plan = [HourPlan(hour=i, grid_kwh=1, solar_used_kwh=0, battery_action="idle", battery_kwh=0, battery_energy_after_kwh=5) for i in range(24)]
    plan[4] = plan[4].model_copy(update={"grid_kwh": 0})
    with pytest.raises(ReplayValidationError):
        replay_validate(plan, hours, battery, constraints)


def _valid_idle_plan(hours):
    return [
        HourPlan(
            hour=i,
            grid_kwh=hours[i].demand_kwh,
            solar_used_kwh=0,
            battery_action="idle",
            battery_kwh=0,
            battery_energy_after_kwh=5,
        )
        for i in range(24)
    ]


def test_replay_rejects_solar_overuse_and_wrong_neutrality():
    hours = [HourInput(hour=i, demand_kwh=1, solar_kwh=0, tariff_bdt_per_kwh=1) for i in range(24)]
    hours[3] = HourInput(hour=3, demand_kwh=1, solar_kwh=0.5, tariff_bdt_per_kwh=1)
    battery = BatteryInput(capacity_kwh=10, initial_energy_kwh=5, minimum_energy_kwh=0, max_charge_kwh_per_hour=2, max_discharge_kwh_per_hour=2)
    constraints = compile_constraints(hours, battery, validate_interpretations([{"note_index": 0, "applies": False, "directive_type": "no_op", "structured_adjustment": None, "explanation": "x"}], 1, 10))
    plan = _valid_idle_plan(hours)
    plan[3] = plan[3].model_copy(update={"solar_used_kwh": 0.6, "grid_kwh": 0.4})
    with pytest.raises(ReplayValidationError):
        replay_validate(plan, hours, battery, constraints)

    plan = _valid_idle_plan(hours)
    plan[-1] = plan[-1].model_copy(update={"battery_energy_after_kwh": 4})
    with pytest.raises(ReplayValidationError):
        replay_validate(plan, hours, battery, constraints)


def test_recomputed_totals_use_the_finalized_rows():
    hours = [HourInput(hour=i, demand_kwh=2, solar_kwh=0, tariff_bdt_per_kwh=i) for i in range(24)]
    plan = _valid_idle_plan(hours)
    total_grid, total_cost, peak = recompute_totals(plan, hours)
    assert total_grid == 48
    assert total_cost == sum(2 * i for i in range(24))
    assert peak == 2
