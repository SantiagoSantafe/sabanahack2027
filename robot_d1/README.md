# Manejar el D1 EDU con WASD (VM Ubuntu + simulación en el Mac)

Puente y teleoperación del cuadrúpedo **AgiBot D1 EDU** para la demo de Berry Good Idea.
El contrato entre piezas está en [`PROTOCOLO.md`](PROTOCOLO.md) (v1).

```
Mac (sim-core :8000, WASD en el navegador) ◄──WebSocket── VM Ubuntu: d1_bridge.py ──SDK (UDP)──► D1 EDU
                                                            (o d1_teleop.py sola)
```

| Archivo | Para qué |
|---|---|
| `d1_teleop.py` | Manejar el robot con el teclado de la VM, sin simulación (respaldo). |
| `d1_bridge.py` | Puente: la simulación del Mac manda, el robot obedece y devuelve telemetría. |
| `tools/fake_sim_server.py` | Simulación falsa para probar el puente sin la de verdad. |
| `scripts/setup_vm_ubuntu.sh` | Prepara la VM (Python 3.10, venv, SDK, prueba de import). |
| `scripts/check_red.sh` | Revisa la red antes de manejar. |
| `d1/` | Código común: `safety.py` (límites), `sdk.py` (robot real y simulado), `controller.py` (lazo). |
| `config.example.yaml` | Valores por defecto (cópialo a `config.yaml`). |

Reglas que el código cumple siempre: el robot solo se mueve con comandos frescos (un teleop vale
0,3 s); detenerse es mandar `move(0,0,0)` sin parar a 20 Hz; `passive()` **no** se usa como parada
(deja caer al robot).

---

## 1. Red: la VM en modo PUENTE

El SDK manda UDP al robot y **el robot contesta a `IP_de_la_VM:43988`**. Con la VM en NAT esa
respuesta nunca llega y el robot se acuesta a los 3 s. La VM tiene que estar en **modo puente**
(bridged) y tener su propia IP en la red del robot.

### Configurar el puente en Windows

- **VirtualBox**: VM apagada → Configuración → Red → Adaptador 1 → *Conectado a: Adaptador puente* →
  *Nombre:* la tarjeta **Wi-Fi** del PC (o la Ethernet si vas por cable). Funciona sobre Wi-Fi.
- **VMware Workstation/Player**: VM → Settings → Network Adapter → *Bridged* y marca *Replicate
  physical network connection state*. En *Edit → Virtual Network Editor* (como admin), pon VMnet0
  en *Bridged to:* la tarjeta Wi-Fi concreta (no "Automatic"). Funciona sobre Wi-Fi.
- **Hyper-V**: Administrador de conmutadores virtuales → *Externo* sobre la tarjeta de red.
  **Aviso:** el puente de Hyper-V sobre **Wi-Fi suele fallar** (DHCP, MAC compartida). El *Default
  Switch* es NAT y no sirve. Si solo tienes Wi-Fi, usa VirtualBox o VMware.
- **WSL no sirve** (la guía del SDK lo dice explícitamente, sección 3.2).

Comprueba en la VM con `ip -4 addr`: debe tener una IP `192.168.234.x` (Wi-Fi) o `192.168.168.x`
(cable). Si ves `10.0.2.15` sigues en NAT.

### Opción A (recomendada): todo por el Wi-Fi del D1

1. El D1 crea su propio Wi-Fi (SSID y clave en la etiqueta del costado o de abajo; tipo `XG2WIFI_…`).
   Su IP es **192.168.234.1** y reparte IPs por DHCP (no pongas IP fija).
2. Conecta el **PC con Windows** a ese Wi-Fi. La VM (puente sobre la tarjeta Wi-Fi) recibe su propia
   IP `192.168.234.x`.
3. Conecta también el **Mac** a ese Wi-Fi (recibe `192.168.234.y`). Así VM, Mac y robot quedan en la
   misma red, y el detector del Mac puede leer `rtsp://192.168.234.1:8554/test`.
   El Mac pierde internet mientras tanto. (Los equipos de la demo no usan VPN; si alguno la tuviera,
   el tráfico al robot se iría por el túnel: `check_red.sh` lo detecta.)
