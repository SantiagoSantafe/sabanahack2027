# Berry Sim — cultivo de arándano + AgiBot D1

Simulación de punta a punta para el Sabana Hack ("Berry Good Idea"): brote en un bloque de arándano, clima Open-Meteo, riesgo de enfermedad, robot D1 y 7 alternativas de detección. Motor en Python; escena 3D en React Three Fiber.

**Fuera de alcance:** gemelo digital con el robot real, física de patas.

## Requisitos (macOS Apple Silicon)

- Python 3.11 (`brew install python@3.11`)
- Node.js 20+ y npm
- (Opcional) curl + unzip para el URDF del D1

## Arranque rápido

```bash
cd ~/Downloads/berry-sim

# Backend
cd sim-core
python3.11 -m venv .venv
source .venv/bin/activate
pip install -i https://pypi.org/simple -r requirements.txt
# Prefetch clima 2025 (también ocurre solo al arrancar)
python -c "from config_loader import load_all_config; from weather import fetch_archive; fetch_archive(load_all_config()['weather'], 2025)"
uvicorn server:app --reload --port 8000

# Frontend (otra terminal)
cd ../web
npm install
npm run dev
```

Abre http://localhost:5173

### URDF del D1 (opcional)

```bash
./scripts/fetch_d1_urdf.sh
```

Descarga el URDF oficial Ultra desde AgiBot (sin licencia declarada; solo demo). Si falla, la escena usa el cuadrúpedo procedural con las mismas medidas.

### Modo batch (evidencia)

```bash
cd sim-core && source .venv/bin/activate
python batch.py --runs 200 --alternatives all --weather historical --year 2025
```

Salida en `sim-core/results/`:

| Archivo | Contenido |
|---------|-----------|
| `runs.csv` | Una fila por corrida: detección, entrega al agrónomo, minutos por recorrido, km, roces y plantas sin revisar |
| `summary.csv` | Mediana y p10/p90 por alternativa |
| `detection_day.png` | Distribución del día de detección |
| `beds_at_detection.png` | Camas infectadas al detectar |
| `risk_days_by_month.csv` / `.png` | Días de riesgo alto por mes, afuera y dentro del macrotúnel |

### Datos de la entrevista con la empresa

Solo se tomó lo que cambia la simulación (configuración en `field.yaml`, `climate.yaml`, `sim.yaml` y `alternatives/REF.yaml`):

- **Bloque:** arándano **en maceta bajo macrotúnel**. Naves de **6,8 m** con **3 camas** (2 a 3 según la finca) y **80 m** de largo (107 macetas por cama a 0,75 m). Camino principal de **5 m** en la cabecera. Se simulan 4 naves (2 macrotúneles) = 12 camas, 1.284 plantas, 0,22 ha; un bloque real tiene 0,5 a 1 ha.
- **Plantas a la cadera o la costilla** (se simulan de 0,9 a 1,3 m; es la interpretación del equipo de una transcripción confusa y falta confirmarla) que **se desbordan hacia los pasillos**. El robot se corre al centro del hueco libre, baja la velocidad (`foliage.careful_*`), roza hojas si es más alto que la rama desbordada y, si es rígido y no cabe, da la vuelta y deja plantas sin revisar. Por eso ancho, alto y rigidez de cada plataforma están en su YAML.
- **Microclima:** la ventilación baja la humedad y la temperatura de día; de noche la humedad alta condensa agua en el follaje; un ventilador olvidado o un alero abierto con lluvia mojan el cultivo. El riesgo se calcula por cama con ese microclima.
- **Sensor de temperatura y humedad en el robot:** registra cada 5 m y en cada incidencia (zona, nave, cama, planta, °C y % HR), como pidió la empresa para su base de datos.
- **Sin WiFi en los bloques:** el robot guarda los registros y los sincroniza al llegar a la base. La alerta llega al agrónomo en ese momento (`metrics.first_alert_delivered_day`). Se exporta todo como CSV desde **Corrida → Exportar registros**.
- **Operario de referencia:** recorre de 6 a 14 h, cada bloque cada ~5 días (15 bloques en 4 a 5 días), registra a mano y digitaliza al final del turno. De ahí sale la línea base de **2,4 h por hectárea**, que se compara con el tiempo de recorrido del robot.
- **El robot no va ligado al aspersor:** AGRAR no asperja (la aplicación la decide el agrónomo de cada finca). El cliente pidió patrullar según el riesgo, sobre todo de noche o al amanecer, porque la alternaria por gutación aparece de una noche a otra. Los robots (A, D, E y F) salen a las **05:00**, con la hoja mojada, y sincronizan antes del turno de las 06:00. La cámara en aspersora (C) sigue atada a los días de aspersión.
- **Enfermedad principal: Botrytis**, según el cliente. Le siguen la alternaria por gutación, el daño de trips y el "velloso/polvoso".

