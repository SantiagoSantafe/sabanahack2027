"""Agrega a drberry_imagenes.csv una columna split_grupal_sugerido (train/valid/test ~70/15/15 por GRUPOS de rafaga,
estratificado por la clase dominante del grupo, semilla fija). No entrena nada.
Uso: python -I split_grupal.py <drberry_imagenes.csv>"""
import csv, collections, random, sys
p = sys.argv[1]
rows = list(csv.DictReader(open(p)))
g_cls = collections.defaultdict(collections.Counter)
g_n = collections.Counter()
for r in rows:
    g_cls[r["grupo_rafaga"]][r["clase_dominante"]] += 1
    g_n[r["grupo_rafaga"]] += 1
by_cls = collections.defaultdict(list)
for g, c in g_cls.items():
    by_cls[c.most_common(1)[0][0]].append(g)
rng = random.Random(20261023)
assign = {}
for cls in sorted(by_cls):
    gs = sorted(by_cls[cls]); rng.shuffle(gs)
    tot = sum(g_n[g] for g in gs); acc = {"test": 0, "valid": 0}
    for g in gs:
        if acc["test"] < 0.15 * tot:
            assign[g] = "test"; acc["test"] += g_n[g]
        elif acc["valid"] < 0.15 * tot:
            assign[g] = "valid"; acc["valid"] += g_n[g]
        else:
            assign[g] = "train"
for r in rows:
    r["split_grupal_sugerido"] = assign[r["grupo_rafaga"]]
with open(p, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
c = collections.Counter((r["split_grupal_sugerido"], r["clase_dominante"]) for r in rows)
for sp in ("train", "valid", "test"):
    print(sp, sum(v for (s, _), v in c.items() if s == sp), {k: v for (s, k), v in sorted(c.items()) if s == sp},
          "grupos", len({g for g, s in assign.items() if s == sp}))
