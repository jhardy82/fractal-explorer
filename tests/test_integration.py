"""
test_integration.py — full-lifecycle integration tests for fractal_explorer_v2.

Layer 2 in the doctrine. Every page class is exercised through a full
init → reset → update×N → draw cycle under headless SDL. Catches per-class
init/draw bugs that pure-function unit tests miss.
"""
from __future__ import annotations

import pygame
import pytest

# ── all-pages lifecycle ─────────────────────────────────────────────────────

class TestAllPagesLifecycle:
    """Every one of the 48 pages must instantiate, reset, and survive 30 frames."""

    def test_total_page_count(self, all_page_classes):
        # Anchor: the project ships with 48 forms.
        assert len(all_page_classes) == 48, (
            f"Expected 48 pages, got {len(all_page_classes)}. "
            "If the count changed, update this anchor."
        )

    def test_all_categories_present(self, engine):
        for key in ("A", "B", "C", "D", "E"):
            assert key in engine.PAGE_CLASSES
            assert len(engine.PAGE_CLASSES[key]) >= 5  # minimum 5 forms per category

    @pytest.mark.parametrize("size", [(320, 240), (800, 600), (1280, 720)])
    def test_all_pages_lifecycle(self, all_page_classes, page_factory, size):
        """Init + reset + update×30 + draw must complete without exception."""
        w, h = size
        for _cat, cls in all_page_classes:
            page = page_factory(cls, w=w, h=h)
            surf = pygame.Surface((w, h))
            for f in range(1, 31):
                page.update(f)
                page.draw(surf)
            # surface should be non-empty after rendering
            arr = pygame.surfarray.array3d(surf)
            assert arr.sum() > 0, f"{cls.__name__} produced empty render at {size}"


# ── per-category integration ────────────────────────────────────────────────

class TestEscapeTimeProgressiveRender:
    """Escape-time pages should fill in rows progressively until done."""

    def test_progressive_render_completes(self, engine, page_factory, medium_size):
        for cls in engine.PAGE_CLASSES["A"]:
            if cls.__name__ in ("Buddhabrot", "LyapunovFractal"):
                continue  # custom render strategies
            page = page_factory(cls, *medium_size)
            # Drive until self.row reaches self.h or 200 frames
            for f in range(1, 200):
                page.update(f)
                if getattr(page, "row", 0) >= page.h:
                    break
            assert getattr(page, "row", 0) >= page.h, (
                f"{cls.__name__} did not finish rendering in 200 frames "
                f"(row={getattr(page, 'row', None)}, h={page.h})"
            )


class TestIFSPointAccumulation:
    """IFS chaos-game pages should accumulate at least N points after K frames."""

    def test_ifs_pages_accumulate(self, engine, page_factory):
        for cls in engine.PAGE_CLASSES["B"]:
            if cls.__name__ not in {
                "SierpinskiTriangleIFS", "SierpinskiCarpet", "VicsekFractal",
                "TSquareFractal", "HeighwayDragonIFS", "LevyCIFS",
                "BarnsleyFernIFS", "PlusFractal",
            }:
                continue
            page = page_factory(cls, w=320, h=240)
            for f in range(1, 21):
                page.update(f)
            # IFSChaosFractal exposes self.n
            n = getattr(page, "n", 0)
            assert n > 1000, f"{cls.__name__}: n={n} too low after 20 frames"


class TestLSystemExpansion:
    """L-system pages should produce non-empty point lists after reset."""

    def test_lsystem_pages_have_points(self, engine, page_factory):
        for cls in engine.PAGE_CLASSES["C"]:
            page = page_factory(cls)
            # PenroseTiling does not use the LSystemFractal.points field
            if cls.__name__ == "PenroseTiling":
                continue
            assert hasattr(page, "points"), f"{cls.__name__} missing points"
            assert len(page.points) > 10, f"{cls.__name__}: only {len(page.points)} points"


class TestAttractorPointAccumulation:
    """Strange attractors should produce a point cloud."""

    def test_attractor_pages_accumulate(self, engine, page_factory):
        for cls in engine.PAGE_CLASSES["D"]:
            page = page_factory(cls, w=320, h=240)
            for f in range(1, 11):
                page.update(f)
            n = getattr(page, "n", 0)
            assert n > 1000, f"{cls.__name__}: n={n} too low"


class TestSacredGeometryStaticRender:
    """SG pages render once on reset; subsequent updates should be no-ops."""

    def test_sg_render_is_immediate(self, engine, page_factory):
        for cls in engine.PAGE_CLASSES["E"]:
            page = page_factory(cls)
            import pygame as pg
            arr = pg.surfarray.array3d(page.surface)
            assert arr.sum() > 0, f"{cls.__name__} produced empty render on reset"


# ── explorer-level integration ──────────────────────────────────────────────

class TestFractalExplorerNavigation:
    """The Explorer's category-and-page navigation must be coherent."""

    def test_explorer_instantiates(self, engine, monkeypatch):
        # bypass display.set_mode since we already have one
        monkeypatch.setattr(engine, "WIN_W", 640)
        monkeypatch.setattr(engine, "WIN_H", 480)
        explorer = engine.FractalExplorer()
        assert explorer.cat_idx == 0
        assert explorer.page_idx == 0
        assert explorer.current_cat == "A"
        assert isinstance(explorer.current, engine.FractalPage)

    def test_navigation_within_category(self, engine, monkeypatch):
        monkeypatch.setattr(engine, "WIN_W", 640)
        monkeypatch.setattr(engine, "WIN_H", 480)
        explorer = engine.FractalExplorer()
        n = len(explorer.pages["A"])
        # forward N times wraps back to start
        for _ in range(n):
            explorer.go_next()
        assert explorer.page_idx == 0

    def test_navigation_across_categories(self, engine, monkeypatch):
        monkeypatch.setattr(engine, "WIN_W", 640)
        monkeypatch.setattr(engine, "WIN_H", 480)
        explorer = engine.FractalExplorer()
        explorer.next_category()
        assert explorer.current_cat == "B"
        assert explorer.page_idx == 0

    def test_jump_to_category(self, engine, monkeypatch):
        monkeypatch.setattr(engine, "WIN_W", 640)
        monkeypatch.setattr(engine, "WIN_H", 480)
        explorer = engine.FractalExplorer()
        explorer.jump_category(4)
        assert explorer.current_cat == "E"

    def test_reset_preserves_class(self, engine, monkeypatch):
        monkeypatch.setattr(engine, "WIN_W", 640)
        monkeypatch.setattr(engine, "WIN_H", 480)
        explorer = engine.FractalExplorer()
        before = type(explorer.current)
        explorer.reset_current()
        assert type(explorer.current) is before
