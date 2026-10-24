#!/usr/bin/env bash
# Levanta el PUENTE (d1_bridge.py) del gemelo digital dentro del contenedor Ubuntu 22.04 de OrbStack
# (imagen local "d1sdk", con websockets y pyyaml ya instalados: no necesita internet).
# Se conecta a sim-core del Mac en ws://host.docker.internal:$SIM_PORT/ws/robot (por defecto SIM_PORT=8010).
#
# Uso:
#   bash abrir_puente.sh mock                       # robot SIMULADO del puente (sin SDK ni robot, sin reenvío UDP)
#   bash abrir_puente.sh juanda                     # robot real, red "Juanda" (Mac 10.90.251.94, robot 10.90.251.84)
#   MAC_IP=x ROBOT_IP=y bash abrir_puente.sh red    # robot real en cualquier red
#   bash abrir_puente.sh wifi | cable | hotspot     # presets de abrir_teleop.sh
#   bash abrir_puente.sh juanda check               # SOLO prueba conexión con el robot, NO arranca el puente
# Variables: SPEED_CAP (m/s, por defecto 0.3; 0 = sin tope), MOCK_BATTERY (por defecto 87), SIM_PORT (8010: el 8000 del Mac lo ocupa cfom-backend en OrbStack),
#            EXTRA_ARGS (argumentos extra para d1_bridge.py), SKIP_WAIT=1 (no esperar IP del Mac ni ping).
# Antes: sim-core arriba y escuchando en 0.0.0.0:$SIM_PORT. Ver GEMELO_DIGITAL.md.
set -u
MODO="${1:-mock}"
ACCION="${2:-puente}"
DATOS="/Users/santiagosantafe/Downloads/SabanaHack/datos"
CTRL="/Users/santiagosantafe/Downloads/robot_d1 2"
SDK="$DATOS/raw/agibot_sdk/agibot_D1_Edu-Ultra"
SIM_PORT="${SIM_PORT:-8010}"
SPEED_CAP="${SPEED_CAP:-0.3}"
NOMBRE="d1puente"

case "$MODO" in
  mock)    REAL=0 ;;
  juanda)  REAL=1; MAC_IP="10.90.251.94";    ROBOT_IP="10.90.251.84" ;;
  wifi)    REAL=1; MAC_IP="10.181.108.1";    ROBOT_IP="10.181.108.84" ;;
  cable)   REAL=1; MAC_IP="192.168.168.100"; ROBOT_IP="192.168.168.168" ;;
  hotspot) REAL=1; MAC_IP="172.20.10.12";    ROBOT_IP="172.20.10.13" ;;
  red)     REAL=1; MAC_IP="${MAC_IP:?pon MAC_IP=<IP del Mac>}"; ROBOT_IP="${ROBOT_IP:?pon ROBOT_IP=<IP del robot>}" ;;
  *) echo "Modo desconocido: $MODO (usa mock | juanda | red | wifi | cable | hotspot)"; exit 2 ;;
esac

if ! docker info >/dev/null 2>&1; then
  echo "OrbStack no está corriendo. Ábrelo (app OrbStack) y vuelve a intentar."; exit 1
fi
if ! docker image inspect d1sdk >/dev/null 2>&1; then
  echo "Falta la imagen d1sdk. Constrúyela (una vez, con internet): docker build -t d1sdk $DATOS/robot"; exit 1
fi

if [ "$REAL" = 1 ] && [ "${SKIP_WAIT:-0}" != 1 ]; then
  echo "Modo $MODO: el Mac debe tener $MAC_IP y el robot es $ROBOT_IP"
  until ifconfig | grep -q "inet $MAC_IP "; do echo "  esperando que el Mac tenga la IP $MAC_IP ..."; sleep 3; done
  until ping -c 1 -t 2 "$ROBOT_IP" >/dev/null 2>&1; do echo "  el robot ($ROBOT_IP) aún no responde..."; sleep 2; done
  echo "Robot responde."
fi

docker rm -f "$NOMBRE" >/dev/null 2>&1
MONTAJES=(-v "$CTRL:/ctrl:ro" -v "$DATOS/robot:/robot:ro")
[ "$REAL" = 1 ] && MONTAJES+=(-v "$SDK:/sdk:ro")
docker run -d --name "$NOMBRE" "${MONTAJES[@]}" d1sdk sleep infinity >/dev/null || { echo "No pude crear el contenedor"; exit 1; }
RELAY=""
limpiar() { [ -n "$RELAY" ] && kill "$RELAY" 2>/dev/null; docker rm -f "$NOMBRE" >/dev/null 2>&1; }
trap limpiar EXIT

HIP=$(docker exec "$NOMBRE" getent hosts host.docker.internal | awk '{print $1}')
CIP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$NOMBRE")
if [ -z "$HIP" ]; then echo "El contenedor no resuelve host.docker.internal (¿OrbStack al día?)"; exit 1; fi
echo "Contenedor $CIP · el contenedor ve al Mac (host.docker.internal) en $HIP"

# sim-core debe ser alcanzable DESDE el contenedor (y escuchar en 0.0.0.0, no solo en 127.0.0.1)
if docker exec "$NOMBRE" python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://$HIP:$SIM_PORT/health',timeout=3).status==200 else 1)" 2>/dev/null; then
  echo "sim-core responde en http://$HIP:$SIM_PORT (ws://$HIP:$SIM_PORT/ws/robot)."
else
  echo "AVISO: el contenedor NO alcanza sim-core en $HIP:$SIM_PORT. Arráncalo con --host 0.0.0.0 (cd sim-core && .venv/bin/uvicorn server:app --host 0.0.0.0 --port $SIM_PORT)."
  echo "       El puente reintenta solo; sigo igual."
fi

if [ "$REAL" = 1 ]; then
  pkill -f udp_relay.py 2>/dev/null
  python3 -I "$DATOS/robot/udp_relay.py" "$CIP" "$MAC_IP" "$ROBOT_IP" > /tmp/d1relay.log 2>&1 &
  RELAY=$!
  sleep 1
  if [ "$ACCION" = "check" ]; then
    docker exec -e D1_LOCAL_IP="$CIP" -e D1_DOG_IP="$HIP" "$NOMBRE" timeout 15 python3 /robot/d1_cmd.py check
    echo "--- reenvío: $(tail -1 /tmp/d1relay.log)"
    exit 0
  fi
  ARGS=(--mac-ip "$HIP" --ws-port "$SIM_PORT" --robot-ip "$HIP" --local-ip "$CIP" --sdk-path /sdk)
else
  ARGS=(--mac-ip "$HIP" --ws-port "$SIM_PORT" --mock --mock-battery "${MOCK_BATTERY:-87}")
fi
[ "$SPEED_CAP" != "0" ] && ARGS+=(--speed-cap "$SPEED_CAP")
# shellcheck disable=SC2206
[ -n "${EXTRA_ARGS:-}" ] && ARGS+=($EXTRA_ARGS)

TTY=(-i); [ -t 1 ] && TTY=(-it)
echo "Puente ($MODO) -> ws://$HIP:$SIM_PORT/ws/robot · tope ${SPEED_CAP} m/s · Ctrl-C para salir (acuesta al robot)"
docker exec "${TTY[@]}" -e PYTHONDONTWRITEBYTECODE=1 "$NOMBRE" python3 /ctrl/d1_bridge.py "${ARGS[@]}"
