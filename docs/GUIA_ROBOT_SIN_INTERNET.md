# Guía del robot D1 sin internet

Todo lo de esta guía funciona **sin internet**: el SDK, la imagen de Ubuntu (`d1sdk`), los scripts y el modelo ya están en este Mac. Lo único que necesita conexión es abrir el documento del equipo en Claude.

Carpetas clave:
- Scripts del robot: `~/Downloads/SabanaHack/datos/robot/`
- Controlador del equipo: `~/Downloads/robot_d1 2/`
- SDK oficial: `~/Downloads/SabanaHack/datos/raw/agibot_sdk/agibot_D1_Edu-Ultra/`
- Guía del SDK (PDF): `~/Downloads/SabanaHack/datos/raw/agibot_docs/AGIQUAD_D1_Edu_Ultra_SDK_Guide_V2.0.7.pdf`

---

## 0. Lo que ya sabemos del robot (no cambiar sin acordarlo)

| Dato | Valor |
|---|---|
| Firmware de movimiento | **0.5.1**. El mando sí sirve como parada mientras controla el SDK |
| Red donde escucha el SDK | **Wi-Fi propio del robot** (`ap0`), NO el cable |
| IP del robot en esa red | `10.181.108.84` |
| IP a la que el robot contesta | **`10.181.108.1`** (el Mac debe tener esta) |
| Puertos | El SDK manda a robot:**43997**; el robot contesta a :**43988** |
| Cable (`eth0`) | Robot `192.168.168.168`, sin DHCP. Sirve para SSH y video, **no para el SDK** con la configuración actual |
| SSH | `ssh firefly@<IP_robot>` (la contraseña está en la sección 3.4 de la guía del SDK) |
| Video | `rtsp://<IP_robot>:8554/test`, 1920×1080 a 30 fps, cámara a ~25 cm del piso |

---

## 1. Seguridad (siempre, antes de pulsar U)

- [ ] **Más de 1 m despejado** alrededor del robot. Nada de mochilas, cables ni pies.
- [ ] Alguien con el **mando en la mano**:
  - **LB+RB** = parada de emergencia (se deja caer).
  - **LT+RT+A** = el mando retoma el control del SDK.
  - **LB+Y** = pararse; **LB+X** = agacharse.
- [ ] **Batería > 40 %.** Con menos del 20 % no acepta el SDK y puede apagarse de golpe.
- [ ] En el teclado: **Espacio** = PARADA (cero continuo, se levanta con R) y **Ctrl-C** = frena y se acuesta.
- [ ] La luz trasera **verde fija** indica modo SDK; **azul** indica modo mando.

---

## 2. Conectar el Mac al robot (Wi-Fi del robot)

1. Enciende el robot y espera 1–2 minutos.
2. **Abre OrbStack** (la app). Sin OrbStack corriendo, el SDK no arranca.
3. En el Mac, Wi-Fi → conéctate a la red del robot (el SSID y la clave están en la etiqueta, tipo `XG2WIFI_…`). **El Mac pierde internet**: es normal.
4. Revisa tu IP: Ajustes del Sistema → Wi-Fi → Detalles → TCP/IP.
   - Si es **`10.181.108.1`**, sigue al paso 3.
   - Si es otra, cambia a **Manual**: IP `10.181.108.1`, máscara `255.255.255.0`, router vacío. **Solo un equipo puede tener la .1**: si otro compañero la tiene, desconéctalo de esa red.
5. Prueba:
   ```bash
   ping -c 3 10.181.108.84
   ```

---

## 3. Probar el SDK SIN mover el robot

```bash
bash ~/Downloads/SabanaHack/datos/robot/abrir_teleop.sh wifi check
```

**Bien:** `conexión: True`, una batería distinta de 0 y `del robot` mayor que 0.
**Mal:** si sale `conexión: False` con `del robot 0`, ve a la sección 7.

---

## 4. Manejar el robot (teleop)

```bash
bash ~/Downloads/SabanaHack/datos/robot/abrir_teleop.sh wifi
```

