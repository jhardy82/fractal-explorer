"""
mutation_target.py — pure-algorithm slice for mutmut testing.

No pygame, no SDL, no rendering.  Only the math that drives the fractal
engine so that mutmut can mutate it and the test suite can catch the
difference.

Functions extracted from fractal_explorer_v2.py (logic-equivalent,
simplified for isolated testing).
"""
from __future__ import annotations

import math

# ── module-level constants (anchored by test_defaults_and_properties.py) ──

ESCAPE_RADIUS_SQ: float = 4.0      # |z|^2 threshold for escape-time fractals

LORENZ_SIGMA: float = 10.0         # σ  (Prandtl number)
LORENZ_RHO:   float = 28.0         # ρ  (Rayleigh number)
LORENZ_BETA:  float = 8.0 / 3.0    # β
LORENZ_DT:    float = 0.005        # Euler step size

HENON_A: float = 1.4               # non-linearity coefficient
HENON_B: float = 0.3               # contraction coefficient


# ── escape-time: Mandelbrot ─────────────────────────────────────────────────

def mandelbrot_iter(cx: float, cy: float, max_iter: int = 256) -> int:
    """
    Return the iteration count for point (cx, cy) in the Mandelbrot set.

    Returns max_iter if the point does not escape within max_iter steps.
    """
    zx, zy = 0.0, 0.0
    for i in range(max_iter):
        zx2, zy2 = zx * zx, zy * zy
        if zx2 + zy2 > ESCAPE_RADIUS_SQ:
            return i
        zy = 2.0 * zx * zy + cy
        zx = zx2 - zy2 + cx
    return max_iter


# ── escape-time: Julia ──────────────────────────────────────────────────────

def julia_iter(
    zx: float, zy: float,
    cx: float, cy: float,
    max_iter: int = 256,
) -> int:
    """
    Return the iteration count for orbit starting at (zx, zy) with
    Julia parameter (cx, cy).
    """
    for i in range(max_iter):
        zx2, zy2 = zx * zx, zy * zy
        if zx2 + zy2 > ESCAPE_RADIUS_SQ:
            return i
        zy = 2.0 * zx * zy + cy
        zx = zx2 - zy2 + cx
    return max_iter


# ── smooth colouring ────────────────────────────────────────────────────────

def smooth_colour(
    iteration: int, zx: float, zy: float, max_iter: int
) -> float:
    """
    Log-based smooth (continuous) colouring for escape-time fractals.
    Returns 0.0 for interior points (iteration == max_iter).
    """
    if iteration >= max_iter:
        return 0.0
    log_zn = math.log(zx * zx + zy * zy) / 2.0
    nu = math.log(log_zn / math.log(2.0)) / math.log(2.0)
    return iteration + 1.0 - nu


# ── Lorenz attractor step ───────────────────────────────────────────────────

def lorenz_step(x: float, y: float, z: float) -> tuple[float, float, float]:
    """One forward-Euler step of the Lorenz system."""
    dx = LORENZ_SIGMA * (y - x)
    dy = x * (LORENZ_RHO - z) - y
    dz = x * y - LORENZ_BETA * z
    return (
        x + dx * LORENZ_DT,
        y + dy * LORENZ_DT,
        z + dz * LORENZ_DT,
    )


# ── Hénon map step ──────────────────────────────────────────────────────────

def henon_step(x: float, y: float) -> tuple[float, float]:
    """One step of the Hénon map."""
    return (
        1.0 - HENON_A * x * x + y,
        HENON_B * x,
    )


# ── L-system expansion ──────────────────────────────────────────────────────

def expand_lsystem(axiom: str, rules: dict[str, str], n: int) -> str:
    """Expand an L-system for n iterations, applying rules simultaneously."""
    s = axiom
    for _ in range(n):
        s = "".join(rules.get(ch, ch) for ch in s)
    return s


# ── world-to-screen mapping ─────────────────────────────────────────────────

def to_screen(
    wx: float,
    wy: float,
    bx0: float,
    bx1: float,
    by0: float,
    by1: float,
    w: int,
    h: int,
) -> tuple[int, int]:
    """
    Map world-space point (wx, wy) to screen pixel (sx, sy).

    The bounding box [bx0, bx1] × [by0, by1] is centred on the canvas
    with uniform scaling (preserves aspect ratio) and 10% margin.
    Y-axis is flipped (world up → screen up).
    """
    bw = bx1 - bx0
    bh = by1 - by0
    if bw == 0.0 or bh == 0.0:
        return w // 2, h // 2
    scale = min(w / bw, h / bh) * 0.9
    cx_w = (bx0 + bx1) / 2.0
    cy_w = (by0 + by1) / 2.0
    sx = int((wx - cx_w) * scale + w / 2.0)
    sy = int(-((wy - cy_w) * scale) + h / 2.0)
    return sx, sy
