"""Preprocesamiento común (idéntico al panel) y aumentos realistas de "pantalla vista por la cámara del robot".

`corregir_color` y `recorte_por_color` son copia literal de robot/panel_demo.py (no se importa el panel
para no arrastrar sus dependencias). `preprocesar` = corregir_color -> recorte_por_color (si no hay mancha
de hoja, se devuelve la imagen corregida entera, igual que el panel con auto-recorte).

`aug_camara` se calibró mirando resultados/ml/capturas_pantalla/ (hoja cian/lavada, luces altas quemadas,
reflejos circulares de las luminarias, borde negro del bisel con el cuarto detrás, perspectiva, viñeteo).
Todos los rangos son supuestos calibrados a ojo, no medidos.
"""
from __future__ import annotations

import math
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageFilter

S = 640  # lado de trabajo (el ROI real de la cámara es ~1152x648)


# ----------------------------------------------------------------------------- copia exacta del panel
def corregir_color(im: Image.Image) -> Image.Image:
    """Balance de blancos 'mundo gris' + CLAHE en luminancia: quita el tinte cian/azul de la pantalla."""
    a = np.asarray(im).astype(np.float32)
    medias = a.reshape(-1, 3).mean(axis=0) + 1e-6
    a = np.clip(a * (medias.mean() / medias), 0, 255).astype(np.uint8)
    lab = cv2.cvtColor(a, cv2.COLOR_RGB2LAB)
    lab[..., 0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lab[..., 0])
    return Image.fromarray(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB))


