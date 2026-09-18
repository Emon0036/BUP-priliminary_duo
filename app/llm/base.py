from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LanguageModelProvider(ABC):
    @abstractmethod
    async def interpret(self, *, notes: list[str], capacity_kwh: float, repair: str | None = None) -> Any:
        """Return parsed JSON-like model output for all supplied notes."""
