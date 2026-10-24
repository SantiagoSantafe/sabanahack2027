"""Aplica la revision manual (hojas de contacto) y arma la estructura final + manifiesto.
Uso: python3 -I apply_review.py <campo_ood_dir> <sheets_dir>
"""
import csv, os, sys, shutil, hashlib, collections, json

ROOT, SH = sys.argv[1], sys.argv[2]
CAND = os.path.join(ROOT, "_candidatos")
DESC = os.path.join(ROOT, "_descartadas")
CAP = 60

CONIF = "hospedero_alterno_Tsuga(aecios_en_aciculas,no_hoja_de_arandano)"
PG = "plano_general(sintoma_no_visible)"
NV = "sintoma_no_visible_en_la_foto"
FP = "oruga_fuera_de_planta(mano/papel/mesa)"
LAB = "hoja_desprendida_fondo_laboratorio"
GEN_SANA = "no_cumple_criterio_hoja_sana(flor/fruto/plano_general/maceta)"

DEC = {
    ("oidio", "oidio2"): {
        "0": "herbario(no_campo)", "4": NV, "8": PG, "9": "hospedero_no_parece_Vaccinium", "15": NV, "17": PG, "18": PG,
        "19": NV, "20": PG, "21": PG, "25": PG, "29": "hospedero_no_parece_Vaccinium", "36": PG, "38": NV, "40": NV,
        "41": "hospedero_Catalpa(hoja_cordada)", "42": "hospedero_Catalpa(hoja_cordada)", "43": "hospedero_no_parece_Vaccinium",
        "44": PG, "48": "duplicado_de_otra_observacion", "52": NV, "59": NV, "62": PG, "63": NV, "66": NV, "68": NV,
        "70": NV, "71": PG, "73": PG, "80": "hospedero_Catalpa(hoja_cordada)", "82": "hospedero_Catalpa(hoja_cordada)",
        "84": "sintoma_no_corresponde(mancha_necrotica,no_micelio)", "85": NV},
    ("roya", "roya"): dict({str(i): CONIF for i in [4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 19, 21, 22, 23, 24, 39, 42, 43, 44, 47, 76]},
                           **{"0": "sintoma_ambiguo(agujeros_y_necrosis,roya_no_visible)", "36": NV, "38": NV, "45": NV,
                              "49": "foto_con_lupa/microscopio", "55": NV, "65": NV, "70": NV, "84": NV, "88": PG}),
    ("heliothis_oruga", "heliothis_oruga"): {
        "1": "ilustracion(no_foto)", "14": FP, "15": FP, "18": FP, "20": FP, "22": FP, "24": "sin_larva_ni_dano_visible",
        "27": LAB, "28": LAB, "35": FP, "37": "adulto(no_larva)", "39": FP, "42": FP, "43": "sin_larva_ni_dano_claro",
        "48": "minador_de_hoja(no_oruga_externa)", "53": "sin_larva_ni_dano_claro", "56": FP, "57": "sin_larva_ni_dano_claro",
        "61": "sin_larva_visible", "62": "sin_larva_visible(solo_seda)", "65": LAB, "66": FP, "68": FP, "70": LAB, "72": LAB, "76": FP},
    ("alternaria", "alternaria"): dict({str(i): "ID_dudosa(observador_reporta_picnidios)+tallo/microscopia/etiqueta" for i in range(3, 15)},
                                       **{"0": "plano_general_con_agujeros(posible_dano_por_insecto)", "15": "misma_observacion_que_16(se_conserva_una)"}),
}
SANA_KEEP = {"sana": {0, 7, 11, 16, 18, 19, 21, 24, 25, 27, 28, 33, 36, 39, 42, 43, 50, 54, 56, 59, 60, 63, 68, 74, 75, 76, 79, 80,
                      83, 84, 86, 88, 89, 90, 91, 94, 95, 96, 97},
             "sana2": {0, 3, 6, 8, 10, 12, 15, 17, 21, 25, 26, 28, 32, 34, 35, 36, 37, 38, 43, 48, 52, 53, 57, 59, 61, 62, 64, 65, 68}}
SANA_REASON = {"sana": {"9": "dano_visible(agujero)", "29": "manchas_visibles", "44": "coloracion_otonal", "45": "follaje_rojizo",
                        "46": "follaje_rojizo", "49": "posibles_manchas", "53": "desenfocada", "62": "follaje_rojizo", "85": "oscura/densa",
                        "5": "plano_general(posibles_lesiones)", "31": "sin_hojas"},
               "sana2": {"9": "manchas_visibles", "30": "manchas_visibles", "33": "dano_visible(agujeros)", "69": "herbario(hojas_secas)",
                         "45": "follaje_rojizo"}}


