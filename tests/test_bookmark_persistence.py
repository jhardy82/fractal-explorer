"""tests/test_bookmark_persistence.py — TDD: Bookmark Persistence feature (T18).

All tests validate bookmark save/load functionality added to FractalExplorer:
  - E key exports bookmarks to fractal_bookmarks.json
  - L key loads bookmarks from fractal_bookmarks.json
  - Notice countdown is set on success
  - Round-trip preserves viewport values
"""
from __future__ import annotations

import json
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
        "engine_bm", _SRC / "fractal_explorer_v2.py"
    )
    eng = importlib.util.module_from_spec(spec)
    sys.modules["fractal_engine_bm"] = eng
    sys.modules.setdefault("fractal_explorer_v2", eng)
    pygame.init()
    pygame.display.set_mode((1, 1))
    spec.loader.exec_module(eng)
    yield eng
    pygame.quit()


@pytest.fixture()
def explorer(engine):
    """Create a minimal FractalExplorer instance for each test."""
    from conftest import _apply_minimal_explorer_state
    exp = engine.FractalExplorer.__new__(engine.FractalExplorer)
    _apply_minimal_explorer_state(exp, engine)
    return exp


def _send_key(explorer, key: int) -> None:
    """Simulate a key press through handle_event."""
    e = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")
    explorer.handle_event(e)


def _write_bookmark_json(path: Path, entries: list[dict]) -> None:
    """Write a valid bookmark JSON file to the given path."""
    path.write_text(json.dumps(entries, indent=2))


# ── Test 1 ──────────────────────────────────────────────────────────────────

def test_e_key_noop_when_empty(explorer, tmp_path, monkeypatch):
    """E key with empty _bookmarks must not create a JSON file."""
    monkeypatch.chdir(tmp_path)
    assert explorer._bookmarks == []
    _send_key(explorer, pygame.K_e)
    json_files = list(tmp_path.glob("*.json"))
    assert json_files == [], f"Expected no JSON file, found: {json_files}"


# ── Test 2 ──────────────────────────────────────────────────────────────────

def test_e_key_creates_json_file(explorer, tmp_path, monkeypatch):
    """E key with non-empty _bookmarks must create fractal_bookmarks.json."""
    monkeypatch.chdir(tmp_path)
    explorer._bookmarks = [(0, 1, (-2.5, 1.0), (-1.25, 1.25))]
    _send_key(explorer, pygame.K_e)
    expected = tmp_path / "fractal_bookmarks.json"
    assert expected.exists(), f"fractal_bookmarks.json not found in {tmp_path}"


# ── Test 3 ──────────────────────────────────────────────────────────────────

def test_saved_json_is_valid(explorer, tmp_path, monkeypatch):
    """Saved JSON must contain entries with cat_idx, page_idx, x_range, y_range keys."""
    monkeypatch.chdir(tmp_path)
    explorer._bookmarks = [
        (0, 1, (-2.5, 1.0), (-1.25, 1.25)),
        (2, 3, (-0.5, 0.5), (-0.5, 0.5)),
    ]
    _send_key(explorer, pygame.K_e)
    path = tmp_path / "fractal_bookmarks.json"
    data = json.loads(path.read_text())
    assert isinstance(data, list), "Top-level JSON must be a list"
    assert len(data) == 2, f"Expected 2 entries, got {len(data)}"
    for entry in data:
        assert "cat_idx" in entry, f"Missing cat_idx in {entry}"
        assert "page_idx" in entry, f"Missing page_idx in {entry}"
        assert "x_range" in entry, f"Missing x_range in {entry}"
        assert "y_range" in entry, f"Missing y_range in {entry}"


# ── Test 4 ──────────────────────────────────────────────────────────────────

