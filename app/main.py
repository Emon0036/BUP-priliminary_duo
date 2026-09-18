from __future__ import annotations

import logging
import math
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from app.directives import compile_constraints
from app.errors import GridWiseError, InterpretationError, OptimizationError, ReplayValidationError
from app.llm.interpreter import OperatorNoteInterpreter
from app.models import HourPlan, Interpretation, OptimizeRequest, OptimizeResponse
from app.optimizer import solve_lp
from app.summary import make_summary
from app.validator import recompute_totals, replay_validate

logger = logging.getLogger("gridwise")
app = FastAPI(title="GridWise Energy Optimization", version="1.0.0")
_interpreter: OperatorNoteInterpreter | None = None
_project_root = Path(__file__).resolve().parent.parent
_static_dir = Path(__file__).resolve().parent / "static"
_public_samples = _project_root / "BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json"


def set_interpreter_for_testing(interpreter: OperatorNoteInterpreter | None) -> None:
    global _interpreter
    _interpreter = interpreter


def get_interpreter() -> OperatorNoteInterpreter:
    global _interpreter
    if _interpreter is None:
        _interpreter = OperatorNoteInterpreter()
    return _interpreter


@app.exception_handler(RequestValidationError)
async def request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "invalid request"})


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unexpected sanitized GridWise failure: %s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"error": "internal server error"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(_static_dir / "index.html")


@app.get("/public-samples.json", include_in_schema=False)
async def public_samples() -> FileResponse:
    return FileResponse(_public_samples, media_type="application/json")


def _number(value: float) -> float:
    value = 0.0 if abs(value) < 5e-9 else round(float(value), 8)
    if not math.isfinite(value):
        raise OptimizationError("non-finite response value")
    return value


@app.post("/optimize-energy", response_model=OptimizeResponse)
async def optimize_energy(request: OptimizeRequest) -> OptimizeResponse | JSONResponse:
    try:
        interpretations = await get_interpreter().interpret(request.operator_notes, request.battery.capacity_kwh)
        constraints = compile_constraints(request.hours, request.battery, interpretations)
        solved = solve_lp(request.hours, request.battery, constraints)
        rows: list[HourPlan] = []
        for item in solved:
            change = item.battery_change_kwh
            if change > 1e-8:
                action, amount = "charge", change
            elif change < -1e-8:
                action, amount = "discharge", -change
            else:
                action, amount = "idle", 0.0
            rows.append(
                HourPlan(
                    hour=item.hour,
                    grid_kwh=_number(item.grid_kwh),
                    solar_used_kwh=_number(item.solar_used_kwh),
                    battery_action=action,
                    battery_kwh=_number(amount),
                    battery_energy_after_kwh=_number(item.battery_energy_after_kwh),
                )
            )
        replay_validate(rows, request.hours, request.battery, constraints)
        total_grid_raw, total_cost_raw, peak_grid_raw = recompute_totals(rows, request.hours)
        return OptimizeResponse(
            scenario_id=request.scenario_id,
            directive_interpretation=interpretations,
            hourly_plan=rows,
            total_grid_kwh=_number(total_grid_raw),
            total_cost_bdt=_number(total_cost_raw),
            peak_grid_kwh=_number(peak_grid_raw),
            plan_summary=make_summary(
                interpretations,
                used_solar=any(row.solar_used_kwh > 1e-8 for row in rows),
                battery_moved=any(row.battery_kwh > 1e-8 for row in rows),
            ),
        )
    except InterpretationError as exc:
        logger.warning("controlled interpretation failure: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"error": "operator-note interpretation unavailable"})
    except OptimizationError as exc:
        logger.warning("controlled optimization failure: %s", type(exc).__name__)
        return JSONResponse(status_code=422, content={"error": "scenario cannot be optimized"})
    except ReplayValidationError:
        logger.error("optimizer output failed independent replay validation")
        return JSONResponse(status_code=500, content={"error": "internal plan validation failure"})
    except GridWiseError:
        return JSONResponse(status_code=422, content={"error": "request could not be processed"})
