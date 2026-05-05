"""tests/test_export.py — TDD: failing tests for PNG export feature.

All tests fail until src/fractal_explorer_v2.py is extended with:
  - export_screenshot(page, dest_dir=None) function
  - K_s event wiring to call export_screenshot
"""
from __future__ import annotations

import os
import re
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
    spec = importlib.util.spec_from_file_location("engine_ex", _SRC / "fractal_explorer_v2.py")
    eng = importlib.util.module_from_spec(spec)
    sys.modules["fractal_engine_ex"] = eng
    sys.modules.setdefault("fractal_explorer_v2", eng)
    pygame.init()
    pygame.display.set_mode((1, 1))
    spec.loader.exec_module(eng)
    yield eng
    pygame.quit()


def _make_page(engine, w: int = 80, h: int = 60):
    cls = engine.PAGE_CLASSES["A"][0]   # Mandelbrot
    page = cls(w, h)
    page.reset()
    return page


# ── Test 1: file is created ───────────────────────────────────────────────────

class TestExportCreatesFile:
    def test_export_creates_png_file(self, engine, tmp_path):
        """export_screenshot(page, dest_dir) must create exactly one .png file."""
        page = _make_page(engine)
        engine.export_screenshot(page, dest_dir=tmp_path)
        pngs = list(tmp_path.glob("*.png"))
        assert len(pngs) == 1, f"Expected 1 .png file; found {pngs}"

    def test_export_without_dest_dir_uses_cwd(self, engine, tmp_path, monkeypatch):
        """export_screenshot(page) with no dest_dir must write to cwd."""
        monkeypatch.chdir(tmp_path)
        page = _make_page(engine)
        engine.export_screenshot(page)
        pngs = list(tmp_path.glob("*.png"))
        assert len(pngs) == 1, f"Expected 1 .png file in cwd; found {pngs}"

    def test_export_returns_path(self, engine, tmp_path):
        """export_screenshot must return the Path of the written file."""
        page = _make_page(engine)
        result = engine.export_screenshot(page, dest_dir=tmp_path)
        assert result is not None, "export_screenshot must return the output path"
        assert Path(result).exists(), f"Returned path {result!r} does not exist"


# ── Test 2: filename format ───────────────────────────────────────────────────

class TestExportFilenameFormat:
    def test_filename_contains_class_name(self, engine, tmp_path):
        """Filename must embed the page class name."""
        page = _make_page(engine)
        result = engine.export_screenshot(page, dest_dir=tmp_path)
        filename = Path(result).name
        assert page.__class__.__name__ in filename, (
            f"Filename {filename!r} must contain class name {page.__class__.__name__!r}"
        )

    def test_filename_contains_timestamp(self, engine, tmp_path):
        """Filename must contain a YYYYMMDD_HHMMSS timestamp component."""
        page = _make_page(engine)
        result = engine.export_screenshot(page, dest_dir=tmp_path)
        filename = Path(result).name
        # Match 8-digit date + underscore + 6-digit time
        pattern = r"\d{8}_\d{6}"
        assert re.search(pattern, filename), (
            f"Filename {filename!r} must contain YYYYMMDD_HHMMSS timestamp"
        )

    def test_filename_ends_with_png(self, engine, tmp_path):
        """Filename must end with .png."""
        page = _make_page(engine)
        result = engine.export_screenshot(page, dest_dir=tmp_path)
        assert Path(result).suffix == ".png", (
            f"File must end with .png; got {Path(result).suffix!r}"
        )

    def test_filename_prefix_is_fractal(self, engine, tmp_path):
        """Filename must start with 'fractal_'."""
        page = _make_page(engine)
        result = engine.export_screenshot(page, dest_dir=tmp_path)
        assert Path(result).name.startswith("fractal_"), (
            f"Filename must start with 'fractal_'; got {Path(result).name!r}"
        )


# ── Test 3: PNG is a valid image ──────────────────────────────────────────────

class TestExportValidImage:
    def test_exported_png_is_loadable_by_pygame(self, engine, tmp_path):
        """pygame.image.load must succeed on the exported file."""
        page = _make_page(engine, 80, 60)
        result = engine.export_screenshot(page, dest_dir=tmp_path)
        loaded = pygame.image.load(str(result))
        assert loaded is not None

    def test_exported_png_dimensions_match_page(self, engine, tmp_path):
        """Exported image dimensions must match the page's w × h."""
        w, h = 80, 60
        page = _make_page(engine, w, h)
        result = engine.export_screenshot(page, dest_dir=tmp_path)
        loaded = pygame.image.load(str(result))
        assert loaded.get_width() == w, (
            f"Expected width {w}, got {loaded.get_width()}"
        )
        assert loaded.get_height() == h, (
            f"Expected height {h}, got {loaded.get_height()}"
        )

    def test_exported_png_is_not_empty(self, engine, tmp_path):
        """Exported PNG file must be non-zero bytes."""
        page = _make_page(engine)
        result = engine.export_screenshot(page, dest_dir=tmp_path)
        size = Path(result).stat().st_size
        assert size > 0, f"Exported PNG is empty (0 bytes): {result}"


# ── Test 4: export works for multiple page types ──────────────────────────────

class TestExportAllCategories:
    @pytest.mark.parametrize("cat", ["A", "B"])
    def test_export_non_escape_time_page(self, engine, tmp_path, cat):
        """export_screenshot must work for non-escape-time pages too."""
        cls = engine.PAGE_CLASSES[cat][0]
        page = cls(80, 60)
        page.reset()
        result = engine.export_screenshot(page, dest_dir=tmp_path)
        assert Path(result).exists(), f"Export failed for {cls.__name__}"
