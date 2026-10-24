# Verificación adversaria: finanzas, robots y revisión del documento

Fecha: 2026-10-23. Rol: verificador adversario. Revisé el trabajo de tres agentes: finanzas (`reportes/finanzas.md`, `finanzas/`), robots-competencia (`reportes/robots-competencia.md`) y revision-documento (`reportes/revision-documento.md`). Partí de que había errores y traté de refutarlos. El documento del equipo (Claude Doc `9c0a5374…`, revisión 22) lo leí en modo solo lectura: no lo edité ni lo comenté.

## Resultado en breve

- **El modelo financiero se reproduce bit a bit.** `roi.py` da los mismos 8 CSV con `.venv/bin/python -I` y con `python3 -I`. Recalculé a mano tres filas (F, B y A a 20 ha), además de F en el escenario pesimista, y todas coinciden.
- **Encontré y corregí un error de dato.** El SMMLV 2026 subió **23,0 %** (de 1.423.500 a 1.750.905 COP), no 23,7 %. El valor de 1.750.905 COP es correcto. El error no cambia ninguna salida.
- **TRM, arancel e IVA quedan confirmados contra las fuentes.** También las especificaciones del D1 Ultra, del D1 EDU y del D1 MaxPro, y los precios de la tienda.
- **Cuatro veredictos de revision-documento quedan refutados o matizados:**
  - **Punto 11, FOB de Perú:** el 6,22 sí existe en otro artículo de Gestión. El problema es el enlace, no la cifra.
  - **Punto 16, MaxPro y Genie:** la cifra del documento sí se puede reproducir. Su alternativa (~1.720) aplica a un robot de 68.000 USD el mantenimiento de un D1.
  - **Punto 34, LiDAR de 96 líneas del MaxPro:** está verificado en el GitHub oficial.
  - **Punto 5, DrBerry:** el recall de la mejor configuración es 92,6 %, no 94 %.
- **La matriz de alternativas cuadra:** 73 / 75 / 68 / 42 / 69 / 83, y la sensibilidad da 80 / 81. Pero el resultado depende de los pesos: la red fija (B) le gana al híbrido (F) en el 25 % de las combinaciones de pesos probadas.
- **Riesgo principal para el pitch:** el documento y el modelo financiero dicen cosas distintas.

  | Opción | Documento | Modelo |
  |---|---|---|
  | A (D1 Ultra + mástil) | 320 USD/ha/año, ROI 4,7× | 820 USD/ha/año, ROI 0,83 (necesita 2 robots) |
  | F (híbrido) | 430 USD/ha/año, ROI 3,3× | 722 USD/ha/año, ROI 2,38 |

  Hay que elegir un solo juego de cifras.

---

## 1. Qué hice

1. Copié `roi.py` y `parametros.yaml` al scratchpad y los ejecuté con los dos intérpretes. Comparé byte a byte las salidas con las publicadas en `finanzas/`.
2. Escribí un recálculo independiente que no importa `roi.py` ni lee el YAML: `reportes/verificacion-finanzas-robots-documento_scripts/recalculo.py`. Recalcula las filas F, B y A a 20 ha, F pesimista, sensibilidades nuevas, la matriz con un barrido de pesos y las cifras que cita el revisor.
3. Contrasté con las fuentes que abrí hoy:
   - SMMLV: buk.co, El Tiempo y Portafolio.
   - TRM: API de datos.gov.co, en vivo.
   - Arancel: compilación DIAN del Decreto 1881 de 2021.
   - IVA: estatuto.co, artículos 468 y 459.
   - Robots: ficha D1 Ultra, ficha D1 Pro/Edu, guía SDK V2.0.7 y manual EN (extraídos con `pdftotext`), GitHub oficial de AgiBot (D1 Edu-Ultra y D1 MaxPro), tienda AgiBot en vivo y agibot.com/products/D1_Pro.
4. Revisé cada corrección de `revision-documento.md` que toca finanzas, robots o la matriz. Volví a abrir las fuentes de prensa que cita: Gestión (los dos artículos), Forbes, El Tiempo, Agronegocios, Portal Frutícola y FarmingUK. También el paper DrBerry local y las tablas del documento: matriz, finanzas y cultivo.