| Tecla | Acción |
|---|---|
| **U** | Pararse (espera 2 s antes de moverse) |
| **W / S** | Adelante / atrás (Shift+W = rápido) |
| **A / D** | Girar izquierda / derecha |
| **Q / E** | Paso lateral |
| **+ / −** | Velocidad (40/60/80/100 % de límites bajos; arranca en 60 %) |
| **Espacio** | **PARADA** (bloqueado hasta R) |
| **R** | Reanudar |
| **L** | Acostarse |
| **Ctrl-C** | Salir: frena y se acuesta |

Practicar sin robot: `bash ~/Downloads/SabanaHack/datos/robot/abrir_teleop.sh mock`

---

## 5. Ver el video de la cámara (sin SDK)

Con el Mac en la misma red que el robot:
```bash
cd ~/Downloads/SabanaHack/datos && .venv/bin/python -I -c "import cv2;c=cv2.VideoCapture('rtsp://10.181.108.84:8554/test');ok,f=c.read();print(ok, f.shape if ok else None);ok and cv2.imwrite('resultados/ml/capturas_d1/frame.jpg',f)"
```
Si estás por cable, usa `192.168.168.168` en lugar de `10.181.108.84`.

**Montaje para la demo:** pantalla con la hoja **casi a ras de piso**, a 25–35 cm del lente, centrada en la imagen, con brillo medio y sin reflejos de las luces del techo.

---

## 6. Clasificar hojas en vivo con la cámara del robot

```bash
cd ~/Downloads/SabanaHack/datos
M=resultados/ml/modelo_final
.venv/bin/python -I pipeline/predict.py --weights $M/clip_probe_tiles3.joblib --threshold $M/umbral.json --camera "rtsp://10.181.108.84:8554/test?tcp" --frames 0 --interval 1.0 --center
```
- Las 68 hojas del test están listadas en `resultados/ml/drberry_image/splits/test_relativo.csv` (columna `path`, relativa a `datos/`).
- Si falla por la ruta de `predict.py` o por los pesos, revisa `datos/REPORTE_DATOS.md`, sección 6 (pasos A–D).

---

## 7. Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| "esperando que el Mac tenga la IP…" no avanza | El Mac no tiene `10.181.108.1` | Paso 2.4: pon la IP manual |
| "el robot aún no responde" | Robot apagado, arrancando, o estás en otra red | Espera 2 min y revisa a qué Wi-Fi está conectado el Mac |
| "OrbStack no está corriendo" | La app OrbStack está cerrada | Ábrela y repite |
| `conexión: False` y `del robot 0` | El robot no contesta a esta IP | Revisa la configuración del robot (abajo) |
| Batería 0 % en el panel | No llegan datos del robot (no es la batería real) | Igual que la fila anterior |
| El robot se acuesta solo | Pasaron 3 s sin comandos, o la batería está baja | Revisa la red y la batería |
| Luz azul en lugar de verde | El mando tiene el control | En el mando, LT+RT+A |
| Video negro o trabado | Adaptador de 100 Mbps o Wi-Fi débil | Acércate al robot o usa `?tcp` en la URL |

**Revisar la configuración del robot** (solo lectura; por SSH, por Wi-Fi o por cable):
```bash
ssh firefly@10.181.108.84 'cat /opt/export/config/sdk_config.yaml; grep -n SDK_CLIENT_IP /opt/app_launch/start_motion_control.sh; grep -n ROBOT_NET_INTERFACES /etc/systemd/system/robot-launch.service'
```
Hoy debería mostrar `target_ip: "10.181.108.1"`, `SDK_CLIENT_IP="10.181.108.84"` y `ROBOT_NET_INTERFACES=ap0`.

---

## 8. Plan B: pasar el robot a modo cable (solo si el equipo lo acuerda)

Esto cambia la configuración del robot y le rompe la red al compañero que tenga la `10.181.108.1`. Antes de editar, **anota los valores originales**.

1. Conecta el cable. En el Mac, el adaptador "SZNX LAN 100M" debe quedar con IP manual `192.168.168.100`:
   ```bash
   sudo networksetup -setmanual "SZNX LAN 100M" 192.168.168.100 255.255.255.0
   ```
