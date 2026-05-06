"""test_julia_seed_picker.py — T10 Julia seed picker tests."""
import pygame


def _make_explorer(engine):
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((10, 10))
    return engine.FractalExplorer()


class TestJuliaSeedPicker:
    def test_s_key_on_mandelbrot_navigates_to_julia(self, engine):
        explorer = _make_explorer(engine)
        # Navigate to Mandelbrot (category A, first page)
        explorer.cat_idx = 0  # category 'A'
        explorer.page_idx = 0
        assert isinstance(explorer.current, engine.Mandelbrot)
        # Fire S key event
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, mod=0, unicode='s')
        explorer.handle_event(ev)
        # Should now be on a JuliaFractal
        assert isinstance(explorer.current, engine.JuliaFractal)

    def test_s_key_sets_c_const_from_mouse(self, engine):
        explorer = _make_explorer(engine)
        explorer.cat_idx = 0  # category 'A'
        explorer.page_idx = 0
        assert isinstance(explorer.current, engine.Mandelbrot)
        # Set known mouse position and fire S key
        # mouse position is at screen center; pygame.mouse.get_pos() returns (0,0) in headless
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, mod=0, unicode='s')
        explorer.handle_event(ev)
        julia_page = explorer.current
        assert isinstance(julia_page, engine.JuliaFractal)
        # c_const should be a complex number derived from the Mandelbrot's range
        assert isinstance(julia_page.c_const, complex)

    def test_s_key_resets_julia(self, engine):
        explorer = _make_explorer(engine)
        explorer.cat_idx = 0  # category 'A'
        explorer.page_idx = 0
        # Find Julia page and advance its row to non-zero
        julia_pages = [p for p in explorer.pages.get('A', []) if isinstance(p, engine.JuliaFractal)]
        assert julia_pages, "No JuliaFractal in category A"
        jp = julia_pages[0]
        jp.row = jp.h  # mark as "done rendering"
        # Fire S key
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, mod=0, unicode='s')
        explorer.handle_event(ev)
        # reset() should have been called, so row=0
        assert jp.row == 0

    def test_s_key_noop_on_non_mandelbrot(self, engine):
        explorer = _make_explorer(engine)
        # Navigate to a Julia page directly
        julia_idx = None
        for i, p in enumerate(explorer.pages.get('A', [])):
            if isinstance(p, engine.JuliaFractal):
                julia_idx = i
                break
        assert julia_idx is not None
        explorer.cat_idx = 0  # category 'A'
        explorer.page_idx = julia_idx
        assert isinstance(explorer.current, engine.JuliaFractal)
        c_before = explorer.current.c_const
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, mod=0, unicode='s')
        explorer.handle_event(ev)
        # Still on Julia, c_const unchanged
        assert isinstance(explorer.current, engine.JuliaFractal)
        assert explorer.current.c_const == c_before

    def test_coordinate_mapping_range(self, engine):
        """c_const should be within the Mandelbrot's x/y range bounds."""
        explorer = _make_explorer(engine)
        explorer.cat_idx = 0  # category 'A'
        explorer.page_idx = 0
        page = explorer.current
        assert isinstance(page, engine.Mandelbrot)
        x0, x1 = page.x_range
        y0, y1 = page.y_range
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, mod=0, unicode='s')
        explorer.handle_event(ev)
        jp = explorer.current
        assert isinstance(jp, engine.JuliaFractal)
        assert x0 <= jp.c_const.real <= x1
        assert y0 <= jp.c_const.imag <= y1
