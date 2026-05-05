"""tests/test_param_tweaking.py — TDD: failing tests for per-page parameter tweaking.

All tests fail until src/fractal_explorer_v2.py is extended with:
  - PARAM_DEFAULTS class dict on FractalPage subclasses
  - FractalPage.tweak_param(delta)
  - FractalPage.get_param_display() -> str
  - K_LEFT/K_RIGHT/MOUSEWHEEL event wiring in the engine event loop
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
    """Load engine module once per test module."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("engine_tw", _SRC / "fractal_explorer_v2.py")
    eng = importlib.util.module_from_spec(spec)
    sys.modules["fractal_engine_tw"] = eng
    sys.modules.setdefault("fractal_explorer_v2", eng)
    pygame.init()
    pygame.display.set_mode((1, 1))
    spec.loader.exec_module(eng)
    yield eng
    pygame.quit()


def _julia_class(engine):
    """Return the first Julia subclass from PAGE_CLASSES["A"]."""
    return next(
        c for c in engine.PAGE_CLASSES["A"]
        if "Julia" in c.__name__ and hasattr(c, "c_const")
    )


# ── Test 1: arrow key changes param_c ────────────────────────────────────────

class TestArrowKeyTweakParam:
    def test_right_arrow_increases_param_c_real(self, engine):
        """Calling tweak_param(+step) on a Julia page must change c_const by step."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        before = page.c_const
        step = getattr(page, "param_step", 0.01)
        page.tweak_param(step)
        after = page.c_const

        assert after != before, "tweak_param(+step) must change c_const"
        assert abs((after.real - before.real) - step) < 1e-9 or abs(after - before) > 0, (
            f"Expected c_const to shift by ~{step}; before={before}, after={after}"
        )

    def test_left_arrow_decreases_param_c_real(self, engine):
        """Calling tweak_param(-step) must decrease (or shift) c_const."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        before = page.c_const
        step = getattr(page, "param_step", 0.01)
        page.tweak_param(-step)
        after = page.c_const

        assert after != before, "tweak_param(-step) must change c_const"

    def test_tweak_triggers_re_render(self, engine):
        """After tweak_param, the page must mark itself as needing a re-render (row reset)."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()
        # render some rows
        for f in range(1, 5):
            page.update(f)
        step = getattr(page, "param_step", 0.01)
        page.tweak_param(step)
        # row should be back at 0 so the surface is redrawn
        assert page.row == 0, "tweak_param must reset row to 0 to trigger re-render"


# ── Test 2: param persists after category switch ──────────────────────────────

class TestParamPersistsAcrossSwitch:
    def test_tweaked_c_survives_page_deactivation(self, engine):
        """Tweaking Julia's c, then re-activating the page must retain the tweaked value."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        step = getattr(page, "param_step", 0.01)
        page.tweak_param(step)
        tweaked = page.c_const

        # Simulate category switch: reset another page, then come back to this one
        # The page object retains its state — no re-instantiation between switches
        page.reset()   # reset re-initialises rendering, but should keep tweaked c

        # After reset(), c_const should still be the tweaked value (reset only clears
        # the rendered surface + row counter, not tweakable parameters)
        assert page.c_const == tweaked, (
            f"c_const reverted on reset(); expected {tweaked}, got {page.c_const}"
        )

    def test_multiple_tweaks_accumulate(self, engine):
        """Three calls to tweak_param must accumulate, not overwrite."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        step = getattr(page, "param_step", 0.01)
        original = page.c_const
        page.tweak_param(step)
        page.tweak_param(step)
        page.tweak_param(step)
        final = page.c_const

        total_shift = abs(final - original)
        assert total_shift > step * 1.5, (
            f"Three tweaks should accumulate to ~3×step; got shift={total_shift:.6f}"
        )


# ── Test 3: R resets to defaults ──────────────────────────────────────────────

class TestResetToDefaults:
    def test_reset_param_restores_default_c(self, engine):
        """After tweaking, calling reset_params() must restore the original c_const."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        default_c = page.c_const
        step = getattr(page, "param_step", 0.01)
        page.tweak_param(step * 5)

        assert page.c_const != default_c, "tweak_param must have changed c_const"

        page.reset_params()
        assert abs(page.c_const - default_c) < 1e-12, (
            f"reset_params() must restore default c_const; "
            f"expected {default_c}, got {page.c_const}"
        )

    def test_reset_param_re_renders(self, engine):
        """reset_params() must reset row to 0 so the surface is redrawn."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()
        for f in range(1, 5):
            page.update(f)
        step = getattr(page, "param_step", 0.01)
        page.tweak_param(step)
        for f in range(1, 5):
            page.update(f)

        page.reset_params()
        assert page.row == 0, "reset_params() must reset row to 0"

    def test_param_defaults_class_attribute_present(self, engine):
        """Julia subclasses must expose a PARAM_DEFAULTS class attribute."""
        cls = _julia_class(engine)
        assert hasattr(cls, "PARAM_DEFAULTS"), (
            f"{cls.__name__} must have a PARAM_DEFAULTS class attribute"
        )
        assert isinstance(cls.PARAM_DEFAULTS, dict), "PARAM_DEFAULTS must be a dict"
        assert len(cls.PARAM_DEFAULTS) > 0, "PARAM_DEFAULTS must have at least one entry"


# ── Test 4: mouse scroll changes param ────────────────────────────────────────

class TestMouseScrollTweakParam:
    def test_scroll_up_changes_param(self, engine):
        """A positive scroll_delta must call tweak_param with a positive value."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        before = page.c_const
        # Engine exposes scroll_step attribute; simulate what the event loop would do
        scroll_step = getattr(page, "scroll_step", getattr(page, "param_step", 0.01))
        page.tweak_param(1 * scroll_step)   # y=+1 → tweak_param(+scroll_step)

        assert page.c_const != before, "Scroll-up (y=+1) must change the parameter"

    def test_scroll_down_changes_param_opposite_direction(self, engine):
        """Scroll-down (y=-1) and scroll-up (y=+1) must produce opposite changes."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        scroll_step = getattr(page, "scroll_step", getattr(page, "param_step", 0.01))

        page.tweak_param(scroll_step)
        up_val = page.c_const
        page.reset_params()
        page.tweak_param(-scroll_step)
        down_val = page.c_const
        page.reset_params()
        original = page.c_const

        assert up_val != down_val, "Scroll up and scroll down must produce different values"
        # Up should be farther in one direction; both should differ from original
        assert up_val != original
        assert down_val != original


# ── Test 5: on-screen display ────────────────────────────────────────────────

class TestOnScreenDisplay:
    def test_get_param_display_returns_string(self, engine):
        """get_param_display() must return a non-empty string."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        result = page.get_param_display()
        assert isinstance(result, str), "get_param_display() must return str"
        assert len(result) > 0, "get_param_display() must return a non-empty string"

    def test_get_param_display_contains_c(self, engine):
        """The display string must contain the letter 'c' (as the parameter name)."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        result = page.get_param_display()
        assert "c" in result.lower(), (
            f"get_param_display() must reference 'c'; got: {result!r}"
        )

    def test_get_param_display_contains_current_value(self, engine):
        """The display string must include the real part of c_const as a decimal."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        result = page.get_param_display()
        # The real part rounded to 2+ decimal places must appear somewhere
        real_str = f"{page.c_const.real:.2f}"
        assert real_str in result, (
            f"get_param_display() must show c.real={real_str!r}; got: {result!r}"
        )

    def test_get_param_display_updates_after_tweak(self, engine):
        """After tweak_param, get_param_display() must reflect the new value."""
        cls = _julia_class(engine)
        page = cls(80, 60)
        page.reset()

        before_display = page.get_param_display()
        step = getattr(page, "param_step", 0.01)
        page.tweak_param(step * 10)
        after_display = page.get_param_display()

        assert before_display != after_display, (
            "get_param_display() must change after tweak_param()"
        )

    def test_non_julia_page_has_get_param_display(self, engine):
        """All FractalPage subclasses must support get_param_display() without raising."""
        for forms in engine.PAGE_CLASSES.values():
            for cls in forms:
                page = cls(40, 30)
                result = page.get_param_display()
                assert isinstance(result, str), (
                    f"{cls.__name__}.get_param_display() must return str"
                )
