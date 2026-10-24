# HANDOFF · Berry Good Idea (Sabana Hack, oct 2026)

Archivo para pasarle TODO el contexto a otra IA o a otra sesión. Léelo completo antes de actuar. Ante cualquier conflicto, los archivos de la carpeta `datos/` y los reportes de verificación mandan sobre este resumen.

## 1. El reto
- Hackathon Sabana Hack, unas 20 h, ya corriendo. Pitch y demo: **5 minutos en total**.
- Reto "Berry Good Idea": un robot que detecta a tiempo, cama por cama, señales fisiológicas y ambientales de enfermedad en arándano, y convierte cada hallazgo en alerta + registro.
- Rúbrica (100): Comprensión 15, Pertinencia 20, **Demo 25**, **Evidencia 20**, Justificación 10, Comunicación 10.

## 2. Equipo y recursos
- 5 personas: administrador (finanzas) y 4 ingenieros: robótica (el usuario), UI/UX, analítica de datos y uno más.
- Robots: AgiBot X2, X2 Ultra, **D1 EDU** (tiene código de visión propio, SDK en Python, **sin interfaz ROS**), Booster y NAO.
- Lo que **no** tenemos: plantas, impresora y sensores físicos. Sí tenemos GPU o nube, y el Mac (Apple Silicon).
- Hay mentores en el evento para hacerles preguntas.
- La solución debe ser **escalable para que la organización la venda a muchos productores**. La Sabana es solo el ejemplo.

## 2b. Respuestas del mentor (AGRAR): leer `RESPUESTAS_MENTOR.md`
Puntos que cambian la propuesta:
- **El cliente es AGRAR,** una empresa de automatización de invernaderos (ventilación, PLC, sensores por bloque). Quiere venderlo a grupos floricultores y de arándano, en Colombia y fuera.
- **Su negocio:** 90–110 millones de COP por proyecto, punto de equilibrio en menos de 2 años, margen de al menos 40 % y unos 10 proyectos al año.
- **El cultivo:** maceta bajo invernadero o macrotúnel con malla antitrips. Naves de 6,8 m (invernadero) o 12,5–13 m (macrotúnel) por ~80 m de largo, con 2–3 camas por nave. Camino central de 5–6 m. Bloques de 0,5–1 ha y fincas de 20–25 ha. El arbusto llega a la cadera o la costilla y se sale hacia el pasillo.
- **Enfermedades:** la principal es Botrytis. Le sigue alternaria por gutación nocturna, que aparece de una noche a otra. Trips (ver el daño), y "velloso/polvoso", que solo se detectan viéndolos.
- **AGRAR no hace aspersión.** El manejo fitosanitario lo decide el agrónomo de cada finca.
- **Requisito explícito:** el robot debe enviar temperatura y humedad **en el punto** de cada detección, junto con la ubicación.
- **Conectividad:** no hay red en los bloques. Hay PLC por bloque comunicados por LoRaWAN, SDI-12 o Modbus RTU, e internet solo en la oficina. El robot tiene que guardar y reenviar.
- **Monitoreo hoy:** a mano en papel; una persona tarda 4–5 días por cada 12–15 bloques. Pérdidas del 10–25 % de la cosecha (30–40 % sin prevención).

> **Cifras: la fuente única es `CIFRAS_CLAVE.md`.** Si algo de abajo la contradice, vale ella.

