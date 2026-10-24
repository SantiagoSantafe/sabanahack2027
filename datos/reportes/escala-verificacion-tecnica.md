# Verificación técnica y operativa de la escalabilidad

Sabana Hack 2026, reto "Berry Good Idea". Rol: **verificacion-tecnica** (verificador adversario). Fecha: 23 de octubre de 2026.

**Qué se revisó:** lo que entregaron los roles arquitectura-multifinca, generalizacion-cultivos, clima-global, operacion-escala y datos-aprendizaje en `datos/escalabilidad/`. El objetivo era intentar refutar la arquitectura, la generalización a otros frutales, la capa de clima global, la operación con muchos productores y el ciclo de datos. El clima de la Sabana se tomó solo como banco de prueba. La pregunta de fondo fue si la solución aguanta venderse a muchos productores.

**Marcas que uso:**
- **[V]**: lo comprobé abriendo la URL o el archivo, o volviendo a correr el código.
- **CÁLCULO**: aritmética mía, reproducible con `escalabilidad/verificacion_tecnica/verificacion_rutas.py`.
- **SUPUESTO**: valor mío, sin fuente.
- **NO VERIFICADO**: no lo pude comprobar.

---

## 0. Veredicto en 8 líneas

1. **La arquitectura escala, pero el aislamiento entre clientes tenía huecos.** Las pruebas P1-P11 del rol de arquitectura pasan [V], pero 11 ataques que esas pruebas no cubrían también pasaban. Ejemplos: la empresa B leía la auditoría de A, el cliente con el robot prestado podía cambiarle el dueño y la huella mTLS, y un cliente podía "secuestrar" filas de los catálogos globales y borrarle a A filas de su registro ICA. **Corregí 10. Quedan 2 abiertos.**
2. **El modelo de antracnosis está mal atribuido en toda la propuesta.** Lo que corre en `riesgo/risk.py` es **Wilson 1990 (fresa)** con una aproximación en arándano de **Gillett y Schilder 2009**. **No es Miles 2013**, cuyos coeficientes el equipo nunca obtuvo [V, `riesgo/README.md` §2.1 d]. Lo corregí en 8 archivos de `escalabilidad/`. Los documentos principales del pitch, que están fuera de esta carpeta, todavía dicen "Miles 2013".
3. **El D1 no trae ROS.** La guía oficial del SDK dice "Currently, there is no ROS interface available" [V]. La navegación por pasillo es desarrollo propio.
4. **El límite operativo no es solo la batería.** Hay tres restricciones que el ROI no incluye: la **línea de vista** que exige el manual, el **ritmo de la aspersión** (el robot tiene que ir delante del aspersor) y el **tránsito a la caseta** en fincas grandes.
5. **Los modelos de riesgo están bien citados (salvo el punto 2).** Revisé contra la fuente primaria Wilson, Bulger, Broome, Gubler-Thomas/METOS y 7 filas de la Tabla 2 de Magarey 2005 [V]. Ninguno está validado en el trópico, y los documentos ya lo dicen.
6. **La capa de clima global se sostiene.** Sus resultados se reproducen idénticos [V] y el desfase UTC de IDEAM es real [V]. Pero la calibración corrige el **sesgo**, no el error hora a hora del mojado foliar.
7. **Todos los datasets citados existen** [V]. Uno es **CC BY-NC 4.0** (no comercial) y estaba marcado como "licencia no verificada".
8. **La Res. ICA 824/2022 solo obliga a fincas registradas para exportar** (art. 2) [V]. "El registro regulatorio sale solo" vale para exportadores. Para mora y fresa de mercado nacional, el argumento es BPA.

---

## 1. Qué volví a correr