2. Entra al robot: `ssh firefly@192.168.168.168`. Edita con `sudo vim` (o `sudo nano`):
   - `/opt/export/config/sdk_config.yaml` → `target_ip: "192.168.168.100"`
   - `/opt/app_launch/start_motion_control.sh`, línea 27 → `export SDK_CLIENT_IP="192.168.168.168"`
   - `/etc/systemd/system/robot-launch.service`, línea 13 → `Environment="ROBOT_NET_INTERFACES=eth0"`
   - Después: `sudo reboot`.
3. Prueba sin mover: `bash ~/Downloads/SabanaHack/datos/robot/abrir_teleop.sh cable check`
4. Maneja: `bash ~/Downloads/SabanaHack/datos/robot/abrir_teleop.sh cable`
5. Si la luz queda **azul parpadeando** (el control de movimiento no arranca), vuelve a poner los valores originales y reinicia.

---

## 9. Cómo funciona por dentro (por si hay que depurar)

```
Teclado → d1_teleop.py (contenedor Ubuntu "d1ctl", IP 192.168.215.x, puerto 43988)
        → host.docker.internal:43997 (el Mac) → udp_relay.py
        → robot:43997, saliendo desde <IP del Mac>:43988   (el robot solo atiende a esa IP y puerto)
Robot → <IP del Mac>:43988 → udp_relay.py → contenedor:43988
```
- Log del reenvío: `cat /tmp/d1relay.log` (cuenta "al robot" y "del robot").
- Ver si el robot está mandando algo: `sudo tcpdump -i en0 -n udp port 43988` (`en0` es el Wi-Fi; por cable el adaptador es `en5`).
- Cerrar todo a mano: `pkill -f udp_relay.py; docker rm -f d1ctl`

---

## 10. Archivos del proyecto (sin internet)

| Archivo | Para qué |
|---|---|
| `HANDOFF.md` | Contexto completo del proyecto |
| `RESPUESTAS_MENTOR.md` | Lo que dijo el cliente AGRAR |
| `datos/REPORTE_DATOS.md` | Resultados del clasificador, clima y riesgo, pasos de la demo |
| `datos/finanzas/agrar/RESUMEN.md` | Cifras para el pitch |
| `datos/ESCALABILIDAD.md` | Negocio y escalabilidad |
| `PROMPT_simulacion_camas.md` | Prompt de la simulación |

---

## 11. Ruta hotspot: robot y Mac en el hotspot del iPhone (la que eligió Santiago)

Plan basado en `~/Downloads/BerryGoodIdea_demo_vivo_2026-10-23/HANDOFF_DEMO_VIVO.md` y la guía del SDK §5.7.2. En lugar de la VM, el Mac controla el robot con OrbStack. **Tope: 45 min; si no funciona, se revierte.**

| Equipo | IP |
|---|---|
| iPhone (hotspot) | 172.20.10.1 |
| Mac (Wi-Fi, manual) | **172.20.10.12**, máscara 255.255.255.240, router 172.20.10.1 |
| Robot (wlan0, fija) | **172.20.10.13** |

1. **iPhone:** Compartir Internet ON y **"Maximizar compatibilidad" ON** (el D1 solo tiene 2.4 GHz). Deja esa pantalla abierta.
2. **Cable al robot** (para configurarlo sin cortarse): Mac `192.168.168.100` → `ping 192.168.168.168`.
3. Copia los scripts al robot y córrelos (te pide la clave del robot y la del hotspot):
   ```bash
   scp ~/Downloads/SabanaHack/datos/robot/robot_a_hotspot.sh ~/Downloads/SabanaHack/datos/robot/robot_revertir.sh firefly@192.168.168.168:/tmp/
   ssh -t firefly@192.168.168.168 'sudo bash /tmp/robot_a_hotspot.sh'
   ```
   Si al final muestra `target_ip: "172.20.10.12"`, `SDK_CLIENT_IP="172.20.10.13"` y `ROBOT_NET_INTERFACES=wlan0`, entonces: `ssh -t firefly@192.168.168.168 'sudo reboot'`
