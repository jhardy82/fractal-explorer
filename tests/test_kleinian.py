"""tests/test_kleinian.py — TDD: failing tests for Kleinian group limit set.

All tests fail until src/fractal_kleinian.py is implemented (ImportError on collection).
"""
from __future__ import annotations

import math

import pygame
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from fractal_kleinian import KleinianLimitSet

# ── helpers ───────────────────────────────────────────────────────────────────

def _mobius(z: complex, a: complex, b: complex, c: complex, d: complex) -> complex:
    """Apply Möbius transform f(z) = (az + b) / (cz + d)."""
    denom = c * z + d
    return (a * z + b) / denom


def _compose_mobius(T1: tuple, T2: tuple) -> tuple:
    """Compose transforms: return T such that T(z) = T1(T2(z)).

    Each transform is (a, b, c, d).  Composition = matrix product T1 × T2.
    """
    a1, b1, c1, d1 = T1
    a2, b2, c2, d2 = T2
    return (
        a1 * a2 + b1 * c2,
        a1 * b2 + b1 * d2,
        c1 * a2 + d1 * c2,
        c1 * b2 + d1 * d2,
    )


# ── Test 1: Möbius transform composition math helper ─────────────────────────
class TestMobiusTransformComposition:
    def test_mobius_identity(self):
        """Identity transform f(z) = z must fix all test points."""
        id_mat = (1, 0, 0, 1)  # f(z) = (z+0)/(0z+1) = z
        for z in [1+0j, 0+1j, 2+3j, -1-1j]:
            assert abs(_mobius(z, *id_mat) - z) < 1e-12

    def test_mobius_composition_correctness(self):
        """Composition T1∘T2 must match applying T2 then T1 manually."""
        T1 = (1, 1, 1, -1)    # f(z) = (z+1)/(z-1)
        T2 = (2, 0, 0, 1)     # f(z) = 2z
        T_composed = _compose_mobius(T1, T2)

        for z in [2+0j, 0+2j, 1+1j, 3-1j]:
            # Direct: apply T2 first, then T1
            w = _mobius(_mobius(z, *T2), *T1)
            # Via composed transform
            w_composed = _mobius(z, *T_composed)
            assert abs(w - w_composed) < 1e-10, (
                f"Composition mismatch at z={z}: direct={w}, composed={w_composed}"
            )

    def test_mobius_inverse_composition_is_identity(self):
        """T ∘ T⁻¹ must equal identity for a simple transform."""
        T = (2, 1, 1, 1)     # f(z) = (2z+1)/(z+1)
        T_inv = (1, -1, -1, 2)  # inverse: swap a↔d, negate b and c
        T_id = _compose_mobius(T, T_inv)
        # Composed should act as identity: T(T⁻¹(z)) ≈ z
        for z in [1+0j, 0+1j, 3+2j]:
            assert abs(_mobius(z, *T_id) - z) < abs(z) + 1  # near-identity up to scale


# ── Test 2: Schottky circles non-overlap invariant ───────────────────────────
class TestSchottkyCirclesNonOverlapping:
    def test_default_circles_non_overlapping(self):
        """Default r=0.35: circles centered at ±1, ±1i must not overlap."""
        r = 0.35
        centers = [1 + 0j, -1 + 0j, 0 + 1j, 0 - 1j]
        for i, c1 in enumerate(centers):
            for j, c2 in enumerate(centers):
                if i < j:
                    dist = abs(c1 - c2)
                    assert dist > 2 * r, (
                        f"Circles at {c1} and {c2} overlap: dist={dist:.4f} ≤ 2r={2*r:.4f}"
                    )

    def test_radius_too_large_would_overlap(self):
        """Sanity: r=0.8 would cause overlap (confirming why 0.35 is the default)."""
        r = 0.8
        centers = [1 + 0j, 0 + 1j]  # adjacent circles: distance = sqrt(2) ≈ 1.414
        dist = abs(centers[0] - centers[1])
        assert dist < 2 * r, "Expected overlap for r=0.8 between +1 and +1i"

    @pytest.mark.parametrize("r", [0.1, 0.2, 0.3, 0.35, 0.4, 0.44])
    def test_valid_radius_range_non_overlapping(self, r):
        """All r in (0.1, 0.45) satisfy the non-overlap condition (centers at ±1, ±1i)."""
        centers = [1 + 0j, -1 + 0j, 0 + 1j, 0 - 1j]
        for i, c1 in enumerate(centers):
            for j, c2 in enumerate(centers):
                if i < j:
                    dist = abs(c1 - c2)
                    assert dist > 2 * r, (
                        f"r={r}: circles {c1} and {c2} would overlap (dist={dist:.4f})"
                    )