## 2. Re-ejecución de `roi.py` y filas recalculadas a mano

- `.venv/bin/python -I roi.py` y `python3 -I roi.py` producen los 8 CSV **idénticos** a los publicados. El script consulta `site.getusersitepackages()`, así que también corre con el Python del sistema.
- Recálculo independiente (`recalculo.py`):

| Fila (20 ha, base) | CAPEX USD | Costo USD/ha/año | Beneficio USD/ha/año | ROI | Payback (años) | Equilibrio kg/ha (solo fruta) | ¿Coincide? |
|---|---|---|---|---|---|---|---|
| F híbrido (1 D1 + 20 nodos + 1 gateway) | 17.489,14 | 722,24 | 2.441,47 | 2,380 | 0,43 | 13,5 (120,4) | Sí |
| B red fija | 6.338,01 | 247,63 | 1.290,00 | 4,209 | 0,28 | 0 (41,3) | Sí |
| A (2 D1 Ultra) | 22.839,68 | 820,16 | 1.502,47 | 0,832 | 1,07 | 96,3 (136,7) | Sí |
| F pesimista (2 robots, D1 a 9.600) | 36.828 | 1.585,8 | 280,0 | −0,823 | — | — | Sí |

Cadena de la fila F, para quien quiera repetirla:
1. FOB = 7.499 + 20 × 186 + 500 = 11.719 USD.
2. Flete = 42 kg × 5 + 150 = 360; seguro = 117,19; CIF = 12.196,19.
3. Arancel 5 % = 609,81; IVA 19 % sobre (CIF + arancel) = 2.433,14; agencia y transporte = 350. Total puesto en finca = 15.589,14.
4. CAPEX = 15.589,14 + 400 de instalación + 1.500 de mástil = **17.489,14**.
5. OPEX = 240 de nube + 2.775 de mantenimiento + 2.600 de nodos + 3.000 de falsas alarmas = 8.615.
6. Costo = (17.489,14/3 + 8.615)/20 = **722,24 USD/ha/año**.
7. Beneficio = 12.000 × 6 × 0,10 × 0,25 + 6 × 95 + 3 × 23,82 = **2.441,47 USD/ha/año**.

Capacidad del robot: 36 h × 3.600 s × 0,5 m/s ÷ (10.000/2,5 × 1,3 m por ha) = **12,46 ha/semana**. Con la fracción de inspección de 0,5 en F sube a 24,92 ha. Las dos cifras coinciden con `derivados.csv`.

Otras cifras del reporte de finanzas que reproduje:
- Factor de importación del D1 Ultra: 1,359. Con arancel 0 % baja a 1,296; con IVA recuperable, a 1,149.
- Tornado de F: L tiene un rango de 2.700 USD/ha, f de 2.160, Y de 1.800, P de 1.500 y n de 950.
- Incremental F frente a B: +474,6 de costo, +1.151,5 de beneficio y ROI incremental de 1,426.
- Umbral de decisión: 0,0137. Pérdida base mínima de F: 0,45 %.

**Observaciones de modelo (no son errores de cálculo; los reporto sin cambiar nada):**
1. **Precio base del D1 Ultra.** La base usa 7.499 USD, cifra NO VERIFICADA de la hoja del equipo, y deja el precio verificado de la tienda (9.600 USD, que volví a ver en vivo hoy) como pesimista. Con 9.600 como base, el costo de F sube a 766 USD/ha/año y su ROI baja a **2,19**.
2. **Asimetría en falsas alarmas.** B no paga falsas alarmas (`falsas_alarmas: false`) y las opciones con robot pagan 150 USD/ha/año. Si B pagara las mismas 5 por ha × 30 USD, su ROI bajaría de 4,21 a **2,24**, por debajo de F (2,38). Eso invierte el titular "B tiene el ROI más alto". Es discutible: la falsa alarma de una red ambiental se traduce en una aplicación de más, no en una visita. Hay que decidirlo y decirlo.
3. **Rendimiento.** Y base = 12 t/ha es la cifra de "algunos cultivos" (Planasa vía Forbes). El promedio nacional EVA 2025 es **9,07 t/ha cosechada** (6.030,66 t / 664,72 ha). Con 9,07, el ROI de F queda en **1,77** y el de B en **3,50**.
4. **Valor optimista de Y.** El optimista de 20 t/ha sale de "20.000 t en ~1.000 ha" de Asocolblue, que es 3,3 veces la producción EVA 2025 (6.031 t). Sirve como meta (Planasa, más de 20 t/ha), no como dato.
5. **Costo de una aplicación.** La ficha ODEPA lista **10** pases de aplicación fitosanitaria por temporada, no ~6. Los 95 USD por aplicación suponen que el fungicida se reparte en ~6 aplicaciones; con 10 pases el costo de fungicida por pase baja a ~26.700 CLP. Es un DERIVADO con su supuesto declarado y queda dentro del rango 60–130, así que lo dejo.

