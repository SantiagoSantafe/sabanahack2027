# Verificación adversaria de negocio y mercado

Rol: verificador adversario de negocio y mercado. Reto "Berry Good Idea", Sabana Hack. Fecha: 2026-10-23.

**Qué revisé.**
- `escalabilidad/modelo_negocio.md`, `unit_economics.py` y su YAML.
- `escalabilidad/mercado.md` y `mercado/calc_mercado.py`.

**Contra qué los comparé.**
- `finanzas/` (parametros.yaml, tabla_final_20ha.csv, costo_ha_anio.csv, importacion_factores.csv).
- `escalabilidad/operacion.md`.

**Convención.**
- **FUENTE**: URL abierta en esta sesión.
- **SUPUESTO**: valor del equipo.
- **NO VERIFICADO**: no se pudo confirmar.

Todos los montos están en USD.

---

## 1. Veredicto

1. **Las cuentas están bien hechas, pero el resultado depende de los supuestos más optimistas del equipo.** El script corre igual con `python3 -I` y con PyYAML. Recalculé a mano dos filas y cuadran (sección 2). Lo frágil son los supuestos, no la aritmética.
2. **Corregí un error de cálculo.** La escala mínima del RaaS no es 1.071 ha, sino **1.358 ha, el 150 % del arándano de Colombia**. La búsqueda aceptaba un punto suelto con EBIT positivo, aunque entre ~1.090 y ~1.350 ha el EBIT volvía a ser negativo. El híbrido (1.071 ha) no cambia.
3. **Corregí una afirmación sobre la competencia.** Los dos documentos decían que Saga Thorvald "no diagnostica". La fuente que citan dice lo contrario: sus máquinas nuevas llevan cámaras para detectar enfermedades y plagas.
4. **El margen del RaaS sube y baja según el tamaño de la finca, en dientes de sierra** (tabla 5d nueva).
   - Finca de 30 ha: 23 %.
   - Finca de 20 ha, la de referencia del equipo: **-9 %**.
   - Finca de 40 ha: -2 %.
   - Para venderlo a muchos productores, el RaaS necesita un **cobro mínimo por robot instalado** o robots compartidos entre fincas vecinas.
5. **La capacidad de 36 ha por robot sale del modelo más optimista de los tres del equipo.**
   - Finanzas da 24,9 ha y `operacion.md` da 16,6 ha.
   - Con los supuestos de finanzas, el vendedor necesita cobrar ~668 USD/ha para tener 23 % de margen. El productor acepta como máximo 548 USD/ha con ROI 3x. **La ventana de precio del robot solo existe con los supuestos de `modelo_negocio.md`.**
6. **Los precios de los dos documentos no cuadran entre sí.**
   - `mercado.md` usa 430 USD/ha como precio de Centinela. Es una cifra de costo anterior del equipo: con 20 ha por robot, el vendedor pierde 60 %, y finanzas calcula hoy 722 USD/ha para el híbrido en 20 ha.
   - El plan Vigía de mora (60 USD/ha) no cuenta el kit de sensores. Con el kit, el ROI del productor es ~1,1x.
   - El SaaS de 130 USD/ha en mora da 0,75x.
   - Lo multicultivo escala si casi no lleva hardware por finca.

---

## 2. Re-ejecución y dos filas recalculadas a mano

`python3 -I unit_economics.py --fuentes` da la misma salida que el `unit_economics_salida.txt` original, salvo la línea final del JSON. Con PyYAML (`.venv`, 6.0.3) el resultado es idéntico.

Para el cálculo a mano escribí la aritmética desde cero, en un script aparte que no importa el modelo.

**Fila A: RaaS dedicado, finca de 30 ha (tabla 5)**

