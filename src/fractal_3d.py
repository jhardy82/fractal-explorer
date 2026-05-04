"""
fractal_3d.py — 3D fractal category for fractal_explorer_v2 engine.

Adds three forms via numpy distance-estimator (DE) raymarching:
    Mandelbulb (power-8 polar form, White & Nylander 2009)
    Mandelbox (Tom Lowe 2010, scale=2 fold)
    Menger Sponge (Karl Menger 1926; cross-fold DE)

Each form subclasses Fractal3D, which handles:
    • Camera + ray generation (one ray per pixel, vectorised over a row block)
    • Sphere-tracing march (loop steps along ray, advancing by DE)
    • Hit shading (normal estimated by central differences, simple Lambert + AO)
    • Progressive row rendering (low-res, ~12 rows per frame)

Resolution defaults to 1/3 of canvas (renders to 1/3 surface, scales up) so frame
budget stays in the ~80-200ms range under headless SDL.

USAGE
-----
Add a "F" category to fractal_explorer_v2 PAGE_CLASSES:

    from fractal_3d import Mandelbulb, Mandelbox, MengerSponge
    PAGE_CLASSES["F"] = [Mandelbulb, Mandelbox, MengerSponge]
    CATEGORIES.append(("F", "DIMENSION", (160, 200, 255)))   # cyan

The Explorer's category-jump key range expands to "1..6".
"""
from __future__ import annotations

import math

import numpy as np
import pygame


# import base class lazily to avoid hard dependency at module load
def _get_base():
    """Returns the FractalPage base class from the engine module."""
    import fractal_explorer_v2 as _engine
    return _engine.FractalPage, _engine.BG


# ──────────────────────────────────────────────────────────────────────────────
# Fractal3D base — sphere-tracing distance-estimator raymarcher (numpy)
# ──────────────────────────────────────────────────────────────────────────────