| Prueba | Resultado | Evidencia |
|---|---|---|
| Todos los JSON de `escalabilidad/` (14 archivos, sin la caché) con `python3 -I -c 'import json; json.load(...)'` | 14/14 válidos [V]. `clima_global/perfiles/arandano.json` se revalidó después de corregirlo | — |
| YAML (`perfiles/*.yaml`, `unit_economics_parametros.yaml`) con PyYAML del `.venv` | 5/5 válidos [V] | — |
| `modelo_datos.sql` en contenedor desechable `postgres:16-alpine` (16.14, imagen local, `--pull never`), con el sustituto de PostGIS del rol | El DDL corre. P1-P11 dan **exactamente** lo mismo que `resultado_pruebas_sql.txt`, antes y después de mis correcciones [V] | `verificacion_tecnica/resultado_ataques.txt` |
| `schema_incidencia.json` con Ajv 8.20.0 en modo estricto (copia local en la caché de npx) | 20/20 [V] | `pruebas_arquitectura/validar.js` |
| Ataques entre empresas V1-V6, W1 y X1 (nuevos) | Antes: 11 de 11 pasaban, y X1 también. Después: 10 bloqueados; V5d y X1 siguen abiertos [V] | `verificacion_tecnica/ataques_multiempresa.sql` y `resultado_ataques.txt` |
| `motor_perfiles.py`, en una copia en la carpeta temporal y luego en su sitio tras corregir | Código de salida 0. Los 5 puntos de control de ecuaciones pasan. 22 modelos [V] | `validacion_perfiles.json` (regenerado) |
| `clima_global/scripts/validar_y_calibrar.py`, sin red y desde la caché, en una copia | `validacion_fuentes.csv`, `calibracion_por_estacion.csv`, `qc_estaciones.csv` y `lwp_vs_hr90.csv` salen **idénticos byte a byte** [V] | — |
| Recálculo de EVA 2025 desde los JSON guardados | Áreas y participación por departamento de los 7 cultivos, y los 65 municipios de arándano (34 con menos de 5 ha; 8 con 20 ha o más, que suman el 64,1 %), coinciden [V] | `fuentes_cultivos/`, `mercado/eva_municipal_berries_2025.json` |
| Ciclo diario de T en `raw/ideam_datosgov_2025` | En 5 estaciones IDEAM la mínima cae a las 10-11 h y la máxima a las 18-19 h de `fechaobservacion`, o sea en **UTC**. En Salitre (CAR) caen a las 5 h y a las 13 h, o sea en **hora local** [V] | — |
| `verificacion_rutas.py` (nuevo) | Tránsito, ciclos de batería, ritmo de aspersión y costo de la línea de vista | `verificacion_tecnica/verificacion_rutas.csv` |

---

## 2. Hallazgos, de más a menos grave