| Paso | Cálculo | Resultado | Script |
|---|---|---|---|
| CAPEX del robot | 7.499 × 1,12 + 2.000 + 2 × 450 + 300 | 11.599 | 11.599 |
| Horas útiles por semana | 7 × 6 × [1,25 / (1,25 + 0,1)] × 0,8 | 31,1 h | 31,1 |
| Horas por ha | 10.000 / 3,0 / 0,8 / 3.600 × 1,25 | 1,447 h | 1,45 |
| ha por robot | 31,1 / (1,447 × 0,6) | 35,8 | 35,8 |
| Baterías por año | 31,1 × 52 / 1,25 / 300 | 4,31 | 4,3 |
| Caja del robot por año | 11.599 × 0,11 + 4,31 × 450 | 3.217 | 3.217 |
| Costo por ha | robot 128,9 + 107,2; red 61,0; técnicos 64,4; agrónomo 26,7; nube 4; instalación + CAC 8,9 | **401,1** | 401 |
| Margen | (520 − 401,1) / 520 | **22,9 %** | 23 % |
| Payback | 17.287 / (8.921 / 12) | 23,3 meses | 23 |
| ROI del productor | 1.644,5 / (520 + 517 / 30) | **3,06x** | 3,1x |

**Fila B: SaaS + kit por canal, finca de 5 ha (tabla 5)**

| Paso | Cálculo | Resultado | Script |
|---|---|---|---|
| CAPEX de la red | 2 × 249 + 1.900 / 4 | 973 | 973 |
| Ingreso por ha | [max(650, 450) + 973 × 1,35 / 4] / 5 | 195,7 | 196 |
| Costo por ha | (243,3 + 193,2 + 133,6 + 20 + 83,3) / 5 | **134,7** | 135 |
| Margen | | **31,2 %** | 31 % |
| Costo del productor por ha | (328,4 + 131,4 + 30 + 650) / 5 | 227,9 | 228 |
| ROI | 768 / 227,9 | **3,37x** | 3,4x |
| Payback | 250 / (388 / 12) | 7,7 meses | 8 |

**Aritmética de `mercado.md`.** `calc_mercado.py` reproduce las cifras: TAM 26,0 M, SAM 7,89 M, SOM 0,446 M y 50 robots. Revisé también los equilibrios:
- Mora: 6.896 × 0,57 / 3.185,01 = 1,23 USD/kg. 430 / 1,23 = 348 kg/ha, el 3,5 % de la cosecha.
- Fresa: 0,86 USD/kg, 500 kg/ha, el 1,7 %.

---

## 3. URL abiertas y qué dicen

**URL de `modelo_negocio.md`**

