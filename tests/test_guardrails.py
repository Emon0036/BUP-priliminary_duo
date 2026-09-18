import pytest

from app.errors import GuardrailError
from app.guardrails import validate_interpretations


def base(kind, adjustment, applies=True):
    return {
        "note_index": 0,
        "applies": applies,
        "directive_type": kind,
        "structured_adjustment": adjustment,
        "explanation": "test",
    }


def test_no_op_semantics_are_exact():
    result = validate_interpretations([base("no_op", None, False)], 1, 100)
    assert result[0].structured_adjustment is None
    with pytest.raises(GuardrailError):
        validate_interpretations([base("no_op", {}, True)], 1, 100)


def test_solar_factor_and_exact_fields():
    valid = base("solar_reduction", {"hours": [13, 14], "factor": 0.2})
    assert validate_interpretations([valid], 1, 100)[0].directive_type == "solar_reduction"
    with pytest.raises(GuardrailError):
        validate_interpretations([base("solar_reduction", {"hours": [14, 13], "factor": 0.2})], 1, 100)
    with pytest.raises(GuardrailError):
        validate_interpretations([base("solar_reduction", {"hours": [13], "factor": 1.2})], 1, 100)


def test_reserve_and_grid_bounds():
    with pytest.raises(GuardrailError):
        validate_interpretations([base("minimum_battery_reserve", {"hours": [1], "minimum_energy_kwh": 101})], 1, 100)
    with pytest.raises(GuardrailError):
        validate_interpretations([base("max_grid_window", {"hours": [1], "max_grid_kwh": -1})], 1, 100)


def test_indices_must_be_complete_and_ordered():
    entries = [base("no_op", None, False), base("no_op", None, False)]
    entries[1]["note_index"] = 2
    with pytest.raises(GuardrailError):
        validate_interpretations(entries, 2, 100)


@pytest.mark.parametrize(
    "adjustment",
    [
        {"hours": [1, 1], "factor": 0.5},
        {"hours": [2, 1], "factor": 0.5},
        {"hours": [24], "factor": 0.5},
        {"hours": [-1], "factor": 0.5},
        {"hours": [1], "factor": -0.1},
        {"hours": [1], "factor": 1.1},
    ],
)
def test_solar_guardrails_reject_bad_hours_and_factors(adjustment):
    with pytest.raises(GuardrailError):
        validate_interpretations([base("solar_reduction", adjustment)], 1, 100)


def test_guardrails_reject_unsupported_or_wrong_application_semantics():
    with pytest.raises(GuardrailError):
        validate_interpretations([base("not_a_directive", None)], 1, 100)
    with pytest.raises(GuardrailError):
        validate_interpretations([base("no_charge_window", {"hours": [1]}, applies=False)], 1, 100)
    with pytest.raises(GuardrailError):
        validate_interpretations([base("no_op", None, applies=True)], 1, 100)


def test_guardrails_reject_wrong_adjustment_shapes_and_numeric_types():
    with pytest.raises(GuardrailError):
        validate_interpretations([base("no_charge_window", {"hours": [1], "extra": 2})], 1, 100)
    with pytest.raises(GuardrailError):
        validate_interpretations([base("max_grid_window", {"hours": [1], "max_grid_kwh": True})], 1, 100)
