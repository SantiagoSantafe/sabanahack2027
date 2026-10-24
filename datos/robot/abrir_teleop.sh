#!/usr/bin/env bash
# Abre el control del D1 desde el Mac: SDK de Linux en un contenedor Ubuntu 22.04 (OrbStack, imagen
# local "d1sdk") + reenvío UDP en ambos sentidos (udp_relay.py). Funciona SIN internet.
#
# Uso:
#   bash abrir_teleop.sh hotspot       # robot y Mac en el hotspot del iPhone (Mac 172.20.10.12, robot .13)
#   MAC_IP=x ROBOT_IP=y bash abrir_teleop.sh red   # cualquier red (p. ej. hotspot "Juanda")
#   bash abrir_teleop.sh wifi          # Wi-Fi del robot (config actual: Mac 10.181.108.1, robot 10.181.108.84)
#   bash abrir_teleop.sh cable         # cable (solo si el robot se pasa a modo cable)
#   bash abrir_teleop.sh wifi check    # SOLO conecta y lee batería/postura, NO mueve
#   bash abrir_teleop.sh mock          # práctica sin robot
set -u
MODO="${1:-wifi}"
ACCION="${2:-teleop}"
DATOS="/Users/santiagosantafe/Downloads/SabanaHack/datos"
CTRL="/Users/santiagosantafe/Downloads/robot_d1 2"   # versión más nueva del controlador
SDK="$DATOS/raw/agibot_sdk/agibot_D1_Edu-Ultra"

case "$MODO" in
  mock)  cd "$CTRL" && exec python3 d1_teleop.py --mock ;;
  wifi)  MAC_IP="10.181.108.1";    ROBOT_IP="10.181.108.84" ;;
  cable) MAC_IP="192.168.168.100"; ROBOT_IP="192.168.168.168" ;;
  hotspot) MAC_IP="172.20.10.12";  ROBOT_IP="172.20.10.13" ;;
  red)   MAC_IP="${MAC_IP:?pon MAC_IP=<IP del Mac>}"; ROBOT_IP="${ROBOT_IP:?pon ROBOT_IP=<IP del robot>}" ;;
  *) echo "Modo desconocido: $MODO (usa hotspot | red | wifi | cable | mock)"; exit 2 ;;
esac

echo "Modo $MODO: el Mac debe tener $MAC_IP y el robot es $ROBOT_IP"
until ifconfig | grep -q "inet $MAC_IP "; do echo "  esperando que el Mac tenga la IP $MAC_IP ..."; sleep 3; done
until ping -c 1 -t 2 "$ROBOT_IP" >/dev/null 2>&1; do echo "  el robot ($ROBOT_IP) aún no responde..."; sleep 2; done
echo "Robot responde."

if ! docker info >/dev/null 2>&1; then
  echo "OrbStack no está corriendo. Ábrelo (app OrbStack) y vuelve a intentar."; exit 1
fi

docker rm -f d1ctl >/dev/null 2>&1
docker run -d --name d1ctl -v "$SDK:/sdk:ro" -v "$CTRL:/ctrl:ro" -v "$DATOS/robot:/robot:ro" d1sdk sleep infinity >/dev/null
CIP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' d1ctl)
HIP=$(docker exec d1ctl getent hosts host.docker.internal | awk '{print $1}')
echo "Contenedor $CIP · el contenedor ve al Mac en $HIP"

pkill -f udp_relay.py 2>/dev/null
python3 -I "$DATOS/robot/udp_relay.py" "$CIP" "$MAC_IP" "$ROBOT_IP" > /tmp/d1relay.log 2>&1 &
RELAY=$!
trap 'kill $RELAY 2>/dev/null; docker rm -f d1ctl >/dev/null 2>&1' EXIT
sleep 1

if [ "$ACCION" = "check" ]; then
  docker exec -e D1_LOCAL_IP="$CIP" -e D1_DOG_IP="$HIP" d1ctl timeout 15 python3 /robot/d1_cmd.py check
  echo "--- reenvío: $(tail -1 /tmp/d1relay.log)"
  echo "Si 'conexión: True' y 'del robot' > 0: funciona. Si 'del robot 0': el robot no contesta (ver guía)."
  exit 0
fi

echo "Controles: U pararse · W/S adelante/atrás · A/D girar · Q/E lateral · Espacio PARADA · R reanudar · L acostarse · Ctrl-C salir"
docker exec -it d1ctl python3 /ctrl/d1_teleop.py --robot-ip "$HIP" --local-ip "$CIP" --sdk-path /sdk
