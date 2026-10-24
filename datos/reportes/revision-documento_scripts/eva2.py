import json, sys, collections
rows = json.load(open(sys.argv[1]))
f = lambda r,k: float(r.get(k) or 0)
by_y = collections.defaultdict(lambda:[0,0,0])
by_yd = collections.defaultdict(lambda:[0,0,0])
for r in rows:
    y = r["a_o"]; dpt = r["departamento"]
    for acc in (by_y[y], by_yd[(y,dpt)]):
        acc[0]+=f(r,"rea_sembrada"); acc[1]+=f(r,"rea_cosechada"); acc[2]+=f(r,"producci_n")
print("Año | sembrada ha | cosechada ha | produccion t | rend t/ha cosechada")
for y in sorted(by_y):
    s,c,p = by_y[y]; print(y, round(s,1), round(c,1), round(p,1), round(p/c,2) if c else None)
y = max(by_y)
print("Por departamento", y)
for (yy,dpt),(s,c,p) in sorted(by_yd.items(), key=lambda kv:-kv[1][0]):
    if yy==y: print(dpt, round(s,1), round(c,1), round(p,1), round(p/c,2) if c else None)
