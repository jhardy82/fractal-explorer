# v0.3.0 — Definition of Done Evidence

All five DoD gates (A.3, C.2, C.3, D.1, D.2) targeted for v0.3.0.

---

## A.3 — Mutation kill-rate ≥ 70%

**Status: SATISFIED ✓** (carried forward from v0.2.0; mutation target unchanged)

| Item | Value |
|------|-------|
| Kill rate | 96% (125 killed / 130 total) |
| Threshold | ≥ 70% |
| Last confirmed commit | `3d15894` (v0.2.0) |
| CI run | 25397325857 |

---

## C.2 — Hypothesis property tests pass

**Status: SATISFIED ✓** (regression test suite passes on every push)

| Item | Value |
|------|-------|
| Tests | 14 / 14 passing |
| Test file | `tests/test_properties.py` |

---

## C.3 — 3D perf gate: 30 frames @ 480×360 ≤ 0.500s (CI)

**Status: SATISFIED ✓** — all 7 3D forms pass

| Form | Status |
|------|--------|
| Mandelbulb | ✓ (max_steps=24, downscale=4) |
| Mandelbox | ✓ |
| MengerSponge | ✓ |
| QuatJulia | ✓ (max_steps=20, downscale=5) |
| MandelbulbPower4 | ✓ (max_steps=16, downscale=5) |
| MandelbulbPower6 | ✓ (max_steps=16, downscale=5) |
| MandelbulbPower16 | ✓ (max_steps=16, downscale=5) |

---

## D.1 — Numba ≥ 60fps @ 800×600 (escape-time forms)

**Status: PENDING CI** — local tests pass; CI confirmation pending first push

| Item | Value |
|------|-------|
| Gate | ≤ 16.7ms per frame (= 1/60s) |
| Forms covered | Mandelbrot, Julia, BurningShip, Tricorn, Multibrot3/4, Lyapunov |
| Test file | `tests/test_perf_numba.py` |
| CI job | `perf-numba` (needs: unit; timeout: 10min) |
| JIT decorator | `@numba.jit(nopython=True, cache=False, parallel=True)` |

---

## D.2 — Wheel builds cleanly (hatch)

**Status: PENDING CI** — CI job added; confirmation pending first push

| Item | Value |
|------|-------|
| Build command | `uv run hatch build` |
| CI job | `build` (needs: lint; if: always) |
| Backend | hatchling ≥ 1.26 |

---

---

# v0.2.0 — Definition of Done Evidence

All three DoD gates satisfied as of 2026-05-05. CI is green on every push to `main`.

---

## A.3 — Mutation kill-rate ≥ 70%

**Status: SATISFIED ✓**

| Item | Value |
|------|-------|
| Kill rate | 96% (125 killed / 130 total) |
| Threshold | ≥ 70% |
| Surviving mutants | 5 (all equivalent — integer arithmetic) |
| Commit | `3d15894` |
| CI run | 25397325857 |
| Gate script | `tests/_mutation_target/check_kill_rate.py` |

**Equivalent survivors** (cannot be killed — arithmetic identities when inputs are always int):

| ID | Mutation | Reason equivalent |
|----|----------|------------------|
| mandelbrot_1 | `w / 2` → `w // 2` | `w` is always `int`; `/` and `//` identical |
| mandelbrot_12 | `h / 2` → `h // 2` | same |
| julia_1 | `w / 2` → `w // 2` | same |
| to_screen_12 | `h / bh` → `h // bh` | `bh = 1` always |
| to_screen_21 | `w / bw` → `w // bw` | `bw = 1` always |

---

## C.2 — Hypothesis property tests pass

**Status: SATISFIED ✓**

| Item | Value |
|------|-------|
| Tests | 14 / 14 passing |
| Framework | Hypothesis ≥ 6.150 |
| Test file | `tests/test_properties.py` |
| Green since | commit `a584db9` |

Key properties verified:
- `escape_time` terminates for all finite complex inputs
- Coordinate helpers (`to_screen`, `from_screen`) round-trip within floating-point tolerance
- L-system rewriting is deterministic and length-bounded
- Attractor formulas produce finite outputs for seeded RNG within parameter bounds

---

## C.3 — 3D perf gate: 30 frames @ 480×360 ≤ 0.500s (CI)

**Status: SATISFIED ✓**

| Form | CI time | Gate | Result |
|------|---------|------|--------|
| Mandelbulb | 0.383s | ≤ 0.500s | ✓ pass |
| Mandelbox | < 0.300s | ≤ 0.500s | ✓ pass |
| MengerSponge | 0.380s | ≤ 0.500s | ✓ pass |

| Item | Value |
|------|-------|
| CI gate | 0.500s (GitHub Actions 2-core runner) |
| Local target | ~0.300s (measured ~0.280s on dev hardware) |
| Commit | `d453890` |
| CI run | 25398633873 |
| Test | `tests/test_3d_integration.py::TestThreeDPerformance` |

**Renderer params per form** (`src/fractal_3d.py`):

| Form | downscale | lw×lh | rows/frame | max_steps | iter_count |
|------|-----------|--------|------------|-----------|------------|
| Mandelbulb | 4 | 120×90 | 3 | 32 | 6 |
| Mandelbox | 3 (base) | 160×120 | 6 | 36 | 10 |
| MengerSponge | 4 | 120×90 | 3 | 36 | 5 |
