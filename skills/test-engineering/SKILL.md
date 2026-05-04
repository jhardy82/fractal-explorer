---
author: James Hardy
canonical: true
canonical_for: Layered testing doctrine, pytest config, mutation testing, regression baselines
complexity: advanced
description: Layered testing doctrine for ContextForge / TaskForge — Unit · Integration · Mutation · Regression × CLI / Pygame / Web / Native desktop. Use when designing or extending a test suite, choosing tools, gating CI, or interpreting mutation kill rates.
estimatedTime: 30-90 min
hooks:
  onActivate: Load layer × surface matrix; surface tooling defaults; remind about Triple-Check Protocol mapping.
imports:
  - sacred-geometry-philosophy
license: MIT
name: test-engineering
permissions: read
prerequisites: []
relatedSkills:
  - sacred-geometry-philosophy
  - mcp-engineering
tags:
  - testing
  - pytest
  - mutation
  - regression
  - ci
  - quality
version: 1.0.0
---

# Test Engineering — Layered Doctrine

Compressed canonical version. Full reference: `docs/TESTING_DOCTRINE_v1.md`.

## Core Principle

**Build → Validate → Reproduce.** Layers + surfaces are how the *Validate* leg gets done; CI artefact retention is how *Reproduce* gets done. Skip any leg and you don't ship.

## The 4 Layers

| Layer | Lens | Validates that … | Killer tool (Python) |
|---|---|---|---|
| **Unit** | one function in isolation | logic is right on known inputs | `pytest` + `Hypothesis` |
| **Integration** | composed components, real I/O | components agree on contracts | `pytest` + `:memory:` SQLite / `testcontainers` |
| **Mutation** | the **test suite itself** | tests catch real bugs | `mutmut 3.x` (preferred over cosmic-ray) |
| **Regression** | observable output stable | nothing changed without intent | `syrupy` for golden / SHA-256 for pygame surfaces |

Layers are orthogonal to surfaces. Every surface gets all four.

## The 4 Surfaces

| Surface | What you drive |
|---|---|
| **CLI** | argv, exit code, JSON envelope · use `typer.testing.CliRunner` not subprocess |
| **Pygame GUI** | event loop, surface state · use `SDL_VIDEODRIVER=dummy` headless + surface SHA-256 |
| **Web UI** | DOM, network, screenshot · use `Playwright` (5× lead over Cypress in 2026) |
| **Native desktop** | UIA tree · use `FlaUI v4` for .NET, `Appium Windows Driver` for cross-platform. **Avoid WinAppDriver** (paused since Nov 2020). |

## Decision matrix (Python primary)

| Layer × Lang | Tool | Install |
|---|---|---|
| Unit (Python) | `pytest >=8.3, <10` + `pytest-cov` + `hypothesis` | `uv add --dev pytest pytest-cov hypothesis` |
| Unit (PowerShell) | `Pester 5.7.x` (avoid Pester 4 syntax; 6 still alpha) | `Install-Module Pester -MinimumVersion 5.7` |
| Unit (TypeScript) | `vitest 3.x` (preferred over Jest 30) | `npm i -D vitest` |
| Mutation (Python) | `mutmut 3.5+` | `uv add --dev mutmut` |
| Mutation (TS) | `StrykerJS 8.x` + vitest-runner | `npm i -D @stryker-mutator/core @stryker-mutator/vitest-runner` |
| Mutation (.NET) | `Stryker.NET 4.13+` | `dotnet tool install -g dotnet-stryker` |
| Regression (Python) | `syrupy 4.x` (replaces dead `snapshottest`) | `uv add --dev syrupy` |
| Regression (Web) | Playwright screenshot diff + Argos / Chromatic | `npm init playwright@latest` |

## Default-parameter mutation pattern (load-bearing)

The most common mutmut survivor pattern is mutation of default parameter values. Cover them with **anchor + sentinel** assertions:

```python
def test_default_sat_is_0_78():
    """Anchor: explicit default matches no-args call."""
    assert np.array_equal(hsv_palette(40), hsv_palette(40, sat=0.78))

def test_default_sat_differs_from_other():
    """Sentinel: parameter is load-bearing."""
    assert not np.array_equal(hsv_palette(40), hsv_palette(40, sat=0.50))
```

