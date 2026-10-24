S = {"A":[3,5,3,4,3,4],"B":[5,1,5,5,4,2],"C":[2,4,5,3,3,3],"D":[2,4,1,1,1,4],"E":[3,5,2,4,3,4],"F":[5,5,3,4,3,5]}
def tot(w): return {k: round(sum(s*x for s,x in zip(v,w))/5,1) for k,v in S.items()}
print("Base [20,20,20,15,15,10]:", tot([20,20,20,15,15,10]))
print("Doc sens [20,15,30,15,10,10]:", tot([20,15,30,15,10,10]))
for name,w in [("costo30 quitando 10 a ubicacion",[20,10,30,15,15,10]),("costo30 -5 anticipa -5 ubica",[15,15,30,15,15,10]),("costo30 -5 robustez -5 registro",[20,20,30,15,10,5]),("costo30 -10 anticipa",[10,20,30,15,15,10]),("costo40 -10 ubica -10 robustez",[20,10,40,15,5,10])]:
    t=tot(w); print(name, w, "B",t["B"],"F",t["F"])
print("F con Costo=2:", tot([20,20,20,15,15,10]) and round((5*20+5*20+2*20+4*15+3*15+5*10)/5,1))
def B(Y,P,L,f,n,C,J,w): return Y*P*L*f + n*C + J*w, Y*P*L*f
for lab,args in [("pes",(12000,4,.03,.10,0,60,0,19)),("base",(12000,6,.08,.25,2,100,10,19)),("opt",(12000,8,.15,.40,4,150,20,19))]:
    b,lf=B(*args); print(lab,"B=",round(b),"parte L*f=",round(100*lf/b,1),"%")
trm=3185.01; w=75900/trm; print("jornal USD con TRM real", round(w,2), "SMMLV/30*1.3=", round(1750905/30*1.3))
b,_=B(12000,6,.08,.25,2,100,10,w); print("B base con TRM real", round(b))
b,_=B(9070,6,.08,.25,2,100,10,19); print("B base con Y=9,07 t/ha EVA", round(b), "ROI hibrido",(b-430)/430)
b,_=B(12000,8,.08,.25,2,100,10,19); print("B base con P=8", round(b))
for c,lab in [(320,"A"),(430,"F")]: print("ROI neto",lab, round((1830-c)/c,2), "ROI bruto", round(1830/c,2))
for c in [320,110,90,430,2100,700,2200,650,440]: print("cost",c,"eq kg",round(c/6,1),"% de 12t",round(100*c/6/12000,2))
print("Gestion precio implicito", 2457e6/373514e3)
print("Agraria 261000/16850", 261000/16850)
print("Factor import", 1.08*1.05*1.19)
for m,f in [("D1 Pro",3199),("D1 EDU",5999),("D1 Ultra",7499),("Ultra-W",11699),("Max",47999),("MaxPro",67999),("X2",23999),("X2U",39999),("A3L",54999),("A3U",74999),("G1",75199),("G2",110500),("C5",19740)]: print(m, round(f*1.35))
print("Bateria años", 300/365, 500/365)
print("FA/FN", 2160/30, 2160/105, 12000*0.03*6)
# MaxPro reproduce
for lab,capex,om,ha in [("MaxPro 20ha",91800+1500,3250,20),("MaxPro 60ha",91800+1500,3250,60),("Genie G1",101500+1500,3250,20),("Ultra",11600,2533,20)]:
    print(lab, round((capex/3+om)/ha))
print("pesos humanoides/D1", {k: round(v/15.5,2) for k,v in {"X2":33,"X2U":39,"A2":69,"UG1":35,"H1":47,"T1":30,"K1":19.5,"NAO":5.5}.items()})
print("precio humanoides/D1EDU", {k: round(v/5999,1) for k,v in {"X2":23999,"X2U":39999,"A3L":54999,"A3U":74999,"UG1":16000,"H1":90000,"NAO17":17000,"NAO19":19000}.items()})
print("IP67/D1EDU", {k: round(v/5999,1) for k,v in {"Max":47999,"MaxPro":67999,"X30a":85000,"X30b":99000,"ANYmal":150000,"B2hi":100000}.items()})
print("Ultra vs EDU ahorro USD/ha/año", round((10100-8100)/3/20,1))
