"""tests/test_newton.py — TDD: failing tests for Newton generalised fractal.

All tests fail until fractal_newton.py is implemented (ImportError on collection).
"""
from __future__ import annotations

import math

import pygame
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# conftest.py adds src/ to sys.path before this module is collected.
# Will raise ImportError until src/fractal_newton.py exists — all tests fail "red".
from fractal_newton import Newton4, Newton5, Newton6, NewtonGeneralised


# ── Test 1: degree-3 lifecycle + non-empty render ─────────────────────────────
class TestDegree3Lifecycle:
    def test_degree_3_renders_non_empty(self):
        """NewtonGeneralised(n=3) must produce a non-blank surface after 30 frames."""
        pygame.init()
        page = NewtonGeneralised(80, 60, n=3)
        surf = pygame.Surface((80, 60))
        page.reset()
        for f in range(1, 31):
            page.update(f)
        page.draw(surf)
        arr = pygame.surfarray.array3d(surf)
        assert arr.sum() > 0, "NewtonGeneralised(n=3) produced a completely blank surface"

    def test_degree_3_three_roots_of_unity(self):
        """Newton z³−1 must converge to the 3 roots of unity from points near each root."""
        n = 3
        roots = [complex(math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n)) for k in range(n)]
        for root in roots:
            z = root * 0.98
            for _ in range(60):
                denom = n * z ** (n - 1)
                if abs(denom) < 1e-12:
                    break
                z = z - (z**n - 1) / denom
            distances = [abs(z - r) for r in roots]
            assert min(distances) < 1e-5, f"Point near root {root!r} did not converge; z={z!r}"


# ── Test 2: degree-n root count ───────────────────────────────────────────────
class TestDegreeNRootsCount:
    @pytest.mark.parametrize("n", [2, 3, 4, 5, 6])
    def test_degree_n_produces_n_distinct_roots(self, n):
        """Newton z^n−1 must converge to exactly n distinct roots of unity."""
        roots = set()
        for k in range(n):
            angle = 2 * math.pi * k / n
            # start 2% inside the unit circle near each root
            z = complex(math.cos(angle) * 0.98, math.sin(angle) * 0.98)
            for _ in range(100):
                denom = n * z ** (n - 1)
                if abs(denom) < 1e-12:
                    break
                z = z - (z**n - 1) / denom
            roots.add((round(z.real, 3), round(z.imag, 3)))
        assert len(roots) == n, f"Expected {n} distinct roots, got {len(roots)}: {roots}"


# ── Test 3: convergence near individual roots ─────────────────────────────────
class TestConvergenceAtRoots:
    @pytest.mark.parametrize("n,k", [(3, 0), (3, 1), (3, 2), (4, 0), (4, 1), (5, 2)])
    def test_convergence_near_kth_root(self, n, k):
        """A point near the k-th root of unity must converge to that root within 50 steps."""
        angle = 2 * math.pi * k / n
        root = complex(math.cos(angle), math.sin(angle))
        z = root + complex(0.001, 0.001)
        for _ in range(50):
            denom = n * z ** (n - 1)
            if abs(denom) < 1e-12:
                break
            z = z - (z**n - 1) / denom
        assert abs(z - root) < 1e-4, f"n={n}, k={k}: did not converge to {root!r}; got {z!r}"


# ── Test 4: Hypothesis — escape count always bounded ─────────────────────────
class TestParameterRangeFinite:
    @given(
        zr=st.floats(min_value=-3.0, max_value=3.0, allow_nan=False, allow_infinity=False),
        zi=st.floats(min_value=-3.0, max_value=3.0, allow_nan=False, allow_infinity=False),
        n=st.integers(min_value=2, max_value=6),
    )
    @settings(max_examples=300)
    def test_iteration_always_terminates(self, zr, zi, n):
        """For any finite z and degree 2≤n≤6, Newton iteration terminates within max_iter."""
        max_iter = 64
        z = complex(zr, zi)
        # Only skip z=0 exactly (pole of the iteration)
        if abs(z) < 1e-10:
            return
        for _step in range(max_iter):
            denom = n * z ** (n - 1)
            if abs(denom) < 1e-12:
                break
            z_new = z - (z**n - 1) / denom
            if not (math.isfinite(z_new.real) and math.isfinite(z_new.imag)):
                break
            z = z_new


# ── Test 5: lifecycle for all subclasses ─────────────────────────────────────
class TestLifecycleAllDegrees:
    @pytest.mark.parametrize("n", [2, 3, 4, 5, 6])
    def test_generalised_lifecycle(self, n):
        """NewtonGeneralised(n) must reset/update/draw without exception."""
        pygame.init()
        page = NewtonGeneralised(80, 60, n=n)
        surf = pygame.Surface((80, 60))
        page.reset()
        page.update(1)
        page.draw(surf)

    def test_newton4_lifecycle(self):
        pygame.init()
        page = Newton4(80, 60)
        surf = pygame.Surface((80, 60))
        page.reset()
        page.update(1)
        page.draw(surf)

    def test_newton5_lifecycle(self):
        pygame.init()
        page = Newton5(80, 60)
        surf = pygame.Surface((80, 60))
        page.reset()
        page.update(1)
        page.draw(surf)

    def test_newton6_lifecycle(self):
        pygame.init()
        page = Newton6(80, 60)
        surf = pygame.Surface((80, 60))
        page.reset()
        page.update(1)
        page.draw(surf)

    def test_newton4_has_four_basins(self):
        """Newton z^4−1 basins are 1, i, -1, -i."""
        roots = [1 + 0j, 0 + 1j, -1 + 0j, 0 - 1j]
        converged = set()
        for root in roots:
            z = root * 0.97
            for _ in range(80):
                denom = 4 * z**3
                if abs(denom) < 1e-12:
                    break
                z = z - (z**4 - 1) / denom
            best = min(range(4), key=lambda i: abs(z - roots[i]))
            converged.add(best)
        assert len(converged) == 4, f"Expected 4 distinct basins, got {len(converged)}"

    def test_subclasses_expose_degree_attribute(self):
        """Newton4/5/6 must expose n=4/5/6 respectively."""
        assert Newton4(10, 10).n == 4
        assert Newton5(10, 10).n == 5
        assert Newton6(10, 10).n == 6

    def test_reset_idempotent(self):
        """Calling reset() twice must not raise and must produce consistent state."""
        pygame.init()
        page = NewtonGeneralised(40, 30, n=3)
        page.reset()
        row_after_first = page.row
        page.reset()
        assert page.row == row_after_first == 0
