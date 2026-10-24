"""Comandos básicos al D1 por el SDK oficial (correr en Linux aarch64/x86_64, Python 3.10).
Uso: python3 d1_cmd.py check | stand | lie
"""
import os, platform, sys, time

SDK = os.environ.get("D1_SDK", "/sdk")
arch = platform.machine().replace("amd64", "x86_64").replace("arm64", "aarch64")
sys.path.insert(0, f"{SDK}/lib/zsl-1/{arch}")
import mc_sdk_zsl_1_py  # noqa: E402

LOCAL_IP = os.environ.get("D1_LOCAL_IP", "192.168.168.100")
DOG_IP = os.environ.get("D1_DOG_IP", "192.168.168.168")
PORT = 43988

accion = sys.argv[1] if len(sys.argv) > 1 else "check"
app = mc_sdk_zsl_1_py.HighLevel()
print(f"initRobot({LOCAL_IP}, {PORT}, {DOG_IP})", flush=True)
app.initRobot(LOCAL_IP, PORT, DOG_IP)
for _ in range(50):
    if app.checkConnect():
        break
    time.sleep(0.1)
print("conexión:", app.checkConnect(), flush=True)
for nombre in ("getBatteryPower", "getCurrentCtrlMode", "getRPY", "getPosition"):
    try:
        print(nombre, getattr(app, nombre)(), flush=True)
    except Exception as e:  # noqa: BLE001
        print(nombre, "error", e, flush=True)

if accion == "stand" and app.checkConnect():
    print("standUp()", flush=True)
    app.standUp()
    time.sleep(3)
    print("modo tras standUp:", app.getCurrentCtrlMode(), flush=True)
elif accion == "lie" and app.checkConnect():
    print("lieDown()", flush=True)
    app.lieDown()
    time.sleep(3)