## 3. SMMLV, TRM, arancel e IVA

| Cifra | Valor en finanzas | Verificación | Veredicto |
|---|---|---|---|
| SMMLV 2026 | 1.750.905 COP, Decreto 1469 de 2025 | buk.co: 1.750.905, Decreto 1469 del 29-dic-2025, **"aumento del 23 %"** frente a 1.423.500. Portafolio (10-oct-2026): sigue en 1.750.905, 23 %. El Tiempo (16-feb-2026) dice 23,7 %, pero la cuenta da 1.750.905/1.423.500 = **1,2300** | Valor CONFIRMADO. **"+23,7 %" es INCORRECTO; lo corregí a 23,0 %** |
| Auxilio de transporte | 249.095 COP (Decreto 1470) | buk.co y Portafolio | CONFIRMADO |
| Suspensión del decreto | 12-feb-2026, Decreto 0159, revocada el 9-jul-2026 | La suspensión la confirman buk.co y El Tiempo (16-feb). El Decreto 0159 y la revocatoria del 9-jul solo aparecen en buk.co. Portafolio (10-oct) no menciona ninguna suspensión vigente | El valor no cambia. La historia judicial tiene una sola fuente: NO VERIFICADA del todo |
| Jornal | 75.873 COP = 23,82 USD | 58.363,5 × 1,30 = 75.872,6; ÷ 3.185,01 = 23,822 | CONFIRMADO. El 30 % sale de un proyecto de ley, como ya advierte finanzas |
| TRM | 3.185,01 (23-oct); 3.158,43 (24–26-oct) | API en vivo `32sa-8pi3`: las dos cifras coinciden. En 12 meses: mínimo 3.048,12, máximo 3.900,82, promedio 3.532,26 sobre 236 observaciones | CONFIRMADO. El promedio es por observación, no por día calendario (diferencia menor) |
| Arancel | 8479.50.00.00: 5 %; 8479.89.90.00: 5 %; 8543.70.90.00: 0 % | Encontré las tres subpartidas en la copia DIAN (`raw/finanzas_dian_arancel/`). El 0 % de 8543.70.90.00 lleva la nota NV28: Decreto 1530 del 20-dic-2024, **vigente hasta el 31-dic-2028** | CONFIRMADO. El 0 % es temporal. La clasificación del cuadrúpedo sigue sin confirmar |
| IVA | 19 % sobre valor aduanero más arancel | ET art. 468: "diecinueve por ciento (19%)" (Ley 1819 de 2016, art. 184). ET art. 459: la base es la de los derechos de aduana "adicionados con el valor de este gravamen", es decir, valor en aduana más arancel | CONFIRMADO |

## 4. Especificaciones de robots contra sus fuentes

