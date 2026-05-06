"""test_palette_system.py — T7 named palette system tests."""
import numpy as np
import pytest


class TestGradientPalette:
    def test_shape(self, engine):
        p = engine._gradient_palette(80, [(0, 0, 0), (255, 255, 255)])
        assert p.shape == (81, 3)

    def test_index_zero_black(self, engine):
        p = engine._gradient_palette(80, [(255, 0, 0), (0, 255, 0)])
        assert tuple(p[0]) == (0, 0, 0)

    def test_interpolation(self, engine):
        p = engine._gradient_palette(10, [(100, 100, 100), (200, 200, 200)])
        assert tuple(p[0]) == (0, 0, 0)
        # Check that interpolation produces intermediate values
        assert tuple(p[1]) != (0, 0, 0)
        assert tuple(p[5]) != (0, 0, 0)
        assert tuple(p[10]) != (0, 0, 0)


class TestNamedPalettes:
    @pytest.mark.parametrize("name,builder", [
        ("fire", "_fire_palette"),
        ("ocean", "_ocean_palette"),
        ("neon", "_neon_palette"),
        ("cosmic", "_cosmic_palette"),
        ("ice", "_ice_palette"),
    ])
    def test_palette_shape(self, engine, name, builder):
        fn = getattr(engine, builder)
        p = fn(80)
        assert p.shape == (81, 3)
        assert p.dtype == np.uint8
        assert tuple(p[0]) == (0, 0, 0)

    def test_all_palettes_differ(self, engine):
        palettes = [
            engine._fire_palette(80),
            engine._ocean_palette(80),
            engine._neon_palette(80),
            engine._cosmic_palette(80),
            engine._ice_palette(80),
        ]
        for i, a in enumerate(palettes):
            for j, b in enumerate(palettes):
                if i != j:
                    assert not np.array_equal(a, b), f"palettes {i} and {j} are identical"


class TestCyclePalette:
    def test_cycle_advances(self, engine):
        import pygame
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((10, 10))
        page = engine.Mandelbrot(100, 100)
        page.reset()
        assert page.palette_name == 'hsv'
        page.cycle_palette()
        assert page.palette_name == 'fire'

    def test_cycle_wraps(self, engine):
        import pygame
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((10, 10))
        page = engine.Mandelbrot(100, 100)
        page.reset()
        for _ in range(len(engine.PALETTE_NAMES)):
            page.cycle_palette()
        assert page.palette_name == 'hsv'

    def test_cycle_triggers_rerender(self, engine):
        import pygame
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((10, 10))
        page = engine.Mandelbrot(100, 100)
        page.reset()
        page.row = page.h
        page.cycle_palette()
        assert page.row == 0

    def test_cycle_changes_palette_data(self, engine):
        import pygame
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((10, 10))
        page = engine.Mandelbrot(100, 100)
        page.reset()
        palette_before = page.palette.copy()
        page.cycle_palette()
        assert not np.array_equal(palette_before, page.palette)
