# Prompt: simulación del cultivo de arándano y del robot (sin gemelo digital todavía)

Eres un ingeniero de software senior, experto en gráficos 3D web (Three.js / React Three Fiber) y en simulación en Python. Vas a construir, junto con un equipo de hackathon, **la simulación del entorno de un cultivo de arándano y del robot que lo recorre**. Trabajas en macOS (Apple Silicon). Tenemos pocas horas: prioriza que funcione de punta a punta y luego hazlo bonito.

**Fuera de alcance por ahora:** la conexión con el robot real (gemelo digital), la física de las patas y cualquier motor de física. El robot se mueve por cinemática y animación procedural.

---

## 1. Contexto del reto (Sabana Hack, "Berry Good Idea")

- Pregunta: ¿cómo puede un robot detectar a tiempo, cama por cama, señales ambientales o fisiológicas de enfermedad en un cultivo de arándano, y convertir cada hallazgo en una alerta y un registro?
- Vocabulario:
  - **Bloque:** zona que se maneja como una unidad.
  - **Cama:** hilera elevada donde van las plantas, con un pasillo entre camas.
  - **Aspersión:** aplicación de productos líquidos; se recorre el bloque cama por cama.
- Nuestra propuesta (híbrido):
  1. Una red fija de sensores ambientales anticipa el riesgo.
  2. Un cuadrúpedo AgiBot D1 recorre las camas empezando por las de riesgo alto. **Actualización (entrevista con AGRAR): la patrulla principal es nocturna o al amanecer, activada por el riesgo; AGRAR no asperja, así que NO va "delante del aspersor".** El kit en la aspersora (alternativa C) queda como alternativa descartada, solo para la comparación en pantalla dividida.
  3. Una cámara clasifica las hojas.
  4. Se genera una alerta con triage al agrónomo, el operario confirma o descarta, y todo queda registrado.
- Evaluación: el jurado da 25 puntos a la demo y 20 a la evidencia. Por eso la simulación **tiene que producir evidencia medible**, no solo verse bonita.
- Pitch de 5 minutos: las alternativas se muestran como **un video en pantalla dividida de ~40 s** generado con esta simulación.

## 2. Para qué sirve esta simulación

1. **Escena 3D bonita y colorida** del bloque, las camas, las plantas y el robot, para el pitch y los videos.
2. **Propagación del brote día a día**, dependiente del clima.
3. **Comparación justa de 6 alternativas** con el mismo brote (misma semilla), con dos métricas: día de detección y camas infectadas en ese momento.
4. **Modo sin pantalla** que corre cientos de simulaciones por alternativa y exporta métricas (CSV/JSON) para las diapositivas de evidencia.

## 3. Arquitectura y stack

```
/sim-core        Python 3.11: numpy, fastapi, uvicorn, websockets, pydantic
  engine.py      estado del bloque, propagación, clima, riesgo, robot, detección
  alternatives.py  configuración de las 6 alternativas
  weather.py     cliente de Open-Meteo con caché local (funciona sin internet)
  server.py      WebSocket: emite el estado por tick; recibe controles (play, pausa, velocidad, semilla, alternativa)
  batch.py       modo sin pantalla: N corridas por alternativa → results/*.csv + resumen
  config/*.yaml  TODOS los parámetros (nada fijo en el código)
/web             Vite + React + TypeScript + @react-three/fiber + @react-three/drei (+ zustand para el estado)
  Escena 3D, panel lateral (HUD), controles, modo grabación
```

- Comandos esperados: `uvicorn server:app --reload` y `npm run dev`. Documenta todo en un README.
- El estado viaja como JSON por WebSocket a 5–10 ticks por segundo. Un tick equivale a una fracción de día, configurable.
- **Semilla reproducible:** con la misma semilla y la misma alternativa, el resultado es idéntico.

## 4. Modelo del entorno

**Geometría por defecto** (todo configurable). Fuente: el mentor de AGRAR; ver `RESPUESTAS_MENTOR.md`.

