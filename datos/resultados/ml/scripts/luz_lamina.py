import sys; sys.path.insert(0,"/Users/santiagosantafe/Downloads/SabanaHack/datos/resultados/ml/scripts")
import numpy as np, pandas as pd
from PIL import Image, ImageDraw
import luz_common as L
D="/Users/santiagosantafe/Downloads/SabanaHack/datos/"
tr=pd.read_csv(D+"resultados/ml/drberry_image/splits/train.csv",dtype=str,keep_default_na=False)
rng=np.random.default_rng(777); idx=rng.choice(len(tr),12,replace=False)
T=300; W=Image.new("RGB",(6*T,4*T),(30,30,30))
for n,i in enumerate(idx):
    im=L.cargar(tr.path[i]); a,p=L.aug_camara(im,rng); pp=L.preprocesar(a)
    r,c=(n//6)*2,n%6
    W.paste(a.resize((T,T)),(c*T,r*T)); W.paste(pp.resize((T,T)),(c*T,(r+1)*T))
    d=ImageDraw.Draw(W); d.text((c*T+4,r*T+4),f"{tr.label[i]} {p.get('tinte')}",fill=(255,255,0))
W.save(D+"resultados/ml/modelo_luz/ejemplos_aumentos.png")
# tira de capturas reales para comparar
rows=pd.read_csv(D+"resultados/ml/capturas_pantalla/manifest.csv").iloc[::9][:6]
R=Image.new("RGB",(6*T,T))
for c,(_,r) in enumerate(rows.iterrows()): R.paste(Image.open(D+r.captura_roi).convert("RGB").resize((T,T)),(c*T,0))
R.save("/private/tmp/claude-501/-Users-santiagosantafe-Downloads-SabanaHack/bb0c9bf1-afd6-4481-af59-cdd3c745cea4/scratchpad/real6.png")
