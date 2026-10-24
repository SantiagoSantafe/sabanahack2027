# Protocolo entre las piezas de la demo (contrato v1)

Este archivo es el contrato entre tres programas que se escriben en paralelo. Si una pieza necesita cambiarlo, se cambia aquí primero.

```
 Mac (Apple Silicon)                                   PC Windows → VM Ubuntu 22.04 (x86_64, red en modo PUENTE)
 ┌──────────────────────────────────────┐              ┌──────────────────────────────┐
 │ berry-sim  web (Vite :5173)          │              │ robot_d1/d1_bridge.py        │
 │   teclado WASD ─ws─► sim-core :8000  │◄────ws───────│   cliente WS → Mac:8000      │──SDK (UDP)──► D1 EDU
 │ sim-core (FastAPI, --host 0.0.0.0)   │  /ws/robot   │   lazo de control a 20 Hz    │   192.168.234.1 (Wi-Fi AP)
 │   POST /api/detection ◄── detector   │              │   mc_sdk_zsl_1_py.HighLevel  │   192.168.168.168 (cable)
 │ datos/demo/detector_vivo.py          │◄──RTSP──────────────────────────────────────────── cámara frontal del D1
 └──────────────────────────────────────┘   rtsp://<ip_d1>:8554/test
```

- El **puente se conecta al Mac** (cliente WebSocket) y no al revés: así el Mac no necesita conocer la IP de la VM.
- El SDK **exige que la VM esté en modo puente** (bridged): el robot devuelve UDP a `local_ip:local_port`; con NAT no llega.
- Seguridad: el robot **solo se mueve con comandos frescos**. Detenerse = enviar `move(0,0,0)` de forma continua (si pasan 3 s sin comandos, el D1 se acuesta solo).

## 1. Puente → servidor de la simulación (`ws://<IP_MAC>:8000/ws/robot`)

Todos los mensajes son JSON con campo `type`.

| type | Cuándo | Campos |
|---|---|---|
| `hello` | al conectar | `robot` ("D1 EDU"), `mock` (bool: true si es el robot simulado del puente), `version` (1), `limits` {`vx_max`, `vy_max`, `wz_max`} |
| `telemetry` | 10 Hz | `t` (unix s), `x`, `y`, `yaw` (odometría del D1, m y rad, marco propio del robot; `null` si el SDK no la da), `vx`, `vy`, `wz` (comando aplicado), `state` ("standing", "moving", "lying", "passive", "estop", "detection_hold", "sdk_error"), `sdk_ok` (bool, checkConnection), `battery` (0–100 o `null`), `last_cmd_age_ms` |
| `event` | puntual | `name` ("estop", "resume", "detection_hold_start", "detection_hold_end", "watchdog_zero", "sdk_error", "stood_up", "lay_down", "battery_low", "battery_critical"), `detail` (texto) |

## 2. Servidor de la simulación → puente

| type | Cuándo | Campos |
|---|---|---|
| `teleop` | 20 Hz mientras el modo Manual esté activo y el robot real conectado (también ceros) | `fwd` (−1..1), `strafe` (−1..1, opcional, 0 si no se usa), `turn` (−1..1, positivo = izquierda), `fast` (bool), `seq` (entero creciente) |
| `action` | botones | `name`: "stand", "lie", "estop", "resume" |
| `detection_stop` | al llegar una detección con sospecha | `hold_s` (segundos quieto, por defecto 4), `label`, `conf` |

Reglas del puente:
- Un `teleop` vale **0,3 s**. Si no llega otro, la velocidad objetivo es cero (y se sigue mandando `move(0,0,0)`).
- `fwd/strafe/turn` se escalan a los límites configurados del puente (por defecto, para interiores: `vx` 0,4 m/s, 0,8 con `fast`; `vy` 0,25 m/s; `wz` 0,6 rad/s) y se recortan a los rangos válidos del SDK (|vx| 0,05–3; |vy| 0,1–1,0; |wz| 0,02–3,0; por debajo del mínimo → 0).
- `estop` bloquea el movimiento (velocidad cero continua, **no** `passive`, que deja caer al robot) hasta `resume`.
- `detection_stop` mantiene cero durante `hold_s` e ignora `teleop` en ese tiempo.
- Si se cae el WebSocket: velocidad cero continua y reconexión automática. El robot queda de pie.

## 3. Detector → servidor de la simulación (`POST http://localhost:8000/api/detection`)

```json
{
  "ts": 1792780000.5,
  "label": "oidio",            // clase más probable: sana | oidio | alternaria | heliothis
  "conf": 0.93,                // probabilidad de esa clase
  "p_enfermedad": 0.96,        // 1 - p(sana)
  "sospecha": true,            // p_enfermedad >= umbral
  "umbral": 0.737,
  "cama": 2,                   // id del marcador ArUco visto en el cuadro, o null
  "truth_label": "oidio",      // etiqueta real si el visor del jurado la conoce, o null
  "frame": "datos/resultados/ml/capturas_d1/f_000123.jpg",
  "source": "rtsp"             // rtsp | camera | dryrun
}
```

Respuesta: `{"ok": true, "forwarded_to_robot": bool, "incident_id": ...}`. El servidor, si `sospecha`, manda `detection_stop` al puente, crea la incidencia en la simulación en la posición actual del robot, con temperatura y humedad **simuladas** (rotuladas así: en la demo no hay sensor físico), y la muestra en el registro.

`GET http://localhost:8000/api/robot` devuelve el estado del enlace con el robot real (conectado, mock, última telemetría, latencia).

## 4. Panel de cámara → servidor de la simulación (`POST /api/panel`, opcional)

`panel_demo.py --sim-url http://localhost:8010` manda cada 0,5 s `{cam_ok, fps, frame_age_s, clase, confianza, p_enfermedad, sospecha, estable, p_hoja}` y, además, las detecciones del §3 (predicción estable con sospecha; como mucho 1/s y sin repetir etiqueta en 6 s). `cam_ok` = hay cuadros de la cámara de hace menos de 2 s. El servidor lo reparte a la web (`real_robot.safety.panel`) y lo usa en la barrera de video.

## 5. Barreras de seguridad (integración con el gemelo)

Se deciden en sim-core (`safety.py` + `robot_link.py`) y, las de batería y velocidad, también en el puente. Detalle y pruebas en `datos/robot/GEMELO_DIGITAL.md`.

- `GET/POST /api/safety`: estado y ajustes en caliente (`speed_cap_mps`, `geofence`, `bed_margin_m`, `video_guard`: auto|on|off...).
- Puente: `--speed-cap M` (recorta `vx_max`, `vx_fast`, `vy_max`; el `hello` ya informa los límites recortados), `--mock-battery N`, `control.battery_stand_min` (25) y `control.battery_lie_below` (15) en el YAML.
