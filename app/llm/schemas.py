from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from app.models import Interpretation


INTERPRETATION_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["note_index", "applies", "directive_type", "structured_adjustment", "explanation"],
    "properties": {
        "note_index": {"type": "integer"},
        "applies": {"type": "boolean"},
        "directive_type": {
            "type": "string",
            "enum": [
                "solar_reduction",
                "minimum_battery_reserve",
                "no_charge_window",
                "no_discharge_window",
                "max_grid_window",
                "no_op",
            ],
        },
        "structured_adjustment": {"type": ["object", "null"]},
        "explanation": {"type": "string"},
    },
}

# OpenAI-compatible structured-output APIs require an object at the root. The
# wrapper is transport-only; the provider unwraps it before guardrails validate
# the public interpretation array.
INTERPRETATION_ARRAY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["interpretations"],
    "properties": {"interpretations": {"type": "array", "items": INTERPRETATION_ITEM_SCHEMA}},
}


interpretation_adapter = TypeAdapter(list[Interpretation])