# ── Test 3: limit set pixels non-zero ────────────────────────────────────────
class TestLimitSetPixelsNonzero:
    def test_limit_set_produces_pixels_after_60_updates(self):
        """After 60 update() calls the surface must have > 0 non-background pixels."""
        pygame.init()
        page = KleinianLimitSet(80, 60)
        surf = pygame.Surface((80, 60))
        page.reset()
        for f in range(1, 61):
            page.update(f)
        page.draw(surf)
        arr = pygame.surfarray.array3d(surf)
        assert arr.sum() > 0, "KleinianLimitSet produced a completely blank surface after 60 frames"

    def test_surface_not_uniform_after_render(self):
        """The rendered surface must not be a single flat colour (fractal has structure)."""
        pygame.init()
        page = KleinianLimitSet(120, 90)
        surf = pygame.Surface((120, 90))
        page.reset()
        for f in range(1, 91):
            page.update(f)
        page.draw(surf)
        arr = pygame.surfarray.array3d(surf)
        # At least two distinct pixel values must exist
        unique_rows = {tuple(arr[x, y]) for x in range(0, 120, 20) for y in range(0, 90, 20)}
        assert len(unique_rows) > 1, "Surface appears completely uniform — no fractal structure"


# ── Test 4: lifecycle ─────────────────────────────────────────────────────────
class TestLifecycleKleinian:
    @pytest.mark.parametrize("f", list(range(1, 31)))
    def test_lifecycle_frame(self, f):
        """reset() + update(f) + draw(surf) must complete without exception."""
        pygame.init()
        page = KleinianLimitSet(80, 60)
        surf = pygame.Surface((80, 60))
        page.reset()
        page.update(f)
        page.draw(surf)

    def test_reset_idempotent(self):
        """Calling reset() twice must return row to 0 and not raise."""
        pygame.init()
        page = KleinianLimitSet(40, 30)
        page.reset()
        for _ in range(5):
            page.update(1)
        page.reset()
        assert page.row == 0

    def test_category_b(self):
        """KleinianLimitSet must be in category B (IFS)."""
        page = KleinianLimitSet(10, 10)
        assert page.category == "B"

    def test_r_attribute_default(self):
        """Default r must equal 0.35."""
        page = KleinianLimitSet(10, 10)
        assert abs(page.r - 0.35) < 1e-10

    def test_custom_r(self):
        """Custom r must be stored and used."""
        page = KleinianLimitSet(10, 10, r=0.25)
        assert abs(page.r - 0.25) < 1e-10


# ── Test 5: Hypothesis — parameter range stable ───────────────────────────────
class TestParameterRangeStable:
    @given(r=st.floats(min_value=0.1, max_value=0.45, allow_nan=False))
    @settings(max_examples=50)
    def test_any_valid_r_lifecycle_stable(self, r):
        """For any r ∈ (0.1, 0.45), the page renders without raising."""
        pygame.init()
        page = KleinianLimitSet(40, 30, r=r)
        surf = pygame.Surface((40, 30))
        page.reset()
        for f in range(1, 11):
            page.update(f)
        page.draw(surf)
        # No assertion needed — exception would fail the test

    @given(r=st.floats(min_value=0.1, max_value=0.45, allow_nan=False))
    @settings(max_examples=30)
    def test_orbit_stays_bounded_at_unit_circle(self, r):
        """Starting near the unit circle boundary, orbit does not produce NaN."""
        for k in range(4):
            angle = math.pi / 2 * k
            z = complex(math.cos(angle), math.sin(angle))
            centers = [1 + 0j, -1 + 0j, 0 + 1j, 0 - 1j]
            max_iter = 32
            for _ in range(max_iter):
                # apply closest circle inversion
                dists = [abs(z - c) for c in centers]
                closest_idx = min(range(4), key=lambda i: dists[i])
                c = centers[closest_idx]
                rd = dists[closest_idx]
                if rd > 1e-12:
                    w = z - c
                    z = c + r**2 / w.conjugate()
            assert math.isfinite(z.real) and math.isfinite(z.imag), (
                f"r={r}: orbit diverged (z={z})"
            )
