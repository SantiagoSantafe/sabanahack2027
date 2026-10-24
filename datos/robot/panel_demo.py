"""Panel de la demo: cámara del D1 en vivo + clasificación + visor de hojas para las pantallas.

Uso (desde datos/):
    .venv/bin/python -I robot/panel_demo.py --robot-ip 10.90.251.84 --port 8092
Abre http://localhost:8092  ·  Visor de hojas para otra pantalla: http://<IP_del_Mac>:8092/hoja
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np
from PIL import Image

DATOS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATOS / "pipeline"))
from predict import crop_frame, decide_one, load_classifier, run_one  # noqa: E402
from PIL import ImageFilter  # noqa: E402
sys.path.insert(0, str(DATOS / "robot"))
from filtro_hoja import FiltroHoja  # noqa: E402

MODELO = DATOS / "resultados/ml/modelo_final"
TEST_CSV = DATOS / "resultados/ml/drberry_image/splits/test_relativo.csv"
NOMBRES = {"sin_hoja": "Sin hoja a la vista", "alternaria": "Alternaria", "heliothis": "Heliothis (daño de oruga)", "oidio": "Oídio", "sana": "Sana"}


class Estado:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.frame: np.ndarray | None = None
        self.frame_t = 0.0
        self.pred: dict | None = None
        self.roi = [0.2, 0.2, 0.6, 0.6]  # x, y, w, h en fracciones
        self.cam_ok = False
        self.fps = 0.0
        self.pausa = False
        self.zoom = 1.0
        self.multiescala = False
        self.auto = True
        self.color = True
        self.auto_box = None  # (x, y, w, h) en fracciones del cuadro
        self.ventana: list = []
        self.n_ventana = 8
        self.crudo: dict | None = None
        self.vista = "normal"  # vista por defecto del MJPEG (solo visualización)


E = Estado()


def hilo_camara(url: str) -> None:
    while True:
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        n, t0 = 0, time.time()
        while cap.isOpened():
            ok, f = cap.read()
            if not ok:
                break
            n += 1
            with E.lock:
                E.frame, E.frame_t, E.cam_ok = f, time.time(), True
                if time.time() - t0 > 2:
                    E.fps, n, t0 = n / (time.time() - t0), 0, time.time()
        with E.lock:
            E.cam_ok = False
        cap.release()
        time.sleep(1.5)


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


def zoom_modelo(crop: Image.Image, z: float) -> Image.Image:
    """Zoom para el modelo: centro de la zona (1/z), ampliado con Lanczos y con realce de nitidez."""
    if z <= 1.01:
        return crop
    W, H = crop.size
    cw, ch = W / z, H / z
    c = crop.crop((int((W - cw) / 2), int((H - ch) / 2), int((W + cw) / 2), int((H + ch) / 2)))
    c = c.resize((W, H), Image.LANCZOS)
    return c.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2))


def clasificar(clf, filtro, umbral: float, im: Image.Image, roi=None, z: float = 1.0, multi: bool = False, auto: bool = False) -> dict:
    t0 = time.perf_counter()
    im = im.convert("RGB")
    crop = crop_frame(im, roi)
    with E.lock:
        usar_color = E.color
    if usar_color:
        crop = corregir_color(crop)
    caja = None
    if auto:
        b = recorte_por_color(crop)
        if b is not None:
            bx, by, bw, bh = b
            crop = crop.crop((bx, by, bx + bw, by + bh))
            if roi:
                W, H = im.size
                rx, ry, rw, rh = roi
                caja = (rx + bx / W, ry + by / H, bw / W, bh / H)
            else:
                W, H = im.size
                caja = (bx / W, by / H, bw / W, bh / H)
    with E.lock:
        E.auto_box = caja
    escalas = sorted({1.0, 1.5, 2.0, round(z, 2)}) if multi else [z]
    vistas = [zoom_modelo(crop, s) for s in escalas]
    ph = float(filtro.p_hoja([vistas[0]])[0])
    if ph < filtro.umbral:
        return {"clase": "sin_hoja", "confianza": round(1 - ph, 4), "sospecha": False, "p_hoja": round(ph, 4),
                "umbral_hoja": filtro.umbral, "probabilidades": {}, "p_enfermedad": 0.0, "umbral": umbral,
                "latencia_ms": {"total": round((time.perf_counter() - t0) * 1000, 1)}}
    probs = np.asarray(clf.predict_proba(vistas)).mean(axis=0)
    r = decide_one(probs, clf.classes, "sana", umbral)
    r.update({"p_hoja": round(ph, 4), "umbral_hoja": filtro.umbral, "modelo": clf.name, "escalas": escalas,
              "latencia_ms": {"total": round((time.perf_counter() - t0) * 1000, 1)}})
    return r


def suavizar(ventana: list, umbral: float) -> dict:
    """Decisión estable: promedia las probabilidades de los últimos N cuadros con hoja."""
    con_hoja = [r for r in ventana if r.get("clase") not in (None, "sin_hoja") and r.get("probabilidades")]
    if len(con_hoja) * 2 < len(ventana) or not con_hoja:
        r = dict(ventana[-1]) if ventana else {}
        r.update({"clase": "sin_hoja", "sospecha": False, "estable": True, "n": len(ventana)})
        return r
    clases = list(con_hoja[0]["probabilidades"].keys())
    P = np.array([[r["probabilidades"][c] for c in clases] for r in con_hoja]).mean(axis=0)
    hi = clases.index("sana")
    score = float(1 - P[hi])
    sospecha = score >= umbral
    masked = P.copy(); masked[hi] = -1
    cls = int(masked.argmax()) if sospecha else hi
    votos = sum(1 for r in con_hoja if r["clase"] == clases[cls])
    acuerdo = votos / len(con_hoja)
    estable = len(con_hoja) >= 4 and acuerdo >= 0.6
    ult = con_hoja[-1]
    return {"clase": clases[cls], "confianza": round(float(P[cls]), 4), "p_enfermedad": round(score, 4),
            "sospecha": bool(sospecha and estable), "sospecha_bruta": bool(sospecha), "umbral": umbral,
            "probabilidades": {c: round(float(v), 4) for c, v in zip(clases, P)}, "estable": estable,
            "acuerdo": round(acuerdo, 2), "n": len(con_hoja), "p_hoja": ult.get("p_hoja"), "umbral_hoja": ult.get("umbral_hoja"),
            "latencia_ms": ult.get("latencia_ms", {}), "modelo": ult.get("modelo")}


def hilo_inferencia(clf, filtro, umbral: float, intervalo: float) -> None:
    while True:
        time.sleep(intervalo)
        with E.lock:
            f = None if (E.frame is None or E.pausa) else E.frame.copy()
            roi = tuple(E.roi)
            z, multi, auto = E.zoom, E.multiescala, E.auto
        if f is None:
            continue
        im = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        try:
            r = clasificar(clf, filtro, umbral, im, roi, z, multi, auto)
        except Exception as e:  # noqa: BLE001
            r = {"error": str(e)}
        with E.lock:
            E.crudo = r
            E.ventana = (E.ventana + [r])[-E.n_ventana:]
            E.pred = suavizar(E.ventana, umbral)


def dibujar(f: np.ndarray, esc: float = 1.0) -> np.ndarray:
    """Recuadro de zona, recorte de hoja y etiqueta de clase. `esc` ajusta grosores/letras al ancho de la imagen."""
    H, W = f.shape[:2]
    g = lambda v: max(1, int(round(v * esc)))  # noqa: E731
    with E.lock:
        x, y, w, h = E.roi
        p = E.pred
    color = (80, 200, 80)
    if p and p.get("clase") == "sin_hoja":
        color = (150, 150, 150)
    if p and p.get("sospecha"):
        color = (40, 40, 230)
    cv2.rectangle(f, (int(x * W), int(y * H)), (int((x + w) * W), int((y + h) * H)), color, g(4))
    with E.lock:
        z = E.zoom
        caja = E.auto_box if E.auto else None
    if caja:
        cx, cy, cw, ch = caja
        cv2.rectangle(f, (int(cx * W), int(cy * H)), (int((cx + cw) * W), int((cy + ch) * H)), (255, 255, 0), g(3))
        cv2.putText(f, "hoja", (int(cx * W) + g(6), int((cy + ch) * H) - g(10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9 * esc, (255, 255, 0), g(2))
    if z > 1.01 and not caja:  # zona que realmente entra al modelo con el zoom
        iw, ih = w / z, h / z
        ix, iy = x + (w - iw) / 2, y + (h - ih) / 2
        cv2.rectangle(f, (int(ix * W), int(iy * H)), (int((ix + iw) * W), int((iy + ih) * H)), (255, 200, 0), g(2))
    if p and "clase" in p:
        txt = (f"Sin hoja ({p.get('p_hoja', 0)*100:.0f}% hoja)" if p["clase"] == "sin_hoja" else f"{NOMBRES.get(p['clase'], p['clase'])}  {p['confianza']*100:.0f}%" + ("  ALERTA" if p["sospecha"] else ("  (estabilizando)" if not p.get("estable", True) else ""))).replace("í", "i").replace("Í", "I")
        cv2.rectangle(f, (int(x * W), max(0, int(y * H) - g(60))), (int(x * W) + int(22 * esc * len(txt)), int(y * H)), color, -1)
        cv2.putText(f, txt, (int(x * W) + g(10), int(y * H) - g(18)), cv2.FONT_HERSHEY_SIMPLEX, 1.2 * esc, (255, 255, 255), g(3))
    return f


# ---- Filtros de sensor: SOLO visualización (la clasificación usa siempre el RGB normal) ------------------
VISTAS = ("normal", "termica", "ndvi", "sensores", "comparar")
ANCHO_SALIDA = 960
ANCHO_FILTRO = 480  # los filtros se calculan a esta resolución y se amplían (rinde >=10 fps)
TXT_TERMICA = "SIMULADA — en producción: cámara térmica (p. ej. MLX90640/Lepton)"
TXT_NDVI = "SIMULADO — aproximación desde RGB (ExG); en producción: cámara multiespectral/NIR"
_B, _A = 243.12, 17.62  # constantes de Magnus


def punto_rocio(t: float, hr: float) -> float:
    g = np.log(max(hr, 1.0) / 100.0) + _A * t / (_B + t)
    return float(_B * g / (_A - g))


class Sensores:
    """Lecturas ambientales y del robot. Con --sim-url vienen de sim-core; si no, valores por defecto."""

    def __init__(self, t: float = 18.0, hr: float = 75.0) -> None:
        self.lock = threading.Lock()
        self.t, self.hr = t, hr
        self.bat: float | None = None
        self.riesgo: str | None = None
        self.mojada_sim: float | None = None
        self.fuente = "defecto"
        self.mojada_s = 0.0

    def snap(self) -> dict:
        with self.lock:
            d = {"t": self.t, "hr": self.hr, "bat": self.bat, "riesgo": self.riesgo, "fuente": self.fuente}
            d["td"] = punto_rocio(self.t, self.hr)
            d["horas_mojada"] = self.mojada_sim if self.mojada_sim is not None else self.mojada_s / 3600
            d["mojada_real"] = self.mojada_sim is not None
        return d


SENS = Sensores()


def _buscar(obj, claves, tipos=(int, float)):
    """Primer valor del tipo pedido cuyo nombre de clave esté en `claves` (por prioridad), buscando en anidados."""
    for clave in claves:
        pila = [obj]
        while pila:
            o = pila.pop(0)
            if isinstance(o, dict):
                for k, v in o.items():
                    if str(k).lower() == clave and isinstance(v, tipos) and not isinstance(v, bool):
                        return v
                pila.extend(v for v in o.values() if isinstance(v, (dict, list)))
            elif isinstance(o, list):
                pila.extend(v for v in o[:50] if isinstance(v, (dict, list)))
    return None


def _riesgo_texto(obj) -> str | None:
    v = _buscar(obj, ["riesgo", "nivel_riesgo", "risk", "risk_level"], (str, int, float, dict))
    if isinstance(v, dict):
        v = _buscar(v, ["nivel", "level", "texto", "max", "score", "valor"], (str, int, float))
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return f"{v * 100:.0f} %" if 0 <= v <= 1 else f"{v:.0f}"
    camas = _buscar(obj, ["camas"], (list,))
    if camas:
        vals = [c.get("riesgo", c.get("score")) for c in camas if isinstance(c, dict)]
        vals = [x for x in vals if isinstance(x, (int, float))]
        if vals:
            return f"{max(vals) * 100:.0f} %" if max(vals) <= 1 else f"{max(vals):.0f}"
    return None


def _get_json(base: str, ruta: str):
    import urllib.request
    try:
        with urllib.request.urlopen(base.rstrip("/") + ruta, timeout=1.0) as r:
            return json.loads(r.read())
    except Exception:  # noqa: BLE001 - sim-core apagado no debe afectar al panel
        return None


def hilo_sensores(base: str | None) -> None:
    """Cada ~1 s: lee sim-core (si hay) y acumula las horas de hoja mojada estimadas (T - rocío <= 1,5 °C)."""
    ultimo, t_lect = time.time(), 0.0
    while True:
        time.sleep(0.5)
        ahora = time.time()
        if base and ahora - t_lect >= 2.0:
            t_lect = ahora
            docs = [d for d in (_get_json(base, "/api/robot"), _get_json(base, "/api/dashboard/resumen"),
                                _get_json(base, "/api/dashboard/riesgo")) if d is not None]
            with SENS.lock:
                if not docs:
                    SENS.fuente = "defecto"
                else:
                    SENS.fuente = "sim-core"
                    def pide(claves):
                        for d in docs:
                            v = _buscar(d, claves)
                            if v is not None:
                                return float(v)
                        return None
                    t = pide(["temperatura_actual", "temperatura", "temp", "temperature", "t_aire", "air_temp", "temperatura_promedio"])
                    hr = pide(["humedad_actual", "humedad", "hr", "rh", "humidity", "humedad_promedio"])
                    bat = pide(["bateria", "battery", "battery_pct", "bateria_pct", "soc"])
                    if t is not None:
                        SENS.t = t
                    if hr is not None:
                        SENS.hr = hr * 100 if hr <= 1.0 else hr
                    SENS.bat = None if bat is None else (bat * 100 if bat <= 1.0 else bat)
                    SENS.mojada_sim = pide(["horas_hoja_mojada", "hoja_mojada_h", "leaf_wetness_hours"])
                    SENS.riesgo = next((r for r in (_riesgo_texto(d) for d in docs) if r), None)
        with SENS.lock:
            if SENS.t - punto_rocio(SENS.t, SENS.hr) <= 1.5:
                SENS.mojada_s += ahora - ultimo
        ultimo = ahora


# fuentes con tildes/°/— ; si no hay ninguna se cae a cv2 sin acentos
_FUENTES = ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
_FUENTE_OK = next((p for p in _FUENTES if Path(p).exists()), None)
_cache_fuentes: dict = {}


def _fuente(px: int):
    from PIL import ImageFont
    px = max(8, int(px))
    if px not in _cache_fuentes:
        _cache_fuentes[px] = ImageFont.truetype(_FUENTE_OK, px)
    return _cache_fuentes[px]


def rotular(img: np.ndarray, items: list) -> np.ndarray:
    """items: (texto, x, y, px, color BGR, fondo BGR|None). Un único paso con PIL para todo el texto."""
    if not items:
        return img
    if _FUENTE_OK is None:
        import unicodedata
        for t, x, y, px, col, bg in items:
            t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
            cv2.putText(img, t, (int(x), int(y + px)), cv2.FONT_HERSHEY_SIMPLEX, px / 28, col, 1 + (px > 30))
        return img
    from PIL import ImageDraw
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(pil)
    for t, x, y, px, col, bg in items:
        f = _fuente(px)
        if bg is not None:
            x0, y0, x1, y1 = d.textbbox((x, y), t, font=f)
            d.rectangle((x0 - 6, y0 - 4, x1 + 6, y1 + 4), fill=bg[::-1])
        d.text((x, y), t, font=f, fill=col[::-1])
    return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)


def _fmt(v: float | None, d: int = 1) -> str:
    return "—" if v is None else f"{v:.{d}f}".replace(".", ",")


# iconos mínimos con primitivas de cv2 (s = tamaño en px)
def icono(img, tipo: str, x: int, y: int, s: int, col, frac: float = 1.0) -> None:
    c = (x + s // 2, y + s // 2)
    if tipo == "termometro":
        cv2.rectangle(img, (x + s * 2 // 5, y), (x + s * 3 // 5, y + s * 3 // 4), col, 2)
        cv2.circle(img, (c[0], y + s * 4 // 5), s // 5, col, -1)
    elif tipo in ("gota", "rocio"):
        punta = np.array([(c[0], y), (c[0] - s // 3, y + s * 2 // 3), (c[0] + s // 3, y + s * 2 // 3)])
        cv2.circle(img, (c[0], y + s * 2 // 3), s // 3, col, -1 if tipo == "gota" else 2)
        if tipo == "gota":
            cv2.fillPoly(img, [punta], col)
        else:
            cv2.polylines(img, [punta[[1, 0, 2]]], False, col, 2)
            cv2.line(img, (x, y + s - 1), (x + s, y + s - 1), col, 2)  # línea de "rocío" bajo la gota
    elif tipo == "reloj":
        cv2.circle(img, c, s // 2 - 1, col, 2)
        cv2.line(img, c, (c[0], y + 4), col, 2)
        cv2.line(img, c, (c[0] + s // 4, c[1]), col, 2)
    elif tipo == "alerta":
        cv2.polylines(img, [np.array([(c[0], y), (x, y + s), (x + s, y + s)])], True, col, 2)
        cv2.line(img, (c[0], y + s // 3), (c[0], y + s * 2 // 3), col, 2)
        cv2.circle(img, (c[0], y + s * 5 // 6), 1, col, -1)
    elif tipo == "bateria":
        cv2.rectangle(img, (x, y + s // 4), (x + s - 4, y + s * 3 // 4), col, 2)
        cv2.rectangle(img, (x + s - 4, y + s * 2 // 5), (x + s, y + s * 3 // 5), col, -1)
        cv2.rectangle(img, (x + 3, y + s // 4 + 3), (x + 3 + int((s - 10) * max(0, min(1, frac))), y + s * 3 // 4 - 3), col, -1)
    elif tipo == "robot":
        cv2.rectangle(img, (x + 2, y + s // 4), (x + s - 2, y + s - 2), col, 2)
        cv2.circle(img, (x + s // 3, y + s * 5 // 8), 2, col, -1)
        cv2.circle(img, (x + s * 2 // 3, y + s * 5 // 8), 2, col, -1)
        cv2.line(img, (c[0], y + s // 4), (c[0], y), col, 2)


def _indices(s: np.ndarray):
    f = s.astype(np.float32) / 255.0
    b, g, r = f[..., 0], f[..., 1], f[..., 2]
    exg = (2 * g - r - b) / (r + g + b + 1e-3)  # exceso de verde normalizado, ~[-1, 1]
    lum = 0.114 * b + 0.587 * g + 0.299 * r
    return exg, lum


def efecto_termico(s: np.ndarray, snap: dict):
    """Pseudo-térmica: T = T_aire + delta. delta<0 con más verde y con alta HR en zonas de follaje denso; luminancia da el fondo."""
    exg, lum = _indices(s)
    veg = np.clip((exg - 0.02) / 0.25, 0, 1)
    vegb = cv2.GaussianBlur(veg, (0, 0), max(s.shape[1] / 40, 3))
    hrf = float(np.clip((snap["hr"] - 60) / 40, 0, 1))
    d = np.clip(1.6 * (lum - 0.5) - 1.5 * veg - 1.2 * hrf * vegb, -4, 4)
    d = cv2.GaussianBlur(d, (0, 0), 1.2)
    img = cv2.applyColorMap(((d + 4) / 8 * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    mojada = (snap["t"] + d) <= snap["td"]  # bajo el punto de rocío: posible condensación
    img[mojada] = (0.4 * img[mojada] + 0.6 * np.array([255, 255, 0])).astype(np.uint8)
    return img, float(mojada.mean())


_LUT_VEG = None


def efecto_ndvi(s: np.ndarray):
    global _LUT_VEG
    if _LUT_VEG is None:  # rojo -> amarillo -> verde (BGR)
        xs = [0, 128, 255]
        cols = np.array([(40, 40, 215), (40, 215, 240), (60, 160, 30)], np.float32)
        _LUT_VEG = np.stack([np.interp(np.arange(256), xs, cols[:, k]) for k in range(3)], 1).astype(np.uint8)
    exg, _ = _indices(s)
    idx = (np.clip((exg + 0.05) / 0.55, 0, 1) * 255).astype(np.uint8)
    return _LUT_VEG[idx].reshape(s.shape), _LUT_VEG


def _barra(img, lut, x, y, w, h, marcas: list, escala: float):
    """Barra de color vertical (arriba = valor alto). lut: 256x3 BGR o None para INFERNO."""
    g = np.linspace(255, 0, h).astype(np.uint8).reshape(h, 1)
    if lut is None:
        col = cv2.applyColorMap(np.repeat(g, w, 1), cv2.COLORMAP_INFERNO)
    else:
        col = lut[np.repeat(g, w, 1)]
    img[y:y + h, x:x + w] = col
    cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 255), 1)
    out = []
    px = max(11, int(15 * escala))
    for frac, txt in marcas:
        yy = int(y + (1 - frac) * h)
        cv2.line(img, (x - 4, yy), (x + w, yy), (255, 255, 255), 1)
        out.append((txt, x - 6 - px * len(txt) * 0.55, yy - px // 2, px, (255, 255, 255), (0, 0, 0)))
    return out


def decorar(img: np.ndarray, vista: str, snap: dict, compacto: bool, extra) -> np.ndarray:
    H, W = img.shape[:2]
    k = W / ANCHO_SALIDA
    txt: list = []
    if vista == "termica":
        if compacto:
            txt.append(("Térmica — SIMULADA", 8, 6, 14, (255, 255, 255), (0, 0, 0)))
        else:
            txt.append((TXT_TERMICA, 12, 10, 21, (255, 255, 255), (0, 0, 160)))
        bw, bh = max(10, int(22 * k)), int(H * (0.5 if compacto else 0.62))
        bx, by = W - bw - (36 if compacto else 70), (H - bh) // 2 + (10 if compacto else 20)
        t = snap["t"]
        marcas = [(i / 4, f"{_fmt(t - 4 + 2 * i, 0 if compacto else 1)} °C") for i in range(5)]
        txt += _barra(img, None, bx, by, bw, bh, marcas, k)
        txt.append((f"cian: posible hoja mojada {extra * 100:.0f} %" if compacto else f"cian = posible hoja mojada (bajo el punto de rocío): {extra * 100:.0f} % del cuadro",
                    8, H - (24 if compacto else 36), 12 if compacto else 17, (255, 255, 0), (0, 0, 0)))
        if not compacto:
            fu = "sim-core" if snap["fuente"] == "sim-core" else "valor por defecto"
            txt.append((f"escala: {_fmt(t - 4)} a {_fmt(t + 4)} °C (±4 °C en torno al aire: {_fmt(t)} °C, {fu}; rocío {_fmt(snap['td'])} °C)",
                        12, H - 68, 15, (230, 230, 230), (0, 0, 0)))
    elif vista == "ndvi":
        if compacto:
            txt.append(("NDVI — SIMULADO", 8, 6, 14, (255, 255, 255), (0, 0, 0)))
        else:
            txt.append((TXT_NDVI, 12, 10, 21, (255, 255, 255), (0, 0, 160)))
        bw, bh = max(10, int(22 * k)), int(H * (0.5 if compacto else 0.62))
        bx, by = W - bw - (30 if compacto else 120), (H - bh) // 2 + (10 if compacto else 20)
        marcas = [(1.0, "1,0 vegetación densa"), (0.5, "0,5"), (0.0, "0,0 suelo/sin verde")] if not compacto else [(1.0, "alto"), (0.0, "bajo")]
        txt += _barra(img, extra, bx, by, bw, bh, marcas, k)
    elif vista == "sensores":
        txt += _panel_sensores(img, snap, compacto, extra)
    if compacto and vista == "normal":
        txt.append(("Normal (RGB)", 8, 6, 14, (255, 255, 255), (0, 0, 0)))
    return rotular(img, txt)


def _panel_sensores(img, snap: dict, compacto: bool, robot: dict) -> list:
    H, W = img.shape[:2]
    txt: list = []
    if compacto:
        ov = img.copy()
        cv2.rectangle(ov, (0, H - 64), (W, H), (20, 20, 20), -1)
        cv2.addWeighted(ov, 0.75, img, 0.25, 0, img)
        l1 = f"Sensores · aire {_fmt(snap['t'])} °C · HR {_fmt(snap['hr'], 0)} %"
        l2 = f"rocío {_fmt(snap['td'])} °C · hoja mojada {_fmt(snap['horas_mojada'], 2)} h"
        l3 = f"riesgo {snap['riesgo'] or '—'} · batería {_fmt(snap['bat'], 0) + ' %' if snap['bat'] is not None else '—'} · {robot['txt']}"
        for i, l in enumerate((l1, l2, l3)):
            txt.append((l, 8, H - 62 + i * 20, 14, (255, 255, 255), None))
        return txt
    pw, fila = 330, 56
    filas = [("termometro", "Temperatura del aire", f"{_fmt(snap['t'])} °C", (120, 170, 255)),
             ("gota", "Humedad relativa", f"{_fmt(snap['hr'], 0)} %", (255, 190, 90)),
             ("rocio", "Punto de rocío (Magnus)", f"{_fmt(snap['td'])} °C", (255, 230, 90)),
             ("reloj", "Hoja mojada (estimada)" + ("" if snap["mojada_real"] else " *"), f"{_fmt(snap['horas_mojada'], 2)} h", (200, 200, 255)),
             ("alerta", "Riesgo de hongos", snap["riesgo"] or "—", (80, 200, 255)),
             ("bateria", "Batería del robot", f"{_fmt(snap['bat'], 0)} %" if snap["bat"] is not None else "—", (110, 230, 130)),
             ("robot", "Estado del robot", robot["txt"], (200, 200, 200))]
    ph = 66 + fila * len(filas)
    ov = img.copy()
    cv2.rectangle(ov, (10, 10), (10 + pw, 10 + ph), (20, 20, 20), -1)
    cv2.addWeighted(ov, 0.78, img, 0.22, 0, img)
    fuente = "sim-core (datos simulados)" if snap["fuente"] == "sim-core" else "valores por defecto (sin sim-core)"
    txt.append(("SENSORES · " + fuente, 22, 18, 15, (255, 255, 255), None))
    for i, (ic, lab, val, col) in enumerate(filas):
        y = 52 + i * fila
        icono(img, ic, 24, y + 10, 26, col, (snap["bat"] or 0) / 100)
        txt.append((lab, 64, y + 2, 14, (190, 190, 190), None))
        txt.append((val, 64, y + 20, 25, (255, 255, 255), None))
    txt.append(("* integrado en vivo: horas con T − rocío ≤ 1,5 °C desde que inició el panel", 22, 10 + ph - 22, 11, (160, 160, 160), None))
    return txt


def estado_robot() -> dict:
    with E.lock:
        ok = E.cam_ok and (time.time() - E.frame_t) < 2.0
        t = f"cámara {'OK' if ok else 'sin señal'} · {E.fps:.0f} fps" + (" · pausa" if E.pausa else "")
    return {"txt": t}


def componer(f: np.ndarray, vista: str, ancho: int, snap: dict, robot: dict, small: np.ndarray | None = None) -> np.ndarray:
    """Un cuadro de la vista pedida, de `ancho` px. Filtros a ANCHO_FILTRO y luego ampliados."""
    H0, W0 = f.shape[:2]
    alto = int(round(ancho * H0 / W0))
    if small is None:
        small = cv2.resize(f, (ANCHO_FILTRO, int(round(ANCHO_FILTRO * H0 / W0))), interpolation=cv2.INTER_AREA)
    extra = None
    if vista == "termica":
        base, extra = efecto_termico(small, snap)
    elif vista == "ndvi":
        base, extra = efecto_ndvi(small)
    else:
        base = small if vista == "normal" or ancho <= ANCHO_FILTRO else None
    if base is None:  # normal / sensores a resolución completa de salida
        base = cv2.resize(f, (ancho, alto), interpolation=cv2.INTER_AREA)
        if vista == "sensores":
            extra = robot
    elif vista == "sensores":
        extra = robot
    if base.shape[1] != ancho:
        base = cv2.resize(base, (ancho, alto), interpolation=cv2.INTER_LINEAR)
    else:
        base = base.copy()
    compacto = ancho < 700
    out = decorar(base, vista, snap, compacto, extra if vista != "sensores" else robot)
    return dibujar(out, ancho / W0)


def componer_vista(f: np.ndarray, vista: str) -> np.ndarray:
    snap, robot = SENS.snap(), estado_robot()
    if vista != "comparar":
        return componer(f, vista, ANCHO_SALIDA, snap, robot)
    H0, W0 = f.shape[:2]
    small = cv2.resize(f, (ANCHO_FILTRO, int(round(ANCHO_FILTRO * H0 / W0))), interpolation=cv2.INTER_AREA)
    t = [componer(f, v, ANCHO_FILTRO, snap, robot, small) for v in ("normal", "termica", "ndvi", "sensores")]
    return np.vstack([np.hstack(t[:2]), np.hstack(t[2:])])


def hilo_video(origen: str, fps: float = 10.0, seg_por_imagen: float = 3.0) -> None:
    """Pruebas sin robot: reproduce un video, una imagen o una carpeta de imágenes en bucle como si fuera la cámara."""
    p = Path(origen)
    imgs = sorted(q for q in p.iterdir() if q.suffix.lower() in (".jpg", ".jpeg", ".png"))[:24] if p.is_dir() else (
        [p] if p.suffix.lower() in (".jpg", ".jpeg", ".png") else [])
    cuadros = []
    for q in imgs:
        im = cv2.imread(str(q))
        if im is not None:
            cuadros.append(cv2.resize(im, (1280, int(1280 * im.shape[0] / im.shape[1]))))
    n, t0 = 0, time.time()
    while True:
        if cuadros:
            for im in cuadros:
                t_fin = time.time() + seg_por_imagen
                while time.time() < t_fin:
                    with E.lock:
                        E.frame, E.frame_t, E.cam_ok = im, time.time(), True
                    n += 1
                    time.sleep(1 / fps)
                    if time.time() - t0 > 2:
                        with E.lock:
                            E.fps, n, t0 = n / (time.time() - t0), 0, time.time()
                if len(cuadros) == 1:
                    break
        else:
            cap = cv2.VideoCapture(str(p))
            while cap.isOpened():
                ok, im = cap.read()
                if not ok:
                    break
                with E.lock:
                    E.frame, E.frame_t, E.cam_ok, E.fps = im, time.time(), True, fps
                time.sleep(1 / fps)
            cap.release()
            time.sleep(0.2)


def leer_test() -> list[dict]:
    if not TEST_CSV.exists():
        return []
    with open(TEST_CSV, newline="") as fh:
        return [{"path": r["path"], "label": r["label"]} for r in csv.DictReader(fh)]


HOJAS = leer_test()

PANEL = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panel D1 · Berry Good Idea</title><style>
:root{--bg:#0f1115;--card:#181b22;--ink:#e8eaf0;--mute:#9aa3b2;--ok:#3fb950;--bad:#f85149;--acc:#58a6ff}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.4 -apple-system,system-ui,sans-serif}
header{padding:12px 16px;border-bottom:1px solid #262b36;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
h1{font-size:18px;margin:0}.pill{padding:3px 10px;border-radius:99px;background:#262b36;color:var(--mute);font-size:13px}
main{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:16px;padding:16px}
@media(max-width:900px){main{grid-template-columns:1fr}}
.card{background:var(--card);border-radius:12px;padding:14px}
img.cam{width:100%;border-radius:8px;background:#000;display:block}
.big{font-size:28px;font-weight:700}.ok{color:var(--ok)}.bad{color:var(--bad)}
.bar{height:10px;border-radius:6px;background:#262b36;overflow:hidden;margin:4px 0 10px}.bar>i{display:block;height:100%;background:var(--acc)}
label{display:block;color:var(--mute);font-size:13px;margin-top:8px}input[type=range]{width:100%}
button{background:#262b36;color:var(--ink);border:0;border-radius:8px;padding:8px 12px;cursor:pointer;margin:4px 4px 0 0}
button.p{background:var(--acc);color:#081018}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(70px,1fr));gap:6px;max-height:260px;overflow:auto}
.grid img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:6px;cursor:pointer}
.warn{color:#d29922;font-size:13px}
.vistas{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}.vp{border-radius:99px;padding:6px 14px;margin:0;background:#262b36;color:var(--mute)}.vp.on{background:var(--acc);color:#081018;font-weight:600}
</style></head><body>
<header><h1>Panel D1 · cámara + clasificador</h1><span class="pill" id="cam">cámara…</span><span class="pill" id="lat">—</span>
<a class="pill" href="/hoja?robot=1" target="_blank" style="color:var(--acc)">Visor del robot ↗</a><a class="pill" href="/hoja" target="_blank" style="color:var(--mute)">Visor solo vista ↗</a></header>
<main><section class="card"><div class="vistas" id="vistas"></div><img class="cam" src="/stream.mjpg" alt="Video del robot">
<p class="warn" style="margin-bottom:0">Los filtros de sensor son solo visualización: la clasificación siempre usa la imagen RGB normal. Térmica y NDVI son simulados (ver FILTROS_SENSORES.md).</p>
<p class="warn">Dentro del recuadro de color se busca la mancha de color hoja (cian), se recorta y se clasifica. Si no hay hoja en primer plano, dice "Sin hoja" y no alerta.</p></section>
<aside>
<div class="card"><div id="clase" class="big">—</div><div id="estado" class="pill">esperando</div><div id="probs" style="margin-top:10px"></div>
<button id="pausa">Pausar clasificación</button></div>
<div class="card" style="margin-top:16px"><b>Zona a clasificar (ROI)</b>
<label>X <input type="range" id="x" min="0" max="0.9" step="0.01"></label><label>Y <input type="range" id="y" min="0" max="0.9" step="0.01"></label>
<label>Ancho <input type="range" id="w" min="0.1" max="1" step="0.01"></label><label>Alto <input type="range" id="h" min="0.1" max="1" step="0.01"></label>
<label>Zoom del modelo (recuadro amarillo = lo que clasifica; 1×–4×) <input type="range" id="zoom" min="1" max="4" step="0.1" value="1"></label>
<button id="color" class="p">Corrección de color: sí</button>
<button id="auto" class="p">Auto-recorte por color de hoja: sí</button>
<button id="multi">Multiescala: no</button>
<button onclick="setRoi([0.2,0.2,0.6,0.6])">Centro</button><button onclick="setRoi([0,0,1,1])">Todo el cuadro</button></div>
<div class="card" style="margin-top:16px"><b>Hojas del test (68, el modelo nunca las vio)</b>
<div><button class="p" onclick="mostrar(-1)">Mostrar una al azar en el visor</button></div>
<label>Clic en una miniatura para mostrarla en el visor de hojas</label><div class="grid" id="grid"></div></div>
<div class="card" style="margin-top:16px"><b>Capturar dataset con la cámara del robot</b>
<p style="color:var(--mute);font-size:13px">Abre en la pantalla frente al robot <b>/hoja?robot=1</b> (solo ese visor confirma; los demás solo miran), ajusta el recuadro sobre la imagen y pulsa. Pasa las 410 fotos (train, val y test) por la pantalla y guarda lo que ve la cámara. ~9 min.</p>
<button class="p" onclick="fetch('/api/captura',{method:'POST',body:JSON.stringify({})})">Iniciar captura</button>
<button onclick="fetch('/api/captura_detener',{method:'POST'})">Detener captura</button><div id="cap" style="color:var(--mute);margin-top:6px"></div></div>
<div class="card" style="margin-top:16px"><b>Clasificar una foto propia</b><input type="file" id="foto" accept="image/*" style="margin-top:8px">
<div id="res" style="margin-top:8px;color:var(--mute)"></div></div>
</aside></main>
<script>
const N={sin_hoja:"Sin hoja a la vista",alternaria:"Alternaria",heliothis:"Heliothis (daño de oruga)",oidio:"Oídio",sana:"Sana"};
const VISTAS=[["normal","Normal"],["termica","Térmica (simulada)"],["ndvi","Índice de vegetación (simulado NDVI)"],["sensores","Sensores"],["comparar","Comparar"]];
function pintarVistas(v){document.getElementById("vistas").innerHTML=VISTAS.map(([k,n])=>`<button class="vp${k==v?" on":""}" onclick="setVista('${k}')">${n}</button>`).join("")}
async function setVista(k){const r=await (await fetch("/api/vista",{method:"POST",body:JSON.stringify({vista:k})})).json();pintarVistas(r.vista)}
fetch("/api/vista").then(r=>r.json()).then(r=>pintarVistas(r.vista));
let roi=[0.2,0.2,0.6,0.6];
function pintarRoi(){["x","y","w","h"].forEach((k,i)=>document.getElementById(k).value=roi[i])}
function setRoi(r){roi=r;pintarRoi();fetch("/api/roi",{method:"POST",body:JSON.stringify(roi)})}
["x","y","w","h"].forEach((k,i)=>document.getElementById(k).oninput=e=>{roi[i]=+e.target.value;fetch("/api/roi",{method:"POST",body:JSON.stringify(roi)})});
document.getElementById("pausa").onclick=async e=>{const r=await (await fetch("/api/pausa",{method:"POST"})).json();e.target.textContent=r.pausa?"Reanudar clasificación":"Pausar clasificación"};
function probsHtml(p){return Object.entries(p).sort((a,b)=>b[1]-a[1]).map(([c,v])=>`<div>${N[c]||c} · ${(v*100).toFixed(1)}%</div><div class="bar"><i style="width:${v*100}%"></i></div>`).join("")}
async function tick(){try{const s=await (await fetch("/api/estado")).json();
document.getElementById("cam").textContent=s.cam_ok?`cámara en vivo · ${s.fps.toFixed(0)} fps`:"cámara desconectada";
if(s.roi&&!document.activeElement.type){roi=s.roi;pintarRoi()}
const p=s.pred;if(p&&p.clase){const c=document.getElementById("clase");c.textContent=N[p.clase]||p.clase;c.className="big "+(p.sospecha?"bad":(p.clase=="sin_hoja"?"":"ok"));
document.getElementById("estado").textContent=p.clase=="sin_hoja"?`no alerta: p(hoja) ${(p.p_hoja*100).toFixed(0)}% < ${(p.umbral_hoja*100).toFixed(0)}%`:(p.p_hoja!==undefined?`hoja ${(p.p_hoja*100).toFixed(0)}% · `:"")+(!p.estable&&p.clase!="sin_hoja"?`estabilizando (${Math.round((p.acuerdo||0)*100)}% de acuerdo en ${p.n} cuadros) · `:`estable · ${p.n} cuadros · `)+(p.sospecha?`ALERTA · p(enfermedad) ${(p.p_enfermedad*100).toFixed(0)}% ≥ umbral ${(p.umbral*100).toFixed(0)}%`:"sin alerta");
document.getElementById("probs").innerHTML=probsHtml(p.probabilidades);document.getElementById("lat").textContent=`${p.latencia_ms.total.toFixed(0)} ms por cuadro`}}catch(e){}
try{const c=await (await fetch("/api/captura")).json();document.getElementById("cap").textContent=c.activa?`capturando ${c.split}: ${c.hechas}/${c.total} · omitidas ${c.omitidas} (visor sin confirmar)`:(c.error?c.error:(c.hechas?`listo: ${c.hechas} capturas en ${c.carpeta}`:""))}catch(e){}
setTimeout(tick,500)}
async function grid(){const h=await (await fetch("/api/hojas")).json();document.getElementById("grid").innerHTML=h.map((x,i)=>`<img loading="lazy" src="/img/${i}?mini=1" title="#${i+1}" onclick="mostrar(${i})">`).join("")}
function mostrar(i){fetch("/api/mostrar",{method:"POST",body:JSON.stringify({i})})}
document.getElementById("foto").onchange=async e=>{const f=e.target.files[0];if(!f)return;document.getElementById("res").textContent="clasificando…";
const p=await (await fetch("/api/clasificar",{method:"POST",body:f})).json();
document.getElementById("res").innerHTML=p.clase?`<b class="${p.sospecha?"bad":"ok"}">${N[p.clase]||p.clase} ${(p.confianza*100).toFixed(0)}%</b> · ${p.sospecha?"ALERTA":"sin alerta"}`:(p.error||"error")};
document.getElementById("zoom").oninput=e=>fetch("/api/zoom",{method:"POST",body:JSON.stringify({zoom:+e.target.value})});
document.getElementById("color").onclick=async e=>{const r=await (await fetch("/api/color",{method:"POST"})).json();e.target.textContent="Corrección de color: "+(r.color?"sí":"no")};
document.getElementById("auto").onclick=async e=>{const r=await (await fetch("/api/auto",{method:"POST"})).json();e.target.textContent="Auto-recorte por color de hoja: "+(r.auto?"sí":"no")};
document.getElementById("multi").onclick=async e=>{const r=await (await fetch("/api/multiescala",{method:"POST"})).json();e.target.textContent="Multiescala: "+(r.multiescala?"sí (1×, 1,5×, 2×)":"no")};
pintarRoi();grid();tick();
</script></body></html>"""

