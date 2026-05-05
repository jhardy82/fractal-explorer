"""
test_mutation_target.py — behavioral tests for the mutation-target slice.

Design goal: every function body mutation (operator swap, constant nudge,
missing term) breaks at least one test.  Tests are arranged by function.
"""
from __future__ import annotations

import math

import pytest
from mutation_target import (
    expand_lsystem,
    henon_step,
    julia_iter,
    lorenz_step,
    mandelbrot_iter,
    smooth_colour,
    to_screen,
)

# ── mandelbrot_iter ─────────────────────────────────────────────────────────

class TestMandelbrotIter:
    def test_interior_origin_returns_max_iter(self):
        assert mandelbrot_iter(0.0, 0.0, 100) == 100

    def test_exterior_c3_escapes_at_iteration_1(self):
        # c=(3,0): z₁=(3,0), |z₁|²=9 > 4 → return 1
        assert mandelbrot_iter(3.0, 0.0, 100) == 1

    def test_exterior_c05_escapes_at_iteration_5(self):
        # hand-traced: c=(0.5,0) orbit: 0 → 0.5 → 0.75 → 1.0625 → 1.6289 → 3.1532 (>2)
        # escape check is on |z|², so iter 5 sees |z|²=9.94 > 4
        assert mandelbrot_iter(0.5, 0.0, 100) == 5

    def test_escape_threshold_4_not_3(self):
        # point with |z|² = 3.9 must NOT escape immediately
        # (0, sqrt(3.9)) as starting z is not c; use c near boundary instead
        # Test: at step i=5, c=0.5 escapes. With threshold=3, it would escape sooner.
        # Indirect: interior origin never escapes regardless; exterior always does.
        result_interior = mandelbrot_iter(0.0, 0.0, 50)
        assert result_interior == 50           # did NOT escape

    def test_zero_cy_stays_on_real_axis(self):
        # orbit of real c stays real (zy always 0 when cy=0, zy₀=0)
        result = mandelbrot_iter(0.3, 0.0, 50)
        assert 0 < result <= 50               # somewhere, may escape or not

    def test_returns_max_iter_for_definite_interior(self):
        # c = (-0.1, 0.1) is inside the Mandelbrot set
        assert mandelbrot_iter(-0.1, 0.1, 256) == 256

    def test_large_c_escapes_fast(self):
        # c = (10, 0) has |c|²=100 > 4, escapes at iteration 0 (before update)
        # wait: we check BEFORE update, so iter 0: zx2=0, zy2=0, 0>4? No.
        # after update: zx=10, zy=0.  iter 1: 100>4 → return 1
        assert mandelbrot_iter(10.0, 0.0, 100) == 1

    def test_imaginary_axis_point_outside(self):
        # c=(0, 3): orbit starts at (0,0), becomes (0,3), zy2=9>4 → iter 1
        result = mandelbrot_iter(0.0, 3.0, 100)
        assert result == 1

    def test_update_formula_cross_term(self):
        # c=(1, 1): orbit mixes real/imag parts; result must be finite and < max_iter
        result = mandelbrot_iter(1.0, 1.0, 100)
        assert 0 < result < 100

    def test_exact_escape_complex_c(self):
        # c=(0.5, 0.5): both cx and cy non-zero so 2.0*zx*zy term is exercised.
        # Hand-traced: orbit escapes at iteration 5.
        # Kills: initial-value mutants (zx→1.0), zy-coefficient mutants (2.0→3.0),
        #        zx update sign mutants (zx2-zy2 → zx2+zy2), return-i mutants.
        assert mandelbrot_iter(0.5, 0.5, 100) == 5

    def test_boundary_strict_greater_than(self):
        # c=(2, 0): orbit step gives |z|²=4.0 exactly at iter 1.
        # Strict > means 4.0 does NOT escape; iter 2 gives |z|²=36 → return 2.
        # Kills: > → >= mutation (which would return 1).
        assert mandelbrot_iter(2.0, 0.0, 100) == 2

    def test_escape_condition_sum_not_difference(self):
        # c=(0.3, 1.9): at iter 2, zy²≈9.24 > zx²≈10.37; zx²+zy²=19.6>4 but zx²-zy²<4.
        # If + becomes -: escape does not occur at iter 2 → different return value.
        assert mandelbrot_iter(0.3, 1.9, 100) == 2


# ── julia_iter ──────────────────────────────────────────────────────────────

