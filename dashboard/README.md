# Dashboard de incidencias en vivo (AgiBot D1)

React + TypeScript + Tailwind + recharts. Lee el feed de solo lectura de `sim-core` (no abre `/ws`, así que no crea sesiones de simulación).

## Arranque

1. Backend (carpeta `berry-sim/sim-core`):
   ```bash
   .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8010
   ```
   El feed usa la sesión de simulación más reciente: abre el visor web (http://localhost:5173) o arranca con una sesión sin navegador:
   ```bash
   DASHBOARD_AUTOSESSION=1 DASHBOARD_SPEED=5 .venv/bin/uvicorn server:app --port 8010
   ```
   Las detecciones del robot real (`POST /api/detection`) aparecen con fuente "Cámara D1" (T/HR simuladas).
2. Frontend (esta carpeta):
   ```bash
   npm install
   npm run dev      # http://localhost:5180
   npm run build
   ```

## Variables (`.env`, ver `.env.example`)

- `VITE_API_URL`: URL del sim-core (por defecto `http://localhost:8010`).
- `VITE_FORCE_MOCK=true`: fuerza los datos de ejemplo.

## Modo mock

Si el backend no responde, se usa `src/data/mock.json` (40 registros) y se muestra el badge "Datos de ejemplo"; se reintenta la conexión cada 5-8 s. Con backend: badge "En vivo".

## Endpoints (sim-core)

- `GET /api/dashboard/incidencias?limit=200`: incidencias normalizadas (más recientes primero).
- `GET /api/dashboard/resumen`: KPIs (promedios T/HR, % plantas saludables, activas, por clase).
- `GET /api/dashboard/stream`: SSE (`event: update`, ~1 Hz) con `nuevas`, `resumen` y `reset`.

Campos: `id, ts, dia, hora, ubicacion ("N1 C2 P50"), deteccion, clase (sana|oidio|alternaria|heliothis), temperatura_c, humedad_pct, estado (Saludable|Alerta), fuente (simulacion|camara_d1), confianza`.
Pruebas: `cd sim-core && .venv/bin/python -m pytest tests/test_dashboard.py`.

## Prevención y acción (nuevo)

Pensado para **detectar a tiempo, prevenir y actuar**. Todo es de solo lectura sobre la simulación, salvo el ciclo de acción (SQLite).

- **Qué atender hoy** (`/api/dashboard/focos`): agrupa las detecciones en *focos* (misma nave+cama, misma familia hongo/plaga, plantas a ≤ 5, ≤ 72 h entre detecciones). Prioridad = gravedad × plantas × riesgo de la cama × antigüedad; el puntaje (0-100) y los pesos están en `sim-core/config/dashboard.yaml`. El número grande de la banda es ahora "focos abiertos" (las detecciones son el dato secundario).
- **Ciclo de acción**: Nuevo → Asignado (a quién) → Verificado en campo (confirmado / falsa alarma) → Tratado (qué se hizo) → Cerrado; notas y marca de tiempo en cada paso. `POST /api/dashboard/focos/{id}/accion` con `{"accion": "asignar|verificar|tratar|cerrar|nota", "responsable", "resultado", "detalle", "nota"}`; transición inválida = 409. `GET /api/dashboard/focos/{id}/historial`. Se guarda en `sim-core/data/dashboard_acciones.sqlite3` (variable `DASHBOARD_DB` para cambiarlo) y sobrevive a reinicios. Reloj de atención: ámbar ≥ 12 h, rojo ≥ 24 h (configurable, horas del escenario simulado). Cada verificación cuenta como una etiqueta para mejorar el modelo (KPI "falsas alarmas %").
- **Riesgo próximo** (`/api/dashboard/riesgo`): índice por cama y enfermedad (Botrytis, antracnosis, roya) para 0-24, 24-48 y 48-72 h, con los umbrales de `config/risk.yaml`, horas de hoja mojada/HR alta y avisos preventivos por regla. **ESTIMADO**: el motor solo calcula el día en curso; lo futuro se proyecta con el clima horario del escenario y las reglas de microclima del túnel, sin azar de ventilación. Las recomendaciones son **orientativas**; validar con el agrónomo.
- **Cobertura** (`/api/dashboard/cobertura`): última inspección del robot por cama y "puntos ciegos" (> 48 h, configurable). El motor registra la última captura por cama en `bed_last_t`.
- **Avisos** (`/api/dashboard/avisos`): texto corto por foco/prevención para pantalla de oficina o mensajería; el botón "Copiar aviso" lo copia. No hay integración real con WhatsApp.
- **Foto**: si la detección viene de la cámara del D1 y trae `frame`, el panel de detalle la muestra desde `GET /api/dashboard/captura?f=<archivo>`, solo lectura y limitada a `datos/resultados/ml/capturas_d1/` (`DASHBOARD_CAPTURAS_DIR` para cambiar la carpeta); sin foto se muestra "Sin foto (simulación)".
- En modo de datos de ejemplo se usa `src/data/mock_prevencion.json` y las acciones quedan desactivadas.

Pruebas: `cd sim-core && .venv/bin/python -m pytest tests/test_dashboard.py tests/test_dashboard_focos.py`.

## Vista cenital (nuevo)

Tarjeta "12 · Vista cenital" en la sección Mapa: planta del bloque a escala (naves, camas, plantas, pasillos, camino central, norte y escala) con capas **Temperatura**, **Humedad relativa**, **Riesgo** o ninguna, y encima las detecciones (círculo con radio según la confianza: 50 % a 95 % = 4 a 14 px; rojo oídio/alternaria, ámbar Heliothis, verde hoja sana; borde grueso = foco sin cerrar). Filtros por tiempo (24 h / 7 días / todo), clase y fuente (simulación / robot real D1). Zoom con rueda, pellizco o botones +/−; "Girar 90°" cambia la orientación (por defecto el eje largo del bloque va a lo ancho de la pantalla). Clic en un círculo abre el detalle de la incidencia o del foco.

- `GET /api/dashboard/mapa?horas=24&celda=1`: geometría en metros (x = ancho, +y = norte, mismas coordenadas del motor), rejillas `temperatura` y `humedad` (valores por fila con y creciente, `medido` = celdas con una lectura), lecturas puntuales, detecciones con (x, y) y estado de su foco, riesgo por cama y robot con su rastro reciente.
- **T y HR están interpoladas**, no medidas en toda la superficie: kernel gaussiano (σ = 6 m) suavizado hacia la media, a partir de las sondas del robot, las incidencias (últimas `horas`) y los 12 sensores de bloque del clima del simulador. Todo es simulado. Con una sola lectura el campo es constante.
- Modo ejemplo: `src/data/mock_mapa.json`.
- Pruebas: `cd sim-core && .venv/bin/python -m pytest tests/test_dashboard_mapa.py`.
