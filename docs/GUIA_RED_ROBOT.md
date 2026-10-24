# Guía rápida: encontrar el robot y dejarlo listo antes de la demo

Corte: 24-oct-2026. Sin contraseñas en este archivo: la clave del Wi-Fi la tiene el equipo y la del robot está en la guía del SDK de AgiBot (§3.4).

## 0. IPs conocidas

| Red | Mac | Robot D1 | Router | Nota |
|---|---|---|---|---|
| **Juanda (hoy)** | `10.73.198.94` | `10.73.198.84` | `10.73.198.11` | Hotspot: **puede cambiar de rango al reiniciarse** |
| Juanda (antes) | `10.90.251.94` | `10.90.251.84` | `10.90.251.134` | Rango viejo; ya no sirve |
| Wi-Fi propio del robot | el que dé el robot (p. ej. `192.168.234.28`) | `192.168.234.1` | — | Siempre activo: es la puerta de rescate |
| Cable Ethernet | `192.168.168.100` (fija) | `192.168.168.168` | — | Para SSH y video; el SDK no escucha por cable |
| Hotspot iPhone | `172.20.10.12` | `172.20.10.13` | `172.20.10.1` | Ruta alternativa (máscara /28) |

- **MAC del D1 (wlan0):** `94:ba:06:fb:a7:5e`. Así se reconoce aunque cambie la IP.
- **Puertos:** cámara RTSP `8554` (`rtsp://<IP_ROBOT>:8554/test`), SSH `22`, SDK `43997` (robot) y `43988` (Mac).
- **Redes de universidad u oficina** (máscara más grande que /24, como 172.21.x): no sirven para el robot. Usa Juanda u otro hotspot o router propio.

## 1. Antes de empezar (checklist)
- [ ] Batería **> 40 %**. Por debajo de 25 % no deja pararse; por debajo de 20 % el SDK no responde.
- [ ] Alguien con el **mando**: **LB+RB** = parada de emergencia, **LB+X** = acostarse.
- [ ] **1 m libre** alrededor y el **router o hotspot cerca** del recorrido. Los cortes de antes fueron por señal débil al girar.
- [ ] **OrbStack abierto** (`docker info` responde). Si no: `open -a OrbStack`.

## 2. Encontrar el robot (lo que hace Claude, en un comando)
Con el Mac conectado a la **misma red** que el robot:
```bash
bash ~/Downloads/SabanaHack/datos/robot/buscar_robot.sh
```
Qué hace el script:
1. Toma la IP, la máscara y el router del Mac.
2. Hace ping a las 254 IPs de su red /24.
3. Lee la tabla ARP y marca como robot el equipo con la **MAC del D1** o con la **cámara RTSP (8554) abierta**.
4. Imprime los comandos exactos con las IPs encontradas.

Con `check` al final también prueba el SDK sin mover el robot:
```bash
bash ~/Downloads/SabanaHack/datos/robot/buscar_robot.sh check
```

### A mano, si lo prefieres
```bash
ipconfig getifaddr en0                     # IP del Mac (p. ej. 10.73.198.94 → la red es 10.73.198.x)
for i in $(seq 1 254); do (ping -c 1 -W 300 10.73.198.$i >/dev/null 2>&1 &); done; sleep 3
arp -an | grep -v incomplete               # busca la MAC 94:ba:6:fb:a7:5e
nc -z -G 1 10.73.198.84 8554 && echo "cámara del robot abierta"
```

### Si el robot no aparece
Probablemente no está en esa red: Juanda se reinició o el robot se unió a otra.
1. Conecta el Mac al **Wi-Fi propio del robot** y entra: `ssh firefly@192.168.234.1`
2. Mira dónde está: `ip -4 addr show wlan0; nmcli -t -f NAME,DEVICE con show --active`
3. Únelo a Juanda (escribe tú la clave):
   ```bash
   sudo nmcli dev wifi rescan && sudo nmcli dev wifi connect "Juanda" password "<CLAVE>" ifname wlan0
   ```
4. Vuelve el Mac a Juanda y corre otra vez `buscar_robot.sh`.

## 3. Apuntar el SDK al Mac (cada vez que cambien las IPs)
Entra al robot (`ssh firefly@<IP_ROBOT>`) y revisa:
```bash
grep target_ip /opt/export/config/sdk_config.yaml; grep SDK_CLIENT_IP /opt/app_launch/start_motion_control.sh; grep ROBOT_NET_INTERFACES /etc/systemd/system/robot-launch.service
```
Debe decir `target_ip` = **IP del Mac**, `SDK_CLIENT_IP` = **IP del robot** y `wlan0`. Si no, usa el comando que imprime `buscar_robot.sh` (paso 1), que es este con las IPs puestas:
```bash
sudo sed -i 's/^target_ip:.*/target_ip: "<IP_MAC>"/' /opt/export/config/sdk_config.yaml && sudo sed -i 's/^\([[:space:]]*\)export SDK_CLIENT_IP=.*/\1export SDK_CLIENT_IP="<IP_ROBOT>"/' /opt/app_launch/start_motion_control.sh && sudo systemctl daemon-reload && sudo systemctl restart robot-launch.service
```
**Siempre que el robot acabe de encender**, reinicia el servicio aunque las IPs estén bien: `sudo systemctl restart robot-launch.service`. Si arranca antes de tener Wi-Fi, queda sordo.