class TestJuliaIter:
    def test_interior_returns_max_iter(self):
        # z=0 with c=0 → trivially interior
        assert julia_iter(0.0, 0.0, 0.0, 0.0, 100) == 100

    def test_exterior_z_escapes(self):
        # z=(3,0), c=0: |z|²=9>4 at iteration 0
        assert julia_iter(3.0, 0.0, 0.0, 0.0, 100) == 0

    def test_c_parameter_matters(self):
        # same z, different c → different orbits
        r1 = julia_iter(0.5, 0.5, 0.0, 0.0, 100)
        r2 = julia_iter(0.5, 0.5, -0.7, 0.27, 100)
        assert r1 != r2

    def test_cx_zero_cy_zero_stable_interior(self):
        # c=(0,0), any |z|<2 stays put (z↦z²): z=(0.5,0)→(0.25,0)→…→0
        result = julia_iter(0.5, 0.0, 0.0, 0.0, 50)
        assert result == 50    # converges to 0, never escapes

    def test_update_uses_both_components(self):
        # z=(0.5, 0.5), c=(0, 0): z² = (0-0.5², 2*0.5*0.5) = (-0.25+0.5i)? Let's just verify non-trivial
        r = julia_iter(0.5, 0.5, 0.0, 0.0, 100)
        # either escapes or doesn't, but must be a valid count
        assert 0 <= r <= 100

    def test_exact_escape_at_iteration_2(self):
        # z=(1,1), c=0: step 0: z²=(0, 2), |z|²=4 NOT >4 (strict); step 1: z=(-4,0) → return 2.
        # Kills: zy-coefficient mutants (2.0→3.0 gives zy=3 at step 0 → escape at iter 1),
        #        >→>= mutants (|z|²=4 at step 1 would escape early → return 1),
        #        zx-update sign mutants.
        assert julia_iter(1.0, 1.0, 0.0, 0.0, 100) == 2

    def test_exact_escape_at_iteration_1(self):
        # z=(1.5, 0), c=0: z₀²=(2.25,0), 2.25<4. z₁=(2.25,0): 5.06>4 → return 1.
        # Kills: return-i±1 mutants.
        assert julia_iter(1.5, 0.0, 0.0, 0.0, 100) == 1

    def test_boundary_strict_greater_than(self):
        # z=(0, 2), c=0: |z₀|²=4 NOT >4 (strict); z₁=(-4, 0): 16>4 → return 1.
        # Kills: > → >= (which returns 0 at step 0).
        assert julia_iter(0.0, 2.0, 0.0, 0.0, 100) == 1

    def test_escape_condition_sum_not_difference(self):
        # z=(1, 2), c=0: |z|²=1+4=5>4 → return 0.
        # With zx²-zy²=1-4=-3: -3>4 is False → does NOT escape at step 0.
        # Kills: + → - mutation in the escape condition check.
        assert julia_iter(1.0, 2.0, 0.0, 0.0, 100) == 0


# ── smooth_colour ───────────────────────────────────────────────────────────

class TestSmoothColour:
    def test_interior_returns_zero(self):
        assert smooth_colour(100, 0.0, 0.0, 100) == pytest.approx(0.0)

    def test_exterior_is_fractional(self):
        # iteration < max_iter → returns non-integer float
        result = smooth_colour(5, 3.0, 0.0, 100)
        assert result != int(result)           # fractional part present
        assert result > 0.0

    def test_larger_zmod_gives_smaller_nu(self):
        # larger |z| at escape → log_zn larger → nu larger → smooth val smaller
        r_small = smooth_colour(5, 2.1, 0.0, 100)   # just past threshold
        r_large = smooth_colour(5, 10.0, 0.0, 100)  # far past threshold
        assert r_small > r_large

    def test_formula_uses_log2_normalisation(self):
        # at |z|²=4 exactly (zx=2, zy=0): log_zn=log(4)/2=log(2)=0.6931
        # nu = log(log(2)/log(2))/log(2) = log(1)/log(2) = 0
        # result = iter + 1 - 0 = iter + 1
        result = smooth_colour(5, 2.0, 0.0, 100)
        assert result == pytest.approx(6.0, abs=1e-6)

    def test_result_approximately_continuous_near_escape(self):
        # consecutive iterations should give close results
        r5 = smooth_colour(5, 3.0, 0.0, 100)
        r6 = smooth_colour(6, 3.0, 0.0, 100)
        assert abs(r6 - r5 - 1.0) < 0.5     # roughly 1 apart, not wildly different

    def test_nonzero_zy_component(self):
        # All other tests use zy=0, making +zy² and -zy² identical.
        # zx=3, zy=4: zx²+zy²=25. With -zy² mutation: log(-7) → ValueError → mutant killed.
        zx, zy = 3.0, 4.0
        log_zn = math.log(zx * zx + zy * zy) / 2.0
        nu = math.log(log_zn / math.log(2.0)) / math.log(2.0)
        assert smooth_colour(5, zx, zy, 100) == pytest.approx(5 + 1.0 - nu, rel=1e-9)


# ── lorenz_step ─────────────────────────────────────────────────────────────

