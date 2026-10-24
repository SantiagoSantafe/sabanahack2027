# Reporte: robots-competencia

Fecha: 2026-10-23. Rol: verificar las especificaciones de la línea AgiBot y mapear la competencia (robots, estaciones, startups) para el reto "Berry Good Idea".

Convenciones: **OFICIAL** = página o documento de AgiBot (o del autor). **REVENDEDOR** = tienda o distribuidor. **NO VERIFICADO** = no lo confirmé en una fuente primaria. **INFERENCIA** = lo deduzco yo de datos citados. **CÁLCULO** = derivado con fórmula a partir de un dato citado.

---

## 0. Respuestas directas a lo que se pidió confirmar (D1 EDU)

| Pregunta | Respuesta | Fuente |
|---|---|---|
| ¿IP del D1 EDU? | **No está declarado** en la ficha oficial Pro/Edu (2026-06-10), ni en la página oficial de producto, ni en la tienda oficial. Un revendedor (OpenELAB) dice **IP32** y lo atribuye genéricamente a AgiBot: NO VERIFICADO. La guía SDK oficial V2.0.7 tiene **una sola tabla para Edu y Ultra** con "IP54", sin distinguir modelo. Como la ficha del Ultra sí dice IP54 y la del Edu no dice nada, esa tabla es ambigua. **Para diseño: tratar el D1 EDU como NO protegido contra agua.** | Ficha Pro/Edu (PDF oficial); guía SDK §1.3; https://openelab.io/blogs/learn/agibot-d1-pro-vs-d1-edu-vs-d1-ultra |
| ¿Trae cámara de fábrica? | **Sí.** Ficha oficial: "一个相机，分辨率1920x1080p", DFOV 122°, HFOV 111°, VFOV 70°. El manual la llama "Front camera". La guía SDK §5.1 dice que el video de la cámara gran angular se publica por RTSP en `rtsp://192.168.234.1:8554/test` (Wi-Fi) o `rtsp://192.168.168.168:8554/test` (cable). La guía SDK escribe HFOV 122°, la ficha 111°; parece una errata. | Ficha Pro/Edu; manual Edu (sección "Component Introduction"); guía SDK §5.1 |
| ¿Cómputo cerrado? | **En la práctica, sí.** FAQ 6.20 de la guía oficial: "not recommended to deploy control logic directly on the quadruped robot body, as the robot has no spare computing capacity internally". Hay acceso SSH, y §5.6 explica cómo correr el SDK dentro del robot, pero no hay margen para un clasificador. OpenELAB dice "6 TOPS... not open for user secondary development": REVENDEDOR, NO VERIFICADO. Ficha oficial: "8-core high-performance CPU". INFERENCIA, NO VERIFICADO: el usuario SSH `firefly`, los 8 núcleos y los 6 TOPS encajan con una placa Firefly RK3588. | Guía SDK FAQ 6.20, §3.4 y §5.6 |
| ¿El SDK Python comanda posición/ruta o solo velocidad? | **Solo velocidad** en alto nivel: `move(vx, vy, yaw_rate)`, con vx 0,05–3 m/s, vy 0,1–1,0 m/s y yaw 0,02–3,0 rad/s (bajo esos mínimos el robot no se mueve). No hay "ir a punto" ni rutas. Lo que sí hay es **odometría**: `getPosition()` devuelve [x, y, z] en m en el marco de encendido, y `getWorldVelocity()` la velocidad. Cualquier ruta hay que cerrarla en lazo propio (velocidad + odometría). El bajo nivel `sendMotorCmd` va por articulación (posición/velocidad/torque) a 500 Hz y no se puede usar junto con el alto nivel. **No hay interfaz ROS** (FAQ 6.18). | Guía SDK §4.1.6, §4.1.18, §2.4, FAQ 6.16 y 6.18; README de https://github.com/AgibotTech/agibot_D1_Edu-Ultra |
| ¿URDF/MJCF público del D1? | **No hay URDF del D1 Edu/Ultra en el GitHub oficial.** El repo oficial del SDK https://github.com/AgibotTech/agibot_D1_Edu-Ultra (BSD-3-Clause) solo trae `.so`, demos y docs. `docs/D1_Edu-Ultra` es un submódulo roto, sin URL. La web oficial dice "Provides URDF modeling" y la guía dice que el SDK se pide a posventa, así que el URDF probablemente también: NO VERIFICADO. **Sí hay URDF oficial del D1 Max** (`urdf/max_description`, https://github.com/AgibotTech/Agibot_D1_Max) **y del D1 MaxPro** (`urdf/maxpro_description/urdf/maxpro.urdf` + STL, https://github.com/AgibotTech/Agibot_D1_MaxPro). Ninguno de los dos declara licencia. Hay URDF/MJCF **no oficiales** del D1 Edu: `d1_description/edu.urdf`, `edu_mujoco.urdf` y `edu_mujoco.xml` en https://github.com/Synapes-Robotics-AI-Lab/synapes-d1-pro-edu (licencia NOASSERTION), y `edu_description/urdf/edu.urdf` en https://github.com/chiway-luo/mujoco_agibot_d1 (sin licencia). | API de GitHub (árboles de repos) |
| ¿Existe "D2 Edu"? | **No encontré ningún "D2 Edu".** Sí existe la **serie D2**: el **D2 Max**, "next-generation flagship quadruped", se presentó el 2026-04-17 (APC 2026), sin ficha técnica ni fecha de venta. | §5 |

