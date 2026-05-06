"""
conftest.py — shared fixtures for fractal_explorer_v2 test suite.

Sets up headless SDL before any pygame import.
Provides factories for page classes, deterministic seeding, and module access.
"""
from __future__ import annotations

import importlib.util
import os
import random
import sys
from pathlib import Path

import pytest

# headless SDL must be set BEFORE pygame imports anywhere
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np  # noqa: E402  (intentional after env)
import pygame  # noqa: E402

# locate the engine module (src/ layout)
_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
_ENGINE_PATH = _SRC / "fractal_explorer_v2.py"

if not _ENGINE_PATH.exists():
    raise FileNotFoundError(
        f"fractal_explorer_v2.py not found at expected location: {_ENGINE_PATH}\n"
        "conftest expects the engine at <project-root>/src/fractal_explorer_v2.py"
    )

# put src/ on sys.path so intra-engine imports (e.g. fractal_3d → fractal_explorer_v2) resolve
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture(scope="session")
def engine():
    """Import fractal_explorer_v2 as a module, exactly once per session."""
    spec = importlib.util.spec_from_file_location("fractal_engine_v2", _ENGINE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["fractal_engine_v2"] = module
    pygame.init()
    pygame.display.set_mode((1, 1))
    spec.loader.exec_module(module)
    yield module
    pygame.quit()


@pytest.fixture
def all_page_classes(engine):
    """Flat list of (category, class) for all 48 forms."""
    return [(cat, cls) for cat, classes in engine.PAGE_CLASSES.items() for cls in classes]


@pytest.fixture
def deterministic_page_classes(engine):
    """Pages that don't depend on RNG. Safe for regression snapshotting without seeding."""
    stochastic_names = {
        # IFS chaos-game pages (use random.random())
        "SierpinskiTriangleIFS", "SierpinskiCarpet", "SierpinskiHexagon",
        "CantorSetIFS", "VicsekFractal", "TSquareFractal",
        "HeighwayDragonIFS", "TwindragonIFS", "LevyCIFS",
        "BarnsleyFernIFS", "PlusFractal",
        # attractors using floats but starting at fixed seeds — actually deterministic
        # but classified separately because they're long-running
        # Buddhabrot uses np.random
        "Buddhabrot",
    }
    return [(cat, cls) for cat, classes in engine.PAGE_CLASSES.items()
            for cls in classes if cls.__name__ not in stochastic_names]


@pytest.fixture
def stochastic_page_classes(engine):
    """Pages that need RNG seeding for deterministic regression."""
    stochastic_names = {
        "SierpinskiTriangleIFS", "SierpinskiCarpet", "SierpinskiHexagon",
        "CantorSetIFS", "VicsekFractal", "TSquareFractal",
        "HeighwayDragonIFS", "TwindragonIFS", "LevyCIFS",
        "BarnsleyFernIFS", "PlusFractal", "Buddhabrot",
    }
    return [(cat, cls) for cat, classes in engine.PAGE_CLASSES.items()
            for cls in classes if cls.__name__ in stochastic_names]


@pytest.fixture
def seeded_rng():
    """Seed Python random + numpy random. Yields, then restores nothing (test isolation)."""
    random.seed(42)
    np.random.seed(42)
    yield
    # No restoration; each test that wants determinism should use this fixture.


@pytest.fixture
def small_size():
    """Small canvas for fast tests."""
    return (320, 240)


@pytest.fixture
def medium_size():
    """Medium canvas matching real-ish use."""
    return (800, 600)


@pytest.fixture
def page_factory(engine):
    """Callable that constructs and resets a page deterministically."""
    def _make(cls, w=320, h=240, seed=42):
        random.seed(seed)
        np.random.seed(seed)
        page = cls(w, h)
        page.reset()
        return page
    return _make


def pixel_hash(surface: pygame.Surface) -> str:
    """SHA-256 of the surface's RGBA bytes — the regression-baseline primitive."""
    import hashlib
    raw = pygame.image.tostring(surface, "RGBA")
    return hashlib.sha256(raw).hexdigest()


# expose helper at module level for test imports
@pytest.fixture
def hash_surface():
    return pixel_hash


# ---------------------------------------------------------------------------
# Minimal explorer state helper — single source of truth for bare-__new__ fixtures
# ---------------------------------------------------------------------------

def _apply_minimal_explorer_state(
    exp: object, engine: object, *, w: int = 160, h: int = 120
) -> None:
    """Apply canonical minimal state to a FractalExplorer created via __new__.

    All test files that build a bare explorer (bypassing __new__) MUST call
    this function instead of duplicating state inline.  When a new feature adds
    a state variable to FractalExplorer.__init__, add it here ONLY — every
    bare-fixture test file picks it up automatically.

    Sections are tagged with the task that introduced each variable so the
    maintenance burden is obvious at a glance.
    """
    import pygame  # noqa: PLC0415 (import inside function intentional)

    # ── core display ────────────────────────────────────────────────────────
    exp.w = w                                                           # type: ignore[attr-defined]
    exp.h = h                                                           # type: ignore[attr-defined]
    exp.body_h = h - engine.NAV_H - engine.TITLE_H                     # type: ignore[attr-defined]
    exp.screen = pygame.Surface((w, h))                                 # type: ignore[attr-defined]
    exp.font_big = pygame.font.SysFont("consolas", 14, bold=True)      # type: ignore[attr-defined]
    exp.font_sm  = pygame.font.SysFont("consolas", 11)                 # type: ignore[attr-defined]
    exp.font_xs  = pygame.font.SysFont("consolas", 10)                 # type: ignore[attr-defined]

    # ── navigation / zoom / pan ─────────────────────────────────────────────
    exp.running        = True                                           # type: ignore[attr-defined]
    exp.frame          = 0                                              # type: ignore[attr-defined]
    exp.cat_idx        = 0                                              # type: ignore[attr-defined]
    exp.page_idx       = 0                                              # type: ignore[attr-defined]
    exp._pan_active    = False                                          # type: ignore[attr-defined]
    exp._pan_x0        = 0                                              # type: ignore[attr-defined]
    exp._pan_y0        = 0                                              # type: ignore[attr-defined]
    exp._pan_x_range   = (-2.5, 1.0)                                   # type: ignore[attr-defined]
    exp._pan_y_range   = (-1.25, 1.25)                                  # type: ignore[attr-defined]
    exp._zoom_target_x = None                                           # type: ignore[attr-defined]
    exp._zoom_target_y = None                                           # type: ignore[attr-defined]
    exp._zoom_lowres   = False                                          # type: ignore[attr-defined]
    exp._cinematic     = False                                          # type: ignore[attr-defined]
    exp._show_info     = False                                          # type: ignore[attr-defined]
    exp._show_fps      = False   # T19 FPS overlay                     # type: ignore[attr-defined]
    exp._bookmarks     = []                                             # type: ignore[attr-defined]
    exp._bookmark_idx  = -1                                             # type: ignore[attr-defined]
    exp._julia_seed_px = None                                           # type: ignore[attr-defined]

    # ── GIF capture (T16) ───────────────────────────────────────────────────
    exp._recording      = False                                         # type: ignore[attr-defined]
    exp._frames         = []                                            # type: ignore[attr-defined]
    exp._gif_notice     = 0                                             # type: ignore[attr-defined]
    exp._last_gif_path  = ""                                            # type: ignore[attr-defined]

    # ── kiosk / screensaver (T17) ───────────────────────────────────────────
    exp._kiosk                  = False                                 # type: ignore[attr-defined]
    exp._kiosk_timer            = 0                                     # type: ignore[attr-defined]
    exp._cinematic_before_kiosk = False                                 # type: ignore[attr-defined]

    # ── bookmark persistence (T18) ──────────────────────────────────────────
    exp._bm_notice      = 0                                             # type: ignore[attr-defined]
    exp._bm_notice_text = ""                                            # type: ignore[attr-defined]

    # ── finish construction ─────────────────────────────────────────────────
    exp._instantiate_pages()                                            # type: ignore[attr-defined]
    exp.current.ensure_init()                                           # type: ignore[attr-defined]
