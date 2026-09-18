from fastapi.testclient import TestClient

from app.main import app, set_interpreter_for_testing
from app.errors import ProviderError
from app.llm.interpreter import OperatorNoteInterpreter
from app.llm.base import LanguageModelProvider
from tests.helpers import request_payload


class BrokenProvider(LanguageModelProvider):
    async def interpret(self, *, notes, capacity_kwh, repair=None):
        raise ProviderError("provider unavailable")


def test_provider_failure_is_controlled():
    set_interpreter_for_testing(OperatorNoteInterpreter(BrokenProvider()))
    response = TestClient(app).post("/optimize-energy", json=request_payload())
    assert response.status_code == 503
    assert "Traceback" not in response.text
    assert "provider" not in response.text.lower()


class InvalidThenValidProvider(LanguageModelProvider):
    def __init__(self):
        self.calls = 0

    async def interpret(self, *, notes, capacity_kwh, repair=None):
        self.calls += 1
        if repair is None:
            return [{"note_index": 0, "applies": True, "directive_type": "not_allowed", "structured_adjustment": None, "explanation": "bad"}]
        return [{
            "note_index": 0,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "unrelated",
        }]


def test_invalid_provider_output_gets_one_bounded_repair():
    provider = InvalidThenValidProvider()
    set_interpreter_for_testing(OperatorNoteInterpreter(provider))
    response = TestClient(app).post("/optimize-energy", json=request_payload())
    assert response.status_code == 200
    assert provider.calls == 2


class AlwaysInvalidProvider(LanguageModelProvider):
    async def interpret(self, *, notes, capacity_kwh, repair=None):
        return [{"note_index": 0, "applies": True, "directive_type": "not_allowed", "structured_adjustment": None, "explanation": "bad"}]


def test_invalid_provider_output_never_reaches_optimizer():
    set_interpreter_for_testing(OperatorNoteInterpreter(AlwaysInvalidProvider()))
    response = TestClient(app).post("/optimize-energy", json=request_payload())
    assert response.status_code == 503
    assert response.json() == {"error": "operator-note interpretation unavailable"}
