#!/usr/bin/env python
"""Aumentos fotométricos y de "pantalla vista por cámara" para el clasificador de hojas (D1).

Simula la cadena hoja -> pantalla de portátil -> cámara gran angular del robot: brillo/contraste/gamma
cambiantes, tinte azul/blanco de la pantalla, hoja pequeña en el cuadro (reducción y re-ampliación),
desenfoque (gaussiano y de movimiento), moiré, viñeteo/reflejo especular, ruido y compresión JPEG, y
opcionalmente la hoja pegada sobre un marco de pantalla negro.

Todos los parámetros son SUPUESTOS plausibles (no medidos con la cámara real). Determinista: cada
llamada usa un ``numpy.random.Generator`` (semilla fija) y devuelve también los parámetros muestreados.

Uso como módulo:
    from augment_screen import augment, augment_many
    im2, params = augment(im, np.random.default_rng(123))
    versiones = augment_many(im, k=5, seed=123)

CLI (muestras para inspección visual):
    .venv/bin/python -I pipeline/augment_screen.py --image hoja.jpg --out muestras/ --k 6 --seed 1
"""
from __future__ import annotations

import argparse
import math
from io import BytesIO
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

# probabilidad de aplicar cada efecto (con strength=1)
P = {"foto": 0.95, "tinte": 0.8, "baja_res": 0.7, "blur": 0.5, "motion": 0.2, "moire": 0.35, "vineta": 0.5,
     "especular": 0.45, "ruido": 0.55, "jpeg": 0.7, "marco": 0.3, "hue": 0.4}


def _arr(im: Image.Image) -> np.ndarray:
    return np.asarray(im.convert("RGB"), dtype=np.float32)


