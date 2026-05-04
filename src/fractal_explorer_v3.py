"""
fractal_explorer_v3.py — All-in-one launcher for the fractal engine.

Loads `fractal_explorer_v2.py` (the 48-form base) and `fractal_3d.py`
(the 3D extension), auto-registers category F · DIMENSION, and runs.

USAGE
-----
    pip install pygame numpy
    python fractal_explorer_v3.py

KEYS
----
    1..6      jump to category A..F
    ← →       prev / next page within category
    Tab       next category
    R         reset current page
    F         toggle fullscreen
    Esc       quit

This wrapper lives next to fractal_explorer_v2.py and fractal_3d.py so the
imports resolve without sys.path gymnastics.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ensure the engine + 3D module are importable from THIS directory
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import fractal_explorer_v2 as engine          # noqa: E402  (path-setup-first)
import fractal_3d                              # noqa: E402


def main():
    # register category F before instantiating Explorer
    fractal_3d.register_3d_category(engine)

    # sanity print
    total = sum(len(v) for v in engine.PAGE_CLASSES.values())
    print(f"Fractal Explorer v3 — {total} forms across {len(engine.CAT_KEYS)} categories")
    for k in engine.CAT_KEYS:
        n = len(engine.PAGE_CLASSES[k])
        label = next(c[1] for c in engine.CATEGORIES if c[0] == k)
        print(f"  {k} · {label:<12s}: {n} forms")

    # The Explorer's keyboard handler accepts pygame.K_1..pygame.K_5 by default;
    # patch it to accept up to len(CATEGORIES) - 1 dynamically.
    _orig_handle = engine.FractalExplorer.handle_event
    def _patched_handle(self, e):
        import pygame
        if e.type == pygame.KEYDOWN:
            # extend numeric jump range to current category count
            n_cats = len(engine.CAT_KEYS)
            if pygame.K_1 <= e.key <= pygame.K_1 + n_cats - 1:
                self.jump_category(e.key - pygame.K_1)
                return
        _orig_handle(self, e)
    engine.FractalExplorer.handle_event = _patched_handle

    explorer = engine.FractalExplorer()
    explorer.run()


if __name__ == "__main__":
    main()
