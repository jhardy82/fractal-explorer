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