| Parámetro | Valor por defecto | Nota |
|---|---|---|
| Tipo de estructura | **Invernadero** con techo de plástico translúcido y laterales con malla antitrips. Opción de macrotúnel | Confirmado por el mentor |
| Sistema | **Maceta** (hilera de macetas sobre la cama) | Confirmado |
| Bloque | 0,5 ha (opción 1 ha) | Confirmado |
| Naves por bloque | ~8 en 0,5 ha | Calculado: 0,5 ha / (6,8 m × 80 m) ≈ 9 |
| Ancho de la nave | **6,8 m** en invernadero; 12,5–13 m en macrotúnel | Confirmado |
| Largo de la nave | **~80 m** | Confirmado |
| Camas por nave | **2–3** | Confirmado |
| Camino central | **5–6 m** de ancho, perpendicular a las naves | Confirmado |
| Distancia entre plantas | 0,75 m | SUPUESTO |
| Altura del arbusto | 0,9–1,3 m (cadera o costilla), variable por planta | Interpretación del mentor |
| Ramas hacia el pasillo | Sí: el pasillo útil se angosta; el robot debe pasar sin tocar los racimos | Confirmado; ancho útil SUPUESTO |
| Sensores fijos | Un PLC o datalogger por bloque con temperatura y humedad (los de AGRAR) | Confirmado |
| Base de carga | En la cabecera del bloque o la oficina, con red | SUPUESTO |

**Estados de cada planta y colores** (define una paleta como tokens en un solo archivo):

| Estado | Color del follaje | Nota |
|---|---|---|
| Sana | Verde | |
| En riesgo (por el clima) | Verde con brillo amarillo | |
| Infectada sin síntomas | Igual que sana | Naranja **solo** en el "modo dios" |
| Con síntomas | Rojo | |
| Alerta pendiente de confirmar | Contorno pulsante | |
| Confirmada | Rojo oscuro con marca | |
| Tratada | Azul | |
| Falsa alarma | Contorno gris | |

**Elementos visuales:**

- Suelo de tierra con textura.
- Camas como bloques elevados café oscuro.
- Arbustos hechos de grupos de esferas con `InstancedMesh` (deben aguantar 400 o más plantas a 60 fps en una MacBook).
- Frutos como esferas pequeñas azul arándano, que se vuelven café en plantas enfermas.
- Cielo y luz suave con sombras.
- **Neblina** cuya densidad depende de la humedad relativa.
- **Partículas de lluvia** cuando hay precipitación.
- **Mapa de calor del riesgo** semitransparente sobre el suelo, por cama.
- **Modo dios:** botón que revela las plantas infectadas sin síntomas.
- **Cámaras:** órbita libre, cámara que sigue al robot, y una cámara cinematográfica con recorrido predefinido para grabar.
- **Panel lateral (HUD):** día simulado, clima (temperatura, humedad, horas de hoja mojada), riesgo por enfermedad, plantas infectadas, con síntomas y detectadas, falsas alarmas, casos no detectados, alternativa activa.
- Rótulo fijo **"SIMULACIÓN"** en pantalla.

## 5. Modelo del robot (AgiBot D1 EDU)

- Medidas reales: 635 × 360 × 420 mm, 15,5 kg. Cámara a ~0,3 m del suelo. Velocidad máxima de 3,5 m/s; en inspección usa ~0,5 m/s, que es configurable.
- **Modelo 3D:**
  - Si el equipo tiene el URDF/MJCF oficial del D1 (AgiBot lo publica para Isaac Sim y MuJoCo), cárgalo con `urdf-loader` en Three.js.
  - Si no, construye un cuadrúpedo estilizado con primitivas: cuerpo, cabeza con cámara y 4 patas de 3 segmentos. Debe verse como un robot real, limpio y moderno, no como un juguete.
- **Animación procedural** del paso al trote, con las patas en diagonal moviéndose en fase (onda sinusoidal por articulación) y sincronizada con la velocidad. Al detenerse, se echa ligeramente hacia adelante e "inspecciona".
- **Cono de visión de la cámara**, semitransparente, que muestra qué parte del arbusto ve.
- **Interruptor "mástil de producción"**: añade un mástil de 1,2–1,5 m con una cámara arriba. El cono de visión cambia y alcanza la parte alta del arbusto. Sirve para mostrar por qué el D1 a ras de suelo solo ve la base.
- **Comportamiento:**
  1. Recorre los pasillos cama por cama, en serpentina.
  2. Prioriza las camas con mayor riesgo ambiental cuando la alternativa lo indica.
  3. Se detiene frente a una planta con sospecha y genera la alerta.
  4. Vuelve a la base cuando la batería simulada baja de un umbral. La batería dura 1–2 h y es configurable.
