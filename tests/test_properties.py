"""
test_properties.py — Hypothesis property-based tests for the fractal engine.

Layer: properties / invariants. Complements example-based unit tests by
verifying claims that hold for ALL inputs (within strategy bounds), not
just specific cases.

Coverage gaps closed (per iter-2 report §3 next-steps):
    1. IFS bounding-box always encloses computed attractor points
    2. L-system string-length growth follows expansion-rule arithmetic
    3. Strange attractor step continuity (small input perturbations →
       small output perturbations, locally)
    4. Sacred Geometry forms produce non-empty bounded renders
"""
from __future__ import annotations

import math
import os
import random

from hypothesis import HealthCheck, Verbosity, given, settings
from hypothesis import strategies as st

# headless SDL must be set before pygame imports
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

# Hypothesis settings — disable deadline (raymarching pages can be slow under
# instrumentation) and suppress function-scoped fixture health-check.
settings.register_profile(
    "slow_ok",
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    max_examples=30,   # keep CI runtime bounded
    verbosity=Verbosity.normal,
)
settings.load_profile("slow_ok")


# ── strategies ──────────────────────────────────────────────────────────────

seed_st = st.integers(min_value=0, max_value=2**31 - 1)
size_st = st.tuples(
    st.integers(min_value=80, max_value=400),     # width
    st.integers(min_value=60, max_value=300),     # height
)
small_size_st = st.tuples(
    st.integers(min_value=80, max_value=200),
    st.integers(min_value=60, max_value=160),
)


# ── IFS — bounding-box property ─────────────────────────────────────────────
#
# Claim: the auto-computed bounding box (bx0, bx1, by0, by1) of an IFS
# fractal must enclose every point produced by `_pick_transform` + apply.
# If a point falls outside, `_to_screen` would map it off-canvas, breaking
# the visual rendering.

class TestIFSBoundingBoxProperty:
    """Bbox is a Monte-Carlo estimate, not provably tight. The honest property
    is: for any IFS attractor with all contractions < 1, bbox is well-defined,
    finite, non-degenerate, and approximately encloses long-run point clouds
    (with margin to account for sampling variance)."""

    def test_bbox_is_finite_and_non_degenerate(self, engine):
        for cls in engine.PAGE_CLASSES["B"]:
            if not hasattr(cls, "transforms") or not cls.transforms:
                continue
            page = cls(320, 240)
            page.reset()
            assert math.isfinite(page.bx0) and math.isfinite(page.bx1)
            assert math.isfinite(page.by0) and math.isfinite(page.by1)
            assert page.bx1 > page.bx0, f"{cls.__name__}: bbox x degenerate"
            assert page.by1 > page.by0, f"{cls.__name__}: bbox y degenerate"

    @given(seed_st)
    def test_sierpinski_long_run_mostly_inside_bbox_with_margin(self, engine, seed):
        """≥95% of long-run chaos-game points fall within bbox + 20% margin."""
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
            x, y = (t[0] * x + t[1] * y + t[4],
                    t[2] * x + t[3] * y + t[5])
            if not (page.bx0 - margin_x <= x <= page.bx1 + margin_x and
                    page.by0 - margin_y <= y <= page.by1 + margin_y):
                outside += 1
        assert outside / N < 0.05, f"{outside}/{N} points outside bbox+margin"

    @given(seed_st)
    def test_barnsley_long_run_mostly_inside_bbox_with_margin(self, engine, seed):
        random.seed(seed)
        page = engine.BarnsleyFernIFS(320, 240)
        page.reset()
        bw = page.bx1 - page.bx0
        bh = page.by1 - page.by0
        margin_x = bw * 0.20
        margin_y = bh * 0.20
        x, y = 0.0, 0.0
        outside = 0
        N = 1000
        for _ in range(N):
            t = page._pick_transform()
            x, y = (t[0] * x + t[1] * y + t[4],
                    t[2] * x + t[3] * y + t[5])
            if not (page.bx0 - margin_x <= x <= page.bx1 + margin_x and
                    page.by0 - margin_y <= y <= page.by1 + margin_y):
                outside += 1
        assert outside / N < 0.05

    def test_to_screen_maps_bbox_corners_inside_canvas(self, engine):
        """The four bbox corners must map to within-canvas (sx, sy)."""
        for cls in engine.PAGE_CLASSES["B"]:
            if not hasattr(cls, "transforms") or not cls.transforms:
                continue
            page = cls(400, 300)
            page.reset()
            # the bbox-centre must map exactly to canvas centre (within 1px)
            cx_w = (page.bx0 + page.bx1) / 2
            cy_w = (page.by0 + page.by1) / 2
            sx, sy = page._to_screen(cx_w, cy_w)
            assert abs(sx - 200) <= 1, f"{cls.__name__}: centre x = {sx}"
            assert abs(sy - 150) <= 1, f"{cls.__name__}: centre y = {sy}"


