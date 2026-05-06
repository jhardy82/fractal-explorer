"""test_progressive_quality.py — T11 progressive quality rendering tests."""
import pygame


def _make_explorer(engine):
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((10, 10))
    return engine.FractalExplorer()


class TestRenderDimensions:
    def test_default_full_res(self, engine):
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((10, 10))
        page = engine.Mandelbrot(200, 100)
        page.reset()
        assert page._rw == 200
        assert page._rh == 100

    def test_surface_matches_render_dims(self, engine):
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((10, 10))
        page = engine.Mandelbrot(200, 100)
        page.reset()
        assert page.surface.get_width() == 200
        assert page.surface.get_height() == 100


class TestLowResMode:
    def test_mousewheel_activates_lowres(self, engine, monkeypatch):
        explorer = _make_explorer(engine)
        explorer.cat_idx = 0
        explorer.page_idx = 0
        assert isinstance(explorer.current, engine.Mandelbrot)
        page = explorer.current
        # Dummy SDL cannot warp the mouse — patch get_pos to return a body-region coordinate
        body_y = 30 + explorer.body_h // 2  # TITLE_H + half body = safely in body region
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (explorer.w // 2, body_y))
        ev = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=3)
        explorer.handle_event(ev)
        # Low-res mode should be active
        assert explorer._zoom_lowres is True
        assert page._rw == page.w // 4
        assert page._rh == page.h // 4

    def test_lowres_surface_size(self, engine, monkeypatch):
        explorer = _make_explorer(engine)
        explorer.cat_idx = 0
        explorer.page_idx = 0
        page = explorer.current
        body_y = 30 + explorer.body_h // 2
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (explorer.w // 2, body_y))
        ev = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=3)
        explorer.handle_event(ev)
        assert explorer._zoom_lowres
        assert page.surface.get_width() == page._rw
        assert page.surface.get_height() == page._rh

    def test_zoom_settle_restores_full_res(self, engine):
        explorer = _make_explorer(engine)
        explorer.cat_idx = 0
        explorer.page_idx = 0
        page = explorer.current
        # Manually set low-res mode and a zoom target that immediately snaps
        explorer._zoom_lowres = True
        page._rw = page.w // 4
        page._rh = page.h // 4
        page.surface = pygame.Surface((page._rw, page._rh))
        page.surface.fill((0, 0, 0))
        page.row = page._rh
        explorer._zoom_target_x = page.x_range
        explorer._zoom_target_y = page.y_range
        # Force error = 0 by making target == current (snap)
        explorer._tick_zoom()
        assert explorer._zoom_lowres is False
        assert page._rw == page.w
        assert page._rh == page.h

    def test_pan_clears_lowres(self, engine):
        explorer = _make_explorer(engine)
        explorer.cat_idx = 0
        explorer.page_idx = 0
        page = explorer.current
        # Activate low-res mode manually
        explorer._zoom_lowres = True
        page._rw = page.w // 4
        page._rh = page.h // 4
        page.surface = pygame.Surface((page._rw, page._rh))
        # Fire MOUSEBUTTONDOWN (pan start) in body region
        ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                pos=(explorer.w // 2, explorer.body_h // 2 + 30))
        explorer.handle_event(ev)
        assert explorer._zoom_lowres is False
        assert page._rw == page.w

    def test_reset_current_clears_lowres(self, engine):
        explorer = _make_explorer(engine)
        explorer._zoom_lowres = True
        explorer.reset_current()
        assert explorer._zoom_lowres is False
        page = explorer.current
        if isinstance(page, engine.EscapeTimeFractal):
            assert page._rw == page.w
            assert page._rh == page.h
