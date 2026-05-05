# fractal-explorer

A pygame-based interactive explorer for **51 fractal forms** across 6 mathematical / geometric categories — escape-time, iterated function systems (IFS), L-systems, strange attractors, Sacred Geometry, and 3D distance-estimator raymarching.

## Run

```bash
# Recommended — uv manages the virtualenv automatically
pip install uv
uv run python fractal_explorer_v2.py

# Or install and use the entry-point script
uv sync
uv run fractal-explorer
```

## Keys

| Key | Action |
|---|---|
| `← / →` | prev / next page within category |
| `Tab` | next category |
| `1..6` | jump to category A..F |
| `R` | reset (re-init) current page |
| `F` | toggle fullscreen |
| `Esc` | quit |

## Categories

| Cat | Forms |
|---|---|
| **A · Escape-Time** | Mandelbrot · Julia ×2 · Burning Ship · Tricorn · Multibrot d=3, d=4 · Newton z³−1 · Phoenix · Lyapunov · Buddhabrot |
| **B · IFS** | Sierpiński △ / Carpet / Hexagon · Cantor · Vicsek · T-Square · Koch curve / snowflake · Heighway Dragon · Twindragon · Lévy C · Barnsley Fern · Plus · Pythagoras Tree · Apollonian Gasket |
| **C · L-System** | Binary Tree · Hilbert · Peano · Gosper · Sierpiński Arrowhead · Plant ×2 · Penrose P3 |
| **D · Attractor** | Lorenz · Rössler · Aizawa · Clifford · De Jong · Ikeda · Hénon |
| **E · Sacred Geometry** | Vesica Piscis · Seed of Life · Flower of Life · Metatron's Cube · Tree of Life (10 Sephirot) · Golden Spiral · Sri Yantra |
| **F · Dimension** | Mandelbulb (power-8) · Mandelbox · Menger Sponge — numpy DE raymarcher, auto-rotating camera |

## Tests

```bash
# Linux / macOS
SDL_VIDEODRIVER=dummy uv run pytest tests/

# Windows (SDL_VIDEODRIVER set in pyproject.toml filterwarnings)
uv run pytest tests/
```

Five test layers per the doctrine in `docs/TESTING_DOCTRINE.md`:

- **Unit** (34 tests) — pure-function helpers, attractor formulas, escape-time math, L-system rewriting
- **Integration** (15 tests, 144 lifecycle invocations) — every 2D page × 3 sizes
- **3D Integration** (21 tests) — lifecycle, DE correctness, camera, and C.3 perf gate (30 frames @ 480×360 ≤ 0.500s)
- **Regression** (34 tests, 30 baselines) — pixel-hash snapshots; stochastic pages via seeded RNG
- **Property** (14 tests) — Hypothesis property-based tests (C.2 DoD)
- **Mutation** (mutmut) — 130 mutants, 96% kill-rate (A.3 DoD) — see `docs/TESTING_DOCTRINE.md`

CI: 10-job GitHub Actions pipeline on every push to `main`.

## CI / DoD Dashboard

```bash
uv run python scripts/dashboard.py          # one-shot
uv run python scripts/dashboard.py --watch  # auto-refresh every 30s
```

Queries the latest GitHub Actions run via `gh` CLI and renders a live table of job statuses and DoD gate verdicts. Requires `gh auth login`.

## Project layout

```
fractal-explorer/
├── README.md
├── LICENSE
├── pyproject.toml                      # uv project; dev extras: pytest, hypothesis, mutmut, ruff, rich
├── .gitignore
├── fractal_explorer_v2.py              # 2D engine (1,706 LOC, 48 forms, categories A–E)
├── src/
│   └── fractal_3d.py                  # 3D extension — DE raymarcher (Mandelbulb, Mandelbox, Menger)
├── scripts/
│   └── dashboard.py                   # refreshable Rich terminal CI / DoD status dashboard
├── tests/
│   ├── conftest.py
│   ├── test_unit.py
│   ├── test_integration.py
│   ├── test_3d_integration.py         # 3D lifecycle + DE + perf gate (C.3 DoD)
│   ├── test_regression.py
│   ├── test_properties.py             # Hypothesis property-based tests (C.2 DoD)
│   ├── _baselines/                    # pixel-hash regression baselines (30 files)
│   └── _mutation_target/
│       ├── mutation_target.py         # extracted helpers for mutation testing
│       ├── test_mutation_target.py    # 44 example tests
│       ├── test_defaults_and_properties.py  # 54 default-param + property tests
│       └── check_kill_rate.py         # SQLite gate script (A.3 DoD, ≥70% required)
├── docs/
│   ├── TESTING_DOCTRINE.md            # full layered testing doctrine
│   ├── FRACTAL_ENGINE_DESIGN.md       # architecture + per-fractal citations
│   └── TEST_RESULTS.md                # latest run report
└── .github/
    └── workflows/
        └── test.yml                   # CI: lint · unit×3 · integration · integration-3d · regression · property · mutation
```

## Mathematical references

Each fractal form's source is cited in its `info` string (visible in the title bar). Major references:

- Sierpiński · Cantor · Koch · Lévy: 19th–20th century classical fractals
- Mandelbrot · Julia: Mandelbrot 1980, Julia 1918
- Burning Ship: Michelitsch & Rössler 1992
- Buddhabrot: Melinda Green 1993
- Lyapunov: Markus 1989
- Lorenz attractor: Lorenz 1963
- Rössler attractor: Rössler 1976
- Aizawa: Aizawa 1980s
- Hénon map: Hénon 1976
- Ikeda map: Ikeda 1979
- Clifford / De Jong attractors: Pickover 1990s
- Apollonian gasket: Descartes' theorem (1643)
- Penrose tiling: Penrose 1974
- Mandelbulb: White & Nylander 2009
- Mandelbox: Tom Lowe 2010
- Menger Sponge: Karl Menger 1926

## Architecture invariant

Resource preference: only the active page's `update()` is called per frame. Inactive pages freeze. When you switch back, no recomputation happens unless you press `R`.

## License

MIT.