class Fractal3D:
    """Base class instantiated dynamically (subclasses inherit FractalPage)."""

    category = "F"
    info = ""

    # rendering params (override per subclass for fine-tuning)
    downscale = 3              # render at w/downscale, h/downscale, then scale up
    rows_per_frame = 8         # rows of low-res output per frame
    max_steps = 64             # raymarch iterations
    epsilon = 0.001            # hit threshold (relative to scene scale)
    max_dist = 8.0             # ray cutoff
    bailout = 4.0              # |z| escape bound for fractals
    iter_count = 8             # fractal DE iterations

    # camera: looking at origin from (cam_dist, 0, ~+y up)
    cam_dist = 3.5
    cam_pitch = -0.15          # radians, slight downward tilt
    cam_yaw_speed = 0.004      # auto-rotate per frame

    color_a = (50, 90, 130)    # base albedo (deep)
    color_b = (220, 220, 255)  # highlight albedo

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self._initialised = False

    def reset(self):
        self._initialised = True
        # low-res offscreen buffer
        self.lw = max(1, self.w // self.downscale)
        self.lh = max(1, self.h // self.downscale)
        self.buf = np.zeros((self.lh, self.lw, 3), dtype=np.uint8)
        self.surface = pygame.Surface((self.w, self.h))
        FP, BG = _get_base()
        self.surface.fill(BG)
        self.row = 0
        self.frame = 0

    def ensure_init(self):
        if not self._initialised:
            self.reset()

    # subclasses override
    def DE(self, p: np.ndarray) -> np.ndarray:
        """Distance estimator: input p shape (N, 3); return distances shape (N,)."""
        raise NotImplementedError

    # ── numpy raymarch ──────────────────────────────────────────────────────
    def _camera(self):
        """Returns (eye, forward, right, up) for current frame."""
        yaw = self.frame * self.cam_yaw_speed
        cy, sy = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(self.cam_pitch), math.sin(self.cam_pitch)
        eye = np.array([self.cam_dist * cy * cp,
                        self.cam_dist * sp,
                        self.cam_dist * sy * cp], dtype=np.float32)
        forward = -eye / np.linalg.norm(eye)
        world_up = np.array([0, 1, 0], dtype=np.float32)
        right = np.cross(forward, world_up)
        right /= np.linalg.norm(right) + 1e-9
        up = np.cross(right, forward)
        return eye, forward, right, up

    def _render_rows(self, y0: int, y1: int) -> None:
        """Render rows [y0, y1) of the low-res buffer."""
        eye, forward, right, up = self._camera()
        aspect = self.lw / self.lh
        fov = math.radians(40)
        scale = math.tan(fov / 2)

        # Build pixel grid → ray dirs
        xs = (np.arange(self.lw) + 0.5) / self.lw * 2 - 1     # [-1, 1)
        ys = (np.arange(y0, y1) + 0.5) / self.lh * 2 - 1
        gx, gy = np.meshgrid(xs * scale * aspect, -ys * scale)  # flip y
        # ray dir = forward + gx*right + gy*up, normalized
        rd = (forward[None, None, :]
              + gx[..., None] * right[None, None, :]
              + gy[..., None] * up[None, None, :])
        rd /= np.linalg.norm(rd, axis=-1, keepdims=True) + 1e-9

        # Flatten for DE call
        H = y1 - y0
        rd_flat = rd.reshape(-1, 3)
        ro = np.broadcast_to(eye, rd_flat.shape).copy()

        # March
        t = np.full(rd_flat.shape[0], 0.0, dtype=np.float32)
        active = np.ones(rd_flat.shape[0], dtype=bool)
        hit = np.zeros(rd_flat.shape[0], dtype=bool)
        for _ in range(self.max_steps):
            if not active.any():
                break
            p = ro[active] + t[active, None] * rd_flat[active]
            d = self.DE(p)
            t[active] += d
            new_hit = active.copy()
            new_hit[active] = d < self.epsilon
            hit |= new_hit
            new_far = active.copy()
            new_far[active] = t[active] > self.max_dist
            active &= ~(new_hit | new_far)

        # Shade
        col = np.zeros((rd_flat.shape[0], 3), dtype=np.float32)
        if hit.any():
            p_hit = ro[hit] + t[hit, None] * rd_flat[hit]
            n = self._estimate_normal(p_hit)
            light = np.array([0.6, 0.8, 0.4], dtype=np.float32)
            light /= np.linalg.norm(light)
            lambert = np.maximum(0.0, n @ light)
            # cheap AO: distance from origin → sphere of radius bailout
            r = np.linalg.norm(p_hit, axis=1)
            ao = np.clip(1.0 - r / 2.5, 0.0, 1.0)
            shade = 0.25 + 0.65 * lambert + 0.10 * ao
            ca = np.array(self.color_a, dtype=np.float32)
            cb = np.array(self.color_b, dtype=np.float32)
            col[hit] = ca[None, :] + (cb - ca)[None, :] * shade[:, None]

        rgb = np.clip(col, 0, 255).astype(np.uint8).reshape(H, self.lw, 3)
        self.buf[y0:y1] = rgb

    def _estimate_normal(self, p: np.ndarray, h: float = 0.001) -> np.ndarray:
        """Central-difference normal estimation."""
        ex = np.array([h, 0, 0], dtype=np.float32)
        ey = np.array([0, h, 0], dtype=np.float32)
        ez = np.array([0, 0, h], dtype=np.float32)
        nx = self.DE(p + ex) - self.DE(p - ex)
        ny = self.DE(p + ey) - self.DE(p - ey)
        nz = self.DE(p + ez) - self.DE(p - ez)
        n = np.stack([nx, ny, nz], axis=-1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
        return n

    # ── per-frame update ────────────────────────────────────────────────────
    def update(self, frame):
        self.frame = frame
        # progressive: render rows_per_frame rows of low-res buffer, then loop
        y0 = self.row
        y1 = min(self.lh, self.row + self.rows_per_frame)
        if y1 <= y0:
            self.row = 0
            return
        self._render_rows(y0, y1)
        self.row = y1
        # if we just finished a full pass, scale up + blit
        if self.row >= self.lh:
            # flip axes for pygame: numpy is (h, w, 3); pygame surfarray wants (w, h, 3)
            arr = self.buf.transpose(1, 0, 2)
            sub = pygame.surfarray.make_surface(arr)
            scaled = pygame.transform.scale(sub, (self.w, self.h))
            self.surface.blit(scaled, (0, 0))
            self.row = 0   # restart for next sweep (camera will have rotated)

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))


# ──────────────────────────────────────────────────────────────────────────────
# Mandelbulb (power-8)
# ──────────────────────────────────────────────────────────────────────────────

class _MandelbulbDE(Fractal3D):
    name = "Mandelbulb"
    info = "z' = z⁸ + c (polar form) · White & Nylander 2009"
    iter_count = 8
    bailout = 2.0
    color_a = (60, 30, 130)
    color_b = (250, 220, 180)

    def DE(self, p):
        """Distance estimator for the power-8 Mandelbulb."""
        z = p.copy()
        dr = np.ones(p.shape[0], dtype=np.float32)
        r = np.zeros(p.shape[0], dtype=np.float32)
        active = np.ones(p.shape[0], dtype=bool)
        n = 8.0
        for _ in range(self.iter_count):
            if not active.any():
                break
            r_active = np.linalg.norm(z[active], axis=1)
            r[active] = r_active
            escaped = r_active > self.bailout
            local_active_idx = np.where(active)[0]
            mask_escape = local_active_idx[escaped]
            active[mask_escape] = False
            still = np.where(active)[0]
            if not still.size:
                break
            zs = z[still]
            rs = np.linalg.norm(zs, axis=1)
            theta = np.arccos(np.clip(zs[:, 1] / (rs + 1e-9), -1.0, 1.0))
            phi = np.arctan2(zs[:, 2], zs[:, 0])
            dr_new = rs ** (n - 1) * n * dr[still] + 1.0
            zr = rs ** n
            theta_n = theta * n
            phi_n = phi * n
            x = zr * np.sin(theta_n) * np.cos(phi_n)
            y_ = zr * np.cos(theta_n)
            zc = zr * np.sin(theta_n) * np.sin(phi_n)
            z_new = np.stack([x, y_, zc], axis=1) + p[still]
            z[still] = z_new
            dr[still] = dr_new
        return 0.5 * np.log(np.maximum(r, 1e-9)) * r / (dr + 1e-9)


# ──────────────────────────────────────────────────────────────────────────────
# Mandelbox (Tom Lowe 2010)
# ──────────────────────────────────────────────────────────────────────────────

class _MandelboxDE(Fractal3D):
    name = "Mandelbox"
    info = "Box-fold + sphere-fold + linear scale · Tom Lowe 2010"
    iter_count = 12
    bailout = 1024.0
    scale = 2.0
    fold_limit = 1.0
    min_radius = 0.5
    fixed_radius = 1.0
    color_a = (40, 100, 80)
    color_b = (180, 240, 200)

    def DE(self, p):
        z = p.copy()
        dr = np.ones(p.shape[0], dtype=np.float32) * self.scale
        for _ in range(self.iter_count):
            # box fold
            z = np.clip(z, -self.fold_limit, self.fold_limit) * 2.0 - z
            # sphere fold
            r2 = (z * z).sum(axis=1, keepdims=True)
            cond_inner = (r2 < self.min_radius * self.min_radius)
            cond_mid = ((r2 >= self.min_radius * self.min_radius) &
                        (r2 < self.fixed_radius * self.fixed_radius))
            ratio_inner = (self.fixed_radius * self.fixed_radius) / (self.min_radius * self.min_radius)
            ratio_mid = (self.fixed_radius * self.fixed_radius) / (r2 + 1e-9)
            z = np.where(cond_inner, z * ratio_inner, z)
            z = np.where(cond_mid, z * ratio_mid, z)
            dr = np.where(cond_inner.flatten(), dr * ratio_inner, dr)
            dr = np.where(cond_mid.flatten(), dr * ratio_mid.flatten(), dr)
            z = z * self.scale + p
            dr = dr * abs(self.scale) + 1.0
        r = np.linalg.norm(z, axis=1)
        return r / np.abs(dr + 1e-9)


# ──────────────────────────────────────────────────────────────────────────────
# Menger Sponge (Karl Menger 1926) via cross-fold DE
# ──────────────────────────────────────────────────────────────────────────────

class _MengerSpongeDE(Fractal3D):
    name = "Menger Sponge"
    info = "3D Sierpiński-Carpet analogue · 27→20 cube subdivision · Menger 1926"
    iter_count = 5
    color_a = (90, 60, 50)
    color_b = (240, 200, 150)

    def DE(self, p):
        """DE for the iterated Menger sponge — fold + scale 3."""
        # initial bound: unit cube at origin
        scale = 1.0
        q = p.copy()
        for _ in range(self.iter_count):
            # cross-fold: take symmetric of |q| and remap
            q = np.abs(q)
            # sort the components in descending order so that q.x >= q.y >= q.z
            # This effectively folds the sponge into the wedge x >= y >= z
            qx = q[:, 0]; qy = q[:, 1]; qz = q[:, 2]
            # swap if qx < qy
            sw = qx < qy
            qx, qy = np.where(sw, qy, qx), np.where(sw, qx, qy)
            sw = qx < qz
            qx, qz = np.where(sw, qz, qx), np.where(sw, qx, qz)
            sw = qy < qz
            qy, qz = np.where(sw, qz, qy), np.where(sw, qy, qz)
            q = np.stack([qx, qy, qz], axis=1)
            # translate + scale by 3
            q = q * 3.0 - np.array([2.0, 2.0, 0.0], dtype=np.float32)
            q[:, 2] = np.where(q[:, 2] < -1.0, q[:, 2] + 2.0, q[:, 2])
            scale *= 3.0
        # box-DE in folded space
        dq = np.abs(q) - 1.0
        outside = np.linalg.norm(np.maximum(dq, 0), axis=1)
        inside = np.minimum(np.maximum.reduce([dq[:, 0], dq[:, 1], dq[:, 2]]), 0)
        return (outside + inside) / scale


# ──────────────────────────────────────────────────────────────────────────────
# Materialise the FractalPage subclasses (delayed binding to engine base)
# ──────────────────────────────────────────────────────────────────────────────

def make_3d_pages():
    """Returns [Mandelbulb, Mandelbox, MengerSponge] as FractalPage subclasses."""
    FP, _ = _get_base()

    class Mandelbulb(_MandelbulbDE, FP):
        pass

    class Mandelbox(_MandelboxDE, FP):
        pass

    class MengerSponge(_MengerSpongeDE, FP):
        pass

    return [Mandelbulb, Mandelbox, MengerSponge]


# ──────────────────────────────────────────────────────────────────────────────
# Integration helper
# ──────────────────────────────────────────────────────────────────────────────

def register_3d_category(engine_module):
    """Inject category 'F · DIMENSION' with the 3 forms into a loaded engine."""
    pages = make_3d_pages()
    engine_module.PAGE_CLASSES["F"] = pages
    if ("F", "DIMENSION", (160, 200, 255)) not in engine_module.CATEGORIES:
        engine_module.CATEGORIES.append(("F", "DIMENSION", (160, 200, 255)))
    if "F" not in engine_module.CAT_KEYS:
        engine_module.CAT_KEYS.append("F")
    return pages


if __name__ == "__main__":
    # standalone demo: run only the 3D category
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # change to remove for real GUI
    import fractal_explorer_v2 as engine
    register_3d_category(engine)
    explorer = engine.FractalExplorer()
    # jump straight to category F
    explorer.cat_idx = engine.CAT_KEYS.index("F")
    explorer.page_idx = 0
    explorer.current.ensure_init()
    explorer.run()