- **Ubicación:** cada cama tiene un marcador ArUco virtual en la cabecera. El robot "lo lee" al entrar al pasillo y el HUD muestra "Bloque 1 · Cama 7".

## 6. Modelo del brote y del clima

**Clima:**

- Fuente: Open-Meteo, sin clave.
  - Pronóstico: `https://api.open-meteo.com/v1/forecast`
  - Histórico: `https://archive-api.open-meteo.com/v1/archive`
- Variables horarias: `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `precipitation`.
- Coordenadas por defecto: Sabana de Bogotá, por ejemplo Chía (lat 4.86, lon −74.06). Que sean configurables.
- **Guarda en caché las respuestas en disco**, porque la demo puede no tener internet.
- **Hoja mojada:** como no tenemos sensor, se aproxima como "hora con humedad relativa ≥ 90 % o con precipitación > 0". Es un supuesto y así debe documentarse.

**Riesgo por enfermedad**, como funciones configurables en `config/risk.yaml`:

- **Antracnosis:** el modelo validado en arándano es Miles et al. 2013 (*Plant Pathology* 62:1238). Implementa la forma funcional que publican si la encuentras. Si no, usa una regla documentada (20–30 °C y 12 o más horas de mojadura) **marcada como aproximación**.
- **Botrytis:** Bulger, Ellis y Madden 1987 (*Phytopathology* 77:1225), modelo de fresa usado como proxy. Misma regla: forma publicada si existe; si no, regla aproximada (15–25 °C, humedad relativa > 90 %, 8 o más horas de mojadura).
- **Roya:** regla empírica (19–25 °C con mojadura prolongada; ciclo de 10–14 días).
- **No inventes coeficientes.** Si un parámetro no tiene fuente, ponlo en el YAML con un comentario `# SUPUESTO`.

**Propagación** (en una grilla de plantas):

- Al inicio se siembran 1 a 3 focos según la semilla.
- Cada día, una planta infectada contagia a sus vecinas (en la misma cama, más fuerte; en la cama de al lado, más débil) con una probabilidad que crece con el riesgo del día.
- **Periodo latente:** días sin síntomas antes de que se vean. Ponle 5–10 días como supuesto, configurable.
- Después del tratamiento, la planta deja de contagiar.

## 7. Modelo de detección (debe reflejar errores reales)

- Clases visuales: sana, oídio, alternaria, Heliothis (dataset DrBerry).
- La probabilidad de detectar y las falsas alarmas salen de una **matriz de confusión en `config/detector.yaml`**. Hoy tiene valores de ejemplo marcados `# PROVISIONAL`. El equipo la va a reemplazar por la matriz medida con el modelo real.
- El robot solo puede detectar plantas **con síntomas** y que estén dentro de su cono de visión. Con la cámara baja ve menos la parte alta del arbusto, así que su sensibilidad baja según la altura (factor configurable).
- La hoja mojada sube las falsas alarmas (factor configurable). Por eso el robot va antes de la aspersión.
- Umbral de decisión: favorece la sensibilidad. Una falsa alarma cuesta ~30 USD y una semana sin detectar ~2.160 USD/ha (supuestos del análisis de finanzas).
- **Confirmación humana simulada:** el operario confirma o descarta con un retraso configurable. Su propia tasa de error también es configurable.

## 8. Las 6 alternativas (mismo brote, misma semilla)

| Código | Alternativa | Cómo detecta en la simulación |
|---|---|---|
| A | D1 Ultra con mástil | Recorre cada N días, detecta por planta y no usa el riesgo ambiental |
| B | Red fija de sensores | Marca el riesgo por bloque o cama, pero no la planta; activa una revisión humana del bloque entero |
| C | Kit de cámara en la aspersora (alternativa descartada: AGRAR no asperja) | Solo detecta los días de aspersión, cada N días; la niebla baja su sensibilidad |
| D | Humanoide | Como A, pero con menos autonomía y una probabilidad de caída o detención en terreno malo |
| E | Plataforma con ruedas y torso alto | Ve todo el arbusto; si el terreno es barro, avanza más lento o se atasca |
| F (principal) | Red fija + D1 | El riesgo prioriza qué camas revisa el robot primero |
| Referencia | Solo monitoreo humano | Revisión cada N días, con baja sensibilidad a síntomas pequeños y al envés |