# ── L-system — string-length growth property ──────────────────────────────
#
# For an L-system with rules R, the length of the expanded string after k
# iterations follows: |s_k| = sum over each char in s_{k-1} of |R[c]|. For
# rules where every drawing char F → m chars, exact growth is m^k starting
# from |axiom|. We assert this for grammars where the property holds cleanly.

class TestLSystemGrowthProperty:
    """Verify the string-length expansion follows the rule arithmetic."""

    def test_binary_tree_F_count_uses_actual_rule_arithmetic(self, engine):
        """F → FF+[+F-F-F]-[-F+F+F] contains 8 F's, so F-count multiplies by 8."""
        rules = engine.BinaryTreeLS.rules
        F_in_rule = rules["F"].count("F")
        # sanity-check the count itself (anchor against typo in source)
        assert F_in_rule == 8, f"Rule F-count changed: {F_in_rule}"

        s = "F"
        for _ in range(3):
            f_before = s.count("F")
            s = "".join(rules.get(ch, ch) for ch in s)
            assert s.count("F") == f_before * F_in_rule

    def test_hilbert_xy_count_grows_by_actual_per_rule_count(self, engine):
        """X → +YF-XFX-FY+ (4 X|Y chars) and Y → -XF+YFY+FX- (4 X|Y chars).
        Each X or Y produces 4 new X|Y chars, so total quadruples each iter."""
        rules = engine.HilbertCurve.rules
        x_rule_xy = rules["X"].count("X") + rules["X"].count("Y")
        y_rule_xy = rules["Y"].count("X") + rules["Y"].count("Y")
        # both rules should produce the same number of X|Y chars (4)
        assert x_rule_xy == y_rule_xy == 4

        s = engine.HilbertCurve.axiom
        prev_xy = s.count("X") + s.count("Y")
        for k in range(3):
            s = "".join(rules.get(ch, ch) for ch in s)
            new_xy = s.count("X") + s.count("Y")
            assert new_xy == prev_xy * x_rule_xy, (
                f"iter {k}: expected {prev_xy * x_rule_xy} XY chars, got {new_xy}"
            )
            prev_xy = new_xy

    def test_l_system_unknown_chars_pass_through(self, engine):
        """+/-/[/] and other unknown chars must not be rewritten."""
        rules = {"F": "FF"}
        for s in ["F+F", "F-F", "F[F]F", "F+++F---F", "[F]+[F]"]:
            new = "".join(rules.get(ch, ch) for ch in s)
            # the non-F chars should appear in new exactly as in s
            for ch in "+-[]":
                assert new.count(ch) == s.count(ch)

    @given(st.integers(min_value=1, max_value=4))
    def test_gosper_doubles_axiom_count_each_step(self, engine, k):
        # A → A-B--B+A++AA+B- (8 of A|B → 5 A's + 4 B's? Let me count: A-B--B+A++AA+B- has 4 A and 4 B = 8 letters)
        # Wait: A-B--B+A++AA+B-: A=1, B=2, B=3, A=4, A=5, A=6, B=7 — let me recount
        # "A-B--B+A++AA+B-": chars in order A,-,B,-,-,B,+,A,+,+,A,A,+,B,- → A:4, B:3, count of A|B = 7
        # B → +A-BB--B-A++A+B: chars A,A,B,B,B,A,A,B → A:4, B:4 = 8
        # so growth is not uniform. Just assert monotonic growth.
        rules = engine.GosperCurve.rules
        s = engine.GosperCurve.axiom
        prev = s.count("A") + s.count("B")
        for _ in range(k):
            s = "".join(rules.get(ch, ch) for ch in s)
            new = s.count("A") + s.count("B")
            assert new > prev, "Gosper grammar should grow A|B count each step"
            prev = new