## 3. Decisiones tomadas (algunas en revisión por las respuestas del mentor)
- **Propuesta principal: híbrido.** Red fija de sensores ambientales (riesgo) + cuadrúpedo D1 que recorre las camas **según el riesgo, sobre todo de noche o al amanecer** (AGRAR no asperja; el kit en la aspersora quedó como alternativa descartada; la versión inicial decía "delante del aspersor"). La cámara clasifica, sale una alerta con triage al agrónomo, el operario confirma o descarta, y queda registro y mapa de calor, con aspersión dirigida.
- **Demo:** el D1 real mira una pantalla de PC que muestra hojas del conjunto de prueba, elegidas por el jurado. Clima real de Open-Meteo. El robot reacciona (se detiene). La confirmación la hace un jurado. Lo que sea teleoperado se dice en voz alta.
- **Alternativas:** se muestran en un video de simulación de ~40 s en pantalla dividida, más una matriz de 6 alternativas: A D1+mástil, B red fija, C kit en aspersora, D humanoide, E ruedas, F híbrido. F gana con **89,0** (6 criterios; 87,7 con Escalabilidad 15 %; 85,4 con costo 30 %), `datos/finanzas/agrar/RESUMEN.md` §5. *Versión anterior:* ~83 (matriz verificada previa al contexto AGRAR, con la que F empataba con B al subir el costo).
- **Enfermedades:**
  - Visual: oídio, alternaria, Heliothis y sana (dataset DrBerry).
  - Ambiental: **Botrytis (principal según el mentor)** y antracnosis.
  - Roya: solo regla.
  - Fuera de alcance: Phytophthora, *D. suzukii*, trips y ácaros.
- **Errores:** preferimos falsas alarmas (~30 USD) a casos no detectados (~2.160 USD/ha por semana; supuesto).
- **Gemelo digital** (más adelante): escena 3D en el navegador (Three.js) + puente en Python con el SDK del D1, **en los dos sentidos**: desde la pantalla se ordena "inspeccionar cama X".
- **Simulación:** núcleo en Python + Three.js. El prompt completo está en `PROMPT_simulacion_camas.md`; lo construye otro compañero.

## 4. Correcciones importantes (no repetir estos errores)
- **Antracnosis:** NO se usa Miles 2013, porque no se consiguieron sus coeficientes. Lo que corre es **Wilson 1990** (fruto de fresa) **+ una aproximación de Gillett y Schilder 2009**.
- **Botrytis:** Bulger 1987 (fresa) usado como proxy. Broome 1995 es de **uva**.
- **Competencia:** Saga Thorvald **sí detecta** enfermedades con cámara desde 2025. Lo que nos diferencia es el paquete completo: riesgo + cama por cama + triage + registro, sin atarse a una marca.
- **D1 EDU:** **sí trae cámara frontal** de 1920×1080, con video por RTSP en `rtsp://192.168.234.1:8554/test` (Wi-Fi) o `rtsp://192.168.168.168:8554/test` (cable). No tiene interfaz ROS ni cómputo libre a bordo. El SDK (Python 3.10, Ubuntu 22.04) **no corre en el Mac**, y WSL no está soportado: probar WSL con red "mirrored", y si falla, un USB booteable con Ubuntu. Comanda velocidad con `move(vx,vy,yaw)`; si pasan 3 s sin comandos, se acuesta.
- **Clasificador (modelo EN USO `modelo_camara`, medido con la cámara del D1):** sensibilidad 42/54 = 0,78 (IC por grupo 0,61–0,92), falsas alarmas 4/14 = 0,29 (IC 0,00–0,71), alternaria 3/14. Ver §6d y `reportes/reentreno-camara.md`.
  - *Modelo anterior / imagen limpia (`modelo_final`, sin cámara):* 43/54 = 0,80 y 5/14 = 0,36. No citar como rendimiento del robot.
  - NO mostrar "87/87 con 0/14" (recortes): las lesiones de alternaria miden ~96 px y el tamaño solo las separa (`reportes/verificacion-ml.md` §4.3). Cifra limpia: 52/52 (oídio + Heliothis) con 0/14, cota superior con localización perfecta.
