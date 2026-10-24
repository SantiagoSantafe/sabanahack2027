# Modelo de negocio: vender la solución a muchos productores

Reto "Berry Good Idea", Sabana Hack, octubre de 2026. Rol: modelo-negocio.

**Archivos** (todos en esta carpeta):

- `unit_economics.py`: el modelo.
- `unit_economics_parametros.yaml`: 111 parámetros, cada uno con FUENTE o SUPUESTO.
- `unit_economics_salida.txt`: todas las tablas y el anexo de fuentes.
- `unit_economics_resultados.json`: los mismos resultados para otros agentes.

**Convención.**

- **FUENTE**: cifra leída en una URL que abrimos.
- **CALCULADO**: operación nuestra sobre una FUENTE.
- **CONTEXTO**: dato del equipo que este rol no verificó.
- **SUPUESTO**: valor nuestro.
- **PROPUESTA**: precio que proponemos.
- **NO VERIFICADO**: cifra vista en un resumen de búsqueda, sin abrir la página.

Los montos están en USD por año, salvo que se diga otra cosa. TRM: 3.185,01 COP/USD (2026-10-23, https://www.datos.gov.co/resource/32sa-8pi3.json).

---

## 1. Resumen

1. **El producto es un menú según el tamaño de la finca, no un precio único.**
   - Finca pequeña (unos 5 ha): compra la red de sensores con SaaS, a través de un canal.
   - Finca mediana (20 a 60 ha): toma el robot como servicio (RaaS).
   - Finca grande (100 ha o más): puede comprar el robot y pagar licencia y soporte.

   Ese es el modelo **híbrido**. Es el único que da al productor un ROI de 3x o más en los tres segmentos.
2. **Un D1 Ultra con mástil cubre unas 36 ha.** Supone inspeccionar a 0,8 m/s el 60 % de las camas cada semana, priorizadas por la red. Si recorre el 100 % de las camas, cubre 21,5 ha.
3. **Lo que más cuesta del robot es la batería, que se gasta como un consumible.**
   - El robot puesto en finca cuesta 11.599 USD.
   - Su costo anual es 7.084 USD, e incluye **unas 4,3 baterías repuestas por año**. El manual garantiza la celda por "6 months / 200 cycles", y el robot hace unos 1.300 ciclos al año.
4. **RaaS a 520 USD/ha/año** (unos 138.000 COP/ha/mes):
   - En una finca de 30 ha, el vendedor deja un margen bruto del 23 % y recupera su inversión en 23 meses. En 120 ha, el margen sube al 30 %.
   - El productor obtiene un ROI de 3,1x.
   - Su punto de equilibrio es salvar el equivalente a 90 kg/ha/año, el 0,75 % de 12 t/ha.
   - El precio máximo que acepta con ROI 3x es 548 USD/ha. La ventana de precio existe, pero es estrecha.
5. **La velocidad efectiva de inspección decide si el robot es negocio.**
   - A 0,4 m/s, que es la base de `operacion.md`, un robot cubre 17,9 ha. El RaaS pierde dinero: margen de -14 % aun con la flota bien repartida.
   - A 0,6 m/s el margen es 16 %, y a 0,8 m/s es 32 %.
   - Además, el manual pide "Keep the robot within your line of sight". Si eso obliga a que una persona nueva acompañe al robot, el ROI del productor cae a 1,7x.
   - Las dos cosas se miden en la semana 1 del piloto.
6. **El MaxPro solo como inspector no se paga.** Cuesta 820 USD/ha y deja un margen de -32 %. Solo tendría sentido si además hace la aspersión dirigida, porque carga 50 kg.
7. **Para cubrir una estructura fija de 72.000 USD/año, el híbrido necesita unas 1.070 ha bajo contrato.** Eso es el 118 % del arándano sembrado en Colombia (907 ha, EVA 2025). El negocio que vende la organización tiene que nacer multicultivo y multipaís:
   - fresa y mora, con o sin robot;
   - aguacate Hass, solo con la red y el SaaS;
   - Perú, con unas 30.000 ha de arándano.

---

## 2. Precios de referencia del mercado

| Referencia | Qué vende | Precio | Fuente |
|---|---|---|---|
| METOS / Pessl, modelo de enfermedad | Licencia de modelos de 1 cultivo por 1 año (requiere estación) | 96 EUR/año | FUENTE https://shop.metos.at/products/disease-model-license-for-1-year |
| METOS, estación virtual | Pronóstico y modelos de 1 cultivo por 1 año, sin hardware | 336 EUR/año | FUENTE https://shop.metos.at/products/imetos©-virtual-weather-station |
| METOS, hardware | iMETOS 3.3 completa, con humectación de hoja | 6.500 AUD | NO VERIFICADO (catálogo NSW DPI) |
| Davis WeatherLink | Suscripción Pro+ por equipo | 8,95 USD/mes (1 año) o 7,65 USD/mes (3 años) | FUENTE https://www.davisinstruments.com/weatherlink/ |
| Taranis (imágenes aéreas) | Scouting en cultivos de alto valor | 15-20 USD/acre por temporada, unos 37-49 USD/ha (2018) | FUENTE https://thespoon.tech/taranis-harvests-20m-for-aerial-imaging-tech-that-detects-crop-diseases |
| Aerobotics (dron y satélite) | Suscripción por ha al mes | R10/ha/mes más R100/ha por vuelo (2018) | NO VERIFICADO (la página de fin24 redirige) |
| Saga Robotics, Thorvald | Tratamiento UV-C como servicio, cuota fija por ha o acre. **Corregido en la verificación (2026-10-23):** desde 2025 sus máquinas llevan cámaras para detectar enfermedades y plagas ("We can also recognize outbreaks of diseases and pests") | No publicado | FUENTE https://www.futurefarming.com/tech-in-focus/field-robots/robot-combats-powdery-mildew-in-strawberries-using-uv-c-treatment/ y https://agfundernews.com/saga-robotics-raises-11-2m-to-expand-fleet-of-bots-blasting-powdery-mildew-with-uv-c-light |
| Saga Robotics, escala en EE. UU. | Más de 150 Thorvald y más de 1.300 acres de viñedo en 2025 | Unas 3,5 ha por robot (CALCULADO) | FUENTE https://www.agnavigator.com/Article/2025/08/14/saga-robotics-on-why-its-the-chasing-the-american-dream/ |
| Trapview (trampas inteligentes) | Una trampa vigila 20 ha | No publicado | FUENTE https://www.freshfruitportal.com/news/2025/10/16/trapview-fruit-attraction/ |
| Asesoría agronómica, Colombia | Finca de 1 ha en el altiplano | 1.000.000 COP/mes (unos 3.023 USD/año con la TRM de 2021) | FUENTE Peña et al. 2023, doi 10.15446/agron.colomb.v41n2.103525 (PDF en `raw/finanzas_agrocol2023`) |
| Nodo de humectación LoRaWAN | Dragino LLMS01 | 129 USD | FUENTE https://www.773grp.com/products/llms01-us915-dragino.oembed |
| AgiBot D1 Ultra | Cuadrúpedo IP54, 5 kg de carga útil, 1-2 h de batería | 9.600 USD de lista; 7.499 FOB México | FUENTE https://store.agibot.com/products/d1-ultra.json y la ficha https://www.agibot.com/file/ueditor/php/upload/file/20260825/1787637425866968.pdf; el 7.499 es CONTEXTO |
| Manual del D1 Ultra | Batería extraíble; celda con garantía de "6 months / 200 cycles"; "Keep the robot within your line of sight" | - | FUENTE https://www.agibot.com/file/ueditor/php/upload/file/20260911/1789114774395970.pdf |
| AgiBot D1 MaxPro | IP67, 50 kg de carga, 5,5 h sin carga | 65.999 USD sin accesorios; 67.999 según el equipo | FUENTE https://globaldronehq.com/products/agibot-d1-maxpro-quadruped-robot |

**Lectura de las referencias.**

- **Nadie publica un precio por "detección cama por cama + alerta + registro".**
- **Las estaciones cobran por modelo y por equipo, no por ha:** 96 EUR o unos 107 USD al año.
- **Las imágenes aéreas cobran por ha**, entre 37 y 49 USD por temporada, pero ven la planta desde arriba.
- **Saga cobra por hectárea tratada** y no publica la cuota.
- **Nuestro SaaS a 130 USD/ha/año** queda por encima de una licencia de estación y muy por debajo de una asesoría agronómica.
- **El RaaS a 520 USD/ha/año** se justifica por el valor que genera (sección 6), no por comparación.

---

## 3. Los cuatro modelos comparados (y el MaxPro)

| Modelo | Qué paga el productor | Quién pone el capital | Para quién | Ventaja | Límite |
|---|---|---|---|---|---|
| **Venta de equipo + licencia** | Robot a 15.659 USD (CAPEX × 1,35), kit de sensores, licencia de 90 USD/ha/año y soporte del 22 % del hardware al año (incluye baterías) | El productor | Fincas de 30 ha o más con equipo técnico | El vendedor cobra el hardware por adelantado y casi no necesita capital | En 5 ha el ROI es 0,8x: la finca pequeña no compra |
| **RaaS por ha/año** | 520 USD/ha/año si el robot es dedicado, 620 si va en ruta; todo incluido | El vendedor | Fincas medianas y grandes | El productor no arriesga capital; el vendedor controla la calidad del dato | 658.000 USD de CAPEX por cada 1.000 ha; payback de 19 a 37 meses frente a una vida de 36 meses |
| **SaaS por ha + kit de sensores** | 130 USD/ha/año, mínimo 450 USD por finca, más el kit de sensores (unos 1.314 USD en 5 ha) | El productor (poco) | Todas las fincas; es la puerta de entrada | Escala con software y sirve en cualquier frutal que tenga un modelo de enfermedad | Sin robot se evita la mitad de la pérdida (SUPUESTO); depende del scouting con celular |
| **Híbrido (recomendado)** | Pequeñas: SaaS + kit por canal. Medianas: RaaS. Grandes: compra o RaaS | Mixto | Toda la cartera | ROI de 3x o más en todos los segmentos; la mitad del capital del RaaS puro | Hay que operar y vender tres productos |
| MaxPro compartido | 620 USD/ha/año | El vendedor | Solo si además aplica producto | IP67 (trabaja con lluvia) y 50 kg de carga | Cuesta 820 USD/ha solo para inspeccionar |

En Colombia el arándano produce todo el año (Peña et al. 2023). Por eso el contrato es anual, con cuotas mensuales. En Perú y Chile se cobraría por temporada.

---

## 4. Capacidad de un robot (salida, tablas 1 y 2)

| Robot y modo | Horas de robot por ha (1 pasada) | % de la ventana caminando | Horas útiles/semana | ha/semana con 100 % de camas | ha por robot con 60 % de camas/semana |
|---|---|---|---|---|---|
| D1 Ultra dedicado (finca de 20 ha o más) | 1,45 | 93 % | 31,1 | 21,5 | **35,8** |
| D1 Ultra en ruta (fincas pequeñas) | 1,45 | 93 % | 26,7 | 18,4 | 30,7 |
| D1 MaxPro compartido | 1,45 | 97 % | 51,8 | 35,8 | 59,7 |

| Robot | Precio | CAPEX puesto en finca | Vida (años) | Depreciación/año | Baterías repuestas/año | Mantenimiento + seguro + baterías/año | Costo anual | Costo por ha cubierta |
|---|---|---|---|---|---|---|---|---|
| D1 Ultra + mástil | 7.499 | 11.599 | 3 | 3.866 | 4,3 | 3.217 | 7.084 | 198 |
| D1 MaxPro + mástil | 67.999 | 83.659 | 5 | 16.732 | 0,7 | 11.448 | 28.180 | 472 |

**Cómo se calcula** (todos los valores son SUPUESTOS, salvo que diga FUENTE):

- **Pasillo por ha.** Con camas a 3,0 m hay 3.333 m de pasillo por ha. El pasillo de 2,0 m sale de PROMPT_simulacion_camas.md.
- **Tiempo por ha.** A 0,8 m/s, con 25 % extra por giros y paradas, son 1,45 h.
- **Batería.**
  - Dura 1,25 h con el mástil; la ficha dice 1-2 h.
  - Se trabaja con dos baterías de repuesto.
  - La batería es extraíble según el manual (FUENTE) y se cambia con el robot apagado, en unos 6 minutos.
  - Su vida útil es de 300 ciclos (SUPUESTO) y cada una cuesta 450 USD (NO VERIFICADO).
- **Ventana de trabajo.** 7 h al día sobre hoja seca, 6 días a la semana, con 80 % de disponibilidad, porque con IP54 no sale con lluvia fuerte.
- **MaxPro.** Los ~60 ha del contexto cuadran con estos supuestos: 12 h de ventana gracias al IP67, 1,5 h de traslado y 60 % de camas. `operacion.md` llega a 26 ha en su escenario base y a 53 ha en el optimista.

---

## 5. Economía unitaria por segmento (salida, tablas 5, 5b y 5c)

Las cifras son en régimen: muchas fincas iguales, con técnicos y agrónomo repartidos en fracciones y sin estructura fija.

| Segmento y plan | Precio de lista/ha | Ingreso vendedor/ha | Costo vendedor/ha | Margen bruto | CAPEX vendedor por finca | Payback por finca (meses) | Costo total productor/ha | ROI productor | Equilibrio productor (kg/ha) |
|---|---|---|---|---|---|---|---|---|---|
| RaaS en ruta, finca de 5 ha | 620 | 620 | 608 | 2 % | 3.745 | 37 | 638 | 2,6x | 106 |
| **RaaS dedicado, finca de 30 ha** | 520 | 520 | 401 | **23 %** | 17.287 | 23 | 537 | **3,1x** | 90 |
| RaaS dedicado, finca de 120 ha | 520 | 520 | 365 | 30 % | 61.048 | 19 | 537 | 3,1x | 90 |
| SaaS + kit, finca de 5 ha | 130 | 196 | 171 | 12 % | 800 | 25 | 228 | 3,4x | 38 |
| SaaS + kit, finca de 30 ha | 130 | 185 | 87 | 53 % | 800 | 3 | 211 | 3,6x | 35 |
| **SaaS + kit por canal y autoinstalable, finca de 5 ha** | 130 | 196 | 135 | **31 %** | 250 | 8 | 228 | **3,4x** | 38 |
| Venta + licencia, finca de 5 ha | 90 | 1.946 | 1.654 | 15 % | 800 | 6 | 2.125 | **0,8x** | 354 |
| Venta + licencia, finca de 30 ha | 90 | 482 | 347 | 28 % | 800 | 2 | 515 | 3,2x | 86 |
| Venta + licencia, finca de 120 ha | 90 | 452 | 319 | 29 % | 800 | 1 | 482 | 3,4x | 80 |
| MaxPro compartido, finca de 30 ha | 620 | 620 | 820 | **-32 %** | 48.354 | 145 | 620 | 2,7x | 103 |

En SaaS y en Venta, el ingreso del vendedor incluye el hardware vendido, anualizado por su vida útil. El costo del productor suma el tiempo de su operario y, si compra, el hardware anualizado.

**Desglose del costo del vendedor (USD por ha y año):**

| Rubro | RaaS dedicado 30 ha | RaaS ruta 5 ha | SaaS canal 5 ha | Venta 120 ha | MaxPro 30 ha |
|---|---|---|---|---|---|
| Depreciación del robot | 129 | 131 | 0 | 0 | 284 |
| Mantenimiento, seguro y baterías del robot | 107 | 109 | 0 | 0 | 195 |
| Red de sensores | 61 | 74 | 0 | 0 | 61 |
| Hardware vendido (anualizado) | 0 | 0 | 49 | 158 | 0 |
| Repuestos y baterías del soporte | 0 | 0 | 0 | 107 | 0 |
| Técnicos u operadores | 64 | **209** | 39 | 21 | 241 |
| Agrónomo remoto | 27 | 27 | 27 | 27 | 27 |
| Nube | 4 | 4 | 4 | 4 | 4 |
| Instalación + CAC | 9 | 53 | 17 | 2 | 9 |
| **Total** | **401** | **608** | **135** | **319** | **820** |

**Qué dice el desglose:**

- **El robot es el 59 % del costo RaaS** (236 de 401 USD/ha). De eso, 65 USD/ha son reposición de baterías: 4,3 al año × 450 USD / 30 ha.
- **En la finca pequeña, lo que más pesa es el técnico que mueve el robot** (209 USD/ha), no el robot. Por eso a la finca pequeña se le vende SaaS por un canal, no robot en ruta.
- **El margen del RaaS dedicado (23 %) está lejos del 45 %** que suele pedir un negocio de hardware como servicio.
  - Ese 23 % corresponde a un robot entero usado al 84 % en una finca de 30 ha.
  - Con la flota bien repartida entre fincas, el margen base es 32 % (tabla 9 de la salida).
  - Para acercarse al 45 %:
    - vida del robot de 4 años: 37 %;
    - ventana de 9 h al día: 40 %;
    - batería más barata o con más ciclos;
    - subir el precio a 664-729 USD/ha, aunque eso supera el máximo que acepta el productor con ROI 3x (548).

**Palancas para la finca pequeña de 5 ha** (tabla 5b de la salida):

| Palanca | Margen del vendedor | ROI del productor |
|---|---|---|
| SaaS base (CAC 500, instalación 300) | 12 % | 3,4x |
| Venta por canal: asociación, exportadora o casa de insumos (CAC 150) | 24 % | 3,4x |
| Canal + kit autoinstalable | 31 % | 3,4x |
| Canal + autoinstalable + SaaS a 160 USD/ha | 40 % | 3,0x |
| Robot en ruta con canal y 1 técnico por cada 10 robots | 14 % | 2,6x |

---

## 6. Precio que hace atractivo el ROI del productor (salida, tablas 4 y 10)

| Paquete | Cosecha salvada | Fungicida ahorrado | Scouting ahorrado | Valor/ha/año | Precio máx./ha con ROI 3x | Equilibrio (ROI 1x) |
|---|---|---|---|---|---|---|
| Red + robot | 1.440 | 90 | 115 | 1.645 | **548** | 1.645 USD/ha, es decir 274 kg/ha |
| Solo red + SaaS | 720 | 48 | 0 | 768 | **256** | 768 USD/ha, es decir 128 kg/ha |

**Base de cálculo:**

- Rendimiento de 12 t/ha (CONTEXTO). El promedio nacional EVA 2025 es 9,07 t/ha cosechada.
- Precio de 6 USD/kg (CALCULADO a partir del equipo). La exportación de 2024 sale a 5,25 USD/kg (https://agraria.pe/noticias/colombia-exporto-628-235-kilogramos-de-arandano-en-2024-gene-39081).
- Pérdida evitada: 2 % con robot y 1 % solo con la red (SUPUESTO).
- Gasto en fungicida: 600 USD/ha/año (NO VERIFICADO).

**Sensibilidad: precio máximo con ROI 3x, en USD/ha.**

| Pérdida evitada | 4 USD/kg | 6 USD/kg |
|---|---|---|
| 0,6 % (equilibrio del equipo) | 164 | 212 |
| 1 % | 228 | 308 |
| 2 % | 388 | 548 |
| 4 % | 708 | 1.028 |

**Precios que proponemos:**

- **Plan con robot: 520 USD/ha/año** (unos 1,66 M COP/ha/año o 138.000 COP/ha/mes).
  - El productor recupera lo que paga (equilibrio) si el paquete le da el equivalente a 90 kg/ha, el 0,75 % de su cosecha.
  - Para obtener 3x hay que evitar cerca del 2 % de pérdida.
  - Si el piloto mide menos del 1,5 % (ROI de 2,4x), el robot se ofrece solo en la temporada de mayor riesgo y el plan base pasa a ser SaaS.
- **Plan SaaS: 130 USD/ha/año** (unos 414.000 COP/ha/año o 34.500 COP/ha/mes).
  - El productor llega al equilibrio con 38 kg/ha, el 0,3 % de su cosecha.

---

## 7. Resultados por escala: 10, 50, 200 y 1.000 ha bajo contrato (salida, tablas 6.1 a 6.4)

**Mezcla de fincas en cada escala** (SUPUESTO):

| Escala | Fincas pequeñas | Medianas | Grandes |
|---|---|---|---|
| 10 ha | 100 % | 0 % | 0 % |
| 50 ha | 60 % | 40 % | 0 % |
| 200 ha | 40 % | 60 % | 0 % |
| 1.000 ha | 30 % | 50 % | 20 % |

La estructura fija es de 72.000 USD/año.

| Escala (ha) | Modelo | Robots | Técnicos | Ingreso/año | Margen bruto | EBIT tras estructura fija | CAPEX vendedor | Payback (meses) | Costo productor/ha | ROI productor |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | Venta | 2 | 1 | 19.463 | -165 % | -104.064 | 1.600 | n/a | 2.125 | 0,8x |
| 10 | RaaS | 1 | 1 | 6.200 | -629 % | -111.000 | 15.145 | n/a | 672 | 2,4x |
| 10 | SaaS + kit | 0 | 1 | 1.957 | -1.835 % | -107.905 | 1.600 | n/a | 228 | 3,4x |
| 10 | Híbrido | 0 | 1 | 1.957 | -1.816 % | -107.539 | 500 | n/a | 228 | 3,4x |
| 10 | MaxPro | 1 | 2 | 6.200 | -1.401 % | -158.877 | 87.205 | n/a | 620 | 2,7x |
| 50 | Venta | 7 | 1 | 71.324 | -25 % | -90.099 | 5.600 | n/a | 1.554 | 1,1x |
| 50 | RaaS | 2 | 1 | 29.000 | -96 % | -99.742 | 38.528 | n/a | 601 | 2,7x |
| 50 | SaaS + kit | 0 | 1 | 9.784 | -322 % | -103.518 | 5.600 | n/a | 228 | 3,4x |
| 50 | Híbrido | 1 | 1 | 16.270 | -194 % | -103.524 | 17.791 | n/a | 355 | 3,2x |
| 50 | MaxPro | 2 | 2 | 31.000 | -306 % | -166.715 | 182.648 | n/a | 620 | 2,7x |
| 200 | Venta | 20 | 1 | 213.571 | 11 % | -48.368 | 16.000 | 7 | 1.159 | 1,4x |
| 200 | RaaS | 8 | 2 | 112.000 | -20 % | -94.428 | 143.911 | 76 | 578 | 2,8x |
| 200 | SaaS + kit | 0 | 1 | 37.853 | -37 % | -85.863 | 16.000 | n/a | 218 | 3,5x |
| 200 | Híbrido | 4 | 1 | 78.054 | -2 % | -73.497 | 73.148 | 41 | 414 | 3,1x |
| 200 | MaxPro | 6 | 4 | 124.000 | -142 % | -247.885 | 553.073 | n/a | 620 | 2,7x |
| 1.000 | Venta | 83 | 3 | 913.959 | 19 % | 100.158 | 63.200 | 4 | 990 | 1,7x |
| 1.000 | RaaS | 37 | 5 | 550.000 | 11 % | -10.848 | 657.555 | 30 | 567 | 2,9x |
| 1.000 | SaaS + kit | 0 | 1 | 185.754 | 35 % | -6.118 | 63.200 | 9 | 212 | 3,6x |
| 1.000 | **Híbrido** | 25 (19 propios, 2 de ellos de reserva, y 6 vendidos) | 3 | 403.740 | 16 % | -7.997 | **333.675** | **24** | 428 | **3,2x** |
| 1.000 | MaxPro | 21 | 12 | 620.000 | -63 % | -463.786 | 1.985.232 | 1.085 | 620 | 2,7x |

"Robots" incluye la reserva y los robots vendidos. "Técnicos" incluye a los operadores del MaxPro. El payback es el CAPEX del vendedor dividido por la contribución de caja mensual, antes de la estructura fija.

**Lectura de la tabla.**

- **Entre 10 y 200 ha ningún modelo cubre la estructura fija.** Es la etapa de piloto y hay que financiarla, por ejemplo con un aliado comercial o un fondo de innovación.
- **La venta pura es la única con EBIT positivo en 1.000 ha (100.158 USD), pero es engañosa.** Cobra margen de hardware a fincas de 5 ha que, con un ROI de 0,8x, no comprarían.
- **El híbrido y el RaaS tienen un EBIT parecido en 1.000 ha** (-7.997 frente a -10.848 USD), pero el híbrido:
  - usa la mitad del capital (333.675 frente a 657.555 USD);
  - recupera la inversión antes (24 frente a 30 meses);
  - deja al productor con 3,2x en vez de 2,9x.

---

## 8. Por qué el negocio tiene que salir del arándano (salida, tablas 7 y 11)

| Modelo | ha mínimas para EBIT ≥ 0 | Fincas | % del arándano en Colombia (907 ha) | CAPEX acumulado |
|---|---|---|---|---|
| Venta + licencia (pura, incluye fincas de 5 ha que no comprarían) | 439 | 45 | 48 % | 36.000 |
| RaaS (**corregido** en la verificación del 2026-10-23; antes decía 1.071 ha) | 1.358 | 108 | 150 % | 903.492 |
| SaaS + kit | 1.071 | 85 | 118 % | 68.000 |
| **Híbrido** | **1.071** | 85 | **118 %** | 352.212 |
| MaxPro compartido | más de 100.000 | - | - | - |

**Mercado alcanzable con 5 % de adopción** (SUPUESTO):

| Cultivo | ha | Fuente | Plan | Ingreso/año con 5 % |
|---|---|---|---|---|
| Arándano, Colombia | 907 | EVA 2025, https://www.datos.gov.co/resource/uejq-wxrr.json | RaaS | 23.582 |
| Fresa, Colombia | 3.767 | EVA 2025 | RaaS (falta validar el robot en fresa) | 97.942 |
| Uchuva, Colombia | 1.810 | EVA 2025 | SaaS + kit | 11.765 |
| Mora, Colombia | 15.952 | EVA 2025 | SaaS + kit | 103.688 |
| Aguacate Hass, Colombia | 72.444 | EVA 2025 | SaaS + kit (el mástil no alcanza la copa) | 470.886 |
| Arándano, Perú | unas 30.000 | https://agraria.pe/noticias/superficie-de-arandanos-en-peru-crecio-12-en-2025-paso-de-26-41486 | RaaS | 780.000 |
| **Total** | | | | **1.487.863** |

`mercado.md`, de otro agente, calcula un SOM de unos 0,45 M USD/año a 5 años, con otros precios y otras adopciones. Estas dos cifras no se suman: son estimaciones distintas del mismo mercado.

**Qué se necesita para escalar:**

1. **Software que no dependa del cultivo.**
   - Los modelos de riesgo, las alertas, el registro y el clasificador funcionan con la cámara del robot o con la de un celular.
   - Cada frutal nuevo pide un modelo de enfermedad y un conjunto de imágenes, no hardware nuevo.
   - METOS dice tener más de 80 modelos para más de 45 cultivos (NO VERIFICADO, visto en búsqueda). Un modelo por cultivo es el estándar de la industria.
2. **El robot va solo donde se paga.** Camas y espalderas de cultivos de alto valor: arándano, fresa y, quizá, mora. En el aguacate y en los frutales altos se vende solo la red y el SaaS.
3. **Parámetros por región.** El clima de la Sabana es solo el ejemplo de la demo. Con el YAML se recalculan la ventana de trabajo, la disponibilidad con lluvia y el valor por ha de cada cliente o país, sin tocar el código.

---

## 9. Lista de precios propuesta (para el pitch)

| Plan | Para quién | Incluye | Precio |
|---|---|---|---|
| **Red** (SaaS + kit) | Todas las fincas; es la entrada. A la finca pequeña se llega por la asociación, la exportadora o la casa de insumos | Nodos LoRaWAN de humectación y temperatura/humedad, gateway, modelos de riesgo por cultivo, alertas con triage, registro cama por cama y clasificador con foto de celular | Kit desde unos 1.314 USD (finca de 5 ha) + 130 USD/ha/año, mínimo 450 USD por finca |
| **Red + Robot** (RaaS) | Fincas de 20 ha o más | Todo el plan Red, más un D1 Ultra con mástil que recorre las camas delante del aspersor, mapa de calor, técnico, repuestos y baterías | 520 USD/ha/año, cobrados cada mes |
| **Compra** | Fincas de 100 ha o más con equipo técnico | Robot con mástil a 15.659 USD, kit de red, licencia y soporte con baterías | 90 USD/ha/año de licencia + 22 % del hardware al año de soporte |

---

## 10. Encaje en la operación de la finca (Pertinencia)

| Paso | Quién | Tiempo o costo | Qué cambia frente a hoy |
|---|---|---|---|
| La red marca los bloques y camas de riesgo alto | Automático | Incluido | El riesgo deja de estimarse a ojo o por calendario |
| El robot recorre esas camas delante del aspersor, sobre hoja seca | Robot; el operario cambia la batería | 20 min/día por robot, unos 517 USD/año de operario (SUPUESTO) | Reemplaza el 25 % del recorrido del monitor (SUPUESTO) |
| La alerta va al agrónomo, que decide; el operario confirma o descarta en la cama | Agrónomo de la finca o remoto, y operario | Agrónomo remoto incluido (1 por cada 1.500 ha) | Cada hallazgo queda con fecha, cama y foto |
| Se aplica producto solo en las camas confirmadas | Equipo de aspersión de la finca | 15 % menos fungicida (SUPUESTO) | Se aplica por cama, no por bloque |
| El registro y el mapa de calor quedan para auditoría y para el siguiente ciclo | Plataforma | Incluido | Evidencia trazable para el comprador o la exportadora (no cuantificada) |

Si el fabricante exige línea de vista, el monitor que ya recorre la finca camina con el robot. En ese caso la finca no ahorra scouting y el ROI baja a 2,8x. Si la finca tuviera que contratar a una persona nueva para acompañarlo, el ROI caería a 1,7x (tabla 9b de la salida).

---

## 11. Límites y qué hay que validar (Justificación)

De 111 parámetros, 93 son SUPUESTO, PROPUESTA o NO VERIFICADO (eran 94; la verificación del 2026-10-23 confirmó en el manual la carga de ~1 h de 10 a 90 %). Los que más mueven el resultado (tablas 8, 9 y 9b de la salida):

| Riesgo | Base | Si sale mal | Efecto en el RaaS dedicado |
|---|---|---|---|
| Velocidad efectiva con fotos útiles | 0,8 m/s | 0,4 m/s (base de `operacion.md`) | De 35,8 a 17,9 ha por robot; margen de -14 % aun con la flota repartida |
| | | 0,6 m/s | Margen de 16 % con la flota repartida; -32 % si la finca necesita 2 robots enteros |
| Ciclos de vida de la batería | 300 | 200 (lo que cubre la garantía) | Margen de 27 % (flota repartida) o 17 % (robots enteros) |
| Batería extraíble | Sí (manual) | Si hubiera que cargarla dentro del robot | Margen de 8 % |
| Línea de vista | No hace falta acompañar al robot | Se contrata a alguien que lo acompañe | ROI del productor de 1,7x |
| Distancia entre camas | 3,0 m | 2,0 m | Margen de 9 % |
| Pérdida evitada | 2 % | 0,6 % | El productor paga como máximo 212 USD/ha con ROI 3x, y el robot no se vende |
| Vida del robot | 3 años | 2 años o 4 años | 21 % o 37 % de margen |
| Precio del D1 Ultra | 7.499 (CONTEXTO) | 9.600 (lista) | +29 USD/ha; margen de 26 % |
| Entrecalle (añadido en la verificación) | 3,0 m | 2,5 m (ODEPA, base de finanzas) o 2,2 m (Peña et al. 2023, Cundinamarca) | 29,9 o 26,3 ha por robot; la finca de 30 ha necesita 2 robots y el margen cae a -32 % (23 % o 15 % con flota repartida) |
| IVA de importación (añadido en la verificación) | Se descuenta | Es costo si el servicio queda excluido de IVA (factor 1,359 de finanzas) | Margen de 18 % (28 % con flota repartida) |
| IVA sobre el precio (añadido en la verificación) | No se cobra | Servicio gravado al 19 % que el productor no recupera | ROI del productor de 2,6x |

**Lo que el modelo no incluye:** impuestos, costo financiero del CAPEX, churn explícito (solo se amortiza el CAC en 3 años), comisión del canal (va como CAC), seguro agrícola, subsidios, ni el MaxPro haciendo aspersión.

**Frente a Saga Thorvald.** *Corregido en la verificación (2026-10-23).* Thorvald trata con UV-C y, según AgFunderNews (2025-08-08), sus máquinas nuevas ya llevan cámaras para detectar enfermedades y plagas, así que no se puede decir que "no diagnostica". Nuestra diferencia es otra: riesgo por clima + confirmación cama por cama + triage + registro, sin depender de un tratamiento propio. En EE. UU. tiene unas 3,5 ha por robot (150 robots, 1.300 acres, FUENTE agnavigator.com); que eso se deba a que "trata casi todas las noches" es NO VERIFICADO. Nuestro robot inspecciona entre 16 y 36 ha según la velocidad y el ancho de calle (tablas 5d, 8 y 9b). Los dos servicios pueden complementarse, pero Saga también es competidor directo en detección.

**Frente a drones y satélite (Taranis, Aerobotics).** Cuestan menos por ha (unos 37-49 USD por temporada), pero ven la planta desde arriba. Que el robot detecte antes, por ver el envés de la hoja y el interior de la cama, es un SUPUESTO que el piloto tiene que medir.

**Qué medir en el piloto (en orden):**

1. Velocidad efectiva a la que las fotos siguen siendo útiles (m/s).
2. Si hace falta que una persona acompañe al robot.
3. Horas por batería con el mástil y ciclos reales de la batería.
4. Minutos diarios del operario.
5. Porcentaje de camas que pide el modelo de riesgo.
6. Kg salvados en camas testigo frente a camas monitoreadas.

---

## 12. Frases para el pitch

- "No vendemos un perro robot: vendemos un registro cama por cama. Un D1 Ultra cubre unas 36 ha. Al productor le cuesta 520 USD por ha al año y recupera lo que paga si salva 90 kg por ha, menos del 1 % de su cosecha."
- "La finca pequeña entra con sensores y celular a 130 USD por ha al año, a través de su asociación. La mediana toma el robot como servicio y la grande lo compra. Cada una recibe al menos 3 dólares por cada dólar que paga."
- "El negocio se paga desde unas 1.100 ha, más que todo el arándano de Colombia. Por eso el software sirve para cualquier frutal y el robot va solo donde rinde: arándano, fresa y Perú."

---

## 13. Cómo reproducir

```bash
cd /Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad
python3 -I unit_economics.py                      # tablas en markdown
python3 -I unit_economics.py --fuentes            # más el anexo con la fuente de cada parámetro
python3 -I unit_economics.py --json unit_economics_resultados.json
```

El script usa solo la biblioteca estándar. Si PyYAML está instalado, lo usa; comprobamos que el lector mínimo y PyYAML dan la misma salida. Para recalcular con otro cultivo, otra región u otro precio, se edita `unit_economics_parametros.yaml`.

---

## 14. Nota de verificación de negocio (2026-10-23)

Un verificador adversario revisó este documento. El detalle está en `datos/reportes/escala-verificacion-negocio.md`. Re-ejecutó `unit_economics.py` y recalculó a mano dos filas: RaaS dedicado de 30 ha (401 USD/ha, 23 %, 23 meses, ROI 3,06x) y SaaS por canal de 5 ha (135 USD/ha, 31 %, 8 meses, ROI 3,37x). Las dos cuadran.

**Cambios hechos en esta carpeta**

| Archivo | Cambio | Por qué |
|---|---|---|
| `unit_economics.py`, tabla 7 | La búsqueda de la escala mínima exige ahora EBIT ≥ 0 en todos los puntos hasta 1,5 veces la escala, no solo en el punto 1,5x | El RaaS salía en 1.071 ha, pero volvía a pérdida entre unas 1.090 y 1.350 ha. El valor corregido es **1.358 ha (150 % del arándano colombiano)**. Venta, SaaS e híbrido no cambian |
| `unit_economics.py`, tabla 5d (nueva) | Margen del RaaS dedicado según el tamaño de la finca, con robots enteros | Ver la lectura de abajo |
| `unit_economics.py`, tabla 9b | Cuatro filas nuevas: entrecalle de 2,5 m y de 2,2 m, IVA de importación como costo y operario 40 min/día | Son supuestos de otras fuentes del proyecto que el modelo no mostraba |
| `unit_economics_parametros.yaml` | `carga_h` pasa a FUENTE (manual). Las notas de `importacion_frac` y `distancia_entre_camas_m` llevan advertencias. Los valores no cambian | El manual dice "about 1 hour (battery level 10%-90%)" |
| Este documento | Saga: se corrige "no diagnostica". Tabla 8: se corrige la fila RaaS. Sección 11: tres filas de riesgo nuevas | AgFunderNews, 2025-08-08: "We can also recognize outbreaks of diseases and pests" |

**Lo que hay que saber antes del pitch**

1. **El 23 % de margen de la finca de 30 ha está en un punto favorable de la tabla 5d.**
   - Con robots enteros, la finca de 20 ha (la de referencia del equipo) da -9 % y la de 40 ha da -2 %.
   - Con camas a 2,5 m (el valor de finanzas), un robot cubre 29,9 ha. Con la regla estricta de robots enteros, la finca de 30 ha necesita 2 robots y da -32 %. Con esa misma regla, el RaaS y el híbrido no llegan a EBIT ≥ 0 en ninguna escala. En la práctica bastaría bajar la fracción de camas de 60 % a 59,8 %, pero el ejemplo muestra lo frágil que es el resultado.
   - Por eso el plan RaaS necesita un **cobro mínimo por robot instalado**, por ejemplo el equivalente a 25 ha. La otra opción es compartir el robot entre fincas vecinas.
2. **La capacidad de 36 ha por robot es la más optimista de los tres modelos del equipo.**
   - Este documento: 35,8 ha (3,0 m, 0,8 m/s).
   - Finanzas, opción F: 24,9 ha (2,5 m, 0,5 m/s).
   - `operacion.md`: 16,6 ha (0,4 m/s).
   - Con los supuestos de finanzas, para tener 23 % de margen el precio debe ser unos 668 USD/ha. Eso supera los 548 USD/ha que acepta el productor con ROI 3x. **La ventana de precio del robot solo existe con los supuestos de este documento.**
3. **Mora con SaaS a 130 USD/ha no se paga.** Con el precio SIPSA en finca (1,23 USD/kg) y 10 t/ha, el ROI del productor es 0,75x, porque el kit de sensores le cuesta unos 98 USD/ha/año. Las filas de mora, uchuva y aguacate de la tabla 11 usan el valor por ha del arándano. Ese valor no aplica a esos cultivos. En cultivos de bajo valor, la oferta escalable tiene que poner poco hardware por finca: una estación virtual o compartida por la asociación, más el celular.
4. **El precio de 520 USD/ha puede no incluir IVA.**
   - Si el servicio está gravado, el productor paga 619 USD/ha y su ROI baja a 2,6x.
   - Si el servicio está excluido de IVA, el vendedor no puede descontar el IVA del robot importado y su margen baja a 18 %. Las exclusiones posibles son la asistencia técnica agropecuaria (ET art. 476 num. 24 lit. s, citado en el Concepto DIAN 905867 de 2022) y la computación en la nube (num. 21).
   - Qué régimen aplica está NO VERIFICADO y hay que consultarlo con un contador.
5. **Frase de pitch más segura:** "Un D1 Ultra cubre entre 16 y 36 ha según la velocidad que midamos en la semana 1. Por eso el contrato fija el número de robots después de esa medición y cobra un mínimo por robot."