def _img(a: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def _coords(h: int, w: int) -> tuple[np.ndarray, np.ndarray]:
    return np.mgrid[0:h, 0:w].astype(np.float32)


def _motion_kernel(length: int, angle: float) -> np.ndarray:
    k = np.zeros((length, length), np.float32)
    c = (length - 1) / 2
    for t in np.linspace(-c, c, length * 2):
        x, y = int(round(c + t * math.cos(angle))), int(round(c + t * math.sin(angle)))
        if 0 <= x < length and 0 <= y < length:
            k[y, x] = 1
    return k / k.sum()


def augment(im: Image.Image, rng: np.random.Generator, strength: float = 1.0, frame: bool | None = None) -> tuple[Image.Image, dict[str, Any]]:
    """Aplica una cadena aleatoria de efectos. ``strength`` escala las probabilidades (0-1.3). ``frame`` fuerza/anula el marco."""
    im = im.convert("RGB")
    W, H = im.size
    par: dict[str, Any] = {}
    on = lambda name: rng.random() < min(1.0, P[name] * strength)  # noqa: E731

    # --- 1. fotometría de la pantalla (brillo, contraste, gamma, saturación, tono)
    if on("foto"):
        par["brillo"] = float(rng.uniform(0.6, 1.4))
        par["contraste"] = float(rng.uniform(0.65, 1.3))
        par["gamma"] = float(math.exp(rng.uniform(math.log(0.6), math.log(1.6))))
        par["saturacion"] = float(rng.uniform(0.6, 1.4))
        im = ImageEnhance.Brightness(im).enhance(par["brillo"])
        im = ImageEnhance.Contrast(im).enhance(par["contraste"])
        a = (_arr(im) / 255.0).clip(0, 1) ** par["gamma"] * 255.0
        im = ImageEnhance.Color(_img(a)).enhance(par["saturacion"])
    if on("hue"):
        par["tono_grados"] = float(rng.uniform(-12, 12))  # desplazamiento leve
        hsv = np.asarray(im.convert("HSV")).copy()
        hsv[..., 0] = ((hsv[..., 0].astype(np.int16) + int(round(par["tono_grados"] / 360 * 256))) % 256).astype(np.uint8)
        im = Image.fromarray(hsv, "HSV").convert("RGB")
    a = _arr(im)
    # --- 2. tinte de pantalla (azul/blanco) y balance de blancos
    if on("tinte"):
        modo = rng.choice(["azul", "blanco", "calido", "libre"], p=[0.45, 0.25, 0.1, 0.2])
        if modo == "azul":
            g = np.array([rng.uniform(0.82, 0.97), rng.uniform(0.92, 1.03), rng.uniform(1.05, 1.22)])
        elif modo == "blanco":  # lavado hacia blanco: mezcla con blanco
            g = np.ones(3)
            a = a * (1 - (m := rng.uniform(0.05, 0.25))) + 255.0 * m * np.array([0.97, 1.0, 1.0])
            par["lavado_blanco"] = float(m)
        elif modo == "calido":
            g = np.array([rng.uniform(1.03, 1.15), 1.0, rng.uniform(0.85, 0.97)])
        else:
            g = rng.uniform(0.88, 1.12, size=3)
        a = a * g
        par["tinte"] = str(modo)
    im = _img(a)
    # --- 3. marco de pantalla: la hoja (ya con tinte) pegada sobre un fondo/bisel oscuro con la pantalla más pequeña
    usar_marco = (rng.random() < P["marco"] * strength) if frame is None else frame
    if usar_marco:
        s = float(rng.uniform(0.55, 0.92))
        fondo = int(rng.integers(0, 40))
        canvas = Image.new("RGB", (W, H), (fondo, fondo, min(255, fondo + int(rng.integers(0, 8)))))
        sw, sh = max(8, int(W * s)), max(8, int(H * s))
        # bisel negro fino alrededor de la pantalla
        bz = int(rng.integers(2, 12))
        inner = im.resize((max(4, sw - 2 * bz), max(4, sh - 2 * bz)), Image.Resampling.BILINEAR)
        scr = Image.new("RGB", (sw, sh), (5, 5, 5))
        scr.paste(inner, (bz, bz))
        ox, oy = int(rng.integers(0, W - sw + 1)), int(rng.integers(0, H - sh + 1))
        canvas.paste(scr, (ox, oy))
        im = canvas
        par["marco_escala"] = s
    a = _arr(im)
    # --- 4. hoja pequeña en el cuadro: reducir al 15-40 % del lado y re-ampliar
    if on("baja_res"):
        f = float(rng.uniform(0.15, 0.40))
        sm = im.resize((max(8, int(W * f)), max(8, int(H * f))), Image.Resampling.BILINEAR if rng.random() < 0.6 else Image.Resampling.BICUBIC)
        im = sm.resize((W, H), Image.Resampling.BILINEAR if rng.random() < 0.7 else Image.Resampling.BICUBIC)
        par["fraccion_lado"] = f
    # --- 5. desenfoque
    if on("blur"):
        par["blur_radio"] = float(rng.uniform(0.8, 3.5)) * W / 1024
        im = im.filter(ImageFilter.GaussianBlur(radius=par["blur_radio"]))
    if on("motion"):
        L = int(rng.integers(5, 12)) | 1
        ang = float(rng.uniform(0, math.pi))
        k = _motion_kernel(L, ang)
        a = _arr(im)
        from numpy.lib.stride_tricks import sliding_window_view

        pad = L // 2
        ap = np.pad(a, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
        win = sliding_window_view(ap, (L, L), axis=(0, 1))  # (H, W, 3, L, L)
        im = _img(np.einsum("hwcij,ij->hwc", win, k))
        par["movimiento_px"] = L
    a = _arr(im)
    yy, xx = _coords(H, W)
    # --- 6. moiré suave: batido de dos rejillas casi iguales (multiplicativo)
    if on("moire"):
        amp = float(rng.uniform(0.02, 0.08))
        per = float(rng.uniform(6, 26)) * W / 1024
        th = float(rng.uniform(0, math.pi))
        d_th, d_per = float(rng.uniform(0.02, 0.12)), float(rng.uniform(0.02, 0.1))
        g1 = np.cos(2 * math.pi * (xx * math.cos(th) + yy * math.sin(th)) / per)
        g2 = np.cos(2 * math.pi * (xx * math.cos(th + d_th) + yy * math.sin(th + d_th)) / (per * (1 + d_per)))
        a = a * (1 + amp * (g1 * g2))[..., None]
        par["moire_amp"] = amp
    # --- 7. viñeteo y reflejo especular suave
    if on("vineta"):
        v = float(rng.uniform(0.1, 0.45))
        r2 = ((xx - W / 2) ** 2 + (yy - H / 2) ** 2) / ((W / 2) ** 2 + (H / 2) ** 2)
        a = a * (1 - v * r2)[..., None]
        par["vineta"] = v
    if on("especular"):
        cx, cy = rng.uniform(0.1, 0.9) * W, rng.uniform(0.1, 0.9) * H
        sx, sy = rng.uniform(0.12, 0.4) * W, rng.uniform(0.08, 0.35) * H
        al = float(rng.uniform(0.12, 0.45))
        blob = np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2))
        if rng.random() < 0.4:  # franja diagonal (reflejo de ventana)
            th = rng.uniform(0, math.pi)
            d = (xx - cx) * math.cos(th) + (yy - cy) * math.sin(th)
            blob = np.maximum(blob, np.exp(-((d / (rng.uniform(0.05, 0.15) * W)) ** 2)) * 0.8)
        tono = np.array([1.0, 1.0, 1.0]) if rng.random() < 0.6 else np.array([0.92, 0.97, 1.0])
        a = a * (1 - al * blob)[..., None] + 255.0 * al * blob[..., None] * tono
        par["especular_alfa"] = al
    # --- 8. ruido
    if on("ruido"):
        sg = float(rng.uniform(2, 14))
        a = a + rng.normal(0, sg, a.shape).astype(np.float32)
        par["ruido_sigma"] = sg
    im = _img(a)
    # --- 9. compresión JPEG
    if on("jpeg"):
        q = int(rng.integers(30, 81))
        b = BytesIO()
        im.save(b, format="JPEG", quality=q)
        b.seek(0)
        im = Image.open(b).convert("RGB")
        par["jpeg_q"] = q
    return im, par


def augment_many(im: Image.Image, k: int, seed: int, strength: float = 1.0) -> list[Image.Image]:
    """``k`` versiones deterministas (semilla ``seed``)."""
    rng = np.random.default_rng(seed)
    return [augment(im, rng, strength)[0] for _ in range(k)]


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args(argv)
    from PIL import ImageOps

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with Image.open(args.image) as f:
        im = ImageOps.exif_transpose(f).convert("RGB")
    rng = np.random.default_rng(args.seed)
    for i in range(args.k):
        x, p = augment(im, rng)
        x.save(out / f"aug_{i}.jpg", quality=92)
        print(i, p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
