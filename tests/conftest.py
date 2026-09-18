from __future__ import annotations

import pytest

from app.llm.base import LanguageModelProvider
from app.llm.interpreter import OperatorNoteInterpreter
from app.main import set_interpreter_for_testing


class FakeProvider(LanguageModelProvider):
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = 0

    async def interpret(self, *, notes, capacity_kwh, repair=None):
        self.calls += 1
        return self.outputs


@pytest.fixture
def no_op_interpreter():
    async def _make(notes):
        return [
            {
                "note_index": index,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": None,
                "explanation": "unrelated note",
            }
            for index, _ in enumerate(notes)
        ]
    return _make


@pytest.fixture(autouse=True)
def reset_interpreter():
    set_interpreter_for_testing(None)
    yield
    set_interpreter_for_testing(None)


def make_interpreter(outputs):
    return OperatorNoteInterpreter(FakeProvider(outputs))
