#!/usr/bin/env python
"""Inferencia para la demo: una imagen, una carpeta o frames de cámara (p. ej. la del AgiBot D1).

Devuelve, por imagen o frame, un JSON con la clase decidida, su confianza, el puntaje de
enfermedad ``1 - p(sana)``, si es ``sospecha`` (puntaje >= umbral), las probabilidades y la
latencia medida (preproceso, inferencia, total) en milisegundos.

Modelos aceptados (``--weights``):
* ``.pt`` de Ultralytics clasificación (``train_yolo_cls.py``),
* ``clip_probe.joblib`` o ``clip_zeroshot.joblib`` (``clip_baseline.py``). Son pickles: cargue solo
  archivos generados por este pipeline.

Para la demo con el robot mirando una pantalla conviene recortar la zona útil del frame:
``--roi x,y,w,h`` (fracciones 0-1) o ``--center-crop 0.7``.

Ejemplos:
    .venv/bin/python -I pipeline/predict.py --weights pipeline/work/drberry/clip/clip_probe.joblib \
        --threshold pipeline/work/drberry/clip/threshold_probe.json --image hoja.jpg
    .venv/bin/python -I pipeline/predict.py --weights best.pt --threshold threshold.json --camera 0 \
        --frames 0 --interval 1.0 --center-crop 0.7 --log resultados/demo_predicciones.jsonl
    .venv/bin/python -I pipeline/predict.py --weights best.pt --image hoja.jpg --bench 50 --bench-out latencia.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterator, Protocol, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from common import DEFAULT_HEALTHY, OPEN_CLIP_CACHE, healthy_index, list_images, load_threshold, now_iso, pick_device, set_offline_env, softmax, write_json  # noqa: E402


class Classifier(Protocol):
    classes: list[str]
    name: str

    def predict_proba(self, images: Sequence[Image.Image]) -> np.ndarray: ...


class YoloClassifier:
    def __init__(self, weights: str | Path, device: str = "auto", imgsz: int = 224) -> None:
        from ultralytics import YOLO

        self.model = YOLO(str(weights))
        self.device = pick_device(device)
        self.imgsz = imgsz
        self.classes = [self.model.names[i] for i in sorted(self.model.names)]
        self.name = f"yolo_cls:{Path(weights).name}"

    def predict_proba(self, images: Sequence[Image.Image]) -> np.ndarray:
        # Ultralytics acepta PIL (RGB) y hace él mismo la conversión a BGR, igual que al leer archivos.
        res = self.model.predict([im.convert("RGB") for im in images], imgsz=self.imgsz, device=self.device, verbose=False)
        return np.stack([r.probs.data.float().cpu().numpy() for r in res])


class ClipHeadClassifier:
    def __init__(self, head_path: str | Path, device: str = "auto", cache_dir: str | Path = OPEN_CLIP_CACHE) -> None:
        import joblib

        from clip_baseline import ClipEmbedder

        self.head: dict[str, Any] = joblib.load(head_path)
        if self.head.get("tipo") not in ("clip_probe", "clip_zeroshot"):
            raise ValueError(f"{head_path} no es un cabezal CLIP de este pipeline")
        self.embedder = ClipEmbedder(self.head["clip_model"], self.head["pretrained"], device, cache_dir)
        self.classes = list(self.head["classes"])
        self.name = f"{self.head['tipo']}:{Path(head_path).name}"

    def predict_proba(self, images: Sequence[Image.Image]) -> np.ndarray:
        tiles = int(self.head.get("tiles", 0) or 0)
        if self.head["tipo"] == "clip_probe":
            return self.head["sk_model"].predict_proba(self.embedder.features_pil(images, tiles))
        emb = self.embedder.embed_pil(images)
        return softmax(self.head["logit_scale"] * emb @ np.asarray(self.head["text_mat"]).T, axis=1)


def load_classifier(weights: str | Path, device: str = "auto", imgsz: int = 224) -> Classifier:
    p = Path(weights)
    if p.suffix == ".joblib":
        return ClipHeadClassifier(p, device)
    return YoloClassifier(p, device, imgsz)


# --------------------------------------------------------------------------- preproceso y decisión

def parse_roi(spec: str | None) -> tuple[float, float, float, float] | None:
    if not spec:
        return None
    vals = [float(v) for v in spec.split(",")]
    if len(vals) != 4 or not all(0 <= v <= 1 for v in vals):
        raise ValueError("--roi espera x,y,w,h en fracciones 0-1")
    return vals[0], vals[1], vals[2], vals[3]


def crop_frame(im: Image.Image, roi: tuple[float, float, float, float] | None = None, center: float | None = None) -> Image.Image:
    W, H = im.size
    if roi:
        x, y, w, h = roi
        return im.crop((int(x * W), int(y * H), int(min(1.0, x + w) * W), int(min(1.0, y + h) * H)))
    if center and 0 < center < 1:
        cw, ch = W * center, H * center
        return im.crop((int((W - cw) / 2), int((H - ch) / 2), int((W + cw) / 2), int((H + ch) / 2)))
    return im


def decide_one(probs: np.ndarray, classes: Sequence[str], healthy: str, threshold: float | None) -> dict[str, Any]:
    """Decisión para un vector de probabilidades (misma regla que ``common.decide``)."""
    probs = np.asarray(probs, dtype=float)
    hi = healthy_index(classes, healthy)
    score = float(1.0 - probs[hi])
    top = int(probs.argmax())
    if threshold is None:
        cls = top
        sospecha = cls != hi
    else:
        sospecha = score >= threshold
        masked = probs.copy()
        masked[hi] = -np.inf
        cls = int(masked.argmax()) if sospecha else hi
    return {
        "clase": classes[cls],
        "confianza": round(float(probs[cls]), 4),
        "clase_top1": classes[top],
        "p_enfermedad": round(score, 4),
        "sospecha": bool(sospecha),
        "umbral": threshold,
        "probabilidades": {c: round(float(p), 4) for c, p in zip(classes, probs)},
    }


def run_one(clf: Classifier, im: Image.Image, healthy: str, threshold: float | None, roi: Any = None, center: float | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    x = crop_frame(ImageOps.exif_transpose(im).convert("RGB"), roi, center)
    t1 = time.perf_counter()
    probs = clf.predict_proba([x])[0]
    t2 = time.perf_counter()
    out = decide_one(probs, clf.classes, healthy, threshold)
    out["latencia_ms"] = {"preproceso": round((t1 - t0) * 1000, 2), "inferencia": round((t2 - t1) * 1000, 2), "total": round((t2 - t0) * 1000, 2)}
    out["modelo"] = clf.name
    out["timestamp"] = now_iso()
    return out


def _redact(source: str) -> str:
    """Quita usuario/contraseña de una URL de flujo antes de escribirla en registros."""
    from urllib.parse import urlsplit, urlunsplit

    if "://" not in str(source):
        return str(source)
    u = urlsplit(str(source))
    host = u.hostname or ""
    netloc = host + (f":{u.port}" if u.port else "")
    return urlunsplit((u.scheme, netloc, u.path, "", ""))


def camera_frames(source: str, n: int, interval: float) -> Iterator[Image.Image]:
    """Frames RGB de una cámara local (índice) o de un flujo (URL rtsp/http, p. ej. el del robot)."""
    import cv2

    cap = cv2.VideoCapture(int(source) if str(source).isdigit() else source)
    if not cap.isOpened():
        raise SystemExit(f"No pude abrir la cámara/flujo {source!r} (¿permiso de cámara en macOS? ¿URL correcta?)")
    try:
        k = 0
        while n <= 0 or k < n:
            ok, frame = cap.read()
            if not ok:
                break
            yield Image.fromarray(frame[:, :, ::-1])
            k += 1
            if interval > 0:
                time.sleep(interval)
    finally:
        cap.release()


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", required=True, help=".pt de Ultralytics o .joblib de clip_baseline")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--image", help="Una imagen")
    src.add_argument("--dir", help="Carpeta de imágenes")
    src.add_argument("--camera", help="Índice de cámara (0, 1, ...) o URL de flujo rtsp/http (cv2.VideoCapture)")
    ap.add_argument("--threshold", default=None, help="Número o threshold.json; sin él se usa argmax")
    ap.add_argument("--healthy-class", default=DEFAULT_HEALTHY)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--roi", default=None, help="x,y,w,h en fracciones del frame")
    ap.add_argument("--center-crop", type=float, default=None, help="Fracción central del frame a conservar")
    ap.add_argument("--frames", type=int, default=1, help="(cámara) número de frames; 0 = sin fin")
    ap.add_argument("--interval", type=float, default=0.5, help="(cámara) segundos entre frames")
    ap.add_argument("--save-frames", default=None, help="(cámara) carpeta donde guardar los frames procesados")
    ap.add_argument("--log", default=None, help="Archivo JSONL donde añadir cada resultado (registro para alertas)")
    ap.add_argument("--no-warmup", action="store_true", help="No hacer la inferencia de calentamiento")
    ap.add_argument("--bench", type=int, default=0, help="Repite la imagen N veces y reporta p50/p95 de latencia")
    ap.add_argument("--bench-out", default=None, help="JSON de salida del benchmark")
    ap.add_argument("--allow-online", action="store_true")
    return ap


def main(argv: Sequence[str] | None = None, classifier: Classifier | None = None) -> int:
    args = build_parser().parse_args(argv)
    set_offline_env(args.allow_online)
    thr = load_threshold(args.threshold)
    roi = parse_roi(args.roi)
    t0 = time.perf_counter()
    clf = classifier or load_classifier(args.weights, args.device, args.imgsz)
    load_ms = (time.perf_counter() - t0) * 1000
    if not args.no_warmup:
        clf.predict_proba([Image.new("RGB", (args.imgsz, args.imgsz), (90, 140, 70))])
    log = open(args.log, "a", encoding="utf-8") if args.log else None

    def emit(res: dict[str, Any]) -> None:
        line = json.dumps(res, ensure_ascii=False)
        print(line, flush=True)
        if log:
            log.write(line + "\n")
            log.flush()

    try:
        if args.image and args.bench > 0:
            with Image.open(args.image) as im:
                im.load()
                times = [run_one(clf, im, args.healthy_class, thr, roi, args.center_crop)["latencia_ms"]["total"] for _ in range(args.bench)]
            bench = {"modelo": clf.name, "n": args.bench, "carga_modelo_ms": round(load_ms, 1),
                     "latencia_ms": {"p50": float(np.percentile(times, 50)), "p95": float(np.percentile(times, 95)), "media": float(np.mean(times)), "max": float(np.max(times))},
                     "dispositivo": getattr(clf, "device", None) or getattr(getattr(clf, "embedder", None), "device", None), "creado": now_iso()}
            print(json.dumps(bench, ensure_ascii=False))
            if args.bench_out:
                write_json(args.bench_out, bench)
        elif args.image:
            with Image.open(args.image) as im:
                res = run_one(clf, im, args.healthy_class, thr, roi, args.center_crop)
            emit({"fuente": str(Path(args.image).resolve()), **res})
        elif args.dir:
            for p in list_images(args.dir):
                with Image.open(p) as im:
                    res = run_one(clf, im, args.healthy_class, thr, roi, args.center_crop)
                emit({"fuente": str(p), **res})
        else:
            save = Path(args.save_frames) if args.save_frames else None
            if save:
                save.mkdir(parents=True, exist_ok=True)
            for k, frame in enumerate(camera_frames(args.camera, args.frames, args.interval)):
                res = run_one(clf, frame, args.healthy_class, thr, roi, args.center_crop)
                src = f"camara:{_redact(args.camera)}:frame{k}"
                if save:
                    fp = save / f"frame_{time.strftime('%Y%m%d_%H%M%S')}_{k:05d}.jpg"
                    crop_frame(frame, roi, args.center_crop).save(fp, quality=90)
                    src = str(fp)
                emit({"fuente": src, **res})
    except KeyboardInterrupt:
        pass
    finally:
        if log:
            log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
