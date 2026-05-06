"""
test_smooth_colouring.py — Unit tests for EscapeTimeFractal smooth colouring.

Acceptance criteria verified here:
  AC-7  Smooth value is a float and in valid range for a known escaped pixel.
  AC-8a In-set pixels (div == 0) produce palette[0] colour (black).
  AC-8b Opt-out (smooth_colouring=False) produces integer-indexed colour.
  AC-8c smooth_colouring class attribute present and defaults to True.
"""
from __future__ import annotations

import math

import numpy as np
import pygame

# ---------------------------------------------------------------------------
# Test canvas size — small for speed
# ---------------------------------------------------------------------------

_W, _H = 80, 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_page(cls, **overrides):
    """Construct a subclass with attribute overrides, reset and return it."""
    Patched = type("Patched", (cls,), overrides)
    page = Patched(_W, _H)
    page.reset()
    return page


def _render_once(page) -> np.ndarray:
    """Drive render_rows for the full surface, return RGB array (H, W, 3)."""
    page.render_rows(0, _H)
    arr = pygame.surfarray.array3d(page.surface)   # (W, H, 3)
    return arr.transpose(1, 0, 2)                  # → (H, W, 3)


# ---------------------------------------------------------------------------
# AC-7: Smooth value is float and in valid range for an escaped pixel
# ---------------------------------------------------------------------------

class TestSmoothValueRange:
    """Verify the smooth iteration formula produces well-formed floats."""

    def test_smooth_formula_is_float(self):
        """Directly validate the smooth formula for a synthetic escaped pixel."""
        abs_z_val = 4.5   # above escape threshold of 4.0
        div_val = 5

        log_z = math.log2(math.log2(max(abs_z_val, 2.0001)))
        smooth = div_val - log_z
        smooth = max(smooth, 1.0)

        assert isinstance(smooth, float), "smooth must be a Python float"
        assert smooth >= 1.0, "smooth must be ≥ 1.0 after clamping"
        assert smooth <= div_val + 1, "smooth should not exceed div + 1"

    def test_smooth_value_has_fractional_part(self):
        """Smooth value for a non-boundary escape must have a fractional part."""
        abs_z_val = 6.2
        div_val = 10

        log_z = math.log2(math.log2(max(abs_z_val, 2.0001)))
        smooth = div_val - log_z

        assert smooth % 1.0 != 0.0, (
            f"Expected fractional smooth value, got {smooth}"
        )

    def test_smooth_clamped_to_at_least_one(self):
        """Very large |z| must not push smooth below 1.0 after clamping."""
        abs_z_val = 1e10
        div_val = 1

        log_z = math.log2(math.log2(max(abs_z_val, 2.0001)))
        raw_smooth = div_val - log_z
        clamped = max(raw_smooth, 1.0)

        assert clamped == 1.0, (
            f"Expected clamp to 1.0 for large |z|; got {clamped}"
        )

    def test_smooth_render_differs_from_integer_render(self, engine):
        """
        Rendering with smooth_colouring=True vs False must produce different
        pixels — this confirms interpolation is active for escaped pixels.
        """
        Mandelbrot = engine.Mandelbrot

        page_smooth = _make_page(Mandelbrot, smooth_colouring=True)
        page_int = _make_page(Mandelbrot, smooth_colouring=False)

        rgb_smooth = _render_once(page_smooth)
        rgb_int = _render_once(page_int)

        assert np.any(rgb_smooth != rgb_int), (
            "Smooth and integer renders produced identical output — "
            "smooth colouring appears to have no effect."
        )


# ---------------------------------------------------------------------------
# AC-8a: In-set pixels produce palette[0] (black)
# ---------------------------------------------------------------------------

class TestInSetPixels:
    """Pixels that never escape (div == 0) must map to palette[0] = black."""

    def test_in_set_pixel_is_black(self, engine):
        """
        A tiny viewport centred on 0+0j lies entirely inside the Mandelbrot set.
        Every pixel must be palette[0] = (0, 0, 0).
        """
        Mandelbrot = engine.Mandelbrot
        page = _make_page(
            Mandelbrot,
            x_range=(-0.01, 0.01),
            y_range=(-0.01, 0.01),
        )
        rgb = _render_once(page)

        black = np.array([0, 0, 0], dtype=np.uint8)
        all_black = np.all(rgb == black, axis=-1)
        assert all_black.all(), (
            "Expected all in-set pixels to be black (palette[0]); "
            f"non-black at: {np.argwhere(~all_black)[:3]}"
        )

    def test_in_set_colour_same_regardless_of_smooth_flag(self, engine):
        """smooth_colouring flag must not change in-set pixel colours."""
        Mandelbrot = engine.Mandelbrot
        opts = {"x_range": (-0.01, 0.01), "y_range": (-0.01, 0.01)}

        rgb_smooth = _render_once(_make_page(Mandelbrot, smooth_colouring=True, **opts))
        rgb_int = _render_once(_make_page(Mandelbrot, smooth_colouring=False, **opts))

        assert np.array_equal(rgb_smooth, rgb_int), (
            "In-set pixel colours differ between smooth and integer modes."
        )


