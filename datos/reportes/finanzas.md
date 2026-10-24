# Reporte del agente de finanzas: cifras verificadas y ROI

Fecha de corte: 2026-10-23. Moneda del modelo: USD. TRM usada: 3.185,01 COP/USD (TRM vigente el 23-oct-2026).

## 1. Qué hice

1. Revisé cada cifra financiera del equipo contra fuentes abiertas (ver §6) y la marqué como VERIFICADA, CORREGIDA, NO VERIFICADA o SUPUESTO.
2. Busqué datos que faltaban: SMMLV y jornal 2026, TRM, costo de una aplicación fitosanitaria, pérdidas por enfermedad, arancel e IVA de importación y precio actual del D1.
3. Escribí `finanzas/parametros.yaml`. Cada parámetro trae base, pesimista y optimista, además de su tipo (FUENTE, DERIVADO, SUPUESTO o NO VERIFICADO) y su fuente.
4. Escribí `finanzas/roi.py`. El script calcula, para las 8 opciones y fincas de 5, 20, 50 y 100 ha:
   - el costo puesto en finca;
   - el costo por ha y año;
   - el punto de equilibrio;
   - el ROI en tres escenarios;
   - un tornado de sensibilidad.
5. Corrí el script con `python3 -I` (Python del sistema) y con `.venv/bin/python -I`. Con ambos da el mismo resultado.

Modelo, por ha y año:
- B = Y·P·L·f·mult_f + n·C_ap·mult_n + J·w·mult_J
- C = CAPEX/vida (3 años) + OPEX. OPEX incluye mantenimiento, nube y falsas alarmas × 30 USD. También se reporta una variante con anualidad a la WACC de 13,4 % (columna `_crf`).
- ROI = (B − C)/C
- Punto de equilibrio en kg/ha = (C − n·C_ap − J·w)/P. También se da la versión que solo cuenta fruta salvada: C/P.

Los multiplicadores `mult` asignan a cada opción una parte del beneficio del sistema completo (el híbrido F = 1). Son SUPUESTOS. Por ejemplo, la red sola (B) no ve hojas, así que mult_f = 0,4 y mult_J = 0.

## 2. Tabla final (finca de referencia de 20 ha, escenario base)

| Opción | Robots | CAPEX USD | Costo USD/ha/año | Costo con anualidad 13,4 % | Beneficio USD/ha/año | Equilibrio kg/ha (% cosecha) | Equilibrio solo fruta kg/ha (%) | ROI pes / base / opt | Payback base (años) |
|---|---|---|---|---|---|---|---|---|---|
| A D1 Ultra + mástil | 2 | 22.840 | 820 | 926 | 1.502 | 96 (0,80 %) | 137 (1,14 %) | −0,93 / 0,83 / 32,7 | 1,07 |
| B Red fija | 0 | 6.338 | 248 | 277 | 1.290 | 0 (0 %) | 41 (0,34 %) | −0,39 / 4,21 / 55,6 | 0,28 |
| C Kit en aspersora | 1 | 5.679 | 285 | 311 | 1.050 | 23 (0,19 %) | 48 (0,40 %) | −0,83 / 2,68 / 49,4 | 0,33 |
| D Humanoide X2 Ultra | 3 | 157.972 | 3.716 | 4.451 | 1.502 | 579 (4,82 %) | 619 (5,16 %) | −0,98 / −0,60 / 4,6 | 18,8 |
| E1 Amiga + cámara | 2 | 63.451 | 1.461 | 1.757 | 1.502 | 203 (1,69 %) | 244 (2,03 %) | −0,93 / 0,03 / 20,1 | 2,89 |
| E2 Genie G1 | 2 | 192.838 | 4.340 | 5.238 | 1.502 | 683 (5,69 %) | 723 (6,03 %) | −0,98 / −0,65 / 5,3 | 25,6 |
| **F Híbrido red + D1 Ultra** | **1** | **17.489** | **722** | **804** | **2.441** | **13 (0,11 %)** | **120 (1,00 %)** | **−0,82 / 2,38 / 36,8** | **0,43** |
| G D1 MaxPro como servicio (60 ha) + red | 2 (del proveedor) | 6.338 (solo la red) | 2.257 | 2.623 | 2.441 | 269 (2,24 %) | 376 (3,13 %) | −0,92 / 0,08 / 13,9 | 1,09 |

Base del cultivo: Y = 12.000 kg/ha, P = 6 USD/kg, ingreso bruto 72.000 USD/ha/año.

