"""test_smooth_zoom.py — T3 smooth eased zoom unit tests."""
import pygame

from fractal_explorer_v2 import TITLE_H

# ── helpers ───────────────────────────────────────────────────────────────────

def _lerp(a: float, b: float, alpha: float = 0.25) -> float:
    return a + alpha * (b - a)


def _make_explorer(engine):
    """Headless FractalExplorer with minimal pygame init."""
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((10, 10))
    return engine.FractalExplorer()


# ── tests ─────────────────────────────────────────────────────────────────────

class TestLerp:
    def test_lerp_moves_25_percent(self):
        result = _lerp(0.0, 1.0)
        assert abs(result - 0.25) < 1e-12

    def test_convergence_snaps(self):
        """After enough iterations the lerp must snap exactly to target."""
        cur = 0.0
        target = 1.0
        alpha = 0.25
        for _ in range(200):
            new = cur + alpha * (target - cur)
            if abs(new - target) < 1e-10:
                cur = target
                break
            cur = new
        assert cur == target


class TestTickZoom:
    def test_tick_zoom_noop_when_no_target(self, engine):
        explorer = _make_explorer(engine)
        page = explorer.current
        x_before = page.x_range
        explorer._tick_zoom()
        assert page.x_range == x_before

    def test_pan_clears_zoom_target(self, engine):
        explorer = _make_explorer(engine)
        explorer._zoom_target_x = (-2.0, 1.0)
        explorer._zoom_target_y = (-1.0, 1.0)
        # MOUSEBUTTONDOWN inside body region clears zoom targets
        ev = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=(explorer.w // 2, TITLE_H + 10),
        )
        explorer.handle_event(ev)
        assert explorer._zoom_target_x is None

    def test_reset_clears_zoom_target(self, engine):
        explorer = _make_explorer(engine)
        explorer._zoom_target_x = (-2.0, 1.0)
        explorer._zoom_target_y = (-1.0, 1.0)
        explorer.reset_current()
        assert explorer._zoom_target_x is None
        assert explorer._zoom_target_y is None