VISOR = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Visor de hojas</title><style>
html,body{margin:0;height:100%;background:#000;font-family:-apple-system,system-ui,sans-serif}
img{width:100vw;height:calc(100vh - 64px);object-fit:contain;display:block}
#bar{height:64px;display:flex;align-items:center;justify-content:center;gap:28px;color:#ddd;font-size:22px}
.tag{padding:6px 14px;border-radius:10px;font-weight:700}.sana{background:#1f6f3a}.enf{background:#8b1e1e}.gris{background:#333}
#i{position:fixed;right:10px;top:8px;color:#777;font-size:14px;background:#000a;padding:2px 6px;border-radius:4px}</style></head><body>
<img id="hoja" alt="Hoja"><div id="bar"></div><div id="i"></div><script>
const N={sin_hoja:"Sin hoja",alternaria:"Alternaria",heliothis:"Heliothis (oruga)",oidio:"Oídio",sana:"Sana"};
let cur=-2,ver=true;const NS={cache:"no-store"};
const img=document.getElementById("hoja");const ROBOT=new URLSearchParams(location.search).get("robot")=="1";
img.onload=()=>{if(ROBOT)fetch("/api/visor_ok",{method:"POST",cache:"no-store",body:JSON.stringify({i:cur})})};
async function tick(){try{const s=await (await fetch("/api/mostrar",NS)).json();document.getElementById("i").textContent=(ROBOT?"VISOR DEL ROBOT · ":"solo vista · ")+"#"+(s.i+1)+" · "+new Date().toLocaleTimeString();
if(s.i!==cur){cur=s.i;document.getElementById("hoja").src=(s.url||("/img/"+s.i))+(s.url?"&":"?")+"t="+Date.now();}
const e=await (await fetch("/api/estado",NS)).json();const p=e.pred||{};const real=s.label;
let html="";if(s.captura){html=`<span style="color:#666">captura en curso…</span>`}else if(ver){html+=`<span>Real: <span class="tag ${real=="sana"?"sana":"enf"}">${real=="sana"?"SANA":"ENFERMA · "+(N[real]||real)}</span></span>`;
if(p.clase){const ok=p.clase=="sin_hoja"?null:((real=="sana")===(!p.sospecha));
html+=`<span>Robot: <span class="tag ${p.clase=="sin_hoja"?"gris":(p.sospecha?"enf":"sana")}">${p.clase=="sin_hoja"?"no ve hoja":(p.sospecha?"ENFERMA · "+(N[p.clase]||p.clase):"SANA")}</span> ${ok===null?"":(ok?"✅":"❌")}</span>`}}
document.getElementById("bar").innerHTML=html}catch(err){document.getElementById("i").textContent="SIN CONEXIÓN con el Mac";document.getElementById("i").style.color="#f55"}setTimeout(tick,400)}
document.onkeydown=e=>{if(e.key=="ArrowRight")fetch("/api/mostrar",{method:"POST",body:JSON.stringify({i:cur+1})});
if(e.key=="ArrowLeft")fetch("/api/mostrar",{method:"POST",body:JSON.stringify({i:cur-1})});if(e.key==" ")fetch("/api/mostrar",{method:"POST",body:JSON.stringify({i:-1})});
if(e.key=="e")ver=!ver;if(e.key=="f")document.documentElement.requestFullscreen()};tick();</script></body></html>"""

MOSTRAR: dict = {"i": 0}
VISOR_OK = {"i": None, "robot_visto": 0.0}
CAPTURA = {"detener": False, "omitidas": 0, "activa": False, "hechas": 0, "total": 0, "split": None, "carpeta": None}
CAP_DIR = DATOS / "resultados/ml/capturas_pantalla"


def hilo_captura(splits: list, espera: float) -> None:
    """Pasa las imágenes de cada split por el visor, la cámara del D1 las ve y se guarda el recorte de la zona."""
    filas = []
    for sp in splits:
        f = DATOS / f"resultados/ml/drberry_image/splits/{sp}.csv"
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                rel = r["path"].replace(str(DATOS) + "/", "")
                filas.append((sp, rel, r["label"]))
    if time.time() - VISOR_OK["robot_visto"] > 5:
        CAPTURA.update({"activa": False, "error": "No hay visor del robot abierto: abre /hoja?robot=1 en la pantalla frente al robot."})
        return
    CAPTURA.update({"activa": True, "hechas": 0, "total": len(filas), "detener": False, "omitidas": 0, "error": None})
    CAP_DIR.mkdir(parents=True, exist_ok=True)
    man = open(CAP_DIR / "manifest.csv", "a", newline="")
    w = csv.writer(man)
    if man.tell() == 0:
        w.writerow(["split", "label", "origen", "captura_roi", "captura_completa", "roi", "timestamp"])
    try:
        for k, (sp, rel, lab) in enumerate(filas):
            CAPTURA["split"] = sp
            if CAPTURA.get("detener"):
                break
            VISOR_OK["i"] = None
            MOSTRAR.update({"i": 10000 + k, "url": "/imgp?p=" + rel, "label": lab})
            t0 = time.time()
            while VISOR_OK["i"] != 10000 + k and time.time() - t0 < 6:
                time.sleep(0.05)
            if VISOR_OK["i"] != 10000 + k:
                CAPTURA["omitidas"] += 1  # el visor no confirmó: no se guarda (evita etiqueta equivocada)
                continue
            time.sleep(max(1.5, espera))  # retraso de la cámara RTSP (medido ~1 s)
            with E.lock:
                fr = None if E.frame is None else E.frame.copy()
                roi = tuple(E.roi)
            if fr is None:
                continue
            nombre = Path(rel).stem[:60] + f"_{k}"
            d = CAP_DIR / sp / lab
            d.mkdir(parents=True, exist_ok=True)
            full = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
            crop = crop_frame(full, roi)
            crop.save(d / f"{nombre}.jpg", quality=92)
            (CAP_DIR / "completas").mkdir(exist_ok=True)
            full.resize((960, 540)).save(CAP_DIR / "completas" / f"{sp}_{nombre}.jpg", quality=85)
            w.writerow([sp, lab, rel, str((d / f"{nombre}.jpg").relative_to(DATOS)), f"resultados/ml/capturas_pantalla/completas/{sp}_{nombre}.jpg", ",".join(f"{v:.3f}" for v in roi), time.strftime("%Y-%m-%dT%H:%M:%S")])
            man.flush()
            CAPTURA["hechas"] = k + 1
    finally:
        man.close()
        MOSTRAR.pop("url", None); MOSTRAR.pop("label", None); MOSTRAR["i"] = 0
        CAPTURA.update({"activa": False, "carpeta": str(CAP_DIR)})


# ---- Envío al simulador 3D (opcional: solo con --sim-url; por defecto APAGADO) -------------------------
def _post_sim(base: str, ruta: str, obj: dict) -> bool:
    import urllib.request
    req = urllib.request.Request(base.rstrip("/") + ruta, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=1.0) as r:
            r.read()
        return True
    except Exception:  # noqa: BLE001 - el simulador apagado nunca debe afectar al panel
        return False


def etiqueta_visor() -> str | None:
    """Etiqueta real de la hoja en el visor, solo si el robot está mirando el visor (/hoja?robot=1)."""
    if time.time() - VISOR_OK["robot_visto"] > 10:
        return None
    if MOSTRAR.get("url"):
        return MOSTRAR.get("label")
    i = MOSTRAR.get("i", 0)
    return HOJAS[i]["label"] if HOJAS and 0 <= i < len(HOJAS) else None


def hilo_sim(base: str) -> None:
    """Latido del panel (0,5 s) + detecciones al simulador (PROTOCOLO.md §3).

    Detección: predicción ESTABLE con sospecha, o hoja sana estable (queda en el registro como
    "Saludable", sin alerta). Como mucho 1 POST/s; la misma enfermedad no antes de 6 s y "sana" no antes de 10 s.
    """
    ultimo_t: dict[str, float] = {}
    ultimo_post = 0.0
    ultima_etiqueta: str | None = None
    t_hb = 0.0
    ok_prev: bool | None = None
    while True:
        time.sleep(0.25)
        ahora = time.time()
        with E.lock:
            p = dict(E.pred) if E.pred else None
            cam_ok = bool(E.cam_ok) and (ahora - E.frame_t) < 2.0
            fps, edad = E.fps, ahora - E.frame_t
        if ahora - t_hb >= 0.5:
            t_hb = ahora
            hb = {"cam_ok": cam_ok, "fps": round(fps, 1), "frame_age_s": round(edad, 2) if E.frame_t else None}
            if p:
                hb.update({k: p.get(k) for k in ("clase", "confianza", "p_enfermedad", "sospecha", "estable", "p_hoja")})
            ok = _post_sim(base, "/api/panel", hb)
            if ok != ok_prev:
                print(f"[sim] {'conectado a' if ok else 'SIN conexión con'} {base}", flush=True)
                ok_prev = ok
        if not p or not p.get("estable") or p.get("clase") in (None, "sin_hoja") or p.get("error"):
            continue
        etiqueta, sospecha = p["clase"], bool(p.get("sospecha"))
        if sospecha:
            enviar = True
        else:  # sana estable: se registra para mostrar el caso sano (y cierra un hallazgo previo)
            enviar = etiqueta == "sana"
        espera = 10.0 if etiqueta == "sana" and ultima_etiqueta in (None, "sana") else 6.0
        if not enviar or ahora - ultimo_post < 1.0 or ahora - ultimo_t.get(etiqueta, 0.0) < espera:
            continue
        det = {"ts": ahora, "label": etiqueta, "conf": p.get("confianza"), "p_enfermedad": p.get("p_enfermedad"),
               "sospecha": sospecha, "umbral": p.get("umbral"), "cama": None, "truth_label": etiqueta_visor(),
               "frame": None, "source": "rtsp"}
        if _post_sim(base, "/api/detection", det):
            ultimo_post = ultimo_t[etiqueta] = ahora
            ultima_etiqueta = etiqueta
            print(f"[sim] detección enviada: {etiqueta} {det['conf']} sospecha={sospecha} verdad={det['truth_label']}", flush=True)


def make_handler(clf, filtro, umbral: float):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silencioso
            pass

        def _json(self, obj, code=200):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def _body(self) -> bytes:
            return self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/":
                b = PANEL.encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)
            elif u.path == "/hoja":
                b = VISOR.encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)
            elif u.path == "/api/estado":
                with E.lock:
                    self._json({"cam_ok": E.cam_ok, "fps": E.fps, "pred": E.pred, "roi": E.roi, "pausa": E.pausa})
            elif u.path == "/api/captura":
                self._json(CAPTURA)
            elif u.path == "/imgp":
                q = parse_qs(u.query)
                try:
                    pth = (DATOS / q["p"][0]).resolve()
                    if DATOS.resolve() not in pth.parents:
                        raise ValueError("ruta fuera de datos/")
                    im = Image.open(pth).convert("RGB")
                    buf = io.BytesIO(); im.save(buf, "JPEG", quality=92); b = buf.getvalue()
                    self.send_response(200); self.send_header("Content-Type", "image/jpeg"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
                except Exception:  # noqa: BLE001
                    self.send_error(404)
            elif u.path == "/api/hojas":
                self._json([{"i": i} for i in range(len(HOJAS))])
            elif u.path == "/api/mostrar":
                if "robot=1" in (self.headers.get("Referer") or ""):
                    VISOR_OK["robot_visto"] = time.time()
                if MOSTRAR.get("url"):
                    self._json({"i": MOSTRAR["i"], "url": MOSTRAR["url"], "label": MOSTRAR.get("label"), "captura": True})
                else:
                    i = MOSTRAR["i"]
                    self._json({"i": i, "label": HOJAS[i]["label"] if HOJAS else None})
            elif u.path.startswith("/img/"):
                try:
                    i = int(u.path.split("/")[2]) % max(1, len(HOJAS))
                    im = Image.open(DATOS / HOJAS[i]["path"]).convert("RGB")
                    if "mini" in parse_qs(u.query):
                        im.thumbnail((160, 160))
                    buf = io.BytesIO(); im.save(buf, "JPEG", quality=88)
                    b = buf.getvalue()
                    self.send_response(200); self.send_header("Content-Type", "image/jpeg"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
                except Exception:  # noqa: BLE001
                    self.send_error(404)
            elif u.path == "/api/vista":
                with E.lock:
                    self._json({"vista": E.vista, "vistas": list(VISTAS)})
            elif u.path == "/stream.mjpg":
                pedida = (parse_qs(u.query).get("vista") or [None])[0]
                if pedida is not None and pedida not in VISTAS:
                    self._json({"error": "vista desconocida", "vistas": list(VISTAS)}, 400)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                try:
                    while True:
                        t_ini = time.time()
                        with E.lock:
                            f = None if E.frame is None else E.frame.copy()
                            vista = pedida or E.vista
                        if f is None:
                            f = np.zeros((540, 960, 3), np.uint8)
                            cv2.putText(f, "Esperando la camara del robot...", (40, 270), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (200, 200, 200), 2)
                        else:
                            f = componer_vista(f, vista)
                        ok, jpg = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 75])
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")
                        time.sleep(max(0.0, 1 / 15 - (time.time() - t_ini)))
                except (BrokenPipeError, ConnectionResetError):
                    pass
            else:
                self.send_error(404)

        def do_POST(self):
            u = urlparse(self.path)
            if u.path == "/api/roi":
                try:
                    r = [min(1.0, max(0.0, float(v))) for v in json.loads(self._body())][:4]
                    with E.lock:
                        E.roi = r
                    self._json({"roi": r})
                except Exception as e:  # noqa: BLE001
                    self._json({"error": str(e)}, 400)
            elif u.path == "/api/zoom":
                z = float(json.loads(self._body() or b"{}").get("zoom", 1))
                with E.lock:
                    E.zoom = min(4.0, max(1.0, z))
                    E.ventana = []
                self._json({"zoom": E.zoom})
            elif u.path == "/api/vista":
                try:
                    v = json.loads(self._body() or b"{}").get("vista")
                except Exception:  # noqa: BLE001
                    v = None
                if v not in VISTAS:
                    self._json({"error": "vista desconocida", "vistas": list(VISTAS)}, 400)
                else:
                    with E.lock:
                        E.vista = v
                    self._json({"vista": v})
            elif u.path == "/api/visor_ok":
                VISOR_OK["i"] = int(json.loads(self._body() or b"{}").get("i", -1))
                self._json({"ok": True})
            elif u.path == "/api/captura_detener":
                CAPTURA["detener"] = True
                self._json({"ok": True})
            elif u.path == "/api/color":
                with E.lock:
                    E.color = not E.color
                    E.ventana = []
                    self._json({"color": E.color})
            elif u.path == "/api/captura":
                cfg = json.loads(self._body() or b"{}")
                if CAPTURA["activa"]:
                    self._json({"error": "ya hay una captura en curso", **CAPTURA}, 409)
                else:
                    threading.Thread(target=hilo_captura, args=(cfg.get("splits", ["train", "val", "test"]), float(cfg.get("espera", 1.5))), daemon=True).start()
                    self._json({"ok": True})
            elif u.path == "/api/auto":
                with E.lock:
                    E.auto = not E.auto
                    E.ventana = []
                    self._json({"auto": E.auto})
            elif u.path == "/api/multiescala":
                with E.lock:
                    E.multiescala = not E.multiescala
                    E.ventana = []
                    self._json({"multiescala": E.multiescala})
            elif u.path == "/api/pausa":
                with E.lock:
                    E.pausa = not E.pausa
                    self._json({"pausa": E.pausa})
            elif u.path == "/api/mostrar":
                i = int(json.loads(self._body() or b"{}").get("i", 0))
                MOSTRAR["i"] = random.randrange(len(HOJAS)) if i < 0 else i % max(1, len(HOJAS))
                self._json({"i": MOSTRAR["i"], "label": HOJAS[MOSTRAR["i"]]["label"] if HOJAS else None})
            elif u.path == "/api/clasificar":
                try:
                    im = Image.open(io.BytesIO(self._body()))
                    self._json(clasificar(clf, filtro, umbral, im))
                except Exception as e:  # noqa: BLE001
                    self._json({"error": str(e)}, 400)
            else:
                self.send_error(404)

    return H


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--robot-ip", default="10.90.251.84")
    ap.add_argument("--port", type=int, default=8092)
    ap.add_argument("--modelo", default=str(MODELO), help="carpeta con el .joblib y umbral.json")
    ap.add_argument("--intervalo", type=float, default=0.5, help="segundos entre clasificaciones")
    ap.add_argument("--sim-url", default=None,
                    help="URL de sim-core (p. ej. http://localhost:8000) para enviarle latido y detecciones; por defecto apagado")
    ap.add_argument("--video", default=None,
                    help="PRUEBAS sin robot: video, imagen o carpeta de imágenes que se reproduce en bucle como cámara")
    ap.add_argument("--t-aire", type=float, default=18.0, help="temperatura del aire por defecto (°C) si no hay sim-core")
    ap.add_argument("--hr", type=float, default=75.0, help="humedad relativa por defecto (%%) si no hay sim-core")
    a = ap.parse_args()
    SENS.t, SENS.hr = a.t_aire, a.hr
    mdir = Path(a.modelo)
    umbral = json.load(open(mdir / "umbral.json"))["umbral"]
    print("Cargando modelo…", flush=True)
    clf = load_classifier(next(mdir.glob("clip_probe_tiles3*.joblib")))
    print(f"Modelo: {clf.name}", flush=True)
    filtro = FiltroHoja(clf.embedder)
    print(f"Filtro de hoja activo (umbral p_hoja {filtro.umbral})", flush=True)
    url = f"rtsp://{a.robot_ip}:8554/test"
    if a.video:
        threading.Thread(target=hilo_video, args=(a.video,), daemon=True).start()
        print(f"MODO PRUEBA: cámara simulada con {a.video}", flush=True)
    else:
        threading.Thread(target=hilo_camara, args=(url,), daemon=True).start()
    threading.Thread(target=hilo_sensores, args=(a.sim_url,), daemon=True).start()
    threading.Thread(target=hilo_inferencia, args=(clf, filtro, umbral, a.intervalo), daemon=True).start()
    if a.sim_url:
        threading.Thread(target=hilo_sim, args=(a.sim_url,), daemon=True).start()
        print(f"Enviando latido y detecciones a {a.sim_url}", flush=True)
    print(f"Panel: http://localhost:{a.port}   ·   Visor de hojas: http://localhost:{a.port}/hoja   ·   cámara {url}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", a.port), make_handler(clf, filtro, umbral)).serve_forever()


if __name__ == "__main__":
    main()