| Especificación | Afirmación | Fuente que abrí | Veredicto |
|---|---|---|---|
| D1 Ultra: peso, IP, autonomía, carga | 16 kg, IP54, 1–2 h, 5 kg, 3,7 m/s, 0–40 °C | Ficha oficial `D1_Ultra_Datasheet_1787637425866968.pdf`. Es idéntica, byte a byte, a la copia de `raw/finanzas_agibot_brochure/` | CONFIRMADO |
| D1 EDU: cámara | 1920×1080, DFOV 122° | Ficha Pro/Edu 2026-06-10: "一个相机，分辨率1920x1080p，视场角DFOV122°, HFOV111°, VFOV70°". La guía SDK pone HFOV 122° (errata probable). Las URL RTSP `rtsp://192.168.234.1:8554/test` (wifi) y `…168.168.168…` (cable) aparecen en la §5.1 de la guía | CONFIRMADO |
| D1 EDU: IP | Revisor: IP54; robots-competencia: ambiguo | La ficha Pro/Edu no declara IP, y tampoco agibot.com/products/D1_Pro. La tabla de la guía SDK "D1 Edu & Ultra" separa explícitamente lo que cambia entre modelos (color, medidas, peso, velocidad, control remoto) y da un solo valor, "Ingress Protection Rating IP54" | IP54 es la lectura más razonable de la guía, pero la ficha propia del EDU no lo dice. Sugiero escribir "IP54 según la guía SDK; la ficha del EDU no declara IP" |
| D1 EDU: ROS, cómputo y watchdog | Sin ROS; sin cómputo libre; se acuesta si pasan 3 s sin comandos | Guía SDK, FAQ 6.18: "Currently, there is no ROS interface available". FAQ 6.20: "no spare computing capacity internally". La guía dice además que si no recibe datos en 3 s pasa a modo amortiguado y se acuesta | CONFIRMADO |
| SDK del D1 EDU/Ultra | .so de Linux para cpython-310, BSD-3-Clause, sin URDF | GitHub `AgibotTech/agibot_D1_Edu-Ultra`: `mc_sdk_zsl_1_py.cpython-310-{x86_64,aarch64}-linux-gnu.so`, licencia BSD-3-Clause y ningún archivo URDF. Pero agibot.com/products/D1_Pro dice "Provides URDF modeling, supporting … Isaac Sim and MuJoCo" | CONFIRMADO. La "URDF para Isaac Sim y MuJoCo" del revisor es una promesa de la página de producto; el repositorio oficial no la trae |
| D1 MaxPro | 68 ± 1 kg, 2.081 Wh, IP67, 50 kg de carga, LiDAR de 96 líneas | GitHub oficial, `docs/source/1.3产品参数.md`: "68±1kg", "2081Wh", "额定负载 50kg", "前置一个96线激光雷达", "IP67" | CONFIRMADO. Refuta el "NO VERIFICADO" del punto 34 del revisor |
| Precios en la tienda | Ultra 9.600, Edu 6.080, Pro 3.200 USD | JSON en vivo de store.agibot.com. La moneda es USD (`Shopify.currency {"active":"USD","rate":"1.0"}`) | CONFIRMADO |
| Control remoto del Ultra | Con pantalla (punto 18 del revisor) | Guía SDK: "Remote Controller with Integrated Display — Standard for D1 Ultra" | CONFIRMADO |

## 5. ¿Son correctas las correcciones de `revision-documento.md`?

Revisé las que caen en mi foco. Las demás (ciencia, datasets y licencias) quedan sin re-verificar.

