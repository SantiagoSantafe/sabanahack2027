#!/usr/bin/env python
"""Galería PNG + HTML de errores: falsas alarmas, casos no detectados y confusiones entre enfermedades.

* ``falsas_alarmas``: verdad = sana, decisión = enfermedad (alerta innecesaria).
* ``no_detectados``: verdad = enfermedad, decisión = sana (el error caro).
* ``confusion_enfermedades``: enfermedad A decidida como enfermedad B (la alerta sale, pero con
  el diagnóstico equivocado).

La decisión usa el umbral de ``threshold.py`` si se da ``--threshold``; si no, argmax. Se ordena
por lo "seguro" que estaba el modelo del error (los errores más confiados primero).

Salidas en ``--out``: ``galeria.html`` (miniaturas embebidas, autocontenido), ``<tipo>.png`` y
``errores.csv``. Las imágenes son del dataset de origen: respete su licencia y atribución
(``--attribution``).

Ejemplo:
    .venv/bin/python -I pipeline/gallery.py --pred pipeline/work/drberry/clip/predicciones_probe_test.csv \
        --threshold pipeline/work/drberry/clip/threshold_probe.json --out resultados/galeria_probe_test \
        --attribution "DrBerry (Roboflow Universe), CC BY 4.0"
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image, ImageDraw, ImageFont, ImageOps  # noqa: E402

from common import DEFAULT_HEALTHY, PROB_PREFIX, decide, disease_scores, healthy_index, load_threshold, now_iso, read_predictions, write_csv  # noqa: E402

KINDS = {
    "falsas_alarmas": "Falsas alarmas (sana -> alerta de enfermedad)",
    "no_detectados": "Casos no detectados (enfermedad -> sana)",
    "confusion_enfermedades": "Enfermedad detectada pero con diagnóstico equivocado",
}


def classify_errors(df: pd.DataFrame, classes: Sequence[str], healthy: str, thr: float | None) -> pd.DataFrame:
    probs = df[[f"{PROB_PREFIX}{c}" for c in classes]].to_numpy(float)
    hname = classes[healthy_index(classes, healthy)]
    out = df.copy()
    out["decision"] = decide(probs, classes, healthy, thr)
    out["p_enfermedad"] = disease_scores(probs, classes, healthy)
    out["p_decision"] = [float(probs[i, classes.index(d)]) for i, d in enumerate(out["decision"])]
    kind = []
    for t, d in zip(out["y_true"], out["decision"]):
        if t == d:
            kind.append("")
        elif t == hname:
            kind.append("falsas_alarmas")
        elif d == hname:
            kind.append("no_detectados")
        else:
            kind.append("confusion_enfermedades")
    out["tipo_error"] = kind
    # confianza del error: para no detectados, cuán "sana" la vio (1 - p_enfermedad); para el resto, p_enfermedad
    out["confianza_error"] = np.where(out["tipo_error"] == "no_detectados", 1 - out["p_enfermedad"], out["p_decision"])
    return out


def _thumb(path: str, size: int) -> Image.Image:
    try:
        with Image.open(path) as im:
            t = ImageOps.exif_transpose(im).convert("RGB")
    except Exception:  # noqa: BLE001
        t = Image.new("RGB", (size, size), (200, 200, 200))
    t.thumbnail((size, size))
    canvas = Image.new("RGB", (size, size), (245, 245, 245))
    canvas.paste(t, ((size - t.width) // 2, (size - t.height) // 2))
    return canvas


def _font(size: int) -> ImageFont.ImageFont:
    """DejaVu Sans (viene con matplotlib) para que las tildes se vean; si falla, la fuente por defecto."""
    try:
        from matplotlib import font_manager

        return ImageFont.truetype(font_manager.findfont("DejaVu Sans"), size)
    except Exception:  # noqa: BLE001
        try:
            return ImageFont.load_default(size=size)
        except TypeError:  # Pillow antiguo
            return ImageFont.load_default()


def mosaic(rows: pd.DataFrame, title: str, dest: Path, thumb: int = 180, cols: int = 6, attribution: str = "") -> None:
    n = len(rows)
    r = max(1, int(np.ceil(n / cols)))
    cap = 44
    W = cols * (thumb + 10) + 10
    H = 40 + r * (thumb + cap + 10) + 30
    canvas = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(canvas)
    d.text((10, 10), f"{title} (n={n})", fill="black", font=_font(18))
    f = _font(12)
    for k, (_, row) in enumerate(rows.iterrows()):
        x = 10 + (k % cols) * (thumb + 10)
        y = 40 + (k // cols) * (thumb + cap + 10)
        canvas.paste(_thumb(row["path"], thumb), (x, y))
        d.text((x, y + thumb + 2), f"verdad: {row['y_true']}", fill="black", font=f)
        d.text((x, y + thumb + 16), f"decisión: {row['decision']}", fill="crimson", font=f)
        d.text((x, y + thumb + 30), f"p_enf={row['p_enfermedad']:.2f}", fill="dimgray", font=f)
    if n == 0:
        d.text((10, 50), "Sin casos.", fill="dimgray", font=f)
    if attribution:
        d.text((10, H - 22), f"Imágenes: {attribution}", fill="dimgray", font=f)
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest)


def _b64(path: str, size: int) -> str:
    buf = io.BytesIO()
    _thumb(path, size).save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def write_html(err: pd.DataFrame, dest: Path, meta: dict[str, str], thumb: int, max_per_kind: int, attribution: str) -> None:
    parts = [
        "<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>Galería de errores</title><style>",
        ":root{--bg:#fff;--fg:#1d1d1f;--muted:#666;--card:#f4f4f6;--bad:#b3261e}",
        "@media (prefers-color-scheme: dark){:root{--bg:#141416;--fg:#ececf0;--muted:#a0a0a8;--card:#222226;--bad:#ff8a80}}",
        "body{background:var(--bg);color:var(--fg);font-family:system-ui,sans-serif;margin:0 auto;max-width:1200px;padding:16px}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}",
        ".card{background:var(--card);border-radius:8px;padding:8px;font-size:12px}.card img{width:100%;border-radius:4px}",
        ".bad{color:var(--bad)}.muted{color:var(--muted)}</style></head><body>",
        "<h1>Galería de falsas alarmas y casos no detectados</h1>",
        "<p class='muted'>" + " · ".join(f"{html.escape(k)}: {html.escape(v)}" for k, v in meta.items()) + "</p>",
    ]
    for kind, title in KINDS.items():
        sub = err[err["tipo_error"] == kind].sort_values("confianza_error", ascending=False)
        parts.append(f"<h2>{html.escape(title)} — {len(sub)}</h2>")
        if sub.empty:
            parts.append("<p class='muted'>Sin casos.</p>")
            continue
        parts.append("<div class='grid'>")
        for _, r in sub.head(max_per_kind).iterrows():
            parts.append(
                "<div class='card'>"
                f"<img alt='' src='data:image/jpeg;base64,{_b64(r['path'], thumb)}'>"
                f"<div>verdad: <b>{html.escape(str(r['y_true']))}</b></div>"
                f"<div class='bad'>decisión: <b>{html.escape(str(r['decision']))}</b></div>"
                f"<div class='muted'>p_enfermedad={r['p_enfermedad']:.3f}</div>"
                f"<div class='muted' style='word-break:break-all'>{html.escape(str(r.get('item_id', Path(r['path']).name)))}</div>"
                "</div>"
            )
        parts.append("</div>")
    if attribution:
        parts.append(f"<p class='muted'>Imágenes: {html.escape(attribution)}. Uso interno; no redistribuir.</p>")
    parts.append("</body></html>")
    dest.write_text("\n".join(parts), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threshold", default=None, help="Número o threshold.json; sin él se usa argmax")
    ap.add_argument("--healthy-class", default=DEFAULT_HEALTHY)
    ap.add_argument("--max-per-kind", type=int, default=36)
    ap.add_argument("--thumb", type=int, default=180)
    ap.add_argument("--attribution", default="", help="Texto de atribución/licencia de las imágenes")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    df, classes = read_predictions(args.pred)
    df = df[df["y_true"] != ""].reset_index(drop=True)
    thr = load_threshold(args.threshold)
    err = classify_errors(df, classes, args.healthy_class, thr)
    bad = err[err["tipo_error"] != ""].sort_values(["tipo_error", "confianza_error"], ascending=[True, False])
    keep = [c for c in ("item_id", "path", "y_true", "decision", "tipo_error", "p_enfermedad", "p_decision", "confianza_error", "source_id", "group") if c in bad.columns]
    write_csv(bad[keep], out / "errores.csv")
    for kind, title in KINDS.items():
        sub = err[err["tipo_error"] == kind].sort_values("confianza_error", ascending=False).head(args.max_per_kind)
        mosaic(sub, title, out / f"{kind}.png", args.thumb, attribution=args.attribution)
    meta = {"predicciones": Path(args.pred).name, "regla": f"umbral {thr:.3f}" if thr is not None else "argmax", "n": str(len(df)), "creado": now_iso()}
    write_html(err, out / "galeria.html", meta, args.thumb, args.max_per_kind, args.attribution)
    counts = bad["tipo_error"].value_counts().to_dict()
    print(f"[gallery] errores: {counts} -> {out / 'galeria.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
