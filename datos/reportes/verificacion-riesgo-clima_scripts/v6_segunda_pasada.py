"""v6_segunda_pasada.py -- verificacion-riesgo-clima, 2a pasada (2026-10-23).
Reimplementacion independiente (NO importa risk.py) de los dias en alto 2025 con T-1/0/+1 C y HR 90/85,
Botrytis>=0.50, estacionalidad, regla de roya 19-25 C, hora de la Tmin de Open-Meteo y desfase UTC del IDEAM.
Uso: /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I -B v6_segunda_pasada.py > salida_v6.txt
"""
# Implementacion independiente (no importa risk.py) del conteo de dias en alto 2025.
import pandas as pd, numpy as np, math, sys
B='/Users/santiagosantafe/Downloads/SabanaHack/datos/clima/cache/'
L=lambda z: 1/(1+math.exp(-z))
def g_w(T): return 0.33-0.069*T+0.005*T**2-9.3e-5*T**3
# minimo local de g
a,b,c=3*-9.3e-5,2*0.005,-0.069; r=sorted([(-b+s*math.sqrt(b*b-4*a*c))/(2*a) for s in (1,-1)]); TG=r[0]
def wilson(W,T): return L(-3.7+W*g_w(max(T,TG)))
anc=[(5,0.0),(10,3.7/42),(15,3.7/24),(20,3.7/15),(25,3.7/15),(30,3.7/21),(35,0.0)]
def g_a(T):
    xs,ys=zip(*anc); return float(np.interp(T,xs,ys))
def arand(W,T): return L(-3.7+W*g_a(T))
def bulger(W,T): return L(-4.268-0.0901*W+0.0294*W*T-2.35e-5*W*T**3)
def gim(W,T,tmin,topt,tmax,wmin,wmax):
    if T<tmin or T>tmax: return 0.0
    al=math.log(2)/math.log((tmax-tmin)/(topt-tmin)); x=T-tmin; xo=topt-tmin
    f=max(0,min(1,(2*x**al*xo**al-x**(2*al))/xo**(2*al)))
    if f<=0 or wmin/f>wmax: return 0.0
    I=W*f/wmin; return 0.15**(3.5*0.15**(0.75*I))
def run(p,hr=90,dT=0.0,tmin_roya=8.0):
    d=pd.read_csv(B+'historico_2025_%s.csv'%p); d=d[d.modelo=='best_match'].reset_index(drop=True)
    d['t']=pd.to_datetime(d.time); T=d.temperature_2m.values+dT
    wet=((d.relative_humidity_2m>=hr)|(d.precipitation>=0.5)).values
    best={}
    per=[]; cur=None; last=None
    for i in range(len(d)):
        if not wet[i]: continue
        if cur is not None and i-last-1>3: per.append(cur); cur=None
        if cur is None: cur=[]
        cur.append(i); last=i
    if cur: per.append(cur)
    for pp in per:
        n=0; s=0
        snap={}
        for i in pp:
            n+=1; s+=T[i]; snap[d.t[i].date()]=(n,s/n)
        for day,(W,Tm) in snap.items():
            v={'antracnosis':max(wilson(W,Tm),arand(W,Tm)),'botrytis':bulger(W,Tm),
               'roya':gim(W,Tm,tmin_roya,21.5,32,8,48)}
            for k,x in v.items(): best[(day,k)]=max(best.get((day,k),0),x)
    th={'antracnosis':0.5,'botrytis':0.7,'roya':0.5}
    return {k:sum(1 for (dy,kk),x in best.items() if kk==k and x>=th[k]) for k in th}, \
           sum(1 for (dy,kk),x in best.items() if kk=='botrytis' and x>=0.5)
import collections, json
PTS=['sotaquira','tausa','guasca','chia']
print('== Dias en alto (antracnosis, botrytis, roya) y botrytis>=0.50; criterio HR o lluvia>=0.5')
for hr in (90,85):
    for p in PTS:
        for dT in (-1,0,1):
            print(hr,p,dT,run(p,hr,dT))
