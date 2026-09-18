"""Print a valid request skeleton for local manual/provider testing."""
import json

hours = [{"hour": h, "demand_kwh": 10, "solar_kwh": 0, "tariff_bdt_per_kwh": 5} for h in range(24)]
print(json.dumps({"scenario_id": "LOCAL-01", "operator_notes": ["Keep the battery above 25% from 18:00 until 22:00."], "hours": hours, "battery": {"capacity_kwh": 100, "initial_energy_kwh": 50, "minimum_energy_kwh": 10, "max_charge_kwh_per_hour": 20, "max_discharge_kwh_per_hour": 20}}, indent=2))
