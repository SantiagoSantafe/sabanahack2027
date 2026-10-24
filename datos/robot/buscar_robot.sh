#!/usr/bin/env bash
# Encuentra el AgiBot D1 en la red Wi-Fi actual del Mac y dice qué IPs usar.
# Uso:  bash buscar_robot.sh            → busca y muestra las IPs y los comandos a usar
#       bash buscar_robot.sh check      → además prueba el SDK sin mover el robot
# Cómo busca (lo mismo que se hizo a mano): IP y red del Mac → ping a toda la red /24 → tabla ARP →
# el robot es el equipo con la MAC conocida del D1 o con la cámara RTSP (puerto 8554) abierta.
set -u
MAC_ROBOT="94:ba:6:fb:a7:5e"          # MAC de wlan0 del D1 del equipo (arp la muestra sin ceros a la izquierda)
IF="${IF:-en0}"
DIR="$(cd "$(dirname "$0")" && pwd)"

MAC_IP=$(ipconfig getifaddr "$IF" 2>/dev/null || true)
if [ -z "$MAC_IP" ]; then
  echo "El Mac no tiene IP en $IF: conéctalo al Wi-Fi (Juanda u otra) y repite."; exit 1
fi
GW=$(route -n get default 2>/dev/null | awk '/gateway/{print $2}')
NET="${MAC_IP%.*}"
MASK=$(ipconfig getoption "$IF" subnet_mask 2>/dev/null || true)
echo "Mac: $MAC_IP · máscara: ${MASK:-?} · router: ${GW:-?} · buscando en $NET.0/24 …"
if [ -n "$MASK" ] && [ "$MASK" != "255.255.255.0" ]; then
  echo "  Aviso: esta red es más grande que /24 (red de universidad u oficina). Solo se barre $NET.0/24;"
  echo "  para el robot conviene un hotspot o router propio (Juanda), donde Mac y robot quedan en el mismo /24."
fi

for i in $(seq 1 254); do ping -c 1 -W 300 "$NET.$i" >/dev/null 2>&1 & done
wait 2>/dev/null

ROBOT_IP=""
while read -r ip mac; do
  [ "$ip" = "$MAC_IP" ] && continue
  rtsp=no; ssh=no
  nc -z -G 1 "$ip" 8554 >/dev/null 2>&1 && rtsp=sí
  nc -z -G 1 "$ip" 22 >/dev/null 2>&1 && ssh=sí
  marca=""
  [ "$mac" = "$MAC_ROBOT" ] && marca="  ← MAC del D1"
  [ "$rtsp" = sí ] && marca="$marca  ← cámara RTSP abierta"
  printf "  %-15s %-18s cámara:%-3s ssh:%-3s%s\n" "$ip" "$mac" "$rtsp" "$ssh" "$marca"
  if [ -z "$ROBOT_IP" ] && { [ "$mac" = "$MAC_ROBOT" ] || [ "$rtsp" = sí ]; }; then ROBOT_IP="$ip"; fi
done < <(arp -an | awk -v n="$NET." 'index($2,"(" n)==1 && $4!="(incomplete)" {gsub(/[()]/,"",$2); print $2, $4}' | sort -t. -k4 -n)

# La MAC del D1 también puede estar en la tabla ARP fuera de este /24 (p. ej. red /16): búscala en toda la tabla
if [ -z "$ROBOT_IP" ]; then
  ROBOT_IP=$(arp -an | awk -v m="$MAC_ROBOT" '$4==m {gsub(/[()]/,"",$2); print $2; exit}')
  [ -n "$ROBOT_IP" ] && echo "  MAC del D1 encontrada en la tabla ARP: $ROBOT_IP"
fi
echo
if [ -z "$ROBOT_IP" ]; then
  echo "No apareció el robot en $NET.0/24."
  echo "  1) ¿Está encendido y unido a esta misma red? Entra por su Wi-Fi propio: ssh firefly@192.168.234.1"
  echo "     y revisa: ip -4 addr show wlan0 ; nmcli -t -f NAME,DEVICE con show --active"
  echo "  2) Si la red cambió (hotspot de celular), únelo de nuevo (ver GUIA_RED_ROBOT.md, paso 2)."
  exit 2
fi

echo "ROBOT: $ROBOT_IP   ·   MAC: $MAC_IP"
echo
echo "1) En el robot (ssh firefly@$ROBOT_IP), si las IPs cambiaron, apunta el SDK al Mac y reinicia:"
echo "   sudo sed -i 's/^target_ip:.*/target_ip: \"$MAC_IP\"/' /opt/export/config/sdk_config.yaml && sudo sed -i 's/^\\([[:space:]]*\\)export SDK_CLIENT_IP=.*/\\1export SDK_CLIENT_IP=\"$ROBOT_IP\"/' /opt/app_launch/start_motion_control.sh && sudo systemctl daemon-reload && sudo systemctl restart robot-launch.service"
echo "2) Probar SDK sin mover:  MAC_IP=$MAC_IP ROBOT_IP=$ROBOT_IP bash $DIR/abrir_teleop.sh red check"
echo "3) Puente al simulador:   MAC_IP=$MAC_IP ROBOT_IP=$ROBOT_IP bash $DIR/abrir_puente.sh red"
echo "4) Panel de cámara:       cd $(dirname "$DIR") && HF_HUB_OFFLINE=1 .venv/bin/python -I robot/panel_demo.py --robot-ip $ROBOT_IP --port 8092 --modelo resultados/ml/modelo_camara --sim-url http://localhost:8010"
echo "5) Visor de hojas en los PCs:  http://$MAC_IP:8092/hoja?robot=1   (los demás PCs: http://$MAC_IP:8092/hoja)"

if [ "${1:-}" = "check" ]; then
  echo; echo "Probando el SDK (no mueve el robot)…"
  MAC_IP="$MAC_IP" ROBOT_IP="$ROBOT_IP" bash "$DIR/abrir_teleop.sh" red check 2>&1 | grep -E "conexión|getBattery|reenvío"
fi