ROI base según el tamaño de la finca (costo USD/ha/año entre paréntesis):

| Opción | 5 ha | 20 ha | 50 ha | 100 ha |
|---|---|---|---|---|
| A | −0,02 (1.532) | 0,83 (820) | 0,86 (808) | 1,04 (739) |
| B | 2,76 (343) | 4,21 (248) | 4,64 (229) | 4,80 (222) |
| C | 0,52 (690) | 2,68 (285) | 2,58 (293) | 2,94 (266) |
| F | 0,36 (1.791) | 2,38 (722) | 2,18 (768) | 2,50 (697) |
| G | 0,04 (2.352) | 0,08 (2.257) | 0,09 (2.238) | 0,09 (2.232) |

### Lectura para el pitch

- **El híbrido F se paga si salva 120 kg/ha/año de fruta (1 % de la cosecha), contando solo fruta.** Si además cuenta las aplicaciones evitadas, bastan 13 kg/ha. Su costo es unos 722 USD/ha/año, cerca del 1 % del ingreso bruto. Con f = 25 % de pérdida evitada, se paga si hoy las enfermedades objetivo se llevan al menos 0,45 % de la cosecha.
- **Hay que decirlo con honestidad: la red fija sola (B) tiene el ROI más alto (4,2).** El robot se justifica por su valor incremental. F frente a B cuesta 475 USD/ha/año más y aporta 1.151 USD/ha/año más de beneficio, con un ROI incremental de 1,43. Además confirma visualmente cama por cama, que es justo lo que pide el reto.
- **Un D1 Ultra solo no alcanza para revisar 20 ha cada semana.** Supuestos: 0,5 m/s, 36 h/semana, entrecalle de 2,5 m (4.000 m de cama por ha) y 30 % de tiempo extra en giros y cambios de batería. Con eso cubre ~12,5 ha/semana, así que la opción A necesita 2 robots. Si la red de riesgo lo dirige a ~50 % de las camas (F), un robot cubre ~25 ha. La ficha de AgiBot da 1–2 h de autonomía por batería: se necesitan 3–4 baterías y cambios.
- **Humanoides (D, E2) y MaxPro como servicio (G) no se pagan en el escenario base.** La Amiga (E1) queda en equilibrio.
- **Los escenarios conjuntos son extremos.** El pesimista combina todo lo desfavorable y da negativo en todas las opciones. El optimista combina todo lo favorable y da ROI de 14× a 56×. Para el jurado conviene mostrar la base y el tornado.
- **El tornado de F muestra qué medir en el piloto.** Los parámetros que más mueven el neto son la pérdida base L (rango 2.700 USD/ha), la fracción evitada f (2.160), el rendimiento Y (1.800), el precio P (1.500) y las aplicaciones evitadas n (950). El precio del robot, el arancel, el flete y la TRM casi no pesan (< 50 USD/ha). Lo que más vale medir en piloto son L y f.
- **Umbral de decisión, con los SUPUESTOS del equipo:** falsa alarma 30 USD y caso no detectado 2.160 USD/ha/semana. Alertar es rentable si P(enfermedad) > 30/(30+2.160) = 1,4 %. Esto respalda el umbral orientado a sensibilidad. Advertencia: los dos costos están en unidades distintas (por alerta frente a por ha-semana). Además, 2.160 USD/ha/semana equivale al 3 % del ingreso anual base por cada semana; es plausible solo en picos de presión de enfermedad.

## 3. Qué cambió frente a las cifras previas

