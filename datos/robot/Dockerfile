FROM ubuntu:22.04
RUN apt-get update -qq && apt-get install -y -qq python3 python3-pip libpython3.10 >/dev/null && rm -rf /var/lib/apt/lists/*
# Dependencias del puente (d1_bridge.py) y de sus pruebas: se instalan AQUÍ, al construir la imagen,
# para que el día de la demo no haga falta internet. Reconstruir: docker build -t d1sdk datos/robot
RUN pip3 install --no-cache-dir "websockets>=13,<18" "pyyaml>=6" pytest pytest-asyncio
