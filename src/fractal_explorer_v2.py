"""
fractal_explorer_v2.py — Fractal Visualization Engine
=====================================================

Extends the original fractal_explorer.py (12 forms) to ~50 forms across 5
mathematical / geometric categories.

CATEGORIES
----------
  A  ESCAPE-TIME   complex-plane iteration: Mandelbrot, Julia, Burning Ship,
                   Tricorn, Multibrot³, Multibrot⁴, Newton, Phoenix, Lyapunov,
                   Buddhabrot
  B  IFS           iterated function systems & deterministic self-similar:
                   Sierpiński △/Carpet/Hexagon, Cantor, Vicsek, T-Square,
                   Koch Snowflake/Curve, Heighway Dragon, Twindragon, Lévy C,
                   Pythagoras Tree, Apollonian Gasket, Barnsley Fern, Plus
  C  L-SYSTEM      grammar-rewrite + turtle: Binary Tree, Hilbert Curve,
                   Peano Curve, Gosper Curve, Sierpiński Arrowhead, Plant 1,
                   Plant 2, Penrose-style P3
  D  ATTRACTOR     strange attractors (continuous & discrete chaos):
                   Lorenz, Rössler, Aizawa, Clifford, De Jong, Ikeda, Hénon
  E  SACRED        Sacred Geometry forms (per ContextForge canon):
                   Vesica Piscis, Seed of Life, Flower of Life, Metatron's
                   Cube, Tree of Life (10 Sephirot), Golden Spiral, Sri Yantra

NAV
---
  ← / →   prev / next page within category
  Tab     next category
  1..5    jump to category A..E
  R       reset current page
  F       toggle fullscreen
  Esc     quit

INSTALL
-------
  pip install pygame numpy

RUN
---
  python fractal_explorer_v2.py
"""

from __future__ import annotations

import colorsys
import math
import random
from dataclasses import dataclass

import numpy as np
import pygame

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

WIN_W, WIN_H = 1600, 900
BG = (8, 11, 20)
PANEL_BG = (13, 17, 32)
FG = (218, 228, 248)
DIM = (62, 84, 128)
DIMMER = (128, 150, 188)

# (key, label, color) — color matches the chat-widget canonical palette
CATEGORIES = [
    ("A", "ESCAPE-TIME", (220, 80, 112)),    # rose
    ("B", "IFS",         (130, 215, 30)),    # lime
    ("C", "L-SYSTEM",    (30, 184, 124)),    # teal
    ("D", "ATTRACTOR",   (240, 162, 40)),    # amber
    ("E", "SACRED",      (212, 164, 55)),    # gold
]
CAT_KEYS = [c[0] for c in CATEGORIES]

NAV_H = 56
TITLE_H = 30

PHI = (1 + math.sqrt(5)) / 2

# ──────────────────────────────────────────────────────────────────────────────
# PALETTE HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def hsv_palette(n: int, sat: float = 0.78, val: float = 0.92, hue_offset: float = 0.0) -> np.ndarray:
    """Return (n+1, 3) uint8 — index 0 reserved for in-set (black)."""
    arr = np.zeros((n + 1, 3), dtype=np.uint8)
    for i in range(n):
        h = (hue_offset + i / max(n, 1)) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, sat, val)
        arr[i + 1] = (int(r * 255), int(g * 255), int(b * 255))
    return arr


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ──────────────────────────────────────────────────────────────────────────────
# BASE PAGE
# ──────────────────────────────────────────────────────────────────────────────

class FractalPage:
    name = "Page"
    category = "B"
    info = ""

    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self._initialised = False

    def reset(self) -> None:
        """Override to (re)initialise per-page state. Called once per activation."""
        self._initialised = True

    def ensure_init(self) -> None:
        if not self._initialised:
            self.reset()

    def update(self, frame: int) -> None:
        """Per-frame state update. Called only for the active page."""
        pass

    def draw(self, screen: pygame.Surface) -> None:
        """Draw page contents into the body region (full screen minus chrome)."""
        pass


# ──────────────────────────────────────────────────────────────────────────────
# CATEGORY A — ESCAPE-TIME (numpy vectorised)
# ──────────────────────────────────────────────────────────────────────────────

class EscapeTimeFractal(FractalPage):
    """Vectorised numpy escape-time renderer.

    Subclass overrides:
        x_range, y_range  — viewport in complex plane
        max_iter          — iteration cap
        iter_step(z, c)   — one iteration step (returns new z)
        z0(c)             — optional initial z (defaults to 0+0j)
    """

    category = "A"
    max_iter = 80
    rows_per_frame = 14
    x_range = (-2.5, 1.0)
    y_range = (-1.25, 1.25)
    palette_offset = 0.0

    def reset(self) -> None:
        super().reset()
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(BG)
        self.row = 0
        self.palette = hsv_palette(self.max_iter, hue_offset=self.palette_offset)

    def iter_step(self, z: np.ndarray, c: np.ndarray) -> np.ndarray:
        return z * z + c

    def z0(self, c: np.ndarray) -> np.ndarray:
        return np.zeros_like(c)

    def render_rows(self, y0: int, y1: int) -> None:
        x0, x1 = self.x_range
        ymin, ymax = self.y_range
        xs = np.linspace(x0, x1, self.w)
        ys = np.linspace(ymin, ymax, self.h)[y0:y1]
        cx, cy = np.meshgrid(xs, ys)
        c = cx + 1j * cy
        z = self.z0(c)
        div = np.zeros(c.shape, dtype=np.int32)
        mask = np.ones(c.shape, dtype=bool)
        for i in range(1, self.max_iter + 1):
            z_new = self.iter_step(z, c)
            z = np.where(mask, z_new, z)
            diverged = mask & (np.abs(z) > 4.0)
            div[diverged] = i
            mask &= ~diverged
            if not mask.any():
                break
        rgb = self.palette[div]                                     # (rows, w, 3)
        rgb_t = rgb.transpose(1, 0, 2)                              # (w, rows, 3) for pygame
        sub = pygame.surfarray.make_surface(rgb_t)
        self.surface.blit(sub, (0, y0))

    def update(self, frame: int) -> None:
        if self.row >= self.h:
            return
        y1 = min(self.h, self.row + self.rows_per_frame)
        self.render_rows(self.row, y1)
        self.row = y1

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(self.surface, (0, 0))


class JuliaFractal(EscapeTimeFractal):
    """Julia: z' = z² + c_const. c_const is fixed; varying z₀ across the plane."""
    c_const = complex(-0.79, 0.15)
    x_range = (-1.7, 1.7)
    y_range = (-1.0, 1.0)

    def iter_step(self, z, c):
        return z * z + self.c_const

    def z0(self, c):
        return c.copy()


class Mandelbrot(EscapeTimeFractal):
    name = "Mandelbrot Set"
    info = "z ↦ z² + c · canonical complex escape-time set"
    palette_offset = 0.62


class Julia1(JuliaFractal):
    name = "Julia · c=-0.79+0.15i"
    info = "z ↦ z² + c, c fixed · classic spiral form"
    c_const = complex(-0.79, 0.15)
    palette_offset = 0.85


class Julia2(JuliaFractal):
    name = "Julia · c=-0.7+0.27015i"
    info = "z ↦ z² + c · dendrite-like form"
    c_const = complex(-0.7, 0.27015)
    palette_offset = 0.05


class BurningShip(EscapeTimeFractal):
    name = "Burning Ship"
    info = "z ↦ (|Re z| + i|Im z|)² + c · Michelitsch & Rössler 1992"
    x_range = (-2.0, 1.5)
    y_range = (-2.0, 1.0)
    palette_offset = 0.10

    def iter_step(self, z, c):
        return (np.abs(z.real) + 1j * np.abs(z.imag)) ** 2 + c


class Tricorn(EscapeTimeFractal):
    name = "Tricorn (Mandelbar)"
    info = "z ↦ z̄² + c · anti-holomorphic"
    x_range = (-2.0, 2.0)
    y_range = (-1.5, 1.5)
    palette_offset = 0.30

    def iter_step(self, z, c):
        return np.conj(z) ** 2 + c


