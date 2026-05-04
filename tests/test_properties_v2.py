"""
test_properties_v2.py — Hypothesis property tests for the fractal engine.

Layer: properties / invariants. Complements example-based unit tests by
verifying claims that hold for ALL inputs (within strategy bounds).

Coverage gaps closed (per iter-2 report §3 next-steps):
    1. IFS bbox is finite, non-degenerate, and approximately encloses the
       attractor (Monte-Carlo bounded, with margin allowing for sampling)
    2. L-system string-length growth follows actual rule arithmetic
    3. Strange-attractor step continuity (small dt → small step)
    4. Sacred Geometry forms produce non-empty deterministic renders
    5. Escape-time progressive render advances `row` by exactly rows_per_frame
"""
from __future__ import annotations

import hashlib
import math
import os
import random

from hypothesis import HealthCheck, Verbosity, given, settings
from hypothesis import strategies as st

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

settings.register_profile(
    "slow_ok",
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    max_examples=30,
    verbosity=Verbosity.normal,
)
settings.load_profile("slow_ok")

# strategies
seed_st = st.integers(min_value=0, max_value=2**31 - 1)
small_size_st = st.tuples(
    st.integers(min_value=80, max_value=200),
    st.integers(min_value=60, max_value=160),
)


# ── IFS bbox property ───────────────────────────────────────────────────────

class TestIFSBboxV2:
    """Bbox is a Monte-Carlo estimate; the honest properties are: finite,
    non-degenerate, and approximately enclosing under sampling margin."""

    def test_bbox_finite_and_non_degenerate(self, engine):
        # Cantor Set is genuinely 1D (its y-extent collapses to zero) — exclude
        ONE_D_KNOWN = {"CantorSetIFS"}
        for cls in engine.PAGE_CLASSES["B"]:
            if not hasattr(cls, "transforms") or not cls.transforms:
                continue
            page = cls(320, 240)
            page.reset()
            assert math.isfinite(page.bx0) and math.isfinite(page.bx1)
            assert math.isfinite(page.by0) and math.isfinite(page.by1)
            assert page.bx1 > page.bx0, f"{cls.__name__}: x degenerate"
            if cls.__name__ not in ONE_D_KNOWN:
                assert page.by1 > page.by0, f"{cls.__name__}: y degenerate"

    @given(seed_st)
    def test_sierpinski_long_run_mostly_inside_bbox(self, engine, seed):
        random.seed(seed)
        page = engine.SierpinskiTriangleIFS(320, 240)
        page.reset()
        bw = page.bx1 - page.bx0
        bh = page.by1 - page.by0
        margin_x = bw * 0.20
        margin_y = bh * 0.20
        x, y = 0.0, 0.0
        outside = 0
        N = 500
        for _ in range(N):
            t = page._pick_transform()
            x = t[0] * x + t[1] * y + t[4]
            y = t[2] * x + t[3] * y + t[5]
            if not (page.bx0 - margin_x <= x <= page.bx1 + margin_x and
                    page.by0 - margin_y <= y <= page.by1 + margin_y):
                outside += 1
        assert outside / N < 0.05

    def test_to_screen_centres_origin(self, engine):
        for cls in engine.PAGE_CLASSES["B"]:
            if not hasattr(cls, "transforms") or not cls.transforms:
                continue
            page = cls(400, 300)
            page.reset()
            cx = (page.bx0 + page.bx1) / 2
            cy = (page.by0 + page.by1) / 2
            sx, sy = page._to_screen(cx, cy)
            assert abs(sx - 200) <= 1
            assert abs(sy - 150) <= 1


# ── L-system growth property (with correct rule arithmetic) ────────────────

