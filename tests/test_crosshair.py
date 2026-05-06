"""test_crosshair.py — T12 crosshair coordinate display tests."""
import importlib

import pytest


@pytest.fixture(scope="module")
def _sc():
    """Return the _screen_to_complex function from the engine module."""
    mod = importlib.import_module("fractal_explorer_v2")
    return mod._screen_to_complex


class TestScreenToComplex:
    def test_left_top_maps_to_range_start(self, _sc):
        z = _sc(0, 30, (-2.5, 1.0), (-1.25, 1.25), 1600, 814, 30)
        assert abs(z.real - (-2.5)) < 1e-9
        assert abs(z.imag - (-1.25)) < 1e-9

    def test_right_edge_pixel_near_x_range_end(self, _sc):
        # mx=1599 is the rightmost valid pixel (0..w-1); maps to just under x_range[1]
        z = _sc(1599, 30, (-2.5, 1.0), (-1.25, 1.25), 1600, 814, 30)
        assert abs(z.real - (1.0 - 3.5 / 1600)) < 1e-9

    def test_center_maps_to_range_midpoint(self, _sc):
        z = _sc(800, 30 + 407, (-2.5, 1.0), (-1.25, 1.25), 1600, 814, 30)
        assert abs(z.real - (-0.75)) < 0.01   # (-2.5 + 1.0) / 2
        assert abs(z.imag - 0.0) < 0.01        # (-1.25 + 1.25) / 2

    def test_clamps_mouse_above_body(self, _sc):
        # my < body_y_offset → clamped to body_y=0 → imag = y_range[0]
        z = _sc(0, 0, (-2.5, 1.0), (-1.25, 1.25), 1600, 814, 30)
        assert z.imag == -1.25

    def test_known_point(self, _sc):
        # mx=400 (25% of 1600) → re = -2.5 + 0.25 * 3.5 = -1.625
        z = _sc(400, 30, (-2.5, 1.0), (-1.25, 1.25), 1600, 814, 30)
        assert abs(z.real - (-1.625)) < 1e-9
