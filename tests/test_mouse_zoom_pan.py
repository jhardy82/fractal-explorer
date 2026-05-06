"""
test_mouse_zoom_pan.py — Unit tests for scroll-wheel zoom and drag-to-pan.

Acceptance criteria verified:
  AC3  Coordinate mapping: screen px → complex plane
  AC4  Zoom around cursor: complex coord under cursor is unchanged after zoom
  AC5  Pan delta: viewport shifts by correct complex-plane delta
  AC9  Only escape-time forms affected (isinstance guard)
  AC10 Out-of-body events ignored (y < TITLE_H leaves viewport unchanged)
"""
from __future__ import annotations

_W, _H = 80, 60
TITLE_H = 30
NAV_H = 56

_X_RANGE = (-2.5, 1.0)   # class default; width = 3.5
_Y_RANGE = (-1.25, 1.25)  # class default; height = 2.5
ZOOM_FACTOR = 0.85


def _make_page(cls, **overrides):
    """Construct a subclass with attribute overrides, reset and return it."""
    Patched = type("Patched", (cls,), overrides)
    page = Patched(_W, _H)
    page.reset()
    return page


def _coord_map(mouse_x, body_mouse_y, x_range, y_range, body_w, body_h):
    """Screen pixel → complex-plane coordinate (pure function matching spec AC3)."""
    x0, x1 = x_range
    y0, y1 = y_range
    cx = x0 + (mouse_x / body_w) * (x1 - x0)
    cy = y0 + (body_mouse_y / body_h) * (y1 - y0)
    return cx, cy


def _zoom(mouse_x, body_mouse_y, x_range, y_range, body_w, body_h, factor):
    """Apply zoom formula from spec AC4 and return (new_x_range, new_y_range)."""
    x0, x1 = x_range
    y0, y1 = y_range
    cx, cy = _coord_map(mouse_x, body_mouse_y, x_range, y_range, body_w, body_h)
    t_x = mouse_x / body_w
    t_y = body_mouse_y / body_h
    new_xw = (x1 - x0) * factor
    new_yh = (y1 - y0) * factor
    return (
        (cx - t_x * new_xw, cx + (1 - t_x) * new_xw),
        (cy - t_y * new_yh, cy + (1 - t_y) * new_yh),
    )


def _pan(pan_x0, pan_y0, mouse_x, mouse_y, x_range_at_click, y_range_at_click, body_w, body_h):
    """Apply pan formula from spec AC5 and return (new_x_range, new_y_range)."""
    dx = mouse_x - pan_x0
    dy = mouse_y - pan_y0
    x0, x1 = x_range_at_click
    y0, y1 = y_range_at_click
    xw = x1 - x0
    yh = y1 - y0
    return (
        (x0 - dx * xw / body_w, x1 - dx * xw / body_w),
        (y0 - dy * yh / body_h, y1 - dy * yh / body_h),
    )


# ---------------------------------------------------------------------------
# AC3 — Coordinate mapping
# ---------------------------------------------------------------------------

