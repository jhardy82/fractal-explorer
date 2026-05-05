"""
test_defaults_and_properties.py — anchor + sentinel tests for every default
parameter and module-level constant in mutation_target.py.

Pattern (per test-engineering skill §§ default-parameter mutation):
    anchor  — assert the constant equals a specific known value
    sentinel — assert that the function produces a DIFFERENT output
               when the constant would be different

This file lifts mutation kill rate by catching literal-replacement mutants
that the behavioural tests in test_mutation_target.py don't directly cover.
"""
from __future__ import annotations

import math

import pytest

from mutation_target import (
    ESCAPE_RADIUS_SQ,
    HENON_A,
    HENON_B,
    LORENZ_BETA,
    LORENZ_DT,
    LORENZ_RHO,
    LORENZ_SIGMA,
    henon_step,
    julia_iter,
    lorenz_step,
    mandelbrot_iter,
    smooth_colour,
    to_screen,
)


# ── ESCAPE_RADIUS_SQ = 4.0 ─────────────────────────────────────────────────

class TestEscapeRadiusSq:
    def test_anchor_value(self):
        assert ESCAPE_RADIUS_SQ == pytest.approx(4.0)

    def test_point_just_inside_does_not_escape_immediately(self):
        # c = (1.99, 0): |c|² = 3.96 < 4 → z₁ = c, not yet escaped at iter 0
        # if threshold were 3.9, it would still survive (3.96 > 3.9 would catch it)
        # Actually: we check |z|², and z₀=(0,0): 0 < 4 → passes. After update z₁=(1.99,0).
        # At iter 1: 1.99²=3.96 < 4.0 → not escaped. With threshold=5: same result.
        # Better: a point whose |z|² lands exactly between 3 and 4 at some iteration.
        # c=(0,1.95): z₀=(0,0), z₁=(0,1.95), |z₁|²=3.8025 < 4. Not escaped.
        result = mandelbrot_iter(0.0, 1.95, 10)
        assert result > 1    # survived iteration 1 (|z|²≈3.8 < 4)

    def test_point_just_outside_escapes(self):
        # c=(0, 2.1): z₁=(0, 2.1), |z₁|²=4.41 > 4 → escaped at iter 1
        result = mandelbrot_iter(0.0, 2.1, 100)
        assert result == 1

    def test_threshold_is_4_not_3(self):
        # c=(0, 1.8): |c|²=3.24 < 3.0 and < 4.0 → if threshold were 3, it'd escape
        # With threshold=4, z₁=(0,1.8): 3.24 < 4 → doesn't escape at iter 1
        result = mandelbrot_iter(0.0, 1.8, 10)
        assert result > 1     # if threshold were 3, result would be 1

    def test_threshold_is_4_not_5(self):
        # c=(0, 2.1): z₁ has |z₁|²=4.41, escapes at iter 1 with threshold=4
        # With threshold=5: 4.41 < 5 → would NOT escape at iter 1
        result = mandelbrot_iter(0.0, 2.1, 100)
        assert result == 1    # if threshold were 5, result would be > 1


# ── LORENZ_SIGMA = 10.0 ────────────────────────────────────────────────────

class TestLorenzSigma:
    def test_anchor_value(self):
        assert LORENZ_SIGMA == pytest.approx(10.0)

    def test_sigma_drives_x_derivative(self):
        # dx = σ*(y-x); with x=0, y=1: dx=σ*1=10 → x += 10*dt = 0.05
        x, _, _ = lorenz_step(0.0, 1.0, 0.0)
        assert x == pytest.approx(0.05)           # kills σ→9 (would give 0.045)

    def test_sigma_sentinel_different_from_9(self):
        x, _, _ = lorenz_step(0.0, 1.0, 0.0)
        assert x != pytest.approx(0.045)          # σ=9 would give 0.045


# ── LORENZ_RHO = 28.0 ──────────────────────────────────────────────────────

class TestLorenzRho:
    def test_anchor_value(self):
        assert LORENZ_RHO == pytest.approx(28.0)

    def test_rho_drives_y_derivative(self):
        # dy = x*(ρ-z) - y; with x=1, y=0, z=0: dy=1*(28-0)-0=28 → y += 28*dt = 0.14
        _, y, _ = lorenz_step(1.0, 0.0, 0.0)
        assert y == pytest.approx(0.14)           # kills ρ→27 (would give 0.135)

    def test_rho_sentinel_different_from_27(self):
        _, y, _ = lorenz_step(1.0, 0.0, 0.0)
        assert y != pytest.approx(0.135)          # ρ=27 would give 0.135


# ── LORENZ_BETA = 8/3 ──────────────────────────────────────────────────────

class TestLorenzBeta:
    def test_anchor_value(self):
        assert LORENZ_BETA == pytest.approx(8.0 / 3.0)

    def test_beta_drives_z_derivative(self):
        # dz = x*y - β*z; with x=0, y=0, z=1: dz = -β*1 = -8/3
        # z += (-8/3)*0.005
        _, _, z = lorenz_step(0.0, 0.0, 1.0)
        expected = 1.0 - (8.0 / 3.0) * 0.005
        assert z == pytest.approx(expected)

    def test_beta_sentinel_not_3(self):
        _, _, z = lorenz_step(0.0, 0.0, 1.0)
        wrong = 1.0 - 3.0 * 0.005      # β=3 instead of 8/3
        assert z != pytest.approx(wrong)


# ── LORENZ_DT = 0.005 ──────────────────────────────────────────────────────

