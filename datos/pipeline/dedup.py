#!/usr/bin/env python
"""Agrupa casi-duplicados entre las imágenes de ORIGEN con hash perceptual (imagehash.phash).

Dos imágenes de origen con distancia de Hamming <= ``--threshold`` quedan en el mismo grupo
(cierre transitivo con union-find). Opcionalmente se fusionan grupos externos, por ejemplo las
ráfagas de ``resultados/drberry_imagenes.csv`` (``--extra-groups-csv ... --extra-key nombre_original
--extra-group grupo_rafaga``), cuya clave se compara con ``source_id``.

Salidas en ``--out``: ``groups.csv`` (source_id, phash, group, ...), ``duplicates_report.json``,
``duplicates_report.md`` y, con ``--pairs-png``, un mosaico con los pares más parecidos y los más
cercanos al umbral (para revisar a ojo si el umbral fusiona imágenes distintas).

Ejemplo:
    .venv/bin/python -I pipeline/dedup.py --manifest pipeline/work/drberry/crops/manifest.csv \
        --out pipeline/work/drberry/dedup --threshold 6 \
        --extra-groups-csv resultados/drberry_imagenes.csv --extra-key nombre_original --extra-group grupo_rafaga
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from common import now_iso, read_manifests, write_csv, write_json  # noqa: E402


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, a: int) -> int:
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def compute_phash(path: str | Path, hash_size: int = 8) -> np.ndarray:
    """Bits (bool) del phash de una imagen."""
    import imagehash

    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        return np.asarray(imagehash.phash(im, hash_size=hash_size).hash, dtype=bool).ravel()


def _pack(bits: np.ndarray) -> np.ndarray:
    """(n, nbits) bool -> (n, words) uint64."""
    packed = np.packbits(bits, axis=1)
    pad = (-packed.shape[1]) % 8
    if pad:
        packed = np.pad(packed, ((0, 0), (0, pad)))
    return packed.view(np.uint64)


def near_duplicate_pairs(bits: np.ndarray, threshold: int, block: int = 1024) -> list[tuple[int, int, int]]:
    """Pares (i, j, distancia) con i < j y distancia de Hamming <= threshold."""
    words = _pack(bits)
    n = len(words)
    pairs: list[tuple[int, int, int]] = []
    for s in range(0, n, block):
        a = words[s : s + block]
        d = np.zeros((len(a), n), dtype=np.int32)
        for w in range(words.shape[1]):
            d += np.bitwise_count(a[:, w][:, None] ^ words[:, w][None, :]).astype(np.int32)
        ii, jj = np.nonzero(d <= threshold)
        for i, j in zip(ii.tolist(), jj.tolist()):
            gi = s + i
            if gi < j:
                pairs.append((gi, j, int(d[i, j])))
    return pairs


def group_sources(
    source_ids: Sequence[str],
    bits: np.ndarray,
    threshold: int,
    extra_groups: dict[str, str] | None = None,
) -> tuple[list[str], list[tuple[int, int, int]], int]:
    """Devuelve (grupo por fuente, pares casi-duplicados, n_uniones_por_grupos_externos)."""
    n = len(source_ids)
    uf = UnionFind(n)
    pairs = near_duplicate_pairs(bits, threshold) if n else []
    for i, j, _ in pairs:
        uf.union(i, j)
    n_ext = 0
    if extra_groups:
        first: dict[str, int] = {}
        for i, sid in enumerate(source_ids):
            g = extra_groups.get(sid)
            if g is None or g == "":
                continue
            if g in first:
                if uf.find(first[g]) != uf.find(i):
                    n_ext += 1
                uf.union(first[g], i)
            else:
                first[g] = i
    roots = [uf.find(i) for i in range(n)]
    # nombre determinista: orden por el menor source_id del grupo
    members: dict[int, list[str]] = {}
    for i, r in enumerate(roots):
        members.setdefault(r, []).append(source_ids[i])
    order = sorted(members, key=lambda r: min(members[r]))
    name = {r: f"g{k + 1:05d}" for k, r in enumerate(order)}
    return [name[r] for r in roots], pairs, n_ext


def load_extra_groups(path: str, key: str, group: str) -> dict[str, str]:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for c in (key, group):
        if c not in df.columns:
            raise SystemExit(f"{path} no tiene la columna {c!r}")
    return {k: f"ext:{g}" for k, g in zip(df[key], df[group]) if k}


def pairs_mosaic(paths: Sequence[str], pairs: Sequence[tuple[int, int, int]], dest: Path, max_pairs: int = 12, thumb: int = 160) -> None:
    from PIL import ImageDraw

    # mitad: los pares más parecidos; mitad: los más cercanos al umbral (donde aparecerían falsas fusiones)
    ordered = sorted(pairs, key=lambda p: (p[2], p[0], p[1]))
    if len(ordered) <= max_pairs:
        sel = ordered
    else:
        half = max_pairs // 2
        sel = ordered[:half] + ordered[-(max_pairs - half):]
    if not sel:
        return
    W, H = thumb * 2 + 30, (thumb + 22) * len(sel) + 10
    canvas = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(canvas)
    for k, (i, j, d) in enumerate(sel):
        y = 10 + k * (thumb + 22)
        for col, idx in enumerate((i, j)):
            with Image.open(paths[idx]) as im:
                t = ImageOps.exif_transpose(im).convert("RGB")
                t.thumbnail((thumb, thumb))
            canvas.paste(t, (10 + col * (thumb + 10), y))
        draw.text((10, y + thumb + 4), f"distancia phash = {d}", fill="black")
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", nargs="+", required=True, help="Uno o varios manifest.csv de convert.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--threshold", type=int, default=6, help="Distancia de Hamming máxima para casi-duplicado (de 64 bits con hash-size 8)")
    ap.add_argument("--hash-size", type=int, default=8)
    ap.add_argument("--extra-groups-csv", default=None, help="CSV con grupos externos (p. ej. ráfagas) a fusionar")
    ap.add_argument("--extra-key", default="source_id", help="Columna del CSV externo que coincide con source_id")
    ap.add_argument("--extra-group", default="group", help="Columna del CSV externo con el id de grupo")
    ap.add_argument("--pairs-png", action="store_true", help="Guardar mosaico de pares (los más parecidos y los más cercanos al umbral)")
    ap.add_argument("--max-report-pairs", type=int, default=500)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    man = read_manifests(args.manifest)
    src = (
        man.groupby("source_id", sort=True)
        .agg(source_path=("source_path", "first"), n_items=("item_id", "size"), labels=("label", lambda s: "|".join(sorted(set(s)))))
        .reset_index()
    )
    sids = src["source_id"].tolist()
    bits = np.stack([compute_phash(p, args.hash_size) for p in src["source_path"]]) if len(src) else np.zeros((0, args.hash_size**2), bool)
    extra = load_extra_groups(args.extra_groups_csv, args.extra_key, args.extra_group) if args.extra_groups_csv else None
    groups, pairs, n_ext = group_sources(sids, bits, args.threshold, extra)
    src["phash"] = ["".join("1" if b else "0" for b in row) for row in bits]
    src["phash_hex"] = [f"{int(h, 2):0{max(1, len(h) // 4)}x}" if h else "" for h in src["phash"]]
    src["group"] = groups
    src["n_in_group"] = src.groupby("group")["source_id"].transform("size")
    src["ext_group"] = [extra.get(s, "") if extra else "" for s in sids]
    write_csv(src.drop(columns=["phash"]), out / "groups.csv")

    multi = src[src["n_in_group"] > 1]
    cross_label_pairs = [(i, j, d) for i, j, d in pairs if src.at[i, "labels"] != src.at[j, "labels"]]
    report = {
        "creado": now_iso(),
        "manifiestos": [str(Path(m).resolve()) for m in args.manifest],
        "hash": f"phash hash_size={args.hash_size} ({args.hash_size ** 2} bits)",
        "umbral_hamming": args.threshold,
        "umbral_nota": "SUPUESTO: umbral heurístico; revisar el mosaico de pares antes de confiar en él",
        "n_imagenes_origen": len(src),
        "n_grupos": int(src["group"].nunique()) if len(src) else 0,
        "n_grupos_con_mas_de_una_imagen": int(multi["group"].nunique()) if len(multi) else 0,
        "n_imagenes_en_grupos_multiples": int(len(multi)),
        "n_pares_casi_duplicados": len(pairs),
        "n_pares_con_etiqueta_distinta": len(cross_label_pairs),
        "n_uniones_por_grupos_externos": n_ext,
        "grupos_externos": args.extra_groups_csv,
        "tamano_grupo_max": int(src["n_in_group"].max()) if len(src) else 0,
        "pares": [
            {"a": sids[i], "b": sids[j], "distancia": d, "etiquetas_a": src.at[i, "labels"], "etiquetas_b": src.at[j, "labels"]}
            for i, j, d in sorted(pairs, key=lambda p: (p[2], p[0], p[1]))[: args.max_report_pairs]
        ],
    }
    write_json(out / "duplicates_report.json", report)
    md = [
        "# Reporte de casi-duplicados (dedup.py)",
        "",
        f"- Creado: {report['creado']}",
        f"- Hash: {report['hash']}; umbral de Hamming <= {args.threshold} ({report['umbral_nota']})",
        f"- Imágenes de origen: {report['n_imagenes_origen']}; grupos: {report['n_grupos']}",
        f"- Grupos con más de una imagen: {report['n_grupos_con_mas_de_una_imagen']} ({report['n_imagenes_en_grupos_multiples']} imágenes)",
        f"- Pares casi-duplicados: {report['n_pares_casi_duplicados']} (con etiqueta distinta: {report['n_pares_con_etiqueta_distinta']})",
        f"- Uniones añadidas por grupos externos: {n_ext} (fuente: {args.extra_groups_csv or 'ninguna'})",
        "",
        "| a | b | distancia | etiquetas a | etiquetas b |",
        "|---|---|---|---|---|",
    ]
    md += [f"| {p['a']} | {p['b']} | {p['distancia']} | {p['etiquetas_a']} | {p['etiquetas_b']} |" for p in report["pares"][:50]]
    (out / "duplicates_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if args.pairs_png and pairs:
        pairs_mosaic(src["source_path"].tolist(), pairs, out / "duplicate_pairs.png")
    print(f"[dedup] {len(src)} imágenes de origen -> {report['n_grupos']} grupos; {len(pairs)} pares <= {args.threshold}; {n_ext} uniones externas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