| # | Área | Hallazgo | Evidencia | Estado |
|---|---|---|---|---|
| H1 | Arquitectura | **Aislamiento incompleto entre clientes.** (a) `auditoria` no tenía RLS: B leía la de A (V1). (b) La política de `dispositivo` era FOR ALL: quien tenía el robot prestado podía cambiarle `empresa_id` y `certificado_huella` (V2). (c) `problema_sanitario` y `modelo_version` dejaban hacer UPDATE ... SET empresa_id = B sobre una fila global. La fila desaparecía para todos: el registro ICA de A pasó de 6 a 5 filas (V3) y A dejó de ver el modelo de roya (V4a). También se podían borrar filas globales (V4c). (d) `recorrido_cama.cama_id`, `aplicacion_cama.cama_id` e `incidencia.incidencia_origen_id` eran llaves simples, así que B podía apuntar a camas e incidencias de A (V5a-c) e impedir que A las borrara. (e) B podía renombrar al agrónomo compartido, y ese nombre sale en el registro ICA de A (V6). (f) Un usuario limitado a otra finca veía eventos, fotos (`evidencia`), camas recorridas y el registro de cambios del resto de la empresa (W1) | `resultado_ataques.txt`, sección ANTES [V] | **Corregido** en `modelo_datos.sql`, con FK compuestas, políticas por comando, RLS en auditoría y alcance por finca en las tablas hijas. P1-P11 sin cambios |
| H2 | Riesgo y cultivos | **"Antracnosis Miles 2013" no es el modelo que corre.** `riesgo/README.md` §2.1 dice que los coeficientes de Miles 2013 no se obtuvieron (artículo cerrado) y que el índice es máx(Wilson 1990 de fresa, aproximación de Gillett y Schilder 2009 en arándano). `arandano.yaml` lo declaraba como `referencia_externa: miles2013`, "implementado en el módulo de riesgo". La semilla SQL, `operacion.md`, `clima_global.md`, `datos_aprendizaje.md`, `mercado.md` y `cultivos.md` repetían la atribución | `riesgo/README.md` [V] | **Corregido** en `escalabilidad/`: id `antracnosis_wilson1990_arandano` y fuente `riesgo_equipo`. **Pendiente fuera de esta carpeta:** el pitch y los documentos principales |
| H3 | Robot | **Sin interfaz ROS.** `arquitectura.md` decía, citando a un distribuidor, que el D1 EDU trae ROS 2. La guía oficial del SDK (V2.0.7, §6.18) dice "Currently, there is no ROS interface available". Hay SDK en Python y C++ con comandos de velocidad, posición en el marco de encendido, IMU y cámara frontal (FOV 122°) | `raw/agibot_docs/AGIQUAD_D1_Edu_Ultra_SDK_Guide_V2.0.7.pdf` [V] | **Corregido** en `arquitectura.md`. Riesgo abierto: navegación, lectura de marcadores y odometría por cama son desarrollo propio |
| H4 | Operación | **La línea de vista del manual choca con "20 min/día de operario por robot".** El manual dice "keep it within your line of sight" [V]. Si se exige medio operario a 1 SMMLV por cada 2 robots en 20 ha, son ~250 USD/ha/año; con uno completo, ~500 USD/ha/año (CÁLCULO, SMMLV, factor y TRM de `operacion/capacidad.py`). Eso supera el costo total de ~430 USD/ha/año del híbrido. Los 20 min/día dan ~21 USD/ha/año | Manual D1 Edu, "Safe use and terrain adaptability" [V]; `verificacion_rutas.py` | **Abierto**, con la cifra anotada en `operacion.md` §13. Hay que preguntarle a AgiBot y hacer una evaluación de riesgos antes de vender "sin supervisión" |
| H5 | Operación | **"Siempre delante del aspersor" limita la aspersión.** 2 D1 Ultra (escenario base) inspeccionan ~3,6 ha/día. Si la finca asperja sus 20 ha en 1 día, solo el ~18 % queda inspeccionado antes; en 2 días, el ~36 % (CÁLCULO). La meta del piloto de ≥ 90 % delante del aspersor solo se cumple con la aspersión escalonada en ≥ 6 días, o inspeccionando antes solo las camas de riesgo alto | `operacion/capacidad.csv` [V]; `verificacion_rutas.py` | **Abierto**, anotado en `operacion.md` §4.1. Depende de la pregunta 3 del mentor |
| H6 | Operación | **Caseta a ≤ 150 m y "una por cada ~20 ha" no cuadran.** A 150 m por pasillos se alcanzan ~4,5 ha (CÁLCULO). Con una caseta en el centro de 20 ha, el tránsito promedio es ~10 % a 1 m/s (21 % en la esquina) y ~21 % a 0,5 m/s (41 % en la esquina). Con la batería recortada por el kit del mástil (−25 %, SUPUESTO) sube a 14-28 % | `verificacion_rutas.csv` | **Corregido** en `operacion.md`: una caseta o punto de cambio cada ~5-10 ha, o planear con ~1,6 ha/día por robot |
| H7 | Operación | **Ciclos de batería subestimados.** `capacidad.py` usa el 100 % de la autonomía, pero la restricción dura 5 de `operacion.md` deja un 20 % de reserva. Con la reserva son ~1.510 ciclos/año por robot, no 1.230. Con el kit alimentado por la batería, ~1.970. Si la autonomía cae como en el MaxPro a plena carga (de 5,5 a 2,5 h), ~3.050 (CÁLCULO). La garantía es de 6 meses o 200 ciclos [V] | Manual D1 Edu, tabla de garantía [V] | **Anotado** en `operacion.md` §2.4. Las baterías son un insumo mayor de lo presupuestado |
| H8 | Regulación | **La Res. ICA 824/2022 no aplica a todos.** Art. 2: "personas naturales o jurídicas productoras, exportadoras y/o empacadoras de vegetales para la exportación en fresco" [V]. Los campos de §8.2.4, §8.2.6 y §8.2.7, la conservación por 2 años, la copia de seguridad y el informe trimestral (art. 13.1.6) están bien citados [V] | https://www.ica.gov.co/importacion-y-exportacion/planes-trabajo-exportacion-vegetales/documentos-relacionados/resolucion_ica_824_2022.aspx | **Corregido** en `arquitectura.md` §9.2: para el mercado nacional el argumento es BPA |
| H9 | Clima | **La calibración de 14 días arregla el sesgo, no el error hora a hora.** Juntando las 4 estaciones, el MAE de horas mojadas pasa de 4,1 a 3,4 h/día y la tasa de falsas alarmas de "día favorable" sigue en ~0,42 [V, `calibracion_resumen.csv`]. En Bulger 1987, unas 2,7 h más de mojado a 20,5 °C pasan el índice de 0,50 a 0,70 (`riesgo/README.md`) | Reproducción de `validar_y_calibrar.py` [V] | **Matizado** en el resumen de `clima_global.md`. Para Botrytis y antracnosis, sensor de hoja mojada |
| H10 | Datos | **El dataset de fresa Mendeley k2ptxmfjhj es CC BY-NC 4.0.** Estaba como "declara uso académico; licencia NO VERIFICADA". No sirve para entrenar el producto que se vende | `https://data.mendeley.com/public-api/datasets/k2ptxmfjhj` [V] | **Corregido** en `cultivos.md` |
| H11 | Operación | **Los "~430 USD/ha/año" son un costo, no un beneficio.** `operacion.md` comparaba el costo del técnico contra un "beneficio de ~430". 430 USD ÷ 6 USD/kg ≈ 72 kg/ha es el **punto de equilibrio** (`unit_economics_salida.txt`, línea 219). Además, el costo del híbrido no es el mismo en todo el equipo: 430 en la propuesta, 722 en `finanzas/tabla_final_20ha.csv` (opción F, 1 robot) y 820 en la opción A (2 robots) [V] | Archivos citados [V] | **Corregido** el texto. **Abierto:** unificar la cifra en el pitch |
| H12 | Legal | **El art. 26 de la Ley 1581 regula transferencias.** Para la nube del vendedor como encargado lo que aplica es la transmisión con contrato (Decreto 1377, arts. 24-25). `datos_aprendizaje.md` lo trata bien; `arquitectura.md` se contradecía con él | `datos_aprendizaje.md` §12 | **Matizado** en `arquitectura.md` §11.1 |
| H13 | Cultivos | **Pendiente con mástil sin medir.** Los 30° estándar y 40° máximos son de la ficha, en laboratorio y sin carga. El manual pide no girar en pendientes fuertes y no usar el robot en suelo resbaloso [V]. En mora, con un mástil de 1,4 m, el límite real está NO VERIFICADO | Datasheet y manual [V] | **Matizado** en `cultivos.md`. Propuesta: no aptas por encima de ~15° hasta el piloto (SUPUESTO) |
| H14 | Datos | **El volumen de fotos no es el mismo entre roles.** `datos_aprendizaje.md` usa 42.000 fotos/semana (20 % de las camas). La política de `operacion.md` (0,65 visitas por cama y semana) da ~136.500 (CÁLCULO), y `arquitectura.md` supone ~61.000 cuadros por día. El presupuesto de 5 falsas alarmas por semana exige menos de 3,7 errores por cada 100.000 fotos, no 1,2 por cada 10.000. La conclusión (agregar la alerta por tramo) se refuerza | Documentos citados | **Anotado** en `datos_aprendizaje.md` §9.1 |
| H15 | Arquitectura | **Afirmaciones de "configuración, no código" más amplias que el DDL.** `transicion_estado` no tiene `empresa_id`, así que el flujo es el mismo para todos los clientes. `especie` y `especie_problema` no los puede escribir el cliente | DDL [V] | **Matizado** en `arquitectura.md` §4.1 y §5.2 |

