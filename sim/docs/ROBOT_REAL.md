# Robot real (D1 EDU) en Berry Sim

La simulación puede conducir el AgiBot D1 EDU de verdad. En Manual, el teclado del navegador mueve al robot de la escena y al D1 real a la vez. Cuando la cámara del D1 ve una hoja sospechosa, el robot se detiene y la simulación crea la incidencia en la cama donde está. El contrato entre las piezas es `robot_d1/PROTOCOLO.md` (v1); este documento explica cómo usarlo desde berry-sim.

```
Mac: navegador ─ws /ws─► sim-core :8000 ◄─ws /ws/robot── VM Ubuntu: d1_bridge.py ──SDK UDP──► D1 EDU
                              ▲
                              └── POST /api/detection ── detector (cámara RTSP del D1)
```

## 1. Red

- El **Mac** y el **PC con la VM** se conectan a la red Wi-Fi del D1. El robot hace de punto de acceso y está en `192.168.234.1`.
- La VM Ubuntu va en **modo puente (bridged)**, no NAT. El SDK devuelve UDP a la IP de la VM y con NAT esos paquetes no llegan.
- El **puente es el cliente**: se conecta a `ws://<IP_MAC>:8000/ws/robot`. El Mac no necesita saber la IP de la VM.
- La IP del Mac en esa red se ve con `ipconfig getifaddr en0` (o en Ajustes → Wi-Fi → Detalles).
- La primera vez, macOS pregunta si Python acepta conexiones entrantes: hay que **permitirlo**. Sin ese permiso el puente se queda en "reintentando".
- Prueba desde la VM: `curl http://<IP_MAC>:8000/api/robot` debe devolver un JSON.

## 2. Arrancar

En el Mac, desde la raíz de berry-sim:

```bash
npm run dev:api     # sim-core en 0.0.0.0:8000 (escucha en la red, no solo en localhost)
npm run dev:web     # http://localhost:5173
```

En la VM, desde `robot_d1/`:

```bash
python3.10 d1_bridge.py --mac-ip <IP_MAC>           # robot real por Wi-Fi
python3 d1_bridge.py --mac-ip <IP_MAC> --mock       # sin robot: el puente simula uno
```

El detector envía sus resultados a `POST http://<IP_MAC>:8000/api/detection` (formato en PROTOCOLO.md §3).

Al conectarse el puente aparece abajo en el visor la barra **D1 real**. En el panel del robot, pestaña Sensores, aparece el bloque **D1 real**.

## 3. Probar sin robot ni VM

`sim-core/tools/fake_bridge.py` habla el mismo contrato que el puente. Integra las órdenes como un robot cinemático con los límites del contrato, envía telemetría a 10 Hz, obedece estop, resume, stand y lie, respeta `detection_stop` y se reconecta solo.

```bash
cd sim-core
.venv/bin/python tools/fake_bridge.py                                  # ws://localhost:8000/ws/robot
.venv/bin/python tools/fake_bridge.py --no-odom                        # como un SDK sin odometría
.venv/bin/python tools/fake_bridge.py --url ws://<IP_MAC>:8000/ws/robot --verbose
```

Una detección sin cámara (en otra terminal):

```bash
curl -s -X POST http://localhost:8000/api/detection -H 'Content-Type: application/json' \
  -d '{"ts": 1792780000.5, "label": "oidio", "conf": 0.93, "p_enfermedad": 0.96, "sospecha": true,
       "umbral": 0.737, "cama": 2, "truth_label": "oidio", "frame": null, "source": "dryrun"}'
# {"ok":true,"forwarded_to_robot":true,"incident_id":1,"duplicate":false}
```

Cada 2 s el puente falso imprime lo que recibió (`teleop=… action=… detection_stop=…`) y la odometría.

## 4. En pantalla

