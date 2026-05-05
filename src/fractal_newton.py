"""fractal_newton.py — Newton generalised fractal, category A.

Standalone module — no circular import with fractal_explorer_v2.
Imported by fractal_explorer_v2 at the bottom and registered into PAGE_CLASSES["A"].
"""
from __future__ import annotations

import numpy as np
import pygame

_BG = (10, 10, 10)

# Per-basin accent colours; cycles for n > 6.
_BASIN_COLORS = [
    (220, 80, 110),   # warm red
    (80, 200, 110),   # green
    (110, 130, 230),  # blue
    (220, 180, 50),   # gold
    (50, 200, 200),   # cyan
    (180, 80, 220),   # violet
]


def _build_palette(n: int, max_iter: int) -> np.ndarray:
    """Return (max_iter+1, 3) uint8 palette.  Index 0 = background."""
    colors = [_BG]
    bc = _BASIN_COLORS
    shades = max(1, max_iter // n)
    for i in range(max_iter):
        basin = i % n
        shade_step = (i // n) % shades
        factor = 0.55 + 0.45 * (shade_step / max(shades - 1, 1))
        r, g, b = bc[basin % len(bc)]
        colors.append((int(r * factor), int(g * factor), int(b * factor)))
    return np.array(colors[:max_iter + 1], dtype=np.uint8)


class NewtonGeneralised:
    """Newton's method on z^n − 1 = 0, parameterised by degree n (2–6).

    Progressive row-by-row renderer; mirrors the EscapeTimeFractal contract
    (self.surface, self.row, reset/update/draw) without importing the engine.
    """

    category = "A"
    x_range = (-2.0, 2.0)
    y_range = (-1.5, 1.5)
    max_iter = 40
    rows_per_frame = 16
    info = "Newton iteration z ↦ z − (z^n−1)/(n·z^(n−1)) · root-basin colouring"

    def __init__(self, w: int, h: int, n: int = 3):
        self.w = w
        self.h = h
        self.n = n
        self.name = f"Newton z^{n}−1"
        self._initialised = False

    def reset(self) -> None:
        self.surface = pygame.Surface((self.w, self.h))
        self.surface.fill(_BG)
        self.row = 0
        self.palette = _build_palette(self.n, self.max_iter)
        self._initialised = True

    def _ensure_init(self) -> None:
        if not self._initialised:
            self.reset()

    def ensure_init(self) -> None:
        self._ensure_init()

    def update(self, frame: int) -> None:  # noqa: ARG002
        self._ensure_init()
        if self.row >= self.h:
            return
        y1 = min(self.h, self.row + self.rows_per_frame)
        self._render_rows(self.row, y1)
        self.row = y1

    def _render_rows(self, y0: int, y1: int) -> None:
        n = self.n
        x0, x1 = self.x_range
        ymin, ymax = self.y_range
        xs = np.linspace(x0, x1, self.w)
        ys = np.linspace(ymin, ymax, self.h)[y0:y1]
        cx, cy = np.meshgrid(xs, ys)
        z = cx + 1j * cy
        roots = np.array([np.exp(2j * np.pi * k / n) for k in range(n)])
        out = np.zeros(z.shape, dtype=np.int32)
        converged = np.zeros(z.shape, dtype=bool)
        slot_size = max(1, self.max_iter // n)

        for i in range(self.max_iter):
            denom = n * z ** (n - 1)
            # Avoid division by zero at the origin
            tiny = np.abs(denom) < 1e-12
            denom = np.where(tiny, 1e-12 + 0j, denom)
            z = z - (z**n - 1) / denom

            for r_idx, r in enumerate(roots):
                hit = (np.abs(z - r) < 1e-3) & ~converged
                # palette index: basin slot + shading within slot
                out[hit] = r_idx * slot_size + (i % slot_size) + 1
                converged |= hit

            if converged.all():
                break

        rgb = self.palette[np.clip(out, 0, self.max_iter)]
        sub = pygame.surfarray.make_surface(rgb.transpose(1, 0, 2))
        self.surface.blit(sub, (0, y0))

    def draw(self, screen: pygame.Surface) -> None:
        self._ensure_init()
        screen.blit(self.surface, (0, 0))

    def tweak_param(self, delta: float) -> None:
        pass

    def reset_params(self) -> None:
        pass

    def get_param_display(self) -> str:
        return f"n = {self.n}"


class Newton4(NewtonGeneralised):
    """Newton z^4 − 1 = 0.  Basins: 1, i, −1, −i."""

    name = "Newton z⁴−1"
    info = "Newton iteration on z⁴−1=0 · four root basins (1, i, −1, −i)"

    def __init__(self, w: int, h: int):
        super().__init__(w, h, n=4)


class Newton5(NewtonGeneralised):
    """Newton z^5 − 1 = 0.  Five-fold pentagonal basin symmetry."""

    name = "Newton z⁵−1"
    info = "Newton iteration on z⁵−1=0 · five root basins · pentagonal symmetry"

    def __init__(self, w: int, h: int):
        super().__init__(w, h, n=5)


class Newton6(NewtonGeneralised):
    """Newton z^6 − 1 = 0.  Six-fold hexagonal basin symmetry."""

    name = "Newton z⁶−1"
    info = "Newton iteration on z⁶−1=0 · six root basins · hexagonal symmetry"

    def __init__(self, w: int, h: int):
        super().__init__(w, h, n=6)
