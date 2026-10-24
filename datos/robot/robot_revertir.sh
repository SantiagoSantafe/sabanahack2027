#!/usr/bin/env bash
# CORRER EN EL ROBOT (por cable): sudo bash /tmp/robot_revertir.sh  -> deja todo como estaba
set -euo pipefail
SSID="${SSID:-iPhone de Santiago ;)}"
for f in /opt/export/config/sdk_config.yaml /opt/app_launch/start_motion_control.sh /etc/systemd/system/robot-launch.service; do
  [ -f "$f.bak" ] && cp "$f.bak" "$f" && echo "restaurado $f"
done
nmcli connection delete "$SSID" 2>/dev/null || true
systemctl daemon-reload
echo "Listo. Ahora: sudo reboot"