4. **Una vez, en el robot**: decirle a qué IP debe contestar (guía 3.7.1). Desde la VM:
   ```bash
   ip route get 192.168.234.1          # mira "src 192.168.234.x": esa es la IP de la VM
   ssh firefly@192.168.234.1           # la contraseña por defecto está en la guía, sección 3.4
   sudo vim /opt/export/config/sdk_config.yaml
   #   target_ip: "192.168.234.x"      # <- la IP de la VM
   #   target_port: 43988              # no cambiar
   sudo reboot
   ```
   Si mañana la VM recibe otra IP por DHCP, hay que repetir este paso. Para comprobarlo:
   `CHECK_SSH=1 bash scripts/check_red.sh` compara `target_ip` con la IP actual de la VM.
   En modo Wi-Fi, `SDK_CLIENT_IP` (en `start_motion_control.sh`) y `ROBOT_NET_INTERFACES` (en
   `robot-launch.service`) deben estar **sin** configurar (guía 6.1, punto 3).

### Opción B: por cable

Más estable que el Wi-Fi (la FAQ del repo lo recomienda), pero exige tocar archivos del sistema del
robot. Si algo queda mal, el programa de movimiento no arranca (luz azul parpadeando).

1. Cable del PC al puerto RJ45 del D1. El robot es **192.168.168.168** y no tiene DHCP.
2. VirtualBox: adaptador 1 en **puente** sobre la Ethernet del PC. En la VM pon IP fija, p. ej.
   `192.168.168.10/24`, sin puerta de enlace (no uses `.168`).
3. Para llegar al Mac, añade un **adaptador 2 en NAT** a la VM y deja el PC Windows también conectado
   al Wi-Fi del D1 (o a la red del Mac). El puente es cliente WebSocket, así que la salida por NAT basta.
4. En el robot (guía 3.7.2, por SSH a `192.168.234.1` o `192.168.168.168`):
   - `/opt/export/config/sdk_config.yaml` → `target_ip: "192.168.168.10"` (la IP de la VM).
   - `/opt/app_launch/start_motion_control.sh` → `export SDK_CLIENT_IP="192.168.168.168"`.
   - `/etc/systemd/system/robot-launch.service`, sección `[Service]` →
     `Environment="ROBOT_NET_INTERFACES=eth0"`. **Ojo:** la guía se contradice aquí (un recuadro dice
     `wlan0` para cable); las secciones 5.5 y 6.2 indican que el puerto Ethernet es `eth0`.
   - `sudo reboot`.
5. Para volver a Wi-Fi, deshaz los dos últimos cambios (guía 6.1) y reinicia.
6. Corre todo con `--robot-ip 192.168.168.168`.

---

## 2. Tomar el control por SDK

1. **Versión del firmware** (por SSH en el robot, guía 3.5):
   `grep -oP 'motion-control_\K[^_]+' /etc/release/*[^rootfs]*.yaml`
   - Necesita control de movimiento **≥ 0.2.6** para usar el SDK.
   - Con **≥ 0.3.4** se puede pasar el control entre mando y SDK. **Con menos, el mando no funciona
     mientras el SDK controla**: la única parada sería la de nuestro programa (Espacio o Ctrl-C).
2. **Batería > 20 %**. Con luz amarilla fija (< 20 %) el robot no acepta control por SDK, y con poca
   batería puede devolver el control al mando o incluso apagarse de golpe (guía 5.2.1, FAQ del repo).
3. Al conectarse el SDK, el robot pasa a **modo SDK** (luz trasera **verde fija**; azul = mando).
4. Pasar el control a mano con el mando (guía 5.4.2), mantener pulsado:
   - mando tipo Logitech: **LT + RT + A**
   - mando con pantalla: **L2 + R2 + A**
5. Atajos útiles del mando (manual de usuario): **LB+Y** pararse, **LB+X** agacharse
   (amortiguado lento), **LB+RB** soltar/parada de emergencia (se deja caer).
6. El SDK de Python **no** trae la orden de cambio de control (`CMD_SDK_CONTROL_RIGHT` solo aparece en
   un ejemplo C++ con una librería que no está en el repo). Por eso se cambia con el mando.
7. Orden de estados (guía 3.10): el SDK exige `standUp()` en la sesión antes de `move()`. Nuestros
   programas arrancan con el robot "acostado" y esperan a que pulses **U** (o el botón *stand*).

---

## 3. Teleop solo en la VM (respaldo)

```bash
cd robot_d1
bash scripts/setup_vm_ubuntu.sh            # una vez (WITH_PYNPUT=1 para el modo pynput)
source .venv/bin/activate
bash scripts/check_red.sh                  # todo en OK antes de seguir
python d1_teleop.py --config config.yaml   # por cable: --robot-ip 192.168.168.168
```

