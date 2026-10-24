"""Verificación del entorno .venv del equipo (Sabana Hack - Berry Good Idea).

Uso (desde cualquier carpeta que NO esté dentro de raw/):
    /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I \
        /Users/santiagosantafe/Downloads/SabanaHack/datos/pipeline/verificar_entorno.py

Comprueba imports y versiones, MPS, y una inferencia mínima con
ultralytics (yolo11n-cls) y open_clip (ViT-B-32 laion2b). Los pesos quedan en
pipeline/pesos/. No usa ni imprime la API key de Roboflow.
"""
import importlib
import json
import platform
import sys
import time
from pathlib import Path

BASE = Path("/Users/santiagosantafe/Downloads/SabanaHack/datos")
PESOS = BASE / "pipeline" / "pesos"
PESOS.mkdir(parents=True, exist_ok=True)

resultado = {"python": sys.version.split()[0], "plataforma": platform.platform(),
             "maquina": platform.machine(), "paquetes": {}, "errores": {}}

PAQUETES = [
    ("torch", "torch"), ("torchvision", "torchvision"), ("ultralytics", "ultralytics"),
    ("open_clip_torch", "open_clip"), ("imagehash", "imagehash"),
    ("scikit-learn", "sklearn"), ("pyyaml", "yaml"), ("pillow", "PIL"),
    ("pandas", "pandas"), ("numpy", "numpy"), ("matplotlib", "matplotlib"),
    ("requests", "requests"), ("pytest", "pytest"), ("roboflow", "roboflow"),
    ("tqdm", "tqdm"), ("seaborn", "seaborn"),
]
for nombre, modulo in PAQUETES:
    try:
        m = importlib.import_module(modulo)
        resultado["paquetes"][nombre] = getattr(m, "__version__", "sin __version__")
    except Exception as e:  # noqa: BLE001
        resultado["errores"][nombre] = repr(e)

import torch  # noqa: E402

resultado["mps_disponible"] = bool(torch.backends.mps.is_available())
resultado["mps_compilado"] = bool(torch.backends.mps.is_built())
dispositivo = "mps" if resultado["mps_disponible"] else "cpu"
resultado["dispositivo"] = dispositivo

# Prueba tensorial en MPS
try:
    a = torch.randn(512, 512, device=dispositivo)
    b = (a @ a.T).sum().item()
    resultado["mps_matmul_ok"] = bool(b == b)
except Exception as e:  # noqa: BLE001
    resultado["errores"]["mps_matmul"] = repr(e)

# Imagen sintética (verde con manchas) para la inferencia mínima
from PIL import Image, ImageDraw  # noqa: E402

img = Image.new("RGB", (224, 224), (60, 140, 60))
d = ImageDraw.Draw(img)
for x, y in [(50, 60), (120, 90), (160, 170)]:
    d.ellipse([x, y, x + 25, y + 20], fill=(230, 230, 230))
img_path = PESOS / "_prueba_sintetica.png"
img.save(img_path)

# ultralytics: clasificación con yolo11n-cls
try:
    from ultralytics import YOLO

    t0 = time.time()
    modelo = YOLO(str(PESOS / "yolo11n-cls.pt"))
    pred = modelo.predict(str(img_path), device=dispositivo, verbose=False)[0]
    top1 = int(pred.probs.top1)
    resultado["ultralytics_inferencia"] = {
        "pesos": str(PESOS / "yolo11n-cls.pt"),
        "top1_clase": pred.names[top1],
        "top1_conf": round(float(pred.probs.top1conf), 4),
        "segundos": round(time.time() - t0, 2),
        "dispositivo": dispositivo,
    }
except Exception as e:  # noqa: BLE001
    resultado["errores"]["ultralytics_inferencia"] = repr(e)

# open_clip: ViT-B-32 laion2b_s34b_b79k, zero-shot de prueba
try:
    import open_clip

    t0 = time.time()
    cache = PESOS / "open_clip"
    cache.mkdir(exist_ok=True)
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k", cache_dir=str(cache))
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    model = model.to(dispositivo).eval()
    textos = ["a healthy green leaf", "a leaf with white powdery mildew",
              "a leaf with brown spots", "a caterpillar on a fruit"]
    with torch.no_grad():
        im = preprocess(img).unsqueeze(0).to(dispositivo)
        tx = tokenizer(textos).to(dispositivo)
        fi = model.encode_image(im)
        ft = model.encode_text(tx)
        fi = fi / fi.norm(dim=-1, keepdim=True)
        ft = ft / ft.norm(dim=-1, keepdim=True)
        probs = (100.0 * fi @ ft.T).softmax(dim=-1)[0].cpu().tolist()
    resultado["open_clip_inferencia"] = {
        "modelo": "ViT-B-32", "pretrained": "laion2b_s34b_b79k",
        "cache_dir": str(cache), "dim_embedding": int(fi.shape[-1]),
        "probs_zero_shot": {t: round(p, 4) for t, p in zip(textos, probs)},
        "segundos": round(time.time() - t0, 2), "dispositivo": dispositivo,
    }
except Exception as e:  # noqa: BLE001
    resultado["errores"]["open_clip_inferencia"] = repr(e)

salida = PESOS / "verificacion_entorno.json"
salida.write_text(json.dumps(resultado, indent=2, ensure_ascii=False))
print(json.dumps(resultado, indent=2, ensure_ascii=False))
sys.exit(1 if resultado["errores"] else 0)
