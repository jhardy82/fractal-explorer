"""
test_regression.py — pixel-hash golden tests for fractal_explorer_v2.

Layer 4 in the doctrine. For each deterministic page, advance N frames and
hash the surface bytes. First run captures baselines; subsequent runs assert
against them. Stochastic pages get RNG-seeded captures.

Baselines stored at: tests_fractal_engine/_baselines/<class_name>_<frame>.txt
"""
from __future__ import annotations

import hashlib
import random
from pathlib import Path

import numpy as np
import pygame
import pytest

_BASELINES = Path(__file__).resolve().parent / "_baselines"
_BASELINES.mkdir(exist_ok=True)

# Test sizes
_W, _H = 320, 240


def _hash_surface(surface: pygame.Surface) -> str:
    raw = pygame.image.tostring(surface, "RGBA")
    return hashlib.sha256(raw).hexdigest()


def _baseline_path(class_name: str, frame: int) -> Path:
    return _BASELINES / f"{class_name}_f{frame}.txt"


def _check_or_create_baseline(class_name: str, frame: int, actual_hash: str) -> tuple[str, bool]:
    """
    Returns (status, passed):
        status   = 'created' | 'matched' | 'mismatched'
        passed   = True for created and matched; False for mismatched
    """
    p = _baseline_path(class_name, frame)
    if not p.exists():
        p.write_text(actual_hash + "\n")
        return ("created", True)
    expected = p.read_text().strip()
    if expected == actual_hash:
        return ("matched", True)
    return ("mismatched", False)


def _run_page(cls, frames: list[int], seed: int = 42) -> dict[int, str]:
    """Construct a page deterministically and return {frame: pixel_hash}."""
    random.seed(seed)
    np.random.seed(seed)
    page = cls(_W, _H)
    page.reset()
    surf = pygame.Surface((_W, _H))
    out: dict[int, str] = {}
    target_max = max(frames)
    for f in range(1, target_max + 1):
        page.update(f)
        if f in frames:
            page.draw(surf)
            out[f] = _hash_surface(surf)
    return out


# ── Sacred Geometry: deterministic, single render ───────────────────────────

class TestSacredGeometryRegression:
    """SG pages render once on reset → snapshot frame 1 only."""

    def test_sg_baselines(self, engine, request):
        results = []
        for cls in engine.PAGE_CLASSES["E"]:
            hashes = _run_page(cls, frames=[1])
            status, passed = _check_or_create_baseline(cls.__name__, 1, hashes[1])
            results.append((cls.__name__, status, passed))
        # always print summary
        print("\n[SG regression]")
        for name, status, passed in results:
            print(f"  {name:30s}  {status:12s}  {'OK' if passed else 'FAIL'}")
        # fail if any mismatch
        mismatches = [r for r in results if not r[2]]
        assert not mismatches, f"{len(mismatches)} SG regression mismatches"


# ── Escape-time: deterministic numpy, snapshot at frame 30 ──────────────────

class TestEscapeTimeRegression:
    """Escape-time pages are fully deterministic. Snapshot at frame 30."""

    @pytest.mark.parametrize("class_name", [
        "Mandelbrot", "Julia1", "Julia2", "BurningShip", "Tricorn",
        "Multibrot3", "Multibrot4",
    ])
    def test_escape_time_baseline(self, engine, class_name):
        cls = getattr(engine, class_name)
        hashes = _run_page(cls, frames=[30])
        status, passed = _check_or_create_baseline(class_name, 30, hashes[30])
        if status == "created":
            pytest.skip(f"baseline created for {class_name} (rerun to compare)")
        assert passed, f"{class_name} regression mismatch at frame 30"


# ── Deterministic IFS curves (Koch family) ──────────────────────────────────

class TestKochFamilyRegression:
    """Koch curves are deterministic line-iter. Snapshot at frames 30 and 100."""

    @pytest.mark.parametrize("class_name", ["KochCurve", "KochSnowflake"])
    def test_koch_baseline(self, engine, class_name):
        cls = getattr(engine, class_name)
        hashes = _run_page(cls, frames=[30, 100])
        for f, h in hashes.items():
            status, passed = _check_or_create_baseline(class_name, f, h)
            if status == "created":
                pytest.skip(f"baseline created for {class_name} f{f}")
            assert passed, f"{class_name} regression mismatch at frame {f}"


# ── L-systems are deterministic — but their progressive draw uses idx ───────

class TestLSystemRegression:
    """L-systems are deterministic. Snapshot final fully-drawn frame."""

    @pytest.mark.parametrize("class_name", [
        "BinaryTreeLS", "HilbertCurve", "GosperCurve", "SierpinskiArrowhead",
        "PlantOne", "PlantTwo", "PenroseTiling",
    ])
    def test_lsystem_baseline(self, engine, class_name):
        cls = getattr(engine, class_name)
        # use a high frame count to ensure full draw completes
        hashes = _run_page(cls, frames=[300])
        status, passed = _check_or_create_baseline(class_name, 300, hashes[300])
        if status == "created":
            pytest.skip(f"baseline created for {class_name}")
        assert passed, f"{class_name} regression mismatch"


# ── Stochastic pages: regression via seeded RNG ─────────────────────────────

class TestStochasticRegressionWithSeed:
    """Chaos-game pages are stochastic but become deterministic with a fixed seed."""

    @pytest.mark.parametrize("class_name", [
        "SierpinskiTriangleIFS", "VicsekFractal", "TSquareFractal",
        "HeighwayDragonIFS", "LevyCIFS",
    ])
    def test_seeded_stochastic_baseline(self, engine, class_name):
        cls = getattr(engine, class_name)
        hashes = _run_page(cls, frames=[20], seed=42)
        status, passed = _check_or_create_baseline(class_name, 20, hashes[20])
        if status == "created":
            pytest.skip(f"baseline created for {class_name}")
        assert passed, f"{class_name} (seeded) regression mismatch"


# ── Determinism check (the prerequisite for regression to mean anything) ────

class TestDeterminismProperty:
    """Two seeded runs must produce identical hashes."""

    @pytest.mark.parametrize("class_name", [
        "Mandelbrot", "BurningShip", "KochSnowflake", "BinaryTreeLS",
        "VesicaPiscis", "FlowerOfLife", "TreeOfLife",
    ])
    def test_run_is_deterministic(self, engine, class_name):
        cls = getattr(engine, class_name)
        a = _run_page(cls, frames=[10], seed=42)[10]
        b = _run_page(cls, frames=[10], seed=42)[10]
        assert a == b, f"{class_name} non-deterministic across runs"

    @pytest.mark.parametrize("class_name", [
        "SierpinskiTriangleIFS", "VicsekFractal", "HeighwayDragonIFS",
    ])
    def test_seeded_stochastic_is_deterministic(self, engine, class_name):
        cls = getattr(engine, class_name)
        a = _run_page(cls, frames=[15], seed=42)[15]
        b = _run_page(cls, frames=[15], seed=42)[15]
        assert a == b, f"{class_name} stochastic page non-deterministic with seed 42"

    @pytest.mark.parametrize("class_name", [
        "SierpinskiTriangleIFS", "HeighwayDragonIFS",
    ])
    def test_different_seeds_diverge(self, engine, class_name):
        cls = getattr(engine, class_name)
        a = _run_page(cls, frames=[15], seed=42)[15]
        b = _run_page(cls, frames=[15], seed=999)[15]
        assert a != b, f"{class_name} seed has no effect (suspicious)"