## 4. Probar sin mover
```bash
MAC_IP=<IP_MAC> ROBOT_IP=<IP_ROBOT> bash ~/Downloads/SabanaHack/datos/robot/abrir_teleop.sh red check
```
Bien: `conexión: True` y batería real (no 0). Si `conexión: False`, vuelve al paso 3.

## 5. Levantar todo (orden)
| Qué | Comando | Dónde se ve |
|---|---|---|
| Simulador (backend) | `cd ~/Downloads/BerryGoodIdea_demo_vivo_2026-10-23/berry-sim/sim-core && .venv/bin/uvicorn server:app --host 0.0.0.0 --port 8010` | `http://localhost:8010/health` |
| Gemelo 3D | `cd ~/Downloads/BerryGoodIdea_demo_vivo_2026-10-23/berry-sim/web && npm run dev` | `http://localhost:5173` |
| Dashboard del supervisor | `cd ~/Downloads/SabanaHack/dashboard && npm run dev` | `http://localhost:5180` |
| Puente con el D1 | `MAC_IP=<IP_MAC> ROBOT_IP=<IP_ROBOT> bash ~/Downloads/SabanaHack/datos/robot/abrir_puente.sh red` | barra "D1 real: conectado" en el simulador |
| Panel de cámara | `cd ~/Downloads/SabanaHack/datos && HF_HUB_OFFLINE=1 .venv/bin/python -I robot/panel_demo.py --robot-ip <IP_ROBOT> --port 8092 --modelo resultados/ml/modelo_camara --sim-url http://localhost:8010` | `http://localhost:8092` |
| Visor de hojas (PCs) | — | PC frente al robot: `http://<IP_MAC>:8092/hoja?robot=1` · otros PCs: `http://<IP_MAC>:8092/hoja` |

- Para **reiniciar el simulador**, cierra solo el servidor: `kill $(lsof -ti tcp:8010 -sTCP:LISTEN)`. **No** uses `lsof -ti tcp:8010` sin `-sTCP:LISTEN`: también mata a OrbStack y se cae el puente.
- Usa **un solo** visor con `?robot=1` a la vez.

## 6. La demo
1. **Dashboard** → tarjeta "Estado del bloque" → **Robot asignado a: Bloque 1 / Bloque 2** (lo elige el supervisor).
2. **Simulador** → **⟲ Inicio**: el gemelo vuelve a la entrada del pasillo del bloque. Pon el D1 en esa posición, mirando al fondo.
3. **Pararse** (un solo clic), espera a "De pie" y pulsa **Ruta real** (escala 0,01, unos 6,8 m de sala; 2 paradas por pasillo para mirar a cada lado).
4. Muestra una hoja **sana** (queda registrada sin alerta) y una **enferma** (el robot para 4 s, sale la alerta con nave · cama · planta).
5. En el dashboard: **Enviar operario → Registrar confirmación**.

## 7. Problemas frecuentes
| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `conexión: False` / el robot "no contesta" | SDK apuntando a otra IP o servicio sin reiniciar | Paso 3 y reiniciar el servicio |
| Puente con `sdk=NO`, batería 0 % | Se cortó el Wi-Fi con el robot | Acerca el router, `ping <IP_ROBOT>` (< 50 ms), reinicia el puente: `docker rm -f d1puente` y abrir_puente otra vez |
| Se para y a 1 s se acuesta | Doble clic que cae en "Acostarse", o se quedó sin órdenes (watchdog de 3 s) | Un solo clic en Pararse; revisar la conexión |
| "OrbStack no está corriendo" | OrbStack se cerró | `open -a OrbStack` y abrir_puente otra vez |
| "Fuera del pasillo: parada de emergencia" | Barrera de geocerca en Manual con el gemelo fuera del bloque | ⟲ Inicio y Reanudar |
| Ruta cancelada "sin video" | El panel de cámara perdió la transmisión más de 12 s | Reiniciar el panel (Ctrl-C y volver a lanzarlo) |
| El robot ya no está en la IP de siempre | Juanda cambió de rango | `buscar_robot.sh` y paso 3 |
| Error `0x3007` justo al pararse | Normal en el primer segundo | Ignorar si después dice "De pie" |
