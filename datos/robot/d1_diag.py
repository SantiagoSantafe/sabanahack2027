"""Diagnóstico de la secuencia standUp → move(0,0,0) → lieDown. NO desplaza al robot (velocidad cero).
Mide el modo del robot y cuándo empieza a aceptar move(). Uso dentro del contenedor d1sdk.
"""
import os, platform, sys, time

SDK = os.environ.get("D1_SDK", "/sdk")
arch = platform.machine().replace("amd64", "x86_64").replace("arm64", "aarch64")
sys.path.insert(0, f"{SDK}/lib/zsl-1/{arch}")
import mc_sdk_zsl_1_py  # noqa: E402

app = mc_sdk_zsl_1_py.HighLevel()
app.initRobot(os.environ["D1_LOCAL_IP"], 43988, os.environ["D1_DOG_IP"])
for _ in range(50):
    if app.checkConnect():
        break
    time.sleep(0.1)
modo = getattr(app, "getCurrentCtrlmode", lambda: None)
print("conexión", app.checkConnect(), "batería", app.getBatteryPower(), "modo", modo(), flush=True)
if not app.checkConnect():
    sys.exit(1)

t0 = time.time()
print("standUp() ->", app.standUp(), flush=True)
primero_ok = None
fin = t0 + 12
while time.time() < fin:
    r = app.move(0.0, 0.0, 0.0)
    m = modo()
    if r == 0 and primero_ok is None:
        primero_ok = time.time() - t0
        print(f"  primer move(0,0,0) aceptado a los {primero_ok:.2f} s (modo {m})", flush=True)
    if int((time.time() - t0) * 10) % 5 == 0:
        print(f"  t={time.time()-t0:5.2f}s move->{r} modo={m} conexión={app.checkConnect()}", flush=True)
    time.sleep(0.02)  # 50 Hz
print("lieDown() ->", app.lieDown(), flush=True)
time.sleep(3)
print("fin · primer move aceptado:", primero_ok, "· modo final", modo(), flush=True)
