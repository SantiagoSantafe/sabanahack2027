"""Consulta metadatos de un workspace/proyecto de Roboflow via REST.
Uso: ROBOFLOW_API_KEY=... python -I rf_info.py <workspace> [<project>] <out.json>
La key se lee solo de la variable de entorno y se redacta de cualquier salida.
"""
import json
import os
import sys

import requests

KEY = os.environ.get("ROBOFLOW_API_KEY", "").strip()
if not KEY:
    sys.exit("Falta ROBOFLOW_API_KEY")


def redact(s):
    return s.replace(KEY, "<REDACTED>") if isinstance(s, str) else s


def get(path):
    url = "https://api.roboflow.com/" + path.lstrip("/")
    r = requests.get(url, params={"api_key": KEY}, timeout=60)
    try:
        data = r.json()
    except Exception:
        data = {"_raw": r.text[:2000]}
    return r.status_code, json.loads(redact(json.dumps(data)))


def main():
    args = sys.argv[1:]
    out = args[-1]
    path = "/".join(args[:-1])
    code, data = get(path)
    with open(out, "w") as f:
        json.dump({"status": code, "path": path, "data": data}, f, indent=2, ensure_ascii=False)
    print("status", code, "->", out)


if __name__ == "__main__":
    main()