4. **Mac:** Wi-Fi en el hotspot → Detalles → TCP/IP → Manual: `172.20.10.12`, máscara `255.255.255.240`, router `172.20.10.1` (mantiene internet).
5. Espera 2 min tras el reinicio. Pruebas:
   ```bash
   ping -c 3 172.20.10.13
   bash ~/Downloads/SabanaHack/datos/robot/abrir_teleop.sh hotspot check
   ```
   Si da `conexión: True`, maneja con `bash ~/Downloads/SabanaHack/datos/robot/abrir_teleop.sh hotspot`.
6. **Si falla** (no hay ping, o el LED queda azul parpadeando): por cable,
   ```bash
   ssh -t firefly@192.168.168.168 'sudo bash /tmp/robot_revertir.sh && sudo reboot'
   ```
   Eso restaura los 3 archivos y borra la red del hotspot, y el robot vuelve a como estaba (`10.181.108.x`).

**Riesgos conocidos:**
- El iPhone puede aislar a los clientes entre sí: si el ping al .13 falla con todo bien, es eso.
- El video pasa dos veces por el aire (robot → iPhone → Mac): menos fluido que en la Wi-Fi del robot.
- Si el hotspot no está encendido cuando el robot arranca, el control de movimiento no arranca (LED azul parpadeando). Prende el hotspot **antes** de encender el robot.

---

## 12. ✅ CONFIGURACIÓN QUE FUNCIONÓ (24-oct-2026): red "Juanda"

| Equipo | IP |
|---|---|
| Robot (`wlan0`, fija) | `10.90.251.84` |
| Mac (Wi-Fi, manual) | `10.90.251.94`, máscara 255.255.255.0, router 10.90.251.134 |
| Wi-Fi propio del robot (siempre activo, para rescatarlo) | `192.168.234.1` |

En el robot: `target_ip: "10.90.251.94"`, `SDK_CLIENT_IP="10.90.251.84"`, `ROBOT_NET_INTERFACES=wlan0` (respaldos `*.bak` junto a cada archivo).
Después de cambiar la configuración NO hace falta reiniciar el robot: basta `sudo systemctl restart robot-launch.service`.

Probar sin mover:
```bash
MAC_IP=10.90.251.94 ROBOT_IP=10.90.251.84 bash ~/Downloads/SabanaHack/datos/robot/abrir_teleop.sh red check
```
Manejar:
```bash
MAC_IP=10.90.251.94 ROBOT_IP=10.90.251.84 bash ~/Downloads/SabanaHack/datos/robot/abrir_teleop.sh red
```
Resultado de la prueba: `conexión: True`, batería 61 %, "connect success!".

Si cambian de red: unir el robot (`sudo nmcli dev wifi connect "<RED>" password "<CLAVE>"`), poner en los 3 archivos la IP nueva del Mac y del robot, `sudo systemctl restart robot-launch.service`, y usar `MAC_IP=… ROBOT_IP=… abrir_teleop.sh red`.

---

## 13. Panel de la demo (cámara + clasificador + visor de hojas)

```bash
cd ~/Downloads/SabanaHack/datos && HF_HUB_OFFLINE=1 .venv/bin/python -I robot/panel_demo.py --robot-ip 10.90.251.84 --port 8092
```
- Panel: http://localhost:8092. Muestra la cámara del robot en vivo con un recuadro (ROI) y la predicción, las probabilidades, la latencia, una galería de las 68 hojas del test y un cargador para clasificar una foto propia.
- **Visor de hojas** para la pantalla que mira el robot: `http://<IP_del_Mac>:8092/hoja` (en la red Juanda: http://10.90.251.94:8092/hoja). Tecla `f` = pantalla completa · ←/→ = cambiar · Espacio = al azar. También se cambia desde el panel con clic en una miniatura.
- `HF_HUB_OFFLINE=1` evita que intente conectarse a internet para cargar CLIP.
- Ajusta el ROI para que cubra **solo la hoja de la pantalla**: el modelo no sabe decir "no hay hoja".
