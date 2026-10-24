"""Load and merge YAML configuration files."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
ALT_DIR = CONFIG_DIR / "alternatives"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def load_all_config() -> dict[str, Any]:
    """Load field, sim, weather, risk, detector, robot configs."""
    return {
        "field": _load_yaml(CONFIG_DIR / "field.yaml"),
        "sim": _load_yaml(CONFIG_DIR / "sim.yaml"),
        "weather": _load_yaml(CONFIG_DIR / "weather.yaml"),
        "risk": _load_yaml(CONFIG_DIR / "risk.yaml"),
        "detector": _load_yaml(CONFIG_DIR / "detector.yaml"),
        "robot": _load_yaml(CONFIG_DIR / "robot.yaml"),
        "climate": _load_yaml(CONFIG_DIR / "climate.yaml"),
    }


def list_alternatives() -> list[str]:
    codes = sorted(p.stem for p in ALT_DIR.glob("*.yaml"))
    # Put F first for UX, REF last
    preferred = ["F", "A", "B", "C", "D", "E", "REF"]
    ordered = [c for c in preferred if c in codes]
    ordered += [c for c in codes if c not in ordered]
    return ordered


def load_alternative(code: str) -> dict[str, Any]:
    path = ALT_DIR / f"{code}.yaml"
    if not path.exists():
        # try uppercase
        path = ALT_DIR / f"{code.upper()}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Alternative config not found: {code}")
    data = _load_yaml(path)
    data["code"] = data.get("code", code.upper())
    return data


def load_all_alternatives() -> dict[str, dict[str, Any]]:
    return {code: load_alternative(code) for code in list_alternatives()}
