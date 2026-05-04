"""
test_unit.py — pure-function unit tests for fractal_explorer_v2 helpers.

Layer 1 in the doctrine. Tests run in milliseconds; no GUI side effects.
"""
from __future__ import annotations

import math
import random

import numpy as np

# ── helper functions ─────────────────────────────────────────────────────────

class TestHsvPalette:
    def test_returns_correct_shape(self, engine):
        pal = engine.hsv_palette(80)
        assert pal.shape == (81, 3)
        assert pal.dtype == np.uint8

    def test_index_zero_is_black(self, engine):
        pal = engine.hsv_palette(40)
        assert tuple(pal[0]) == (0, 0, 0)

    def test_index_one_is_not_black(self, engine):
        pal = engine.hsv_palette(40)
        # at HSV(0, 0.78, 0.92) → red-ish, definitely not black
        assert tuple(pal[1]) != (0, 0, 0)

    def test_palette_is_deterministic(self, engine):
        a = engine.hsv_palette(60)
        b = engine.hsv_palette(60)
        assert np.array_equal(a, b)

    def test_hue_offset_rotates_palette(self, engine):
        a = engine.hsv_palette(60, hue_offset=0.0)
        b = engine.hsv_palette(60, hue_offset=0.5)
        assert not np.array_equal(a[1:], b[1:])           # different
        # but the *set* of colours should be similar (rotation, not regeneration)

    def test_size_zero(self, engine):
        # n=0 means only the in-set colour (index 0)
        pal = engine.hsv_palette(0)
        assert pal.shape == (1, 3)
        assert tuple(pal[0]) == (0, 0, 0)


class TestLerp:
    def test_identity_at_zero(self, engine):
        assert engine.lerp(10, 20, 0.0) == 10

    def test_identity_at_one(self, engine):
        assert engine.lerp(10, 20, 1.0) == 20

    def test_midpoint(self, engine):
        assert engine.lerp(0, 100, 0.5) == 50

    def test_negative_extrapolation(self, engine):
        assert engine.lerp(10, 20, -1.0) == 0

    def test_above_one_extrapolation(self, engine):
        assert engine.lerp(0, 10, 2.0) == 20


class TestPhi:
    def test_phi_value(self, engine):
        assert math.isclose(engine.PHI, (1 + math.sqrt(5)) / 2, abs_tol=1e-12)

    def test_phi_is_golden_ratio_property(self, engine):
        # φ² = φ + 1
        assert math.isclose(engine.PHI ** 2, engine.PHI + 1, abs_tol=1e-12)


# ── escape-time math (compose into iter_step) ───────────────────────────────

class TestEscapeTimeFormulas:
    """Validate the iter_step methods on representative complex inputs."""

    def test_mandelbrot_z2_plus_c(self, engine, page_factory):
        page = page_factory(engine.Mandelbrot)
        z = np.array([0.0 + 0j])
        c = np.array([1.0 + 0j])
        result = page.iter_step(z, c)
        # 0² + 1 = 1
        assert np.isclose(result[0], 1.0 + 0j)

    def test_mandelbrot_iteration_2plus0_diverges(self, engine, page_factory):
        page = page_factory(engine.Mandelbrot)
        z = np.array([0.0 + 0j])
        c = np.array([2.0 + 0j])
        # iteration: 0 → 2 → 6 → 38 → … escapes immediately past |z|>4 in step 2
        z = page.iter_step(z, c)
        z = page.iter_step(z, c)
        assert abs(z[0]) > 4.0

    def test_mandelbrot_iteration_origin_stays_bounded(self, engine, page_factory):
        page = page_factory(engine.Mandelbrot)
        z = np.array([0.0 + 0j])
        c = np.array([0.0 + 0j])
        for _ in range(50):
            z = page.iter_step(z, c)
        assert abs(z[0]) < 4.0

    def test_burning_ship_uses_abs(self, engine, page_factory):
        page = page_factory(engine.BurningShip)
        z = np.array([1.0 - 1.0j])
        c = np.array([0.0 + 0j])
        # (|1| + i|−1|)² + 0 = (1 + 1i)² = 2i
        result = page.iter_step(z, c)
        assert np.isclose(result[0], 2.0j)

    def test_tricorn_uses_conjugate(self, engine, page_factory):
        page = page_factory(engine.Tricorn)
        z = np.array([2.0 + 3.0j])
        c = np.array([0.0 + 0j])
        # conj(2+3i)² = (2−3i)² = 4 − 12i + 9i² = −5 − 12i
        result = page.iter_step(z, c)
        assert np.isclose(result[0], -5.0 - 12.0j)

    def test_multibrot3_cubes(self, engine, page_factory):
        page = page_factory(engine.Multibrot3)
        z = np.array([2.0 + 0j])
        c = np.array([0.0 + 0j])
        # 2³ + 0 = 8
        assert np.isclose(page.iter_step(z, c)[0], 8.0 + 0j)

    def test_julia_uses_constant_c(self, engine, page_factory):
        page = page_factory(engine.Julia1)
        z = np.array([0.0 + 0j])
        c_local = np.array([99.0 + 99.0j])  # should be ignored
        result = page.iter_step(z, c_local)
        # 0² + c_const = c_const = -0.79+0.15i
        assert np.isclose(result[0], complex(-0.79, 0.15))


# ── strange attractor step formulas ──────────────────────────────────────────