def recorte_por_color(crop: Image.Image, margen: float = 0.15, area_min: float = 0.01):
    """Busca la mancha de color hoja más grande (verde, amarillo o rojizo) y devuelve su caja (px) o None."""
    a = cv2.cvtColor(np.asarray(crop), cv2.COLOR_RGB2HSV)
    h, s, v = a[..., 0], a[..., 1], a[..., 2]
    verde = (h >= 25) & (h <= 95) & (s >= 45) & (v >= 40)
    amarillo = (h >= 15) & (h < 25) & (s >= 70) & (v >= 60)
    mask = (verde | amarillo).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(cv2.morphologyEx(mask, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k, iterations=2)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    H, W = mask.shape
    if cv2.contourArea(c) < area_min * W * H:
        return None
    x, y, w, hh = cv2.boundingRect(c)
    mx, my = int(w * margen), int(hh * margen)
    x0, y0 = max(0, x - mx), max(0, y - my)
    x1, y1 = min(W, x + w + mx), min(H, y + hh + my)
    lado = max(x1 - x0, y1 - y0)  # casi cuadrado: las teselas 3x3 trabajan mejor
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    x0, x1 = max(0, cx - lado // 2), min(W, cx + lado // 2)
    y0, y1 = max(0, cy - lado // 2), min(H, cy + lado // 2)
    return x0, y0, x1 - x0, y1 - y0


def preprocesar(im: Image.Image) -> Image.Image:
    """Lo que hace el panel antes de clasificar: corregir_color y recorte por color de hoja (si hay)."""
    im = corregir_color(im.convert("RGB"))
    b = recorte_por_color(im)
    return im.crop((b[0], b[1], b[0] + b[2], b[1] + b[3])) if b else im


def cargar(path, lado: int = S) -> Image.Image:
    from PIL import ImageOps

    with Image.open(path) as f:
        im = ImageOps.exif_transpose(f).convert("RGB")
    if max(im.size) > lado:
        r = lado / max(im.size)
        im = im.resize((max(8, round(im.width * r)), max(8, round(im.height * r))), Image.Resampling.LANCZOS)
    return im


# ----------------------------------------------------------------------------- aumentos de cámara
def _clip(a):
    return np.clip(a, 0, 255)


def _img(a):
    return Image.fromarray(_clip(a).astype(np.uint8))


def _disc_mask(H, W, cx, cy, r, soft):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    return np.clip((r - d) / max(soft, 1e-3) + 0.5, 0, 1)


def aug_camara(im: Image.Image, rng: np.random.Generator, strength: float = 1.0) -> tuple[Image.Image, dict]:
    """Cadena aleatoria hoja -> pantalla -> cámara. Devuelve imagen RGB y los parámetros muestreados.
    `strength` (0-1.3) escala las probabilidades."""
    par: dict = {}
    on = lambda p: rng.random() < min(1.0, p * strength)  # noqa: E731
    im = im.convert("RGB")
    if max(im.size) != S:
        r = S / max(im.size)
        im = im.resize((max(8, round(im.width * r)), max(8, round(im.height * r))), Image.Resampling.BILINEAR)
    W, H = im.size

    # 1. encuadre: zoom parcial (el ROI de la cámara corta la hoja)
    if on(0.4):
        f = float(rng.uniform(0.65, 0.95))
        cw, ch = int(W * f), int(H * f)
        x0, y0 = int(rng.integers(0, W - cw + 1)), int(rng.integers(0, H - ch + 1))
        im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.Resampling.BILINEAR)
        par["zoom"] = f
    a = np.asarray(im, dtype=np.float32)

    # 2. fotometría de la pantalla: gamma que aclara, ganancia con recorte de luces altas, contraste y saturación bajos
    g = float(math.exp(rng.uniform(math.log(0.55), math.log(1.25))))
    a = (a / 255.0) ** g * 255.0
    par["gamma"] = g
    gain = float(rng.uniform(1.0, 1.5)) if on(0.7) else float(rng.uniform(0.75, 1.0))
    a = _clip(a * gain)
    par["ganancia"] = gain
    c = float(rng.uniform(0.5, 1.05))
    a = (a - a.mean()) * c + a.mean()
    par["contraste"] = c
    gray = a.mean(axis=2, keepdims=True)
    sat = float(rng.uniform(0.5, 1.15))
    a = gray + (a - gray) * sat
    par["saturacion"] = sat

    # 3. tinte de color: cian/azul frío (dominante en capturas reales), lavado hacia cian claro, neutro o cálido
    modo = str(rng.choice(["cian", "azul", "neutro", "calido"], p=[0.45, 0.25, 0.15, 0.15]))
    if modo == "cian":
        k = np.array([rng.uniform(0.62, 0.95), rng.uniform(0.95, 1.05), rng.uniform(0.95, 1.2)])
    elif modo == "azul":
        k = np.array([rng.uniform(0.7, 0.95), rng.uniform(0.85, 1.0), rng.uniform(1.05, 1.35)])
    elif modo == "calido":
        k = np.array([rng.uniform(1.03, 1.2), 1.0, rng.uniform(0.75, 0.95)])
    else:
        k = rng.uniform(0.93, 1.07, size=3)
    a = a * k
    if modo in ("cian", "azul") and on(0.8):
        m = float(rng.uniform(0.04, 0.25))
        a = a * (1 - m) + m * np.array([205.0, 238.0, 245.0])
        par["lavado"] = m
    par["tinte"] = modo
    a = _clip(a)
    im = _img(a)

    # 4. hoja reducida dentro de un marco negro de pantalla (a veces con el cuarto detrás, abajo)
    if on(0.3):
        s = float(rng.uniform(0.5, 0.9))
        sw, sh = int(W * s), int(H * s)
        bz = int(rng.integers(2, 14))
        scr = Image.new("RGB", (sw, sh), (4, 4, 4))
        scr.paste(im.resize((max(4, sw - 2 * bz), max(4, sh - 2 * bz)), Image.Resampling.BILINEAR), (bz, bz))
        fondo = int(rng.integers(5, 45))
        canvas = np.full((H, W, 3), fondo, np.float32) + rng.normal(0, 3, (H, W, 1)).astype(np.float32)
        ox, oy = int(rng.integers(0, W - sw + 1)), int(rng.integers(0, H - sh + 1))
        canvas[oy : oy + sh, ox : ox + sw] = np.asarray(scr, np.float32)
        im = _img(canvas)
        par["marco"] = s
    # 4b. franja de bisel oscuro con el cuarto/portátil visible a un costado (muy frecuente en las capturas)
    elif on(0.55):
        w = int(W * rng.uniform(0.08, 0.3))
        side = int(rng.integers(0, 4))
        a = np.asarray(im, np.float32)
        base = float(rng.uniform(8, 40))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        strip = np.full((H, W, 3), base, np.float32)
        for _ in range(int(rng.integers(0, 4))):  # manchas de objetos del cuarto
            cx, cy, rr = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.04, 0.15) * W
            strip += (np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / rr**2))[..., None] * rng.uniform(10, 60)).astype(np.float32)
        m = np.zeros((H, W), np.float32)
        if side == 0:
            m[:, W - w :] = 1
        elif side == 1:
            m[:, :w] = 1
        elif side == 2:
            m[H - w :, :] = 1
        else:
            m[:w, :] = 1
        m = cv2.GaussianBlur(m, (0, 0), 2)
        im = _img(a * (1 - m[..., None]) + strip * m[..., None])
        par["bisel"] = side
    a = np.asarray(im, np.float32)

    # 5. perspectiva leve (pantalla vista desde un ángulo)
    if on(0.65):
        d = float(rng.uniform(0.02, 0.1))
        src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
        dst = src + rng.uniform(-d, d, (4, 2)).astype(np.float32) * np.float32([W, H])
        M = cv2.getPerspectiveTransform(src, dst)
        fill = float(rng.uniform(5, 35))
        a = cv2.warpPerspective(a, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(fill, fill, fill))
        par["persp"] = d
    # 6. viñeteo
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    if on(0.45):
        v = float(rng.uniform(0.15, 0.55))
        r2 = ((xx - W / 2) ** 2 + (yy - H / 2) ** 2) / ((W / 2) ** 2 + (H / 2) ** 2)
        a = a * (1 - v * r2)[..., None]
        par["vineta"] = v
    # 7. reflejos: discos brillantes de luminarias (varios) y/o velo difuso/franja de ventana
    if on(0.6):
        n = int(rng.integers(1, 5))
        for _ in range(n):
            cx, cy, r = rng.uniform(0.05, 0.95) * W, rng.uniform(0.05, 0.95) * H, rng.uniform(0.008, 0.028) * W
            al = float(rng.uniform(0.7, 1.0))
            mk = _disc_mask(H, W, cx, cy, r, 2.5)[..., None]
            tono = np.array([255, 255, 255]) if rng.random() < 0.7 else np.array([235, 250, 255])
            a = a * (1 - al * mk) + tono * al * mk
        par["discos"] = n
    if on(0.4):
        cx, cy = rng.uniform(0.1, 0.9) * W, rng.uniform(0.1, 0.9) * H
        al = float(rng.uniform(0.1, 0.4))
        th = rng.uniform(0, math.pi)
        dd = (xx - cx) * math.cos(th) + (yy - cy) * math.sin(th)
        blob = np.exp(-((dd / (rng.uniform(0.08, 0.3) * W)) ** 2))
        if rng.random() < 0.5:
            blob = np.maximum(blob, np.exp(-(((xx - cx) / (0.3 * W)) ** 2 + ((yy - cy) / (0.2 * H)) ** 2)))
        a = a * (1 - al * blob)[..., None] + 255.0 * al * blob[..., None] * np.array([0.93, 0.98, 1.0])
        par["velo"] = al
    # 8. moiré (batido de dos rejillas, la rejilla de píxeles de la pantalla vs el sensor)
    if on(0.3):
        amp = float(rng.uniform(0.02, 0.08))
        per = float(rng.uniform(5, 22)) * W / 1024
        th = float(rng.uniform(0, math.pi))
        dth, dper = float(rng.uniform(0.02, 0.12)), float(rng.uniform(0.02, 0.1))
        g1 = np.cos(2 * math.pi * (xx * math.cos(th) + yy * math.sin(th)) / per)
        g2 = np.cos(2 * math.pi * (xx * math.cos(th + dth) + yy * math.sin(th + dth)) / (per * (1 + dper)))
        a = a * (1 + amp * g1 * g2)[..., None]
        par["moire"] = amp
    # 9. baja resolución efectiva, desenfoque (enfoque/movimiento), ruido
    im = _img(a)
    if on(0.4):
        f = float(rng.uniform(0.35, 0.8))
        im = im.resize((max(8, int(W * f)), max(8, int(H * f))), Image.Resampling.BILINEAR).resize((W, H), Image.Resampling.BILINEAR)
        par["baja_res"] = f
    if on(0.6):
        rad = float(rng.uniform(0.7, 3.2))
        im = im.filter(ImageFilter.GaussianBlur(radius=rad))
        par["blur"] = rad
    if on(0.15):
        L = int(rng.integers(5, 13)) | 1
        k = np.zeros((L, L), np.float32)
        ang = rng.uniform(0, math.pi)
        c0 = (L - 1) / 2
        for t in np.linspace(-c0, c0, L * 2):
            xk, yk = int(round(c0 + t * math.cos(ang))), int(round(c0 + t * math.sin(ang)))
            if 0 <= xk < L and 0 <= yk < L:
                k[yk, xk] = 1
        im = _img(cv2.filter2D(np.asarray(im, np.float32), -1, k / k.sum()))
        par["movimiento"] = L
    a = np.asarray(im, np.float32)
    if on(0.65):
        sg = float(rng.uniform(2, 11))
        a = a + rng.normal(0, sg, a.shape).astype(np.float32)
        par["ruido"] = sg
    im = _img(a)
    # 10. JPEG de la cámara/transmisión
    if on(0.8):
        q = int(rng.integers(30, 86))
        b = BytesIO()
        im.save(b, format="JPEG", quality=q)
        b.seek(0)
        im = Image.open(b).convert("RGB")
        par["jpeg"] = q
    return im, par