### Abiertos que no corregí (decisiones de diseño o de otros dueños)

| # | Qué falta | Por qué no lo toqué | Propuesta |
|---|---|---|---|
| A1 | **X1:** un cliente puede reservarse el robot compartido del proveedor por un año (`asignacion_dispositivo`), y la restricción `EXCLUDE` se lo bloquea a los demás | Corregirlo cambia la prueba P5h del rol de arquitectura | `REVOKE INSERT, UPDATE, DELETE ON asignacion_dispositivo FROM bgi_app`; que asigne solo el planificador de flota; P5h pasa a `bgi_admin` |
| A2 | **V5d:** las referencias a `dispositivo` y a `modelo_version` son llaves simples. B puede citar el robot asignado hoy a A, o el modelo calibrado privado de A | El robot del proveedor tiene `empresa_id` NULL y no admite FK compuesta | Un disparador que exija una asignación vigente a la empresa en la fecha del registro |
| A3 | El aislamiento depende de que la API fije bien `app.empresas` desde el token: `bgi_app` puede fijar cualquier valor | Es el patrón estándar de RLS | Fijar el contexto en un solo módulo, probarlo y auditarlo |
| A4 | El JSON Schema exige modelo y confianza también a `camara_aspersora`; el `CHECK` SQL solo a `robot` | Diferencia menor | `CHECK (fuente_tipo NOT IN ('robot','camara_aspersora') OR (...))` |
| A5 | El perfil de arándano define la roya como regla (15-25 °C, ≥ 6 h); `riesgo/risk.py` la calcula con un GIM (Topt 21,5, Tmin 8, Tmax 32 °C). Son dos modelos distintos con el mismo nombre | Lo decide el rol de riesgo | El perfil debería delegar en `risk.py`, como ya hace con la antracnosis |
| A6 | El onboarding de `operacion.md` pide pasillo ≥ 1,2 m; el validador de perfiles acepta 0,56 m | Criterio de diseño | Escribir los dos: 0,56 m como mínimo físico y ~1,0-1,2 m como recomendado con mástil (SUPUESTO) |
| A7 | **Etiqueta retroactiva de "pre-síntoma"** (`datos_aprendizaje.md` §3.3). La foto RGB de una semana antes puede no tener ninguna señal (antracnosis y Botrytis tienen infección latente). El modelo podría aprender la cama o la luz en lugar del síntoma | Es una hipótesis del rol, no un error | Validar dividiendo por tramo y por finca. Presentarla como hipótesis, no como "lo que el ojo todavía no ve" |
| A8 | La batería se cambia con el robot apagado ("Remove the battery and insert it..."); no hay cambio en caliente [V]. Además, "Continuous use for a long time may cause the motor to overheat. Please take regular breaks" [V] | Ya está en `operacion.md` | Medir en el piloto las pausas térmicas reales: la disponibilidad de 0,9 es SUPUESTO |
| A9 | PostGIS real sigue sin ejecutarse | No descargué imágenes | Correr una vez con `postgis/postgis:16-3.x` cuando el equipo la tenga |