| Cifra del equipo | Estado | Valor que queda / comentario |
|---|---|---|
| Rendimiento Colombia ~12 t/ha (Forbes 2026) | VERIFICADA | Forbes, 26-may-2026: "algunos cultivos rinden cerca de 12 t/ha", producción ~12.000 t (Planasa estima 15.000–16.000 t). Asocolblue (Agronegocios, 11-feb-2026) habla de ~20.000 t en ~1.000 ha (≈20 t/ha, cálculo propio). Rango del modelo: 8 / 12 / 20 t/ha. |
| Perú 19,2 t/ha (2021) | NO VERIFICADA | No encontré la fuente. Perú 2025: ~30.000 ha (Agraria.pe) y 412.239 t exportadas (Gestión), es decir ~13,7 t/ha exportables (derivado grueso). Recomiendo no usar 19,2 sin cita. |
| Precio en finca 8–10 USD/kg y costo 3,5–5 USD/kg (Planasa vía Forbes) | VERIFICADA como cita | Es una estimación de una empresa vivero/productora. **El precio base del modelo baja a 6 USD/kg.** Razones: el FOB implícito de Colombia 2025 es 5,2–6,1 USD/kg (574.607 kg por 3–3,5 MUSD, El Tiempo) y el FOB de Perú es 6,22. El valor pesimista de 4 USD/kg sale del comercio interno formal de Asocolblue. 8–10 USD/kg queda como optimista. |
| 95 % mercado local | VERIFICADA | Forbes y El Tiempo (2026). |
| FOB Perú 6,22 USD/kg (2025) | VERIFICADA | Gestión, 14-ene-2026 (2024: 6,43). Son cifras preliminares de Fresh Fruit con datos de Sunat. |
| Establecimiento 50–60 mil USD/ha (UNAD 2021) | FUENTE NO LOCALIZADA, se reemplaza | Peña Baracaldo et al. (2023, *Agronomía Colombiana* 41(2)): estructura inicial ~58.606 USD/ha (1 ha, 7.680 plantas, malla antigranizo), mantenimiento ~22.800 USD/ha/año, WACC 13,4 %, TIR 19 %. Usan TRM de noviembre de 2021, de 3.875,38 COP/USD. |
| Área 500 ha (Asocolblue) frente a ~1.000 ha (Forbes) | CORREGIDA | Asocolblue (feb-2026) ya dice ~1.000 ha, ~50 % en Boyacá y ~50 % en Cundinamarca, con +20 % esperado en 2026. **Usar ~1.000 ha.** |
| SMMLV 2026 1.750.905 COP | VERIFICADA | Decreto 1469 de 2025 (+23,0 % sobre 1.423.500 COP de 2025; corregido por el verificador, decía 23,7 %); auxilio de transporte 249.095 COP (Decreto 1470). El Consejo de Estado lo suspendió el 12-feb-2026; el Decreto transitorio 0159 mantuvo el valor; la suspensión se revocó el 9-jul-2026. |
| Jornal ~75.900 COP con prestaciones | VERIFICADA como cálculo | 1.750.905/30 × 1,30 = **75.873 COP = 23,82 USD**. La regla "SMMLV diario + ≥30 % prestacional" viene del **proyecto** de ley 504 de 2025, que no es ley vigente. Rango: 58.364 (informal) a 88.700 COP (SUPUESTO formal +52 %). |
| TRM | NUEVA | 3.185,01 (23-oct-2026), 3.158,43 vigente del 24 al 26 de octubre. Últimos 12 meses: mínimo 3.048, máximo 3.901, promedio 3.532. |
| Costo de una aplicación fitosanitaria | NUEVO (DERIVADO) | ~95 USD/ha por aplicación, con rango 60–130. Sale de la ficha ODEPA Maule 2020-21 (~112 USD/ha a 707,85 CLP/USD) ajustada con el jornal colombiano. |
| Pérdidas por enfermedad | NUEVO | Antracnosis: 10–20 % precosecha en campos bien manejados y hasta 100 % en poscosecha (MSU E3039; Neugebauer et al. 2024). Botrytis: episódica, hasta 30–40 %. Roya: sin estudios de pérdida, el efecto es por defoliación. L en el modelo: 5 / 10 / 20 % (SUPUESTO; no hay dato colombiano). |
| Aplicaciones evitables | NUEVO | Un sistema de alerta ambiental en fresa (StAS, Florida) redujo el fungicida en 50 % en 39 fincas, sin pérdida de rendimiento (UF/IFAS 2017). n en el modelo: 2 / 6 / 12 por ha y año, sobre un calendario supuesto de ~24 aplicaciones. |
| Factor de importación 1,35 | VERIFICADO EN LO ESENCIAL | Para un D1 Ultra el factor calculado es **1,36**: flete 300 + seguro 1 %, arancel 5 % sobre el CIF, IVA 19 % sobre CIF + arancel, agencia y transporte 350. Si el arancel es 0 %, baja a 1,30; si el IVA se recupera, a 1,15. Para equipos baratos sube (D1 Pro 1,49; red de 20 nodos 1,41) por los costos fijos. Para equipos caros baja (MaxPro, X2 y G1 ~1,28). |
| Subpartida y arancel | NUEVO | En el Arancel de Aduanas (Decreto 1881 de 2021, compilación DIAN con decretos hasta 2026), 8479.50.00.00 "Robots industriales, n.e.p." paga **5 %**. 8479.89.90.00 (los demás) paga 5 %. 8543.70.90.00 paga 0 % (Decreto 1530 de 2024). La clasificación del cuadrúpedo no está verificada: pedir clasificación arancelaria anticipada a la DIAN. El TLC con México no aplica a un robot de origen chino. |
| IVA | VERIFICADO | 19 % (Estatuto Tributario art. 468). La base es el valor aduanero + arancel (art. 459). El arándano fresco se vende sin IVA, así que el IVA de la importación es costo. El descuento en renta del art. 258-1 queda NO VERIFICADO para este caso. |
| Precio D1 Ultra 7.499 FOB México | NO VERIFICADO; hay dato mayor | En store.agibot.com el 23-oct-2026 aparece en **9.600 USD**, con envío aparte (D1 Edu 6.080, D1 Pro 3.200, que coinciden con la hoja del equipo). Se usa 9.600 como pesimista. La ficha da 16 kg, 1–2 h de autonomía, carga útil 5 kg, 0–40 °C e IP54. |
| Nodo 100–186 USD | VERIFICADO en parte | Dragino LLMS01 (mojadura foliar, LoRaWAN) cuesta 129 USD. 186 USD es la versión solar, según un resultado de búsqueda. El gateway de 500 USD es SUPUESTO. |
| OPEX de la red, 1.050–1.550 USD por 10 nodos | SUPUESTO; parece alto | Se mantiene como base y pesimista. Agregué un optimista de 50 USD/nodo/año. |
| Amiga 20–25k, X2 Ultra, Genie G1, D1 MaxPro | NO VERIFICADOS | Quedan los precios de la hoja del equipo. La Amiga no se pudo abrir (la página de RobotShop da 404). |