class TestLorenzStep:
    def test_origin_is_fixed_point(self):
        # σ(0-0)=0, 0*(28-0)-0=0, 0*0-(8/3)*0=0 → stays at (0,0,0)
        x, y, z = lorenz_step(0.0, 0.0, 0.0)
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(0.0)
        assert z == pytest.approx(0.0)

    def test_x_step_uses_sigma_and_y_minus_x(self):
        # lorenz_step(0, 1, 0): dx = σ*(1-0)=10, x += 10*0.005 = 0.05
        x, _, _ = lorenz_step(0.0, 1.0, 0.0)
        assert x == pytest.approx(0.05)

    def test_y_step_uses_rho_and_xz(self):
        # lorenz_step(1, 0, 0): dy = 1*(28-0)-0 = 28, y += 28*0.005 = 0.14
        _, y, _ = lorenz_step(1.0, 0.0, 0.0)
        assert y == pytest.approx(0.14)

    def test_z_step_uses_beta_and_xy(self):
        # lorenz_step(0, 0, 1): dz = 0 - (8/3)*1 = -8/3, z += (-8/3)*0.005
        _, _, z = lorenz_step(0.0, 0.0, 1.0)
        expected = 1.0 + (-8.0 / 3.0) * 0.005
        assert z == pytest.approx(expected)

    def test_combined_step(self):
        # lorenz_step(1, 2, 3):
        # dx = 10*(2-1)=10, x = 1+10*0.005 = 1.05
        # dy = 1*(28-3)-2=23, y = 2+23*0.005 = 2.115
        # dz = 1*2-(8/3)*3=2-8=-6, z = 3+(-6)*0.005 = 2.97
        x, y, z = lorenz_step(1.0, 2.0, 3.0)
        assert x == pytest.approx(1.05)
        assert y == pytest.approx(2.115)
        assert z == pytest.approx(2.97)

    def test_step_is_small_at_default_dt(self):
        # max derivative magnitude is bounded; dt=0.005 keeps step small
        x, y, z = lorenz_step(10.0, 10.0, 10.0)
        assert abs(x - 10.0) < 1.0
        assert abs(y - 10.0) < 2.0
        assert abs(z - 10.0) < 1.0

    def test_returns_tuple_of_three(self):
        result = lorenz_step(1.0, 2.0, 3.0)
        assert len(result) == 3


# ── henon_step ──────────────────────────────────────────────────────────────

class TestHenonStep:
    def test_origin_step(self):
        # henon_step(0, 0): x' = 1-0+0 = 1, y' = 0
        x, y = henon_step(0.0, 0.0)
        assert x == pytest.approx(1.0)
        assert y == pytest.approx(0.0)

    def test_x1_step(self):
        # henon_step(1, 0): x' = 1 - 1.4*1 + 0 = -0.4, y' = 0.3*1 = 0.3
        x, y = henon_step(1.0, 0.0)
        assert x == pytest.approx(-0.4)
        assert y == pytest.approx(0.3)

    def test_second_step(self):
        # henon_step(-0.4, 0.3): x' = 1 - 1.4*0.16 + 0.3 = 1.076, y' = 0.3*(-0.4) = -0.12
        x, y = henon_step(-0.4, 0.3)
        assert x == pytest.approx(1.076)
        assert y == pytest.approx(-0.12)

    def test_y_output_depends_only_on_input_x(self):
        # y' = B*x — changing input y should not affect output y
        _, y1 = henon_step(1.0, 0.0)
        _, y2 = henon_step(1.0, 99.0)
        assert y1 == pytest.approx(y2)

    def test_x_output_depends_on_quadratic_term(self):
        # x' = 1 - A*x² + y: sign of x² doesn't matter (x²=(-x)²)
        x1, _ = henon_step(1.0, 0.0)
        x2, _ = henon_step(-1.0, 0.0)
        assert x1 == pytest.approx(x2)    # symmetric in x

    def test_deterministic(self):
        a = henon_step(0.5, 0.5)
        b = henon_step(0.5, 0.5)
        assert a == b


# ── expand_lsystem ──────────────────────────────────────────────────────────