def test_l_key_loads_bookmarks(explorer, tmp_path, monkeypatch):
    """L key with an existing JSON file must populate _bookmarks."""
    monkeypatch.chdir(tmp_path)
    entries = [
        {"cat_idx": 1, "page_idx": 2, "x_range": [-1.0, 1.0], "y_range": [-0.5, 0.5]},
        {"cat_idx": 3, "page_idx": 0, "x_range": [-2.0, 2.0], "y_range": [-1.0, 1.0]},
    ]
    _write_bookmark_json(tmp_path / "fractal_bookmarks.json", entries)
    explorer._bookmarks = []
    _send_key(explorer, pygame.K_l)
    assert len(explorer._bookmarks) == 2, (
        f"Expected 2 bookmarks after L key, got {len(explorer._bookmarks)}"
    )


# ── Test 5 ──────────────────────────────────────────────────────────────────

def test_l_key_noop_when_no_file(explorer, tmp_path, monkeypatch):
    """L key with no JSON file must not crash and must leave _bookmarks empty."""
    monkeypatch.chdir(tmp_path)
    explorer._bookmarks = []
    _send_key(explorer, pygame.K_l)
    assert explorer._bookmarks == [], (
        "_bookmarks must remain empty when no JSON file exists"
    )


# ── Test 6 ──────────────────────────────────────────────────────────────────

def test_round_trip_preserves_viewport(explorer, tmp_path, monkeypatch):
    """Save then load must reproduce x_range and y_range within floating-point tolerance."""
    monkeypatch.chdir(tmp_path)
    original = [
        (0, 1, (-2.123456789, 1.987654321), (-1.111111111, 1.222222222)),
        (4, 6, (0.123456789012345, 0.234567890123456), (-0.0001, 0.0002)),
    ]
    explorer._bookmarks = list(original)
    _send_key(explorer, pygame.K_e)

    # Clear and reload
    explorer._bookmarks = []
    _send_key(explorer, pygame.K_l)

    assert len(explorer._bookmarks) == len(original), (
        f"Expected {len(original)} bookmarks after round-trip, got {len(explorer._bookmarks)}"
    )
    for i, (loaded, orig) in enumerate(zip(explorer._bookmarks, original, strict=True)):
        ci_l, pi_l, xr_l, yr_l = loaded
        ci_o, pi_o, xr_o, yr_o = orig
        assert ci_l == ci_o, f"Entry {i}: cat_idx mismatch {ci_l} != {ci_o}"
        assert pi_l == pi_o, f"Entry {i}: page_idx mismatch {pi_l} != {pi_o}"
        assert abs(xr_l[0] - xr_o[0]) < 1e-9, f"Entry {i}: x_range[0] mismatch"
        assert abs(xr_l[1] - xr_o[1]) < 1e-9, f"Entry {i}: x_range[1] mismatch"
        assert abs(yr_l[0] - yr_o[0]) < 1e-9, f"Entry {i}: y_range[0] mismatch"
        assert abs(yr_l[1] - yr_o[1]) < 1e-9, f"Entry {i}: y_range[1] mismatch"


# ── Test 7 ──────────────────────────────────────────────────────────────────

def test_bm_notice_set_on_save(explorer, tmp_path, monkeypatch):
    """_bm_notice must be > 0 after a successful E key press with non-empty bookmarks."""
    monkeypatch.chdir(tmp_path)
    explorer._bookmarks = [(0, 0, (-2.5, 1.0), (-1.25, 1.25))]
    explorer._bm_notice = 0
    _send_key(explorer, pygame.K_e)
    assert explorer._bm_notice > 0, (
        f"_bm_notice must be set after successful save, got {explorer._bm_notice}"
    )


# ── Test 8 ──────────────────────────────────────────────────────────────────

def test_bm_notice_set_on_load(explorer, tmp_path, monkeypatch):
    """_bm_notice must be > 0 after a successful L key press on an existing file."""
    monkeypatch.chdir(tmp_path)
    entries = [
        {"cat_idx": 0, "page_idx": 0, "x_range": [-2.5, 1.0], "y_range": [-1.25, 1.25]},
    ]
    _write_bookmark_json(tmp_path / "fractal_bookmarks.json", entries)
    explorer._bm_notice = 0
    _send_key(explorer, pygame.K_l)
    assert explorer._bm_notice > 0, (
        f"_bm_notice must be set after successful load, got {explorer._bm_notice}"
    )