## 4. Archivos producidos

Todos en `/Users/santiagosantafe/Downloads/SabanaHack/datos/finanzas/`:
- `parametros.yaml`: parámetros con base, pesimista y optimista, tipo y fuente.
- `roi.py`: modelo. Se corre con `python3 -I roi.py`.
- `importacion_factores.csv`: costo puesto en finca por equipo y embarque, comparado con el factor 1,35.
- `costo_ha_anio.csv`: 8 opciones × 4 tamaños de finca. Incluye unidades, capacidad, CAPEX, OPEX y costo por ha (lineal y con anualidad).
- `punto_equilibrio.csv`: kg/ha y % de cosecha, pérdida base mínima y versión solo fruta.
- `roi_escenarios.csv`: escenarios pesimista, base y optimista, con el beneficio desagregado y el payback.
- `tabla_final_20ha.csv`: la tabla de §2.
- `derivados.csv`: jornal, capacidad por robot, umbral de Bayes y análisis incremental F vs B.
- `tornado_F_20ha.png` / `.csv` y `tornado_A_20ha.png` / `.csv`: sensibilidad de un factor a la vez sobre el beneficio neto.

Descargas en `raw/` (cada fuente en su carpeta): `finanzas_trm`, `finanzas_agrocol2023`, `finanzas_odepa`, `finanzas_clp`, `finanzas_msu`, `finanzas_msu_archive`, `finanzas_frontiers2024`, `finanzas_dian_arancel`, `finanzas_agibot_store`, `finanzas_agibot_brochure`. `finanzas_msu` quedó con dos páginas HTML de bloqueo; no se usó.

## 5. Límites

- **Las cifras de beneficio que más pesan son SUPUESTOS sin dato colombiano:** la fracción evitada f, la pérdida base L, las aplicaciones evitadas n, los jornales J y los multiplicadores por opción. Las pérdidas de referencia son de EE. UU. (Michigan) y la reducción de fungicida viene de fresa en Florida.
- El precio de 6 USD/kg es un supuesto conservador. Planasa dice 8–10, pero es una fuente interesada.
- La capacidad por robot sale de un modelo simple: velocidad × horas frente a metros de cama. Hay efectos de umbral, porque se redondea hacia arriba el número de robots. Por ejemplo, la Amiga cubre 19,9 ha y necesita 2 unidades para 20 ha. F en 50 ha necesita 3 D1. Con revisitas cada 8 días cambian.
- Flete, seguro, agencia de aduanas, accesorios, mantenimiento de los robots grandes y la tarifa del servicio MaxPro son SUPUESTOS.
- No se modela impuesto de renta, financiación, valor residual ni reemplazo de baterías aparte del mantenimiento.
- El costo de 30 USD por falsa alarma y la tasa de 5 falsas alarmas/ha/año son SUPUESTOS. En la opción A esa línea pesa 150 USD/ha/año, casi tanto como el robot.