| Punto | Veredicto del revisor | Mi veredicto | Evidencia |
|---|---|---|---|
| 1. Área sembrada | Las dos fuentes están mal atribuidas; usar EVA 906,7 ha | **CONFIRMADO, con un matiz** | Portal Frutícola: 760 ha, de Agroventure, sin mencionar a Asocolblue ni 500 ha. El artículo de Forbes enlazado no da área. Pero El Tiempo (4-may-2026) atribuye "aproximadamente 1.000 hectáreas" a Forbes Colombia, y Asocolblue dice "alrededor de 1.000" (Agronegocios, 11-feb-2026). EVA 2025: 906,72 ha sembradas, 664,72 cosechadas y 6.030,66 t. La corrección a EVA es buena; "~1.000 ha (Asocolblue)" también tiene fuente |
| 2. El D1 EDU sí trae cámara | INCORRECTO en el documento | **CONFIRMADO** | Ficha y guía (§4) |
| 3. IP54 del EDU | INCORRECTO en el documento | **CONFIRMADO con matiz** | Ver la fila de IP en §4. "IP32 (las fuentes no coinciden)" era prudente; la corrección propuesta es correcta si dice la fuente |
| 4. Sin ROS | INCORRECTO en el documento | **CONFIRMADO** | FAQ 6.18. Ver la fila de URDF en §4 |
| 5. "84 %" de DrBerry | IMPRECISO | **CONFIRMADO, con un error menor del revisor** | Sin aumentación: 69,0 / 44,5 / 53,4 (tabla 2) ✓. Pero "la mejor configuración da 88 / 94 / 94" está mal: la tabla 3 da YOLOv5s **88,4 / 92,6 / 94,1** y YOLOv5m **93,0 / 92,7 / 96,1**. Además, el 84 % y el 91 % del resumen no coinciden con ninguna fila de las tablas 2 y 3, así que llamar "precisión" a ese 84 % es una interpretación |
| 7. Huaral frente a Sayán | IMPRECISO | **CONFIRMADO** | El paper dice "Sayan district, Huaura Province", y en total 544 imágenes = 439 + 105 |
| 6. 8 de 8 da un límite inferior de 63 % | — | **CONFIRMADO** | Clopper-Pearson: 0,025^(1/8) = 0,631 |
| 8. Thorvald | Más de 10 ha, no 30 | **CONFIRMADO** | FarmingUK, 16-dic-2021: "over 10 hectares" en dos fincas de Kent; la afirmación es de la propia empresa |
| 10. TRM y jornal | B base sube a ~1.878 | **CONFIRMADO** (1.878,3) | Usa los parámetros del documento, no los del modelo (ver §7) |
| 11. FOB de Perú 6,22 | INCORRECTO; usar 6,58 | **REFUTADO en parte** | El documento enlaza el artículo de Gestión del 16-feb-2026 (Midagri: 2.457 MUSD, 373.514 t), que no da precio. Pero Gestión del **14-ene-2026** (Sunat, Fresh Fruit y Preciso, preliminar) dice textualmente **6,22 USD/kg en 2025 (6,43 en 2024)**, con 2.563 MUSD y 412.239 t (cociente 6,217). Corrección justa: "6,22 (Gestión, 14-ene-2026, preliminar); 6,58 con cifras de Midagri", cambiando el enlace |
| 12. Rendimiento EVA 9,07 | IMPRECISO | **CONFIRMADO** | 6.030,66/664,72 = 9,07. B del documento con ese rendimiento = 1.478,4. Con el modelo nuevo, F baja a ROI 1,77 |
| 13. P = 6 frente a 8–10 | Incoherencia interna | **CONFIRMADO** | Con P = 8, B = 2.310. El modelo de finanzas ya declara 6 como supuesto conservador anclado en el FOB implícito de Colombia (5,22–6,09) |
| 14. Peso de L·f = 78,7 % | IMPRECISO | **CONFIRMADO** | 1.440/1.830 |
| 15. Sensibilidad de la matriz | Depende de qué pesos se bajan | **CONFIRMADO** y generalizado en §6 | — |
| 16. MaxPro, Genie | NO REPRODUCIBLE; ~1.720 / ~1.880 / ~570 | **REFUTADO en la conclusión** | Las cifras del documento se reproducen con un mantenimiento de **~10.900 USD/año para MaxPro (11,7 % del CAPEX) y ~9.660 para Genie**. Además, 700 USD/ha × 60 ha = 2.100 × 20 ha = 42.000 USD/año, así que son coherentes entre sí. El revisor les aplicó el mantenimiento de 2.300–3.250 USD que el documento da para el D1, a robots de 6 a 9 veces su precio. El modelo de finanzas usa 10 % del CAPEX (MaxPro unos 8.700 USD/año). **No adoptar "~1.720, por debajo de B"**: solo pedir que se documente el mantenimiento por plataforma |
| 17. ROI 4,7× y 3,3× | Correcto como (B − C)/C | **CONFIRMADO** | Pero el modelo nuevo da 0,83 y 2,38 (§7) |
| 18. Ultra frente a EDU | Ahorro de ~33 USD/ha/año | **CONFIRMADO con los precios de la hoja.** Con los precios de la tienda (6.080 frente a 9.600) el ahorro es de **~74 USD/ha/año** | Diferencia FOB 3.520 × 1,262 (seguro, arancel e IVA) ÷ 3 años ÷ 20 ha |
| 19. Ultra 16 kg, 6 ± 1 km | IMPRECISO | **CONFIRMADO** | Ficha y nota (2) de la ficha Pro/Edu |
| 24. Baterías: 0,8–1,4 años | IMPRECISO | **CONFIRMADO** | 300/365 y 500/365 |
| 25 y 26. Pesos y precios relativos | IMPRECISO | **Aritmética CONFIRMADA** (p. ej. 47.999/5.999 = 8,0; 150.000/5.999 = 25,0) | No re-verifiqué los valores de la tabla del documento |
| 33. Pendiente 30°/40° | IMPRECISO | **CONFIRMADO** | Ficha: "30° standard, up to 40° maximum" |
| 34. "LiDAR de 96 líneas" del MaxPro | NO VERIFICADO | **REFUTADO**: está VERIFICADO | GitHub oficial `Agibot_D1_MaxPro`, ficha de parámetros |