---

## 1. Qué hice

1. Descargué las páginas oficiales de producto de agibot.com: D1 Pro/Edu, D1 Ultra, D1 Max, D1 MaxPro, X2, A3, A2 Lite, G1, G2 y C5. También las de la tienda oficial store.agibot.com: D1 Edu, D1 Pro, D1 Ultra, A3 y A3 Ultra. Extraje su texto.
2. Bajé del Document Center oficial la ficha Pro/Edu, el manual del Edu, la lista de empaque, la guía SDK V2.0.7, el flyer y la ficha del D1 Ultra. Las convertí a texto con `pdftotext` y las leí.
3. Revisé con la API pública de GitHub, sin login, los repos de la organización AgibotTech: SDK D1, D1 Max, D1 MaxPro, modelos A3 y genie_sim_robot_model. También revisé repos de terceros con modelos del D1 y parseé el URDF no oficial del Edu (masas y longitudes).
4. Investigué la competencia: Saga Thorvald, el paper arXiv 2603.23112, Metos/FieldClimate, Davis, el Strawberry Advisory System de Florida, Instacrops, hexafarms, proyectos en Perú, Colombia y México, y robots de scouting en invernadero.
5. No usé la API key de Roboflow, porque no hacía falta para este rol.

---

## 2. Línea AgiBot: tabla de especificaciones

Notas: los "–" son datos que no encontré en la fuente citada. Los precios son "Sale price" de la tienda oficial en USD salvo que diga otra cosa.

### 2.1 Cuadrúpedos D1 (los que importan para el proyecto)

| Modelo | Peso | Batería / autonomía | IP | Carga | Sensores de fábrica | Cómputo | SDK | Terreno | Altura | Precio | Fuente (URL) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **D1 Pro** | 15,5 kg con batería | 4,6 Ah / 43,2 V; 1–2 h; 6 ± 1 km (1 m/s, sin carga); carga ~1 h (10→90 %) | No declarado | 5 kg | 1 cámara 1920×1080, DFOV 122°; IMU | CPU 8 núcleos | **No** ("Secondary development: Not supported"); sin puertos de expansión | Escalón 16 cm; pendiente 30° estándar / 40° límite; salto 35 cm; 3,5 m/s | De pie 635×360×420 mm; echado 145 mm | 3.200 USD | https://agibot.com/products/D1_Pro ; https://store.agibot.com/products/d1-pro |
| **D1 EDU** | 15,5 kg con batería (oficial). Un revendedor dice 15 kg. URDF no oficial: 15,19 kg | Igual que Pro | **No declarado** (ver §0) | 5 kg (un revendedor dice 8 kg máx.: NO VERIFICADO) | Igual que Pro (cámara frontal 1080p + IMU) | CPU 8 núcleos, sin margen libre (FAQ 6.20) | **Sí**: C++ y Python 3.10 en Linux. Ethernet 1 Gbps, 2×USB, 2 salidas de potencia (12 V ≤ 36 W; BAT ≤ 100 W, XT30U-M), SBUS, UART. Montaje trasero M4 | Igual que Pro. El manual prohíbe superficies "slippery, debris-covered, overly steep" | Igual que Pro | 6.080 USD | Ficha oficial Pro/Edu (PDF) ; https://store.agibot.com/products/d1-edu ; guía SDK V2.0.7 |
| **D1 Ultra** | 16 kg con batería | 4,6 Ah / 43,2 V; 1–2 h; 6 ± 1 km; 4 km con 5 kg | **IP54** | 5 kg | Cámara 1920×1080, DFOV 122° (tienda oficial) | CPU 8 núcleos (guía SDK) | Sí (mismo SDK que Edu). Mando con pantalla | 16 cm; 30°/40°; 3,7 m/s; "splashing, damp, muddy, and sandy" | 630×360×420 mm | 9.600 USD | https://agibot.com/products/D1Ultra ; ficha PDF https://www.agibot.com/file/ueditor/php/upload/file/20260825/1787637425866968.pdf ; https://store.agibot.com/products/d1-ultra |
| **D1 Ultra-W** (rueda-pata) | 22 kg (REVENDEDOR, NO VERIFICADO) | 4,6 Ah / 43,2 V; 1–2 h; 9 ± 1 km (REVENDEDOR) | IP54 (REVENDEDOR) | 5 kg (REVENDEDOR) | FPV (REVENDEDOR) | – | Sí. El SDK oficial trae `zsl-1w` "小狗轮足", con soporte desde v0.2.7 (2025-11-04) | Ruedas sólidas de 6" (REVENDEDOR) | 630×360×420 mm (REVENDEDOR) | 9.899 USD (globaldronehq) / 13.999 USD (openelab): NO VERIFICADO | Existencia OFICIAL: Document Center ("D1 Ultra/Ultra-W manual") y https://github.com/AgibotTech/agibot_D1_Edu-Ultra (demo/zsl-1w). Specs: https://globaldronehq.com/products/agibot-d1-ultra-w-quadruped-robot ; https://openelab.com/products/agibot-d1-ultra-wheeled-robot |
| **D1 Max** (rueda-pata, industrial) | 41 kg con batería | 2 × 504,9 Wh intercambiables en caliente; ≥ 5 h sin carga / ≥ 3,5 h con carga; ≥ 29 km / ≥ 18 km | **IP67**; −20 a 55 °C | 25 kg nominal (web) / 30 kg "estable" (GitHub): **conflicto entre fuentes oficiales** | 2 LiDAR de 96 líneas (Airy), 2 cámaras FPV de 8 MP DFOV 122°, 4 luces, 2 ultrasonidos (5 m), **RTK GNSS**, IMU | **NVIDIA Orin NX 16 GB, 157 TOPS** | Sí. **URDF oficial público**. ROS2 multi-máquina (docs) | Escalón 25 cm; obstáculo 80 cm; zanja 80 cm; 45°. Docs: grava, asfalto, **césped**, arena, bosque | De pie 930×480×585 mm | 42.999 USD (globaldronehq: NO VERIFICADO) | https://agibot.com/products/D1_Max ; https://github.com/AgibotTech/Agibot_D1_Max (docs/source/1.3产品参数.md) |
| **D1 MaxPro** (carga pesada) | 68 ± 1 kg (GitHub oficial). Generation Robots dice 64 kg | 2.081 Wh; 5,5 h sin carga / ≥ 2 h con 50 kg; carga ~4,5 h | **IP67**; −20 a 55 °C; vadeo 20 cm | 50 kg sostenidos | LiDAR de 96 líneas frontal; cámara frontal 1080p a 30 fps; cámara trasera 1080p | – | Sí. **URDF + STL oficiales públicos** | Escalón 30 cm; 45°; 0–1,2 m/s continuos, 3 m/s pico | 1270×520×730 mm | – | https://agibot.com/products/D1_MaxPro ; https://github.com/AgibotTech/Agibot_D1_MaxPro |

