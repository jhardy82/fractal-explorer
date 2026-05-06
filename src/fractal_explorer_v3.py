"""
fractal_explorer_v3.py — All-in-one launcher for the fractal engine.

Loads `fractal_explorer_v2.py` (the 48-form base) and `fractal_3d.py`
(the 3D extension), auto-registers category F · DIMENSION, and runs.

INTERACTIVE USAGE
-----------------
    pip install pygame numpy
    python fractal_explorer_v3.py

HEADLESS RENDER
---------------
    python fractal_explorer_v3.py --render Mandelbrot
    python fractal_explorer_v3.py --render Mandelbrot --frames 80 --size 1920x1080 --output out.png
    python fractal_explorer_v3.py --list          # show all available form names

KEYS (interactive)
------------------
    1..6      jump to category A..F
    ← →       prev / next page within category
    Tab       next category
    R         reset current page
    F         toggle fullscreen
    Esc       quit
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Parse args at module scope — BEFORE any pygame import.
# SDL_VIDEODRIVER=dummy must be set before fractal_explorer_v2 imports pygame.
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fractal_explorer_v3.py",
        description="Fractal Explorer v3 — 51 forms interactive or headless render",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python fractal_explorer_v3.py                          # interactive\n"
            "  python fractal_explorer_v3.py --list                   # show form names\n"
            "  python fractal_explorer_v3.py --render Mandelbrot      # headless 480×360\n"
            "  python fractal_explorer_v3.py --render Julia1 --frames 60 --size 1920x1080 --output julia.png\n"
        ),
    )
    p.add_argument("--render", metavar="FORM", default=None,
                   help="Render one form headlessly to PNG (no window)")
    p.add_argument("--frames", type=int, default=30, metavar="N",
                   help="Frames to compute before saving (default: 30)")
    p.add_argument("--size", default="480x360", metavar="WxH",
                   help="Canvas size in pixels (default: 480x360)")
    p.add_argument("--output", metavar="FILE", default=None,
                   help="Output PNG path (default: <FORM>.png)")
    p.add_argument("--list", action="store_true", dest="list_forms",
                   help="List all available form names and exit")
    return p


_args = _build_parser().parse_args()

# Set headless SDL env vars BEFORE engine modules import pygame
if _args.render or _args.list_forms:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


# ---------------------------------------------------------------------------
# Engine imports (pygame is imported transitively here)
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import fractal_3d  # noqa: E402
import fractal_explorer_v2 as engine  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_page_classes() -> list[tuple[str, str, type]]:
    """Return [(cat_key, title, cls), ...] for all registered forms."""
    result = []
    for cat_key, pages in engine.PAGE_CLASSES.items():
        for cls in pages:
            title = getattr(cls, "TITLE", cls.__name__)
            result.append((cat_key, title, cls))
    return result


def _find_page_class(name: str) -> type | None:
    """Find a page class by class name or TITLE (case-insensitive)."""
    name_lower = name.lower().strip()
    name_norm = name_lower.replace(" ", "").replace("_", "")
    for _cat, title, cls in _all_page_classes():
        if cls.__name__.lower() == name_lower:
            return cls
        if title.lower() == name_lower:
            return cls
        if cls.__name__.lower().replace("_", "") == name_norm:
            return cls
        if title.lower().replace(" ", "").replace("_", "") == name_norm:
            return cls
    return None


def _list_forms() -> None:
    """Print all form names grouped by category."""
    fractal_3d.register_3d_category(engine)
    print("Available forms (51 total):\n")
    for cat_key in engine.CAT_KEYS:
        label = next(c[1] for c in engine.CATEGORIES if c[0] == cat_key)
        print(f"  {cat_key} · {label}")
        for cls in engine.PAGE_CLASSES[cat_key]:
            title = getattr(cls, "TITLE", cls.__name__)
            print(f"    {cls.__name__:<28s}  title: {title!r}")
        print()


# ---------------------------------------------------------------------------
# Headless render
# ---------------------------------------------------------------------------

def _render_headless(args: argparse.Namespace) -> None:
    import pygame

    try:
        w_str, h_str = args.size.lower().split("x")
        w, h = int(w_str), int(h_str)
        assert w > 0 and h > 0
    except (ValueError, AssertionError):
        sys.exit(f"--size must be WxH with positive integers, e.g. 480x360; got: {args.size!r}")

    fractal_3d.register_3d_category(engine)

    page_cls = _find_page_class(args.render)
    if page_cls is None:
        names = sorted(
            f"{cls.__name__} ({getattr(cls, 'TITLE', '')})"
            for _, _, cls in _all_page_classes()
        )
        print(f"Form {args.render!r} not found. Available:\n  " + "\n  ".join(names),
              file=sys.stderr)
        sys.exit(1)

    pygame.init()
    screen = pygame.display.set_mode((w, h))

    page = page_cls(w, h)
    page.ensure_init()

    for frame in range(args.frames):
        page.update(frame)
    page.draw(screen)

    out_path = args.output or f"{args.render}.png"
    pygame.image.save(screen, out_path)

    title = getattr(page_cls, "TITLE", page_cls.__name__)
    print(f"Rendered '{title}' — {args.frames} frames, {w}×{h} → {out_path}")

    pygame.quit()


# ---------------------------------------------------------------------------
# Interactive main
# ---------------------------------------------------------------------------

def main() -> None:
    fractal_3d.register_3d_category(engine)

    total = sum(len(v) for v in engine.PAGE_CLASSES.values())
    print(f"Fractal Explorer v3 — {total} forms across {len(engine.CAT_KEYS)} categories")
    for k in engine.CAT_KEYS:
        n = len(engine.PAGE_CLASSES[k])
        label = next(c[1] for c in engine.CATEGORIES if c[0] == k)
        print(f"  {k} · {label:<12s}: {n} forms")

    class FractalExplorer6(engine.FractalExplorer):
        def handle_event(self, e):
            import pygame
            if e.type == pygame.KEYDOWN:
                n_cats = len(engine.CAT_KEYS)
                if pygame.K_1 <= e.key <= pygame.K_1 + n_cats - 1:
                    self.jump_category(e.key - pygame.K_1)
                    return
            super().handle_event(e)

    explorer = FractalExplorer6()
    explorer.run()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if _args.list_forms:
        _list_forms()
    elif _args.render:
        _render_headless(_args)
    else:
        main()