print('== Estacionalidad HR90 (suma 4 puntos, dias-enfermedad en alto por mes)')
def mensual(p,dT):
    d=pd.read_csv(B+'historico_2025_%s.csv'%p); d=d[d.modelo=='best_match'].reset_index(drop=True)
    d['t']=pd.to_datetime(d.time); T=d.temperature_2m.values+dT
    wet=((d.relative_humidity_2m>=90)|(d.precipitation>=0.5)).values
    per=[];cur=None;last=None
    for i in range(len(d)):
        if not wet[i]: continue
        if cur is not None and i-last-1>3: per.append(cur); cur=None
        if cur is None: cur=[]
        cur.append(i); last=i
    if cur: per.append(cur)
    best={}
    for pp in per:
        n=0;s=0;snap={}
        for i in pp: n+=1;s+=T[i];snap[d.t[i].date()]=(n,s/n)
        for day,(W,Tm) in snap.items():
            v={'a':max(wilson(W,Tm),arand(W,Tm)),'b':bulger(W,Tm),'r':gim(W,Tm,8,21.5,32,8,48)}
            for k,x in v.items(): best[(day,k)]=max(best.get((day,k),0),x)
    th={'a':.5,'b':.7,'r':.5}
    return collections.Counter(day.month for (day,k),x in best.items() if x>=th[k])
for dT in (-1,0,1):
    tot=collections.Counter()
    for p in PTS: tot+=mensual(p,dT)
    s=sum(tot.values()); fm=sum(tot[m] for m in (2,3,4,5))
    print(dT,[tot[m] for m in range(1,13)],s,'feb-may %.0f%%'%(100*fm/s),'pico',tot.most_common(1))
print('== Regla de roya del equipo (19-25 C con mojadura prolongada) y QC/hora de la Tmin')
for p in PTS:
    d=pd.read_csv(B+'historico_2025_%s.csv'%p); d=d[d.modelo=='best_match'].reset_index(drop=True)
    wet=(d.relative_humidity_2m>=90)|(d.precipitation>=0.5); T=d.temperature_2m
    per=[];cur=[];last=None
    for i in d.index[wet]:
        if cur and i-last-1>3: per.append(cur); cur=[]
        cur.append(i); last=i
    if cur: per.append(cur)
    lg=[T[x].mean() for x in per if len(x)>=12]
    d['t']=pd.to_datetime(d.time); d['dia']=d.t.dt.date; d['h']=d.t.dt.hour
    fh=d.loc[d.groupby('dia').temperature_2m.idxmin()].h
    print(p,'n',len(d),'dup',int(d.time.duplicated().sum()),'h mojadas',int(wet.sum()),'T>=15',int((wet&(T>=15)).sum()),
          'T>=19',int((wet&(T>=19)).sum()),'periodos>=12h',len(lg),'max Tmedia %.1f'%max(lg),
          'Tmin moda',fh.mode().tolist(),'mediana',fh.median())
print('== IDEAM crudo: hora del minimo/maximo del ciclo medio de T (UTC si min ~10-11 h)')
R='/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/ideam_datosgov_2025/'
for cod in ['2120500135','2401500040','2403500041','0021205700','0024035430','0021205518']:
    d=pd.DataFrame(json.load(open(R+'temperatura_%s_2025.json'%cod)))
    d['t']=pd.to_datetime(d.fechaobservacion); d['v']=pd.to_numeric(d.valorobservado,errors='coerce')
    h=d.groupby(d.t.dt.floor('h')).v.mean(); cyc=h.groupby(h.index.hour).mean()
    print(cod,d.nombreestacion.iloc[0],'hora_min',cyc.idxmin(),'hora_max',cyc.idxmax())
print('== Puntos de referencia NCSU')
print('Wilson 26.6C',[round(wilson(w,26.6),3) for w in (7.0,13.1,20.9)],'0C 20.9h',round(wilson(20.9,0),3))
print('Bulger 20.5C',[round(bulger(w,20.5),3) for w in (13.8,16.5,20.8)])