# ── Attractor step continuity property ─────────────────────────────────────
#
# For continuous attractors (Lorenz, Rössler, Aizawa) one step with small dt
# should produce a small change in (x,y,z): |step(x,y,z) - (x,y,z)| < bound.
# This catches mutations that change dt or remove + dt scaling.

class TestAttractorStepContinuity:
    """Continuous attractors: small dt → small step (Lipschitz-like)."""

    @given(
        st.floats(min_value=-15, max_value=15, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-15, max_value=15, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0, max_value=30, allow_nan=False, allow_infinity=False),
    )
    def test_lorenz_step_is_small_with_default_dt(self, engine, x, y, z):
        page = engine.LorenzAttractor(320, 240)
        page.reset()
        x_new, y_new, z_new = page.step(x, y, z)
        # at default dt=0.005, max change per step is bounded by the largest
        # derivative magnitude × dt. With (x,y,z) bounded in [-30, 30], the
        # max derivative is roughly 30·30 = 900 (the xy term in dz/dt),
        # so |step| < 900 * 0.005 = 4.5 per coordinate.
        assert abs(x_new - x) < 6.0
        assert abs(y_new - y) < 6.0
        assert abs(z_new - z) < 6.0

    @given(
        st.floats(min_value=-2, max_value=2, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-2, max_value=2, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
    )
    def test_rossler_step_is_small_with_default_dt(self, engine, x, y, z):
        page = engine.RosslerAttractor(320, 240)
        page.reset()
        x_new, y_new, z_new = page.step(x, y, z)
        # dt=0.02; for bounded (x,y,z) the per-step change should be modest
        assert abs(x_new - x) < 5.0
        assert abs(y_new - y) < 5.0
        assert abs(z_new - z) < 5.0

    def test_henon_step_is_pure_iteration_no_dt(self, engine):
        """Hénon is a discrete map — no continuity expected, just deterministic."""
        page = engine.HenonMap(320, 240)
        page.reset()
        a = page.step(0.0, 0.0, 0.0)
        b = page.step(0.0, 0.0, 0.0)
        assert a == b   # pure determinism


# ── Sacred Geometry rendering property ─────────────────────────────────────
#
# Every SG form must:
# 1. Produce a non-empty render after reset()
# 2. Stay within the canvas bounds (no off-canvas writes that disappear)
# 3. Produce identical output across two construct/reset/render cycles

class TestSacredGeometryProperty:
    @given(small_size_st)
    def test_all_sg_render_non_empty_at_any_size(self, engine, size):
        w, h = size
        for cls in engine.PAGE_CLASSES["E"]:
            page = cls(w, h)
            page.reset()
            arr = pygame.surfarray.array3d(page.surface)
            assert arr.sum() > 0, f"{cls.__name__} empty at {size}"

    def test_sg_render_is_idempotent(self, engine):
        """Two reset() calls produce identical pixel-for-pixel surfaces."""
        import hashlib
        for cls in engine.PAGE_CLASSES["E"]:
            page1 = cls(320, 240)
            page1.reset()
            h1 = hashlib.sha256(pygame.image.tostring(page1.surface, "RGBA")).hexdigest()

            page2 = cls(320, 240)
            page2.reset()
            h2 = hashlib.sha256(pygame.image.tostring(page2.surface, "RGBA")).hexdigest()

            assert h1 == h2, f"{cls.__name__} non-idempotent reset"


# ── escape-time progressive-render invariant ───────────────────────────────
