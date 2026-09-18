# Three-minute technical video script

**0:00-0:25 - Problem.** GridWise receives a campus demand, solar forecast,
tariff schedule, battery state, and one to three operator notes. It must turn
those notes into a feasible, cost-minimal 24-hour energy plan.

**0:25-0:55 - Architecture.** The request passes through strict Pydantic
validation, one structured LLM interpretation call, deterministic guardrails,
directive compilation, a HiGHS linear program, independent replay validation,
and recomputed response totals.

**0:55-1:30 - LLM role.** The model sees operator notes as untrusted data and
returns exactly one of six supported directives per note. It normalizes
whole-hour windows, solar factors, and relative battery reserves. It never
changes demand, tariffs, battery inputs, or the final schedule. Guardrails
reject missing notes, duplicate or invalid hours, unsupported directives, bad
numeric bounds, and malformed adjustment shapes.

**1:30-2:05 - Optimization.** The deterministic compiler creates effective
solar, battery reserve, charge/discharge permissions, and grid caps. The LP
minimizes tariff-weighted grid import while enforcing energy balance, battery
rates, capacity, reserves, solar availability, grid limits, and restoration of
the initial battery energy at hour 23.

**2:05-2:30 - Replay.** The returned rows are independently replayed hour by
hour. Any state transition, energy balance, directive, or total mismatch is
rejected. The API only returns totals calculated from the validated final plan.

**2:30-2:50 - Verification.** `pytest -q` exercises schemas, guardrails,
optimizer behavior, randomized feasible scenarios, provider failures, and
replay corruption. The public-sample script iterates the organizer's JSON and
checks all cases without hard-coding their schedules.

**2:50-3:00 - Operations.** `/health` is lightweight, the model provider is
configured only through environment variables, and Docker runs the service as
a non-root process on port 8000. This keeps language interpretation flexible
while making the physics and final answer deterministic and auditable.