| Cifra del documento | URL abierta | ¿Coincide? |
|---|---|---|
| D1 Ultra a 9.600 USD | https://store.agibot.com/products/d1-ultra.json ("price": "9600.00", USD) | Sí |
| Ficha del D1 Ultra: 1-2 h, 5 kg, IP54, 3,7 m/s, 16 kg, 0-40 °C | https://www.agibot.com/file/ueditor/php/upload/file/20260825/1787637425866968.pdf | Sí |
| Manual: "Keep the robot within your line of sight"; celda "6 months / 200 cycles"; batería extraíble; 4,6 Ah y 43,2 V | https://www.agibot.com/file/ueditor/php/upload/file/20260911/1789114774395970.pdf | Sí |
| Carga de ~1 h de 10 a 90 % (estaba como NO VERIFICADO) | El mismo manual: "about 1 hour (battery level 10%-90%)" | Sí; **pasa a FUENTE** |
| Batería de repuesto a 450 USD | La tienda (https://store.agibot.com/products.json) no vende baterías | Sigue NO VERIFICADO |
| MaxPro: 65.999 USD, 50 kg, 5,5 ± 0,5 h, carga de 4,5 h, IP67 | https://globaldronehq.com/products/agibot-d1-maxpro-quadruped-robot | Sí |
| METOS: 96 EUR por cultivo y año | https://shop.metos.at/products/disease-model-license-for-1-year | Sí; hace falta estación |
| METOS: estación virtual a 336 EUR al año | https://shop.metos.at/products/imetos©-virtual-weather-station | Sí |
| Davis Pro+: 8,95 o 7,65 USD/mes | https://www.davisinstruments.com/weatherlink/ | Sí; el precio es por equipo |
| Taranis: 15-20 USD/acre por temporada | https://thespoon.tech/taranis-harvests-20m-for-aerial-imaging-tech-that-detects-crop-diseases (2018) | Sí, pero el "alto valor" de la fuente es remolacha y papa, no frutales |
| Saga: cuota fija por ha; menos de 5 km/h | https://www.futurefarming.com/tech-in-focus/field-robots/robot-combats-powdery-mildew-in-strawberries-using-uv-c-treatment/ | Sí |
| Saga: más de 150 robots y más de 1.300 acres en EE. UU. (3,5 ha por robot) | https://www.agnavigator.com/Article/2025/08/14/saga-robotics-on-why-its-the-chasing-the-american-dream/ | Sí. "Trata casi todas las noches" no está en la fuente: **NO VERIFICADO** |
| Saga "no diagnostica" | https://agfundernews.com/saga-robotics-raises-11-2m-to-expand-fleet-of-bots-blasting-powdery-mildew-with-uv-c-light | **No.** La fuente dice "We can also recognize outbreaks of diseases and pests". **Corregido** |
| Trapview: 1 trampa vigila 20 ha | https://www.freshfruitportal.com/news/2025/10/16/trapview-fruit-attraction/ | Sí |
| Dragino LLMS01 a 129 USD | https://www.773grp.com/products/llms01-us915-dragino.oembed | Sí |
| TRM de 3.185,01 COP/USD el 2026-10-23 | https://www.datos.gov.co/resource/32sa-8pi3.json | Sí |
| SMMLV 2026 de 1.750.905 COP y auxilio de 249.095 COP | https://consultorsalud.com/aumento-del-salario-minimo-en-colombia-2026/ | Sí |
| Colombia exportó 628.235 kg por más de 3,3 M USD en 2024 (5,25 USD/kg) | https://agraria.pe/noticias/colombia-exporto-628-235-kilogramos-de-arandano-en-2024-gene-39081 | Sí; 5,25 es un mínimo |
| Perú, "cerca de 30,000" ha en 2025 | https://agraria.pe/noticias/superficie-de-arandanos-en-peru-crecio-12-en-2025-paso-de-26-41486 | Sí, pero la nota no nombra fuente primaria. `mercado.md` usa 26.786 (ProArándanos) |
| EVA 2025: arándano 906,7; fresa 3.767; mora 15.952; uchuva 1.810; Hass 72.444 ha | https://www.datos.gov.co/resource/uejq-wxrr.json (consulta agregada) | Sí. Todo el aguacate suma 141.051 ha |
| Asesoría de 1.000.000 COP/mes = 3.023 USD/año | Peña et al. 2023 (PDF local en `raw/finanzas_agrocol2023`) | Sí (3.022,7) |

**URL de `mercado.md` (abrí 24 de 31)**

| Cifra del documento | URL | ¿Coincide? |
|---|---|---|
| Perú: 26.786 cultivadas, 23.344 certificadas y reparto por región | https://agraria.pe/noticias/peru-cuenta-con-23-344-hectareas-certificadas-de-arandanos-p-41924 | Sí |
| Perú: más de 27.000 ha en producción, unas 3.000 nuevas, "elevado nivel de incertidumbre" | https://cdn.freshfruitportal.com/2026/06/Proarandanos-statement-on-2026-season-projections.pdf | Sí |
| Perú: los pequeños (5-50 ha) producen el 30 %; los grandes tienen más de 1.000 ha | https://agraria.pe/noticias/el-30-de-la-produccion-de-arandanos-de-peru-proviene-de-pequ-37145 | Sí. El 30 % es de la producción, no del área; el documento ya lo aclara |
| Perú: 207 exportadoras y 6,22 USD/kg | https://www.portalfruticola.com/?p=610281 | Sí |
| Perú: 56 % de las importaciones de EE. UU. | https://www.portalfruticola.com/?p=615425 | Sí (2025) |
| Chile: 14.000 ha (Odepa) y 15.700 ha (Comité) | https://www.revistaeconomia.com/?p=111222 | Sí |
| Ñuble: 3.250 ha, el 23 % de Chile | https://www.portalfruticola.com/?p=610283 | Sí |
| México: 11.000 ha y 7.648 ha, con reparto por estado | https://www.freshplaza.com/latin-america/article/9788676/mexico-targets-91-700-ton-blueberry-output-for-2025-2026/ | Sí |
| Colombia: unas 1.000 ha que pasarían a 1.200; Nación Berries | https://www.portalfruticola.com/?p=614315 | Sí |
| Asocolblue: 28 empresas; proyectos de 5 a 30 ha | https://www.elcolombiano.com/negocios/arandanos-en-colombia-cultivos-expansion-FA33220603 | Sí. La misma nota dice que el productor recibe "unos 8 USD/kg" en el mercado local |
| ~200 agricultores y ~600 ha en 2023 | https://www.agronegocios.co/agricultura/arandanos-un-mercado-que-llegaria-a-us-3-000-millones-en-exportaciones-para-2025-3636243 | Sí |
| La mano de obra pesa 70 %; 28 productores | Copia local `raw/paramsim_agronegocios_arandano/text.txt` | Sí. La nota habla del salario mínimo como 70 % del costo |
| 95 % de consumo interno; 12.000 t | https://forbes.co/economia-y-finanzas/colombia-consume-el-95-de-su-produccion-de-arandanos-y-busca-crecer-en-exportaciones | Sí |
| Mora a 6.896 COP/kg (+10 %) | https://www.dane.gov.co/files/operaciones/SIPSA/bol-SIPSADiario-19jun2026.pdf | Sí |
| Fresa a 4.563 COP/kg; mora en finca 57 % en Bogotá; pérdidas de 8-15 % | https://www.dane.gov.co/files/operaciones/SIPSA/bol-SIPSASemanal-13jun19jun-2026.pdf | Sí |
| Saga: 13 productores; pasaría de 20 % a 30 % | AgFunderNews (URL de arriba) | Sí. Pero "no diagnostica" no: **corregido** |
| Syngenta Robodog: malezas, plagas y enfermedades; ~4 h; en desarrollo | https://bichosdecampo.com/el-mejor-amigo-del-hombre-ya-no-persigue-liebres-sino-que-monitorea-los-cultivos-syngenta-diseno-el-robodog-un-robot-capaz-de-detectar-malezas-y-otras-amenazas-en-los-lotes/ | Sí. FertilizerDaily no menciona malezas ni las 4 h |
| 56,9 % de hogares rurales con internet | https://mintic.gov.co/portal/inicio/Sala-de-prensa/Noticias/437305:Gobierno-Petro-conecto-3-5-millones-de-hogares-en-tres-anos-y-por-primera-vez-mas-de-la-mitad-de-los-hogares-rurales-tienen-internet | Sí |
| ISA: 128.000 M COP; subsidio de 80 % y 30 % | https://www.agronegocios.co/agricultura/habilitan-128-000-millones-para-que-campesinos-aseguren-sus-cultivos-ante-fenomenos-climaticos-4135544 | Sí; además, hasta 85 % para pequeños de bajos ingresos |

**No abiertas:** fuentes 10, 14, 17, 19, 20, 21 y 30 de `mercado.md`. No sostienen ninguna cifra que entre al TAM, al SAM o al SOM.

---

## 4. Errores corregidos (todos en `escalabilidad/`)

Hice copias de respaldo previas en el scratchpad de la sesión.

| # | Archivo | Antes | Ahora | Por qué |
|---|---|---|---|---|
| 1 | `unit_economics.py`, tabla 7 | Escala mínima del RaaS: 1.071 ha, 85 fincas, 118 % | **1.358 ha, 108 fincas, 150 %**, CAPEX de 903.492 | La búsqueda solo probaba S y 1,5·S. Ahora exige EBIT ≥ 0 en todos los puntos de la malla entre S y 1,5·S. Venta (439), SaaS (1.071) e híbrido (1.071) no cambian |
| 2 | `modelo_negocio.md` y `mercado.md` | Saga "no diagnostica" | Saga detecta con cámara desde 2025. Nuestra diferencia es juntar riesgo por clima, confirmación cama por cama, triage, registro y neutralidad | La fuente citada (AgFunderNews, 2025-08-08) lo contradice |
| 3 | YAML, `carga_h` | NO VERIFICADO | FUENTE (manual) | El manual dice "about 1 hour (battery level 10%-90%)". Ahora son 93 parámetros sin fuente, no 94 |
| 4 | YAML, nota de `importacion_frac` | "El IVA se descuenta y no se cuenta como costo" | Advertencia: NO VERIFICADO, con los dos regímenes posibles | Ver la sección 6, punto 4 |
| 5 | YAML, nota de `distancia_entre_camas_m` | Sin comparación con otras fuentes | Cita 2,2 m (Peña et al. 2023), 2,5 m (finanzas) y ~2,35 m (`operacion.md`) | Es el valor más optimista del proyecto. **El valor de 3,0 m no se cambió**: es una decisión del equipo |
| 6 | `unit_economics.py`: tabla 5d nueva y 4 filas nuevas en la 9b | - | Margen por tamaño de finca; entrecalle de 2,5 y 2,2 m; IVA como costo; operario 40 min/día | Supuestos de otras fuentes que el modelo no mostraba |
| 7 | `mercado.md` | Centinela a 430; Flota con MaxPro de ~60 ha; equilibrio de Vigía sin hardware | Advertencias en las secciones 2.1, 2.2 y 3.2, y nota final (sección 12) | Contradicen `modelo_negocio.md`, finanzas y `operacion.md` |
| 8 | Salidas | - | Regeneré `unit_economics_salida.txt` y `unit_economics_resultados.json` | El JSON no cambió: no incluye la tabla 7 |

**No pude corregir** `reportes/escala-modelo-negocio.md` ni `reportes/escala-mercado-go-to-market.md`, porque no tengo permiso de escritura ahí. Siguen diciendo "1.071 ha" para el RaaS y "Saga no diagnostica".

---

## 5. Contradicciones con finanzas y con `operacion.md`

| Supuesto | `modelo_negocio.md` | Finanzas, opción F | `operacion.md` | Efecto |
|---|---|---|---|---|
| Entrecalle | 3,0 m (SUPUESTO) | 2,5 m (FUENTE ODEPA) | 4.250 m/ha, unos 2,35 m | Con 2,5 m un robot cubre 29,9 ha y la finca de 30 ha necesita 2 |
| Velocidad | 0,8 m/s | 0,5 m/s | 0,4 m/s | Es la variable que más mueve el resultado |
| Camas por semana | 60 % | 50 % | 0,65 visitas por cama | - |
| **ha por robot** | **35,8** | **24,9** | **16,6** | El costo por ha del vendedor va de 354 a 621 USD (flota repartida) |
| Factor de importación del D1 | 1,12, sin IVA | 1,359, con IVA como costo | - | +27 USD/ha; margen de 23 % → 18 % |
| Nodos de sensores | 1 cada 2,5 ha; mantenimiento 10 % del CAPEX | 1 por ha; 130 USD por nodo al año | - | Red: 61 USD/ha frente a ~250 USD/ha (finanzas, opción B) |
| Falsas alarmas | No se cuentan | 5 por ha × 30 USD = 150 USD/ha/año | - | El costo del productor está subestimado |
| Fungicida ahorrado | 600 × 15 % = 90 USD/ha | 6 aplicaciones × 95 USD = 570 USD/ha | - | Finanzas supone 24 aplicaciones al año (SUPUESTO); Peña et al. reportan 130,8 USD/ha/año en agroquímicos |
| Costo anual del sistema, finca de 20 ha | El vendedor gasta 569 USD/ha con un robot entero (tabla 5d) | **722 USD/ha** si el productor es dueño | - | Las dos cifras están por encima de 520, el precio propuesto |
| Cifra "430 USD/ha y 72 kg" | Se usa para derivar 6 USD/kg | Desactualizada: hoy son 722 USD/ha y 120 kg/ha | - | `mercado.md` la usa como precio |

**Qué significa.** Finanzas tiene costos altos y beneficios altos: ahorra muchas aplicaciones. `modelo_negocio.md` tiene costos bajos y beneficios bajos. Cada uno es coherente por dentro, pero el pitch no puede mezclar un costo de un modelo con un ROI del otro. Hay que acordar un juego único para cuatro supuestos: entrecalle, velocidad, nodos por ha y falsas alarmas.

**Escenarios recalculados con `unit_economics.py`** (RaaS dedicado a 520 USD/ha, finca de 30 ha):

| Escenario | ha por robot | Margen (robots enteros) | Margen (flota repartida) | Precio para 23 % de margen (flota) | Precio máx. del productor (ROI 3x) |
|---|---|---|---|---|---|
| Base del modelo | 35,8 | 23 % | 32 % | 460 | 548 |
| Entrecalle de 2,5 m (finanzas) | 29,9 | -32 % | 23 % | 523 | 548 |
| Entrecalle de 2,2 m (Peña et al. 2023) | 26,3 | -32 % | 15 % | 574 | 548 |
| Supuestos de finanzas, opción F (2,5 m; 0,5 m/s; 50 %; +30 %) | 21,5 | -32 % | 1 % | 668 | 548 |
| Supuestos base de `operacion.md` (2,35 m; 0,4 m/s; 1,5 h; 65 %) | 16,4 | -29 % | -19 % | 806 | 548 |
| IVA de importación como costo | 35,8 | 18 % | 28 % | 489 | 548 |
| IVA como costo + 2,5 m + batería de 200 ciclos | 29,9 | - | 11 % | - | 548 |

---

## 6. Supuestos poco realistas o frágiles

1. **El margen sube y baja según el tamaño de la finca** (tabla 5d, robots enteros, camas a 3,0 m):

   | Finca (ha) | 15 | 20 | 25 | 30 | 35 | 40 | 50 | 60 | 70 | 100 |
   |---|---|---|---|---|---|---|---|---|---|---|
   | Robots | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 3 |
   | Margen RaaS a 520 | -42 % | **-9 %** | 10 % | 23 % | 32 % | **-2 %** | 15 % | 27 % | 36 % | 35 % |

   - El documento ofrece RaaS a fincas de "20 a 60 ha", pero solo gana en parte de ese rango.
   - Las fincas colombianas van de 5 a 30 ha (El Colombiano, 2026).
   - Para venderlo a muchos productores, el precio tiene que ser **por robot-cupo, con un mínimo**, o la flota tiene que compartirse entre fincas vecinas.
   - Con camas a 2,5 m y regla estricta de un robot por finca, el RaaS y el híbrido no llegan a EBIT ≥ 0 en ninguna escala. En la práctica se bajaría un poco la fracción de camas, pero el ejemplo muestra lo frágil que es el resultado.

2. **Utilización del robot.** El modelo supone 31 h por semana caminando: 7 h al día, 6 días, 80 % de disponibilidad y 93 % del tiempo en marcha. Son unas 1.600 h al año por robot.
   - Las reparaciones van a fábrica: 7 días hábiles más la logística (`operacion.md`, citando el manual).
   - La garantía del equipo es de 1 año.
   - El 80 % de disponibilidad es SUPUESTO y no descuenta esas paradas.
   - La reserva de 10 % de robots solo entra desde 5 robots.

3. **El tiempo del operario está subestimado.** Con 1,25 h de batería y 6 min por cambio hay unos 5 cambios al día, es decir ~31 min solo en baterías. El modelo supone 20 min. Con 40 min, el ROI del productor baja de 3,06x a **2,97x**, debajo del objetivo de 3x.

4. **IVA.** El modelo dice que no incluye impuestos.
   - Si el servicio está gravado, el productor paga 619 USD/ha, porque el arándano fresco se vende sin IVA y no puede descontarlo. Su ROI baja a **2,6x**.
   - Si el servicio está excluido, el vendedor no descuenta el IVA de la importación y su margen baja a **18 %**. Dos exclusiones podrían aplicar:
     - asistencia técnica agropecuaria, ET art. 476 num. 24 lit. s ([Concepto DIAN 905867 de 2022](https://www.ambitojuridico.com/sites/default/files/2022-09/Cpto-974%28905867%29-22.pdf));
     - computación en la nube, num. 21 ([INCP sobre el Oficio DIAN 100208192-190 de 2024](https://incp.org.co/agendatributariaincp/noticias/2024/05/dian-reafirmo-que-los-proveedores-de-servicios-en-la-nube-estan-excluidos-del-iva/)).
   - Qué régimen aplica y que el IVA pagado en una actividad excluida no se pueda descontar son puntos NO VERIFICADOS. Hay que consultarlos con un contador.

5. **Batería de repuesto a 450 USD (NO VERIFICADO).** Es la mayor partida de costo sin fuente: unos 1.940 USD al año por robot, el 27 % de su costo anual. AgiBot no la vende en su tienda.

   | Precio de la batería | 250 | 450 | 700 | 1.000 |
   |---|---|---|---|---|
   | Margen, finca de 30 ha | 30 % | 23 % | 15 % | 5 % |

6. **Estructura fija de 72.000 USD al año.** Cubre administración y una persona de ML, sin ventas, soporte ni expansión a otros países. Si fuera mayor, la escala mínima sube así:

   | Estructura fija | Híbrido | RaaS | Venta |
   |---|---|---|---|
   | 144.000 USD/año | 1.722 ha | 2.272 ha | 780 ha |
   | 240.000 USD/año | 2.939 ha | 3.444 ha | 1.385 ha |

   Esto refuerza la conclusión del documento: el negocio tiene que salir del arándano colombiano.

7. **El SaaS en mora, uchuva y aguacate usa el valor por ha del arándano** (tabla 11).
   - En mora (1,23 USD/kg en finca según SIPSA, 10 t/ha), el SaaS de 130 USD/ha más el kit da un ROI de **0,75x**.
   - Vigía a 60 USD/ha sin mínimo da ~1,1x, y el vendedor pierde 7 %.
   - Para aguacate no se calculó el ROI (falta el precio en finca: NO VERIFICADO).
   - Para que lo multicultivo escale, el producto tiene que llevar casi nada de hardware por finca: una estación virtual (tipo METOS, 336 EUR al año por ubicación) o una estación compartida por la asociación, más el celular.

---

## 7. Sospechas mías que no se confirmaron

| Sospecha | Resultado |
|---|---|
| 6 USD/kg es demasiado alto para el productor colombiano | **No se confirmó.** El Colombiano (2026-02-05) reporta unos 8 USD/kg en el mercado local, y Perú exportó a 6,22 USD/kg. El 4 USD/kg pesimista de finanzas sigue siendo un riesgo: con él, el ROI baja a 2,2x |
| 12 t/ha es un rendimiento inflado | **Solo en parte.** Forbes da 12.000 t en ~1.000 ha. EVA da 9,07 t/ha porque cuenta plantaciones jóvenes. Con 9,07 t/ha el ROI baja a 2,4x |
| Los precios de AgiBot, METOS, Davis y Dragino están mal leídos | **No.** Todos coinciden con su fuente |
| La batería no es extraíble | **No.** El manual confirma que se saca y se carga en base aparte |
| El área de Hass (72.444) choca con la de aguacate (141.051) | **No.** Hass es una parte del total en EVA |

---

## 8. Riesgos abiertos y decisiones pendientes

1. **Elegir un solo juego de supuestos de capacidad** (entrecalle, velocidad, fracción de camas) para finanzas, operación y negocio. Mientras no se elija, el pitch debería decir "entre 16 y 36 ha por robot".
2. **Cambiar la forma de cobrar el RaaS:** cuota por robot-cupo con mínimo, o flota compartida entre fincas. La tabla 5d muestra por qué.
3. **Medir en la semana 1 del piloto:** velocidad útil, ancho real de calle y minutos del operario. Después, cotizar el precio de la batería con AgiBot.
4. **Definir el régimen de IVA** del servicio con un contador antes de publicar el precio.
5. **Alinear `mercado.md` con `modelo_negocio.md`:** 520 y 130 USD/ha, 26.786 ha en Perú y Flota con D1 Ultra. Con esos precios y 35,8 ha por robot, el TAM es ~32,4 M, el SAM ~9,7 M y el SOM ~0,55 M USD al año, con ~28 robots (cálculo de esta verificación).
6. **Ajustar la diferenciación frente a Saga y Syngenta**, que ya detectan con cámara. Lo defendible es el paquete completo y la neutralidad, no "ver la enfermedad".
7. **Rehacer el valor por ha de cada cultivo** antes de proponer SaaS en mora, uchuva o aguacate. El modelo usa el del arándano.

---

## 9. Cómo reproducir

```bash
cd /Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad
python3 -I unit_economics.py --fuentes   # tablas 5d, 7 (corregida) y 9b (ampliada)
cd mercado && python3 -I calc_mercado.py
```