---

## 3. Lo que intenté refutar y se sostuvo

| Afirmación | Cómo la comprobé | Resultado |
|---|---|---|
| Parámetros GIM de Magarey 2005, Tabla 2 (*B. cinerea* en uva, en flor de fresa y en flor de uva; *C. acutatum*; *G. bidwellii*; *P. viticola*; *P. cactorum*) | Leí la tabla en el PDF: https://www.suddenoakdeath.org/wp-content/uploads/pdf/PHYTO-95-0092%20Magarey%20nappfast.pdf | Las 7 filas coinciden en Tmin, Topt, Tmax, Wmin, Wmax y r [V] |
| Broome 1995 en uva | https://ipm.ucanr.edu/DISEASE/DATABASE/grapebotrytis.html | Ecuación, umbrales 0 / 0,5 / 1,0, rango de 12-32 °C, HR ≥ 95 % como hora mojada, 4 h secas, 2 años de validación en uva de mesa de Chile y ~50 % menos fungicida [V] |
| Oídio de fresa "Gubler modificado por Broome" de METOS | https://metos.global/en/?p=49800 | 21-30 °C, 6 h, 3 días seguidos, +20/−10 y > 60 alto [V]. METOS no lista Botrytis para fresa en esa página |
| Wilson 1990 y Bulger 1987 (logit) | Puntos de control a mano en `motor_perfiles.py` | −0,3775 y 0,6904 [V]. Bien atribuidos a fresa; los documentos los marcan como prestados en arándano y mora |
| D1 Ultra: 630 × 360 × 420 mm, 16 kg, 4,6 Ah × 43,2 V (≈ 199 Wh, CÁLCULO), 1-2 h, 5 kg, 30°/40°, IP54, 0-40 °C | `raw/agibot_docs/D1_Ultra_Datasheet_*.pdf` | Coincide [V]. El manual del D1 Edu (misma familia; la ficha del Edu da 635 × 360 × 420 mm y 15,5 kg) agrega que el alcance de 6 km se midió "at 1 m/s speed under no-load conditions" [V]. La autonomía con mástil y cámaras no está medida |
| Manual: no limpiar con líquidos ni alcohol, garantía de batería de 6 meses o 200 ciclos, carga de ~1 h del 10 al 90 % | `raw/agibot_docs/D1_Edu_User_Manual_EN.pdf` | Coincide [V] |
| El "~60 ha por MaxPro" no se sostiene | `operacion/capacidad.csv` | Confirmado: 26 ha en el escenario base y 53 en el optimista [V] |
| 20 ha necesitan 2 D1 Ultra en el escenario base | `capacidad.csv` y `finanzas.md` | Confirmado [V]. Con mis correcciones de tránsito sigue en 2 |
| Pasillo mínimo de 0,56 m (0,36 + 2 × 0,10) | Aritmética | Correcto. Ojo: echado mide 435 mm de ancho [V] |
| Desfase UTC de IDEAM | Ciclo diario de T | Confirmado (sección 1) [V] |
| Open-Meteo gratis solo para uso no comercial | Ya citado por clima-global | El documento lo dice bien: para vender hay que pagar el plan o alojar el servidor |
| Datasets HERMOS, NGLD, K-Kotagiri y Afzaal | API pública de Mendeley y LICENSE local de DatasetNinja | Existen; CC BY 4.0 [V]. El de Afzaal toma la licencia del artículo (MDPI): conviene confirmarla en el repositorio original |
| Intervalos de Wilson (8/9 → 57-98 %; 46/52 → 77-95 %; 920/1.040 → 86-90 %), n = 96 y n = 62 | Recalculados | Correctos (CÁLCULO). Ojo: 30 fincas × 9 focos = 270, no 1.040. Con 270 focos el intervalo es 85-92 %; el efecto de red sigue, pero más chico |
| Legal: Ley 1581, arts. 5, 23 y 26; Decreto 1377, arts. 24-25; Decreto 090/2018; Circular SIC 005/2017; Decisión 486, arts. 260 y 265; Ley 256/1996, art. 16 | Contenido de cada artículo frente a lo citado | Bien citados en `datos_aprendizaje.md` (salvo el matiz H12) |

