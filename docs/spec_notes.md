# GridWise specification notes

These notes summarize the organizer's GridWise preliminary contract. The
public sample pack is copied into the project root as
`BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json`; the validator also accepts
an alternate path at runtime.

## Contract

- `GET /health` returns HTTP 200 and `{"status":"ok"}` without an LLM call.
- `POST /optimize-energy` accepts a scenario ID, one to three non-empty notes,
  exactly one hour record for each integer hour 0 through 23, and a battery.
- Invalid structure is rejected with a sanitized 400 response.
- Provider failures return a sanitized 503 response; infeasible scenarios are
  controlled 422 responses.

## Interpretation

The model returns exactly one entry per note, in note order. The only valid
directive types are `solar_reduction`, `minimum_battery_reserve`,
`no_charge_window`, `no_discharge_window`, `max_grid_window`, and `no_op`.
Every non-`no_op` entry has `applies=true`; `no_op` has `applies=false` and a
null adjustment. Hours are unique ascending integers in `0..23`, and windows
are start-inclusive/end-exclusive. A solar factor is the fraction remaining.

The model is untrusted. Deterministic guardrails validate count, indices,
directive type, exact adjustment shape, hours, finite numeric bounds, and
reserve capacity before any directive reaches the optimizer.

## Energy model

For each hour, the compiler derives effective solar, active reserve, charge and
discharge permissions, and an optional grid-import cap. The LP minimizes
tariff-weighted grid import subject to:

```text
grid + solar_used = demand + battery_charge - battery_discharge
E_after = E_before + battery_charge - battery_discharge
active_reserve <= E_after <= capacity
E_after[23] = initial_energy
```

Solar can be curtailed, grid export does not exist, and there are no invented
battery efficiency losses. SciPy HiGHS solves the deterministic LP.

## Replay and totals

The finalized 24-row plan is replayed independently against every compiled
constraint, including energy balance, battery transitions, rates, reserves,
solar availability, grid caps, and end-of-day neutrality. Totals are then
recomputed from the replay-validated rows. The public validator additionally
checks response schema, directive semantics, replay, totals, and cost against
each public reference optimum while allowing equivalent schedules.

## Operational requirements

The service is designed for one compact model request per scenario, bounded
provider timeout/retry behavior, and a deterministic LP/replay path. Secrets
are environment-only; `.env` is ignored and `.env.example` contains no
credential. Docker binds port 8000 on `0.0.0.0` and runs the application as a
non-root user.