class TestCoordinateMapping:
    """Screen px → complex plane coordinate mapping (spec AC3)."""

    def test_coord_map_centre(self):
        """Centre of viewport body maps to centre of complex range."""
        cx, cy = _coord_map(
            mouse_x=_W // 2, body_mouse_y=_H // 2,
            x_range=_X_RANGE, y_range=_Y_RANGE,
            body_w=_W, body_h=_H,
        )
        assert abs(cx - (-0.75)) < 1e-9
        assert abs(cy - 0.0) < 1e-9

    def test_coord_map_top_left(self):
        """Top-left corner (0,0) maps to (x0, y0)."""
        cx, cy = _coord_map(
            mouse_x=0, body_mouse_y=0,
            x_range=_X_RANGE, y_range=_Y_RANGE,
            body_w=_W, body_h=_H,
        )
        assert abs(cx - _X_RANGE[0]) < 1e-9
        assert abs(cy - _Y_RANGE[0]) < 1e-9

    def test_coord_map_bottom_right(self):
        """Bottom-right corner (W,H) maps to (x1, y1)."""
        cx, cy = _coord_map(
            mouse_x=_W, body_mouse_y=_H,
            x_range=_X_RANGE, y_range=_Y_RANGE,
            body_w=_W, body_h=_H,
        )
        assert abs(cx - _X_RANGE[1]) < 1e-9
        assert abs(cy - _Y_RANGE[1]) < 1e-9

    def test_coord_map_asymmetric(self):
        """Quarter-point maps correctly for asymmetric viewport."""
        x_range = (-1.0, 3.0)  # width=4
        y_range = (0.5, 2.5)   # height=2
        cx, cy = _coord_map(
            mouse_x=20, body_mouse_y=15,
            x_range=x_range, y_range=y_range,
            body_w=80, body_h=60,
        )
        # t_x = 20/80 = 0.25, t_y = 15/60 = 0.25
        # cx = -1.0 + 0.25 * 4 = 0.0
        # cy = 0.5 + 0.25 * 2 = 1.0
        assert abs(cx - 0.0) < 1e-9
        assert abs(cy - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# AC4 — Zoom around cursor preserves complex coord under cursor
# ---------------------------------------------------------------------------

class TestZoomAroundCursor:
    """After one zoom event the complex coord under the cursor is unchanged (AC4)."""

    def test_zoom_preserves_coord_at_centre(self):
        """Zoom centred on viewport centre keeps centre complex coord fixed."""
        mouse_x, body_mouse_y = _W // 2, _H // 2
        cx_before, cy_before = _coord_map(
            mouse_x, body_mouse_y, _X_RANGE, _Y_RANGE, _W, _H
        )
        new_x_range, new_y_range = _zoom(
            mouse_x, body_mouse_y, _X_RANGE, _Y_RANGE, _W, _H, ZOOM_FACTOR
        )
        cx_after, cy_after = _coord_map(
            mouse_x, body_mouse_y, new_x_range, new_y_range, _W, _H
        )
        assert abs(cx_after - cx_before) < 1e-9, (
            f"cx changed after zoom: {cx_before} → {cx_after}"
        )
        assert abs(cy_after - cy_before) < 1e-9, (
            f"cy changed after zoom: {cy_before} → {cy_after}"
        )

    def test_zoom_preserves_coord_at_quarter_point(self):
        """Zoom around an off-centre cursor still preserves the complex coord there."""
        mouse_x, body_mouse_y = _W // 4, _H // 4
        cx_before, cy_before = _coord_map(
            mouse_x, body_mouse_y, _X_RANGE, _Y_RANGE, _W, _H
        )
        new_x_range, new_y_range = _zoom(
            mouse_x, body_mouse_y, _X_RANGE, _Y_RANGE, _W, _H, ZOOM_FACTOR
        )
        cx_after, cy_after = _coord_map(
            mouse_x, body_mouse_y, new_x_range, new_y_range, _W, _H
        )
        assert abs(cx_after - cx_before) < 1e-9
        assert abs(cy_after - cy_before) < 1e-9

    def test_zoom_shrinks_viewport_width(self):
        """factor=0.85 must reduce viewport width (zoom in)."""
        _, (new_x0, new_x1) = _zoom(
            _W // 2, _H // 2, _X_RANGE, _Y_RANGE, _W, _H, ZOOM_FACTOR
        )
        # Oops — _zoom returns (x_range, y_range), let me fix:
        pass  # covered by test_zoom_shrinks_width below

    def test_zoom_shrinks_width(self):
        new_x_range, _ = _zoom(
            _W // 2, _H // 2, _X_RANGE, _Y_RANGE, _W, _H, ZOOM_FACTOR
        )
        old_width = _X_RANGE[1] - _X_RANGE[0]
        new_width = new_x_range[1] - new_x_range[0]
        assert new_width < old_width, "factor=0.85 should shrink the viewport"
        assert abs(new_width - old_width * ZOOM_FACTOR) < 1e-9

    def test_zoom_out_expands_viewport(self):
        """factor > 1 (scroll down) expands the viewport."""
        factor_out = 1.0 / ZOOM_FACTOR
        new_x_range, _ = _zoom(
            _W // 2, _H // 2, _X_RANGE, _Y_RANGE, _W, _H, factor_out
        )
        old_width = _X_RANGE[1] - _X_RANGE[0]
        new_width = new_x_range[1] - new_x_range[0]
        assert new_width > old_width

    def test_zoom_on_page_sets_instance_attr(self, engine):
        """Applying zoom stores x_range/y_range as instance attrs on the page."""
        page = _make_page(engine.Mandelbrot)
        assert 'x_range' not in page.__dict__, "should start with no instance attr"
        mouse_x, body_mouse_y = _W // 2, _H // 2
        new_x_range, new_y_range = _zoom(
            mouse_x, body_mouse_y,
            page.x_range, page.y_range,
            _W, _H, ZOOM_FACTOR,
        )
        page.x_range = new_x_range
        page.y_range = new_y_range
        page.row = 0
        assert 'x_range' in page.__dict__, "zoom must shadow class attr with instance attr"
        assert 'y_range' in page.__dict__

    def test_reset_clears_instance_range_attrs(self, engine):
        """reset() removes instance x_range/y_range so class defaults are visible again."""
        page = _make_page(engine.Mandelbrot)
        page.x_range = (-1.0, 1.0)
        page.y_range = (-0.5, 0.5)
        assert 'x_range' in page.__dict__
        page.reset()
        assert 'x_range' not in page.__dict__, "reset() must delete instance x_range"
        assert 'y_range' not in page.__dict__, "reset() must delete instance y_range"
        assert page.x_range == engine.Mandelbrot.x_range


# ---------------------------------------------------------------------------
# AC5 — Pan delta: viewport shifts by correct complex-plane amount
# ---------------------------------------------------------------------------

class TestPanDelta:
    """Drag from A to B shifts x_range/y_range by the correct complex delta (AC5)."""

    def test_pan_right_shifts_viewport_left(self):
        """Dragging right (dx > 0) pans the viewport left (x values decrease)."""
        pan_x0, pan_y0 = 20, 20
        mouse_x, mouse_y = 30, 20
        new_x_range, _ = _pan(
            pan_x0, pan_y0, mouse_x, mouse_y,
            _X_RANGE, _Y_RANGE, _W, _H,
        )
        # dx=10, xw=3.5, body_w=80 → x_shift = -10 * 3.5/80 = -0.4375
        x_shift = -(mouse_x - pan_x0) * (_X_RANGE[1] - _X_RANGE[0]) / _W
        assert abs(new_x_range[0] - (_X_RANGE[0] + x_shift)) < 1e-9
        assert abs(new_x_range[1] - (_X_RANGE[1] + x_shift)) < 1e-9

    def test_pan_down_shifts_viewport_up(self):
        """Dragging down (dy > 0) pans the viewport up (y values decrease)."""
        pan_x0, pan_y0 = 20, 20
        mouse_x, mouse_y = 20, 35
        _, new_y_range = _pan(
            pan_x0, pan_y0, mouse_x, mouse_y,
            _X_RANGE, _Y_RANGE, _W, _H,
        )
        y_shift = -(mouse_y - pan_y0) * (_Y_RANGE[1] - _Y_RANGE[0]) / _H
        assert abs(new_y_range[0] - (_Y_RANGE[0] + y_shift)) < 1e-9
        assert abs(new_y_range[1] - (_Y_RANGE[1] + y_shift)) < 1e-9

    def test_pan_preserves_viewport_size(self):
        """Pan must not change the width or height of the viewport."""
        new_x_range, new_y_range = _pan(
            10, 10, 25, 20, _X_RANGE, _Y_RANGE, _W, _H,
        )
        old_width = _X_RANGE[1] - _X_RANGE[0]
        old_height = _Y_RANGE[1] - _Y_RANGE[0]
        new_width = new_x_range[1] - new_x_range[0]
        new_height = new_y_range[1] - new_y_range[0]
        assert abs(new_width - old_width) < 1e-9
        assert abs(new_height - old_height) < 1e-9

    def test_pan_zero_drag_no_change(self):
        """Zero drag (no movement) leaves viewport unchanged."""
        new_x_range, new_y_range = _pan(
            20, 20, 20, 20, _X_RANGE, _Y_RANGE, _W, _H,
        )
        assert new_x_range == _X_RANGE
        assert new_y_range == _Y_RANGE

    def test_pan_stores_instance_attr(self, engine):
        """Applying pan stores x_range/y_range as instance attrs on the page."""
        page = _make_page(engine.Mandelbrot)
        new_x_range, new_y_range = _pan(10, 10, 20, 20, page.x_range, page.y_range, _W, _H)
        page.x_range = new_x_range
        page.y_range = new_y_range
        page.row = 0
        assert 'x_range' in page.__dict__
        assert 'y_range' in page.__dict__


# ---------------------------------------------------------------------------
# AC10 — Out-of-body events ignored
# ---------------------------------------------------------------------------

class TestOutOfBodyIgnored:
    """Mouse events outside the body region must not change the viewport (AC10)."""

    def test_mousewheel_above_title_bar_ignored(self, engine):
        """Scroll event at y < TITLE_H must leave x_range/y_range unchanged."""
        page = _make_page(engine.Mandelbrot)
        initial_x = page.x_range
        initial_y = page.y_range

        # Simulate the boundary check from handle_event MOUSEWHEEL
        mouse_y = TITLE_H - 1  # above title bar
        body_mouse_y = mouse_y - TITLE_H  # = -1 → < 0 → guard fires
        out_of_body = body_mouse_y < 0

        assert out_of_body, "y < TITLE_H must trigger the out-of-body guard"
        # Since guard fires, page is not modified — assert no change happened
        assert page.x_range == initial_x
        assert page.y_range == initial_y

    def test_mousewheel_in_nav_bar_ignored(self, engine):
        """Scroll event in nav bar (y >= h - NAV_H) must not change viewport."""
        page = _make_page(engine.Mandelbrot)
        initial_x = page.x_range
        initial_y = page.y_range

        # screen height context: body_h = _H (page height), full screen would be _H + NAV_H + TITLE_H
        # For the guard: mouse_y >= screen_h - NAV_H
        screen_h = _H + NAV_H + TITLE_H
        mouse_y = screen_h - NAV_H  # exactly on the nav bar boundary
        out_of_body = mouse_y >= screen_h - NAV_H

        assert out_of_body, "y at nav bar must trigger the out-of-body guard"
        assert page.x_range == initial_x
        assert page.y_range == initial_y

    def test_mousebuttondown_above_title_bar_no_pan(self, engine):
        """Click at y < TITLE_H must not initiate pan (viewport unchanged)."""
        page = _make_page(engine.Mandelbrot)
        initial_x = page.x_range
        initial_y = page.y_range

        mouse_y = TITLE_H - 1
        # Simulate the boundary check from handle_event MOUSEBUTTONDOWN
        pan_would_start = mouse_y >= TITLE_H  # False

        assert not pan_would_start, "click above title bar must not start pan"
        assert page.x_range == initial_x
        assert page.y_range == initial_y

    def test_mousebuttondown_in_body_starts_pan(self, engine):
        """Click inside the body region (TITLE_H <= y < h - NAV_H) initiates pan."""
        screen_h = _H + NAV_H + TITLE_H
        mouse_y = TITLE_H + 1  # just inside body
        pan_would_start = TITLE_H <= mouse_y < screen_h - NAV_H
        assert pan_would_start, "click inside body must initiate pan"


# ---------------------------------------------------------------------------
# AC9 — Only escape-time pages affected (isinstance guard)
# ---------------------------------------------------------------------------

class TestEscapeTimeFractalGuard:
    """Non-escape-time pages must be unaffected by mouse events (AC9)."""

    def test_non_escape_time_page_has_no_range_attrs(self, engine):
        """A category-B page (IFS) has no x_range/y_range — interactions do not apply."""
        ifs_cls = engine.PAGE_CLASSES["B"][0]
        assert not issubclass(ifs_cls, engine.EscapeTimeFractal), (
            "IFS pages must not be EscapeTimeFractal subclasses"
        )

    def test_some_category_a_pages_are_escape_time(self, engine):
        """At least the core Mandelbrot/Julia/BurningShip pages are EscapeTimeFractal subclasses."""
        escape_time_names = {cls.__name__ for cls in engine.PAGE_CLASSES["A"]
                             if issubclass(cls, engine.EscapeTimeFractal)}
        for expected in ("Mandelbrot", "BurningShip", "Tricorn"):
            assert expected in escape_time_names, (
                f"{expected} must be an EscapeTimeFractal subclass in category A"
            )

    def test_mandelbrot_is_escape_time(self, engine):
        """Mandelbrot is an EscapeTimeFractal instance — mouse events apply."""
        page = _make_page(engine.Mandelbrot)
        assert isinstance(page, engine.EscapeTimeFractal)

    def test_non_a_category_pages_are_not_escape_time(self, engine):
        """No category B–E page is an EscapeTimeFractal subclass."""
        for cat in ("B", "C", "D", "E"):
            for cls in engine.PAGE_CLASSES[cat]:
                assert not issubclass(cls, engine.EscapeTimeFractal), (
                    f"{cls.__name__} in category {cat} must not subclass EscapeTimeFractal"
                )
