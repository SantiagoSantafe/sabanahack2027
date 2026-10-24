#!/usr/bin/env bash
# Revisa la red antes de manejar el D1 (correr en la VM Ubuntu).
#
# Uso:
#   bash scripts/check_red.sh --mac 192.168.234.23
#   bash scripts/check_red.sh --robot 192.168.168.168 --mac 192.168.234.23     # por cable
#   CHECK_SSH=1 bash scripts/check_red.sh --mac ...   # + lee la config SDK del robot por SSH
#                                                     #   (pide la contraseña: ver guía, sección 3.4)
# Revisa: ping al robot, IP local con ruta al robot (¿NAT?), puerto RTSP 8554, firewall UDP,
# y que el servidor de la simulación del Mac responda en http://<IP_MAC>:8000/api/robot.
set -u

ROBOT="192.168.234.1"
MAC="${MAC_IP:-}"
PORT=8000
LOCAL_PORT=43988
while [ $# -gt 0 ]; do
  case "$1" in
    --robot) ROBOT="$2"; shift 2 ;;
    --mac) MAC="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "Opción desconocida: $1"; exit 2 ;;
  esac
done

OK=0; FAIL=0; WARN=0
ok()   { printf '  \033[32m[OK]\033[0m    %s\n' "$*"; OK=$((OK+1)); }
bad()  { printf '  \033[31m[FALLA]\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); }
note() { printf '  \033[33m[AVISO]\033[0m %s\n' "$*"; WARN=$((WARN+1)); }

tcp_open() {  # host puerto
  if command -v nc >/dev/null 2>&1; then nc -z -w 2 "$1" "$2" >/dev/null 2>&1; return $?; fi
  (exec 3<>"/dev/tcp/$1/$2") >/dev/null 2>&1
}

echo "== Robot $ROBOT"
if ping -c 3 -W 1 "$ROBOT" >/dev/null 2>&1; then
  ok "ping al robot responde"
else
  bad "ping al robot NO responde. ¿Conectado al Wi-Fi del D1 (SSID en la etiqueta) o al cable? ¿VM en modo puente?"
fi

LOCAL_IP=""; IFACE=""
if command -v ip >/dev/null 2>&1; then
  ROUTE="$(ip route get "$ROBOT" 2>/dev/null | head -1)"
  LOCAL_IP="$(printf '%s' "$ROUTE" | sed -n 's/.* src \([0-9.]*\).*/\1/p')"
  IFACE="$(printf '%s' "$ROUTE" | sed -n 's/.* dev \([^ ]*\).*/\1/p')"
fi
if [ -n "$LOCAL_IP" ]; then
  ok "IP local con ruta al robot: $LOCAL_IP (interfaz $IFACE)  -> úsala como target_ip en el robot"
  case "$LOCAL_IP" in
    10.0.2.*) bad "10.0.2.x = VirtualBox en NAT. Cambia el adaptador a 'Adaptador puente' (bridged)." ;;
    192.168.122.*) bad "192.168.122.x = libvirt NAT. Usa modo puente." ;;
    192.168.56.*) bad "192.168.56.x = VirtualBox host-only. Usa 'Adaptador puente'." ;;
    172.*) note "172.x puede ser el 'Default Switch' (NAT) de Hyper-V. El SDK necesita modo puente." ;;
  esac
  if [ "${LOCAL_IP%.*}" != "${ROBOT%.*}" ]; then
    bad "La IP local $LOCAL_IP no está en la subred del robot (${ROBOT%.*}.x)."
  fi
else
  bad "No hay ruta hacia $ROBOT desde esta máquina."
fi

case "$IFACE" in
  tun*|utun*|wg*|ppp*|tailscale*|zt*)
    bad "La ruta al robot pasa por una VPN ($IFACE). Desactívala: el tráfico al robot se va por el túnel." ;;
esac

