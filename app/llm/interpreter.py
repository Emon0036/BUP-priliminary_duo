from __future__ import annotations

from pydantic import ValidationError

from app.errors import GuardrailError, InterpretationError
from app.config import settings
from app.guardrails import validate_interpretations
from app.llm.base import LanguageModelProvider
from app.llm.provider import OpenAICompatibleProvider
from app.models import Interpretation


class OperatorNoteInterpreter:
    def __init__(self, provider: LanguageModelProvider | None = None) -> None:
        self.provider = provider or OpenAICompatibleProvider()

    async def interpret(self, notes: list[str], capacity_kwh: float) -> list[Interpretation]:
        try:
            raw = await self.provider.interpret(notes=notes, capacity_kwh=capacity_kwh)
        except InterpretationError:
            raise
        except Exception as exc:
            raise InterpretationError("operator-note interpretation was unavailable") from exc
        try:
            result = validate_interpretations(raw, len(notes), capacity_kwh)
            return result
        except (GuardrailError, ValidationError) as first_error:
            retry_count = min(settings.llm_max_retries, 2)
            if retry_count < 1:
                raise InterpretationError("operator-note interpretation was invalid") from first_error
            last_error: Exception = first_error
            for _ in range(retry_count):
                try:
                    raw = await self.provider.interpret(
                        notes=notes,
                        capacity_kwh=capacity_kwh,
                        repair=f"Previous output failed validation: {str(last_error)[:1200]}. Return the complete corrected array only.",
                    )
                    return validate_interpretations(raw, len(notes), capacity_kwh)
                except Exception as retry_error:
                    last_error = retry_error
            raise InterpretationError("operator-note interpretation was invalid") from last_error