class TestLorenzDt:
    def test_anchor_value(self):
        assert LORENZ_DT == pytest.approx(0.005)

    def test_dt_scales_the_step(self):
        # x=0, y=1, z=0 → dx=10; x += 10*dt = 10*0.005 = 0.05
        x, _, _ = lorenz_step(0.0, 1.0, 0.0)
        assert x == pytest.approx(0.05)

    def test_dt_sentinel_not_0_01(self):
        # if dt were 0.01, x would be 0.10
        x, _, _ = lorenz_step(0.0, 1.0, 0.0)
        assert x != pytest.approx(0.10)


# ── HENON_A = 1.4 ──────────────────────────────────────────────────────────

class TestHenonA:
    def test_anchor_value(self):
        assert HENON_A == pytest.approx(1.4)

    def test_a_drives_quadratic_term(self):
        # henon_step(1, 0): x' = 1 - A*1² + 0 = 1 - 1.4 = -0.4
        x, _ = henon_step(1.0, 0.0)
        assert x == pytest.approx(-0.4)           # kills A→1.5 (would give -0.5)

    def test_a_sentinel_not_1_5(self):
        x, _ = henon_step(1.0, 0.0)
        assert x != pytest.approx(-0.5)           # A=1.5 would give -0.5


# ── HENON_B = 0.3 ──────────────────────────────────────────────────────────

class TestHenonB:
    def test_anchor_value(self):
        assert HENON_B == pytest.approx(0.3)

    def test_b_drives_contraction(self):
        # henon_step(1, 0): y' = B*x = 0.3*1 = 0.3
        _, y = henon_step(1.0, 0.0)
        assert y == pytest.approx(0.3)            # kills B→0.4 (would give 0.4)

    def test_b_sentinel_not_0_4(self):
        _, y = henon_step(1.0, 0.0)
        assert y != pytest.approx(0.4)


# ── mandelbrot_iter default max_iter=256 ────────────────────────────────────

class TestMandelbrotDefaultMaxIter:
    def test_anchor_interior_returns_256(self):
        # origin is interior; no explicit max_iter → should return 256
        assert mandelbrot_iter(0.0, 0.0) == 256

    def test_anchor_matches_explicit_256(self):
        assert mandelbrot_iter(0.0, 0.0) == mandelbrot_iter(0.0, 0.0, 256)

    def test_sentinel_differs_from_100(self):
        assert mandelbrot_iter(0.0, 0.0) != mandelbrot_iter(0.0, 0.0, 100)


# ── julia_iter default max_iter=256 ────────────────────────────────────────

class TestJuliaDefaultMaxIter:
    def test_anchor_interior_returns_256(self):
        assert julia_iter(0.0, 0.0, 0.0, 0.0) == 256

    def test_anchor_matches_explicit_256(self):
        assert julia_iter(0.0, 0.0, 0.0, 0.0) == julia_iter(0.0, 0.0, 0.0, 0.0, 256)

    def test_sentinel_differs_from_100(self):
        assert julia_iter(0.0, 0.0, 0.0, 0.0) != julia_iter(0.0, 0.0, 0.0, 0.0, 100)


# ── smooth_colour: formula constant log(2) normalisation ───────────────────

class TestSmoothColourFormula:
    def test_exact_log2_normalisation_at_threshold(self):
        # At |z|²=4 exactly (zx=2, zy=0):
        # log_zn = log(4)/2 = log(2), nu = log(log(2)/log(2))/log(2) = log(1)/log(2) = 0
        # result = iter + 1 - 0 = iter + 1
        result = smooth_colour(5, 2.0, 0.0, 100)
        assert result == pytest.approx(6.0, abs=1e-6)

    def test_interior_always_zero(self):
        for iter_val in [0, 50, 99, 100]:
            assert smooth_colour(iter_val, 1.5, 0.0, 100) == pytest.approx(
                0.0 if iter_val >= 100 else smooth_colour(iter_val, 1.5, 0.0, 100)
            )
        # explicit interior check
        assert smooth_colour(100, 0.5, 0.0, 100) == pytest.approx(0.0)

    def test_division_by_log2_not_log10(self):
        # If formula used log10 instead of log2, nu would differ significantly
        # log(log_zn / log10(2)) / log10(2) vs log(log_zn / log(2)) / log(2)
        # We anchor against the log2 value for a specific point
        zx, zy = 3.0, 0.0
        log_zn = math.log(zx * zx + zy * zy) / 2.0
        nu_expected = math.log(log_zn / math.log(2.0)) / math.log(2.0)
        expected = 5 + 1.0 - nu_expected
        assert smooth_colour(5, zx, zy, 100) == pytest.approx(expected)


# ── to_screen: 0.9 margin constant ─────────────────────────────────────────

class TestToScreenMargin:
    def test_90_percent_margin(self):
        # With bbox=(0,1,0,1), canvas=100×100:
        # scale = min(100, 100) * 0.9 = 90
        # corner (0,0) → sx = (0-0.5)*90 + 50 = -45+50 = 5
        #               → sy = -(0-0.5)*90 + 50 = 45+50 = 95
        sx, sy = to_screen(0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 100, 100)
        assert sx == 5
        assert sy == 95

    def test_margin_sentinel_not_1_0(self):
        # If margin were 1.0 (no padding), corner maps to exact edge: sx=0
        sx, _ = to_screen(0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 100, 100)
        assert sx != 0   # with 0.9 margin, should be 5, not 0