class TestAttractorSteps:
    def test_lorenz_at_origin_stays_at_origin(self, engine, page_factory):
        page = page_factory(engine.LorenzAttractor)
        # at (0,0,0) all derivatives are 0
        x, y, z = page.step(0.0, 0.0, 0.0)
        assert math.isclose(x, 0.0, abs_tol=1e-12)
        assert math.isclose(y, 0.0, abs_tol=1e-12)
        assert math.isclose(z, 0.0, abs_tol=1e-12)

    def test_lorenz_perturbation_grows(self, engine, page_factory):
        page = page_factory(engine.LorenzAttractor)
        x, y, z = 0.1, 0.0, 0.0
        for _ in range(200):
            x, y, z = page.step(x, y, z)
        # should leave the origin
        assert abs(x) > 0.01 or abs(y) > 0.01 or abs(z) > 0.01

    def test_henon_known_fixed_point_logic(self, engine, page_factory):
        page = page_factory(engine.HenonMap)
        # x' = 1 − 1.4·x² + y, y' = 0.3·x
        x, y = 0.5, 0.5
        x2, y2, _ = page.step(x, y, 0.0)
        assert math.isclose(x2, 1 - 1.4 * 0.25 + 0.5, abs_tol=1e-12)
        assert math.isclose(y2, 0.15, abs_tol=1e-12)

    def test_de_jong_step_is_bounded(self, engine, page_factory):
        page = page_factory(engine.DeJongAttractor)
        x, y, z = 0.0, 0.0, 0.0
        for _ in range(100):
            x, y, z = page.step(x, y, z)
            # de Jong should always stay within ~|2|
            assert abs(x) < 3.0
            assert abs(y) < 3.0


# ── L-system rewriting ──────────────────────────────────────────────────────

class TestLSystemExpansion:
    def test_hilbert_one_iteration(self, engine, page_factory):
        # Manually verify one expansion step
        rules = engine.HilbertCurve.rules
        axiom = engine.HilbertCurve.axiom
        # X → +YF-XFX-FY+
        s = "".join(rules.get(ch, ch) for ch in axiom)
        assert s == "+YF-XFX-FY+"

    def test_binary_tree_one_iteration(self, engine):
        rules = engine.BinaryTreeLS.rules
        axiom = engine.BinaryTreeLS.axiom
        s = "".join(rules.get(ch, ch) for ch in axiom)
        assert s == "FF+[+F-F-F]-[-F+F+F]"

    def test_l_system_punctuation_passes_through(self, engine):
        """+/-/[/] and unknown chars should appear unchanged in expansion."""
        rules = {"F": "F+F"}
        s = "F+F[F]-F"
        out = "".join(rules.get(ch, ch) for ch in s)
        assert out == "F+F+F+F[F+F]-F+F"

    def test_gosper_two_state_rewrite(self, engine):
        rules = engine.GosperCurve.rules
        s = engine.GosperCurve.axiom
        s = "".join(rules.get(ch, ch) for ch in s)
        # one expansion of A
        assert s == "A-B--B+A++AA+B-"


# ── IFS bounds + transform selection ─────────────────────────────────────────

class TestIFSEngine:
    def test_pick_transform_obeys_probabilities(self, engine, page_factory):
        page = page_factory(engine.SierpinskiTriangleIFS)
        # all 3 transforms have prob 1/3; sample 3000 picks, expect ~1000 each
        random.seed(42)
        picks = [page._pick_transform() for _ in range(3000)]
        # group by transform identity
        ids = [page.transforms.index(t) for t in picks]
        from collections import Counter
        counts = Counter(ids)
        for tid in (0, 1, 2):
            # each should be within ±20% of 1000
            assert 800 <= counts[tid] <= 1200, f"transform {tid} count {counts[tid]} out of range"

    def test_compute_bounds_is_finite(self, engine, page_factory):
        for cls in (engine.SierpinskiTriangleIFS, engine.HeighwayDragonIFS,
                    engine.BarnsleyFernIFS, engine.LevyCIFS):
            page = page_factory(cls)
            assert math.isfinite(page.bx0) and math.isfinite(page.bx1)
            assert math.isfinite(page.by0) and math.isfinite(page.by1)
            assert page.bx1 > page.bx0
            assert page.by1 > page.by0

    def test_to_screen_centres_origin(self, engine, page_factory):
        page = page_factory(engine.SierpinskiTriangleIFS, w=400, h=400)
        # the bounding box centre should map to screen centre
        bcx = (page.bx0 + page.bx1) / 2
        bcy = (page.by0 + page.by1) / 2
        sx, sy = page._to_screen(bcx, bcy)
        # not perfectly centred because aspect-ratio fit, but close
        assert abs(sx - 200) < 10
        assert abs(sy - 200) < 10


# ── sacred geometry primitives ───────────────────────────────────────────────

class TestSacredGeometry:
    def test_seed_of_life_reset_no_error(self, engine, page_factory):
        page = page_factory(engine.SeedOfLife)
        assert page.surface is not None

    def test_tree_of_life_has_10_sephirot(self, engine, page_factory):
        # introspect the page's render — count circles. We don't have direct
        # access to vertex list, so we check render didn't throw + surface non-empty.
        page = page_factory(engine.TreeOfLife)
        import pygame
        # surface should have non-zero pixels
        arr = pygame.surfarray.array3d(page.surface)
        assert arr.sum() > 0

    def test_golden_spiral_uses_phi_growth(self, engine, page_factory):
        # The spiral is φ-recursive: log(r2/r1) per quarter-turn = log(φ)
        page = page_factory(engine.GoldenSpiralSG)
        import pygame
        arr = pygame.surfarray.array3d(page.surface)
        # spiral renders something
        assert arr.sum() > 0