| Dónde | Qué muestra |
|---|---|
| Barra **D1 real** (abajo, siempre visible con el robot enlazado) | "D1 real: conectado (mock\|real) · 12 ms" o "sin conexión"; estado, batería, segundos de pausa por detección y si recibe WASD. Botones **Parar D1** (rojo), **Reanudar**, **Pararse** y **Acostarse**. |
| Indicador de la barra superior | "Conduciendo el D1 real, tiempo real" mientras se conduce en Manual. |
| Panel del robot → Sensores → **D1 real** | Estado, batería, odometría, antigüedad de la última orden, **Re-centrar el gemelo**, la última detección con su incidencia y el conteo contra la verdad de terreno. |
| Aviso y Registro | "Cámara del D1: oídio 93 % · Nave 1 · Cama 2 · 18,4 °C 91 % HR (simulado)". En la escena, una etiqueta roja marca la planta durante 9 s. |
| Pestaña Datos | Las incidencias de la cámara aparecen como "(D1*)", con una nota de que la temperatura y la humedad son simuladas. |
| Vista → **Sensores de producción** | Capa de ejemplo con sonda de temperatura y humedad en el follaje, cámara térmica, cámara hacia arriba para el envés y enlace LoRaWAN/Modbus al PLC del bloque. Rotulada "Ejemplo · no montado en la demo". |

## 5. Atajos

| Tecla | Acción |
|---|---|
| `M` | Automático ↔ Manual. Solo en Manual se envían órdenes al D1. |
| `W A S D` | Conducir (adelante, girar, atrás). Con el D1 conectado mueve también el robot real. |
| `Shift` | Más rápido (el doble de la velocidad configurada en el puente). |
| `X` | **Parar el D1 real** (parada de emergencia). Funciona aunque haya un diálogo abierto. |
| `E` | Inspeccionar en Manual. |
| `Espacio` | Pausar o reanudar la simulación. |
| `?` | Ayuda (incluye la sección "Robot real"). |

## 6. Qué hace el servidor

- **Teleop a 20 Hz**, solo mientras algún visor está en Manual y el puente está conectado.
- Envía ceros si la última tecla tiene más de 0,25 s (pestaña en segundo plano o red lenta), durante una parada de emergencia y durante la pausa por detección.
- Al salir de Manual envía un último cero explícito y luego deja de enviar; el puente mantiene `move(0,0,0)` por su cuenta.
- Solo cuentan las teclas de los visores que están en Manual. Con varios visores en Manual, manda el último que pide moverse; uno sin teclas no hace tartamudear al que conduce. Si todos sueltan, cero.
- **Rearmar no arranca**: si el puente se reconecta (o, en el puente, tras Reanudar o Pararse) con una tecla todavía apretada, el D1 no se mueve hasta soltarla y volver a pulsar.
- **Botones** (`action`): estop, resume, stand y lie, desde la barra, la tecla X o `POST /api/robot/action`. El estado de parada que se muestra es el del botón durante 0,6 s y después el que reporta la telemetría.
- **La parada de emergencia es pegajosa** también en el servidor: si un puente se conecta (o reconecta) con la parada puesta, lo primero que recibe es `estop`. Solo **Reanudar** la quita.
- **Un solo puente**: si llega un segundo puente mientras el actual envía telemetría, se rechaza (código 4001) y aparece un aviso con su dirección. Antes se turnaban cada ~0,5 s y la parada podía ir al equivocado. Un puente que dejó de enviar telemetría (más de 1 s) sí se reemplaza.
- **Detección con `sospecha`**:
  - envía `detection_stop` (pausa de 4 s, la misma que la inspección simulada);
  - crea una incidencia en la cama del marcador ArUco (`cama` N = cama N del bloque, la convención de los marcadores de la simulación) o, si no hay marcador, en la cama más cercana al robot de la escena;
  - adjunta la temperatura y la humedad del microclima simulado de esa cama.
