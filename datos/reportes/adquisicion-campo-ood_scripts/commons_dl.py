"""Descarga imagenes seleccionadas de Wikimedia Commons (API publica) con licencia y autor.
Uso: python3 -I commons_dl.py <campo_ood_dir>
"""
import json, sys, os, re, csv, time, site, warnings, html
warnings.filterwarnings("ignore")
sys.path.append(site.getusersitepackages())
import requests

ROOT = sys.argv[1]
CAND = os.path.join(ROOT, "_candidatos")
API = "https://commons.wikimedia.org/w/api.php"
s = requests.Session()
s.headers.update({"User-Agent": "SabanaHack-BerryGoodIdea/0.1 (hackathon academic project; low-volume)"})
SEL = {
    "roya": [
        ("File:Starr-110621-6276-Vaccinium hybrid-Southern highbush cv Misty leaf with rust-Hawea Pl Olinda-Maui (24466601624).jpg", "estricta(titulo_autor:rust)", "Vaccinium hybrid southern highbush cv Misty"),
        ("File:Starr-110621-6275-Vaccinium hybrid-Southern highbush cv Misty fruit and leaves with rust-Hawea Pl Olinda-Maui (25097294125).jpg", "estricta(titulo_autor:rust)", "Vaccinium hybrid southern highbush cv Misty"),
        ("File:Naohidemyces vacciniorum on Vaccinium oxycoccos.jpg", "estricta(hospedero_arandano_rojo)", "Vaccinium oxycoccos"),
    ],
    "heliothis_oruga": [
        ("File:Actebia fennica caterpillar on blueberry.jpg", "proxy_oruga_no_heliothinae", "blueberry"),
        ("File:Acrobasis vaccinii 1496495.jpg", "proxy_oruga_no_heliothinae", "Vaccinium"),
    ],
    "sana": [
        ("File:Highbush Blueberry Vaccinium corymbosum Leaves 3008px.jpg", "especie_titulo+revision_visual", "Vaccinium corymbosum"),
        ("File:2020-07-06 16 05 58 Leaves in mid-summer on a Bountiful Blue Blueberry bush along Tranquility Court in the Franklin Farm section of Oak Hill, Fairfax County, Virginia.jpg", "cultivar_titulo+revision_visual", "Vaccinium cv Bountiful Blue (cultivado)"),
        ("File:Vaccinium corymbosum Bluecrop 0zz.jpg", "cultivar_titulo+revision_visual", "Vaccinium corymbosum cv Bluecrop"),
        ("File:Vaccinium corymbosum Patriot 1zz.jpg", "cultivar_titulo+revision_visual", "Vaccinium corymbosum cv Patriot"),
        ("File:Vaccinium corymbosum Duke.jpeg", "cultivar_titulo+revision_visual", "Vaccinium corymbosum cv Duke"),
        ("File:Vaccinium corymbosum Northland 1zz.jpg", "cultivar_titulo+revision_visual", "Vaccinium corymbosum cv Northland"),
        ("File:Starr-110621-6264-Vaccinium hybrid-Southern highbush cv Emerald habit-Hawea Pl Olinda-Maui (25070946446).jpg", "cultivar_titulo+revision_visual", "Vaccinium hybrid southern highbush cv Emerald"),
        ("File:Starr-110621-6278-Vaccinium hybrid-Southern highbush cv Sharpblue habit-Hawea Pl Olinda-Maui (24729634009).jpg", "cultivar_titulo+revision_visual", "Vaccinium hybrid southern highbush cv Sharpblue"),
    ],
}
rows = []
for clase, lst in SEL.items():
    d = os.path.join(CAND, clase)
    os.makedirs(d, exist_ok=True)
    for title, nivel, host in lst:
        p = dict(action="query", titles=title, prop="imageinfo", iiprop="url|extmetadata|size|mime",
                 iiurlwidth=1024, format="json")
        r = s.get(API, params=p, timeout=60)
        if r.status_code != 200 or not r.text.startswith("{"):
            print("API FAIL", title, r.status_code); time.sleep(10); continue
        pages = r.json()["query"]["pages"]
        pg = list(pages.values())[0]
        if "imageinfo" not in pg:
            print("MISSING", title); continue
        ii = pg["imageinfo"][0]
        em = ii.get("extmetadata", {})
        lic = em.get("LicenseShortName", {}).get("value", "")
        artist = re.sub("<[^>]+>", "", html.unescape(em.get("Artist", {}).get("value", ""))).strip()
        thumb = ii.get("thumburl") or ii["url"]
        time.sleep(3)
        img = s.get(thumb, timeout=60)
        if img.status_code != 200:
            print("IMG FAIL", title, img.status_code); time.sleep(10); continue
        fn = "commons_%d.jpg" % pg["pageid"]
        open(os.path.join(d, fn), "wb").write(img.content)
        rows.append({"clase": clase, "archivo": fn, "fuente": "Wikimedia Commons", "obs_id": "", "photo_id": pg["pageid"],
                     "taxon_identificado": title[5:], "nivel_etiqueta": nivel, "hospedero_declarado": host,
                     "quality_grade": "", "cultivado_captive": "", "lugar": "", "lat": "", "lon": "",
                     "fecha": re.sub("<[^>]+>", "", em.get("DateTimeOriginal", {}).get("value", ""))[:40],
                     "autor_login": "", "autor_nombre": artist[:120], "licencia": lic,
                     "atribucion": "%s, %s, via Wikimedia Commons" % (artist[:120], lic),
                     "url_observacion": ii.get("descriptionurl"), "url_foto": thumb})
        print(clase, fn, lic, artist[:50], flush=True)
        time.sleep(3)
with open(os.path.join(CAND, "candidatos_commons.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
