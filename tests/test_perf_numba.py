"""tests/test_perf_numba.py — TDD: failing tests for Numba JIT performance.

Tests 2–4 fail until src/fractal_explorer_v2.py exposes a module-level
`_numba_escape_kernel` function decorated with @numba.jit.
Test 5 (speedup) fails until the kernel exists and is properly JIT-compiled.
Test 1 (availability) passes immediately once numba is installed.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture(scope="module")
def engine():
    import importlib.util
    spec = importlib.util.spec_from_file_location("engine_nb", _SRC / "fractal_explorer_v2.py")
    eng = importlib.util.module_from_spec(spec)
    sys.modules["fractal_engine_nb"] = eng
    sys.modules.setdefault("fractal_explorer_v2", eng)
    pygame.init()
    pygame.display.set_mode((1, 1))
    spec.loader.exec_module(eng)
    yield eng
    pygame.quit()


# ── Test 1: numba is importable ───────────────────────────────────────────────

class TestNumbaAvailable:
    def test_numba_importable(self):
        """numba must be importable (hard dep declared in pyproject.toml)."""
        import numba  # noqa: F401
        assert hasattr(numba, "jit"), "numba.jit must be available"

    def test_numba_version_meets_minimum(self):
        """numba must be ≥0.59 as declared in pyproject.toml."""
        import numba
        major, minor = (int(x) for x in numba.__version__.split(".")[:2])
        assert (major, minor) >= (0, 59) or major >= 1, (
            f"numba {numba.__version__} does not meet ≥0.59 requirement"
        )


# ── Test 2: engine exposes JIT-compiled kernel ────────────────────────────────

class TestEngineHasNumbaKernel:
    def test_numba_escape_kernel_exists(self, engine):
        """engine must expose _numba_escape_kernel at module level."""
        assert hasattr(engine, "_numba_escape_kernel"), (
            "engine must define a module-level _numba_escape_kernel function "
            "(decorated with @numba.jit)"
        )

    def test_numba_escape_kernel_is_jit_compiled(self, engine):
        """_numba_escape_kernel must be a numba CPUDispatcher (i.e., @jit decorated)."""
        import numba
        kernel = engine._numba_escape_kernel
        assert isinstance(kernel, numba.core.registry.CPUDispatcher), (
            f"_numba_escape_kernel must be a numba CPUDispatcher; got {type(kernel)}"
        )

    def test_numba_kernel_accepts_correct_args(self, engine):
        """_numba_escape_kernel(zr, zi, cr, ci, max_iter) must return an int."""
        kernel = engine._numba_escape_kernel
        result = kernel(0.0, 0.0, -0.5, 0.5, 80)
        assert isinstance(result, (int, np.integer)), (
            f"kernel must return an integer escape count; got {type(result)}"
        )
        assert 0 <= result <= 80, f"escape count must be in [0, max_iter]; got {result}"


# ── Test 3: Mandelbrot 60fps at 800×600 ──────────────────────────────────────

class TestMandelbrot60fps:
    """A single render_rows() call (rows_per_frame rows at 800×600) must
    complete within 16.7ms (= 1 frame at 60fps) after JIT warmup.
    """

    def test_mandelbrot_single_band_within_16ms(self, engine):
        """One render_rows() call at 800×600 must complete ≤16.7ms after warmup."""
        cls = next(c for c in engine.PAGE_CLASSES["A"] if c.__name__ == "Mandelbrot")
        page = cls(800, 600)
        page.reset()

        # Warmup: trigger JIT compilation
        page.render_rows(0, page.rows_per_frame)

        # Timed run
        t0 = time.perf_counter()
        page.render_rows(page.rows_per_frame, page.rows_per_frame * 2)
        elapsed = time.perf_counter() - t0

        assert elapsed <= 0.0167, (
            f"Mandelbrot render_rows at 800×600 took {elapsed*1000:.1f}ms "
            f"(limit: 16.7ms = 60fps)"
        )


# ── Test 4: Julia + BurningShip at 60fps ────────────────────────────────────

class TestJuliaAndBurningShip60fps:
    @pytest.mark.parametrize("name", ["Julia1", "BurningShip"])
    def test_form_single_band_within_16ms(self, engine, name):
        """One render_rows() call for Julia/BurningShip at 800×600 must ≤16.7ms."""
        cls = next(c for c in engine.PAGE_CLASSES["A"] if c.__name__ == name)
        page = cls(800, 600)
        page.reset()

        page.render_rows(0, page.rows_per_frame)   # warmup

        t0 = time.perf_counter()
        page.render_rows(page.rows_per_frame, page.rows_per_frame * 2)
        elapsed = time.perf_counter() - t0

        assert elapsed <= 0.0167, (
            f"{name} render_rows at 800×600 took {elapsed*1000:.1f}ms (limit: 16.7ms)"
        )


# ── Test 5: speedup vs pure-numpy baseline ───────────────────────────────────

class TestNumbaSpeedup:
    """Numba JIT kernel must be ≥3× faster than a pure Python scalar loop."""

    def test_speedup_vs_python_scalar(self, engine):
        """_numba_escape_kernel must be ≥3× faster than an equivalent Python loop."""
        kernel = engine._numba_escape_kernel

        # Pure Python scalar reference (same algorithm as the kernel)
        def python_escape(zr: float, zi: float, cr: float, ci: float, max_iter: int) -> int:
            for i in range(1, max_iter + 1):
                zr2 = zr * zr - zi * zi + cr
                zi = 2.0 * zr * zi + ci
                zr = zr2
                if zr * zr + zi * zi > 4.0:
                    return i
            return 0

        test_points = [(-0.7 + 0.01 * k, 0.27 + 0.01 * k) for k in range(50)]
        max_iter = 80

        # Warmup numba
        kernel(test_points[0][0], test_points[0][1], -0.7, 0.27, max_iter)

        # Time numba
        t0 = time.perf_counter()
        for _ in range(200):
            for cr, ci in test_points:
                kernel(cr, ci, -0.7, 0.27, max_iter)
        numba_time = time.perf_counter() - t0

        # Time Python
        t0 = time.perf_counter()
        for _ in range(200):
            for cr, ci in test_points:
                python_escape(cr, ci, -0.7, 0.27, max_iter)
        python_time = time.perf_counter() - t0

        speedup = python_time / max(numba_time, 1e-9)
        assert speedup >= 3.0, (
            f"Numba kernel speedup vs Python: {speedup:.1f}× (required ≥3×). "
            f"numba={numba_time*1000:.1f}ms, python={python_time*1000:.1f}ms"
        )
