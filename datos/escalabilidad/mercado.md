# Mercado y go-to-market: monitoreo de enfermedades cama por cama para berries

Rol: mercado-go-to-market · Sabana Hack, reto "Berry Good Idea" · Fecha: 2026-10-23

**Para qué sirve este documento:** muestra a quién puede vender la organización la solución (sensores + modelos de riesgo + cuadrúpedo + alerta + registro), cuántas hectáreas hay, por dónde entrar y qué puede salir mal. El clima de la Sabana de Bogotá es solo el caso de la demo. El producto se diseña para venderse a muchos productores, en varios países y en otros frutales.

**Cómo leer las cifras**
- Cada dato lleva su fuente. Todas las URL de la sección 11 se abrieron en esta sesión.
- **SUPUESTO** = decisión del equipo, no es un dato publicado.
- **NO VERIFICADO** = solo se vio en resultados de búsqueda, sin abrir la página, o la fuente no da el dato exacto.
- Las cifras de TAM, SAM y SOM se calculan con `escalabilidad/mercado/calc_mercado.py` (`python3 -I calc_mercado.py`). Los datos EVA que usa están guardados en la misma carpeta.

---

## 0. Resumen en 6 puntos

1. **El mercado de arándano está fuera de Colombia.** Perú tiene 26.786 ha, Chile entre 14.000 y 18.000 ha, México unas 11.000 ha y Colombia unas 1.000 ha. Colombia es menos del 2 % de las ~54.500 ha de los cuatro países.
2. **Colombia sirve para el piloto, no para el volumen.** El cultivo está concentrado: el 94 % del área está en Boyacá y Cundinamarca, y 10 municipios suman el 68 %. Asocolblue reúne a 28 productores. La mano de obra pesa el 70 % del costo. Se cultiva bajo invernadero con techo antigranizo. Todo esto hace que el piloto sea barato y fácil de mostrar.
3. **Fresa y mora en Colombia suman 19.719 ha**, 22 veces el arándano, pero tienen otra economía. El plan con robot (430 USD/ha/año) exige salvar 3,5 % de la cosecha de mora, así que la mora necesita un plan sin robot (**Vigía**, SUPUESTO 60 USD/ha/año), que se paga con 0,5 % de la cosecha.
4. **TAM ≈ 26 M USD/año** (74.205 ha). **SAM ≈ 7,9 M USD/año** (20.415 ha). **SOM a 5 años ≈ 0,45 M USD/año** (1.242 ha, unos 50 robots). Los porcentajes de SAM y SOM son SUPUESTOS.
5. **El negocio se decide en las cuentas grandes de Perú.** Los pequeños (5–50 ha) producen el 30 % del arándano peruano; el otro ~70 % sale de empresas medianas y grandes, y las grandes tienen más de 1.000 ha. Una sola cuenta de 1.000 ha en el plan Centinela vale lo mismo que todo el SOM base.
6. **Para escalar hay que vender por canales, no finca por finca:** gremios (Asocolblue, ProArándanos, Comité de Arándanos, Aneberries), Asohofrucol para fresa y mora, y distribuidores e integradores locales. El producto se configura por cultivo y región, no se reprograma.

---

## 1. Tamaño del mercado

### 1.1 Superficie por país y cultivo

