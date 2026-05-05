"""
test_3d_integration.py — integration tests for the 3D fractal category.

Mirrors the pattern of test_integration.py for the F · DIMENSION category
introduced by fractal_3d.register_3d_category.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame  # noqa: E402

# add src/ to sys.path so fractal_3d + fractal_explorer_v2 imports work
_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


@pytest.fixture(scope="module")
def engine_with_3d():
    """Engine module with category F registered."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("engine_3d", _SRC / "fractal_explorer_v2.py")
    eng = importlib.util.module_from_spec(spec)
    sys.modules["fractal_engine_v2"] = eng    # match conftest naming
    sys.modules["fractal_explorer_v2"] = eng
    pygame.init()
    pygame.display.set_mode((1, 1))
    spec.loader.exec_module(eng)

    spec3 = importlib.util.spec_from_file_location("f3d", _SRC / "fractal_3d.py")
    f3d = importlib.util.module_from_spec(spec3)
    sys.modules["fractal_3d"] = f3d
    spec3.loader.exec_module(f3d)
    f3d.register_3d_category(eng)

    yield eng
    pygame.quit()


# ── existence + count ──────────────────────────────────────────────────────

class TestThreeDCategoryRegistration:
    def test_category_F_present(self, engine_with_3d):
        assert "F" in engine_with_3d.PAGE_CLASSES

    def test_three_3d_forms(self, engine_with_3d):
        forms = engine_with_3d.PAGE_CLASSES["F"]
        names = [c.__name__ for c in forms]
        assert "Mandelbulb" in names
        assert "Mandelbox" in names
        assert "MengerSponge" in names
        assert len(forms) == 3

    def test_total_forms_now_51(self, engine_with_3d):
        total = sum(len(v) for v in engine_with_3d.PAGE_CLASSES.values())
        assert total == 51, f"Expected 51 forms, got {total}"

    def test_categories_metadata_extended(self, engine_with_3d):
        keys = [c[0] for c in engine_with_3d.CATEGORIES]
        assert "F" in keys
        f_meta = next(c for c in engine_with_3d.CATEGORIES if c[0] == "F")
        assert f_meta[1] == "DIMENSION"
        assert isinstance(f_meta[2], tuple) and len(f_meta[2]) == 3   # RGB color


# ── lifecycle: instantiate + reset + update + draw ─────────────────────────

