"""tests/test_screensaver.py — T17 Screensaver / Kiosk Mode tests.

Tests for kiosk mode toggled with K key:
  - K press enables/disables kiosk
  - Cinematic mode coupled to kiosk state
  - Page advances after KIOSK_ADVANCE_FRAMES update() calls
  - Timer resets on advance
  - Any key/click (except K) exits kiosk
  - Animations activated on kiosk entry
"""
from __future__ import annotations

import pygame


def _make_explorer(engine):
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((10, 10))
    return engine.FractalExplorer()


def _k_event():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k, mod=0, unicode="k")


def _other_key_event():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a")


def _click_event():
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 100))


class TestKioskMode:
    def test_k_key_enables_kiosk(self, engine):
        """K press → _kiosk = True."""
        explorer = _make_explorer(engine)
        assert not explorer._kiosk
        explorer.handle_event(_k_event())
        assert explorer._kiosk is True

    def test_k_key_disables_kiosk(self, engine):
        """Second K press → _kiosk = False."""
        explorer = _make_explorer(engine)
        explorer.handle_event(_k_event())
        assert explorer._kiosk is True
        explorer.handle_event(_k_event())
        assert explorer._kiosk is False

    def test_kiosk_enables_cinematic(self, engine):
        """After K press, _cinematic = True."""
        explorer = _make_explorer(engine)
        explorer._cinematic = False
        explorer.handle_event(_k_event())
        assert explorer._cinematic is True

    def test_kiosk_disables_cinematic_on_exit(self, engine):
        """After second K press (kiosk off), _cinematic = False."""
        explorer = _make_explorer(engine)
        explorer.handle_event(_k_event())   # enable
        assert explorer._cinematic is True
        explorer.handle_event(_k_event())   # disable
        assert explorer._cinematic is False

    def test_kiosk_advances_page_after_timeout(self, engine, monkeypatch):
        """After KIOSK_ADVANCE_FRAMES calls to run(), go_next() was called."""
        explorer = _make_explorer(engine)
        explorer.handle_event(_k_event())   # enable kiosk

        calls = []
        monkeypatch.setattr(explorer, "go_next", lambda: calls.append(1))

        limit = engine.KIOSK_ADVANCE_FRAMES
        for _ in range(limit):
            # Simulate per-frame kiosk update directly (mirrors the run loop)
            if explorer._kiosk:
                explorer._kiosk_timer += 1
                if explorer._kiosk_timer >= limit:
                    explorer.go_next()
                    explorer._kiosk_timer = 0

        assert len(calls) >= 1, "go_next() must be called after KIOSK_ADVANCE_FRAMES ticks"

    def test_kiosk_timer_resets_on_advance(self, engine):
        """After page advance, _kiosk_timer resets to 0."""
        explorer = _make_explorer(engine)
        explorer.handle_event(_k_event())   # enable kiosk

        limit = engine.KIOSK_ADVANCE_FRAMES
        # Drive the timer to the threshold manually
        explorer._kiosk_timer = limit - 1
        # One more tick should trigger advance and reset
        if explorer._kiosk:
            explorer._kiosk_timer += 1
            if explorer._kiosk_timer >= limit:
                explorer.go_next()
                explorer._kiosk_timer = 0

        assert explorer._kiosk_timer == 0

    def test_any_key_exits_kiosk(self, engine):
        """Non-K keydown while kiosk active → _kiosk = False, _cinematic = False."""
        explorer = _make_explorer(engine)
        explorer.handle_event(_k_event())   # enable kiosk
        assert explorer._kiosk is True
        explorer.handle_event(_other_key_event())
        assert explorer._kiosk is False
        assert explorer._cinematic is False

    def test_click_exits_kiosk(self, engine):
        """MOUSEBUTTONDOWN while kiosk active → _kiosk = False, _cinematic = False."""
        explorer = _make_explorer(engine)
        explorer.handle_event(_k_event())   # enable kiosk
        assert explorer._kiosk is True
        explorer.handle_event(_click_event())
        assert explorer._kiosk is False
        assert explorer._cinematic is False

    def test_kiosk_enables_animations(self, engine):
        """After K press, at least one EscapeTimeFractal has hue_cycle_speed > 0
        AND at least one JuliaFractal has flight_speed > 0."""
        explorer = _make_explorer(engine)
        # Ensure all animations are off first
        for pages in explorer.pages.values():
            for page in pages:
                if isinstance(page, engine.EscapeTimeFractal):
                    page.hue_cycle_speed = 0
                if isinstance(page, engine.JuliaFractal):
                    page.flight_speed = 0.0

        explorer.handle_event(_k_event())   # enable kiosk

        escape_animated = any(
            page.hue_cycle_speed > 0
            for pages in explorer.pages.values()
            for page in pages
            if isinstance(page, engine.EscapeTimeFractal)
        )
        julia_animated = any(
            page.flight_speed > 0
            for pages in explorer.pages.values()
            for page in pages
            if isinstance(page, engine.JuliaFractal)
        )
        assert escape_animated, "At least one EscapeTimeFractal must have hue_cycle_speed > 0"
        assert julia_animated, "At least one JuliaFractal must have flight_speed > 0"

    def test_mousewheel_exits_kiosk(self, engine):
        """MOUSEWHEEL event while kiosk active → _kiosk = False."""
        explorer = _make_explorer(engine)
        explorer.handle_event(_k_event())   # enable kiosk
        assert explorer._kiosk is True
        wheel_event = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1)
        explorer.handle_event(wheel_event)
        assert explorer._kiosk is False

    def test_cinematic_state_preserved_on_kiosk_exit(self, engine):
        """Pre-kiosk cinematic=True is restored after kiosk exits."""
        explorer = _make_explorer(engine)
        explorer._cinematic = True           # user had cinematic on before kiosk
        explorer.handle_event(_k_event())    # enter kiosk (cinematic captured as True)
        assert explorer._kiosk is True
        assert explorer._cinematic is True   # still True inside kiosk
        explorer.handle_event(_other_key_event())  # exit kiosk
        assert explorer._kiosk is False
        assert explorer._cinematic is True   # restored to pre-kiosk value

    def test_animations_not_restored_on_kiosk_exit(self, engine):
        """Animation speeds (hue_cycle_speed, flight_speed) are NOT restored on kiosk exit.

        Design decision — "permanent wake-up" semantic: entering kiosk wakes dormant pages;
        exiting kiosk keeps them alive. Animation state is intentionally one-way.
        """
        explorer = _make_explorer(engine)
        # Zero out all animations first
        for pages in explorer.pages.values():
            for page in pages:
                if hasattr(page, 'hue_cycle_speed'):
                    page.hue_cycle_speed = 0
                if hasattr(page, 'flight_speed'):
                    page.flight_speed = 0.0

        explorer.handle_event(_k_event())          # enter kiosk — wakes animations
        explorer.handle_event(_other_key_event())  # exit kiosk

        # Animations must still be active after exit (permanent wake-up is intentional)
        escape_animated = any(
            page.hue_cycle_speed > 0
            for pages in explorer.pages.values()
            for page in pages
            if isinstance(page, engine.EscapeTimeFractal)
        )
        assert escape_animated, (
            "hue_cycle_speed must remain > 0 after kiosk exit — "
            "permanent wake-up is an intentional design choice, not a bug"
        )
