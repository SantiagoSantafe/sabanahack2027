"""Carga config/dashboard.yaml con valores por defecto (el dashboard funciona aunque falte el archivo)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "focos": {
        "max_gap_plantas": 5, "ventana_h": 72,
        "familias": {"oidio": "hongo", "alternaria": "hongo", "heliothis": "plaga", "desconocida": "otro"},
        "gravedad": {"heliothis": 1.0, "alternaria": 0.9, "oidio": 0.8, "desconocida": 0.5},
        "pesos": {"p_plantas": 1.0, "riesgo_piso": 0.25, "antig_escala_h": 24, "antig_tope_h": 96, "puntaje_ref": 3.0},
        "nivel_puntaje": {"alto": 55, "medio": 30},
        "tendencia": {"ventana_h": 24, "puntos": 8}, "nuevas_para_crecer": 2,
    },
    "atencion": {"rojo_h": 24, "ambar_h": 12},
    "cobertura": {"ciego_h": 48},
    "riesgo": {"ventanas_h": [24, 48, 72], "hr_alta_pct": 85, "max_avisos": 12},
}


def _merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_dashboard_config(path: Path | None = None) -> dict[str, Any]:
    p = path or Path(__file__).parent / "config" / "dashboard.yaml"
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        data = {}
    return _merge(DEFAULTS, data)