- **Costo del híbrido por ha/año (unificado):** **~867 USD/ha/año** para AGRAR (22,5 ha; 717 sin falsas alarmas), `finanzas/agrar/RESUMEN.md` §6. Las otras cifras responden a otro supuesto: 722 = productor que compra y arma todo, en 20 ha; 820 = opción A, D1 sin red con 2 robots en filas de campo; 520 = precio de servicio RaaS (otro modelo); 430 = obsoleta.
- **Hardware del kit:** documento de presentación ≈ 34,85 M COP sin IVA (≈ 41,5 M con IVA; D1 Ultra, 1 batería de repuesto, Jetson, LoRaWAN). `RESUMEN.md` §1 trae 35,40 M: la diferencia (~0,55 M) es la fuente DC-DC, SSD y caja del cómputo (0,54 M) que AGRAR ya tiene; `RESUMEN.md` ya cuenta 1 batería. Cámaras fijas ≈ 2.300 M; humanoides 4–8×.
- **Capacidad por robot:** vigente para AGRAR ~19 ha/semana (patrulla nocturna de riesgo, 0,5 m/s). 12,5 = de día sin red (finanzas A); 16,6 = 0,4 m/s con red; 24,9 = finanzas F con red; 36 = modelo de negocio a 0,8 m/s. Frase: "entre 16 y 36 ha según la velocidad medida".
- **Registro ICA (Resolución 824 de 2022):** aplica solo a exportadores. Para el mercado nacional aplica BPA.
- **Licencias:**
  - YOLO/ultralytics es AGPL-3.0.
  - La API gratuita de Open-Meteo es solo para uso no comercial.
  - El dataset de fresa de Mendeley es CC BY-NC.
  - PlantVillage es CC BY-SA.
- **Precios AgiBot** (FOB México, USD): D1 EDU 5.999, D1 Ultra 7.499, D1 MaxPro 67.999, X2 Ultra 39.999 y G1 75.199. Factor de importación ~1,35 (supuesto).

## 5. Archivos clave
| Archivo | Qué es |
|---|---|
| `CIFRAS_CLAVE.md` | **Fuente única de cifras** (clasificador, riesgo, finanzas, capacidad, hardware, frase de limitaciones). Citarla en vez de copiar números |
| Documento del equipo (Claude Docs) https://claude.ai/artifact/LGaKdVBrfj9E9nWZjkuyig | Plan completo en 20 secciones. **Todavía no tiene las correcciones de la sección 4** |
| `Preguntas_mentor_BerryGoodIdea.pdf` | 30 preguntas para el mentor. Faltan las 31–35: fenología, etapa de cada enfermedad, importancia relativa, frutos momificados, periodo latente |
| `PROMPT_simulacion_camas.md` | Prompt para construir la simulación |
| `datos/REPORTE_DATOS.md` | Consolidado del workflow de datos (si ya existe) |
| `datos/ESCALABILIDAD.md` | Modelo de negocio, arquitectura multi-finca, otros cultivos, mercado |
| `datos/resultados/ml/RESULTADOS.md` | Métricas del clasificador, prueba fuera del dataset, guía para GPU |
| `datos/resultados/detector.yaml` | Matriz de confusión para la simulación |
| `datos/resultados/ml/modelo_final/` | Modelo + `predict.py`, para conectarlo al robot |
| `datos/resultados/backtest/` | Días de riesgo por mes y `riesgo_hoy.json` |
| `datos/riesgo/risk.py` | Modelos de riesgo, con sus pruebas |
| `datos/clima/` | Caché de Open-Meteo y cliente de clima |
| `datos/finanzas/roi.py` | ROI y sensibilidad |
| `datos/escalabilidad/` | Economía unitaria, SQL multi-cliente, perfiles de cultivo (YAML), operación |
| `datos/simulacion/parametros.yaml` | Parámetros de la simulación, con fuente |
| `datos/reportes/*.md` | Un reporte por agente. Los de **verificacion-*** mandan |
| `datos/.secrets/roboflow_api_key` | API key de Roboflow. **No imprimirla ni copiarla.** Rotarla después del hackathon |
| `datos/.venv/` | Entorno Python con torch, ultralytics y open_clip |

