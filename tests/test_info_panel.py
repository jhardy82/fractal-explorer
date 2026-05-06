"""test_info_panel.py — T14 math info panel tests."""
import pygame


def _make_explorer(engine):
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((10, 10))
    return engine.FractalExplorer()


class TestInfoPanel:
    def test_mandelbrot_has_formula(self, engine):
        page = engine.Mandelbrot(800, 600)
        assert page.formula != ""

    def test_julia_has_formula(self, engine):
        page = engine.JuliaFractal(800, 600)
        assert page.formula != ""

    def test_show_info_default_false(self, engine):
        ex = _make_explorer(engine)
        assert ex._show_info is False

    def test_m_key_toggles(self, engine):
        ex = _make_explorer(engine)
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, mod=0, unicode="m")
        ex.handle_event(ev)
        assert ex._show_info is True
        ex.handle_event(ev)
        assert ex._show_info is False

    def test_burning_ship_has_formula(self, engine):
        page = engine.BurningShip(800, 600)
        assert page.formula != ""