Apply this pattern to every default in every public function. Without it, mutmut kill rate caps in the 60s. With it, 90%+.

## Pygame headless caveats

```python
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"  # before pygame import
import pygame
pygame.init()
pygame.display.set_mode((1, 1))  # any size, dummy doesn't care
```

Three rules:

1. Set the env var **before** `import pygame`.
2. **Do not** call `Surface.convert()` in headless mode — it downsamples to dummy driver's pixel format, losing precision.
3. For regression baselines, hash the pixel bytes directly: `hashlib.sha256(pygame.image.tostring(surf, "RGBA")).hexdigest()`.

## Stochastic-page regression

Chaos-game IFS pages, Buddhabrot, anything using `random.random()` or `np.random` won't pass identical-hash assertions on rerun. Two fixes:

1. **Seed the RNG** in `reset()`: `random.seed(seed); np.random.seed(seed)`.
2. **Skip with parametrize** for known-stochastic classes that don't accept a seed.

A determinism property test (`hash_run_a == hash_run_b`) belongs in the regression layer too — it validates that regression-baseline assertions are even meaningful.

## Mutation kill rate thresholds

| Kill rate | Reading |
|---|---|
| ≥ 90% | Strong. Surviving mutants likely equivalent (no observable behaviour change). |
| 80–89% | Good. Worth one survivor-analysis pass. |
| 70–79% | Acceptable for non-critical paths. CI gate floor. |
| 60–69% | Suite checks happy paths only. Default-parameter assertions are the usual fix. |
| < 60% | Tests don't exercise the function bodies meaningfully. |

## CI orchestration (skeleton)

```yaml
jobs:
  unit:    {needs: [], steps: [..., pytest tests/test_unit.py]}
  integ:   {needs: unit, steps: [..., pytest tests/test_integration.py]}
  regr:    {needs: unit, steps: [..., pytest tests/test_regression.py]}
  mutation:
    needs: [unit, integ]
    steps:
      - run: cd tests/_mutation_target && mutmut run
      - run: KILLED=$(... grep killed); TOTAL=$(... ); [ $((KILLED*100/TOTAL)) -ge 70 ] || exit 1
```

Set `MUTANT_UNDER_TEST=""` and `TMPDIR=/tmp` at the workflow `env:` level to sidestep two known mutmut + pytest cleanup interactions.

## Sacred Geometry mapping

- **Triangle** = Arrange / Act / Assert per test, and Build / Validate / Reproduce per artefact.
- **Pentad (PAOAL)** = Plan (write spec) → Act (run) → Observe (capture) → Assess (interpret) → Learn (update suite).
- **Spiral** = each iteration lifts kill rate / closes a gap. Flat circle (same metrics for months) = suite saturated; introduce a new layer.
- **Decad** = full coverage = unit + integration + mutation + regression + property + lint + types + CI + artefact-retention + flaky-test management.

## Red flags

- Mock the database in repository tests → real bugs hide. Use `:memory:` SQLite.
- `Mock()` without `spec=` → typos pass silently.
- Snapshot tests without seeded RNG → flake.
- Mutation kill rate without test-pass-rate context → meaningless.
- "It passes locally" → you forgot `SDL_VIDEODRIVER=dummy` or `TMPDIR=/tmp`.
- WinAppDriver in 2026 → use FlaUI v4.

## Cross-cluster handoff (UCL Lifecycle compliance)

When this skill produces a deliverable that hands off to another agent / future session, attach a Research Baton + Lifecycle attestation:

```markdown
## Research Baton
| Source | test-engineering skill |
| Lane | synthesis |
| Confidence | HIGH/MEDIUM/LOW |
| Status | COMPLETE / NEEDS_REVIEW |
| Artifact | <path or inline> |

## UCL Lifecycle 5-Law
| Law 3 — Propagation | this baton record carries context forward |
| Law 4 — Preservation | <N> tests preserved verbatim in suite |
| Law 5 — Reporting | audit trail: <run-id>, ISO timestamp |
```

## References

- Full doctrine: `docs/TESTING_DOCTRINE_v1.md`
- Worked example: `docs/FRACTAL_TEST_RESULTS.md` + iter-2
- Mutmut vs Cosmic-Ray: IEEE 10818231 (2025 study)
- Playwright vs Cypress 2026: 33M / 6.5M weekly DL → 5× lead