class TestLSystemGrowthV2:
    def test_binary_tree_F_count_grows_by_actual_rule_F_count(self, engine):
        rules = engine.BinaryTreeLS.rules
        F_in_rule = rules["F"].count("F")   # 8 in current source
        s = "F"
        for _ in range(3):
            f_before = s.count("F")
            s = "".join(rules.get(ch, ch) for ch in s)
            assert s.count("F") == f_before * F_in_rule

    def test_hilbert_xy_count_grows_by_per_rule_xy_count(self, engine):
        rules = engine.HilbertCurve.rules
        x_xy = rules["X"].count("X") + rules["X"].count("Y")
        y_xy = rules["Y"].count("X") + rules["Y"].count("Y")
        # both rules should produce the same count of X|Y chars
        assert x_xy == y_xy
        s = engine.HilbertCurve.axiom
        prev = s.count("X") + s.count("Y")
        for _ in range(3):
            s = "".join(rules.get(ch, ch) for ch in s)
            new = s.count("X") + s.count("Y")
            assert new == prev * x_xy
            prev = new

    def test_unknown_chars_pass_through(self):
        rules = {"F": "FF"}
        for s in ["F+F", "F-F", "F[F]F", "F+++F---F"]:
            new = "".join(rules.get(ch, ch) for ch in s)
            for ch in "+-[]":
                assert new.count(ch) == s.count(ch)

    @given(st.integers(min_value=1, max_value=4))
    def test_gosper_AB_count_grows_monotonically(self, engine, k):
        rules = engine.GosperCurve.rules
        s = engine.GosperCurve.axiom
        prev = s.count("A") + s.count("B")
        for _ in range(k):
            s = "".join(rules.get(ch, ch) for ch in s)
            new = s.count("A") + s.count("B")
            assert new > prev
            prev = new


# ── attractor continuity ───────────────────────────────────────────────────

class TestAttractorContinuityV2:
    @given(
        st.floats(min_value=-15, max_value=15, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-15, max_value=15, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0, max_value=30, allow_nan=False, allow_infinity=False),
    )
    def test_lorenz_step_bounded(self, engine, x, y, z):
        page = engine.LorenzAttractor(320, 240)
        page.reset()
        x_n, y_n, z_n = page.step(x, y, z)
        # default dt=0.005; max derivative magnitude bounded by ~30^2 on the xy term
        assert abs(x_n - x) < 6.0
        assert abs(y_n - y) < 6.0
        assert abs(z_n - z) < 6.0

    @given(
        st.floats(min_value=-2, max_value=2, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-2, max_value=2, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
    )
    def test_rossler_step_bounded(self, engine, x, y, z):
        page = engine.RosslerAttractor(320, 240)
        page.reset()
        x_n, y_n, z_n = page.step(x, y, z)
        assert abs(x_n - x) < 5.0
        assert abs(y_n - y) < 5.0
        assert abs(z_n - z) < 5.0

    def test_henon_is_deterministic(self, engine):
        page = engine.HenonMap(320, 240)
        page.reset()
        a = page.step(0.0, 0.0, 0.0)
        b = page.step(0.0, 0.0, 0.0)
        assert a == b


# ── Sacred Geometry property ───────────────────────────────────────────────

class TestSacredGeometryV2:
    @given(small_size_st)
    def test_all_sg_non_empty_at_any_size(self, engine, size):
        w, h = size
        for cls in engine.PAGE_CLASSES["E"]:
            page = cls(w, h)
            page.reset()
            arr = pygame.surfarray.array3d(page.surface)
            assert arr.sum() > 0

    def test_sg_render_idempotent(self, engine):
        for cls in engine.PAGE_CLASSES["E"]:
            page1 = cls(320, 240); page1.reset()
            page2 = cls(320, 240); page2.reset()
            h1 = hashlib.sha256(pygame.image.tostring(page1.surface, "RGBA")).hexdigest()
            h2 = hashlib.sha256(pygame.image.tostring(page2.surface, "RGBA")).hexdigest()
            assert h1 == h2


# ── escape-time progressive ───────────────────────────────────────────────

class TestEscapeTimeProgressiveV2:
    def test_mandelbrot_row_advance_consistent(self, engine):
        page = engine.Mandelbrot(320, 240)
        page.reset()
        rpf = page.rows_per_frame
        prev = 0
        for _ in range(20):
            page.update(1)
            advance = page.row - prev
            if page.row < page.h:
                assert advance == rpf
            prev = page.row
            if page.row >= page.h:
                break
        assert page.row >= page.h

    @given(st.sampled_from(["Mandelbrot", "Julia1", "BurningShip", "Tricorn"]))
    def test_escape_time_finishes(self, engine, name):
        """All escape-time forms complete rendering within a bounded frame count."""
        cls = next(c for c in engine.PAGE_CLASSES["A"] if c.__name__ == name)
        page = cls(160, 120)
        page.reset()
        max_frames = (page.h // max(page.rows_per_frame, 1)) + 10
        for _ in range(max_frames):
            page.update(1)
            if page.row >= page.h:
                break
        assert page.row >= page.h, f"{name} did not finish in {max_frames} frames"