- **Una sola incidencia por hallazgo**: la misma etiqueta en la misma cama dentro de 6 s cuenta como duplicado (`duplicate: true`, sin una segunda parada).
- **Verdad de terreno**: si llega `truth_label`, se cuentan en vivo aciertos, falsas alarmas, no detectadas y sanas bien descartadas. Una "hoja" es la serie de cuadros seguidos con la misma etiqueta del visor (con menos de 6 s entre cuadros); la hoja cuenta como sospechosa si alguno de sus cuadros lo fue.
- La incidencia se crea en la simulación abierta en el navegador. Sin ningún visor abierto el robot igual se detiene, pero `incident_id` es `null`.
- `GET /api/robot` devuelve el enlace (conectado, mock, última telemetría, latencia, estop, estado, conteos y verdad de terreno) y el registro de eventos. El mismo bloque llega al visor como `real_robot` en cada mensaje de estado.

## 7. El gemelo en la escena

- En Manual, si la telemetría trae odometría, el robot de la escena **sigue la odometría del D1**.
- Se ancla a la pose de la escena al conectar el puente, al entrar en Manual y con **Re-centrar el gemelo**, que lo pone en el centro del pasillo más cercano mirando a lo largo de él. Usarlo con el D1 parado al inicio de un pasillo real.
- La odometría deriva con el tiempo; re-centrar al empezar cada pasillo.
- Si la telemetría no trae odometría (`x, y, yaw = null`), el robot de la escena avanza con el teclado como siempre, con colisiones y con los límites de velocidad que anunció el puente. Se queda quieto mientras el D1 está parado, en pausa o acostado.
- En Automático el robot de la escena sigue su recorrido simulado y no envía órdenes al D1.

## 8. Qué es simulado

- **Temperatura y humedad de las detecciones**: salen del microclima simulado de la cama. Se rotulan "simulado (en producción: sensor a bordo)". La demo no lleva sensor físico.
- **Sensores de producción**: la capa de Vista es solo un ejemplo de lo que llevaría el robot en el bloque. Nada de eso está montado.
- **El bloque, las plantas y la enfermedad** de la escena siguen siendo la simulación. La planta de la incidencia se toma de la posición del robot de la escena, no de la del D1.
- Lo real: el D1 que se mueve, su estado, batería y odometría, la cámara y el detector.

## 9. Problemas frecuentes

| Síntoma | Causa probable |
|---|---|
| "D1 real: sin conexión" y el puente reintenta | IP del Mac equivocada, firewall de macOS sin permiso, la VM en NAT o en otra red Wi-Fi, o sim-core arrancado sin `--host 0.0.0.0`. |
| "latencia n/d (relojes desfasados)" | Los relojes del Mac y de la VM no coinciden. La latencia se estima con la hora de la telemetría. Sincronizar la VM (`sudo timedatectl set-ntp true`). |
| El D1 no se mueve con WASD | No estás en Manual (`M`), está en parada de emergencia (**Reanudar**), en pausa por detección (la barra muestra los segundos) o acostado (**Pararse**; la barra lo pide en naranja). Si acabas de Pararse o Reanudar, o volvió el enlace, con la tecla apretada: suéltala y vuelve a pulsar. |
| Se detiene a ratos | La pestaña del navegador quedó en segundo plano: el navegador frena el envío y el servidor manda ceros. Es lo seguro. |
| Llega una detección pero no hay incidencia | No hay ningún navegador con la simulación abierta, o era un duplicado de la anterior. |

## 10. Límites conocidos

- La pose simulada del servidor no entra en las camas: con odometría que cruza una cama, el robot de la escena la sigue, pero la posición del servidor (la que usa la incidencia) se queda en el último punto válido del pasillo.
- El gemelo solo sigue la odometría en Manual.
- Desde el teclado no se envía desplazamiento lateral (`strafe` siempre 0).
- Si hay varios navegadores en Manual a la vez, manda el último que pide moverse; cualquiera puede parar con **X**.