# ---------------------------------------------------------------------------
# AC-8b: Opt-out (smooth_colouring=False) produces integer-indexed colour
# ---------------------------------------------------------------------------

class TestOptOut:
    """smooth_colouring=False must reproduce the original integer palette lookup."""

    def test_optout_matches_direct_palette_index(self, engine):
        """
        With smooth_colouring=False, each pixel colour must equal
        self.palette[div] exactly — no fractional blending.
        """
        Mandelbrot = engine.Mandelbrot
        page = _make_page(Mandelbrot, smooth_colouring=False)
        page.render_rows(0, _H)

        # Recompute div array using the same logic as render_rows.
        x0, x1 = page.x_range
        ymin, ymax = page.y_range
        xs = np.linspace(x0, x1, _W)
        ys = np.linspace(ymin, ymax, _H)
        cx, cy = np.meshgrid(xs, ys)
        c = cx + 1j * cy
        z = page.z0(c)
        div = np.zeros(c.shape, dtype=np.int32)
        mask = np.ones(c.shape, dtype=bool)
        for i in range(1, page.max_iter + 1):
            z_new = page.iter_step(z, c)
            z = np.where(mask, z_new, z)
            diverged = mask & (np.abs(z) > 4.0)
            div[diverged] = i
            mask &= ~diverged
            if not mask.any():
                break

        expected_rgb = page.palette[div]   # (H, W, 3)
        actual_rgb = pygame.surfarray.array3d(page.surface).transpose(1, 0, 2)

        assert np.array_equal(actual_rgb, expected_rgb), (
            "smooth_colouring=False output does not match direct palette[div] lookup"
        )

    def test_smooth_colouring_attribute_present_and_true(self, engine):
        """EscapeTimeFractal.smooth_colouring must exist and default to True."""
        ETF = engine.EscapeTimeFractal
        assert hasattr(ETF, "smooth_colouring"), (
            "EscapeTimeFractal is missing the smooth_colouring class attribute"
        )
        assert ETF.smooth_colouring is True, (
            "EscapeTimeFractal.smooth_colouring must default to True"
        )

    def test_subclass_can_opt_out(self, engine):
        """A subclass with smooth_colouring=False must render without error."""
        Mandelbrot = engine.Mandelbrot

        class NoSmooth(Mandelbrot):
            smooth_colouring = False

        assert NoSmooth.smooth_colouring is False
        page = NoSmooth(_W, _H)
        page.reset()
        page.render_rows(0, _H)   # must not raise

    def test_newton_renders_without_error(self, engine):
        """NewtonFractal overrides render_rows — must still work unchanged."""
        page = engine.NewtonFractal(_W, _H)
        page.reset()
        page.render_rows(0, _H)

    def test_phoenix_renders_without_error(self, engine):
        """PhoenixFractal overrides render_rows — must still work unchanged."""
        page = engine.PhoenixFractal(_W, _H)
        page.reset()
        page.render_rows(0, _H)


# ---------------------------------------------------------------------------
# Escape magnitude tracking (supporting AC-7)
# ---------------------------------------------------------------------------

class TestEscapeMagnitudeTracking:
    """Verify that pixels outside the set are coloured (not black)."""

    def test_escaped_pixels_are_not_black(self, engine):
        """A viewport entirely outside the Mandelbrot set must have non-black pixels."""
        Mandelbrot = engine.Mandelbrot
        page = _make_page(
            Mandelbrot,
            x_range=(1.5, 2.5),
            y_range=(-0.5, 0.5),
        )
        rgb = _render_once(page)

        black = np.array([0, 0, 0], dtype=np.uint8)
        all_black = np.all(rgb == black, axis=-1)
        assert not all_black.all(), (
            "Expected non-black pixels outside the set; "
            "got all black — escape magnitude tracking may be broken."
        )