Ninguna corrección del revisor mete un error grave si se aplica tal cual, salvo dos:
- **Punto 16:** adoptar ~1.720 USD/ha/año para MaxPro y concluir "ajustado".
- **Punto 11:** reemplazar 6,22 por 6,58 como si el primero fuera falso.

En el punto 5 hay que corregir "94 %" por 92,6 %.

## 6. Matriz de alternativas

Leí la tabla del documento (revisión 22). Los puntajes son anticipa, ubica, costo, encaje, robustez y registro, sobre 5:

| Alternativa | Puntajes | Total recalculado | Documento |
|---|---|---|---|
| A. D1 Ultra + mástil | 3, 5, 3, 4, 3, 4 | 73 | 73 |
| B. Red fija | 5, 1, 5, 5, 4, 2 | 75 | 75 |
| C. Kit en aspersora | 2, 4, 5, 3, 3, 3 | 68 | 68 |
| D. Humanoide | 2, 4, 1, 1, 1, 4 | 42 | 42 |
| E. Ruedas | 3, 5, 2, 4, 3, 4 | 69 | 69 |
| F. Red + D1 Ultra | 5, 5, 3, 4, 3, 5 | 83 | 83 |

Los pesos base son 20 / 20 / 20 / 15 / 15 / 10, y el total es la suma de puntaje × peso dividida entre 5. La sensibilidad del documento (pesos 20 / 15 / 30 / 15 / 10 / 10) da A 71, **B 80**, C 71, D 39, E 65 y **F 81**: cuadra.

Lo que la matriz no dice:
- **La diferencia entre F y B tiene una fórmula cerrada:** F − B = (4·ubica − 2·costo − encaje − robustez + 3·registro)/5. La anticipación se cancela porque las dos sacan 5.
- **El resultado depende de los pesos.** En un barrido de pesos múltiplos de 5 que suman 100, **B gana a F en 2.911 de 11.598 combinaciones (25 %)**. En el barrido, cada uno de los cinco primeros pesos va de 5 a 65 y registro completa hasta 100, con un mínimo de 5. Por ejemplo:
  - 20 / 10 / 30 / 15 / 15 / 10 da B 83 y F 79;
  - 20 / 10 / 40 / 15 / 5 / 10 da B 85 y F 79;
  - 15 / 15 / 30 / 15 / 15 / 10 da un empate a 79.
- **La frase del pitch** "lo que inclina la balanza es saber en qué cama está el problema" es, literalmente, el término 4·ubica.
- **El puntaje de costo choca con el modelo nuevo.** En el modelo, A (2 robots, 820 USD/ha) cuesta más que F (722). Aun así, la matriz les da a los dos un 3. Si A bajara a 2, quedaría en 69; F seguiría en 83.

## 7. Inconsistencias entre agentes (lo más urgente)