No se modelaron, porque no cambian la detección simulada: los clientes, la jerarquía de la finca, los costos de poscosecha (150 millones de pesos) y las pérdidas del 10 al 25 % de lo cosechado (30 a 40 % sin manejo preventivo). Esas cifras sirven para el pitch, no como parámetros.

### Uso de la interfaz

La auditoría con las heurísticas de Nielsen y las leyes de Maeda está en [docs/AUDITORIA_UX.md](docs/AUDITORIA_UX.md).

- **Barra superior:** alternativa, pausa, velocidad (1×, 10×, 50×), día y hora, y un indicador de estado: "Robot en campo, tiempo real" o "Próximo recorrido: día 4, 05:00" con **Ir al recorrido**. A la derecha: **Auto/Manual**, **Vista** (cámaras y capas), **Corrida** (semilla, mástil, reinicio, exportar CSV, comparar, grabar) y **?** (ayuda).
- **Panel Bloque 1:** pestañas **Resumen** (indicadores, primera detección, último recorrido frente al operario, cobertura), **Clima** (afuera y adentro, ventilación, alero, riesgo por enfermedad y por cama) y **Plantas** (conteo por estado y follaje desbordado).
- **Panel del robot:** pestañas **Sensores** (cámara con confianza frente al umbral, sonda de temperatura y humedad, ArUco, avance por pasillos), **Registro** (con filtro de alertas) y **Datos** (incidencias pendientes de enviar, última sincronización, exportar).
- **Avisos:** agrupados ("3 alertas nuevas"), un aviso corto por pasillo completo y una tarjeta de resumen al terminar el recorrido.
- Cambiar alternativa, semilla o mástil pide confirmación porque reinicia la corrida.

Atajos: `Espacio` pausa, `M` auto/manual, `WASD` conducir, `Shift` rápido, `E` inspeccionar en manual, `C` cámara, `V` sensores, `H` mapa de riesgo, `G` modo dios, `?` ayuda, `Esc` cierra diálogos o sale de grabación. `?fps` muestra el contador de FPS.

### Tiempo simulado

Mientras el robot está en el campo el reloj corre en **tiempo real** (1×): el D1 camina a 0,5 m/s y un recorrido del bloque (8 pasillos, ~720 m) tarda unos 29 minutos en la mediana del batch (antes ~26: con la tasa medida hay más alertas, y cada una corta el paso de tiempo en curso); un operario tardaría ~31 min en la misma área. Cuando el robot está en la base, el tiempo **avanza rápido** (30 min por paso) hasta el siguiente recorrido (05:00 para los robots, 09:00 para la cámara en aspersora y la red fija, 06:00 para el operario). El batch usa la misma lógica con pasos de 2 s durante el recorrido (`sim.yaml → time.batch_patrol_dt_s`).

### Control manual

En modo Manual el cliente conduce el robot con WASD y envía la pose al motor 10 veces por segundo. Las hileras de macetas, las paredes entre naves y los bordes del túnel son obstáculos. La cámara captura las plantas de ambos lados que quedan 1,2 m adelante; `E` fuerza una inspección. Al volver a Auto, el robot retoma los pasillos pendientes.

### Modelos 3D

