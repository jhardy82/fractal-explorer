# fractal-explorer

A pygame-based interactive explorer for **48 fractal forms** across 5 mathematical / geometric categories — escape-time, iterated function systems (IFS), L-systems, strange attractors, and Sacred Geometry.

## Run

```bash
pip install pygame numpy
python fractal_explorer_v2.py
```

## Keys

| Key | Action |
|---|---|
| `← / →` | prev / next page within category |
| `Tab` | next category |
| `1..5` | jump to category A..E |
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

## Tests

```bash
SDL_VIDEODRIVER=dummy pytest tests/
```

Four test layers per the doctrine in `docs/TESTING_DOCTRINE.md`:

- **Unit** (34 tests) — pure-function helpers, attractor formulas, escape-time math, L-system rewriting
- **Integration** (15 tests, 144 lifecycle invocations) — every page × 3 sizes
- **Regression** (34 tests, 30 baselines) — pixel-hash snapshots; stochastic pages handled via seeded RNG
- **Mutation** (mutmut) — see `docs/TESTING_DOCTRINE.md` §3 and `.github/workflows/test.yml`

Latest run: 181 / 181 passing. Manual targeted mutation: 20 / 20 = 100% on the iter-1 survivor patterns.

## Project layout

```
fractal-explorer/
├── README.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── fractal_explorer_v2.py          # the engine (1,706 LOC, 48 forms)
├── fractal_3d.py                   # optional 3D extension (Mandelbulb, Mandelbox, Menger)
├── tests/                          # all four test layers
│   ├── conftest.py
│   ├── test_unit.py
│   ├── test_integration.py
│   ├── test_regression.py
│   ├── test_properties.py          # Hypothesis property-based tests
│   ├── _baselines/                 # pixel-hash regression baselines (30 files)
│   └── _mutation_target/
│       ├── mutation_target.py      # extracted helpers for mutation testing
│       ├── test_mutation_target.py # 44 example tests
│       └── test_defaults_and_properties.py  # 54 default-param + property tests
├── docs/
│   ├── TESTING_DOCTRINE.md         # full layered testing doctrine
│   ├── FRACTAL_ENGINE_DESIGN.md    # architecture + per-fractal citations
│   └── TEST_RESULTS.md             # latest run report
└── .github/
    └── workflows/
        └── test.yml                # CI: unit + integration + regression + mutation
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

## Architecture invariant

Resource preference: only the active page's `update()` is called per frame. Inactive pages freeze. When you switch back, no recomputation happens unless you press `R`.

## License

MIT.
