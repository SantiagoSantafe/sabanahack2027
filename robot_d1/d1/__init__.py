"""Paquete del puente y la teleoperación del AgiBot D1 EDU (equipo Berry Good Idea).

Módulos:
- safety:     funciones puras de seguridad (escalado, recorte al SDK, rampa, vigencia, estop).
- sdk:        adaptador RealRobot (mc_sdk_zsl_1_py) y MockRobot (cinemática simple).
- controller: núcleo de control compartido por d1_teleop.py y d1_bridge.py.
- keyboard:   lectura de teclado (terminal sin dependencias o pynput).
- bridge:     cliente WebSocket hacia la simulación (contrato v1, PROTOCOLO.md).
- config:     valores por defecto, YAML opcional y argumentos de línea de comandos.
"""

__version__ = "1.0.0"
PROTOCOL_VERSION = 1