- Cada alternativa es un archivo YAML. No pongas ramas `if` por alternativa en el motor: deben salir del mismo código con distinta configuración.
- **Modo comparación:** 4 escenas en cuadrícula de 2 × 2 corriendo en paralelo con la misma semilla. Esta es la vista que se graba para el video.

## 9. Evidencia (modo sin pantalla)

- `python batch.py --runs 200 --alternatives all --weather historical --year 2025`
- Por corrida guarda: alternativa, semilla, día del primer foco, día de la primera detección correcta, camas y plantas infectadas en ese día, falsas alarmas y casos no detectados al final.
- Exporta `results/runs.csv` y `results/summary.csv`, con mediana y percentiles 10/90 por alternativa.
- Genera 2 gráficas en PNG (matplotlib) para las diapositivas:
  - Distribución del día de detección por alternativa.
  - Camas infectadas al detectar, por alternativa.
- También corre los modelos de riesgo sobre un año histórico de la Sabana y reporta cuántos días de riesgo alto hubo por mes.

## 10. Modo grabación

- Pantalla limpia: sin controles, con el rótulo "SIMULACIÓN" y el título de la alternativa.
- Cámara cinematográfica y velocidad fija.
- Resolución de 1920 × 1080.
- Debe poder grabarse con QuickTime (Cmd+Shift+5). Si es sencillo, añade exportación de cuadros con CCapture o similar.

## 11. Orden de trabajo y criterios de aceptación

1. **Núcleo en Python** con propagación, clima en caché y estado en JSON. *Acepta si:* con la misma semilla el resultado se repite y una prueba unitaria lo verifica.
2. **Escena básica:** suelo, 10 camas, 400 arbustos con colores por estado y actualización en vivo desde el WebSocket. *Acepta si:* corre a 60 fps en una MacBook.
3. **Robot:** modelo, animación del paso, recorrido en serpentina, cono de visión, parada y alerta. *Acepta si:* recorre un bloque completo sin atravesar camas.
4. **Las 6 alternativas y el modo sin pantalla** con los CSV y las gráficas. *Acepta si:* `batch.py` termina y produce los archivos.
5. **Lo bonito:** neblina, lluvia, mapa de calor, modo dios, cámaras y HUD pulido.
6. **Vista de comparación 2 × 2 y modo grabación.**

Si el tiempo aprieta, recorta en este orden: macrotúnel, lluvia, neblina, cámara cinematográfica. **Nunca recortes el paso 4.**

## 12. Reglas

- Ningún número se inventa en silencio. Cada parámetro sin fuente lleva `# SUPUESTO` o `# PROVISIONAL` en el YAML y aparece en el README.
- Código limpio, tipado (TypeScript y type hints de Python), con README de cómo correr todo en macOS.
- Prioriza que funcione de punta a punta antes de cualquier detalle visual.
- Si algo bloquea (falta el URDF, el SDK, un dato del mentor), usa el valor por defecto de este documento, márcalo y sigue. No te detengas a preguntar salvo que sea imposible avanzar.

## 12b. Cambios por la entrevista con el mentor (prevalecen sobre lo anterior)
- (Vigente, también para el apartado 1) El robot **no** va ligado al aspersor y AGRAR no asperja. Patrulla según el riesgo, sobre todo **de noche o al amanecer**, cuando se condensa la humedad.
- En cada detección el robot registra **temperatura y humedad del punto exacto** (sensor a bordo) junto con la ubicación. Muéstralo en el HUD y en el registro.
- Enfermedad principal en la escena: **Botrytis**. Le siguen **alternaria por gutación** (gotas en la hoja que aparecen de noche: muéstralas como brillo y gotas) y el **oídio**. El daño por trips es una clase opcional.
- La "red fija" son los **PLC de AGRAR por bloque**. Muestra un gabinete por bloque.
- No hay red en los bloques: el robot guarda los datos y **sincroniza al volver a la base**. Muestra un indicador de "pendiente de sincronizar".

## 13. Datos abiertos que el equipo completará después

- Matriz de confusión real del modelo, entrenado con DrBerry.
- Respuestas del mentor: suelo o maceta, macrotúnel, ancho del pasillo, altura del arbusto, frecuencia de aspersión, periodo latente y cuántas falsas alarmas tolerarían.
- URDF del D1 (si el SDK lo trae).
- Número de camas y plantas que queremos mostrar.