---

## 4. Correcciones aplicadas (todas marcadas con "verificación técnica" en el archivo)

| Archivo | Cambio |
|---|---|
| `escalabilidad/modelo_datos.sql` | FK compuestas en `recorrido_cama`, `aplicacion_cama` e `incidencia_origen_id`; `UNIQUE (id, empresa_id)` en `cama`; RLS en `auditoria`; políticas por comando en `usuario`, `problema_sanitario`, `modelo_version` y `dispositivo`; alcance por finca en `incidencia_evento`, `evidencia`, `recorrido_cama` y `registro_cambios`; semilla de antracnosis renombrada; registro de cambios en el encabezado |
| `escalabilidad/arquitectura.md` | Nota de los huecos en §0; SDK sin ROS (§3 y §13.6); alcance de catálogos (§4.1) y de transiciones (§5.2); alcance de la Res. 824 (§9.2); transferencia frente a transmisión (§11.1); límite 8 con los huecos abiertos (§13); fila de pruebas V/W/X (§14) |
| `escalabilidad/perfiles/arandano.yaml` | Modelo `antracnosis_wilson1990_arandano` con referencia `riesgo_equipo`; nota de `miles2013` corregida |
| `escalabilidad/validacion_perfiles.json` | Regenerado con `motor_perfiles.py` (código 0) |
| `escalabilidad/cultivos.md` | Atribución de la antracnosis (2 líneas); licencia CC BY-NC del dataset Mendeley; matiz de la pendiente con mástil |
| `escalabilidad/operacion.md` | Antracnosis; 430 USD es costo; ciclos de batería con la reserva; regla de la caseta; ritmo de aspersión; costo de la línea de vista |
| `escalabilidad/clima_global.md` y `clima_global/perfiles/arandano.json` | Antracnosis; matiz de la calibración (sesgo frente a error) |
| `escalabilidad/datos_aprendizaje.md` | Antracnosis (3 líneas); volumen de fotos entre roles |
| `escalabilidad/mercado.md` | Antracnosis (1 línea) |
| `escalabilidad/verificacion_tecnica/` (nuevo) | `ataques_multiempresa.sql`, `resultado_ataques.txt`, `modelo_datos_antes_verificacion.sql` (DDL anterior, para repetir la parte ANTES), `verificacion_rutas.py` y `verificacion_rutas.csv` |

No modifiqué nada fuera de `escalabilidad/` y `reportes/`. **Pendiente para los dueños del pitch:** cambiar "antracnosis Miles 2013" por "antracnosis: Wilson 1990, adaptado a arándano con Gillett y Schilder 2009" en los documentos principales y en las diapositivas.

---

## 5. Qué cambia en el pitch (rúbrica)