| Tecla | Acción |
|---|---|
| **U** | pararse (espera 2 s antes de aceptar movimiento) |
| **W / S** | adelante / atrás (Shift+W = rápido) |
| **A / D** | girar izquierda / derecha |
| **Q / E** | paso lateral izquierda / derecha |
| **+ / −** | nivel de velocidad (40/60/80/100 % de los límites; arranca en 60 %) |
| **Espacio** | **parada de emergencia**: cero continuo, bloqueado hasta **R** |
| **R** | reanudar |
| **L** | acostarse (frena primero) |
| **H** | ayuda |
| **Ctrl-C / Esc** | salida segura: cero y luego acostarse |

Abajo se ve una línea de estado en vivo: estado, `vx vy wz` aplicados, origen del comando, edad del
último comando, batería, modo del robot y pose.

**Terminal vs pynput.** Una terminal no avisa cuando sueltas una tecla.
- `--keys terminal` (por defecto, sin dependencias): la 1ª pulsación cuenta 0,6 s (cubre la demora de
  autorrepetición) y luego cada repetición 0,15 s. Al soltar una tecla mantenida, el robot frena en
  ≤ 0,15 s; un toque corto lo mueve ~0,6 s. **Una tecla a la vez** (la terminal solo repite la última).
- `--keys pynput`: sabe cuándo sueltas y permite W+A. Necesita sesión gráfica **X11** (en Ubuntu 22.04
  elige "Ubuntu on Xorg" al iniciar sesión) y `WITH_PYNPUT=1` en el setup. Escucha el teclado de
  **todo el escritorio**: no escribas en otra ventana mientras manejas.

Para practicar sin robot (en el Mac o la VM): `python3 d1_teleop.py --mock`.

---

## 4. Puente con la simulación

**En el Mac**: arranca sim-core escuchando en todas las interfaces (`--host 0.0.0.0`, puerto 8000) y
anota su IP en la red del robot: `ipconfig getifaddr en0`. Si macOS pregunta por conexiones entrantes
para Python, acepta.

**En la VM**:
```bash
source .venv/bin/activate
bash scripts/check_red.sh --mac 192.168.234.23
python d1_bridge.py --config config.yaml --mac-ip 192.168.234.23 --local-keys
```
- En la simulación, activa el modo Manual y pulsa *stand*. Luego WASD en el navegador.
- `--local-keys`: el teclado de la VM también manda. El teclado local gana cuando se mueve, y su
  **Espacio es un estop que la simulación no puede levantar** (solo R en la VM).
- Qué hace el puente: un `teleop` vale 0,3 s (después, cero); `estop` = cero continuo hasta `resume`;
  `detection_stop` = cero durante `hold_s` ignorando el teleop; si se cae el WebSocket, cero continuo,
  el robot queda de pie y el puente reconecta solo.
- Parar es inmediato: cuando el objetivo es cero (teclas sueltas, teleop caducado, WebSocket caído,
  detección, acostarse) se manda `move(0,0,0)` en el siguiente tick, sin rampa, igual que el estop.
  La rampa solo se usa al acelerar y entre velocidades distintas de cero.
- Rearmar no arranca: tras **Reanudar**, tras **pararse** y tras **reconectar** el WebSocket, si las
  teclas siguen apretadas el robot no se mueve hasta soltarlas y volver a pulsar.
- Manda `hello` al conectar, `telemetry` a 10 Hz y `event` puntuales (contrato v1).

**Probar sin la simulación de verdad** (en el Mac, sin robot):
```bash
python3 tools/fake_sim_server.py --port 8000              # WASD en esta terminal, U/L/Espacio/R/P
python3 d1_bridge.py --mock --mac-ip 127.0.0.1            # en otra terminal
python3 tools/fake_sim_server.py --mode pattern           # o un patrón automático
```
Con el robot real, corre `fake_sim_server.py` en el Mac y `d1_bridge.py --mac-ip <IP_MAC>` en la VM.

---

## 5. Lista de seguridad (antes de cada prueba)

- [ ] Zona despejada: más de 1 m libre alrededor del robot, nadie en su camino, nada colgando.
- [ ] Alguien con el **mando en la mano** y sabiendo **LB+RB** (parada) y **LT+RT+A** (retomar el
      control). Recuerda: con firmware < 0.3.4 el mando no funciona durante el control por SDK.
- [ ] Batería por encima de ~40 % (bajo 20 % no hay SDK y puede apagarse de golpe).
- [ ] Velocidades bajas: los límites por defecto son de interiores (0,4 m/s; 0,8 con rápido;
      0,25 lateral; 0,6 rad/s). No los subas en la demo.