## 6. Fuentes abiertas (consultadas el 2026-10-23)

- TRM, datos abiertos: https://www.datos.gov.co/resource/32sa-8pi3.json
- SMMLV 2026: https://www.buk.co/blog/salario-minimo-2026-en-colombia y https://www.eltiempo.com/economia/sectores/salario-minimo-2026-diez-preguntas-y-respuestas-para-entender-la-suspension-del-decreto-y-su-impacto-en-los-trabajadores-3532351
- Jornal agropecuario, PL 504 de 2025: https://www.icef.com.co/component/k2/item/8152-se-radico-proyecto-de-ley-que-busca-reglamentar-contrato-y-jornal-agropecuario
- Forbes Colombia, 26-may-2026: https://forbes.co/2026/05/26/negocios/arandano-colombiano-el-sello-que-lanzo-el-sector-para-impulsar-el-consumo-y-exportacion/
- El Tiempo, 4-may-2026: https://www.eltiempo.com/economia/sector-financiero/colombia-dispara-su-produccion-de-arandanos-pero-el-95-se-queda-en-casa-y-frena-el-salto-exportador-3552946
- Agronegocios (Asocolblue), 11-feb-2026: https://www.agronegocios.co/agricultura/el-arandano-crece-pero-lejos-de-su-potencial-exportador-4321623
- Gestión, FOB Perú: https://gestion.pe/economia/arandanos-rompen-record-de-exportaciones-pero-un-factor-preocupa-al-peru-noticia/
- Agraria.pe, área Perú: https://agraria.pe/noticias/superficie-de-arandanos-en-peru-crecio-12-en-2025-paso-de-26-41486
- Peña Baracaldo et al. 2023: https://revistas.unal.edu.co/index.php/agrocol/article/view/103525
- ODEPA, ficha arándano Maule 2020-21: https://www.odepa.gob.cl/fichas_de_costo/fichas_pdf/arandano_maule_2020-21.pdf
- Dólar observado de Chile 2021: https://mindicador.cl/api/dolar/2021
- Neugebauer et al. 2024, Front. Plant Sci. 15:1428769 (CC BY 4.0): https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2024.1428769/pdf
- MSU E-3039 (Miles y Schilder 2008): https://archive.lib.msu.edu/DMC/extension_publications/e3039/E3039.pdf
- StAS, UF/IFAS 2017: https://blogs.ifas.ufl.edu/news/2017/11/27/uf-web-tool-helps-south-carolina-florida-strawberry-growers/
- Arancel de Aduanas, compilación DIAN: https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1881_2021.htm
- IVA, Estatuto Tributario: https://estatuto.co/468 y https://estatuto.co/459
- Tienda AgiBot (JSON de producto): https://store.agibot.com/products/d1-ultra
- Ficha AgiBot D1 Ultra: https://www.agibot.com/file/ueditor/php/upload/file/20260825/1787637425866968.pdf
- Dragino LLMS01: https://www.773grp.com/products/llms01-us915-dragino

Licencias: los artículos de prensa y las fichas se citan, no se redistribuyen. Neugebauer et al. 2024 es CC BY 4.0. Las descargas quedan en `raw/` solo para uso interno.

## 7. Pendientes

1. Pedir a AgiBot o al distribuidor una cotización formal del D1 Ultra con entrega en Colombia. Hoy hay dos cifras: 7.499 FOB México y 9.600 en la tienda.
2. Pedir a la DIAN clasificación arancelaria anticipada del cuadrúpedo: 8479.50 al 5 % o 8543.70.90 al 0 %.
3. Cotizar el flete aéreo México–Bogotá y la agencia de aduanas.
4. Reemplazar las falsas alarmas/ha/año por la tasa real de la matriz de confusión del clasificador, en `beneficio.falsas_alarmas_ha_anio`.
5. Conseguir con Asocolblue o una finca piloto la pérdida actual L por enfermedad y el número real de aplicaciones fungicidas por año. Son los parámetros que más mueven el resultado.
6. Verificar los precios de Amiga, X2 Ultra, Genie G1 y D1 MaxPro, y la autonomía real del D1 con mástil y cámara.