| Criterio | Antes | Después de verificar |
|---|---|---|
| **Pertinencia (20): encaje en la operación** | El robot va "delante del aspersor" y opera solo | Decir que el robot **marca el ritmo de la aspersión** (≤ ~1,8 ha/día por robot) y que el manual pide **un operario a la vista**. Ofrecer las dos versiones: "inspección previa solo de camas de riesgo alto" y "aspersión escalonada" |
| **Justificación (10): alternativas y límites** | Modelos "Miles 2013, Bulger 1987" | "Wilson 1990 y Bulger 1987, de fresa, usados en arándano por el Blueberry Advisory System de UF/IFAS (según `riesgo/README.md`), sin validar en el trópico; los usamos para **priorizar camas**, no para dosis" |
| **Comprensión (15)** | "Mojado foliar desde el pronóstico" | "El pronóstico corregido da la T con ~1,2-1,6 °C de error; el mojado foliar necesita sensor: incluso calibrado, el error es de ~3 h/día" |
| **Escalar a muchos productores** | "El registro ICA sale solo" | "Para exportadores sale el registro ICA (Res. 824/2022); para el mercado nacional, el registro BPA" |
| **Multi-cliente** | "B no ve nada de A" | "B no ve nada de A: lo probamos con 11 ataques y además 11 pruebas funcionales; quedan 2 casos documentados" |

---

## 6. Cómo repetir

```bash
D=/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad
T=$(mktemp -d)
python3 -I $D/pruebas_arquitectura/transformar.py $D/modelo_datos.sql $T/nuevo.sql
python3 -I $D/pruebas_arquitectura/transformar.py $D/verificacion_tecnica/modelo_datos_antes_verificacion.sql $T/antes.sql
docker run -d --pull never --name bgi-verif -e POSTGRES_PASSWORD=local postgres:16-alpine
until docker exec bgi-verif pg_isready -U postgres; do sleep 1; done; sleep 2
docker exec bgi-verif psql -U postgres -c "CREATE DATABASE antes" -c "CREATE DATABASE nuevo"
docker exec -i bgi-verif psql -q -v ON_ERROR_STOP=1 -U postgres -d antes < $T/antes.sql
docker exec -i bgi-verif psql -q -v ON_ERROR_STOP=1 -U postgres -d nuevo < $T/nuevo.sql
docker exec -i bgi-verif psql -U postgres -d antes < $D/verificacion_tecnica/ataques_multiempresa.sql
docker exec -i bgi-verif psql -U postgres -d nuevo < $D/verificacion_tecnica/ataques_multiempresa.sql
docker exec -i bgi-verif psql -U postgres -d nuevo < $D/pruebas_arquitectura/pruebas.sql
docker rm -f bgi-verif
python3 -I $D/verificacion_tecnica/verificacion_rutas.py
/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I $D/motor_perfiles.py
```

---

## 7. Fuentes abiertas en esta verificación

| Tema | Fuente |
|---|---|
| GIM, Tabla 2 | Magarey, Sutton y Thayer 2005, *Phytopathology* 95:92-100: https://www.suddenoakdeath.org/wp-content/uploads/pdf/PHYTO-95-0092%20Magarey%20nappfast.pdf |
| Broome 1995 | UC IPM: https://ipm.ucanr.edu/DISEASE/DATABASE/grapebotrytis.html |
| Oídio de fresa (METOS) | https://metos.global/en/?p=49800 |
| Res. ICA 824/2022 (texto y manual) | https://www.ica.gov.co/importacion-y-exportacion/planes-trabajo-exportacion-vegetales/documentos-relacionados/resolucion_ica_824_2022.aspx |
| Licencias de datasets | API pública de Mendeley Data: `https://data.mendeley.com/public-api/datasets/{j4xs3kh3fd, 8nnd2ypcv3, 6zy6wxhf2v, k2ptxmfjhj}` |
| D1 Ultra y SDK | Archivos locales `datos/raw/agibot_docs/` (datasheet, manual D1 Edu, guía del SDK V2.0.7). Uso interno: no redistribuir (`FUENTES.txt`) |
| Modelo de antracnosis del equipo | `datos/riesgo/README.md` §2.1 |
| Costos del equipo | `datos/finanzas/tabla_final_20ha.csv`, `datos/escalabilidad/unit_economics_salida.txt` |
| Datos IDEAM | `datos/raw/ideam_datosgov_2025/` |
