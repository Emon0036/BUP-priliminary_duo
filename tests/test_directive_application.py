from app.directives import compile_constraints
from app.models import BatteryInput, HourInput, Interpretation


def make_hours():
    return [HourInput(hour=i, demand_kwh=1, solar_kwh=10, tariff_bdt_per_kwh=1) for i in range(24)]


def battery():
    return BatteryInput(capacity_kwh=20, initial_energy_kwh=10, minimum_energy_kwh=2, max_charge_kwh_per_hour=5, max_discharge_kwh_per_hour=5)


def item(kind, adjustment):
    return Interpretation(note_index=0, applies=True, directive_type=kind, structured_adjustment=adjustment, explanation="x")


def test_overlapping_directives_compile_conservatively():
    result = compile_constraints(
        make_hours(), battery(), [
            item("solar_reduction", {"hours": [3], "factor": 0.2}),
            item("minimum_battery_reserve", {"hours": [3], "minimum_energy_kwh": 8}),
            item("no_charge_window", {"hours": [3]}),
            item("no_discharge_window", {"hours": [3]}),
            item("max_grid_window", {"hours": [3], "max_grid_kwh": 4}),
        ],
    )
    assert result.effective_solar[3] == 2
    assert result.minimum_reserve[3] == 8
    assert not result.can_charge[3] and not result.can_discharge[3]
    assert result.max_grid[3] == 4
