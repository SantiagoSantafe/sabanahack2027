"""Robot routes stay on aisles/headlands, cover every row, and react to overflowing foliage."""
from __future__ import annotations

import numpy as np

from config_loader import load_all_config
from robot import FieldMap, RobotController, build_patrol_path


def _assert_clear(fm: FieldMap, path) -> None:
    prev = fm.base
    for w in path:
        assert fm.segment_clear(prev, (w.x, w.z), margin=0.05), f"segment {prev}->{(w.x, w.z)} crosses a pot row"
        prev = (w.x, w.z)


def test_full_patrol_never_crosses_rows_and_covers_all_beds() -> None:
    cfg = load_all_config()
    fm, path = build_patrol_path(cfg["field"], cfg["robot"])
    _assert_clear(fm, path)
    seen = {pair for w in path if w.kind == "capture" for pair in w.plants}
    assert {b for b, _ in seen} == set(range(fm.n_beds))
    assert len({p for _, p in seen}) == fm.n_plants


def test_priority_order_is_respected() -> None:
    cfg = load_all_config()
    order = [5, 0, 7, 2, 1, 3, 4, 6]
    fm, path = build_patrol_path(cfg["field"], cfg["robot"], order=order)
    _assert_clear(fm, path)
    assert [w.aisle for w in path if w.kind == "aisle_enter"] == order


def _with_overflow(cfg, alt):
    fm = FieldMap(cfg["field"], cfg["robot"])
    a = fm.aisles[0]
    p = fm.n_plants // 2
    fm.spread_r[fm.idx(a.left, p)] = 0.9
    fm.spread_l[fm.idx(a.right, p)] = 0.9
    ctl = RobotController(fm, cfg["robot"], alt, np.random.default_rng(0))
    ctl._plan([0])
    return fm, ctl.path


def test_low_quadruped_slows_but_passes_under_overflow() -> None:
    cfg = load_all_config()
    _, path = _with_overflow(cfg, {"platform": "quadruped", "mobility": {"width_m": 0.36, "height_m": 0.42}})
    caps = [w for w in path if w.kind == "capture"]
    assert any(w.careful for w in caps)
    assert not any(w.contact for w in caps)
    assert not any(w.kind == "blocked" for w in path)


def test_rigid_wheeled_platform_gets_blocked() -> None:
    cfg = load_all_config()
    _, path = _with_overflow(cfg, {"platform": "wheeled", "mobility": {"width_m": 0.7, "height_m": 1.5, "rigid": True}})
    assert any(w.kind == "blocked" for w in path)
