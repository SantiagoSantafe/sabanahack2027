#!/usr/bin/env bash
# Prepara la VM Ubuntu 22.04 para manejar el D1 EDU con el SDK oficial.
#
# Uso (desde la carpeta robot_d1/):
#   bash scripts/setup_vm_ubuntu.sh
#   WITH_PYNPUT=1 bash scripts/setup_vm_ubuntu.sh           # + teclado que sabe cuándo sueltas
#   D1_SDK_PATH=/ruta/al/agibot_D1_Edu-Ultra bash scripts/setup_vm_ubuntu.sh   # SDK ya copiado
#
# Qué hace:
#   1. Comprueba Ubuntu 22.04 y la arquitectura (x86_64 o aarch64).
#   2. Instala python3.10 + venv + herramientas de red (apt, pide sudo).
#   3. Crea robot_d1/.venv con websockets y pyyaml (y pynput si WITH_PYNPUT=1).
#   4. Clona el SDK (o usa D1_SDK_PATH) y prueba "import mc_sdk_zsl_1_py".
#   5. Crea config.yaml desde config.example.yaml con la ruta del SDK.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_URL="https://github.com/AgibotTech/agibot_D1_Edu-Ultra.git"
SDK_DIR="${D1_SDK_PATH:-$HOME/agibot_D1_Edu-Ultra}"
VENV="$HERE/.venv"

say()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mAVISO:\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mERROR:\033[0m %s\n' "$*"; exit 1; }

say "1/5 Sistema"
if [ -r /etc/os-release ]; then . /etc/os-release; fi
echo "Sistema: ${PRETTY_NAME:-desconocido}  Arquitectura: $(uname -m)"
[ "$(uname -s)" = "Linux" ] || die "Esto es para la VM Linux. En el Mac usa --mock."
if [ "${VERSION_ID:-}" != "22.04" ]; then
  warn "La guía del SDK pide Ubuntu 22.04 (sección 3.2). Sigo, pero puede fallar."
fi
case "$(uname -m)" in
  x86_64|amd64) ARCH=x86_64 ;;
  aarch64|arm64) ARCH=aarch64 ;;
  *) die "Arquitectura $(uname -m) no soportada por el SDK (solo x86_64 y aarch64)." ;;
esac
if grep -qi microsoft /proc/version 2>/dev/null; then
  warn "Parece WSL. La guía dice que WSL NO sirve para el SDK (sección 3.2). Usa una VM en modo puente."
fi

say "2/5 Paquetes del sistema (sudo apt)"
PKGS="python3.10 python3.10-venv python3-pip git curl iputils-ping netcat-openbsd iproute2"
if [ "${WITH_PYNPUT:-0}" = "1" ]; then
  PKGS="$PKGS python3.10-dev build-essential"   # pynput compila evdev en Linux
fi
if [ "${WITH_FFMPEG:-0}" = "1" ]; then
  PKGS="$PKGS ffmpeg"                            # ffplay para ver el RTSP del robot (guía 5.1)
fi
sudo apt-get update -y
# shellcheck disable=SC2086
sudo apt-get install -y $PKGS

say "3/5 Entorno virtual de Python 3.10 en $VENV"
python3.10 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV/bin/pip" install -r "$HERE/requirements.txt"
if [ "${WITH_PYNPUT:-0}" = "1" ]; then
  if ! "$VENV/bin/pip" install pynput; then
    warn "No se pudo instalar pynput. El modo terminal (por defecto) funciona igual."
  fi
fi
if [ "${WITH_TESTS:-0}" = "1" ]; then
  "$VENV/bin/pip" install pytest pytest-asyncio
fi

say "4/5 SDK del D1 en $SDK_DIR"
if [ -d "$SDK_DIR/lib/zsl-1/$ARCH" ]; then
  echo "Ya existe: $SDK_DIR"
elif [ -n "${D1_SDK_PATH:-}" ]; then
  die "D1_SDK_PATH=$D1_SDK_PATH no tiene lib/zsl-1/$ARCH. Copia el repo completo del SDK."
else
  echo "Clonando $SDK_URL (si la VM no tiene internet, copia la carpeta y usa D1_SDK_PATH=...)"
  git clone --depth 1 "$SDK_URL" "$SDK_DIR" || die "No pude clonar el SDK. Cópialo a mano y vuelve a correr con D1_SDK_PATH."
fi
ls -1 "$SDK_DIR/lib/zsl-1/$ARCH"
echo "Probando el import con Python 3.10:"
if (cd "$HERE" && "$VENV/bin/python" -m d1.sdk --sdk-path "$SDK_DIR"); then
  echo "OK: el SDK se importa."
else
  die "El SDK no se importa. Revisa que sea Python 3.10 y que exista lib/zsl-1/$ARCH (guía 6.4)."
fi

say "5/5 config.yaml"
if [ -f "$HERE/config.yaml" ]; then
  echo "Ya existe $HERE/config.yaml (no lo toco)."
else
  sed "s#^  sdk_path: .*#  sdk_path: $SDK_DIR#" "$HERE/config.example.yaml" > "$HERE/config.yaml"
  echo "Creado $HERE/config.yaml"
fi

if command -v ufw >/dev/null 2>&1 && sudo ufw status 2>/dev/null | grep -q "Status: active"; then
  warn "El firewall ufw está activo. El robot devuelve UDP al puerto 43988: sudo ufw allow 43988/udp"
fi

cat <<EOF

Listo. Siguientes pasos (ver README.md):
  source $VENV/bin/activate
  bash scripts/check_red.sh --mac <IP_DEL_MAC>
  python d1_teleop.py --config config.yaml              # teleop solo en la VM
  python d1_bridge.py --config config.yaml --mac-ip <IP_DEL_MAC> --local-keys
EOF
