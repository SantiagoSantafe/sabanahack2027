"""Descarga SOLO el split test (traditional-augmentation) del dataset Mendeley k2ptxmfjhj (CC BY-NC 4.0).
Uso: python3 -I mendeley_dl.py <meta.json> <outdir>
"""
import json, sys, os, re, time, hashlib, site, warnings
warnings.filterwarnings("ignore")
sys.path.append(site.getusersitepackages())
import requests

meta = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
FOLDER = "316bbb2a-3c73-4725-a67c-6372323c3c57"  # Strawberry-segmentation-traditional-augmentation/test
s = requests.Session()
s.headers.update({"User-Agent": "SabanaHack-BerryGoodIdea/0.1 (hackathon, investigacion academica)"})
n = 0
for f in meta["files"]:
    if f.get("folder_id") != FOLDER:
        continue
    name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(f["filename"]))
    fp = os.path.join(OUT, name)
    if os.path.exists(fp):
        continue
    url = f["content_details"]["download_url"]
    if not url.startswith("https://data.mendeley.com/"):
        print("skip url", url); continue
    r = s.get(url, timeout=120)
    if r.status_code != 200:
        print("FAIL", name, r.status_code); continue
    h = hashlib.sha256(r.content).hexdigest()
    if h != f["content_details"].get("sha256_hash"):
        print("HASH MISMATCH", name)
    with open(fp, "wb") as fh:
        fh.write(r.content)
    n += 1
    if n % 50 == 0:
        print(n, flush=True)
    time.sleep(0.25)
print("done", n)