| Cifra | Documento (revisión 22) | Modelo de finanzas (`finanzas/`) |
|---|---|---|
| Parámetros del beneficio | L 8 %, n 2, C_ap 100, J 10, w 19 USD | L 10 %, n 6, C_ap 95, J 3, w 23,82 USD |
| Beneficio base | 1.830 USD/ha/año (igual para todas las opciones) | B 1.290; A 1.502; F 2.441 (con multiplicadores por opción) |
| D1 Ultra + mástil, 20 ha | 1 robot, ~320 USD/ha/año, ROI ~4,7× | **2 robots** (12,5 ha/semana cada uno), 820 USD/ha/año, ROI 0,83 |
| Híbrido | ~430, ROI ~3,3× | 722, ROI 2,38 |
| Red fija | ~110 | 248 (sin falsas alarmas) |
| Falsas alarmas | No entran al costo | 150 USD/ha/año en las opciones con robot |
| Área nacional | 500 / 1.000 ha | 1.000 ha (Asocolblue). Revisor y verificador: **EVA 906,7 ha** |

Las correcciones del revisor (puntos 10, 12, 13 y 14) están calculadas sobre los parámetros viejos del documento. Si el equipo adopta el modelo de finanzas, esas cifras (1.878, 1.478, 2.310, 78,7 %) dejan de aplicar. **Recomiendo publicar en el documento la tabla de `finanzas/tabla_final_20ha.csv`** con:
- Y = 9,07 t/ha como escenario de "promedio nacional";
- D1 a 9.600 USD;
- una nota sobre las falsas alarmas de B.

## 8. Correcciones aplicadas

1. `finanzas/parametros.yaml`, nota de `macro.smmlv_2026_cop`: "+23,7 %" pasa a "+23,0 % sobre 1.423.500 de 2025", con una marca del verificador.
2. `reportes/finanzas.md`, fila SMMLV de la tabla §3: el mismo cambio.

Es un cambio solo de texto. Verifiqué que el YAML editado sigue produciendo los 8 CSV idénticos. No toqué el documento del equipo ni `revision-documento.md`: sus discrepancias son de criterio y quedan reportadas arriba.

## 9. Archivos producidos

