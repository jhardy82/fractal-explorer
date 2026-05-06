"""tests/test_iter_control.py — T20 max-iteration control tests.

All tests validate the [ and ] key handlers for adjusting max_iter:
  - ] increases max_iter by 50 (capped at 2000)
  - [ decreases max_iter by 50 (clamped to 50 minimum)
  - Both handlers reset row to 0 to restart progressive render
  - Non-EscapeTimeFractal pages ignore bracket keys
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture(scope="module")
def engine():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "engine_iter", _SRC / "fractal_explorer_v2.py"
    )
    eng = importlib.util.module_from_spec(spec)
    sys.modules["fractal_engine_iter"] = eng
    sys.modules.setdefault("fractal_explorer_v2", eng)
    pygame.init()
    pygame.display.set_mode((1, 1))
    spec.loader.exec_module(eng)
    yield eng
    pygame.quit()


@pytest.fixture()
def explorer(engine):
    """Create a minimal FractalExplorer instance for each test."""
    exp = engine.FractalExplorer.__new__(engine.FractalExplorer)
    exp.w = 160
    exp.h = 120
    exp.body_h = 120 - engine.NAV_H - engine.TITLE_H
    exp.screen = pygame.Surface((exp.w, exp.h))
    exp.font_big = pygame.font.SysFont("consolas", 14, bold=True)
    exp.font_sm = pygame.font.SysFont("consolas", 11)
    exp.font_xs = pygame.font.SysFont("consolas", 10)

    # Nav/zoom/pan state
    exp.running = True
    exp.frame = 0
    exp.cat_idx = 0
    exp.page_idx = 0
    exp._pan_active = False
    exp._pan_x0 = 0
    exp._pan_y0 = 0
    exp._pan_x_range = (-2.5, 1.0)
    exp._pan_y_range = (-1.25, 1.25)
    exp._zoom_target_x = None
    exp._zoom_target_y = None
    exp._zoom_lowres = False
    exp._cinematic = False
    exp._show_info = False
    exp._show_fps = False
    exp._bookmarks = []
    exp._bookmark_idx = -1
    exp._julia_seed_px = None

    # GIF state
    exp._recording = False
    exp._frames = []
    exp._gif_notice = 0
    exp._last_gif_path = ""

    # Kiosk state
    exp._kiosk = False
    exp._kiosk_timer = 0
    exp._cinematic_before_kiosk = False

    # Bookmark persistence state
    exp._bm_notice = 0
    exp._bm_notice_text = ""

    exp._instantiate_pages()
    exp.current.ensure_init()

    return exp


def _send_key(explorer, key: int) -> None:
    """Simulate a key press through handle_event."""
    e = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")
    explorer.handle_event(e)


# ── Test 1 ──────────────────────────────────────────────────────────────────

def test_rightbracket_increases_max_iter(engine, explorer):
    """Pressing ] must increase max_iter by 50."""
    # Mandelbrot is at cat_idx=0, page_idx=0 by default
    explorer.cat_idx = 0
    explorer.page_idx = 0
    assert isinstance(explorer.current, engine.EscapeTimeFractal)
    original = explorer.current.max_iter
    _send_key(explorer, pygame.K_RIGHTBRACKET)
    assert explorer.current.max_iter == original + 50


# ── Test 2 ──────────────────────────────────────────────────────────────────

def test_leftbracket_decreases_max_iter(engine, explorer):
    """Pressing [ must decrease max_iter by 50."""
    explorer.cat_idx = 0
    explorer.page_idx = 0
    assert isinstance(explorer.current, engine.EscapeTimeFractal)
    original = explorer.current.max_iter
    _send_key(explorer, pygame.K_LEFTBRACKET)
    assert explorer.current.max_iter == max(original - 50, 50)


# ── Test 3 ──────────────────────────────────────────────────────────────────

def test_leftbracket_clamps_at_minimum_50(engine, explorer):
    """Pressing [ when max_iter is 50 must not go below 50."""
    explorer.cat_idx = 0
    explorer.page_idx = 0
    explorer.current.max_iter = 50
    _send_key(explorer, pygame.K_LEFTBRACKET)
    assert explorer.current.max_iter == 50


# ── Test 4 ──────────────────────────────────────────────────────────────────

def test_rightbracket_clamps_at_maximum_2000(engine, explorer):
    """Pressing ] when max_iter is 2000 must not exceed 2000."""
    explorer.cat_idx = 0
    explorer.page_idx = 0
    explorer.current.max_iter = 2000
    _send_key(explorer, pygame.K_RIGHTBRACKET)
    assert explorer.current.max_iter == 2000


# ── Test 5 ──────────────────────────────────────────────────────────────────

def test_bracket_resets_row(engine, explorer):
    """Pressing ] or [ must reset row to 0 to restart progressive render."""
    explorer.cat_idx = 0
    explorer.page_idx = 0
    explorer.current.row = 100  # simulate mid-render
    _send_key(explorer, pygame.K_RIGHTBRACKET)
    assert explorer.current.row == 0, "row should be reset after ] press"

    explorer.current.row = 50
    _send_key(explorer, pygame.K_LEFTBRACKET)
    assert explorer.current.row == 0, "row should be reset after [ press"


# ── Test 6 ──────────────────────────────────────────────────────────────────

def test_bracket_noop_on_non_escape_time(engine, explorer):
    """Pressing ] or [ on a non-EscapeTimeFractal page must do nothing."""
    # Navigate to category B (IFS pages) — find the first non-EscapeTimeFractal
    found_ifs = False
    for cat_idx, (cat_key, _, _) in enumerate(engine.CATEGORIES):
        for page_idx, page_class in enumerate(engine.PAGE_CLASSES.get(cat_key, [])):
            if not issubclass(page_class, engine.EscapeTimeFractal):
                found_ifs = True
                explorer.cat_idx = cat_idx
                explorer.page_idx = page_idx
                break
        if found_ifs:
            break

    if found_ifs:
        assert not isinstance(explorer.current, engine.EscapeTimeFractal)
        original_cat = explorer.cat_idx
        original_page = explorer.page_idx
        # Should not raise and should not change cat/page
        _send_key(explorer, pygame.K_RIGHTBRACKET)
        assert explorer.cat_idx == original_cat
        assert explorer.page_idx == original_page
        _send_key(explorer, pygame.K_LEFTBRACKET)
        assert explorer.cat_idx == original_cat
        assert explorer.page_idx == original_page