**Altura de la cámara del D1 EDU:** no aparece en ninguna fuente oficial (NO VERIFICADO). Solo sé que el robot de pie mide 420 mm en total y que el URDF no oficial tiene muslo de 0,200 m y pierna de 0,214 m, sin eslabón de cámara. INFERENCIA: el lente queda a unos 0,28–0,35 m del suelo de pie, y cambia con `attitudeControl` y el ajuste de altura. **Hay que medirlo con cinta el día de la demo.**

### 2.2 Resto de la línea AgiBot (humanoides, manipuladores y otros)

| Modelo | Qué es | Datos clave | IP | Fuente (URL) |
|---|---|---|---|---|
| **X2** | Humanoide pequeño, interacción | 1,31 m; ~35 kg; 25 GDL; cámara RGB de interacción; sin LiDAR ni RGB-D; 2 × RK3588; ~500 Wh, ~2 h a 0,5 m/s; carga ≤ 1 kg en todo el rango; **sin desarrollo secundario** | No declarado | https://agibot.com/products/X2 |
| **X2 Ultra** | X2 con percepción y desarrollo abierto | 1,31 m; ~39 kg; 30 GDL; LiDAR 3D + RGB-D + RGB frontal doble + RGB trasera; 2 × RK3588 + **Orin NX 157 TOPS**; ~500 Wh; desarrollo secundario sí | No declarado | https://agibot.com/products/X2 |
| **A3** | Humanoide de tamaño completo, "para el escenario" | 173 cm; 55 kg; 31 GDL; 2 baterías, 1.152 Wh, hasta 10 h; 0,218 kW/kg; UWB; versión estándar y versión desarrollador con el mismo hardware | No declarado | https://agibot.com/products/A3 ; https://store.agibot.com/products/a3 |
| **A3 Ultra** (nuevo, WAIC 2026) | Humanoide comercial de servicio de larga jornada | 174 cm; 60 kg; **700 TOPS**; LiDAR + RGB-D + 3 fisheye + RGB binocular; 7 GDL por brazo, 6 por pierna, 3 de cintura; manos de hasta 20 GDL; objetos de hasta 5 kg; **8 h**; autocarga y cambio de batería en 10 s; precio a consultar. URDF/MJCF oficiales en https://github.com/AgibotTech/A3-A3U-robot-model | No declarado | https://store.agibot.com/products/a3u ; https://autonews.gasgoo.com/articles/news/waic-2026-agibot-to-debut-multiple-new-products-2078355073401847808 |
| **A3 Lite** | **No existe en las fuentes oficiales.** El menú oficial lista A3, A2 Ultra y **A2 Lite**; es probable que se confunda con el A2 Lite | A2 Lite: 169 cm; ≈ 64 kg; 23 GDL ("Master of Performance") | – | https://agibot.com/products/A2_Pro (página del A2 Lite) |
| **Genie G1** | Humanoide sobre ruedas para recolección de datos y manufactura | 130–180 cm; 150 kg; 20 GDL sin efector; 3 RGBD + 5 fisheye; LiDAR en el chasis; **Jetson AGX Orin 64 GB**; 4 h+; supera obstáculos de 20 mm | No declarado | https://agibot.com/products/G1 |
| **Genie G2** | Humanoide industrial sobre ruedas, 2 brazos de 7 GDL con control de fuerza | 122,5–179,5 cm; **185 kg**; 26 GDL activos; 5 kg por brazo; 1.652 Wh, ~4 h; 1,5 m/s; 2 LiDAR 3D; Jetson T5000 (distribuidor RBTX). URDF oficial en https://github.com/AgibotTech/genie_sim_robot_model | **IP42** (oficial) | https://agibot.com/products/G2 ; datasheet RBTX https://a.storyblok.com/f/298593/x/380ef106f1/agibot_g2_technical_datasheet_rbtx_en.pdf |
| **C5** | **Robot comercial de limpieza de pisos** (barre, friega, mopa), el "First Commercial Cleaning Robot" de AgiBot. No es agrícola | Tanque de 90 L; ancho de lavado 550 mm; hasta 1.980 m²/h; 3 h de fregado; estación de autocarga y agua | – | https://agibot.com/products/C5 |

