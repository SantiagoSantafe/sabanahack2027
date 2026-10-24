"""Descarga una exportacion de Roboflow (REST) y la extrae de forma segura.
Uso: ROBOFLOW_API_KEY=... python -I rf_download.py <workspace> <project> <version> <format> <dest_dir>
- La key solo se lee de la variable de entorno y nunca se imprime (se redacta).
- Omite archivos > 2 GB.
- Extraccion con proteccion contra rutas fuera del destino (zip slip).
"""
import json
import os
import sys
import time
import zipfile

import requests

KEY = os.environ.get("ROBOFLOW_API_KEY", "").strip()
if not KEY:
    sys.exit("Falta ROBOFLOW_API_KEY")
MAX_BYTES = 2 * 1024 ** 3


def redact(s):
    return str(s).replace(KEY, "<REDACTED>")


def main():
    ws, proj, ver, fmt, dest = sys.argv[1:6]
    dest = os.path.abspath(dest)
    os.makedirs(dest, exist_ok=True)
    url = "https://api.roboflow.com/%s/%s/%s/%s" % (ws, proj, ver, fmt)
    link = None
    for attempt in range(40):
        r = requests.get(url, params={"api_key": KEY}, timeout=120)
        try:
            data = r.json()
        except Exception:
            print("respuesta no JSON", r.status_code, redact(r.text[:300]))
            sys.exit(1)
        exp = data.get("export") or {}
        link = exp.get("link")
        if link:
            break
        prog = data.get("progress") or exp.get("progress")
        print("esperando exportacion... status", r.status_code, "progress", prog,
              redact(json.dumps({k: v for k, v in data.items() if k != "version"})[:300]))
        time.sleep(10)
    if not link:
        sys.exit("No se obtuvo enlace de exportacion")
    meta = {k: v for k, v in data.items()}
    with open(os.path.join(dest, "_export_meta.json"), "w") as f:
        f.write(redact(json.dumps(meta, indent=2, ensure_ascii=False)))
    h = requests.head(link, timeout=60, allow_redirects=True)
    size = int(h.headers.get("Content-Length", "0") or 0)
    print("tamano reportado (bytes):", size)
    if size > MAX_BYTES:
        sys.exit("OMITIDO: archivo > 2 GB")
    zpath = os.path.join(dest, "%s-v%s-%s.zip" % (proj, ver, fmt))
    got = 0
    with requests.get(link, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        with open(zpath, "wb") as f:
            for chunk in resp.iter_content(1 << 20):
                got += len(chunk)
                if got > MAX_BYTES:
                    f.close()
                    os.remove(zpath)
                    sys.exit("OMITIDO: descarga supero 2 GB")
                f.write(chunk)
    print("descargado", zpath, got, "bytes")
    outdir = os.path.join(dest, "%s-v%s-%s" % (proj, ver, fmt))
    os.makedirs(outdir, exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        total = sum(i.file_size for i in z.infolist())
        if total > MAX_BYTES:
            sys.exit("OMITIDO: contenido descomprimido > 2 GB")
        for info in z.infolist():
            target = os.path.abspath(os.path.join(outdir, info.filename))
            if not target.startswith(outdir + os.sep) and target != outdir:
                print("ruta sospechosa omitida:", info.filename)
                continue
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, "wb") as dst:
                while True:
                    b = src.read(1 << 20)
                    if not b:
                        break
                    dst.write(b)
    print("extraido en", outdir, "archivos:", len(z.infolist()), "bytes descomprimidos:", total)


if __name__ == "__main__":
    main()