def idx(name):
    return dict(l.rstrip("\n").split("\t") for l in open(os.path.join(SH, name + "_index.tsv")))


discard = {}  # (clase, archivo) -> motivo
for (clase, sheet), d in DEC.items():
    ix = idx(sheet)
    for i, m in d.items():
        discard[(clase, ix[i])] = m
for sheet, keep in SANA_KEEP.items():
    ix = idx(sheet)
    for i, fn in ix.items():
        if int(i) not in keep:
            discard[("sana", fn)] = SANA_REASON[sheet].get(i, GEN_SANA)

meta = {}
for fn in ("candidatos_inat.csv", "candidatos_commons.csv"):
    for r in csv.DictReader(open(os.path.join(CAND, fn))):
        meta[(r["clase"], r["archivo"])] = r

# verificar duplicados exactos (md5) entre candidatos
def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()

accepted = collections.defaultdict(list)
for clase in ("oidio", "roya", "sana", "heliothis_oruga", "alternaria"):
    seen = {}
    for fn in sorted(os.listdir(os.path.join(CAND, clase))):
        key = (clase, fn)
        h = md5(os.path.join(CAND, clase, fn))
        if key in discard:
            continue
        if h in seen:
            discard[key] = "duplicado_exacto_de_" + seen[h]
            continue
        seen[h] = fn
        r = dict(meta[key]); r["md5"] = h
        accepted[clase].append(r)

# tope de 60 por clase: se recorta del autor mas repetido (en sana se priorizan cultivadas)
for clase, lst in accepted.items():
    while len(lst) > CAP:
        cnt = collections.Counter(r["autor_login"] or r["autor_nombre"] for r in lst)
        top = cnt.most_common(1)[0][0]
        cands = [r for r in lst if (r["autor_login"] or r["autor_nombre"]) == top]
        cands.sort(key=lambda r: (str(r.get("cultivado_captive")) == "True", r["archivo"]))
        victim = cands[0]
        lst.remove(victim)
        discard[(clase, victim["archivo"])] = "recorte_tope_60(autor_mas_repetido)"

# mover a estructura final
desc_rows = []
for (clase, fn), motivo in sorted(discard.items()):
    src = os.path.join(CAND, clase, fn)
    if os.path.exists(src):
        os.makedirs(os.path.join(DESC, clase), exist_ok=True)
        shutil.move(src, os.path.join(DESC, clase, fn))
    r = dict(meta.get((clase, fn), {"clase": clase, "archivo": fn}))
    r["motivo_descarte"] = motivo
    desc_rows.append(r)
# descartes del prefiltro de oidio (formas de E. vaccinii en hospederos no-Vaccinium)
pre = os.path.join(DESC, "descartes_prefiltro_oidio.csv")
if os.path.exists(pre):
    for r in csv.DictReader(open(pre)):
        desc_rows.append(r)

man = []
for clase, lst in accepted.items():
    os.makedirs(os.path.join(ROOT, clase), exist_ok=True)
    for r in lst:
        shutil.move(os.path.join(CAND, clase, r["archivo"]), os.path.join(ROOT, clase, r["archivo"]))
        lugar = r.get("lugar") or ""
        r["pais_aprox"] = lugar.split(",")[-1].strip() if lugar else ""
        r["ruta"] = "%s/%s" % (clase, r["archivo"])
        r["revision_manual"] = "aceptada"
        man.append(r)

fields = ["ruta", "clase", "archivo", "fuente", "nivel_etiqueta", "taxon_identificado", "hospedero_declarado", "obs_id",
          "photo_id", "quality_grade", "cultivado_captive", "lugar", "pais_aprox", "lat", "lon", "fecha", "autor_login",
          "autor_nombre", "licencia", "atribucion", "url_observacion", "url_foto", "md5", "revision_manual"]
with open(os.path.join(ROOT, "manifiesto.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(man)
dfields = fields[:-2] + ["motivo_descarte"]
with open(os.path.join(DESC, "descartes.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=dfields, extrasaction="ignore"); w.writeheader(); w.writerows(desc_rows)

print("ACEPTADAS", {c: len(l) for c, l in accepted.items()}, "total", len(man))
print("DESCARTADAS", collections.Counter(r["clase"] for r in desc_rows))
print("motivos", collections.Counter((r["clase"], r["motivo_descarte"].split("(")[0]) for r in desc_rows).most_common(40))
left = {c: os.listdir(os.path.join(CAND, c)) for c in os.listdir(CAND) if os.path.isdir(os.path.join(CAND, c))}
print("restantes en _candidatos:", {c: len(v) for c, v in left.items()})
