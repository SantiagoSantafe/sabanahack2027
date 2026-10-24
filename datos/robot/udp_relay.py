"""Reenvío UDP en ambos sentidos entre el SDK (contenedor OrbStack) y el D1.

El robot solo atiende a 192.168.168.100:43988 (su target_ip/target_port) y escucha en :43997.
Al salir del contenedor, OrbStack cambia el puerto de origen, así que aquí:
  contenedor -> Mac:43997 (este script)  -> robot:43997 desde 192.168.168.100:43988
  robot -> 192.168.168.100:43988         -> contenedor:43988
Uso: python3 -I udp_relay.py <IP_contenedor> [IP_Mac_hacia_robot] [IP_robot]
(por defecto cable: 192.168.168.100 y 192.168.168.168; Wi-Fi actual del robot: 10.181.108.1 y 10.181.108.84)
"""
import select
import socket
import sys

CONT = (sys.argv[1], 43988)
MAC_IP = sys.argv[2] if len(sys.argv) > 2 else "192.168.168.100"
ROBOT = (sys.argv[3] if len(sys.argv) > 3 else "192.168.168.168", 43997)

lado_robot = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
lado_robot.bind((MAC_IP, 43988))
lado_cont = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
lado_cont.bind(("0.0.0.0", 43997))

ida = vuelta = 0
while True:
    listos, _, _ = select.select([lado_robot, lado_cont], [], [])
    for s in listos:
        data, _ = s.recvfrom(65535)
        if s is lado_cont:
            lado_robot.sendto(data, ROBOT)
            ida += 1
        else:
            lado_cont.sendto(data, CONT)
            vuelta += 1
        if (ida + vuelta) in (1, 10, 100, 1000) or (ida + vuelta) % 20000 == 0:
            print(f"al robot {ida} · del robot {vuelta}", flush=True)