| País / cultivo | Superficie (ha) | Año | Tipo de cifra | Fuente |
|---|---:|---|---|---|
| Colombia, arándano | 906,7 sembradas (664,7 cosechadas) | 2025 | Oficial (EVA, MADR/UPRA) | [datos.gov.co EVA uejq-wxrr](https://www.datos.gov.co/resource/uejq-wxrr.json) |
| Colombia, arándano | ~1.000 (proyección ~1.200 en 2026) | 2025 | Gremio (Asocolblue) | [El Colombiano, 2026-02-05](https://www.elcolombiano.com/negocios/arandanos-en-colombia-cultivos-expansion-FA33220603); [Portal Frutícola, 2026-04-06](https://www.portalfruticola.com/?p=614315) |
| Colombia, fresa | 3.767 | 2025 | Oficial (EVA) | [datos.gov.co EVA](https://www.datos.gov.co/resource/uejq-wxrr.json) |
| Colombia, mora | 15.952 | 2025 | Oficial (EVA) | [datos.gov.co EVA](https://www.datos.gov.co/resource/uejq-wxrr.json) |
| Colombia, uchuva (adyacente) | 1.810 | 2025 | Oficial (EVA) | [datos.gov.co EVA](https://www.datos.gov.co/resource/uejq-wxrr.json) |
| Colombia, aguacate (adyacente, frutal de árbol) | 141.051 | 2025 | Oficial (EVA) | [datos.gov.co EVA](https://www.datos.gov.co/resource/uejq-wxrr.json) |
| Perú, arándano | 26.786 cultivadas; 23.344 certificadas por SENASA | Campaña 2025-26 | Gremio (ProArándanos) + SENASA | [Agraria.pe, 2026-03-26](https://agraria.pe/noticias/peru-cuenta-con-23-344-hectareas-certificadas-de-arandanos-p-41924) |
| Perú, arándano | >27.000 en producción (+~3.000 nuevas) | Campaña 2026-27 | Gremio | [ProArándanos, junio 2026 (PDF)](https://cdn.freshfruitportal.com/2026/06/Proarandanos-statement-on-2026-season-projections.pdf) |
| Chile, arándano | ~14.000 (Odepa) / ~15.700 (Comité) | 2025 | Oficial / gremio | [Revista Economía, 2025-10-30](https://www.revistaeconomia.com/?p=111222) |
| Chile, arándano | 18.071 plantadas | 2023 | Gremio (Comité de Arándanos, Asoex, iQonsulting) | [Portal Frutícola, 2023-10-04](https://www.portalfruticola.com/noticias/2023/10/04/chile-campana-23-24-de-arandanos-llegaria-a-82-mil-toneladas/) |
| México, arándano | 11.000 plantadas (2024-25); 7.648 registradas a la fecha en 2025-26 | 2024-26 | Gremio (panel Aneberries) | [FreshPlaza, 2025-11-27](https://www.freshplaza.com/latin-america/article/9788676/mexico-targets-91-700-ton-blueberry-output-for-2025-2026/) |
| México, todos los berries | 48.000–50.000 | 2025 | Gremio (Aneberries) | [Agraria.pe, 2025-06-27](https://agraria.pe/noticias/exportadores-preven-que-mexico-tenga-ventas-record-de-fresas-39928) |

### 1.2 Colombia en detalle (EVA 2025, consulta API del 2026-10-23)

| Indicador | Arándano | Fresa | Mora |
|---|---:|---:|---:|
| Área sembrada 2025 (ha) | 907 | 3.767 | 15.952 |
| Producción 2025 (t) | 6.031 | 103.669 | 153.988 |
| Rendimiento (t/ha cosechada) | 9,1 | 30,1 | 10,0 |
| Área 2019 → 2025 | 265 → 907 (×3,4; ~23 %/año) | 2.905 → 3.767 | 16.495 → 15.952 (máximo 17.914 en 2020) |
| Departamentos principales 2025 (ha) | Boyacá 437, Cundinamarca 420, Antioquia 41 | Cundinamarca 1.605, Antioquia 625, Cauca 577, N. Santander 376, Boyacá 324 | Cundinamarca 3.989, Santander 3.087, Huila 1.667, Nariño 1.474, Boyacá 1.415 |
| Municipios con registro | 65 (31 con ≥5 ha) | 127 registros municipio-año | 305 registros municipio-año |

**Concentración del arándano (EVA 2025):** 10 municipios suman el 68 % del área nacional: Sotaquirá 182 ha, Tausa 121, Cómbita 85, Ventaquemada 59, Guasca 57, Sopó 31, Chocontá 25, Guatavita 21, Tenjo 19 y Entrerríos 19. Así, un piloto y un técnico de campo en el altiplano cundiboyacense cubren la mayor parte del mercado colombiano.

**Lo que dice el gremio sobre el arándano colombiano** ([Agronegocios, 2026-02-11](https://www.agronegocios.co/agricultura/el-arandano-crece-pero-lejos-de-su-potencial-exportador-4321623); leído de la copia local `datos/raw/paramsim_agronegocios_arandano/text.txt`):
- Asocolblue agrupa a 28 productores.
- La mano de obra pesa el 70 % de los costos de producción. Por eso automatizar el recorrido de monitoreo toca el costo principal.
- Para empezar se necesitan al menos 1.200 millones de COP, con invernadero antigranizo y antipájaros de unos 400 millones de COP. El robot trabaja bajo cubierta, donde ni el satélite ni el dron ven la hoja.
- "Solo hay dos empresas que exportan por mar de manera constante". El 95 % de la producción se consume en el país ([Forbes Colombia, 2026-05-04](https://forbes.co/economia-y-finanzas/colombia-consume-el-95-de-su-produccion-de-arandanos-y-busca-crecer-en-exportaciones)).
- El potencial que estima el gremio es de 5.000 a 10.000 ha.

### 1.3 Productores y tamaño típico de finca

| País | Productores / empresas | Tamaño típico | Estructura | Fuente |
|---|---|---|---|---|
| Colombia (arándano) | ~200 agricultores (2023); 28 en Asocolblue (2026) | Proyectos de 5 a 30 ha; en 2023 los 28 socios tenían 200–250 ha (~7–9 ha cada uno, cálculo propio) | Pocas empresas tecnificadas y algunos pequeños asociados | [Agronegocios, 2023-06-14](https://www.agronegocios.co/agricultura/arandanos-un-mercado-que-llegaria-a-us-3-000-millones-en-exportaciones-para-2025-3636243); [El Colombiano, 2026-02-05](https://www.elcolombiano.com/negocios/arandanos-en-colombia-cultivos-expansion-FA33220603) |
| Colombia (mora) | Pequeños y medianos productores (no se encontró un número) | NO VERIFICADO | Atomizada, con intermediación; pérdidas de 8 a 15 % en la comercialización | [DANE SIPSA semanal 13–19 jun 2026](https://www.dane.gov.co/files/operaciones/SIPSA/bol-SIPSASemanal-13jun19jun-2026.pdf) |
| Perú | 207 empresas exportadoras (2025; ~170 en 2024) | Pequeños de 5–50 ha = 30 % de la producción; grandes >1.000 ha | Muy concentrada en grandes agroexportadoras de La Libertad y Lambayeque | [Portal Frutícola, 2026-01-15](https://www.portalfruticola.com/?p=610281); [Agraria.pe, 2024-09-27](https://agraria.pe/noticias/el-30-de-la-produccion-de-arandanos-de-peru-proviene-de-pequ-37145) |
| Chile | No se encontró un número oficial de productores | NO VERIFICADO | En recambio de variedades: las nuevas serían el 35 % de lo exportado en 2025-26 | [Revista Economía, 2025-10-30](https://www.revistaeconomia.com/?p=111222) |
| México | Aneberries: 40 asociados, que producen el 75–80 % de los berries del país | NO VERIFICADO | Dominada por integradoras (Driscoll's, Hortifrut, Sun Belle, entre otras) y viveros (Fall Creek, Planasa) | [Agraria.pe, 2024-05-20](https://agraria.pe/noticias/volumen-de-produccion-de-berries-de-mexico-caeria-20-este-35776); [FreshPlaza, 2025-11-27](https://www.freshplaza.com/latin-america/article/9788676/mexico-targets-91-700-ton-blueberry-output-for-2025-2026/) |

**Regiones donde entrar en cada país**
- Perú: La Libertad (11.480 ha, 42,9 %), Lambayeque (7.112), Ica (3.643), Lima (1.671), Áncash (1.472) y Piura (1.226) ([Agraria.pe](https://agraria.pe/noticias/peru-cuenta-con-23-344-hectareas-certificadas-de-arandanos-p-41924)).
- México: Jalisco (3.663 ha), Michoacán (1.374), Sinaloa (759) y Baja California (712), con datos de 2025-26 a la fecha ([FreshPlaza](https://www.freshplaza.com/latin-america/article/9788676/mexico-targets-91-700-ton-blueberry-output-for-2025-2026/)).
- Chile: Ñuble tiene 3.250 ha, el 23 % del país ([Portal Frutícola, 2026-01-15](https://www.portalfruticola.com/?p=610283)). Maule y Biobío fueron las regiones principales en catastros anteriores (NO VERIFICADO para 2025).

### 1.4 Cifras que no cuadran entre fuentes (para no equivocarse en el pitch)

| Tema | Fuente A | Fuente B | Qué usamos |
|---|---|---|---|
| Área de arándano en Colombia | EVA 2025: 907 ha | Gremio: ~1.000 ha | Rango 907–1.000; la cifra central es 1.000 |
| Producción de arándano en Colombia | EVA 2025: 6.031 t | Forbes: 12.000 t; vicepresidente de Asocolblue: ~20.000 t | No se usa en el TAM; se cita como rango |
| Área en Perú | 23.344 certificadas | 26.786 cultivadas; >27.000 en producción en 2026-27 | Central 26.786 |
| Área en Chile | Odepa ~14.000 | Comité ~15.700 (2025) y 18.071 (2023). Ñuble 3.250 = 23 % implica ~14.100 | Central 15.700 |
| Área en México | 7.648 registradas a la fecha (2025-26) | 11.000 plantadas (2024-25) | Central 11.000 |
| Precio del D1 Ultra | Tienda oficial: **9.600 USD** + envío + aranceles ([store.agibot.com](https://store.agibot.com/products/d1-ultra), 2026-10-23) | Dato del equipo: ~7.499 USD FOB México | Confirmar con finanzas: cambia el costo por ha |

---

## 2. Qué vende la organización y a qué precio

### 2.1 Tres planes sobre la misma plataforma (SUPUESTO de diseño)

| Plan | Qué incluye | Para quién | Precio (SUPUESTO) |
|---|---|---|---|
| **Vigía** | Red de sensores ambientales, modelos de riesgo (antracnosis, Botrytis, roya), alertas, registro de incidencias y scouting asistido con el celular del operario | Mora, fresa a campo abierto, pequeños asociados, otros frutales | 60 USD/ha/año |
| **Centinela** | Vigía + cuadrúpedo propio (D1 Ultra) que recorre camas, clasificador visual, mapa de calor, triage agrónomo → operario y aspersión dirigida | Arándano tecnificado y fresa en macrotúnel, de 5 a 50 ha | 430 USD/ha/año (cifra de costo del equipo, finca de 20 ha) |
| **Flota** | Centinela operado como servicio, con robot IP67 compartido (D1 MaxPro, ~60 ha por equipo), contrato por ha. **Advertencia de la verificación (2026-10-23):** el MaxPro solo como inspector no se paga (margen -32 % en `modelo_negocio.md`; ROI 0,08 en finanzas, opción G), y `operacion.md` le da 26 ha, no 60, en su escenario base. Flota debería operar con una flota de D1 Ultra repartida entre fincas. El MaxPro queda solo si además aplica producto | Agroexportadoras grandes (Perú, Chile, México) | Por ha y por contrato (a definir con finanzas) |

**Referencias de precio del mercado**
- Una licencia de modelo de enfermedad de Metos cuesta **96 EUR por cultivo y por año**, sin la estación ([shop.metos.at](https://shop.metos.at/products/disease-model-license-for-1-year)).
- Saga Robotics cobra una **tarifa fija por hectárea** por el servicio con robot y no vende el robot ([Future Farming, 2021-12-22](https://www.futurefarming.com/tech-in-focus/field-robots/robot-combats-powdery-mildew-in-strawberries-using-uv-c-treatment/)).

### 2.2 ¿Cuánta cosecha hay que salvar para pagar el plan? (punto de equilibrio)

TRM: 3.185,01 COP/USD, vigente el 2026-10-23 ([datos.gov.co TRM 32sa-8pi3](https://www.datos.gov.co/resource/32sa-8pi3.json)).

| Cultivo | Precio al productor usado | Rendimiento (EVA 2025) | Equilibrio Centinela (430 USD) | Equilibrio Vigía (60 USD) |
|---|---|---:|---|---|
| Arándano | ~6 USD/kg (implícito en los 72 kg del equipo). El precio medio de exportación de Perú en 2025 fue 6,22 USD/kg ([Portal Frutícola](https://www.portalfruticola.com/?p=610281)) | 9,1 t/ha (el equipo usa 12 t/ha) | **72 kg/ha = 0,6–0,8 %** | 10 kg/ha = 0,1 % |
| Fresa | 4.563 COP/kg mayorista en Corabastos (semana 13–19 jun 2026, [SIPSA](https://www.dane.gov.co/files/operaciones/SIPSA/bol-SIPSASemanal-13jun19jun-2026.pdf)) × 60 % en finca (SUPUESTO por analogía con la mora) = 0,86 USD/kg | 30,1 t/ha | 500 kg/ha = 1,7 % | 70 kg/ha = 0,2 % |
| Mora | 6.896 COP/kg mayorista en Corabastos (19 jun 2026, [SIPSA diario](https://www.dane.gov.co/files/operaciones/SIPSA/bol-SIPSADiario-19jun2026.pdf)) × 57 % en finca (Bogotá, [SIPSA semanal, tabla 1](https://www.dane.gov.co/files/operaciones/SIPSA/bol-SIPSASemanal-13jun19jun-2026.pdf)) = 1,23 USD/kg | 10,0 t/ha | 349 kg/ha = **3,5 %** (difícil) | **49 kg/ha = 0,5 %** |

*Advertencia de la verificación (2026-10-23):* los equilibrios de esta tabla solo cuentan la suscripción y dejan fuera el kit de sensores. En una finca pequeña de mora, el kit (nodos más gateway y estación compartidos) le cuesta al productor unos 98 USD/ha/año según `unit_economics.py`. Con Vigía a 60 USD/ha sin mínimo por finca, el equilibrio real sube a ~1,3 % de la cosecha, el ROI queda en ~1,1x y el vendedor pierde 7 %. Para mora, el plan Vigía tiene que llevar casi nada de hardware por finca: una estación virtual o una estación compartida por la asociación, más el celular.

**Conclusión:** el robot se paga en arándano y, con algo más de margen, en fresa tecnificada. En mora, la oferta escalable es el plan Vigía. Los precios de SIPSA son de un día o de una semana y la mora subió 10 % ese mismo día, así que el equilibrio varía con el mercado.

---

## 3. TAM, SAM y SOM

**Definiciones**
- **TAM:** valor anual si toda el área usara el plan que le corresponde.
- **SAM:** la parte del TAM que el producto y los canales planeados alcanzan en 5 años.
- **SOM:** la cuota que es realista ganar al cerrar la etapa 3.

### 3.1 TAM (superficie central × precio del plan)

| Segmento | ha bajo | ha central | ha alto | Plan | USD/ha/año | TAM central (USD/año) |
|---|---:|---:|---:|---|---:|---:|
| Arándano Colombia | 907 | 1.000 | 1.200 | Centinela | 430 | 430.000 |
| Arándano Perú | 23.344 | 26.786 | 27.000 | Centinela | 430 | 11.517.980 |
| Arándano Chile | 14.000 | 15.700 | 18.071 | Centinela | 430 | 6.751.000 |
| Arándano México | 7.648 | 11.000 | 11.000 | Centinela | 430 | 4.730.000 |
| Fresa Colombia | 3.767 | 3.767 | 3.767 | Centinela | 430 | 1.619.672 |
| Mora Colombia | 15.952 | 15.952 | 15.952 | Vigía | 60 | 957.112 |
| **Total** | | **74.205** | | | | **≈ 26,0 M** |

Sensibilidad del TAM de arándano en los 4 países: escenario bajo 45.899 ha (19,7 M USD/año), central 54.486 ha (23,4 M) y alto 57.271 ha (24,6 M).

### 3.2 SAM y SOM (todos los porcentajes son SUPUESTO)

| Segmento | % SAM | Por qué ese filtro | ha SAM | USD SAM/año | % SOM (del SAM) | ha SOM | USD SOM/año | Robots (20 ha c/u) |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| Arándano Colombia | 80 % | Casi todo es tecnificado; se excluyen lotes muy pequeños | 800 | 344.000 | 30 % | 240 | 103.200 | 12 |
| Arándano Perú | 30 % | Productores de 5–50 ha, que Midagri llama "pequeños" (30 % de la producción, usado como proxy del área) | 8.036 | 3.455.394 | 5 % | 402 | 172.770 | 20 |
| Arándano Chile | 35 % | Huertos en recambio de variedades (nueva inversión) | 5.495 | 2.362.850 | 3 % | 165 | 70.886 | 8 |
| Arándano México | 25 % | Mercado dominado por integradoras con agronomía propia | 2.750 | 1.182.500 | 2 % | 55 | 23.650 | 3 |
| Fresa Colombia | 25 % | Fresa en macrotúnel o sustrato | 942 | 404.918 | 15 % | 141 | 60.738 | 7 |
| Mora Colombia | 15 % | Productores en asociaciones (vía Asohofrucol o gobernaciones) | 2.393 | 143.567 | 10 % | 239 | 14.357 | 0 |
| **Total** | | | **20.415** | **≈ 7,9 M** | | **1.242** | **≈ 0,45 M** | **≈ 50** |

**Qué se lee en estas tablas**
- **El SOM base es pequeño, unos 0,45 M USD/año.** Es honesto decirlo, porque muestra que no basta con ir finca por finca. Tres fuentes de crecimiento quedan fuera del SOM base:
  1. **Cuentas grandes en Perú (plan Flota).** El ~70 % del arándano peruano que no producen los pequeños sale de empresas medianas y grandes; las grandes superan las 1.000 ha. Una cuenta de 1.000 ha a 430 USD equivale a 430.000 USD/año, casi todo el SOM base.
  2. **Plan Vigía en otros frutales.** Por ejemplo, 1 % de los 141.051 ha de aguacate de Colombia son 1.410 ha × 60 = ~85.000 USD/año.
  3. **Datos agregados** para aseguradoras y exportadoras (ver la sección 5).
- **Costo del robot.** Cada robot Centinela factura 20 ha × 430 = 8.600 USD/año. El D1 Ultra cuesta 9.600 USD de lista, sin envío ni aranceles. El hardware del robot se recupera en ~1,1 años, sin contar sensores, soporte ni nube. Finanzas tiene que confirmar que los 430 USD/ha cubren todo eso más el margen.
  - *Respuesta de la verificación (2026-10-23): no los cubren.* El robot puesto en finca cuesta 7.084 USD/año, contando depreciación, mantenimiento, seguro y unas 4,3 baterías (`unit_economics.py`, tabla 2). Con 430 USD/ha y 20 ha por robot, el vendedor pierde 60 % con robots enteros y 20 % con la flota repartida. Además, finanzas calcula hoy que el híbrido le cuesta al productor 722 USD/ha/año en una finca de 20 ha (`finanzas/tabla_final_20ha.csv`, opción F); los 430 USD/ha son una cifra anterior del equipo. Hay que usar el precio con costo calculado de `modelo_negocio.md`: 520 USD/ha con robot y 130 USD/ha sin robot. Con esos precios y 35,8 ha por robot, el TAM sube a ~32,4 M USD/año, el SAM a ~9,7 M USD/año y el SOM a ~0,55 M USD/año, con unos 28 robots.

---

## 4. Segmentos: quién decide, qué le duele y qué compra

| Segmento | Quién decide | Dolor principal | Qué compra | Canal de entrada |
|---|---|---|---|---|
| Arándano tecnificado en Colombia (5–30 ha, bajo cubierta) | Dueño o gerente con su agrónomo | Mano de obra (70 % del costo) y pérdidas por focos que se ven tarde | Centinela | Asocolblue (28 productores) y Nación Berries |
| Fresa tecnificada en Colombia | Productor y asistente técnico | Oídio y Botrytis; mano de obra | Centinela o Vigía | Asohofrucol, distribuidores de insumos en Cundinamarca y Antioquia |
| Mora en Colombia (pequeños) | Asociación de productores | Pérdidas de 8–15 % y hongos en poscosecha (SIPSA); poca asistencia técnica | Vigía, compartido por la asociación | Asohofrucol/FNFH, gobernaciones, programas públicos |
| Productores de 5–50 ha en Perú | Productor que vende a exportadora | Calidad exigida por la exportadora y riesgo climático (El Niño) | Centinela | ProArándanos, exportadoras compradoras |
| Agroexportadoras grandes (Perú, Chile, México) | Gerencia agrícola o de innovación | Escala del monitoreo, trazabilidad, cumplimiento de certificaciones | Flota (RaaS) y API hacia su ERP | Venta directa con piloto pagado; integradoras y viveros |
| Huertos en recambio en Chile | Productor que invierte en variedades nuevas | Proteger la inversión nueva; lluvias (Botrytis) | Centinela | Comité de Arándanos (Frutas de Chile), INIA |

---

## 5. Canales y aliados

| Actor | País | Qué aporta | Qué gana | Dato y verificación |
|---|---|---|---|---|
| **Asocolblue** | CO | Acceso a los 28 productores principales, comités técnicos y feria Nación Berries (con Agrilink; 2.ª edición el 20 y 21 de mayo de 2026 en Bogotá) | Herramienta de competitividad para exportar | [Agronegocios 2026](https://www.agronegocios.co/agricultura/el-arandano-crece-pero-lejos-de-su-potencial-exportador-4321623), [Portal Frutícola](https://www.portalfruticola.com/?p=614315) |
| **Asohofrucol / FNFH** | CO | Asistencia técnica para fresa, mora y otras frutas, con recursos parafiscales (Ley 118 de 1994) | Herramienta digital para sus agrónomos | NO VERIFICADO (solo resultados de búsqueda). Hay noticias de 2026 sobre una disputa por la administración del fondo, por lo que conviene no depender solo de este canal |
| **Gobernación de Cundinamarca** | CO | Programa de arándano en 12 municipios (>553 M COP) | Resultados medibles en sus programas | NO VERIFICADO (la página respondió 402) |
| **AGROSAVIA** | CO | Validación agronómica independiente y datos de enfermedades (trabaja en mora andina) | Transferencia de tecnología | NO VERIFICADO: no se encontró un proyecto suyo de arándano |
| **UPTC y universidades** | CO | Caracterización de patologías del arándano en el trópico alto | Datos y publicaciones | NO VERIFICADO (estudio visto en búsqueda) |
| **ICA** | CO | Registro de lugares de producción para exportación (Res. 824 de 2022, que derogó la 448 de 2016) | Informes de monitoreo de plagas de mejor calidad | [Compilación ICA, Res. 448 (derogada)](https://compilacionmsf.ica.gov.co:4443/compilacion/docs/pdf/resolucion_ica_0448_2016.pdf). El detalle de la 824 está NO VERIFICADO |
| **FINAGRO + aseguradoras** | CO | Incentivo al Seguro Agropecuario 2025: subsidio a la prima de 80 % para pequeños y 30 % para medianos; 128.000 M COP | Datos de riesgo por finca para tarificar o hacer seguros paramétricos | [Agronegocios, 2025-05-16](https://www.agronegocios.co/agricultura/habilitan-128-000-millones-para-que-campesinos-aseguren-sus-cultivos-ante-fenomenos-climaticos-4135544). La lista de aseguradoras (Mapfre, Sura, Previsora, Bolívar, Allianz) está NO VERIFICADA |
| **Distribuidores de agroquímicos** | Todos | Fuerza de venta en campo, instalación y crédito al productor | La aspersión dirigida orienta la compra de producto; recomendaciones con datos | SUPUESTO. Ojo: Syngenta tiene su propio perro robot en desarrollo (sección 8) |
| **Exportadoras** | CO, PE | Pueden exigir monitoreo a sus proveedores y cofinanciarlo | Trazabilidad y menos rechazos | En Perú hay 207 exportadoras ([Portal Frutícola](https://www.portalfruticola.com/?p=610281)) |
| **ProArándanos** | PE | Gremio de productores y exportadores; consolida cada semana la información de sus socios | Alerta climática y de riesgo (El Niño) | [ProArándanos, 2026](https://cdn.freshfruitportal.com/2026/06/Proarandanos-statement-on-2026-season-projections.pdf) |
| **SENASA** | PE | Certifica 23.344 ha para exportación | Registro de campo estandarizado | [Agraria.pe](https://agraria.pe/noticias/peru-cuenta-con-23-344-hectareas-certificadas-de-arandanos-p-41924) |
| **Comité de Arándanos (Frutas de Chile)** e **INIA** | CL | Gremio técnico y ensayos de campo | Apoyo al recambio de variedades | [Revista Economía](https://www.revistaeconomia.com/?p=111222), [Portal Frutícola](https://www.portalfruticola.com/?p=610283) |
| **Aneberries** | MX | 40 asociados que producen el 75–80 % de los berries mexicanos | Herramienta de sanidad para sus socios | [Agraria.pe, 2024-05-20](https://agraria.pe/noticias/volumen-de-produccion-de-berries-de-mexico-caeria-20-este-35776) |
| **Viveros e integradoras** (Fall Creek, Planasa, Driscoll's, Hortifrut) | MX, PE, CL | Llegan a cientos de productores con paquete técnico | Mejor desempeño de su genética y de sus proveedores | Aparecen en el [panel Aneberries](https://www.freshplaza.com/latin-america/article/9788676/mexico-targets-91-700-ton-blueberry-output-for-2025-2026/). Su interés es SUPUESTO |

---

## 6. Estrategia en 3 etapas

| | Etapa 1: Piloto que demuestra | Etapa 2: Colombia comercial y otros berries | Etapa 3: Exportar el modelo |
|---|---|---|---|
| **Cuándo** | Meses 0–9 | Meses 9–30 | Meses 24–60 |
| **Dónde** | Altiplano cundiboyacense: 2 fincas de arándano (una en Cundinamarca, p. ej. Tausa, Guasca o Sopó; otra en Boyacá, p. ej. Sotaquirá o Cómbita) y 1 de fresa en Cundinamarca | Boyacá y Cundinamarca (arándano, fresa); mora en Cundinamarca y Santander; Antioquia | 1.º Perú (La Libertad, Lambayeque); 2.º Chile (Ñuble, Maule, Biobío); 3.º México (Jalisco, Michoacán) |
| **Qué se instala** | D1 EDU → 1–2 D1 Ultra; red de sensores; plataforma con triage y registro | 15–25 fincas Centinela (~380 ha de arándano y fresa); Vigía en ~240 ha de mora | Socio local por país; 1 piloto Flota con una agroexportadora grande |
| **Precio** | Gratis o con costo compartido, a cambio de datos etiquetados y carta de intención | Lista (Centinela 430, Vigía 60 USD/ha/año; SUPUESTO) | Por ha; contrato anual Flota |
| **Canal** | Asocolblue (presentación en Nación Berries) | Asocolblue, Asohofrucol, 1 distribuidor de insumos como revendedor e instalador | ProArándanos, Comité de Arándanos, Aneberries; integradoras y viveros |
| **Qué se aprende o construye** | Precisión real de alertas; días de anticipación frente al scouting humano; costo operativo por ha | Kit de instalación estándar; módulo de informe ICA (Res. 824 de 2022); piloto de datos con aseguradora | Recalibrar modelos al clima local (costa desértica peruana, lluvias del sur de Chile); clasificador con imágenes locales |
| **Se pasa a la siguiente etapa si** (SUPUESTO) | ≥70 % de alertas confirmadas por agrónomo; detección ≥3 días antes en ≥50 % de los focos; ≥90 % de las camas recorridas cada semana; robot operativo ≥85 % del tiempo; ≥2 cartas de intención | ≥600 ha pagando; retención anual ≥80 %; costo de soporte ≤20 % del ingreso | Piloto Flota convertido en contrato; margen bruto positivo por país |

**¿Por qué Perú primero en la etapa 3?** Tiene el área más grande (26.786 ha), cada año suma unas 3.000 ha nuevas, el arándano peruano es el 56 % de las importaciones de arándano fresco de EE. UU. ([Portal Frutícola, 2026-04-28](https://www.portalfruticola.com/?p=615425)) y su propio gremio advierte de un "elevado nivel de incertidumbre" climático para 2026-27 ([ProArándanos](https://cdn.freshfruitportal.com/2026/06/Proarandanos-statement-on-2026-season-projections.pdf)).

El riesgo de enfermedad en la costa desértica es distinto al de la Sabana: hay menos lluvia y más estrés por calor. Por eso el paquete de modelos de Perú hay que validarlo antes de venderlo (hipótesis NO VERIFICADA en esta sesión).

---

## 7. Diseño para que la organización venda a muchos productores

| Decisión de diseño | Por qué escala | Cómo se muestra en la demo |
|---|---|---|
| **Paquete por cultivo y región = configuración, no código.** El paquete trae modelos de riesgo, umbrales, clases del clasificador y calendario | Para un frutal o país nuevo se carga un paquete; no hay que reprogramar | Mostrar el perfil "Sabana de Bogotá" junto a otro perfil de ejemplo |
| **Modelos genéricos de temperatura y mojado de hoja** (antracnosis: Wilson 1990 adaptado a arándano, no Miles 2013 [verificación técnica 2026-10-23]; Bulger 1987 para Botrytis), con parámetros por región | Valen fuera de la Sabana; el primer ciclo sirve para recalibrar | Una curva de riesgo con dos climas distintos |
| **Tres planes sobre una sola plataforma** (Vigía, Centinela, Flota) | El mismo software sirve a un asociado de mora y a una exportadora de 1.000 ha | Tabla de planes |
| **Hardware intercambiable:** capa de abstracción del robot (D1 EDU, Ultra, MaxPro u otro) y sensores de terceros por API, incluidas estaciones que el productor ya tenga | Baja el costo de entrada y reduce la dependencia de un proveedor | Diagrama de arquitectura |
| **Varias fincas y varios usuarios:** un agrónomo maneja varias fincas; el gremio ve un mapa regional anonimizado | Cada nuevo cliente mejora la alerta temprana regional (efecto red) | Mapa de calor por finca y vista regional |
| **Procesamiento en el robot o el gateway:** inferencia local y sincronización cuando hay señal | Solo el 56,9 % de los hogares rurales tenía internet en 2025 ([MinTIC/DANE ECV](https://mintic.gov.co/portal/inicio/Sala-de-prensa/Noticias/437305:Gobierno-Petro-conecto-3-5-millones-de-hogares-en-tres-anos-y-por-primera-vez-mas-de-la-mitad-de-los-hogares-rurales-tienen-internet)) | Demo en modo sin conexión |
| **Instalación estándar:** mapa de camas, sensores, capacitación de operario y agrónomo | La puede ejecutar un socio local sin el equipo fundador | Lista de pasos de instalación |
| **Registro exportable:** formato propio + exportación a informes ICA, SENASA, SAG y certificadoras | Un registro que ya hay que llevar se convierte en valor (la Res. 448 exigía monitoreo trimestral de plagas y registro de aplicaciones; la 824 la reemplazó) | Botón "exportar informe trimestral" |

---

## 8. Competencia y alternativas (criterio Justificación)

| Alternativa | Qué hace | Modelo y precio | Límite frente a nuestra propuesta | Fuente |
|---|---|---|---|---|
| Monitoreo manual por un trabajador | Recorre y anota | Jornales (mano de obra = 70 % del costo en arándano en Colombia) | Ve tarde, cubre poco, registro irregular | [Agronegocios 2026](https://www.agronegocios.co/agricultura/el-arandano-crece-pero-lejos-de-su-potencial-exportador-4321623) |
| Estación + modelos de enfermedad (Metos/Pessl) | Riesgo según el clima | 96 EUR por cultivo y año + estación | No ve síntomas cama por cama ni ubica focos. **Es complementaria:** podemos integrarla | [shop.metos.at](https://shop.metos.at/products/disease-model-license-for-1-year) |
| Saga Robotics Thorvald | Trata el oídio con UV-C (fresa, viñedo). **Corregido en la verificación (2026-10-23):** la misma fuente dice que sus máquinas nuevas llevan cámaras para detectar enfermedades y plagas ("We can also recognize outbreaks of diseases and pests") | Robot como servicio, por ha; 13 productores de fresa en el Reino Unido; pasaría de ~20 % a ~30 % de la fresa en mesa del Reino Unido | Su negocio es el tratamiento; la detección es un complemento. No se encontró que haga riesgo por clima, triage ni registro exportable. Es competidor directo si entra a berries en Latinoamérica | [AgFunderNews, 2025-08-08](https://agfundernews.com/saga-robotics-raises-11-2m-to-expand-fleet-of-bots-blasting-powdery-mildew-with-uv-c-light) |
| Syngenta "Robodog" | Perro robot con cámaras 3D y visión para malezas, plagas y enfermedades; ~4 h de autonomía | En desarrollo (marzo de 2026), sin precio | Amenaza directa y posible socio. Va atado a una marca de agroquímicos; nuestra ventaja es ser neutrales | [FertilizerDaily](https://www.fertilizerdaily.com/20260304-syngenta-introduces-robotic-dog-to-support-agronomists-in-the-field/), [Bichos de Campo](https://bichosdecampo.com/el-mejor-amigo-del-hombre-ya-no-persigue-liebres-sino-que-monitorea-los-cultivos-syngenta-diseno-el-robodog-un-robot-capaz-de-detectar-malezas-y-otras-amenazas-en-los-lotes/) |
| Plataformas digitales de agroquímicas (Cropwise, FieldView, xarvio) y satélite | Índices de vegetación y priorización de lotes | Licencia o ligadas a la compra de producto | No ven el envés de la hoja ni bajo plástico. En Colombia el arándano va bajo invernadero (razonamiento propio) | NO VERIFICADO (resultados de búsqueda) |
| Drones | Imagen aérea | Servicio | Mismo límite bajo cubierta; además requieren permisos de vuelo | Razonamiento propio, NO VERIFICADO |

**Nuestra posición:** somos la única opción de la tabla que junta **riesgo por clima + confirmación visual cama por cama + triage + registro + aspersión dirigida**, y no estamos atados a ninguna marca de agroquímicos. *Matiz de la verificación (2026-10-23):* Saga y Syngenta ya detectan con cámara. La diferencia no es "ver la enfermedad", sino juntar las cinco piezas y ser neutrales.

---

## 9. Riesgos

| Riesgo | Señal o dato | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| **Adopción**: desconfianza y cansancio por falsas alarmas | En Colombia hay ~200 productores de arándano y el 95 % de la producción va al mercado interno | Media | Alto | Triage obligatorio por agrónomo; precisión publicada en el piloto; plan Vigía como entrada; pago atado a resultados en etapa 1 |
| **Costo**: 430 USD/ha no cierra en cultivos de bajo valor | Equilibrio en mora = 3,5 % de la cosecha | Alta en mora, baja en arándano | Medio | Vigía para mora; Flota compartida; financiación con crédito agropecuario (NO VERIFICADO) |
| **Precio del robot más alto de lo previsto** | 9.600 USD en la tienda oficial frente a 7.499 FOB del equipo, más envío y aranceles | Media | Medio | Cotizar con distribuidor; modelo de servicio; capa de abstracción para cambiar de robot |
| **Conectividad rural** | 56,9 % de los hogares rurales con internet (2025) | Alta | Medio | Procesamiento local, LoRa, sincronización diferida; registro sin conexión |
| **Robustez del robot** | D1 Ultra: IP54, 0–40 °C, batería de 1–2 h, carga útil de 5 kg ([store.agibot.com](https://store.agibot.com/products/d1-ultra)) | Media | Alto | Recorridos cortos con estación de carga; MaxPro IP67 para lluvia y polvo (Flota); repuestos y SLA locales. **La batería de 1–2 h limita las ha por robot (20 ha = SUPUESTO)** |
| **Regulación fitosanitaria** | Registro ICA de exportación (Res. 824 de 2022); la aspersión dirigida cuenta como aplicación de plaguicida | Media | Medio | Solo productos con registro ICA; registrar cada aplicación; convertir la regla en función del producto (informe trimestral) |
| **Regulación de datos y equipos** | Datos personales de operarios; equipos de radio importados | Baja | Medio | Datos del productor como propiedad suya; consentimiento. La homologación de radio y la Ley 1581 de 2012 están NO VERIFICADAS en esta sesión |
| **El clasificador no generaliza** | Entrenado con datasets públicos (DrBerry y otros) | Alta | Alto | Etiquetar imágenes locales en cada piloto; reportar métricas por región y variedad |
| **Mercado pequeño en Colombia** | ~1.000 ha y 28 empresas en el gremio | Alta | Medio | Usar Colombia como vitrina y pasar a Perú en el mes 24 |
| **Entrada de grandes** | Syngenta Robodog (2026), plataformas de agroquímicas | Media | Alto | Neutralidad de marca, integración por API, alianzas con distribuidores independientes |
| **Clima extremo (El Niño)** | ProArándanos advierte alta incertidumbre para 2026-27 | Media | Medio | Es también argumento de venta: alerta temprana de riesgo climático |
| **Canal institucional inestable** | Disputa en 2026 por la administración del FNFH (NO VERIFICADO) | Media | Bajo | No depender de un solo canal público |

---

## 10. Límites de este análisis y lo que falta verificar

- **Productores en Chile y México:** no se encontró un número oficial. Para Chile habría que revisar el catastro de Odepa/CIREN o el SAG; para México, el cierre agrícola del SIAP.
- **Precios al productor de fresa y arándano en Colombia:** el de fresa aplica a precio mayorista la proporción en finca de la mora (SUPUESTO). Con datos del gremio (>200.000 M COP de comercio formal al año sobre 12.000–20.000 t) se obtienen ~10.000–16.700 COP/kg, pero ese es un precio de mercado, no en finca (cálculo propio indicativo).
- **Los porcentajes de SAM y SOM y los precios de los planes son SUPUESTOS.** Se cambian en `calc_mercado.py`.
- **Artículos de la Res. ICA 824 de 2022:** no se leyeron completos; las obligaciones citadas son de la 448 de 2016 (derogada).
- **Supuesto de 20 ha por robot:** depende de la batería (1–2 h según la ficha) y de la velocidad de recorrido por cama. Hay que coordinarlo con el rol técnico y con finanzas.

---

## 11. Fuentes abiertas en esta sesión (consulta: 2026-10-23)

| # | Fuente | Fecha de publicación | Qué se tomó |
|---|---|---|---|
| 1 | [datos.gov.co EVA 2019–2025, Base Agrícola (uejq-wxrr), API SODA](https://www.datos.gov.co/resource/uejq-wxrr.json) | Actualizado 2026-08-28 | Área, producción y municipios de arándano, fresa, mora, uchuva y aguacate. Copia en `escalabilidad/mercado/eva_*.json` |
| 2 | [datos.gov.co TRM (32sa-8pi3)](https://www.datos.gov.co/resource/32sa-8pi3.json) | 2026-10-23 | 3.185,01 COP/USD |
| 3 | [Forbes Colombia](https://forbes.co/economia-y-finanzas/colombia-consume-el-95-de-su-produccion-de-arandanos-y-busca-crecer-en-exportaciones) | 2026-05-04 | ~1.000 ha, 12.000 t, 95 % consumo interno |
| 4 | [Portal Frutícola ?p=614315](https://www.portalfruticola.com/?p=614315) | 2026-04-06 | ~1.000 ha → ~1.200 ha; Nación Berries |
| 5 | [El Colombiano](https://www.elcolombiano.com/negocios/arandanos-en-colombia-cultivos-expansion-FA33220603) | 2026-02-05 | 28 empresas Asocolblue; proyectos de 5–30 ha |
| 6 | [Agronegocios, "El arándano crece…"](https://www.agronegocios.co/agricultura/el-arandano-crece-pero-lejos-de-su-potencial-exportador-4321623) (copia local en `raw/paramsim_agronegocios_arandano/`) | 2026-02-11 | Mano de obra = 70 % del costo; inversión; 28 productores; potencial de 5.000–10.000 ha |
| 7 | [Agronegocios, 2023](https://www.agronegocios.co/agricultura/arandanos-un-mercado-que-llegaria-a-us-3-000-millones-en-exportaciones-para-2025-3636243) | 2023-06-14 | ~200 agricultores, ~600 ha |
| 8 | [Agraria.pe, 23.344 ha certificadas](https://agraria.pe/noticias/peru-cuenta-con-23-344-hectareas-certificadas-de-arandanos-p-41924) | 2026-03-26 | Perú 26.786 ha y regiones |
| 9 | [ProArándanos, proyección 2026-27 (PDF)](https://cdn.freshfruitportal.com/2026/06/Proarandanos-statement-on-2026-season-projections.pdf) | Junio 2026 | >27.000 ha en producción; incertidumbre climática |
| 10 | [Agraria.pe, superficie ×10](https://agraria.pe/noticias/superficie-de-arandanos-en-peru-crecio-mas-de-10-veces-en-la-42874) | 2026-08-14 | SENASA: >20.000 ha certificadas en 2025 |
| 11 | [Agraria.pe, 30 % pequeños](https://agraria.pe/noticias/el-30-de-la-produccion-de-arandanos-de-peru-proviene-de-pequ-37145) | 2024-09-27 | Pequeños de 5–50 ha = 30 %; grandes >1.000 ha |
| 12 | [Portal Frutícola ?p=610281](https://www.portalfruticola.com/?p=610281) | 2026-01-15 | 207 exportadoras; 6,22 USD/kg |
| 13 | [Portal Frutícola ?p=615425](https://www.portalfruticola.com/?p=615425) | 2026-04-28 | Perú = 56 % de las importaciones de EE. UU. |
| 14 | [Portal Frutícola, Chile 2023](https://www.portalfruticola.com/noticias/2023/10/04/chile-campana-23-24-de-arandanos-llegaria-a-82-mil-toneladas/) | 2023-10-04 | 18.071 ha |
| 15 | [Revista Economía](https://www.revistaeconomia.com/?p=111222) | 2025-10-30 | Odepa ~14.000 ha, Comité ~15.700 ha |
| 16 | [Portal Frutícola ?p=610283](https://www.portalfruticola.com/?p=610283) | 2026-01-15 | Ñuble 3.250 ha = 23 % |
| 17 | [Portal Frutícola ?p=609061](https://www.portalfruticola.com/?p=609061) | 2025-12-12 | Chile 161.500 t; recambio de variedades |
| 18 | [FreshPlaza, México](https://www.freshplaza.com/latin-america/article/9788676/mexico-targets-91-700-ton-blueberry-output-for-2025-2026/) | 2025-11-27 | 11.000 ha; estados; empresas del panel |
| 19 | [Agraria.pe, México berries](https://agraria.pe/noticias/exportadores-preven-que-mexico-tenga-ventas-record-de-fresas-39928) | 2025-06-27 | 48.000–50.000 ha de berries |
| 20 | [Agraria.pe, Aneberries](https://agraria.pe/noticias/volumen-de-produccion-de-berries-de-mexico-caeria-20-este-35776) | 2024-05-20 | 40 asociados; 75–80 % |
| 21 | [Agraria.pe, México 2025](https://agraria.pe/noticias/produccion-de-arandanos-en-mexico-caera-9-en-2025-ante-compe-38539) | 2025-02-10 | 73.500 t en 2025 (−9 %) |
| 22 | [DANE SIPSA diario 19 jun 2026](https://www.dane.gov.co/files/operaciones/SIPSA/bol-SIPSADiario-19jun2026.pdf) | 2026-06-19 | Mora 6.896 COP/kg en Corabastos |
| 23 | [DANE SIPSA semanal 13–19 jun 2026](https://www.dane.gov.co/files/operaciones/SIPSA/bol-SIPSASemanal-13jun19jun-2026.pdf) | 2026-06-19 | Fresa 4.563 COP/kg; precio en finca de la mora = 57–65 %; pérdidas de 8–15 % |
| 24 | [Metos shop](https://shop.metos.at/products/disease-model-license-for-1-year) | Sin fecha | 96 EUR por cultivo y año |
| 25 | [Future Farming](https://www.futurefarming.com/tech-in-focus/field-robots/robot-combats-powdery-mildew-in-strawberries-using-uv-c-treatment/) | 2021-12-22 | Saga: tarifa fija por ha |
| 26 | [AgFunderNews](https://agfundernews.com/saga-robotics-raises-11-2m-to-expand-fleet-of-bots-blasting-powdery-mildew-with-uv-c-light) | 2025-08-08 | Saga: 11,2 M USD; 13 productores; 20 → 30 % |
| 27 | [FertilizerDaily](https://www.fertilizerdaily.com/20260304-syngenta-introduces-robotic-dog-to-support-agronomists-in-the-field/) / [Bichos de Campo](https://bichosdecampo.com/el-mejor-amigo-del-hombre-ya-no-persigue-liebres-sino-que-monitorea-los-cultivos-syngenta-diseno-el-robodog-un-robot-capaz-de-detectar-malezas-y-otras-amenazas-en-los-lotes/) | 2026-03-04 / 2026-03-07 | Syngenta Robodog en desarrollo |
| 28 | [MinTIC (DANE ECV 2025)](https://mintic.gov.co/portal/inicio/Sala-de-prensa/Noticias/437305:Gobierno-Petro-conecto-3-5-millones-de-hogares-en-tres-anos-y-por-primera-vez-mas-de-la-mitad-de-los-hogares-rurales-tienen-internet) | Actualizado 2026-04-27 | 56,9 % de hogares rurales con internet |
| 29 | [Agronegocios, ISA 2025](https://www.agronegocios.co/agricultura/habilitan-128-000-millones-para-que-campesinos-aseguren-sus-cultivos-ante-fenomenos-climaticos-4135544) | 2025-05-16 | Subsidio a la prima 80 % / 30 % |
| 30 | [Compilación ICA, Res. 448 de 2016](https://compilacionmsf.ica.gov.co:4443/compilacion/docs/pdf/resolucion_ica_0448_2016.pdf) | Sin fecha | Derogada por la Res. 824 de 2022; obligaciones de registro |
| 31 | [AgiBot store, D1 Ultra](https://store.agibot.com/products/d1-ultra) | Consulta 2026-10-23 | 9.600 USD; IP54; 0–40 °C; batería de 1–2 h; 5 kg |

---

## 12. Nota de verificación de negocio (2026-10-23)

Un verificador adversario reabrió en la sesión 24 de las 31 URL. El detalle está en `datos/reportes/escala-verificacion-negocio.md`. Todas las cifras de superficie y de precio revisadas coinciden con su fuente: Perú, Chile, México, EVA 2025, SIPSA, Metos, ISA, MinTIC, Forbes, Portal Frutícola y El Colombiano. También cuadra la aritmética de `calc_mercado.py`.

**Correcciones de esta nota**

| Punto | Antes | Ahora |
|---|---|---|
| Saga Thorvald | "no diagnostica" | La fuente citada dice que sus máquinas nuevas detectan enfermedades y plagas (sección 8) |
| Precio Centinela | 430 USD/ha | 430 es una cifra de costo anterior del equipo. No cubre el costo del vendedor (sección 3.2). Usar 520 USD/ha, el precio calculado en `modelo_negocio.md` |
| Plan Flota | D1 MaxPro, ~60 ha | El MaxPro solo como inspector no se paga. Usar una flota de D1 Ultra (sección 2.1) |
| Vigía en mora | Equilibrio de 0,5 % de la cosecha | Con el kit de sensores incluido, ~1,3 % (sección 2.2) |

**Diferencias que quedan abiertas**

| Tema | Este documento | `modelo_negocio.md` | Qué hacer |
|---|---|---|---|
| Área de arándano en Perú | 26.786 ha (ProArándanos, 2025-26) | ~30.000 ha (Agraria.pe, 2026-01-15, sin fuente primaria) | Usar 26.786 en los dos documentos |
| ha por robot | 20 (supuesto heredado) | 35,8 (base) | Mostrar un rango de 16 a 36 ha, según `operacion.md` y finanzas |
| Precio sin robot | Vigía, 60 USD/ha | SaaS, 130 USD/ha | Dos niveles: 130 en arándano y fresa, menos de 60 y casi sin hardware en mora |

**Precio local del arándano.** El Colombiano (2026-02-05) dice que el productor recibe "unos 8 USD/kg" en el mercado local. Eso respalda los 6 USD/kg del modelo como cifra prudente.
