# Filtros de sensor del panel (`panel_demo.py`)

Selector de vista en el panel (y `GET /stream.mjpg?vista=normal|termica|ndvi|sensores|comparar`; `GET/POST /api/vista` para la vista por defecto, cuerpo `{"vista":"termica"}`).
**Son solo visualización**: la clasificación (filtro de hoja, auto-recorte, corrección de color, decisión estable de 8 cuadros, envío a sim-core) usa siempre el cuadro RGB normal. El visor `/hoja` no cambia. El recuadro de zona, el recorte de hoja y la etiqueta de clase se dibujan encima en todas las vistas.

| Vista | ¿Qué es real? | ¿Qué es simulado? | Sensor real que la reemplazaría |
|---|---|---|---|
| Normal | Cámara RGB del D1 (o `--video` en pruebas) | nada | — (ya es la cámara real) |
| Térmica (simulada) | Imagen RGB de fondo; T y HR si vienen de sim-core | **Toda la temperatura por píxel**: no se mide calor | Cámara térmica MLX90640 / FLIR Lepton, ~250 USD (cifra ya usada en el proyecto) |
| Índice de vegetación (simulado NDVI) | Los píxeles RGB | **El índice**: ExG no es NDVI (no hay banda NIR) | Cámara multiespectral/NIR (NDVI real = (NIR−Rojo)/(NIR+Rojo)) o cámara RGB+NIR modificada |
| Sensores | Estado de la cámara/fps/pausa del panel | T, HR, batería y riesgo vienen de **sim-core (simulados)**; sin `--sim-url` son valores por defecto rotulados | Sensor T/HR del invernadero (p. ej. SHT31/DHT22), lectura de batería del D1, sensor de hoja mojada |
| Comparar | — | Cuadrícula 2×2 con las cuatro vistas (cada una con su rótulo) | — |

## Cómo se calcula

**Punto de rocío (Magnus):** `γ = ln(HR/100) + 17,62·T/(243,12+T)`, `Td = 243,12·γ/(17,62−γ)`.

**Térmica simulada.** Se calcula a 480 px de ancho y se amplía.
1. `ExG = (2G − R − B)/(R+G+B)` (verdor) y luminancia `L`.
2. `veg = clip((ExG−0,02)/0,25, 0, 1)`; `vegb` = `veg` desenfocado (follaje denso en la zona).
3. `Δ = 1,6·(L−0,5) − 1,5·veg − 1,2·hrf·vegb`, con `hrf = clip((HR−60)/40, 0, 1)`; limitado a ±4 °C. Más verde y más HR en follaje denso ⇒ más frío (transpiración/condensación); el fondo sigue la luminancia. Es un modelo heurístico, no física medida.
4. `T_píxel = T_aire + Δ`; escala fija T_aire ± 4 °C con `COLORMAP_INFERNO` y barra con °C. T_aire viene de sim-core (`/api/robot`, `/api/dashboard/resumen`) o, sin sim-core, de `--t-aire` (18 °C por defecto).
5. Píxeles con `T_píxel ≤ Td` se pintan en cian: "posible hoja mojada" (con T y HR por defecto casi nunca aparecen; con HR alta sí).

**NDVI simulado.** `ExG` normalizado a 0–1 (`(ExG+0,05)/0,55`) con colormap rojo→amarillo→verde y leyenda. Rotulado "aproximación desde RGB". Sirve para distinguir follaje de suelo/fondo; **no** detecta estrés fisiológico como un NDVI real.

**Sensores.** Panel superpuesto con T, HR, punto de rocío, horas de hoja mojada, riesgo, batería y estado del robot.
- Horas de hoja mojada: si sim-core entrega `horas_hoja_mojada` se usa; si no, se integra en vivo el tiempo con `T − Td ≤ 1,5 °C` desde que arrancó el panel (marcado con `*`).
- sim-core: el panel lee `/api/robot`, `/api/dashboard/resumen` y `/api/dashboard/riesgo` cada 2 s buscando claves por nombre (`temperatura_actual`, `humedad_actual`, `bateria`, `riesgo`, …; HR y batería en 0–1 se pasan a %). **No se verificó contra un sim-core real**, solo contra un servidor de prueba con esas claves; si los nombres difieren, ajustar las listas en `hilo_sensores`. Si sim-core no responde, se muestran los valores por defecto y el panel lo dice.

## Rendimiento
Filtros a 480 px de ancho, salida 960 px, MJPEG a 15 fps como máximo; medido ~14 fps en las 5 vistas en un Mac M4 con el modelo clasificando a la vez.

## Probar sin robot
```
cd datos && HF_HUB_OFFLINE=1 .venv/bin/python -I robot/panel_demo.py --robot-ip 10.90.251.84 --port 8093 \
  --modelo resultados/ml/modelo_camara --video resultados/ml/capturas_pantalla/completas [--hr 90 --t-aire 18]
```
`--video` acepta un video, una imagen o una carpeta de imágenes (en bucle). Las capturas de las cinco vistas están en `robot/capturas_filtros/` (tomadas con `--hr 88` y sin sim-core; las imágenes de `completas/` son fotos de una pantalla, por eso hay poco verde).
