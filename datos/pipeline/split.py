#!/usr/bin/env python
"""División train/val/test (70/15/15 por defecto) estratificada por clase y AGRUPADA.

La unidad que nunca se reparte entre splits es el grupo: el grupo de casi-duplicados de
``dedup.py`` (``--groups groups.csv``) o, si no se da, la imagen de origen (``source_id``).
Así ningún recorte de la misma foto (ni de una ráfaga o casi-duplicado) cae en dos splits.

Algoritmo (determinista con ``--seed``): cada grupo recibe la clase mayoritaria de sus ítems; por
clase, los grupos se recorren en orden aleatorio y cada uno va al split con mayor déficit relativo
respecto a la proporción objetivo. Se prueban ``--trials`` órdenes y se queda el que mejor respeta
las proporciones por clase (a nivel de ítem).

Salidas en ``--out``: ``train.csv``, ``val.csv``, ``test.csv``, ``split_summary.json`` y
``test_frozen.json`` (SHA-256 del manifiesto de test; ``test.csv`` queda en solo lectura). Si ya
existe un test congelado distinto, el script se niega a sobrescribirlo salvo con ``--force``.
``--verify DIR`` comprueba que el test congelado no cambió. ``--materialize DIR`` crea la estructura
``DIR/{train,val,test}/<clase>/`` que espera Ultralytics.

Ejemplo:
    .venv/bin/python -I pipeline/split.py --manifest pipeline/work/drberry/crops/manifest.csv \
        --groups pipeline/work/drberry/dedup/groups.csv --out pipeline/work/drberry/splits --seed 20261023 \
        --materialize pipeline/work/drberry/yolo_cls
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import SPLITS, now_iso, read_json, read_manifests, safe_filename, sha256_file, sha256_text, write_csv, write_json  # noqa: E402

FROZEN_NAME = "test_frozen.json"
MATERIALIZE_MARKER = ".materializado_por_split_py"


def group_majority_labels(df: pd.DataFrame) -> pd.Series:
    """Clase mayoritaria de cada grupo (empate: alfabético)."""
    counts = df.groupby(["group", "label"]).size().reset_index(name="n")
    counts = counts.sort_values(["group", "n", "label"], ascending=[True, False, True])
    return counts.drop_duplicates("group").set_index("group")["label"]


def assign_groups(
    df: pd.DataFrame,
    ratios: Sequence[float] = (0.70, 0.15, 0.15),
    seed: int = 20261023,
    trials: int = 200,
) -> tuple[dict[str, str], float]:
    """Asigna cada grupo a un split. Devuelve (grupo -> split, puntaje de desviación)."""
    r = np.asarray(ratios, dtype=float)
    r = r / r.sum()
    glabel = group_majority_labels(df)
    gsize = df.groupby("group").size().to_dict()
    classes = sorted(df["label"].unique())
    # ítems por (grupo, clase) para puntuar a nivel de ítem
    gc = df.groupby(["group", "label"]).size().unstack(fill_value=0).reindex(columns=classes, fill_value=0)
    class_tot = gc.sum(axis=0).to_numpy(dtype=float)
    groups_by_class = {c: sorted(glabel.index[glabel == c].tolist()) for c in classes}

    best: tuple[float, dict[str, str]] | None = None
    for t in range(max(1, trials)):
        rng = np.random.default_rng([seed, t])
        assign: dict[str, str] = {}
        for c in classes:
            gs = groups_by_class[c]
            if not gs:
                continue
            order = rng.permutation(len(gs))
            total = float(sum(gsize[g] for g in gs))
            target = r * total
            cur = np.zeros(len(SPLITS))
            for k in order:
                g = gs[k]
                rel = (target - cur) / np.maximum(target, 1e-9)
                s = int(np.argmax(rel))
                cur[s] += gsize[g]
                assign[g] = SPLITS[s]
        split_of = np.array([assign[g] for g in gc.index])
        mat = np.stack([gc.to_numpy()[split_of == s].sum(axis=0) for s in SPLITS], axis=0)  # (3, k)
        frac = mat / np.maximum(class_tot, 1)
        score = float(((frac - r[:, None]) ** 2).sum())
        overall = mat.sum(axis=1) / max(mat.sum(), 1)
        score += float(((overall - r) ** 2).sum())
        if best is None or score < best[0] - 1e-15:
            best = (score, assign)
    assert best is not None
    return best[1], best[0]


def content_hash(df: pd.DataFrame) -> str:
    """Hash del CONTENIDO (independiente de rutas absolutas): item_id, label, source_id, group."""
    lines = sorted(f"{a}\t{b}\t{c}\t{d}" for a, b, c, d in zip(df["item_id"], df["label"], df["source_id"], df["group"]))
    return sha256_text("\n".join(lines))


def _write_readonly_csv(df: pd.DataFrame, path: Path) -> None:
    if path.exists():
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    write_csv(df, path)
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def verify_frozen(split_dir: Path) -> tuple[bool, str]:
    fz = split_dir / FROZEN_NAME
    test = split_dir / "test.csv"
    if not fz.exists() or not test.exists():
        return False, f"Falta {fz.name} o test.csv en {split_dir}"
    info = read_json(fz)
    h = sha256_file(test)
    if h != info["sha256"]:
        return False, f"test.csv CAMBIÓ: sha256 {h[:12]}… != congelado {info['sha256'][:12]}…"
    return True, f"test.csv intacto (sha256 {h[:12]}…, {info['n_items']} ítems, {info['n_grupos']} grupos)"


def materialize(splits: dict[str, pd.DataFrame], dest: Path, link: str) -> None:
    dest = dest.resolve()
    if dest.exists() and any(dest.iterdir()):
        if not (dest / MATERIALIZE_MARKER).exists():
            raise SystemExit(f"{dest} existe, no está vacío y no lo creó split.py: no lo toco")
        shutil.rmtree(dest)  # solo carpetas generadas por este script (tienen el marcador)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / MATERIALIZE_MARKER).write_text(now_iso() + "\n", encoding="utf-8")
    for s, df in splits.items():
        for item_id, label, path in zip(df["item_id"], df["label"], df["path"]):
            src = Path(path)
            out = dest / s / safe_filename(label) / (safe_filename(item_id.replace("/", "__")) + src.suffix.lower())
            out.parent.mkdir(parents=True, exist_ok=True)
            if link == "symlink":
                out.symlink_to(src.resolve())
            elif link == "hardlink":
                os.link(src, out)
            else:
                shutil.copy2(src, out)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", nargs="+", help="Uno o varios manifest.csv de convert.py")
    ap.add_argument("--groups", default=None, help="groups.csv de dedup.py (source_id -> group)")
    ap.add_argument("--out", help="Carpeta de salida de los manifiestos")
    ap.add_argument("--ratios", default="0.70,0.15,0.15", help="Proporciones train,val,test")
    ap.add_argument("--seed", type=int, default=20261023)
    ap.add_argument("--trials", type=int, default=200, help="Órdenes aleatorios a probar (se queda el más estratificado)")
    ap.add_argument("--exclude-classes", default=None, help="Etiquetas a excluir, separadas por comas")
    ap.add_argument("--force", action="store_true", help="Permite reemplazar un test congelado distinto")
    ap.add_argument("--materialize", default=None, help="Crea DIR/{train,val,test}/<clase>/ para Ultralytics")
    ap.add_argument("--link", choices=["copy", "symlink", "hardlink"], default="copy")
    ap.add_argument("--verify", default=None, metavar="DIR", help="Solo verifica el test congelado de DIR y sale")
    ap.add_argument("--assign-from", default=None, metavar="DIR",
                    help="Reutiliza la asignación source_id -> split de los train/val/test.csv de DIR (p. ej. para que el "
                         "modo imagen use exactamente las mismas fotos de test que el modo recortes). Falla si falta alguna fuente.")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.verify:
        ok, msg = verify_frozen(Path(args.verify))
        print(f"[split] {msg}")
        return 0 if ok else 1
    if not args.manifest or not args.out:
        raise SystemExit("--manifest y --out son obligatorios (salvo con --verify)")
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    df = read_manifests(args.manifest)
    if args.exclude_classes:
        excl = {c.strip() for c in args.exclude_classes.split(",")}
        df = df[~df["label"].isin(excl)].reset_index(drop=True)
    if args.groups:
        g = pd.read_csv(args.groups, dtype={"source_id": str, "group": str}, keep_default_na=False)[["source_id", "group"]]
        df = df.drop(columns=[c for c in ("group",) if c in df.columns]).merge(g, on="source_id", how="left")
        missing = df["group"].isna() | (df["group"] == "")
        if missing.any():
            print(f"[split] AVISO: {int(missing.sum())} ítems sin grupo en {args.groups}; uso su source_id")
        df.loc[missing, "group"] = "src:" + df.loc[missing, "source_id"]
    else:
        df["group"] = "src:" + df["source_id"].astype(str)
    ratios = tuple(float(x) for x in args.ratios.split(","))
    if len(ratios) != 3:
        raise SystemExit("--ratios necesita tres valores")

    if args.assign_from:
        prev = pd.concat([pd.read_csv(Path(args.assign_from) / f"{s}.csv", dtype=str, keep_default_na=False)[["source_id", "split"]]
                          for s in SPLITS], ignore_index=True)
        if (prev.groupby("source_id")["split"].nunique() > 1).any():
            raise SystemExit(f"{args.assign_from}: hay fuentes en varios splits; no se puede reutilizar")
        src2split = prev.drop_duplicates("source_id").set_index("source_id")["split"].to_dict()
        missing_src = sorted(set(df["source_id"]) - set(src2split))
        if missing_src:
            raise SystemExit(f"--assign-from: {len(missing_src)} fuentes sin split en {args.assign_from} (ej. {missing_src[:3]})")
        df["split"] = df["source_id"].map(src2split)
        score = float("nan")
    else:
        assign, score = assign_groups(df, ratios, args.seed, args.trials)
        df["split"] = df["group"].map(assign)
    df = df.sort_values("item_id", kind="stable").reset_index(drop=True)

    # Comprobaciones de fuga (deben ser 0 por construcción)
    leak_groups = int((df.groupby("group")["split"].nunique() > 1).sum())
    leak_sources = int((df.groupby("source_id")["split"].nunique() > 1).sum())
    if leak_groups or leak_sources:
        raise RuntimeError(f"Fuga detectada: {leak_groups} grupos y {leak_sources} fuentes en varios splits")

    parts = {s: df[df["split"] == s].reset_index(drop=True) for s in SPLITS}
    test_hash_content = content_hash(parts["test"])
    fz_path = out / FROZEN_NAME
    if fz_path.exists() and not args.force:
        prev = read_json(fz_path)
        if prev.get("sha256_contenido") != test_hash_content:
            print(f"[split] ERROR: ya hay un test congelado distinto en {fz_path}. Usa --force si de verdad quieres reemplazarlo.")
            return 2
    for s in ("train", "val"):
        write_csv(parts[s], out / f"{s}.csv")
    _write_readonly_csv(parts["test"], out / "test.csv")
    frozen = {
        "archivo": "test.csv",
        "sha256": sha256_file(out / "test.csv"),
        "sha256_contenido": test_hash_content,
        "n_items": int(len(parts["test"])),
        "n_grupos": int(parts["test"]["group"].nunique()),
        "semilla": args.seed,
        "creado": now_iso(),
        "nota": "CONGELADO: no usar para elegir modelos, hiperparámetros ni umbrales. Verificar con split.py --verify.",
    }
    write_json(fz_path, frozen)

    classes = sorted(df["label"].unique())
    tab = df.groupby(["split", "label"]).size().unstack(fill_value=0).reindex(index=list(SPLITS), columns=classes, fill_value=0)
    gmaj = group_majority_labels(df)
    gtab = df.drop_duplicates("group").assign(label=lambda x: x["group"].map(gmaj)).groupby(["split", "label"]).size()
    warnings = []
    for c in classes:
        for s in SPLITS:
            if tab.loc[s, c] == 0:
                warnings.append(f"La clase {c!r} no tiene ítems en {s} (muy pocos grupos)")
    summary = {
        "creado": now_iso(),
        "manifiestos": [{"ruta": str(Path(m).resolve()), "sha256": sha256_file(m)} for m in args.manifest],
        "grupos": str(Path(args.groups).resolve()) if args.groups else "source_id",
        "semilla": args.seed,
        "proporciones_objetivo": dict(zip(SPLITS, ratios)),
        "trials": args.trials,
        "puntaje_desviacion": score,
        "asignacion_desde": str(Path(args.assign_from).resolve()) if args.assign_from else None,
        "n_items": int(len(df)),
        "n_grupos": int(df["group"].nunique()),
        "n_fuentes": int(df["source_id"].nunique()),
        "items_por_split": {s: int(len(parts[s])) for s in SPLITS},
        "grupos_por_split": {s: int(parts[s]["group"].nunique()) for s in SPLITS},
        "items_por_split_y_clase": {s: {c: int(tab.loc[s, c]) for c in classes} for s in SPLITS},
        "grupos_por_split_y_clase_mayoritaria": {f"{s}/{c}": int(v) for (s, c), v in gtab.items()},
        "fuga_grupos_entre_splits": leak_groups,
        "fuga_fuentes_entre_splits": leak_sources,
        "test_congelado": frozen,
        "avisos": warnings,
    }
    write_json(out / "split_summary.json", summary)
    if args.materialize:
        materialize(parts, Path(args.materialize), args.link)
        summary["materializado_en"] = str(Path(args.materialize).resolve())
        write_json(out / "split_summary.json", summary)
    print(f"[split] ítems por split: {summary['items_por_split']}; grupos: {summary['grupos_por_split']}")
    print(tab.to_string())
    for w in warnings:
        print(f"[split] AVISO: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
