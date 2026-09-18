from fastapi.testclient import TestClient
import json
import math

from app.main import app, set_interpreter_for_testing
from tests.conftest import make_interpreter
from tests.helpers import no_op_output, request_payload


def test_health_is_immediate_and_exact():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_invalid_hour_set_is_400():
    payload = request_payload()
    payload["hours"][23]["hour"] = 22
    response = TestClient(app).post("/optimize-energy", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid request"}


def test_missing_and_extra_fields_are_rejected():
    payload = request_payload()
    del payload["battery"]["capacity_kwh"]
    payload["unexpected"] = 1
    response = TestClient(app).post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_valid_request_echoes_scenario_and_returns_24_rows():
    set_interpreter_for_testing(make_interpreter(no_op_output()))
    response = TestClient(app).post("/optimize-energy", json=request_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scenario_id"] == "TEST-01"
    assert len(body["directive_interpretation"]) == 1
    assert len(body["hourly_plan"]) == 24


def test_note_count_and_note_types_are_strict():
    client = TestClient(app)
    for notes in ([], ["a", "b", "c", "d"], [123]):
        payload = request_payload(operator_notes=notes)
        response = client.post("/optimize-energy", json=payload)
        assert response.status_code == 400


def test_numeric_inputs_reject_negative_and_non_finite_values():
    client = TestClient(app)
    negative = request_payload()
    negative["hours"][0]["demand_kwh"] = -1
    assert client.post("/optimize-energy", json=negative).status_code == 400

    infinite = request_payload()
    infinite["hours"][0]["solar_kwh"] = math.inf
    response = client.post(
        "/optimize-energy",
        content=json.dumps(infinite, allow_nan=True),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400


def test_battery_bounds_and_types_are_validated():
    client = TestClient(app)
    invalid = request_payload()
    invalid["battery"]["initial_energy_kwh"] = 41
    assert client.post("/optimize-energy", json=invalid).status_code == 400

    invalid = request_payload()
    invalid["battery"]["minimum_energy_kwh"] = 41
    assert client.post("/optimize-energy", json=invalid).status_code == 400

    invalid = request_payload()
    invalid["battery"]["capacity_kwh"] = "40"
    assert client.post("/optimize-energy", json=invalid).status_code == 400
