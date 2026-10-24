#!/usr/bin/env python
"""Entrena un clasificador YOLO (yolo11n-cls por defecto, o yolov8n-cls) en MPS, con presupuesto de tiempo.

* Tras la 1.ª época estima el tiempo total y lo escribe en ``train_status.json`` (y en consola).
* ``--max-minutes``: si la siguiente época no cabe en el presupuesto, para limpiamente.
* Reanudable: en cada época se guarda una copia completa (con optimizador) en
  ``weights/resume.pt``; ``--resume RUN_DIR`` continúa desde ahí (Ultralytics elimina el
  optimizador de ``last.pt`` al terminar, por eso se guarda esa copia aparte).
* ``--estimate-only``: entrena 1 época, informa la estimación y deja el run reanudable.
* Con ``--splits-dir`` escribe al final ``predicciones_yolo_{val,test}.csv`` (formato estándar)
  usando ``best.pt``.

``--data-dir`` es la carpeta que crea ``split.py --materialize`` (``train/``, ``val/``, ``test/``).

Ejemplo:
    .venv/bin/python -I pipeline/train_yolo_cls.py --data-dir pipeline/work/drberry/yolo_cls \
        --splits-dir pipeline/work/drberry/splits --project pipeline/work/drberry/runs --name y11n \
        --epochs 40 --max-minutes 25
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import PESOS_DIR, SPLITS, YOLO_CLS_WEIGHTS, build_predictions_frame, now_iso, pick_device, set_offline_env, write_csv, write_json  # noqa: E402

STATUS = "train_status.json"
CALLBACKS = ("on_train_start", "on_train_epoch_end", "on_model_save", "on_fit_epoch_end")


class TimeBudget:
    """Callbacks de Ultralytics: registra tiempos por época, estima el total y corta por presupuesto."""

    def __init__(self, max_minutes: float | None, status_path_fn: Any, estimate_only: bool = False) -> None:
        self.max_s = max_minutes * 60.0 if max_minutes else None
        self.status_path_fn = status_path_fn
        self.estimate_only = estimate_only
        self.t0 = time.time()
        self.t_last = self.t0
        self.epoch_times: list[float] = []
        self.stopped_by_time = False
        self.status: dict[str, Any] = {}
        self._pending = False

    def on_train_start(self, trainer: Any) -> None:
        self.t0 = self.t_last = time.time()

    def on_train_epoch_end(self, trainer: Any) -> None:
        self._pending = True  # distingue el fin de época real de la llamada extra de final_eval

    def on_model_save(self, trainer: Any) -> None:
        last = Path(trainer.last)
        if last.exists():
            shutil.copy2(last, last.with_name("resume.pt"))

    def on_fit_epoch_end(self, trainer: Any) -> None:
        now = time.time()
        if not self._pending:
            return  # llamada extra de final_eval (validación de best.pt)
        self._pending = False
        self.epoch_times.append(now - self.t_last)
        self.t_last = now
        done = trainer.epoch + 1
        mean = float(np.mean(self.epoch_times))
        remaining_epochs = max(trainer.epochs - done, 0)
        elapsed = now - self.t0
        est_total_min = (elapsed + mean * remaining_epochs) / 60.0
        if len(self.epoch_times) == 1:
            msg = f"[yolo] 1.ª época de esta sesión: {self.epoch_times[0]:.1f} s -> estimado {est_total_min:.1f} min para {trainer.epochs - trainer.start_epoch} épocas"
            if self.max_s:
                fit = int(max(0, (self.max_s - elapsed) // mean)) + 1
                msg += f"; con --max-minutes caben ~{min(fit, trainer.epochs - trainer.start_epoch)} épocas"
            print(msg, flush=True)
        if self.estimate_only:
            trainer.stop = True
        if self.max_s and elapsed + mean > self.max_s and remaining_epochs > 0:
            self.stopped_by_time = True
            trainer.stop = True
            print(f"[yolo] presupuesto de {self.max_s / 60:.1f} min alcanzado tras {done} épocas; run reanudable", flush=True)
        self.status = {
            "actualizado": now_iso(),
            "epocas_completadas": done,
            "epocas_objetivo": trainer.epochs,
            "segundos_por_epoca": [round(t, 2) for t in self.epoch_times],
            "segundos_por_epoca_media": round(mean, 2),
            "minutos_transcurridos_esta_sesion": round(elapsed / 60.0, 2),
            "minutos_estimados_total_esta_sesion": round(est_total_min, 2),
            "parado_por_tiempo": self.stopped_by_time,
            "solo_estimacion": self.estimate_only,
            "fitness": float(getattr(trainer, "fitness", 0) or 0),
            "metricas": {k: float(v) for k, v in (getattr(trainer, "metrics", None) or {}).items() if isinstance(v, (int, float))},
        }
        write_json(self.status_path_fn(trainer), self.status)


def predict_paths(weights: str | Path, paths: Sequence[str], imgsz: int, device: str, batch: int = 32) -> tuple[np.ndarray, list[str]]:
    """Probabilidades por clase (orden de ``model.names``) para una lista de imágenes."""
    from ultralytics import YOLO

    model = YOLO(str(weights))
    names = [model.names[i] for i in sorted(model.names)]
    probs = []
    for s in range(0, len(paths), batch):
        for r in model.predict(list(paths[s : s + batch]), imgsz=imgsz, device=device, verbose=False):
            probs.append(r.probs.data.float().cpu().numpy())
    return (np.stack(probs) if probs else np.zeros((0, len(names)))), names


def write_split_predictions(weights: Path, splits_dir: Path, out_dir: Path, imgsz: int, device: str) -> list[Path]:
    written = []
    for s in ("val", "test"):
        f = splits_dir / f"{s}.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f, keep_default_na=False, dtype={"label": str, "source_id": str})
        probs, names = predict_paths(weights, df["path"].tolist(), imgsz, device)
        dest = out_dir / f"predicciones_yolo_{s}.csv"
        write_csv(build_predictions_frame(df, probs, names, df["path"].tolist(), df["label"].tolist(), f"yolo_cls:{weights.name}"), dest)
        written.append(dest)
        print(f"[yolo] predicciones {s}: {dest}")
    return written


def parse_extra(items: Sequence[str]) -> dict[str, Any]:
    """``["cos_lr=True", "dropout=0.2"]`` -> ``{"cos_lr": True, "dropout": 0.2}`` (valores como YAML)."""
    import yaml

    out: dict[str, Any] = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"--extra espera CLAVE=VALOR: {it!r}")
        k, v = it.split("=", 1)
        out[k.strip()] = yaml.safe_load(v)
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", help="Carpeta con train/ val/ (test/) por clase (split.py --materialize)")
    ap.add_argument("--model", default=str(YOLO_CLS_WEIGHTS), help="Pesos iniciales: ruta o nombre (yolo11n-cls.pt, yolov8n-cls.pt)")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--device", default="auto", help="mps, cpu o auto")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--patience", type=int, default=15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lr0", type=float, default=None)
    ap.add_argument("--max-minutes", type=float, default=None, help="Presupuesto de tiempo de esta sesión de entrenamiento")
    ap.add_argument("--estimate-only", action="store_true", help="Solo 1 época para estimar el tiempo (queda reanudable)")
    ap.add_argument("--project", default=str(PESOS_DIR.parent / "runs"), help="Carpeta de runs")
    ap.add_argument("--name", default="yolo_cls")
    ap.add_argument("--resume", default=None, metavar="RUN_DIR", help="Reanuda desde RUN_DIR/weights/resume.pt")
    ap.add_argument("--splits-dir", default=None, help="Si se da, escribe predicciones de val y test con best.pt")
    ap.add_argument("--predict-only", default=None, metavar="WEIGHTS", help="No entrena: solo predicciones con estos pesos")
    ap.add_argument("--pred-out", default=None, help="Carpeta para las predicciones (por defecto el run)")
    ap.add_argument("--plots", action="store_true")
    ap.add_argument("--extra", action="append", default=[], metavar="CLAVE=VALOR",
                    help="Argumento extra para model.train de Ultralytics (repetible; valor leído como YAML), p. ej. cos_lr=True, dropout=0.2")
    ap.add_argument("--allow-online", action="store_true")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    set_offline_env(args.allow_online)
    device = pick_device(args.device)
    if device == "cuda":
        device = "0"

    if args.predict_only:
        if not args.splits_dir:
            raise SystemExit("--predict-only necesita --splits-dir")
        w = Path(args.predict_only).resolve()
        write_split_predictions(w, Path(args.splits_dir), Path(args.pred_out or w.parent.parent), args.imgsz, device)
        return 0

    from ultralytics import YOLO

    def status_path(trainer: Any) -> Path:
        return Path(trainer.save_dir) / STATUS

    budget = TimeBudget(args.max_minutes, status_path, args.estimate_only)
    t_start = time.time()
    if args.resume:
        run = Path(args.resume).resolve()
        ckpt = run / "weights" / "resume.pt"
        if not ckpt.exists():
            raise SystemExit(f"No existe {ckpt}")
        st = json.loads((run / STATUS).read_text()) if (run / STATUS).exists() else {}
        if st.get("completado"):
            raise SystemExit(f"El run {run} ya terminó; no hay nada que reanudar")
        model = YOLO(str(ckpt))
        for ev in CALLBACKS:
            model.add_callback(ev, getattr(budget, ev))
        model.train(resume=str(ckpt), device=device, workers=args.workers)
    else:
        if not args.data_dir:
            raise SystemExit("--data-dir es obligatorio para entrenar")
        data = Path(args.data_dir).resolve()
        for s in ("train", "val"):
            if not (data / s).is_dir():
                raise SystemExit(f"Falta {data / s} (usa split.py --materialize)")
        model = YOLO(args.model)
        for ev in CALLBACKS:
            model.add_callback(ev, getattr(budget, ev))
        kw: dict[str, Any] = dict(
            data=str(data),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=device,
            workers=args.workers,
            patience=args.patience,
            seed=args.seed,
            deterministic=True,
            project=str(Path(args.project).resolve()),
            name=args.name,
            exist_ok=False,
            plots=args.plots,
            verbose=False,
        )
        if args.lr0 is not None:
            kw["lr0"] = args.lr0
        kw.update(parse_extra(args.extra))
        model.train(**kw)

    trainer = model.trainer
    run_dir = Path(trainer.save_dir)
    best = Path(trainer.best) if Path(trainer.best).exists() else Path(trainer.last)
    completed = not budget.stopped_by_time and not args.estimate_only
    try:
        names = model.names
        class_names = [names[i] for i in sorted(names)]
    except Exception:  # noqa: BLE001
        class_names = None
    status = {**budget.status, "completado": completed, "best": str(best), "resume": str(run_dir / "weights" / "resume.pt"),
              "minutos_sesion": round((time.time() - t_start) / 60.0, 2), "dispositivo": device, "modelo_inicial": args.model,
              "clases": class_names}
    write_json(run_dir / STATUS, status)
    print(f"[yolo] run: {run_dir} | best: {best} | completado: {completed}")
    if not completed:
        print(f"[yolo] reanudar con: --resume {run_dir}")
    if args.splits_dir and not args.estimate_only:
        write_split_predictions(best, Path(args.splits_dir), Path(args.pred_out) if args.pred_out else run_dir, args.imgsz, device)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
