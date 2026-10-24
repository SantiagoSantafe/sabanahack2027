#!/usr/bin/env bash
# CORRER EN EL ROBOT (por SSH por CABLE): sudo bash /tmp/robot_a_hotspot.sh
# Une el D1 al hotspot del iPhone como cliente (wlan0, IP fija) y apunta el SDK al Mac.
# Respaldos: *.bak. Para volver atrás: sudo bash /tmp/robot_revertir.sh
set -euo pipefail
SSID="${SSID:-iPhone de Santiago ;)}"
ROBOT_IP="172.20.10.13"
MAC_IP="172.20.10.12"
CFG=/opt/export/config/sdk_config.yaml
MC=/opt/app_launch/start_motion_control.sh
SVC=/etc/systemd/system/robot-launch.service

for f in "$CFG" "$MC" "$SVC"; do [ -f "$f.bak" ] || cp "$f" "$f.bak"; done
echo "Respaldos listos (*.bak)."

PASS="${PASS:-}"
[ -n "$PASS" ] || { read -r -s -p "Clave del hotspot '$SSID': " PASS; echo; }
nmcli device wifi rescan || true
nmcli device wifi connect "$SSID" password "$PASS" ifname wlan0
nmcli con mod "$SSID" ipv4.method manual ipv4.addresses "$ROBOT_IP/28" ipv4.gateway 172.20.10.1 ipv4.dns 172.20.10.1 connection.autoconnect yes
nmcli con up "$SSID"
ip -4 addr show wlan0 | grep -q "$ROBOT_IP" || { echo "wlan0 NO tiene $ROBOT_IP: no toco el SDK. Revisa el hotspot."; exit 1; }
ping -c 2 -W 2 172.20.10.1 >/dev/null && echo "wlan0 ve al iPhone." || echo "AVISO: no responde 172.20.10.1"

sed -i "s/^target_ip:.*/target_ip: \"$MAC_IP\"/" "$CFG"
sed -i "s/^\([[:space:]]*\)#\{0,1\}[[:space:]]*export SDK_CLIENT_IP=.*/\1export SDK_CLIENT_IP=\"$ROBOT_IP\"/" "$MC"
sed -i 's/^Environment="ROBOT_NET_INTERFACES=.*"/Environment="ROBOT_NET_INTERFACES=wlan0"/' "$SVC"
systemctl daemon-reload

echo "--- quedó así:"
grep -n target_ip "$CFG"; grep -n SDK_CLIENT_IP "$MC"; grep -n ROBOT_NET_INTERFACES "$SVC"
if [ "${AUTO_REBOOT:-0}" = "1" ]; then echo "Reiniciando en 5 s..."; sleep 5; reboot; else echo "Si se ve bien: sudo reboot"; fi
