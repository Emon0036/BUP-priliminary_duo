from __future__ import annotations

from app.models import Interpretation


def make_summary(interpretations: list[Interpretation], *, used_solar: bool, battery_moved: bool) -> str:
    active = [item.directive_type for item in interpretations if item.applies]
    if not active:
        lead = "Applied no operational directives"
    else:
        labels = {
            "solar_reduction": "solar reductions",
            "minimum_battery_reserve": "battery reserve constraints",
            "no_charge_window": "charge restrictions",
            "no_discharge_window": "discharge restrictions",
            "max_grid_window": "grid-import caps",
        }
        names = list(dict.fromkeys(labels[item] for item in active))
        lead = "Applied " + ", ".join(names)
    actions = []
    if used_solar:
        actions.append("used available solar")
    if battery_moved:
        actions.append("shifted battery energy across the day")
    actions.append("restored the initial battery level by the end of hour 23")
    return lead + ", " + ", ".join(actions) + "."