## 6d. Modelo con capturas reales de la cámara (24-oct-2026)
- **Modelo en uso:** `resultados/ml/modelo_camara`, con preprocesamiento del panel (corrección de color + auto-recorte). Panel: `... panel_demo.py --modelo resultados/ml/modelo_camara --sim-url http://localhost:8010`.
- **Test capturado por la cámara** (68 hojas, 14 sanas): sensibilidad 0,78 · falsas alarmas 0,29 · enfermedad exacta 0,54.
  - Con B, en las mismas condiciones, las falsas alarmas eran del **100 %**.
  - Alternaria sigue débil (3/14).
  - Detalle en `reportes/reentreno-camara.md`.
- **Gemelo digital y ruta real:** guía en `datos/robot/GEMELO_DIGITAL.md`. Sim-core en el puerto 8010, web en 5173, puente con `abrir_puente.sh juanda`.
- **Puente corregido:** tras `standUp` manda velocidad cero continua, y el lazo va a 50 Hz. El D1 llega al modo 18 en ~1 s.

## 6c. Panel de la demo y modelo (24-oct-2026, pausado aquí) — VERSIÓN ANTERIOR: el modelo en uso hoy es `modelo_camara` (§6d)
- **Panel:** `datos/robot/panel_demo.py`. Muestra la cámara del D1 en vivo con la predicción. Incluye:
  - Filtro de "¿hay hoja?" con CLIP (`robot/filtro_hoja.py`, umbral 0,9).
  - Auto-recorte por color de hoja, corrección de color (balance de blancos y CLAHE) y zoom del modelo con multiescala.
  - Decisión estable sobre 8 cuadros.
  - Visor de hojas con etiqueta real frente a la del robot (✅/❌) y modo captura de dataset.
- **Retomar el panel:**
  `cd ~/Downloads/SabanaHack/datos && HF_HUB_OFFLINE=1 .venv/bin/python -I robot/panel_demo.py --robot-ip 10.90.251.84 --port 8092 --modelo resultados/ml/modelo_aug_B`
  Panel en http://localhost:8092 · visor en `http://<IP_Mac>:8092/hoja` (tecla f = pantalla completa, e = ocultar la franja).
- **Modelo (anterior, reemplazado por `modelo_camara`):** B, en `resultados/ml/modelo_aug_B`, entrenado con aumentos de brillo, color y pantalla.
  - Test limpio (imagen limpia, sin cámara): sensibilidad 0,80 y falsas alarmas 0,29. Con la cámara real B daba falsas alarmas 1,00.
  - Cambio de clase bajo estrés: del 29 % al 16 %.
  - Alternaria sigue débil.
  - Detalles en `reportes/reentreno-aumentos.md`. El modelo anterior sigue en `modelo_final/`.
- **Auto-recorte por color**, medido en el test (una corrida, observación sin repetir): falsas alarmas de 5/14 a 1/14 y enfermedad exacta de 45 a 49 de 68.
- **Lo que se vio con la cámara real:** la hoja en pantalla aparece cian o lavada. Antes de agregar la corrección de color, el filtro la rechazaba o confundía la enfermedad.
- [ ] **Siguiente paso clave:** captura con la cámara real (botón "Iniciar captura" del panel, ~9 min, 410 fotos). Luego reentrenar B con las capturas de train, fijar el umbral con las de val y medir sobre las 68 de test capturadas.
- [ ] Probar el teleop moviendo el robot (solo se hizo el `check`).