# RTSP de verdad (OPTIONS) y no solo "puerto abierto": una VPN/proxy acepta cualquier TCP.
RTSP_CODE="$(curl -s -m 3 -o /dev/null -w '%{response_code}' "rtsp://$ROBOT:8554/test" 2>/dev/null || true)"
if [ "$RTSP_CODE" = "200" ]; then
  ok "servidor RTSP responde en rtsp://$ROBOT:8554/test (video de la cámara)"
elif tcp_open "$ROBOT" 8554; then
  note "TCP 8554 abierto pero no respondió RTSP (código '${RTSP_CODE:-ninguno}'): ¿VPN/proxy en medio?"
else
  note "puerto RTSP 8554 cerrado o filtrado (el video de la cámara no llegaría; el control sí puede)"
fi

if command -v ufw >/dev/null 2>&1 && sudo -n ufw status 2>/dev/null | grep -q "Status: active"; then
  if sudo -n ufw status 2>/dev/null | grep -q "$LOCAL_PORT/udp"; then
    ok "ufw activo y permite $LOCAL_PORT/udp"
  else
    bad "ufw activo sin regla para el UDP de retorno del robot: sudo ufw allow $LOCAL_PORT/udp"
  fi
else
  ok "firewall ufw inactivo (o sin permiso para verlo); el UDP $LOCAL_PORT no debería bloquearse aquí"
fi

echo "== Simulación en el Mac"
if [ -z "$MAC" ]; then
  note "sin --mac: no reviso el servidor de la simulación"
else
  if tcp_open "$MAC" "$PORT"; then
    ok "TCP $MAC:$PORT abierto"
  else
    bad "TCP $MAC:$PORT cerrado. ¿sim-core corre con --host 0.0.0.0? ¿firewall del Mac? ¿misma red?"
  fi
  RESP="$(curl -s -m 3 "http://$MAC:$PORT/api/robot" 2>/dev/null || true)"
  if [ -n "$RESP" ]; then
    ok "GET /api/robot responde: $(printf '%s' "$RESP" | tr -d '\n' | cut -c1-160)"
  else
    bad "GET http://$MAC:$PORT/api/robot no responde"
  fi
fi

if [ "${CHECK_SSH:-0}" = "1" ]; then
  echo "== Config SDK dentro del robot (SSH, solo lectura; pide la contraseña de la guía 3.4)"
  REMOTE='echo "--- sdk_config.yaml"; cat /opt/export/config/sdk_config.yaml;
          echo "--- versión de control de movimiento (>= 0.3.4 permite retomar con el mando)";
          grep -oP "motion-control_\K[^_]+" /etc/release/*[^rootfs]*.yaml 2>/dev/null;
          echo "--- SDK_CLIENT_IP (en Wi-Fi debe estar comentado; guía 6.1)";
          grep -n "SDK_CLIENT_IP" /opt/app_launch/start_motion_control.sh;
          echo "--- ROBOT_NET_INTERFACES (en Wi-Fi no debe estar; guía 6.1)";
          grep -n "ROBOT_NET_INTERFACES" /etc/systemd/system/robot-launch.service; true'
  OUT="$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new "firefly@$ROBOT" "$REMOTE" 2>&1)"
  echo "$OUT" | sed 's/^/    /'
  TARGET="$(printf '%s\n' "$OUT" | sed -n 's/^target_ip: *"\{0,1\}\([0-9.]*\)"\{0,1\}.*/\1/p' | head -1)"
  if [ -n "$TARGET" ] && [ -n "$LOCAL_IP" ]; then
    if [ "$TARGET" = "$LOCAL_IP" ]; then
      ok "target_ip del robot ($TARGET) = IP local de esta VM"
    else
      bad "target_ip del robot es $TARGET pero esta VM es $LOCAL_IP. Edítalo (guía 3.7) y reinicia el robot."
    fi
  fi
fi

echo
echo "Resumen: $OK OK, $WARN avisos, $FAIL fallas"
[ "$FAIL" -eq 0 ]
