"""test_orbit_trap.py — T8 orbit trap colouring tests."""
import numpy as np
import pygame
import pytest

_W, _H = 80, 60


def _make_page(cls, **overrides):
    Patched = type("Patched", (cls,), overrides)
    page = Patched(_W, _H)
    page.reset()
    return page


class TestOrbitTrapDisabled:
    def test_default_off(self, engine):
        page = _make_page(engine.Mandelbrot)
        assert page.orbit_trap == ''

    def test_no_trap_colours_in_set_black(self, engine):
        """Without orbit trap, in-set pixels must be palette[0] (black)."""
        page = _make_page(engine.Mandelbrot, x_range=(-0.01, 0.01), y_range=(-0.01, 0.01))
        page.render_rows(0, _H)
        rgb = pygame.surfarray.array3d(page.surface).transpose(1, 0, 2)
        assert np.all(rgb == 0), "In-set pixels must be black when no orbit trap"


class TestOrbitTrapEnabled:
    @pytest.mark.parametrize("trap", ['point', 'line', 'cross', 'circle'])
    def test_trap_produces_nonblack_interior(self, engine, trap):
        """With an orbit trap, in-set region must not be uniformly black."""
        page = _make_page(engine.Mandelbrot, orbit_trap=trap,
                          x_range=(-0.01, 0.01), y_range=(-0.01, 0.01))
        page.render_rows(0, _H)
        rgb = pygame.surfarray.array3d(page.surface).transpose(1, 0, 2)
        assert not np.all(rgb == 0), f"Trap '{trap}': interior should not be all black"

    @pytest.mark.parametrize("trap", ['point', 'line', 'cross', 'circle'])
    def test_trap_produces_colour_variety(self, engine, trap):
        """Orbit trap output must have more than one unique colour."""
        page = _make_page(engine.Mandelbrot, orbit_trap=trap)
        page.render_rows(0, _H)
        rgb = pygame.surfarray.array3d(page.surface).transpose(1, 0, 2)
        unique = np.unique(rgb.reshape(-1, 3), axis=0)
        assert len(unique) > 1, f"Trap '{trap}': expected colour variety"

    def test_trap_differs_from_no_trap(self, engine):
        """Orbit-trap render must differ from standard render."""
        page_std = _make_page(engine.Mandelbrot)
        page_std.render_rows(0, _H)
        rgb_std = pygame.surfarray.array3d(page_std.surface).transpose(1, 0, 2)

        page_trap = _make_page(engine.Mandelbrot, orbit_trap='point')
        page_trap.render_rows(0, _H)
        rgb_trap = pygame.surfarray.array3d(page_trap.surface).transpose(1, 0, 2)

        assert not np.array_equal(rgb_std, rgb_trap)


class TestTrapDistance:
    def test_point_trap(self, engine):
        z = np.array([0.5 + 0.5j, 0.0 + 0.0j])
        page = _make_page(engine.Mandelbrot, orbit_trap='point')
        d = page._trap_dist(z)
        assert abs(d[0] - abs(0.5 + 0.5j)) < 1e-12
        assert d[1] == 0.0

    def test_line_trap(self, engine):
        z = np.array([1.0 + 0.3j])
        page = _make_page(engine.Mandelbrot, orbit_trap='line')
        d = page._trap_dist(z)
        assert abs(d[0] - 0.3) < 1e-12

    def test_cross_trap(self, engine):
        z = np.array([0.2 + 0.5j])
        page = _make_page(engine.Mandelbrot, orbit_trap='cross')
        d = page._trap_dist(z)
        assert abs(d[0] - 0.2) < 1e-12

    def test_circle_trap(self, engine):
        z = np.array([1.3 + 0.0j])
        page = _make_page(engine.Mandelbrot, orbit_trap='circle')
        d = page._trap_dist(z)
        assert abs(d[0] - 0.3) < 1e-12