- `/Users/santiagosantafe/Downloads/SabanaHack/datos/reportes/verificacion-finanzas-robots-documento.md` (este reporte).
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/reportes/verificacion-finanzas-robots-documento_scripts/recalculo.py` (recálculo independiente; corre con `python3 -I` en menos de 1 s).
- Editados: `finanzas/parametros.yaml` y `reportes/finanzas.md` (§8).
- No descargué nada nuevo a `raw/`. Los textos extraídos de los PDF y las READMEs de GitHub quedaron en el scratchpad de la sesión.

## 10. Fuentes que abrí (2026-10-23)

- TRM: https://www.datos.gov.co/resource/32sa-8pi3.json (consulta en vivo)
- SMMLV:
  - https://www.buk.co/blog/salario-minimo-2026-en-colombia
  - https://www.eltiempo.com/economia/sectores/salario-minimo-2026-diez-preguntas-y-respuestas-para-entender-la-suspension-del-decreto-y-su-impacto-en-los-trabajadores-3532351
  - https://www.portafolio.co/economia/gobierno/salario-minimo-de-2026-sigue-en-1-750-905-millones-tras-aclaracion-sobre-fallos-del-consejo-de-estado-504236
- IVA: https://estatuto.co/468 y https://estatuto.co/459
- Arancel: copia local de https://normograma.dian.gov.co/dian/compilacion/docs/decreto_1881_2021.htm (`raw/finanzas_dian_arancel/`)
- AgiBot:
  - PDF locales de `raw/agibot_docs/` (orígenes en `FUENTES.txt`)
  - https://agibot.com/products/D1_Pro
  - https://store.agibot.com/products/d1-ultra.json, d1-edu.json y d1-pro.json
  - https://github.com/AgibotTech/agibot_D1_Edu-Ultra
  - https://github.com/AgibotTech/Agibot_D1_MaxPro (`docs/source/1.3产品参数.md`)
- Prensa y sector:
  - Gestión, 14-ene-2026: https://gestion.pe/economia/arandanos-rompen-record-de-exportaciones-pero-un-factor-preocupa-al-peru-noticia/
  - Gestión, 16-feb-2026: https://gestion.pe/economia/mercados/peru-consolida-liderazgo-mundial-en-arandanos-exportaciones-suman-usd-2457-millones-en-2025-noticia/
  - Forbes: https://forbes.co/2026/05/26/negocios/arandano-colombiano-el-sello-que-lanzo-el-sector-para-impulsar-el-consumo-y-exportacion/
  - El Tiempo: https://www.eltiempo.com/economia/sector-financiero/colombia-dispara-su-produccion-de-arandanos-pero-el-95-se-queda-en-casa-y-frena-el-salto-exportador-3552946
  - Agronegocios: https://www.agronegocios.co/agricultura/el-arandano-crece-pero-lejos-de-su-potencial-exportador-4321623
  - Portal Frutícola: https://www.portalfruticola.com/noticias/2025/01/28/arandanos-en-colombia
  - FarmingUK: https://www.farminguk.com/news/robot-delivers-world-first-season-free-of-powdery-mildew-sprays_59536.html
- Copias locales de otros agentes:
  - paper DrBerry (`raw/drberry_paper/122071.pdf`);
  - Peña et al. 2023 (`raw/finanzas_agrocol2023/`), con 58.606 USD, 22.800 USD, WACC 13,4 %, TIR 19 % y TRM 3.875,38: confirmados;
  - ODEPA Maule (`raw/finanzas_odepa/`);
  - dólar de Chile de 2021 (`raw/finanzas_clp/`): promedio de abril 707,85, confirmado;
  - EVA (`raw/revision_documento_eva/`).
- Documento del equipo: Claude Doc `9c0a5374-f338-45a8-9ac1-6089724600e1`, revisión 22. Leí las tablas de matriz, finanzas y cultivo, y los párrafos de sensibilidad y de mantenimiento.

Licencias: el material de AgiBot, la prensa y los papers se citan y no se redistribuyen. El SDK de GitHub es BSD-3-Clause, y la licencia del repositorio del MaxPro no la revisé.

## 11. Límites

- No re-verifiqué los puntos de ciencia, datasets y licencias del revisor (9, 20–23, 27–32, 35), ni la competencia del agente de robots (CMU, hexafarms, METOS).
- La historia judicial del SMMLV (Decreto 0159 y revocatoria del 9-jul-2026) se apoya en una sola fuente secundaria, buk.co. No abrí el Diario Oficial ni el auto del Consejo de Estado.
- No verifiqué los precios de X2 Ultra, Genie G1, MaxPro, Amiga ni el gateway; siguen NO VERIFICADOS en el YAML.
- Lo que digo sobre el IVA del art. 459 es la lectura estándar del texto ("adicionados con el valor de este gravamen" se refiere a los derechos de aduana). No consulté doctrina de la DIAN.
- La API key de Roboflow no la usé ni la leí, porque mi rol no la necesitaba. Llegó en texto plano en el mensaje del usuario, así que conviene rotarla al terminar el hackathon.

## 12. Pendientes

1. Unificar las cifras del documento con `finanzas/tabla_final_20ha.csv` (§7). Es lo que más riesgo tiene frente al jurado.
2. Decidir si la red fija (B) paga falsas alarmas. Con el mismo costo que las demás, B baja a ROI 2,24 y F (2,38) queda primera.
3. Usar 9.600 USD (tienda) como base del D1 Ultra hasta tener una cotización, y agregar el escenario Y = 9,07 t/ha (EVA).
4. En el documento:
   - FOB de Perú: cambiar el enlace al artículo de Gestión del 14-ene-2026, o usar 6,58 citando a Midagri.
   - MaxPro: dejar "LiDAR de 96 líneas" como verificado.
   - DrBerry: escribir 88,4 / 92,6 / 94,1.
   - IP54 del EDU: decir que la cifra viene de la guía SDK.
5. Publicar el barrido de pesos de la matriz: B gana en el 25 % de las combinaciones, y la fórmula F − B muestra que la decisión depende del peso de "ubica".
