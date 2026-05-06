"""test_zoom_stack.py — T13 zoom stack / location bookmarks tests."""
import pygame


def _make_explorer(engine):
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((10, 10))
    return engine.FractalExplorer()


class TestZoomStack:
    def test_b_key_saves_bookmark(self, engine):
        ex = _make_explorer(engine)
        ex.cat_idx = 0
        ex.page_idx = 0
        assert isinstance(ex.current, engine.Mandelbrot)
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode="b")
        ex.handle_event(ev)
        assert len(ex._bookmarks) == 1

    def test_bookmark_captures_viewport(self, engine):
        ex = _make_explorer(engine)
        ex.cat_idx = 0
        ex.page_idx = 0
        page = ex.current
        assert isinstance(page, engine.EscapeTimeFractal)
        page.x_range = (-1.0, 0.5)
        page.y_range = (-0.5, 0.5)
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode="b")
        ex.handle_event(ev)
        _, _, xr, yr = ex._bookmarks[0]
        assert xr == (-1.0, 0.5)
        assert yr == (-0.5, 0.5)

    def test_n_key_restores_bookmark(self, engine):
        ex = _make_explorer(engine)
        ex.cat_idx = 0
        ex.page_idx = 0
        page = ex.current
        assert isinstance(page, engine.EscapeTimeFractal)
        page.x_range = (-1.0, 0.5)
        page.y_range = (-0.5, 0.5)
        b_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode="b")
        ex.handle_event(b_ev)
        page.x_range = (-2.5, 1.0)
        n_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n, mod=0, unicode="n")
        ex.handle_event(n_ev)
        assert ex.current.x_range == (-1.0, 0.5)
        assert ex.current.y_range == (-0.5, 0.5)

    def test_ring_buffer_caps_at_10(self, engine):
        ex = _make_explorer(engine)
        ex.cat_idx = 0
        ex.page_idx = 0
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode="b")
        for _ in range(12):
            ex.handle_event(ev)
        assert len(ex._bookmarks) == 10

    def test_n_on_empty_is_noop(self, engine):
        ex = _make_explorer(engine)
        prev_cat = ex.cat_idx
        prev_page = ex.page_idx
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n, mod=0, unicode="n")
        ex.handle_event(ev)
        assert ex.cat_idx == prev_cat
        assert ex.page_idx == prev_page

    def test_n_restores_cross_page_bookmark(self, engine):
        ex = _make_explorer(engine)
        # Save bookmark on page_idx=1 in cat 0
        ex.cat_idx = 0
        ex.page_idx = 1
        page1 = ex.current
        assert isinstance(page1, engine.EscapeTimeFractal)
        page1.x_range = (-0.5, 0.5)
        page1.y_range = (-0.5, 0.5)
        b_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode="b")
        ex.handle_event(b_ev)
        # Navigate away
        ex.cat_idx = 0
        ex.page_idx = 0
        # Restore via N — must update page_idx back to 1 and restore viewport
        n_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n, mod=0, unicode="n")
        ex.handle_event(n_ev)
        assert ex.page_idx == 1
        assert ex.current.x_range == (-0.5, 0.5)
        assert ex.current.y_range == (-0.5, 0.5)

    def test_b_noop_on_non_escape_time(self, engine):
        # Navigate to IFS category (B = index 1)
        ex = _make_explorer(engine)
        from fractal_explorer_v2 import CAT_KEYS
        b_cat = CAT_KEYS.index("B")
        ex.cat_idx = b_cat
        ex.page_idx = 0
        # Confirm it's not EscapeTimeFractal
        assert not isinstance(ex.current, engine.EscapeTimeFractal)
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode="b")
        ex.handle_event(ev)
        assert len(ex._bookmarks) == 0
