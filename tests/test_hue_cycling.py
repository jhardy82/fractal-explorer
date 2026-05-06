"""test_hue_cycling.py — T4 hue cycling animation unit tests."""
import numpy as np
import pygame

_W, _H = 80, 60


def _make_page(cls, **overrides):
    Patched = type("Patched", (cls,), overrides)
    page = Patched(_W, _H)
    page.reset()
    return page


class TestHueCyclingDisabled:
    def test_hue_shift_zero_by_default(self, engine):
        page = _make_page(engine.Mandelbrot)
        assert page._hue_shift == 0

    def test_no_shift_when_speed_zero(self, engine):
        page = _make_page(engine.Mandelbrot, hue_cycle_speed=0)
        page.update(100)
        assert page._hue_shift == 0


class TestHueCyclingEnabled:
    def test_shift_advances_at_correct_rate(self, engine):
        page = _make_page(engine.Mandelbrot, hue_cycle_speed=4)
        page.update(0)
        assert page._hue_shift == 0
        page.row = 0
        page.update(4)
        assert page._hue_shift == 1

    def test_shift_wraps_around(self, engine):
        page = _make_page(engine.Mandelbrot, hue_cycle_speed=1)
        max_shift = page.max_iter + 1
        page.update(max_shift)
        assert page._hue_shift == 0

    def test_different_shifts_produce_different_colours(self, engine):
        """Rendering with shift=0 vs shift=10 must differ for escaped pixels."""
        Mandelbrot = engine.Mandelbrot
        page0 = _make_page(Mandelbrot, hue_cycle_speed=0,
                           x_range=(1.5, 2.5), y_range=(-0.5, 0.5))
        page0.render_rows(0, _H)
        rgb0 = pygame.surfarray.array3d(page0.surface).transpose(1, 0, 2)

        page10 = _make_page(Mandelbrot, hue_cycle_speed=0,
                            x_range=(1.5, 2.5), y_range=(-0.5, 0.5))
        page10._hue_shift = 10
        page10.render_rows(0, _H)
        rgb10 = pygame.surfarray.array3d(page10.surface).transpose(1, 0, 2)

        assert not np.array_equal(rgb0, rgb10), (
            "Expected different colours for shift=0 vs shift=10"
        )

    def test_integer_path_shifts_escaped_only(self, engine):
        """Integer path (smooth_colouring=False): shift=0 vs shift=10 differ; in-set stays black."""
        Mandelbrot = engine.Mandelbrot

        # Outside the set — all pixels escape, shift must change colours.
        page0 = _make_page(Mandelbrot, smooth_colouring=False,
                           x_range=(1.5, 2.5), y_range=(-0.5, 0.5))
        page0.render_rows(0, _H)
        rgb0 = pygame.surfarray.array3d(page0.surface).transpose(1, 0, 2)

        page10 = _make_page(Mandelbrot, smooth_colouring=False,
                            x_range=(1.5, 2.5), y_range=(-0.5, 0.5))
        page10._hue_shift = 10
        page10.render_rows(0, _H)
        rgb10 = pygame.surfarray.array3d(page10.surface).transpose(1, 0, 2)

        assert not np.array_equal(rgb0, rgb10), "Integer path: shift must change escaped pixel colours"

        # Inside the set — all pixels are in-set, shift must NOT change colours.
        page_in0 = _make_page(Mandelbrot, smooth_colouring=False,
                              x_range=(-0.01, 0.01), y_range=(-0.01, 0.01))
        page_in0.render_rows(0, _H)
        rgb_in0 = pygame.surfarray.array3d(page_in0.surface).transpose(1, 0, 2)

        page_in10 = _make_page(Mandelbrot, smooth_colouring=False,
                               x_range=(-0.01, 0.01), y_range=(-0.01, 0.01))
        page_in10._hue_shift = 10
        page_in10.render_rows(0, _H)
        rgb_in10 = pygame.surfarray.array3d(page_in10.surface).transpose(1, 0, 2)

        assert np.array_equal(rgb_in0, rgb_in10), "Integer path: in-set pixels must be unaffected by shift"

    def test_reset_clears_shift(self, engine):
        page = _make_page(engine.Mandelbrot, hue_cycle_speed=2)
        page._hue_shift = 15
        page.reset()
        assert page._hue_shift == 0