## 6b. Robot funcionando (24-oct-2026, madrugada)
- [x] **El SDK controla el D1 desde el Mac** (OrbStack con Ubuntu 22.04 + `datos/robot/udp_relay.py` en las dos direcciones). Red "Juanda": robot `10.90.251.84` (`wlan0`, fija) y Mac `10.90.251.94` (manual). Prueba: `conexión: True`, batería 61 %. Ver `GUIA_ROBOT_SIN_INTERNET.md` §12.
- [x] Configuración del robot cambiada a `wlan0` (respaldos `*.bak` junto a cada archivo). Basta `sudo systemctl restart robot-launch.service`; no hace falta reiniciar el robot.
- [x] Inferencia en vivo desde el RTSP del robot: 80–125 ms por cuadro.
- [ ] **Riesgo encontrado:** el clasificador dijo "alternaria 99,9 %" mirando pantalones y sillas. **Falta un filtro de "¿hay una hoja?"** antes de alertar, y usar `--roi` sobre la pantalla en la demo.
- [ ] Revisar `networkmanager-cleanup.service` en el robot (que no borre "Juanda" al reiniciar).
- [ ] Teleop real probado solo con `check`. Falta pararlo con U y moverlo, con la zona despejada y el mando en la mano.

## 6a. Estado actualizado (después de la entrevista con AGRAR)
- [x] Workflow de datos terminado: ver `datos/REPORTE_DATOS.md`.
- [x] Finanzas con AGRAR: `datos/finanzas/agrar/RESUMEN.md`. Kit con D1 Ultra ~100 M COP, retorno en ~24 meses con 1 punto de pérdida evitado, cifra unificada ~867 USD/ha/año, matriz híbrido 89 (6 criterios).
- [x] Documento del equipo actualizado con las respuestas del mentor, los 8 cambios, las correcciones, la evidencia, la escalabilidad y la matriz nueva.
- [x] Propuesta principal aceptada por el equipo: híbrido = sensores de AGRAR + D1 (23-oct-2026).
- [x] Capacidad por robot unificada en `CIFRAS_CLAVE.md` §4 (19 ha/semana para AGRAR; 12,5–36 según supuesto).
- [ ] Regenerar el PDF del mentor con las preguntas 31–50, que están en el documento.
- [ ] Robot: probar el video RTSP desde el Mac, montar el SDK en Ubuntu (WSL "mirrored" o USB booteable) y conseguir un sensor de temperatura y humedad.

## 6. Estado y pendientes (versión anterior; las cifras vigentes están en `CIFRAS_CLAVE.md`)
- [x] Workflow de escalabilidad (10 agentes), terminado.
- [ ] Workflow de datos: faltaba el verificador de ML y el integrador, que se reanudaron en Sonnet. Revisar si existe `datos/REPORTE_DATOS.md`.
- [ ] Revisar a mano 2–3 cifras clave contra su fuente.
- [ ] Actualizar el documento del equipo: correcciones de la sección 4, resultados del clasificador y del backtest, escalabilidad, criterio nuevo "Escalabilidad" en la matriz y plan de datos con casillas.
- [ ] Regenerar el PDF del mentor con las preguntas 31–35 y las que salgan de `REPORTE_DATOS.md`. El script está en el scratchpad de la sesión; si no está, rehacerlo con reportlab.
- [ ] Lo del robot:
  1. Montar la cámara en el D1 y probarlo frente a la pantalla (20 fotos).
  2. Conectar `predict.py`.
  3. Hacer que el D1 se detenga cuando hay detección.
  4. Leer la odometría.
  5. Más adelante, el gemelo digital en los dos sentidos.
- [ ] Respuestas del mentor: suelo o maceta, macrotúnel, pasillo, altura del arbusto, aspersión, falsas alarmas toleradas, roles en la finca, efectividad del monitoreo actual.
- [ ] Preguntas sin responder del equipo: cámara del D1, dónde corre el modelo, odometría, espacio para la pista, modelo exacto del "D2 Edu", qué robot es el "C5".

## 7. Cómo trabajar (preferencias del usuario)
- En español. Crítica directa y objetiva, sin adular.
- No asumir: preguntar lo que falte.
- Cada cifra con fuente, o marcada como SUPUESTO / NO VERIFICADO.
- Subagentes en **Sonnet** para ahorrar tokens.
