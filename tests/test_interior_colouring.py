"""test_interior_colouring.py — T9 interior colouring tests."""
import numpy as np
import pygame

_W, _H = 80, 60


def _make_page(cls, **overrides):
    Patched = type("Patched", (cls,), overrides)
    page = Patched(_W, _H)
    page.reset()
    return page


class TestInteriorColourDefault:
    def test_off_by_default(self, engine):
        page = _make_page(engine.Mandelbrot)
        assert page.interior_colouring is False

    def test_in_set_black_when_disabled(self, engine):
        """In-set region must remain black when interior_colouring is False."""
        page = _make_page(engine.Mandelbrot, x_range=(-0.01, 0.01), y_range=(-0.01, 0.01))
        page.render_rows(0, _H)
        rgb = pygame.surfarray.array3d(page.surface).transpose(1, 0, 2)
        assert np.all(rgb == 0), "In-set pixels must be black when interior_colouring=False"


class TestInteriorColourEnabled:
    def test_in_set_not_black_when_enabled(self, engine):
        """In-set region must NOT be uniformly black when interior_colouring is True."""
        page = _make_page(engine.Mandelbrot, interior_colouring=True,
                          x_range=(-0.01, 0.01), y_range=(-0.01, 0.01))
        page.render_rows(0, _H)
        rgb = pygame.surfarray.array3d(page.surface).transpose(1, 0, 2)
        assert not np.all(rgb == 0), "Interior colouring should produce non-black in-set pixels"

    def test_escaped_pixels_unchanged(self, engine):
        """Enabling interior colouring must not change escaped pixel colours."""
        # Render a region fully outside the set (all pixels escape)
        x_out = (1.5, 2.5)
        y_out = (-0.5, 0.5)
        page_std = _make_page(engine.Mandelbrot, x_range=x_out, y_range=y_out)
        page_std.render_rows(0, _H)
        rgb_std = pygame.surfarray.array3d(page_std.surface).transpose(1, 0, 2)

        page_ic = _make_page(engine.Mandelbrot, interior_colouring=True,
                              x_range=x_out, y_range=y_out)
        page_ic.render_rows(0, _H)
        rgb_ic = pygame.surfarray.array3d(page_ic.surface).transpose(1, 0, 2)

        assert np.array_equal(rgb_std, rgb_ic), (
            "Escaped pixels must be identical with and without interior_colouring"
        )

    def test_orbit_trap_takes_precedence(self, engine):
        """When orbit_trap is active, interior_colouring must not change the render."""
        page_trap = _make_page(engine.Mandelbrot, orbit_trap='point',
                               x_range=(-0.01, 0.01), y_range=(-0.01, 0.01))
        page_trap.render_rows(0, _H)
        rgb_trap = pygame.surfarray.array3d(page_trap.surface).transpose(1, 0, 2)

        page_both = _make_page(engine.Mandelbrot, orbit_trap='point', interior_colouring=True,
                               x_range=(-0.01, 0.01), y_range=(-0.01, 0.01))
        page_both.render_rows(0, _H)
        rgb_both = pygame.surfarray.array3d(page_both.surface).transpose(1, 0, 2)

        assert np.array_equal(rgb_trap, rgb_both), (
            "orbit_trap should suppress interior_colouring"
        )

    def test_interior_colour_variety(self, engine):
        """Interior pixels should have more than one unique colour.

        Use the default Mandelbrot viewport so the render contains both in-set
        (deep interior) and near-boundary pixels — the boundary pixels will have
        different accumulated log|z| sums and therefore different palette entries.
        """
        # Default range: x=(-2.5, 1.0), y=(-1.25, 1.25) — contains rich boundary
        page = _make_page(engine.Mandelbrot, interior_colouring=True)
        page.render_rows(0, _H)
        rgb = pygame.surfarray.array3d(page.surface).transpose(1, 0, 2)
        unique = np.unique(rgb.reshape(-1, 3), axis=0)
        assert len(unique) > 2, "Interior colouring should produce varied colours"