- **Arbustos:** procedurales (tallos leñosos, grupos de hojas elípticas, racimos de bayas con corona y una rama arqueada hacia el pasillo en las plantas desbordadas), en macetas sobre cobertura negra, con goteo, bajo el macrotúnel. Con más de 800 plantas la escena usa un nivel de detalle menor para mantener ~56 FPS.
- **Baya de Sketchfab (opcional):** [Blueberry de Bogdan_estos](https://sketchfab.com/3d-models/blueberry-19dfbb37d9af4ebc9ebf2c0462409604) es CC-BY y descargable, pero Sketchfab exige iniciar sesión. Descárgalo en formato glTF binario y guárdalo como `web/public/models/blueberry.glb`; la escena lo usa en lugar de la baya procedural. Si lo publicas, da crédito al autor.
- Los modelos "Cartel de minecraft: Tienda de cultivos" y "Modelo 3D cultivo" **no son descargables ni tienen licencia**: no se usan. El cartel de la entrada y las camas se recrearon de forma procedural inspirados en ellos.

### Grabación / comparación

- `?record=1` — pantalla limpia, rótulo SIMULACIÓN, cámara cinematográfica, 1920×1080 (QuickTime: Cmd+Shift+5)
- `?compare=1` — cuadrícula 2×2 (F, A, C, REF) con la misma semilla
- Botones equivalentes en el panel de controles

### Tests

```bash
cd sim-core && source .venv/bin/activate && pytest -v
```

## Arquitectura

```
berry-sim/
  sim-core/          Python 3.11 — motor, clima, WS, batch
  web/               Vite + React + R3F + drei + zustand
  scripts/           fetch_d1_urdf.sh
```

Estado JSON por WebSocket a 10 Hz; un paso del motor por mensaje a 1× (ver "Tiempo simulado"). Misma semilla + misma alternativa → resultado idéntico (verificado por pytest).

Las 6 alternativas + REF son YAML en `config/alternatives/`. El motor no tiene `if` por código de alternativa: solo lee parámetros (`sensor`, `schedule`, `prioritize_by_risk`, `mobility`, etc.).

## Alternativas

| Código | Nombre | Idea |
|--------|--------|------|
| A | D1 Ultra + mástil | Patrulla cada N días, cámara alta; el mástil roza el follaje desbordado |
| B | Red fija | Riesgo por cama → revisión humana del bloque |
| C | Cámara en aspersora | Solo días de aspersión (09:00); niebla baja sensibilidad. AGRAR no asperja: depende de la finca |
| D | Humanoide | Como A, con fallas/atascos en terreno malo |
| E | Ruedas + torso alto | Ve todo el arbusto, pero es rígido (0,7 m) y no cabe donde el follaje se desborda |
| F | Red fija + D1 | Sale al amanecer; el riesgo por cama ordena los pasillos; el D1 bajo pasa bajo el follaje (propuesta) |
| REF | Solo humano | 6–14 h, cada ~5 días, 2,4 h/ha, registro a mano digitalizado a las 14 h |

## Modelos de riesgo (fuentes)

Son los de la capa verificada del equipo (`BerryGoodIdea_handoff/datos/riesgo/risk.py`, 136 pruebas). `sim-core/risk.py` copia las funciones necesarias (no importa nada de `datos/`) y `tests/test_risk.py` repite sus casos de libro y fija los coeficientes de `config/risk.yaml`. Cada modelo da un índice de 0 a 1 por cama y día a partir de las horas de hoja mojada (LWD) y la temperatura media de esas horas.

- **Botrytis (enfermedad principal según el cliente):** Bulger, Ellis y Madden 1987, *Phytopathology* 77:1225. Es una logística de infección de **flores de fresa** (proxy), con los coeficientes de NC State IPM, y reproduce su gráfica: 0,50 a 13,8 h y 0,70 a 16,5 h a 20,5 °C.
  - Umbrales publicados: medio 0,50 (umbral de acción, MacKenzie y Peres 2012b) y alto 0,70.
  - **Rango de validez:** 5–30 °C y hasta 32 h de mojadura (NO VERIFICADO directamente). En la Sabana la hoja se moja a 8–11 °C, en el borde frío de ese rango.
  - Regla de arándano, solo como contexto: más de 6 h de mojadura entre 14 y 25 °C (Rivera et al. 2013, sin validar en campo).
- **Antracnosis:** se toma la mayor de dos curvas, para favorecer la sensibilidad. Umbrales 0,15/0,50 (MacKenzie y Peres 2012a).
  - (a) Wilson, Madden y Ellis 1990, *Phytopathology* 80:111. Es de fruto de fresa, pero es la ecuación del Blueberry Advisory System de UF/IFAS, validada en arándano por Gama et al. 2021. Bajo 9,33 °C se recorta la pendiente.
  - (b) Aproximación calibrada en arándano con Gillett y Schilder 2009, *Acta Hortic.* 810:355: la mojadura que lleva el índice a 0,5 es el punto medio de cada rango publicado.
  - **No se usa Miles et al. 2013:** sus coeficientes nunca se obtuvieron, porque el artículo es cerrado. La versión anterior de este simulador traía coeficientes "de Miles" sin fuente, y también un juego de Botrytis "fruto, Tabla 2" sin fuente. Los dos se eliminaron.
- **Roya:** es una **regla de vigilancia**, no un modelo validado. Aproxima con el modelo genérico de infección (GIM) de Magarey et al. 2005, con Topt de 21,5 °C (Pfister et al. 2004, en rododendro); Tmin, Tmax y LWDmin son SUPUESTOS. En la Sabana sus días de riesgo dependen de Tmin = 8 °C. La regla anterior del brief (19–25 °C) se eliminó: casi nunca se activa.
- **Hoja mojada:** dentro del túnel, HR ≥ 90 % (escenario central del equipo de clima; falta calibración local). La lluvia solo moja el follaje si el alero quedó abierto. Afuera (gráfica de días de riesgo): HR ≥ 90 % o lluvia ≥ 0,5 mm/h. La llovizna espuria de Open-Meteo hace inservible "lluvia > 0".
- **Cómo entra al motor:** la presión de cada cama es el máximo de los tres índices. La Botrytis domina ese máximo el 99 % de los días (clima 2025 dentro del túnel). Por eso los niveles de la interfaz (medio 0,50, alto 0,70) y el umbral de la red fija (B: 0,50) son los publicados para Botrytis. Los de antracnosis y roya son más bajos, así que el día en que domina una de ellas se muestra un nivel por debajo.
- **Simplificación conocida:** el motor suma las horas mojadas de la cama en el día calendario. No usa los periodos de mojadura de `datos/riesgo` (que se cortan con 4 h secas). En la mediana coinciden (~11 h por noche), pero la versión diaria corta los episodios de más de 24 h. Con el clima 2025, la Botrytis llega a 0,70 en 5–6 días por cama, frente a 14–16 con periodos: el motor subestima la cola alta.
- **Correcciones del motor (oct-2026):** solo contagian las plantas que de verdad tienen una enfermedad. Antes, una planta sana con una falsa alarma pendiente o confirmada contagiaba antracnosis a sus vecinas; con la tasa medida de falsas alarmas, era ~80 % de la presión de contagio en F. Una alerta descartada sobre una planta infectada que aún no muestra síntomas ya no la "cura": vuelve a incubar. Antes, la falsa alarma detenía su latencia y la infección desaparecía; con la tasa medida, A borraba ~8 infecciones por corrida y casi nunca detectaba. Además, las camas y plantas "infectadas al detectar" se cuentan por verdad de campo, sin las falsas alarmas. **Pendiente:** mientras una alerta espera al agrónomo (0,5–2 días), la planta deja de incubar. Con muchas falsas alarmas eso retrasa los síntomas de parte de los focos, más en A y D (más falsas alarmas por planta) que en F.

## Clima

- Open-Meteo archive/forecast, sin API key. Coordenadas por defecto: Chía 4.86, −74.06.
- Caché en `sim-core/data/weather_cache/` (el de 2025 se versiona para demos offline).
- Si no hay red ni caché: año sintético marcado `# SUPUESTO`.
- Atribución: [Open-Meteo](https://open-meteo.com/) (CC BY 4.0), uso no comercial en el plan gratuito.

## Supuestos y provisionales

Todo número sin fuente primaria lleva `# SUPUESTO` en el YAML. Lo MEDIDO viene de la evaluación del equipo; lo PUBLICADO, de la fuente citada en el YAML. Resumen:

| Parámetro | Marca | Nota |
|-----------|-------|------|
| Espaciado plantas 0,75 m | SUPUESTO | Brief; Colombia UMNG sugiere 0,8–1,0 m |
| Nave 6,8 m, 3 camas, 80 m, camino de 5 m | Dato empresa | El pasillo resulta de 6,8 / 3 = 2,27 m entre centros de hilera |
| Altura de planta 0,9–1,3 m | SUPUESTO (interpretación del dato empresa) | "A la cadera o la costilla"; dijo "unos 50" sin aclarar. Antes 1,3–1,7 m. Por confirmar |
| Follaje desbordado: 22 % de plantas, +0,25–0,6 m | SUPUESTO | La empresa lo describe; falta medir cuánto |
| Maceta 0,42 m, cobertura 0,6 m | SUPUESTO | |
| Efecto del plástico (+3 °C de día, +6 % HR de noche) | SUPUESTO | `climate.yaml` |
| Ventilación: −12 % HR, −2 °C sobre 85 % HR | SUPUESTO | Dato empresa: hay controladores |
| Olvido de ventilador 5 %/día, alero abierto 10 % con lluvia | SUPUESTO | La empresa menciona ambos casos |
| Hoja mojada: HR ≥ 90 % (afuera, o lluvia ≥ 0,5 mm/h) | SUPUESTO | Escenario central del equipo de clima; calibración local pendiente |
| Coeficientes de Botrytis, antracnosis y GIM | PUBLICADO / APROXIMACIÓN | `risk.yaml`, con cita por coeficiente; Tmin, Tmax y LWDmin de roya son SUPUESTOS |
| Niveles de riesgo medio 0,50 y alto 0,70 | PUBLICADO (Botrytis) | NCSU FLSAS; MacKenzie y Peres 2012b. Un solo par para las tres enfermedades (la interfaz admite uno) |
| Umbral de la red fija (B) 0,50 | PUBLICADO | Umbral de acción de Botrytis. Antes 0,12, ajustado a los modelos sin fuente |
| Escala riesgo → contagio 0,45 (antes 1,35) | SUPUESTO | Re-escalada (×0,33) para conservar la velocidad de brote ajustada para la demo al cambiar de modelos. Con el operario (REF) se comprobó: termina con una mediana de 6 plantas infectadas, antes y después |
| Sin fenología (índice a susceptibilidad máxima) | SUPUESTO | `datos/riesgo` tiene multiplicadores por etapa, también SUPUESTOS |
| Sincronización al llegar a la base | Dato empresa | No hay WiFi en los bloques |
| Operario 2,4 h/ha, 6–14 h, cada 5 días | Dato empresa | 15 bloques en 4–5 días |
| Periodo latente 3–7 d | FUENTE (Botrytis) | Neugebauer et al. 2024. El motor usa un solo rango: acorta la antracnosis (5–10 d, MSU) y la roya (10–21 d; 15–21 d en 'Biloxi') |
| Enfermedad del foco inicial: 1/3 cada una | SUPUESTO | El cliente dice que la principal es Botrytis |
| Prob. contagio vecinos | SUPUESTO | Sin tasas publicadas para arándano |
| Clasificador: sensibilidad 0,80 [IC95 0,66–0,89]; falsas alarmas 0,36 por planta sana (especificidad 0,64) | MEDIDO | Test congelado de DrBerry (43/54 y 5/14). Escenario pesimista (estrés pantalla→cámara sintético): 0,65 y 0,64. Por clase: oídio 0,95, Heliothis 1,00, alternaria 0,29 |
| Botrytis, antracnosis y roya como clases visuales futuras con sensibilidad 0,80 | SUPUESTO | El clasificador real no tiene esas clases. Con `visual_classes_mode: current` el robot no las ve y solo detectan las personas |
| Hoja mojada ×1,8 en falsas alarmas (tope 0,64) | SUPUESTO | Sin medición con hoja mojada; el tope es la tasa pesimista medida |
| Factor de altura de cámara (mínimo 0,35) | SUPUESTO | La cámara baja del D1 queda siempre en el mínimo |
| Altura cámara D1 0,3 m | SUPUESTO | Estimada; URDF sin link de cámara |
| Inicio de recorrido: robots 05:00; C y B 09:00; operario 06:00 | SUPUESTO (dato empresa: noche o amanecer) | El robot no va ligado al aspersor. Al amanecer casi todas las camas tienen hoja mojada (99 % de los días en 2025) |
| Luz propia de noche; la sensibilidad medida de día vale de noche | SUPUESTO | No medido |
| F cada 2 días; A, D, E cada 3 | SUPUESTO | El riesgo ordena los pasillos de F, pero no agrega recorridos |
| Frecuencia aspersión 10 d (solo C) | SUPUESTO | Guías 7–14 d; AGRAR no asperja |
| Anticipo de cámara 1,2 m | SUPUESTO | `robot.yaml → path` |
| Parada por sospecha 4 s | SUPUESTO, **no aplicado** | `robot.yaml → path.stop_inspect_seconds` se lee, pero el motor no llama a `hold()`: cada alerta solo corta el paso en curso (≤ 2 s en el batch). Con ~190 falsas alarmas por recorrido, aplicarla sumaría ~13 min a cada recorrido de F |
| Falsos positivos humanos 3 % | SUPUESTO informado | `datos/simulacion/parametros.yaml`: especificidad 0,97 (Combes et al. 2025). Antes 1 % sin fuente |
| Sensibilidad humana por planta revisada (REF ~0,11; B ~0,37) | SUPUESTO, sin revisar | `parametros.yaml` da 0,65 con síntoma claro y 0,35 inicial. La de la simulación es más baja y favorece a los robots |
| Costos: falsa alarma 30 USD; caso no detectado 2.160 USD/ha/semana | SUPUESTO del equipo | 12.000 kg × 3 % × 6 USD. El motor no los usa; justifican preferir sensibilidad |
| URDF D1 | — | Sin licencia declarada; no se versiona |

## HUD / estados de planta

Sana · En riesgo · Infectada asintomática (naranja solo en modo dios) · Con síntomas · Alerta pendiente · Confirmada · Tratada · Falsa alarma. Paleta en `web/src/theme/palette.ts`.

## Licencias de terceros

- Open-Meteo data: CC BY 4.0
- AgiBot D1 URDF/STL: licencia no declarada — solo uso interno/demo; no redistribuir
- Código de este repo: ver con el equipo del hackathon