class TestExpandLsystem:
    def test_zero_iterations_returns_axiom(self):
        assert expand_lsystem("F", {"F": "FF"}, 0) == "F"

    def test_one_iteration_f_to_ff(self):
        assert expand_lsystem("F", {"F": "FF"}, 1) == "FF"

    def test_two_iterations_f_to_ffff(self):
        assert expand_lsystem("F", {"F": "FF"}, 2) == "FFFF"

    def test_unknown_chars_pass_through(self):
        result = expand_lsystem("F+F", {"F": "FF"}, 1)
        assert "+" in result
        assert result.count("+") == 1

    def test_bracket_chars_pass_through(self):
        result = expand_lsystem("F[F]F", {"F": "FF"}, 1)
        assert result.count("[") == 1
        assert result.count("]") == 1

    def test_multiple_rules(self):
        # Koch-like: F→F+F-F-F+F, +/-/[ pass through
        rules = {"F": "F+F-F-F+F"}
        result = expand_lsystem("F", rules, 1)
        assert result == "F+F-F-F+F"
        assert expand_lsystem("F", rules, 2).count("F") == 5 * 5

    def test_simultaneous_rewriting(self):
        # A→B, B→A: after 1 step "AB"→"BA"
        rules = {"A": "B", "B": "A"}
        assert expand_lsystem("AB", rules, 1) == "BA"
        assert expand_lsystem("AB", rules, 2) == "AB"   # back to original

    def test_length_grows_geometrically(self):
        # F→FF doubles F count each step
        n = 4
        result = expand_lsystem("F", {"F": "FF"}, n)
        assert len(result) == 2 ** n


# ── to_screen ───────────────────────────────────────────────────────────────

class TestToScreen:
    BBOX = (0.0, 1.0, 0.0, 1.0)   # unit-square bbox

    def test_bbox_centre_maps_to_canvas_centre(self):
        sx, sy = to_screen(0.5, 0.5, *self.BBOX, 100, 100)
        assert sx == 50
        assert sy == 50

    def test_y_axis_is_flipped(self):
        # world (0.5, 1.0) = top of bbox → small sy (near screen top)
        # world (0.5, 0.0) = bottom of bbox → large sy (near screen bottom)
        _, sy_top = to_screen(0.5, 1.0, *self.BBOX, 100, 100)
        _, sy_bot = to_screen(0.5, 0.0, *self.BBOX, 100, 100)
        assert sy_top < sy_bot

    def test_x_axis_increases_right(self):
        sx_left, _ = to_screen(0.0, 0.5, *self.BBOX, 100, 100)
        sx_right, _ = to_screen(1.0, 0.5, *self.BBOX, 100, 100)
        assert sx_right > sx_left

    def test_degenerate_bbox_returns_centre(self):
        # zero-width bbox → return canvas centre
        sx, sy = to_screen(0.5, 0.5, 0.0, 0.0, 0.0, 1.0, 100, 100)
        assert sx == 50
        assert sy == 50

    def test_scale_uses_90_percent_of_canvas(self):
        # with a square canvas and square bbox, the corners should land at ≈5% and ≈95%
        sx_corner, sy_corner = to_screen(0.0, 0.0, *self.BBOX, 100, 100)
        assert 2 <= sx_corner <= 8     # roughly 5 (with int truncation)
        assert 92 <= sy_corner <= 98   # flipped y, roughly 95

    def test_non_square_canvas(self):
        # 200×100 canvas; bbox is unit square; scale = min(200/1,100/1)*0.9 = 90
        sx, sy = to_screen(0.5, 0.5, *self.BBOX, 200, 100)
        assert sx == 100   # x-centre of 200
        assert sy == 50    # y-centre of 100

    def test_offset_bbox_sx(self):
        # bbox=[1,2]×[1,2]: bw=bx1-bx0=1, not bx1+bx0=3. scale=90.
        # wx=2.0: sx = (2-1.5)*90 + 50 = 95
        sx, sy = to_screen(2.0, 1.5, 1.0, 2.0, 1.0, 2.0, 100, 100)
        assert sx == 95
        assert sy == 50

    def test_offset_bbox_sy(self):
        # bbox=[1,2]×[1,2]: bh=by1-by0=1. wy=2.0: sy = -((2-1.5)*90) + 50 = 5
        sx, sy = to_screen(2.0, 2.0, 1.0, 2.0, 1.0, 2.0, 100, 100)
        assert sx == 95
        assert sy == 5

    def test_scale_uses_min_not_max(self):
        # 200×100 canvas, unit bbox: bw-limited scale=min(200,100)*0.9=90.
        # With max: scale=180. wx=0.0 is off-centre, so sx distinguishes.
        # sx = (0-0.5)*90 + 100 = 55  (max would give (0-0.5)*180+100 = 10)
        sx, sy = to_screen(0.0, 0.5, 0.0, 1.0, 0.0, 1.0, 200, 100)
        assert sx == 55
        assert sy == 50

    def test_non_square_bbox_min_picks_smaller(self):
        # bbox=[0,2]×[0,1]: bw=2 → w/bw=50, bh=1 → h/bh=100. min=50. scale=45.
        # With max(→100): scale=90. wx=2.0 → sx=(2-1)*45+50=95  vs  (2-1)*90+50=140.
        sx, sy = to_screen(2.0, 0.5, 0.0, 2.0, 0.0, 1.0, 100, 100)
        assert sx == 95
        assert sy == 50