**Lectura para el proyecto:** fuera de la familia D1, nada de la línea sirve para recorrer camas de arándano. Los humanoides pesan 55–185 kg, no declaran IP o tienen IP42, y están pensados para interiores.

---

## 3. Lo que significa para la demo (D1 EDU mirando la pantalla)

1. **Video sin SDK.** El video sale por RTSP (`rtsp://<IP_robot>:8554/test`). El demo oficial `demo/zsl-1/python/examples/video.py` lo lee con `cv2.VideoCapture(url + "?tcp")`. Ese camino es solo OpenCV y debería funcionar en la Mac: NO VERIFICADO con el robot real, **probarlo primero**. Así el clasificador corre en la Mac (MPS) y el robot no carga nada.
2. **El SDK de movimiento no corre en macOS.** Las bibliotecas son `.so` de Linux: `mc_sdk_zsl_1_py.cpython-310-x86_64-linux-gnu.so` y `...-aarch64-linux-gnu.so`. Requisitos oficiales: Ubuntu 22.04, Python 3.10, Boost 1.74, y no sirve WSL. Opciones, de la más simple a la más compleja:
   - (a) Mover el robot con el mando y usar la Mac solo para video y clasificación.
   - (b) Un portátil con Ubuntu 22.04.
   - (c) Una VM Ubuntu arm64 en la Mac con red en puente: NO VERIFICADO, porque el SDK usa UDP/multicast.
   - (d) Correr un script mínimo de control dentro del robot (guía §5.6, aarch64). El clasificador nunca va ahí (FAQ 6.20).
3. **Watchdog de 3 s.** Si el robot no recibe datos del SDK durante 3 s, pasa a modo amortiguado y **se echa** (FAQ 6.9). El control debe enviar comandos a 20–50 Hz (FAQ 6.7). Si el script se cae, el perro se acuesta en plena demo.
4. **Red.** El AP Wi-Fi del robot es de 2,4 GHz, con IP 192.168.234.1 y DHCP. Por cable es 192.168.168.168, sin DHCP. Si la Mac usa el Wi-Fi del robot, pierde internet: el clima de Open-Meteo hay que **precargarlo** o traerlo por otra interfaz (cable o USB del celular). Esto último es SUPUESTO operativo y no lo probé.
5. **Distancia a la pantalla (CÁLCULO, modelo pinhole, ignora la distorsión gran angular).** Con HFOV de 111°, el ancho visible es 2·d·tan(55,5°) ≈ 2,91·d. Una pantalla de 34,5 cm a d = 0,30 m ocupa alrededor del 40 % del ancho del cuadro. Eso son unos 760 px si el stream es de 1920 px, de sobra para un clasificador de 224 px. Recomendación: pantalla a **25–35 cm**, centrada a la altura del lente (medirla), con brillo alto y sin reflejos. La resolución real del stream RTSP no está documentada; el demo graba a 800×600. NO VERIFICADO.
6. **IP y aspersor.** La propuesta pone al robot "delante del aspersor". Con el D1 EDU (IP no declarada) **no se puede mojar**. Para un despliegue real hay que nombrar el **D1 Ultra (IP54, 9.600 USD)** como mínimo, o el **D1 Max (IP67, RTK, LiDAR, Orin NX)** si se quiere navegación autónoma en campo. Conviene decirlo así en el pitch: el EDU es la plataforma de demo, no la de producción.
7. **Terreno.** El manual del Edu, en "Notes to be Observed", prohíbe "slippery, debris-covered, overly steep". Un camellón de arándano con mulch y suelo húmedo cae fuera del uso declarado del EDU. El D1 Max sí declara césped, arena y bosque.
8. **Seguridad.** La guía publica las credenciales SSH por defecto del robot (§3.4). No las copio aquí. Si el robot se conecta a una red compartida del hackathon, conviene cambiarlas.

---

## 4. ¿Existe un D2 de AgiBot?