- [ ] Prueba primero con `--mock` y luego con el robot real a nivel de velocidad bajo (`−`).
- [ ] Sabes dónde está el **Espacio** (estop) y que **Ctrl-C** lo acuesta.
- [ ] Lo teleoperado se dice en voz alta en la demo.

---

## 6. Problemas comunes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Se para y **se acuesta a los 3 s** | No le llegan comandos (watchdog de 3 s, FAQ 6.9) | VM en NAT, `target_ip` del robot ≠ IP de la VM, firewall, Wi-Fi débil. Corre `check_red.sh`. |
| `connect time out` / `error async receive from` al arrancar | El robot no contesta a esta IP | `target_ip` en `sdk_config.yaml` y reinicio del robot (guía 6.1). En Wi-Fi, `SDK_CLIENT_IP` comentado. |
| IP local `10.0.2.15` | VM en NAT | Adaptador puente (sección 1). |
| La IP local detectada es la equivocada | Varias interfaces | `--local-ip 192.168.234.x`. Debe coincidir con `target_ip` del robot. |
| UDP bloqueado | `ufw` activo en la VM | `sudo ufw allow 43988/udp`. |
| `ModuleNotFoundError: mc_sdk_zsl_1_py` | Python ≠ 3.10 o ruta del SDK | Usa `.venv` (3.10) y `--sdk-path` (guía 6.4). Diagnóstico: `python -m d1.sdk --sdk-path ~/agibot_D1_Edu-Ultra`. |
| `sdk_error` con `0x3007` | Cambio de estado rechazado | Pulsa U (pararse) antes de mover; no se puede parar/acostar caminando. |
| El mando hace "flexiones" al pararse | `SDK_CLIENT_IP` apunta a una IP que no existe (FAQ 6.14) | Revierte la config de cable. |
| Luz azul parpadeando y no arranca | `ROBOT_NET_INTERFACES` mal puesto (guía 6.2) | Revierte el cambio en `robot-launch.service`. |
| `[WS --]` y "sin conexión" | sim-core no escucha en `0.0.0.0`, firewall del Mac, IP equivocada | `check_red.sh --mac <IP>`; `curl http://<IP_MAC>:8000/api/robot`. |
| `[guardia] el lazo de control no late` | El lazo se congeló (llamada bloqueante) | El hilo vigilante manda ceros; revisa la salida y reinicia el programa. |

---

## 7. Plan B

- **SDK a bordo del robot** (guía 5.6): copiar el SDK al robot y usar `local_ip = dog_ip =
  192.168.234.1`, con `target_ip: "192.168.234.1"` en `sdk_config.yaml`. El repo trae los `.so` para
  `aarch64`. **Pero** la guía (FAQ 6.20) y la FAQ del repo **no lo recomiendan**: el robot no tiene
  cómputo libre. Haría falta además Python 3.10 y `websockets` dentro del robot. Solo como último recurso.
- **Linux arm64 en el Mac** (UTM/Parallels/VMware Fusion con Ubuntu 22.04 arm64, red en puente): el
  SDK trae `lib/zsl-1/aarch64/mc_sdk_zsl_1_py.cpython-310-aarch64-linux-gnu.so` y el código elige la
  arquitectura solo (igual que el ejemplo oficial). La guía no lo menciona para Mac: **no probado**.

---

## 8. Pruebas y lo que falta verificar

```bash
python3.11 -m venv /tmp/d1venv && /tmp/d1venv/bin/pip install -i https://pypi.org/simple \
    websockets pyyaml pytest pytest-asyncio
/tmp/d1venv/bin/python -m pytest -q          # desde robot_d1/
```
Cubren `safety.py`, el núcleo de control con `MockRobot` y el puente contra un servidor WebSocket
falso: teleop vigente, caducidad a 0,3 s, estop que bloquea, `detection_stop` que sostiene, caída del
WebSocket → cero continuo y reconexión.

**NO VERIFICADO con el robot real** (marcado así en el código):
- Tipos y marcos de `getPosition()`, `getRPY()`, `getBatteryPower()` y `getCurrentCtrlmode()` (se leen
  con defensas; si fallan, la telemetría manda `null`).
- Si `standUp()`/`lieDown()` bloquean o vuelven enseguida (se asume que vuelven; si bloquean, el hilo
  vigilante cubre).
- Si la librería repite sola el último comando por UDP (el demo oficial se queda esperando `input()`
  más de 3 s sin acostarse, lo que lo sugiere). Por eso mandamos ceros explícitos y hay hilo vigilante.
- El tiempo de asentado tras `standUp()` (2 s) y la detección de "se acostó solo" por el modo 0.