class TestThreeDLifecycle:
    @pytest.mark.parametrize("name", ["Mandelbulb", "Mandelbox", "MengerSponge"])
    def test_form_lifecycle(self, engine_with_3d, name):
        cls = next(c for c in engine_with_3d.PAGE_CLASSES["F"] if c.__name__ == name)
        page = cls(160, 120)
        page.reset()
        # advance enough frames to complete at least one full pass
        # (low-res lh / rows_per_frame ≈ 40/8 = 5 frames per pass)
        surf = pygame.Surface((160, 120))
        for f in range(1, 12):
            page.update(f)
            page.draw(surf)
        # surface should have been written to (non-zero pixel sum after full pass)
        arr = pygame.surfarray.array3d(surf)
        assert arr.sum() > 0, f"{name}: empty surface after 12 frames"

    @pytest.mark.parametrize("size", [(120, 90), (240, 180), (480, 360)])
    def test_all_3d_forms_at_size(self, engine_with_3d, size):
        w, h = size
        for cls in engine_with_3d.PAGE_CLASSES["F"]:
            page = cls(w, h)
            page.reset()
            surf = pygame.Surface((w, h))
            # at larger sizes need more frames to complete
            n_frames = max(15, page.lh // page.rows_per_frame + 5)
            for f in range(1, n_frames + 1):
                page.update(f)
                page.draw(surf)
            arr = pygame.surfarray.array3d(surf)
            assert arr.sum() > 0, f"{cls.__name__}@{size}: empty after {n_frames} frames"


# ── camera + DE function sanity ────────────────────────────────────────────

class TestThreeDDistanceEstimators:
    """Verify each DE returns sensible (finite, broadly correct-sign) values."""

    @pytest.mark.parametrize("name", ["Mandelbulb", "Mandelbox", "MengerSponge"])
    def test_DE_at_origin_is_negative_or_small(self, engine_with_3d, name):
        """Origin is inside (Mandelbulb/Mandelbox) or near boundary (Menger)."""
        cls = next(c for c in engine_with_3d.PAGE_CLASSES["F"] if c.__name__ == name)
        page = cls(120, 90)
        page.reset()
        # origin must be inside or very near surface — DE should be ≤ small positive
        p = np.array([[0.0, 0.0, 0.0]], dtype=np.float32)
        d = page.DE(p)
        assert np.isfinite(d).all(), f"{name}: non-finite DE at origin"
        # most DEs at origin are 0 (interior) or small; very far points have larger d
        assert d[0] < 5.0, f"{name}: DE at origin = {d[0]} (suspiciously large)"

    @pytest.mark.parametrize("name", ["Mandelbulb", "Mandelbox", "MengerSponge"])
    def test_DE_far_away_is_large_positive(self, engine_with_3d, name):
        cls = next(c for c in engine_with_3d.PAGE_CLASSES["F"] if c.__name__ == name)
        page = cls(120, 90)
        page.reset()
        # 100 units away is far outside any reasonable fractal boundary
        p = np.array([[100.0, 100.0, 100.0]], dtype=np.float32)
        d = page.DE(p)
        assert np.isfinite(d).all()
        # should be roughly the distance to origin (with possible scale factor)
        assert d[0] > 10.0, f"{name}: DE at far point = {d[0]} (should be >> 10)"

    def test_camera_returns_orthonormal_basis(self, engine_with_3d):
        cls = engine_with_3d.PAGE_CLASSES["F"][0]   # any 3D form
        page = cls(120, 90)
        page.reset()
        page.frame = 100
        eye, fwd, right, up = page._camera()
        assert eye.shape == (3,)
        # fwd should be unit length
        assert abs(np.linalg.norm(fwd) - 1.0) < 1e-5
        # right and up should be unit length and roughly perpendicular to fwd
        assert abs(np.linalg.norm(right) - 1.0) < 1e-5
        assert abs(np.linalg.norm(up) - 1.0) < 1e-5
        assert abs(fwd @ right) < 1e-5
        assert abs(fwd @ up) < 1e-5


# ── camera animation property ──────────────────────────────────────────────

class TestThreeDCameraAnimation:
    def test_camera_yaw_changes_per_frame(self, engine_with_3d):
        cls = engine_with_3d.PAGE_CLASSES["F"][0]
        page = cls(120, 90)
        page.reset()
        page.frame = 0
        eye_a = page._camera()[0]
        page.frame = 100
        eye_b = page._camera()[0]
        # yaw should have rotated, eye position changed
        assert not np.allclose(eye_a, eye_b), "Camera should auto-rotate over frames"


# ── performance: 30 frames at 480×360 ≤ 0.300s ────────────────────────────

class TestThreeDPerformance:
    """C.3 DoD: 30 frames at 480×360 must complete in ≤ 0.300s per form."""

    @pytest.mark.parametrize("name", ["Mandelbulb", "Mandelbox", "MengerSponge"])
    def test_30_frames_at_480x360_within_300ms(self, engine_with_3d, name):
        import time
        cls = next(c for c in engine_with_3d.PAGE_CLASSES["F"] if c.__name__ == name)
        page = cls(480, 360)
        page.reset()
        surf = pygame.Surface((480, 360))
        N = 30
        t0 = time.perf_counter()
        for f in range(1, N + 1):
            page.update(f)
            page.draw(surf)
        elapsed = time.perf_counter() - t0
        assert elapsed <= 0.300, (
            f"{name}: {elapsed:.3f}s for {N} frames at 480×360 (limit 0.300s)"
        )