- **Sí: la serie D2 está anunciada, con un solo modelo nombrado, el D2 Max.** El comunicado oficial del 2026-04-17 lo llama "next-generation flagship quadruped... the world's first all-terrain Level 3 autonomous" y menciona "agriculture" entre sus usos. No trae ficha técnica, precio ni fecha de venta. Fuentes: https://tools.prnewswire.com/en-us/live/20813/release/20260417EN37328 ; https://www.jiemian.com/article/14237067.html (2026-04-10, entrevista con 智元酷拓, la filial de cuadrúpedos de AgiBot: "下一代旗舰机型 D2 Max").
- **"D2 Edu": no aparece en ninguna fuente** (comunicado, Jiemian, nota de WAIC 2026 en Gasgoo, página APC2026 de agibot.com). La web oficial de productos sigue mostrando solo la familia D1 en octubre de 2026.
- En WAIC 2026 (julio) se mencionó un "quadruped riding robot" desarrollado con Haochen Technology, sin nombre de modelo (Gasgoo).

---

## 5. Competencia

### 5.1 Saga Robotics Thorvald (UV-C contra oídio)
- **No diagnostica enfermedades.** Hace **tratamiento UV-C** contra oídio en fresa (y vid) y **conteo** de flores y frutos con dos cámaras, con datos "roughly every 4 days". Su sitio no ofrece detección de enfermedad como servicio (https://sagarobotics.com/).
- Ensayo en Kent (Reino Unido), marzo a octubre de 2021: ~10,6 ha + 2 ha de fresa en túnel, sin fungicida químico contra oídio. Robot de ~200 kg, eléctrico, < 5 km/h. **Modelo robot-como-servicio: tarifa fija por hectárea** (https://futurefarming.com/tech-in-focus/field-robots/robot-combats-powdery-mildew-in-strawberries-using-uv-c-treatment).
- Flota de más de 150 robots y ronda de 11,2 M USD en 2025: solo resumen de buscador (agroempresario.com), NO VERIFICADO.
- **Para el pitch:** Thorvald trata a ciegas, por calendario, todo el lote. Nuestra propuesta detecta y localiza cama por cama. Son complementarios: la detección puede decidir dónde tratar.

### 5.2 Paper CMU, arXiv 2603.23112 (corrección: la base **no es Amiga**)
- "Active Robotic Perception for Disease Detection and Mapping in Apple Trees". Autores: Feddock, Yandun y Silwal (CMU Robotics Institute) y Aćimović (Virginia Tech, Fitopatología). IROS 2026, enviado el 2026-03-24.
- **Plataforma: Clearpath Husky A200 + brazo xArm6**, con cámara estéreo RGB e iluminación de flash en el efector (1440×1088). Segmentación de instancias **YOLO26 (Ultralytics)**. Profundidad con FoundationStereo (~30 ms). Mapa volumétrico semántico con confianza por vóxel. Tres planificadores de vista (geométrico, NBV volumétrico, NBV semántico).
- Datos: 1.275 imágenes reales anotadas, más ajuste fino con 289 de laboratorio y 849 simuladas. Enfermedad: **fuego bacteriano en manzano en dormancia**.
- Resultados a 30 vistas: en simulación, F1 0,6106 (semántico) y cobertura 85,82 % (volumétrico). En laboratorio, **F1 0,9058** (semántico) y cobertura 97,46 % (volumétrico). **Sin prueba de campo**: un árbol fabricado con 6 "shepherd's crooks" impresos en 3D. No reporta precisión ni recall por separado.
- Fuentes: https://arxiv.org/abs/2603.23112 ; https://arxiv.org/html/2603.23112
- **Para el pitch:** el estado del arte académico de 2026 en mapeo de enfermedades con robot sigue en laboratorio y simulación, con un solo cultivo y una sola enfermedad. Nuestra demo es más modesta, pero el criterio de evidencia del jurado (falsas alarmas y no detectados) es el mismo que usa este paper (F1).

### 5.3 Estaciones con modelos de enfermedad

| Plataforma | ¿Modelo para arándano? | Detalle | Fuente (URL) |
|---|---|---|---|
| **Pessl / METOS FieldClimate** | **Sí: antracnosis** (*C. acutatum*, ripe rot), con infección débil, moderada o severa según temperatura, mojadura foliar y precipitación ("12–27 °C y mojadura > 12 h"). Cita Peres et al. 2005, Wharton y Diéguez-Uribeondo 2004 y Gillett y Schilder 2009. **No cita Miles et al. 2013 ni dice que el modelo esté validado en arándano.** | Requiere estación METOS + licencia de modelos. También existe un artículo de soporte "Blueberry Botrytis cinerea" que no se renderizó; lo que sé de él (temperatura + mojadura, riesgo 0–30/30–60/60–100 %) es solo resumen de buscador: NO VERIFICADO | https://metos.global/en/disease-models-blueberry/ ; https://metos.global/en/blueberry-production-with-metos-systems/ ; https://support.metos.at/en/support/solutions/articles/15000056895-blueberry-boytrytis-cinerea (no renderizó) |
| **FieldClimate, fresa** | (No es arándano) | Antracnosis y 2 modelos de oídio, uno de ellos el **"Broome Modified Gubler"**, que **viene de vid** (Gubler-Thomas; Broome 2010). **No tiene modelo de Botrytis en fresa** en esa página. Esto respalda la regla del equipo de no usar modelos de uva como si fueran de fresa | https://metos.global/en/disease-models-strawberry/ |
| **Strawberry Advisory System (UF/IFAS, Florida)** | No (fresa) | **Antracnosis y Botrytis** en fresa con temperatura + mojadura (FAWN + pronóstico de 2 días). Alertas por email/SMS y app. Botrytis: > 6 h de mojadura y 60–72 °F; antracnosis: > 65 °F y > 12 h. Validación: "fungicide applications could be reduced by half in some years". No nombra las ecuaciones; que sean Bulger 1987 / Wilson 1990 queda NO VERIFICADO | https://ask.ifas.ufl.edu/publication/AE450 |
| **Davis Instruments (WeatherLink)** | **No encontré modelos de enfermedad para arándano** | En davisinstruments.com no hay contenido de enfermedades (búsqueda; la página agrícola dio 404). Un revendedor británico (EnviroMonitors) vende un "IPM module for grapes" y una suscripción WeatherLink Pro+ con "IPM". Davis vende el sensor de mojadura aparte. NO VERIFICADO en fuente de Davis | https://www.davisinstruments.com/pages/weatherlink-agriculture (404) ; resumen de buscador de enviromonitors.co.uk |
| **NEWA (Cornell) / Delaware** | No para arándano (en lo revisado) | Modelo de riesgo de antracnosis y Botrytis en fresa con estaciones DEOS. Solo resumen de buscador, NO VERIFICADO | sites.udel.edu/weeklycropupdate (no abierto) |
| **Instacrops (Chile)** | Dice operar en arándano entre más de 20 cultivos | Módulos solares (1 por 15 ha, cuota anual), helada temprana y "visión computacional para el control de plagas y enfermedades". 8 países de LatAm, incluido México. **La nota es de 2021** y puede estar desactualizada. Presencia en Perú: solo resumen de buscador (portalinnova.cl), NO VERIFICADO | https://dplnews.com/?p=115811 |

**Para el pitch:** el único modelo comercial de enfermedad de arándano que encontré (FieldClimate, antracnosis) usa las mismas variables que el nuestro (temperatura, mojadura, lluvia). No declara validación en arándano; el nuestro se apoya en Miles et al. 2013, que sí está validado en arándano. Además, ninguna estación **ve** la planta: dan riesgo, no hallazgos. Ese es el hueco que cubre el híbrido estación + robot.

### 5.4 Robots y drones de detección en arándano/berries en Latinoamérica

| Iniciativa | País | Qué hace | Estado | Fuente (URL) |
|---|---|---|---|---|
| Robot peruano de **conteo de frutos** de arándano (Dr. Sixto Prado Gardini, fondos Prociencia-Concytec) | Perú | Plataforma móvil + cámaras + brazo. Hasta **92 %** en detección y conteo en arándano (82 % en uva); ~5 ha/día. **No detecta enfermedad** | Prototipo (nota del 2026-09-11) | https://agraria.pe/noticias/robot-peruano-ayuda-a-predecir-la-cosecha-de-arandanos-con-m-43072 |
| "An autonomous mobile robot for monitoring and detection of **foliar fungi in blueberry** crops" (UPC, IP Guillermo Kemper) | Perú | Robot móvil autónomo para hongos foliares en arándano | Terminado (2023-12 a 2025-08), fondos internos. **Sin publicaciones listadas** | https://cris.upc.edu.pe/en/projects/an-autonomous-mobile-robot-for-monitoring-and-detection-of-foliar/ |
| Detección de oídio en hojas de arándano con YOLOv7 (Univ. César Vallejo) | Perú | Clasificación sana vs. oídio | Académico. La revista bloqueó el acceso (anti-bot), así que métricas NO VERIFICADO | revistas.ucv.edu.pe (bloqueado) |
| Tesis UNALM: dron de ala fija multiespectral en arándano (NDVI, vigor) | Perú | Zonas de bajo vigor; en campo halló larvas de *Anomala* | Académico. Solo resumen de buscador, NO VERIFICADO | https://repositorio.lamolina.edu.pe/items/edee52ed-8a21-4caf-bbcc-9a485d069881 (no abierto) |
| Detección temprana de *Botrytis cinerea* en arándano con termografía + IA (Univ. de Cundinamarca) | **Colombia** | Sistema portátil | Semillero (boletín de junio de 2025). El PDF dio error de certificado; NO VERIFICADO | https://www.ucundinamarca.edu.co/documents/comunicaciones/boletines-prensa/BOLETIN-19-06-2025.pdf (no abrió) |
| Dron con lógica difusa + redes profundas para arándano en invernadero (Javeriana) | **Colombia** | Monitoreo activo en invernadero | Académico. Solo resumen de buscador, NO VERIFICADO | apidspace.javeriana.edu.co (no abierto) |
| Sistema experto de alerta de plagas y enfermedades (UNAM + Fundación Produce Michoacán), incluye fresa | México | Alertas a partir de conocimiento experto, no de imágenes | Solo resumen de buscador, NO VERIFICADO | portalfruticola.com (no abierto) |
| Instacrops | Chile → LatAm | Sensores + alertas (§5.3) | Comercial (nota de 2021) | https://dplnews.com/?p=115811 |

**Conclusión, con cautela:** en búsquedas limitadas **no encontré ningún producto comercial en LatAm que detecte enfermedades de arándano con robot terrestre**. Lo que hay son prototipos académicos (UPC, UCV, Cundinamarca, Javeriana), un robot peruano de conteo (no sanitario) y plataformas de sensores con alertas (Instacrops, METOS). Que no lo haya encontrado no prueba que no exista.

### 5.5 Inspección y scouting de berries en invernadero (robots comerciales)

| Empresa / robot | Cultivo | Cómo se mueve | Qué detecta | Estado | Fuente (URL) |
|---|---|---|---|---|---|
| **hexafarms** (Alemania → Huelva, España) | Fresa, arándano y frambuesa (sitio); también tomate, pimiento y otros | **"Robot dogs" (cuadrúpedos) que recorren las hileras**, sin marca indicada, más "Insight Station" solar fija con cámaras (cuenta frutos y flores cada 4 h) y datos de clima, drenaje y nutrición | Color anómalo e insectos para anticipar plagas y enfermedades. Modelos activos publicados solo para pimiento (Tuta absoluta, trips) | "First robots rolling out this season". Nota del 2026-06-26 | https://www.hortidaily.com/article/9850160/sensors-ai-and-robot-dogs-patrolling-berry-greenhouses/ ; https://www.hexafarms.com/ |
| **IRIS! Scout** (Metazet-Formflex + Ecoation + Micothon) | Invernadero, configurable por cultivo | **Carro autónomo sobre riel de tubo** | Enfermedades, plagas, deficiencias, conteo y color de frutos; sensor SABER + clima, CO2 y PAR | Comercial limitado (nota de 2018) | https://www.hortidaily.com/article/6043086/scout-robot-detects-plant-abnormalities-at-an-early-stage/ |
| **Mythronics Skout** (Países Bajos) | Tomate (ToBRFV) | Autónomo en el invernadero, sin riel según la nota | Enfermedad temprana y madurez; mapa de calor por planta; ~3 ha por robot | Preventas (nota de 2023-01-09) | https://www.hortidaily.com/article/9492189/meet-skout-mythronics-latest-scouting-robot/ |
| **iUNU LUNA** | Hortalizas de hoja y ornamentales (EE. UU.) | Cámaras en riel (chasis Octiva) | Zonas problema y cosecha | Solo resumen de buscador (TechCrunch 2022), NO VERIFICADO; sin evidencia en berries | techcrunch.com (no abierto) |

**Para el pitch:** **hexafarms es el competidor más parecido a nuestra propuesta** (cuadrúpedo + estaciones fijas + clima, en berries, 2026). Eso valida el concepto híbrido, pero hay que diferenciarse. Opciones: (1) arándano en campo abierto andino, no invernadero europeo; (2) foco en evidencia de errores (sensibilidad ≥ 90 %, conteo de falsas alarmas); (3) triage y confirmación del operario con registro por cama; (4) modelos de riesgo específicos de arándano (Miles 2013) en vez de genéricos.

---

## 6. Archivos producidos

- `/Users/santiagosantafe/Downloads/SabanaHack/datos/reportes/robots-competencia.md` (este reporte)
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/agibot_docs/`: 6 PDF oficiales de AgiBot (19 MB) y `FUENTES.txt` con la URL de cada uno. Copyright de AgiBot: **no redistribuir**.
  - `D1_Pro-Edu_Spec_20260610.pdf`, `D1_Edu_User_Manual_EN.pdf`, `D1_Edu_Packing_List_20260104.pdf`, `AGIQUAD_D1_Edu_Ultra_SDK_Guide_V2.0.7.pdf`, `D1_Pro_Edu_Flyer_20260710.pdf`, `D1_Ultra_Datasheet_1787637425866968.pdf`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/raw/agibot_g2_rbtx/agibot_g2_technical_datasheet_rbtx_en.pdf` (datasheet del distribuidor RBTX; no redistribuir)

No clonar ni redistribuir los URDF de terceros: tienen licencia NOASSERTION o ninguna. El SDK oficial es BSD-3-Clause; los repos D1 Max y MaxPro no declaran licencia.

---

## 7. Fuentes abiertas (URLs que realmente consulté)

AgiBot, oficial:
- https://agibot.com/products/D1_Pro · https://agibot.com/products/D1Ultra · https://agibot.com/products/D1_Max · https://agibot.com/products/D1_MaxPro · https://agibot.com/products/X2 · https://agibot.com/products/A3 · https://agibot.com/products/A2_Pro · https://agibot.com/products/G1 · https://agibot.com/products/G2 · https://agibot.com/products/C5
- https://agibot.com/filepage/298.html (Document Center) y los PDF listados en `raw/agibot_docs/FUENTES.txt`
- https://www.agibot.com/file/ueditor/php/upload/file/20260825/1787637425866968.pdf (ficha del D1 Ultra)
- https://store.agibot.com/collections/quadruped-robot · https://store.agibot.com/products/d1-edu · https://store.agibot.com/products/d1-pro · https://store.agibot.com/products/d1-ultra · https://store.agibot.com/products/a3 · https://store.agibot.com/products/a3u
- https://github.com/AgibotTech/agibot_D1_Edu-Ultra (README, changelog, sdk_download, demos, docs/source/1.3产品参数.md) · https://github.com/AgibotTech/Agibot_D1_Max · https://github.com/AgibotTech/Agibot_D1_MaxPro · https://github.com/AgibotTech/A3-A3U-robot-model · https://github.com/AgibotTech/genie_sim_robot_model · https://api.github.com/orgs/AgibotTech/repos
- https://www.agibot.com/news/APC2026 · https://tools.prnewswire.com/en-us/live/20813/release/20260417EN37328

AgiBot, terceros:
- https://openelab.io/blogs/learn/agibot-d1-pro-vs-d1-edu-vs-d1-ultra · https://openelab.com/products/agibot-d1-ultra-wheeled-robot · https://globaldronehq.com/products/agibot-d1-ultra-w-quadruped-robot · https://a.storyblok.com/f/298593/x/380ef106f1/agibot_g2_technical_datasheet_rbtx_en.pdf
- https://github.com/Synapes-Robotics-AI-Lab/synapes-d1-pro-edu · https://github.com/chiway-luo/mujoco_agibot_d1 · https://github.com/chiway-luo/ign_robot_dog · https://github.com/skyboooox/agibot_d1_ros
- https://autonews.gasgoo.com/articles/news/waic-2026-agibot-to-debut-multiple-new-products-2078355073401847808 · https://www.jiemian.com/article/14237067.html

Competencia:
- https://arxiv.org/abs/2603.23112 · https://arxiv.org/html/2603.23112
- https://sagarobotics.com/ · https://futurefarming.com/tech-in-focus/field-robots/robot-combats-powdery-mildew-in-strawberries-using-uv-c-treatment
- https://metos.global/en/disease-models-blueberry/ · https://metos.global/en/blueberry-production-with-metos-systems/ · https://metos.global/en/disease-models-strawberry/
- https://ask.ifas.ufl.edu/publication/AE450
- https://dplnews.com/?p=115811
- https://agraria.pe/noticias/robot-peruano-ayuda-a-predecir-la-cosecha-de-arandanos-con-m-43072 · https://cris.upc.edu.pe/en/projects/an-autonomous-mobile-robot-for-monitoring-and-detection-of-foliar/
- https://www.hortidaily.com/article/9850160/sensors-ai-and-robot-dogs-patrolling-berry-greenhouses/ · https://www.hexafarms.com/ · https://www.hortidaily.com/article/9492189/meet-skout-mythronics-latest-scouting-robot/ · https://www.hortidaily.com/article/6043086/scout-robot-detects-plant-abnormalities-at-an-early-stage/

Intenté abrir estas y no pude: support.metos.at (no renderizó), revistas.ucv.edu.pe (anti-bot, no lo eludí), ucundinamarca.edu.co (error de certificado), davisinstruments.com/pages/weatherlink-agriculture (404), aap.com.au (403).

---

## 8. Límites

- Las fichas de AgiBot son de laboratorio ("based on laboratory test data") y a veces se contradicen entre documentos oficiales:
  - pendiente: 40° en la web, 30°/40° en la ficha, 30° en la tienda;
  - HFOV: 111° en la ficha, 122° en la guía SDK;
  - carga del D1 Max: 25 kg en la web, 30 kg en GitHub;
  - IP en la tabla compartida Edu/Ultra.
- No probé nada con el robot real (RTSP, SDK, latencia, resolución del stream).
- La altura de la cámara es una inferencia.
- Para la competencia en LatAm la búsqueda fue limitada (buscador web en inglés y español, sin bases de patentes ni directorios de pago). Que no aparezca un producto no prueba que no exista.
- Las métricas de los prototipos LatAm vienen de notas de prensa, no de papers revisados.
- No abrí Kaggle ni nada que pida login.

## 9. Pendientes (para el equipo)

1. **Probar el día 1**: `ffplay rtsp://192.168.234.1:8554/test` o OpenCV desde la Mac conectada al AP del robot. Anotar resolución, fps y latencia reales.
2. **Medir con cinta** la altura del lente del D1 EDU de pie y fijar la distancia a la pantalla (25–35 cm según el cálculo del §3).
3. Decidir si el robot se mueve en la demo. Si sí: conseguir Ubuntu 22.04 (portátil o VM), revisar la versión de firmware (≥ 0.2.6; ≥ 0.3.4 para alternar mando/SDK) y respetar el watchdog de 3 s.
4. En el pitch: decir que el EDU es la plataforma de demo y que la de campo es el **D1 Ultra (IP54) o el D1 Max (IP67 + RTK + LiDAR)**; mostrar el **D2 Max** como hoja de ruta.
5. Diferenciarse explícitamente de **hexafarms** (el competidor más cercano) y de **FieldClimate** (riesgo sin ver la planta).
6. Si hace falta simulación: pedir a posventa de AgiBot el URDF oficial del D1 Edu, o usar el del D1 Max (oficial) como sustituto. No redistribuir los URDF no oficiales.
