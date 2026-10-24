import sys; sys.path.insert(0,'/Users/santiagosantafe/Downloads/SabanaHack/datos/riesgo')
import risk as r
for p in ['sotaquira','tausa','guasca','chia']:
    hs=r.horas_desde_csv('/Users/santiagosantafe/Downloads/SabanaHack/datos/clima/cache/historico_2025_%s.csv'%p,{'modelo':'best_match'})
    a={}
    for hr in (90,85):
        d=r.resumen_diario(hs,r.ConfigMojadura(umbral_hr=hr,umbral_lluvia_mm=0.5))
        a[hr]={x['fecha'] for x in d if any(x['clase_'+e]=='alto' for e in ('antracnosis','botrytis','roya'))}
    u=a[90]|a[85]
    def ep(s):
        s=sorted(s); return sum(1 for i,x in enumerate(s) if i==0 or (x-s[i-1]).days>1)
    print(p,'HR90',len(a[90]),ep(a[90]),'HR85',len(a[85]),ep(a[85]),'union',len(u),ep(u),'HR90 no en HR85',len(a[90]-a[85]))