class Multibrot3(EscapeTimeFractal):
    name = "Multibrot d=3"
    info = "z ↦ z³ + c · 2-fold symmetry"
    x_range = (-1.5, 1.5)
    y_range = (-1.2, 1.2)
    palette_offset = 0.50

    def iter_step(self, z, c):
        return z ** 3 + c


class Multibrot4(EscapeTimeFractal):
    name = "Multibrot d=4"
    info = "z ↦ z⁴ + c · 3-fold symmetry"
    x_range = (-1.4, 1.4)
    y_range = (-1.1, 1.1)
    palette_offset = 0.42

    def iter_step(self, z, c):
        return z ** 4 + c


class NewtonFractal(EscapeTimeFractal):
    """Newton's method on z³ - 1 = 0. Coloured by which root each point converges to."""
    name = "Newton z³ - 1"
    info = "Newton iteration on z³−1=0 · root-basin colouring"
    x_range = (-2.0, 2.0)
    y_range = (-1.5, 1.5)
    max_iter = 32
    rows_per_frame = 18

    def reset(self) -> None:
        super().reset()
        # custom palette for 3 roots + iteration shading
        self.palette = np.array([
            [16, 16, 16],
            [220, 80, 110],     # root 1
            [80, 200, 110],     # root 2
            [110, 130, 230],    # root 3
        ] * (self.max_iter // 3 + 4), dtype=np.uint8)[:self.max_iter + 1]

    def render_rows(self, y0, y1):
        x0, x1 = self.x_range
        ymin, ymax = self.y_range
        xs = np.linspace(x0, x1, self.w)
        ys = np.linspace(ymin, ymax, self.h)[y0:y1]
        cx, cy = np.meshgrid(xs, ys)
        z = cx + 1j * cy
        roots = np.array([1, complex(-0.5, math.sqrt(3) / 2), complex(-0.5, -math.sqrt(3) / 2)])
        out = np.zeros(z.shape, dtype=np.int32)
        for i in range(1, self.max_iter + 1):
            denom = 3 * z * z
            denom[denom == 0] = 1e-12
            z = z - (z ** 3 - 1) / denom
            for r_idx, r in enumerate(roots):
                hit = (np.abs(z - r) < 1e-3) & (out == 0)
                out[hit] = (r_idx + 1) + (i % 8) * 3
        rgb = self.palette[np.clip(out, 0, self.max_iter)]
        rgb_t = rgb.transpose(1, 0, 2)
        sub = pygame.surfarray.make_surface(rgb_t)
        self.surface.blit(sub, (0, y0))


class PhoenixFractal(EscapeTimeFractal):
    """Phoenix: z_{n+1} = z_n² + c + p · z_{n-1}."""
    name = "Phoenix"
    info = "z ↦ z² + c + p·z_prev · 2-step memory"
    x_range = (-1.4, 1.4)
    y_range = (-1.1, 1.1)
    p_const = complex(-0.5, 0.0)
    c_const = complex(0.5667, 0.0)
    palette_offset = 0.72

    def render_rows(self, y0, y1):
        x0, x1 = self.x_range
        ymin, ymax = self.y_range
        xs = np.linspace(x0, x1, self.w)
        ys = np.linspace(ymin, ymax, self.h)[y0:y1]
        cx, cy = np.meshgrid(xs, ys)
        z = cx + 1j * cy
        z_prev = np.zeros_like(z)
        div = np.zeros(z.shape, dtype=np.int32)
        mask = np.ones(z.shape, dtype=bool)
        for i in range(1, self.max_iter + 1):
            z_new = z * z + self.c_const + self.p_const * z_prev
            z_prev = np.where(mask, z, z_prev)
            z = np.where(mask, z_new, z)
            diverged = mask & (np.abs(z) > 4.0)
            div[diverged] = i
            mask &= ~diverged
            if not mask.any():
                break
        rgb = self.palette[div]
        rgb_t = rgb.transpose(1, 0, 2)
        sub = pygame.surfarray.make_surface(rgb_t)
        self.surface.blit(sub, (0, y0))


class LyapunovFractal(FractalPage):
    """Lyapunov fractal — string 'AB' over (a,b) parameter plane."""
    name = "Lyapunov AB"
    category = "A"
    info = "Lyapunov exponent over (a,b) plane · sequence 'AB' · Markus 1989"
    rows_per_frame = 8
    max_iter = 90
    a_range = (3.4, 4.0)
    b_range = (3.4, 4.0)
    seq = "AB"

    def reset(self):
        super().reset()
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(BG)
        self.row = 0

    def update(self, frame):
        if self.row >= self.h:
            return
        y1 = min(self.h, self.row + self.rows_per_frame)
        a_min, a_max = self.a_range
        b_min, b_max = self.b_range
        a = np.linspace(a_min, a_max, self.w)
        b = np.linspace(b_min, b_max, self.h)[self.row:y1]
        A, B = np.meshgrid(a, b)
        x = np.full_like(A, 0.5)
        lam = np.zeros_like(A)
        for n in range(1, self.max_iter + 1):
            r = A if self.seq[n % len(self.seq)] == "A" else B
            x = r * x * (1 - x)
            x = np.clip(x, 1e-10, 1 - 1e-10)
            lam += np.log(np.abs(r * (1 - 2 * x)))
        lam /= self.max_iter
        # negative lambda → stable (yellow-green); positive → chaos (blue-violet)
        rgb = np.zeros((*lam.shape, 3), dtype=np.uint8)
        neg = lam < 0
        pos = ~neg
        rgb[neg, 0] = np.clip(255 * (-lam[neg] / 1.5), 0, 255)
        rgb[neg, 1] = np.clip(180 + 70 * (-lam[neg] / 1.5), 0, 255)
        rgb[pos, 2] = np.clip(40 + 200 * lam[pos], 0, 255)
        rgb[pos, 0] = np.clip(20 + 60 * lam[pos], 0, 80)
        rgb_t = rgb.transpose(1, 0, 2)
        sub = pygame.surfarray.make_surface(rgb_t)
        self.surface.blit(sub, (0, self.row))
        self.row = y1

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


class Buddhabrot(FractalPage):
    """Buddhabrot — accumulate orbits of *escaping* points back into the plane."""
    name = "Buddhabrot"
    category = "A"
    info = "Mandelbrot orbit-density of escaping points · Melinda Green 1993"

    samples_per_frame = 25_000
    max_iter = 80
    x_range = (-2.0, 1.0)
    y_range = (-1.5, 1.5)

    def reset(self):
        super().reset()
        self.density = np.zeros((self.h, self.w), dtype=np.float32)
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(BG)
        self.frames_done = 0

    def update(self, frame):
        if self.frames_done > 80:
            return
        x0, x1 = self.x_range
        y0, y1 = self.y_range
        cs_re = np.random.uniform(x0, x1, self.samples_per_frame)
        cs_im = np.random.uniform(y0, y1, self.samples_per_frame)
        cs = cs_re + 1j * cs_im
        zs = np.zeros_like(cs)
        traj_re = np.zeros((self.max_iter, self.samples_per_frame), dtype=np.float32)
        traj_im = np.zeros((self.max_iter, self.samples_per_frame), dtype=np.float32)
        active = np.ones(self.samples_per_frame, dtype=bool)
        escaped_at = np.zeros(self.samples_per_frame, dtype=np.int32)
        for i in range(self.max_iter):
            zs[active] = zs[active] ** 2 + cs[active]
            traj_re[i] = zs.real
            traj_im[i] = zs.imag
            esc = active & (np.abs(zs) > 2.0)
            escaped_at[esc] = i
            active &= ~esc
        # accumulate only escaping orbits
        for s in range(self.samples_per_frame):
            ea = escaped_at[s]
            if ea == 0:
                continue
            for i in range(ea):
                rx = traj_re[i, s]
                ry = traj_im[i, s]
                px = int((rx - x0) / (x1 - x0) * self.w)
                py = int((ry - y0) / (y1 - y0) * self.h)
                if 0 <= px < self.w and 0 <= py < self.h:
                    self.density[py, px] += 1
        # render
        m = self.density.max()
        if m > 0:
            norm = np.power(self.density / m, 0.4)
            r = (norm * 220).astype(np.uint8)
            g = (norm * 180).astype(np.uint8)
            b = (norm * 255).astype(np.uint8)
            rgb = np.stack([r, g, b], axis=-1)
            rgb_t = rgb.transpose(1, 0, 2)
            sub = pygame.surfarray.make_surface(rgb_t)
            self.surface.blit(sub, (0, 0))
        self.frames_done += 1

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


# ──────────────────────────────────────────────────────────────────────────────
# CATEGORY B — IFS / CHAOS GAME / SELF-SIMILAR
# ──────────────────────────────────────────────────────────────────────────────

class IFSChaosFractal(FractalPage):
    """Chaos-game IFS: pick a random affine transform, apply, plot."""
    category = "B"
    transforms: list[tuple] = []        # list of (a,b,c,d,e,f, prob)
    point_color = (255, 255, 255)
    points_per_frame = 1500
    total_points = 60_000
    fit_padding = 30

    def reset(self):
        super().reset()
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(BG)
        self.x, self.y = 0.0, 0.0
        self.n = 0
        self._compute_bounds()

    def _compute_bounds(self):
        # Quick Monte-Carlo to find bounding box of the attractor
        x, y = 0.0, 0.0
        xs, ys = [], []
        for _ in range(2000):
            t = self._pick_transform()
            x, y = t[0] * x + t[1] * y + t[4], t[2] * x + t[3] * y + t[5]
            xs.append(x); ys.append(y)
        self.bx0, self.bx1 = min(xs), max(xs)
        self.by0, self.by1 = min(ys), max(ys)

    def _pick_transform(self):
        r = random.random()
        cumulative = 0.0
        for t in self.transforms:
            cumulative += t[6]
            if r < cumulative:
                return t
        return self.transforms[-1]

    def _to_screen(self, x, y):
        bx0, bx1, by0, by1 = self.bx0, self.bx1, self.by0, self.by1
        bw, bh = bx1 - bx0, by1 - by0
        sw, sh = self.w - 2 * self.fit_padding, self.h - 2 * self.fit_padding
        scale = min(sw / max(bw, 1e-9), sh / max(bh, 1e-9))
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        return (int(self.w / 2 + (x - cx) * scale),
                int(self.h / 2 - (y - cy) * scale))

    def update(self, frame):
        if self.n >= self.total_points:
            return
        for _ in range(self.points_per_frame):
            t = self._pick_transform()
            self.x, self.y = (t[0] * self.x + t[1] * self.y + t[4],
                              t[2] * self.x + t[3] * self.y + t[5])
            sx, sy = self._to_screen(self.x, self.y)
            if 0 <= sx < self.w and 0 <= sy < self.h:
                self.surface.set_at((sx, sy), self.point_color)
        self.n += self.points_per_frame

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


class SierpinskiTriangleIFS(IFSChaosFractal):
    name = "Sierpiński Triangle"
    info = "3 contractions toward triangle vertices · D ≈ 1.585"
    point_color = (130, 215, 30)
    transforms = [
        (0.5, 0, 0, 0.5, 0,    0,    1 / 3),
        (0.5, 0, 0, 0.5, 0.5,  0,    1 / 3),
        (0.5, 0, 0, 0.5, 0.25, 0.5,  1 / 3),
    ]


class SierpinskiCarpet(IFSChaosFractal):
    name = "Sierpiński Carpet"
    info = "8 contractions over 3×3 grid (centre removed) · D ≈ 1.893"
    point_color = (230, 230, 100)
    transforms = []
    for i in range(3):
        for j in range(3):
            if not (i == 1 and j == 1):
                transforms.append((1 / 3, 0, 0, 1 / 3, i / 3, j / 3, 1 / 8))
    del i, j


class SierpinskiHexagon(IFSChaosFractal):
    name = "Sierpiński Hexagon"
    info = "6 hexagonal contractions · D ≈ 1.633"
    point_color = (140, 200, 240)
    transforms = []
    _r = 1 / 3
    for k in range(6):
        ang = math.pi * k / 3
        cx_, cy_ = math.cos(ang), math.sin(ang)
        transforms.append((_r, 0, 0, _r, cx_ * (1 - _r), cy_ * (1 - _r), 1 / 6))
    del k, ang, cx_, cy_, _r


class CantorSetIFS(IFSChaosFractal):
    name = "Cantor Set"
    info = "2 contractions on a line · D ≈ 0.631"
    point_color = (20, 190, 215)
    transforms = [
        (1 / 3, 0, 0, 0.001, 0, 0, 0.5),
        (1 / 3, 0, 0, 0.001, 2 / 3, 0, 0.5),
    ]
    points_per_frame = 800
    total_points = 30_000


class VicsekFractal(IFSChaosFractal):
    name = "Vicsek Fractal"
    info = "4 corner + 1 centre contraction (plus form) · D ≈ 1.465"
    point_color = (220, 80, 200)
    transforms = [
        (1 / 3, 0, 0, 1 / 3, 0,     0,     0.2),
        (1 / 3, 0, 0, 1 / 3, 2 / 3, 0,     0.2),
        (1 / 3, 0, 0, 1 / 3, 0,     2 / 3, 0.2),
        (1 / 3, 0, 0, 1 / 3, 2 / 3, 2 / 3, 0.2),
        (1 / 3, 0, 0, 1 / 3, 1 / 3, 1 / 3, 0.2),
    ]


class TSquareFractal(IFSChaosFractal):
    name = "T-Square"
    info = "4 corner contractions, half-scale · D = 2"
    point_color = (170, 130, 220)
    transforms = [
        (0.5, 0, 0, 0.5, -0.5, -0.5, 0.25),
        (0.5, 0, 0, 0.5,  0.5, -0.5, 0.25),
        (0.5, 0, 0, 0.5, -0.5,  0.5, 0.25),
        (0.5, 0, 0, 0.5,  0.5,  0.5, 0.25),
    ]


class HeighwayDragonIFS(IFSChaosFractal):
    name = "Heighway Dragon"
    info = "2 affines, 90° rotations · D ≈ 1.524"
    point_color = (220, 80, 110)
    transforms = [
        ( 0.5, -0.5, 0.5,  0.5, 0, 0, 0.5),
        (-0.5, -0.5, 0.5, -0.5, 1, 0, 0.5),
    ]


class TwindragonIFS(IFSChaosFractal):
    name = "Twindragon"
    info = "Two Heighway dragons together · D ≈ 1.524"
    point_color = (255, 140, 90)
    transforms = [
        ( 0.5, -0.5, 0.5,  0.5,  0, 0, 0.5),
        (-0.5,  0.5, -0.5, -0.5, 1, 0, 0.5),
    ]


class LevyCIFS(IFSChaosFractal):
    name = "Lévy C Curve"
    info = "Two 45° contractions · D = 2 (space-filling)"
    point_color = (240, 162, 40)
    transforms = [
        (0.5, -0.5, 0.5,  0.5, 0,   0,   0.5),
        (0.5,  0.5, -0.5, 0.5, 0.5, 0.5, 0.5),
    ]


class BarnsleyFernIFS(IFSChaosFractal):
    name = "Barnsley Fern"
    info = "Barnsley 1988 · 4 affines, plant-like attractor"
    point_color = (130, 215, 30)
    transforms = [
        (0,     0,    0,    0.16, 0, 0,    0.01),
        (0.85,  0.04, -0.04, 0.85, 0, 1.6,  0.85),
        (0.20, -0.26, 0.23,  0.22, 0, 1.6,  0.07),
        (-0.15, 0.28, 0.26,  0.24, 0, 0.44, 0.07),
    ]
    total_points = 80_000


class PlusFractal(IFSChaosFractal):
    name = "Plus Sign"
    info = "5 contractions in plus pattern · D ≈ 1.465"
    point_color = (200, 240, 130)
    _r = 1 / 3
    transforms = [
        (_r, 0, 0, _r,  0,    -_r,  0.2),  # bottom
        (_r, 0, 0, _r,  0,     _r,  0.2),  # top
        (_r, 0, 0, _r, -_r,    0,   0.2),  # left
        (_r, 0, 0, _r,  _r,    0,   0.2),  # right
        (_r, 0, 0, _r,  0,     0,   0.2),  # centre
    ]
    del _r


# Deterministic line-iter forms (Koch family)

class DeterministicCurve(FractalPage):
    """Iteratively expand a polyline by a per-segment rule. Animate by drawing
    progressively more points each frame."""
    category = "B"
    iterations = 6
    line_width = 1
    color = (218, 228, 248)

    def axiom_points(self) -> list[tuple[float, float]]:
        return [(0.0, 0.0), (1.0, 0.0)]

    def expand(self, p0, p1) -> list[tuple[float, float]]:
        """Override: replace segment p0→p1 with a list of points."""
        return [p0, p1]

    def reset(self):
        super().reset()
        pts = self.axiom_points()
        for _ in range(self.iterations):
            new_pts = [pts[0]]
            for i in range(len(pts) - 1):
                seg = self.expand(pts[i], pts[i + 1])
                new_pts.extend(seg[1:])
            pts = new_pts
        # normalise
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
        bw, bh = bx1 - bx0, by1 - by0
        pad = 60
        scale = min((self.w - 2 * pad) / max(bw, 1e-9), (self.h - 2 * pad) / max(bh, 1e-9))
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        self.points = [(int(self.w / 2 + (x - cx) * scale),
                        int(self.h / 2 - (y - cy) * scale)) for x, y in pts]
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(BG)
        self.idx = 0
        self.step = max(1, len(self.points) // 240)

    def update(self, frame):
        if self.idx + 1 >= len(self.points):
            return
        end = min(len(self.points), self.idx + self.step)
        if end - self.idx > 1:
            pygame.draw.lines(self.surface, self.color, False,
                              self.points[self.idx:end + 1], self.line_width)
        self.idx = end

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


def _rot(angle):
    c, s = math.cos(angle), math.sin(angle)
    return c, s


def _seg_rotated(p0, p1, frac, angle):
    """Insert a peak between p0 and p1, displaced by `frac` along the segment
    and rotated `angle` radians."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    base_x, base_y = p0[0] + frac * dx, p0[1] + frac * dy
    # rotate (dx, dy) by `angle`, scale by frac
    c, s = math.cos(angle), math.sin(angle)
    rx = c * dx - s * dy
    ry = s * dx + c * dy
    peak_x = p0[0] + rx * frac
    peak_y = p0[1] + ry * frac
    return base_x, base_y, peak_x, peak_y


class KochCurve(DeterministicCurve):
    name = "Koch Curve"
    info = "Each segment → 4 segments with central peak · D ≈ 1.262"
    color = (140, 215, 90)
    iterations = 5

    def expand(self, p0, p1):
        x0, y0 = p0; x1, y1 = p1
        ax, ay = x0 + (x1 - x0) / 3, y0 + (y1 - y0) / 3
        bx, by = x0 + 2 * (x1 - x0) / 3, y0 + 2 * (y1 - y0) / 3
        # peak at 60° from a→b, length = |ab|
        dx, dy = bx - ax, by - ay
        c, s = math.cos(math.pi / 3), math.sin(math.pi / 3)
        px = ax + (c * dx - s * dy)
        py = ay + (s * dx + c * dy)
        return [p0, (ax, ay), (px, py), (bx, by), p1]


class KochSnowflake(DeterministicCurve):
    name = "Koch Snowflake"
    info = "Koch curve on equilateral triangle · D ≈ 1.262"
    color = (180, 240, 220)
    iterations = 4

    def axiom_points(self):
        # equilateral triangle (closed)
        h = math.sqrt(3) / 2
        return [(0.0, 0.0), (1.0, 0.0), (0.5, h), (0.0, 0.0)]

    def expand(self, p0, p1):
        x0, y0 = p0; x1, y1 = p1
        ax, ay = x0 + (x1 - x0) / 3, y0 + (y1 - y0) / 3
        bx, by = x0 + 2 * (x1 - x0) / 3, y0 + 2 * (y1 - y0) / 3
        dx, dy = bx - ax, by - ay
        c, s = math.cos(math.pi / 3), math.sin(math.pi / 3)
        px = ax + (c * dx - s * dy)
        py = ay + (s * dx + c * dy)
        return [p0, (ax, ay), (px, py), (bx, by), p1]


class PythagorasTree(FractalPage):
    """Pythagoras tree of squares, recursive."""
    name = "Pythagoras Tree"
    category = "B"
    info = "Square + two child squares at 45°/45° · classic recursion"
    depth = 11
    color = (180, 230, 130)

    def reset(self):
        super().reset()
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(BG)
        self.theta = math.radians(45)
        self.tick = 0
        self._render()

    def _render(self):
        self.surface.fill(BG)
        size = self.h * 0.18
        cx = self.w / 2
        bottom_y = self.h - 80
        # initial square corners (clockwise from bottom-left)
        a = complex(cx - size / 2, bottom_y)
        b = complex(cx + size / 2, bottom_y)
        self._draw_square(a, b, self.depth)

    def _draw_square(self, a: complex, b: complex, n: int):
        if n == 0:
            return
        # vector along bottom edge
        ab = b - a
        # perpendicular up (in screen coords y grows downward → use -1j)
        perp = ab * (-1j)
        c = b + perp
        d = a + perp
        # draw square
        pts = [(int(z.real), int(z.imag)) for z in (a, b, c, d)]
        alpha = 0.30 + 0.65 * (n / self.depth)
        col = tuple(int(c_ * alpha) for c_ in self.color)
        pygame.draw.polygon(self.surface, col, pts, 1)
        # apex (right-angled triangle on top: split d→c at angle theta)
        th = self.theta
        # left child: rotate (c - d) by -th and scale by cos(th)
        rot_l = complex(math.cos(-th), math.sin(-th)) * math.cos(th)
        rot_r = complex(math.cos(math.pi / 2 - th), math.sin(math.pi / 2 - th)) * math.sin(th)
        apex = d + (c - d) * rot_l
        # left child square
        self._draw_square(d, apex, n - 1)
        # right child square
        self._draw_square(apex, c, n - 1)

    def update(self, frame):
        # gentle theta breathing
        self.theta = math.radians(28 + 28 * (1 + math.sin(frame * 0.012)))
        if frame % 4 == 0:
            self._render()

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


class ApollonianGasket(FractalPage):
    """Apollonian gasket — recursive circle packing inside a curvature triple."""
    name = "Apollonian Gasket"
    category = "B"
    info = "Tangent-circle recursion · Descartes' theorem"
    depth = 8
    color = (110, 180, 220)

    def reset(self):
        super().reset()
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(BG)
        # outer circle (concave) curvature = -1/R
        cx, cy = self.w / 2, self.h / 2
        R = min(self.w, self.h) * 0.42
        # use Descartes-Soddy: 3 inner circles of equal radius r₀ touching each other and outer
        # r0 such that 3*r0 + 2*r0/sqrt(3) = R  (approximate canonical packing)
        r0 = R * (2 * math.sqrt(3) - 3)
        # actually use the canonical gasket: outer r=1, three inner r = 1/(2+2/sqrt(3))
        r1 = R / (2 + 2 / math.sqrt(3))
        # three positions around centre at 120°
        circles = [(cx, cy, -1 / R)]   # outer (negative curvature)
        for k in range(3):
            ang = math.pi / 2 + 2 * math.pi * k / 3
            x = cx + (R - r1) * math.cos(ang)
            y = cy + (R - r1) * math.sin(ang)
            circles.append((x, y, 1 / r1))
        # draw initial 4
        for (x, y, k) in circles:
            r = abs(1 / k)
            if r < 2: continue
            pygame.draw.circle(self.surface, self.color, (int(x), int(y)), int(r), 1)
        # recursive Soddy-fill: for each triple, compute the two new tangent circles via Descartes
        self._fill(circles[0], circles[1], circles[2], self.depth)
        self._fill(circles[0], circles[2], circles[3], self.depth)
        self._fill(circles[0], circles[1], circles[3], self.depth)
        self._fill(circles[1], circles[2], circles[3], self.depth)

    def _fill(self, c1, c2, c3, n):
        if n == 0: return
        # Descartes: k4 = k1+k2+k3 ± 2√(k1 k2 + k2 k3 + k1 k3)
        k1, k2, k3 = c1[2], c2[2], c3[2]
        s = k1 * k2 + k2 * k3 + k1 * k3
        if s < 0: return
        ks = math.sqrt(s)
        for sign in (+1, -1):
            k4 = k1 + k2 + k3 + sign * 2 * ks
            if abs(k4) < 1e-3: continue
            # complex centre formula
            z1 = complex(c1[0], c1[1]); z2 = complex(c2[0], c2[1]); z3 = complex(c3[0], c3[1])
            # weighted Descartes
            try:
                w_inner = z1 * z2 * k1 * k2 + z2 * z3 * k2 * k3 + z1 * z3 * k1 * k3
                z4 = (z1 * k1 + z2 * k2 + z3 * k3 + sign * 2 * (w_inner) ** 0.5) / k4
            except Exception:
                continue
            r4 = abs(1 / k4)
            if r4 < 1.5 or r4 > min(self.w, self.h) / 2: continue
            x4, y4 = z4.real, z4.imag
            if not (0 < x4 < self.w and 0 < y4 < self.h): continue
            pygame.draw.circle(self.surface, self.color, (int(x4), int(y4)), int(r4), 1)
            new_c = (x4, y4, k4)
            self._fill(c1, c2, new_c, n - 1)
            self._fill(c2, c3, new_c, n - 1)
            self._fill(c1, c3, new_c, n - 1)

    def update(self, frame): pass
    def draw(self, screen): screen.blit(self.surface, (0, 0))


# ──────────────────────────────────────────────────────────────────────────────
# CATEGORY C — L-SYSTEMS
# ──────────────────────────────────────────────────────────────────────────────

class LSystemFractal(FractalPage):
    """Generic L-system: axiom + rules + turtle drawing.

    Subclass overrides:
        axiom, rules, angle_deg, iterations, draw_chars, length
    """
    category = "C"
    axiom = "F"
    rules: dict[str, str] = {}
    angle_deg = 90
    iterations = 4
    draw_chars = ("F",)
    length = 10
    line_color = (218, 228, 248)
    line_width = 1
    start_dir_deg = -90
    pad = 50

    def reset(self):
        super().reset()
        # expand
        s = self.axiom
        for _ in range(self.iterations):
            s = "".join(self.rules.get(ch, ch) for ch in s)
        # turtle-walk to get points
        points = [(0.0, 0.0)]
        x, y = 0.0, 0.0
        head = math.radians(self.start_dir_deg)
        a = math.radians(self.angle_deg)
        stack: list[tuple[float, float, float]] = []
        for ch in s:
            if ch in self.draw_chars:
                x += self.length * math.cos(head)
                y += self.length * math.sin(head)
                points.append((x, y))
            elif ch == "f":
                x += self.length * math.cos(head); y += self.length * math.sin(head)
                points.append((None, None)); points.append((x, y))   # pen-up break
            elif ch == "+":
                head += a
            elif ch == "-":
                head -= a
            elif ch == "[":
                stack.append((x, y, head))
            elif ch == "]":
                if stack:
                    x, y, head = stack.pop()
                    points.append((None, None)); points.append((x, y))
        # bbox + scale
        xs = [p[0] for p in points if p[0] is not None]
        ys = [p[1] for p in points if p[1] is not None]
        if not xs:
            self.points = []
            self.surface = pygame.Surface((self.w, self.h)); self.surface.fill(BG); return
        bx0, bx1 = min(xs), max(xs); by0, by1 = min(ys), max(ys)
        bw, bh = bx1 - bx0, by1 - by0
        scale = min((self.w - 2 * self.pad) / max(bw, 1e-9),
                    (self.h - 2 * self.pad) / max(bh, 1e-9))
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
        self.points = [(None if p[0] is None else
                        (int(self.w / 2 + (p[0] - cx) * scale),
                         int(self.h / 2 + (p[1] - cy) * scale)))
                       for p in points]
        self.surface = pygame.Surface((self.w, self.h)); self.surface.fill(BG)
        self.idx = 0
        self.step = max(1, len(self.points) // 220)

    def update(self, frame):
        if not self.points:
            return
        if self.idx + 1 >= len(self.points):
            return
        end = min(len(self.points), self.idx + self.step)
        # draw segments, splitting on None breaks
        run = []
        for i in range(self.idx, end + 1):
            p = self.points[i] if i < len(self.points) else None
            if p is None or (isinstance(p, tuple) and p[0] is None):
                if len(run) >= 2:
                    pygame.draw.lines(self.surface, self.line_color, False, run, self.line_width)
                run = []
            else:
                run.append(p)
        if len(run) >= 2:
            pygame.draw.lines(self.surface, self.line_color, False, run, self.line_width)
        self.idx = end

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


class BinaryTreeLS(LSystemFractal):
    name = "Binary Tree (L-system)"
    info = "F → FF+[+F-F-F]-[-F+F+F] · classic branching"
    axiom = "F"
    rules = {"F": "FF+[+F-F-F]-[-F+F+F]"}
    angle_deg = 22.5
    iterations = 4
    length = 5
    line_color = (130, 215, 30)
    start_dir_deg = -90


class HilbertCurve(LSystemFractal):
    name = "Hilbert Curve"
    info = "Space-filling curve · D = 2"
    axiom = "X"
    rules = {"X": "+YF-XFX-FY+", "Y": "-XF+YFY+FX-"}
    angle_deg = 90
    iterations = 6
    length = 6
    line_color = (240, 162, 40)
    start_dir_deg = 0


class PeanoCurve(LSystemFractal):
    name = "Peano Curve"
    info = "Peano 1890 · space-filling · D = 2"
    axiom = "X"
    rules = {"X": "XFYFX+F+YFXFY-F-XFYFX",
             "Y": "YFXFY-F-XFYFX+F+YFXFY"}
    angle_deg = 90
    iterations = 3
    length = 4
    line_color = (220, 80, 200)


class GosperCurve(LSystemFractal):
    name = "Gosper Curve (flowsnake)"
    info = "Hex space-filling · D = 2"
    axiom = "A"
    rules = {"A": "A-B--B+A++AA+B-",
             "B": "+A-BB--B-A++A+B"}
    draw_chars = ("A", "B")
    angle_deg = 60
    iterations = 4
    length = 8
    line_color = (200, 240, 130)


class SierpinskiArrowhead(LSystemFractal):
    name = "Sierpiński Arrowhead"
    info = "Curve approximation of Sierpiński triangle · D ≈ 1.585"
    axiom = "A"
    rules = {"A": "+B-A-B+", "B": "-A+B+A-"}
    draw_chars = ("A", "B")
    angle_deg = 60
    iterations = 6
    length = 5
    line_color = (220, 180, 60)


class PlantOne(LSystemFractal):
    name = "L-system Plant 1"
    info = "Lindenmayer plant · F → F[+F]F[-F]F"
    axiom = "F"
    rules = {"F": "F[+F]F[-F]F"}
    angle_deg = 25.7
    iterations = 4
    length = 3
    line_color = (140, 215, 90)


class PlantTwo(LSystemFractal):
    name = "L-system Plant 2"
    info = "Bushy plant · F → FF-[-F+F+F]+[+F-F-F]"
    axiom = "F"
    rules = {"F": "FF-[-F+F+F]+[+F-F-F]"}
    angle_deg = 22.5
    iterations = 4
    length = 4
    line_color = (110, 220, 140)


class PenroseTiling(FractalPage):
    """Penrose P3 (rhombs) — recursive subdivision rendering."""
    name = "Penrose P3 (approx)"
    category = "C"
    info = "Thin + fat rhomb subdivision · 5-fold quasi-periodic"
    depth = 6
    color_thin = (130, 90, 200)
    color_fat = (220, 170, 70)

    def reset(self):
        super().reset()
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(BG)
        # initial sun: 10 fat rhombs around centre
        cx, cy = self.w / 2, self.h / 2
        R = min(self.w, self.h) * 0.45
        triangles: list[tuple[int, complex, complex, complex]] = []
        for i in range(10):
            a1 = (2 * i - 1) * math.pi / 10
            a2 = (2 * i + 1) * math.pi / 10
            v1 = complex(cx + R * math.cos(a1), cy + R * math.sin(a1))
            v2 = complex(cx + R * math.cos(a2), cy + R * math.sin(a2))
            v0 = complex(cx, cy)
            if i % 2 == 0:
                triangles.append((0, v0, v1, v2))
            else:
                triangles.append((0, v0, v2, v1))
        for _ in range(self.depth):
            triangles = self._subdivide(triangles)
        # draw — group by type
        for kind, A, B, C in triangles:
            pts = [(int(A.real), int(A.imag)),
                   (int(B.real), int(B.imag)),
                   (int(C.real), int(C.imag))]
            col = self.color_thin if kind == 1 else self.color_fat
            pygame.draw.polygon(self.surface, col, pts, 1)

    def _subdivide(self, triangles):
        phi_inv = 1 / PHI
        out = []
        for kind, A, B, C in triangles:
            if kind == 0:  # half-fat (acute Robinson)
                P = A + (B - A) * phi_inv
                out.append((0, C, P, B))
                out.append((1, P, C, A))
            else:  # half-thin (obtuse Robinson)
                Q = B + (A - B) * phi_inv
                R = B + (C - B) * phi_inv
                out.append((1, R, C, A))
                out.append((1, Q, R, B))
                out.append((0, R, Q, A))
        return out

    def update(self, frame): pass
    def draw(self, screen): screen.blit(self.surface, (0, 0))


# ──────────────────────────────────────────────────────────────────────────────
# CATEGORY D — STRANGE ATTRACTORS
# ──────────────────────────────────────────────────────────────────────────────

class StrangeAttractor(FractalPage):
    """3D continuous attractor projected to 2D, or 2D map iterated."""
    category = "D"
    points_per_frame = 2500
    total_points = 250_000
    color = (240, 162, 40)
    point_alpha = 0.35
    fit_3d = False

    def step(self, x, y, z):
        """Override: return next (x, y, z) — used for both 2D maps (z ignored)
        and 3D continuous (RK4-like) systems."""
        raise NotImplementedError

    def reset(self):
        super().reset()
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(BG)
        self.x, self.y, self.z = 0.1, 0.0, 0.0
        self.n = 0
        # estimate bounds
        bx0 = by0 = math.inf
        bx1 = by1 = -math.inf
        x, y, z = self.x, self.y, self.z
        for _ in range(3000):
            x, y, z = self.step(x, y, z)
            bx0 = min(bx0, x); bx1 = max(bx1, x)
            by0 = min(by0, y); by1 = max(by1, y)
        self.bx0, self.bx1, self.by0, self.by1 = bx0, bx1, by0, by1
        self.x, self.y, self.z = 0.1, 0.0, 0.0

    def _to_screen(self, x, y):
        bw = self.bx1 - self.bx0; bh = self.by1 - self.by0
        pad = 40
        scale = min((self.w - 2 * pad) / max(bw, 1e-9), (self.h - 2 * pad) / max(bh, 1e-9))
        cx = (self.bx0 + self.bx1) / 2; cy = (self.by0 + self.by1) / 2
        return int(self.w / 2 + (x - cx) * scale), int(self.h / 2 - (y - cy) * scale)

    def update(self, frame):
        if self.n >= self.total_points:
            return
        col = self.color
        for _ in range(self.points_per_frame):
            self.x, self.y, self.z = self.step(self.x, self.y, self.z)
            sx, sy = self._to_screen(self.x, self.y)
            if 0 <= sx < self.w and 0 <= sy < self.h:
                self.surface.set_at((sx, sy), col)
        self.n += self.points_per_frame

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


class LorenzAttractor(StrangeAttractor):
    name = "Lorenz Attractor"
    info = "ẋ = σ(y−x), ẏ = x(ρ−z)−y, ż = xy−βz · σ=10, ρ=28, β=8/3"
    color = (130, 200, 250)
    sigma, rho, beta = 10.0, 28.0, 8 / 3
    dt = 0.005

    def step(self, x, y, z):
        dx = self.sigma * (y - x)
        dy = x * (self.rho - z) - y
        dz = x * y - self.beta * z
        return x + dx * self.dt, y + dy * self.dt, z + dz * self.dt


class RosslerAttractor(StrangeAttractor):
    name = "Rössler Attractor"
    info = "ẋ = −y−z, ẏ = x+ay, ż = b+z(x−c) · a=0.2, b=0.2, c=5.7"
    color = (200, 130, 240)
    a, b, c = 0.2, 0.2, 5.7
    dt = 0.02

    def step(self, x, y, z):
        return (x + (-y - z) * self.dt,
                y + (x + self.a * y) * self.dt,
                z + (self.b + z * (x - self.c)) * self.dt)


class AizawaAttractor(StrangeAttractor):
    name = "Aizawa Attractor"
    info = "Aizawa system · spherical core with helical loops"
    color = (255, 180, 80)
    a, b, c, d, e, f = 0.95, 0.7, 0.6, 3.5, 0.25, 0.1
    dt = 0.01

    def step(self, x, y, z):
        dx = (z - self.b) * x - self.d * y
        dy = self.d * x + (z - self.b) * y
        dz = self.c + self.a * z - z ** 3 / 3 - (x * x + y * y) * (1 + self.e * z) + self.f * z * x ** 3
        return x + dx * self.dt, y + dy * self.dt, z + dz * self.dt


class CliffordAttractor(StrangeAttractor):
    name = "Clifford Attractor"
    info = "x' = sin(ay)+c·cos(ax), y' = sin(bx)+d·cos(by) · Pickover 1990s"
    color = (220, 80, 130)
    a, b, c, d = -1.4, 1.6, 1.0, 0.7
    points_per_frame = 5000

    def step(self, x, y, z):
        return (math.sin(self.a * y) + self.c * math.cos(self.a * x),
                math.sin(self.b * x) + self.d * math.cos(self.b * y),
                0.0)


class DeJongAttractor(StrangeAttractor):
    name = "De Jong Attractor"
    info = "x' = sin(ay)−cos(bx), y' = sin(cx)−cos(dy)"
    color = (130, 230, 160)
    a, b, c, d = 1.4, -2.3, 2.4, -2.1
    points_per_frame = 5000

    def step(self, x, y, z):
        return (math.sin(self.a * y) - math.cos(self.b * x),
                math.sin(self.c * x) - math.cos(self.d * y),
                0.0)


class IkedaMap(StrangeAttractor):
    name = "Ikeda Map"
    info = "z' = A + B·z·exp(i(C − D/(1+|z|²))) · Ikeda 1979"
    color = (250, 200, 100)
    A, B, C, D = 1.0, 0.9, 0.4, 6.0
    points_per_frame = 5000

    def step(self, x, y, z):
        t = self.C - self.D / (1 + x * x + y * y)
        return (self.A + self.B * (x * math.cos(t) - y * math.sin(t)),
                self.B * (x * math.sin(t) + y * math.cos(t)),
                0.0)


class HenonMap(StrangeAttractor):
    name = "Hénon Map"
    info = "x' = 1 − ax² + y, y' = bx · Hénon 1976 · a=1.4, b=0.3"
    color = (200, 120, 220)
    a, b = 1.4, 0.3
    points_per_frame = 5000

    def step(self, x, y, z):
        return (1 - self.a * x * x + y, self.b * x, 0.0)


# ──────────────────────────────────────────────────────────────────────────────
# CATEGORY E — SACRED GEOMETRY (per ContextForge canon)
# ──────────────────────────────────────────────────────────────────────────────

class SacredGeometryForm(FractalPage):
    """Static geometric figure with subtle animation."""
    category = "E"
    color = (212, 164, 55)

    def render(self):
        """Override: draw the form into self.surface."""
        pass

    def reset(self):
        super().reset()
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(BG)
        self.render()

    def update(self, frame):
        pass

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


class VesicaPiscis(SacredGeometryForm):
    name = "Vesica Piscis"
    info = "Two equal circles, each centred on the other's circumference"
    color = (212, 164, 55)

    def render(self):
        cx, cy = self.w / 2, self.h / 2
        r = min(self.w, self.h) * 0.22
        pygame.draw.circle(self.surface, self.color, (int(cx - r / 2), int(cy)), int(r), 2)
        pygame.draw.circle(self.surface, self.color, (int(cx + r / 2), int(cy)), int(r), 2)
        # axis
        pygame.draw.line(self.surface, DIM, (int(cx), int(cy - r)), (int(cx), int(cy + r)), 1)


class SeedOfLife(SacredGeometryForm):
    name = "Seed of Life"
    info = "7 circles: 1 centre + 6 perimeter on hexagonal lattice"

    def render(self):
        cx, cy = self.w / 2, self.h / 2
        r = min(self.w, self.h) * 0.18
        pygame.draw.circle(self.surface, self.color, (int(cx), int(cy)), int(r), 2)
        for k in range(6):
            ang = math.pi / 3 * k
            x = cx + r * math.cos(ang)
            y = cy + r * math.sin(ang)
            pygame.draw.circle(self.surface, self.color, (int(x), int(y)), int(r), 2)


class FlowerOfLife(SacredGeometryForm):
    name = "Flower of Life"
    info = "Hexagonal lattice of circles · 19-circle canonical form"
    color = (220, 180, 80)

    def render(self):
        cx, cy = self.w / 2, self.h / 2
        r = min(self.w, self.h) * 0.10
        # 19 circles in hex packing
        positions = [(0, 0)]
        for ring in (1, 2):
            for k in range(6 * ring):
                ang = math.pi / 3 * (k / ring) + (math.pi / 6 if ring == 2 and k % 2 == 1 else 0)
                positions.append((ring * r * math.cos(ang), ring * r * math.sin(ang)))
        # use a cleaner hex: 1 + 6 + 12 = 19
        positions = [(0, 0)]
        for k in range(6):
            ang = math.pi / 3 * k
            positions.append((r * math.cos(ang), r * math.sin(ang)))
        for k in range(6):
            ang = math.pi / 3 * k
            positions.append((2 * r * math.cos(ang), 2 * r * math.sin(ang)))
        for k in range(6):
            ang = math.pi / 3 * k + math.pi / 6
            positions.append((math.sqrt(3) * r * math.cos(ang), math.sqrt(3) * r * math.sin(ang)))
        for (dx, dy) in positions:
            pygame.draw.circle(self.surface, self.color, (int(cx + dx), int(cy + dy)), int(r), 2)
        # outer boundary
        pygame.draw.circle(self.surface, DIM, (int(cx), int(cy)), int(3 * r), 1)


class MetatronCube(SacredGeometryForm):
    name = "Metatron's Cube"
    info = "13 spheres of Fruit of Life joined by all line segments"
    color = (200, 160, 240)

    def render(self):
        cx, cy = self.w / 2, self.h / 2
        r = min(self.w, self.h) * 0.07
        sep = r * 2.0
        # 13 nodes: 1 centre + 6 inner hex + 6 outer hex
        nodes = [(cx, cy)]
        for k in range(6):
            ang = math.pi / 3 * k
            nodes.append((cx + sep * math.cos(ang), cy + sep * math.sin(ang)))
        for k in range(6):
            ang = math.pi / 3 * k
            nodes.append((cx + 2 * sep * math.cos(ang), cy + 2 * sep * math.sin(ang)))
        # all-pairs lines
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                pygame.draw.line(self.surface, (40, 60, 100),
                                 (int(nodes[i][0]), int(nodes[i][1])),
                                 (int(nodes[j][0]), int(nodes[j][1])), 1)
        # nodes on top
        for (x, y) in nodes:
            pygame.draw.circle(self.surface, self.color, (int(x), int(y)), int(r), 2)


class TreeOfLife(SacredGeometryForm):
    name = "Tree of Life (10 Sephirot)"
    info = "Kabbalistic Tree · 10 Sephirot + 22 paths"
    color = (250, 200, 100)

    def render(self):
        cx, cy = self.w / 2, self.h / 2
        r = min(self.w, self.h) * 0.04
        unit = min(self.w, self.h) * 0.13
        # canonical Sephirot positions (Kether at top, Malkuth at bottom)
        # name : (x, y) in unit-multiples relative to centre
        positions = {
            "Kether":   (0,  -3),
            "Chokmah":  (-1, -2),
            "Binah":    (1,  -2),
            "Chesed":   (-1, -1),
            "Gevurah":  (1,  -1),
            "Tiferet":  (0,   0),
            "Netzach":  (-1,  1),
            "Hod":      (1,   1),
            "Yesod":    (0,   2),
            "Malkuth":  (0,   3),
        }
        coords = {n: (cx + p[0] * unit, cy + p[1] * unit) for n, p in positions.items()}
        # 22 traditional paths
        paths = [
            ("Kether", "Chokmah"), ("Kether", "Binah"), ("Kether", "Tiferet"),
            ("Chokmah", "Binah"), ("Chokmah", "Chesed"), ("Chokmah", "Tiferet"),
            ("Binah", "Gevurah"), ("Binah", "Tiferet"),
            ("Chesed", "Gevurah"), ("Chesed", "Tiferet"), ("Chesed", "Netzach"),
            ("Gevurah", "Tiferet"), ("Gevurah", "Hod"),
            ("Tiferet", "Netzach"), ("Tiferet", "Hod"), ("Tiferet", "Yesod"),
            ("Netzach", "Hod"), ("Netzach", "Yesod"), ("Netzach", "Malkuth"),
            ("Hod", "Yesod"), ("Hod", "Malkuth"),
            ("Yesod", "Malkuth"),
        ]
        for a, b in paths:
            x1, y1 = coords[a]; x2, y2 = coords[b]
            pygame.draw.line(self.surface, (110, 130, 180),
                             (int(x1), int(y1)), (int(x2), int(y2)), 2)
        # spheres
        for n, (x, y) in coords.items():
            pygame.draw.circle(self.surface, self.color, (int(x), int(y)), int(r), 0)
            pygame.draw.circle(self.surface, BG, (int(x), int(y)), int(r * 0.5), 0)


class GoldenSpiralSG(SacredGeometryForm):
    name = "Golden Spiral (φ)"
    info = "Logarithmic spiral, growth factor φ per quarter-turn"
    color = (212, 164, 55)

    def render(self):
        cx, cy = self.w / 2, self.h / 2
        max_r = min(self.w, self.h) * 0.42
        b = math.log(PHI) / (math.pi / 2)
        a = 1.0
        theta_max = math.log(max_r / a) / b
        pts = []
        STEPS = 1200
        for i in range(STEPS):
            theta = -theta_max + 2 * theta_max * i / STEPS
            r = a * math.exp(b * theta)
            pts.append((int(cx + r * math.cos(theta)), int(cy + r * math.sin(theta))))
        if len(pts) >= 2:
            pygame.draw.lines(self.surface, self.color, False, pts, 2)
        # Fibonacci circle whispers
        for fib in (1, 1, 2, 3, 5, 8, 13, 21, 34, 55):
            rr = (fib / 55) * max_r
            pygame.draw.circle(self.surface, (40, 60, 100),
                               (int(cx), int(cy)), int(rr), 1)


class SriYantra(SacredGeometryForm):
    name = "Sri Yantra"
    info = "9 interlocking triangles + lotus petals · classic Tantric form (approx)"
    color = (220, 130, 90)

    def render(self):
        cx, cy = self.w / 2, self.h / 2
        R = min(self.w, self.h) * 0.36
        # outer square / lotus
        pygame.draw.rect(self.surface, (80, 60, 40),
                         pygame.Rect(int(cx - R), int(cy - R), int(2 * R), int(2 * R)), 1)
        # 16-petal lotus (outer)
        for k in range(16):
            ang = 2 * math.pi * k / 16
            pygame.draw.line(self.surface, (90, 60, 50),
                             (int(cx), int(cy)),
                             (int(cx + R * math.cos(ang)), int(cy + R * math.sin(ang))), 1)
        # 8-petal lotus (inner)
        r2 = R * 0.7
        for k in range(8):
            ang = 2 * math.pi * k / 8 + math.pi / 8
            pygame.draw.line(self.surface, (110, 80, 60),
                             (int(cx), int(cy)),
                             (int(cx + r2 * math.cos(ang)), int(cy + r2 * math.sin(ang))), 1)
        # 4 upward + 5 downward triangles (approx scaling)
        # Generate triangles inscribed in circle r3
        r3 = R * 0.55
        for i in range(4):
            scale = 1.0 - 0.18 * i
            self._tri(cx, cy, r3 * scale, math.pi / 2, color=self.color)
        for i in range(5):
            scale = 0.95 - 0.15 * i
            self._tri(cx, cy, r3 * scale, -math.pi / 2, color=(240, 200, 130))
        # bindu
        pygame.draw.circle(self.surface, self.color, (int(cx), int(cy)), 4, 0)

    def _tri(self, cx, cy, r, base_angle, color):
        verts = []
        for k in range(3):
            ang = base_angle + 2 * math.pi * k / 3
            verts.append((int(cx + r * math.cos(ang)), int(cy + r * math.sin(ang))))
        pygame.draw.polygon(self.surface, color, verts, 1)


# ──────────────────────────────────────────────────────────────────────────────
# PAGE REGISTRY (organised by category)
# ──────────────────────────────────────────────────────────────────────────────

PAGE_CLASSES: dict[str, list[type[FractalPage]]] = {
    "A": [Mandelbrot, Julia1, Julia2, BurningShip, Tricorn,
          Multibrot3, Multibrot4, NewtonFractal, PhoenixFractal,
          LyapunovFractal, Buddhabrot],
    "B": [SierpinskiTriangleIFS, SierpinskiCarpet, SierpinskiHexagon,
          CantorSetIFS, VicsekFractal, TSquareFractal,
          KochCurve, KochSnowflake, HeighwayDragonIFS, TwindragonIFS,
          LevyCIFS, BarnsleyFernIFS, PlusFractal,
          PythagorasTree, ApollonianGasket],
    "C": [BinaryTreeLS, HilbertCurve, PeanoCurve, GosperCurve,
          SierpinskiArrowhead, PlantOne, PlantTwo, PenroseTiling],
    "D": [LorenzAttractor, RosslerAttractor, AizawaAttractor,
          CliffordAttractor, DeJongAttractor, IkedaMap, HenonMap],
    "E": [VesicaPiscis, SeedOfLife, FlowerOfLife, MetatronCube,
          TreeOfLife, GoldenSpiralSG, SriYantra],
}


# ──────────────────────────────────────────────────────────────────────────────
# EXPLORER (categorised navigation)
# ──────────────────────────────────────────────────────────────────────────────

class FractalExplorer:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Fractal Explorer v2 — 50+ forms")
        self.fullscreen = False
        flags = 0
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), flags)
        self.w, self.h = WIN_W, WIN_H
        self.body_h = self.h - NAV_H - TITLE_H
        self.font_big = pygame.font.SysFont("consolas", 14, bold=True)
        self.font_sm = pygame.font.SysFont("consolas", 11)
        self.font_xs = pygame.font.SysFont("consolas", 10)

        self._instantiate_pages()
        self.cat_idx = 0
        self.page_idx = 0
        self.frame = 0
        self.clock = pygame.time.Clock()
        self.running = True

        self.current.ensure_init()

    def _instantiate_pages(self):
        self.pages: dict[str, list[FractalPage]] = {}
        for cat_key, _, _ in CATEGORIES:
            self.pages[cat_key] = [cls(self.w, self.body_h) for cls in PAGE_CLASSES[cat_key]]

    @property
    def current_cat(self) -> str:
        return CAT_KEYS[self.cat_idx]

    @property
    def current(self) -> FractalPage:
        return self.pages[self.current_cat][self.page_idx]

    # ── navigation ──────────────────────────────────────────────────────────
    def go_prev(self):
        cat_pages = self.pages[self.current_cat]
        self.page_idx = (self.page_idx - 1) % len(cat_pages)
        self.current.ensure_init()

    def go_next(self):
        cat_pages = self.pages[self.current_cat]
        self.page_idx = (self.page_idx + 1) % len(cat_pages)
        self.current.ensure_init()

    def jump_category(self, idx: int):
        if 0 <= idx < len(CATEGORIES):
            self.cat_idx = idx
            self.page_idx = 0
            self.current.ensure_init()

    def next_category(self):
        self.cat_idx = (self.cat_idx + 1) % len(CATEGORIES)
        self.page_idx = 0
        self.current.ensure_init()

    def reset_current(self):
        self.current.reset()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.screen = pygame.display.set_mode((WIN_W, WIN_H), flags)

    # ── draw ────────────────────────────────────────────────────────────────
    def draw_chrome(self):
        # title bar (top)
        pygame.draw.rect(self.screen, PANEL_BG, pygame.Rect(0, 0, self.w, TITLE_H))
        pygame.draw.line(self.screen, DIM, (0, TITLE_H - 1), (self.w, TITLE_H - 1), 1)
        cat_key, cat_label, cat_col = CATEGORIES[self.cat_idx]
        page = self.current
        n_pages = len(self.pages[self.current_cat])
        title = f"{cat_key} · {cat_label}  ·  {self.page_idx + 1}/{n_pages}  ·  {page.name}"
        self.screen.blit(self.font_big.render(title, True, cat_col), (12, 8))
        # info on right
        info_surface = self.font_xs.render(page.info, True, DIMMER)
        self.screen.blit(info_surface, (self.w - info_surface.get_width() - 12, 10))

        # nav bar (bottom)
        nav_y = self.h - NAV_H
        pygame.draw.rect(self.screen, PANEL_BG, pygame.Rect(0, nav_y, self.w, NAV_H))
        pygame.draw.line(self.screen, DIM, (0, nav_y), (self.w, nav_y), 1)
        # category chips
        chip_w = (self.w - 220) // len(CATEGORIES)
        for i, (k, label, col) in enumerate(CATEGORIES):
            x = 110 + i * chip_w
            active = i == self.cat_idx
            chip_rect = pygame.Rect(x + 6, nav_y + 8, chip_w - 12, NAV_H - 16)
            pygame.draw.rect(self.screen, col if active else (30, 38, 60), chip_rect, 2 if active else 1)
            label_col = (0, 0, 0) if active else col
            if active:
                pygame.draw.rect(self.screen, col, chip_rect)
            txt = self.font_sm.render(f"{k} · {label}", True, label_col)
            self.screen.blit(txt, (chip_rect.x + 8, chip_rect.y + 6))
            # page count under
            cnt = self.font_xs.render(f"{len(PAGE_CLASSES[k])} forms", True, DIM)
            self.screen.blit(cnt, (chip_rect.x + 8, chip_rect.y + 22))
        # arrows
        arrow_l = self.font_big.render("◀", True, DIMMER)
        arrow_r = self.font_big.render("▶", True, DIMMER)
        self.screen.blit(arrow_l, (40, nav_y + (NAV_H - arrow_l.get_height()) // 2))
        self.screen.blit(arrow_r, (self.w - 40 - arrow_r.get_width(),
                                   nav_y + (NAV_H - arrow_r.get_height()) // 2))
        # keys hint
        hint = self.font_xs.render("← →  Tab  1-5  R  F  Esc", True, DIM)
        self.screen.blit(hint, ((self.w - hint.get_width()) // 2, nav_y + NAV_H - 12))

    def draw(self):
        # body region: between TITLE_H and (h - NAV_H)
        self.screen.fill(BG)
        body_surface = pygame.Surface((self.w, self.body_h))
        body_surface.fill(BG)
        page = self.current
        # page renders into its own (w, body_h) surface; we blit
        page.draw(body_surface)
        self.screen.blit(body_surface, (0, TITLE_H))
        self.draw_chrome()
        pygame.display.flip()

    # ── main loop ───────────────────────────────────────────────────────────
    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN:
            k = e.key
            if k == pygame.K_ESCAPE:
                self.running = False
            elif k == pygame.K_LEFT:
                self.go_prev()
            elif k == pygame.K_RIGHT:
                self.go_next()
            elif k == pygame.K_TAB:
                self.next_category()
            elif k == pygame.K_r:
                self.reset_current()
            elif k == pygame.K_f:
                self.toggle_fullscreen()
            elif pygame.K_1 <= k <= pygame.K_5:
                self.jump_category(k - pygame.K_1)

    def run(self):
        while self.running:
            for e in pygame.event.get():
                self.handle_event(e)
            self.current.update(self.frame)
            self.draw()
            self.frame += 1
            self.clock.tick(60)
        pygame.quit()


def main():
    explorer = FractalExplorer()
    explorer.run()


if __name__ == "__main__":
    main()
