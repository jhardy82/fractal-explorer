"""test_fps_overlay.py — T19 FPS/performance overlay tests."""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture(scope="module")
def engine():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "engine_fps", _SRC / "fractal_explorer_v2.py"
    )
    eng = importlib.util.module_from_spec(spec)
    sys.modules["fractal_engine_fps"] = eng
    sys.modules.setdefault("fractal_explorer_v2", eng)
    pygame.init()
    pygame.display.set_mode((1, 1))
    spec.loader.exec_module(eng)
    yield eng
    pygame.quit()


def _make_explorer(engine):
    """Create a minimal FractalExplorer instance for testing."""
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((800, 600))
    return engine.FractalExplorer()


class TestFpsOverlay:
    def test_show_fps_default_false(self, engine):
        """_show_fps should default to False."""
        ex = _make_explorer(engine)
        assert ex._show_fps is False

    def test_d_key_toggles_fps(self, engine):
        """D key press should toggle _show_fps between True and False."""
        ex = _make_explorer(engine)
        ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d, mod=0, unicode="d")
        ex.handle_event(ev)
        assert ex._show_fps is True
        ex.handle_event(ev)
        assert ex._show_fps is False

    def test_fps_rendered_changes_surface(self, engine):
        """draw() output should differ when _show_fps is True vs False."""
        ex = _make_explorer(engine)
        ex._show_fps = False
        ex.draw()
        # capture a portion of the top-right where FPS text would appear
        off_surf = ex.screen.copy()
        ex._show_fps = True
        ex.draw()
        on_surf = ex.screen.copy()
        # at least one pixel must differ in the top-right region
        changed = False
        for x in range(ex.w - 150, ex.w):
            for y in range(30, 50):
                if off_surf.get_at((x, y)) != on_surf.get_at((x, y)):
                    changed = True
                    break
            if changed:
                break
        assert changed, "FPS text should change pixels in top-right area"

    def test_fps_absent_when_off(self, engine):
        """When _show_fps is False, two draws should produce identical top-right regions."""
        ex = _make_explorer(engine)
        ex._show_fps = False
        ex.draw()
        surf1 = ex.screen.copy()
        ex.draw()
        surf2 = ex.screen.copy()
        for x in range(ex.w - 150, ex.w):
            for y in range(30, 50):
                assert surf1.get_at((x, y)) == surf2.get_at((x, y)), \
                    f"Unexpected pixel change at ({x},{y}) when FPS overlay is off"
