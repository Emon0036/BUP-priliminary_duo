from __future__ import annotations


def request_payload(**overrides):
    hours = [
        {
            "hour": hour,
            "demand_kwh": 10.0,
            "solar_kwh": 4.0 if 8 <= hour < 16 else 0.0,
            "tariff_bdt_per_kwh": 2.0 if hour < 12 else 8.0,
        }
        for hour in range(24)
    ]
    payload = {
        "scenario_id": "TEST-01",
        "operator_notes": ["No operational changes."],
        "hours": hours,
        "battery": {
            "capacity_kwh": 40.0,
            "initial_energy_kwh": 20.0,
            "minimum_energy_kwh": 0.0,
            "max_charge_kwh_per_hour": 10.0,
            "max_discharge_kwh_per_hour": 10.0,
        },
    }
    payload.update(overrides)
    return payload


def no_op_output(count=1):
    return [
        {
            "note_index": index,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "unrelated",
        }
        for index in range(count)
    ]
