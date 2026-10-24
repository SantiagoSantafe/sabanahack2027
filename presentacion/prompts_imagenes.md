# Prompts de imágenes · Berry Good Idea (pitch Sabana Hack)

Todos los prompts están en inglés, listos para copiar (el bloque de código es lo que se pega). La línea en español de cada uno dice para qué sirve y dónde va. Formato objetivo: **16:9**.

## Cómo usarlos (30 segundos)

- **ChatGPT (imágenes):** pega el bloque tal cual. Suele entregar 1536×1024 (3:2) aunque pidas 16:9. Si sale 3:2, recorta a 16:9 en Canva (se pierde ~8 % arriba y ~8 % abajo). Por eso cada prompt deja el sujeto y el HUD en el 80 % central de la altura.
- **Midjourney:** pega el bloque y agrega al final `--ar 16:9 --style raw --stylize 150 --v 7 --no people, logo, watermark, brown spots`. Midjourney escribe mal el texto: para el HUD usa la versión "sin texto" (ver 1D) y rotula en Canva.
- **Iterar rápido:** no regeneres todo. Si algo falla, usa los arreglos de una línea de la sección 1C sobre la imagen ya generada.
- **Texto del HUD:** los generadores se equivocan en tildes y símbolos. Si no sale exacto, usa 1C-4 o escríbelo en Canva (Inter o Montserrat SemiBold, blanco sobre vidrio oscuro; caja roja coral #FF5A5F).
- **Honestidad:** el "87 %" y el "96 %" de los HUD son decorativos. Si la imagen va en una diapositiva de evidencia, rotúlala "ejemplo ilustrativo"; las cifras reales salen de `CIFRAS_CLAVE.md` (sensibilidad 0,78, falsas alarmas 0,29).
- **Estilo común:** foto realista, cinematográfica, paleta verde bosque oscuro, azul frío de madrugada, acentos blancos (LED) y verde lima (#B8E04A), como la portada de Canva.

## Mapa del deck (~5 min, 11 diapositivas) y dónde cae cada imagen

| # | Diapositiva | 5 min | Imagen / fondo | Si son 3 min | Si son 9 min |
|---|---|---|---|---|---|
| 1 | Portada · "Los ojos que llegan a la cama exacta" | 0:05 | IMG-2 | Se queda | Se queda |
| 2 | Una noche en la finca · 2 a. m., hoja mojada | 0:20 | IMG-9 | CORTA: se funde con la 3 | Se queda |
| 3 | El problema (3 cifras: 4–5 días, 10–25 %, 1 defecto) | 0:25 | IMG-3 | Se queda, más corta (con la 2) | Se queda + 1 cifra de contexto |
| 4 | La misma noche con nosotros (diagrama de una alerta) | 0:30 | IMG-1 + IMG-4 | Se queda | Se queda |
| 5 | DEMO EN VIVO (robot real, hojas en PCs, hallazgo en el dashboard) | 1:40 | Videos de fondo; IMG-4 como póster/respaldo | Se queda, 1:15 | AMPLÍA: ciclo completo sana + enferma + confirmación del operario + registro |
| 6 | El supervisor decide y envía a un operario | 0:15 | IMG-5 | CORTA: se cuenta dentro de la demo | Se queda |
| 7 | Evidencia y límites (sensibilidad 78 %, falsas alarmas 29 %, alternaria débil) | 0:25 | IMG-8A | Se queda | AMPLÍA: matriz de errores y qué mide el piloto |
| 8 | Por qué esta solución vs alternativas | 0:15 | IMG-8A | CORTA: se funde con la 9 | AMPLÍA: matriz de 6 alternativas |
| 9 | Negocio y ROI (lo más fuerte para este público) | 0:35 | IMG-8B | Se queda | AMPLÍA: sensibilidad del ROI |
| 10 | Escalabilidad (de 1 finca a muchos productores) | 0:15 | IMG-7 + IMG-6 | CORTA: una frase en el cierre | AMPLÍA: otros cultivos y multi-finca |
| 11 | Cierre: piloto, límites, "De 5 días a 5 minutos" | 0:15 | IMG-2 (eco de portada) o IMG-1 | Se queda | Se queda |

---

## 1. CORRECCIÓN · Robot entre arándanos (imagen estrella)

**Qué estaba mal en la versión actual** (`Dewy Greenhouse Robot Inspection at Dawn.png`): el robot ocupa ~20 % del ancho, el mástil mide ~0,5× la altura del cuerpo y la cámara queda casi a la altura del lomo, así que no se entiende que "ve las hojas".

**Nota de geometría (para no frustrarse):** con medidas reales (cuerpo ~63×36 cm + mástil de 1,0–1,2 m → conjunto de ~1,4–1,6 m de alto) el robot completo solo cabe en ~25–30 % del ancho de un 16:9. El prompt pide ~40 % del ancho con vista 3/4 cercana, gran angular y contrapicado leve, y el mástil casi a toda la altura del cuadro. Si el generador lo deja en ~30 %, es aceptable; si quieres más, haz zoom 120–130 % en Canva sobre el robot. La altura "~1,0–1,2 m" del mástil se mide desde el lomo; con el lomo a ~0,42 m, la cámara queda a ~1,3–1,4 m del piso, a la altura de las hojas. Las patas con "ruedas" (D1 Ultra-W) se dejan como en la imagen actual; si el D1 real que van a mostrar tiene patas sin ruedas, cambia `small black rounded wheel-foot pods` por `rounded rubber foot pads`.

### 1A. Prompt completo (generación nueva) · va en la diapositiva 4 y de eco en la 11 · 16:9 · zona libre: franja superior derecha o el 20 % superior

```
Photorealistic cinematic 16:9 wide landscape image (1792x1024), documentary look, shot inside a blueberry greenhouse in the blue hour before dawn.

HERO SUBJECT, MUST BE BIG IN THE FOREGROUND: a compact industrial quadruped inspection robot in the style of the AgiBot D1 (no logo): matte dark-grey and black body with brushed light-grey accents, four articulated legs ending in small black rounded wheel-foot pods; the body is only about 42 cm tall at the back and about 60 cm long. Three-quarter front view, close-up, from a LOW camera at the robot's back height (about 45 cm above the floor), slight upward tilt, wide 24 mm lens. The robot, with its mast, fills about 40 % of the image width (body and spread legs) and about 85-90 % of the image height. It stands on the central aisle, slightly right of center, its flank about half a meter from the plant bed on the left, its camera head turned toward the bushes on the left.

MAST, VERY IMPORTANT, CLEARLY VISIBLE AND TALL: a slim vertical black anodized aluminium mast rising from the robot's back, about 1.0-1.2 m long, roughly 2.5 times taller than the robot's own body height, reaching the height of the blueberry leaves. At the very top: a compact cylindrical 4K camera module with a bright white LED ring around the lens, at the same height as the leaves of the bush (about 1.2-1.4 m above the floor), pointing at the leaves and lighting them with a soft cool-white glow. Halfway up the mast, on a short side arm: a temperature and humidity sensor inside a white louvered radiation shield. On the robot's back at the base of the mast: one compact rectangular dark electronics box (Jetson computer) with a few neat cables running up the mast, and one short (about 25 cm) black LoRaWAN whip antenna at the rear of the back. Nothing else mounted on the robot.

PLANTS: blueberry bushes about 1.3 m tall in black plastic pots on a white ground cover, drip irrigation lines, healthy dark-green leaves covered in dew droplets, a few blue berries. On the bush closest to the mast camera, a cluster of leaves shows real powdery mildew (oidio): a matte whitish-grey powdery film on the upper side of the leaves, irregular dusty patches, clearly different from the glossy transparent dew droplets. NO brown spots, NO necrosis, NO dark lesions on any leaf.

HUD OVERLAYS (flat, crisp, semi-transparent, clean modern UI, not photographic): (1) a thin red-coral rectangle around the mildew-covered leaves with a small label above it reading exactly "Oídio · 87%"; (2) a rounded dark-glass label with white text reading exactly "Nave 2 · Cama 3 · Planta 41 · 10,4 °C · 95 % HR", joined by a thin white line ending in a small dot on the diseased plant. No other text anywhere in the image.

GREENHOUSE: translucent plastic roof with open zenithal ventilation windows, side roll-up curtains partly rolled up, galvanized steel structure. In the middle distance at the end of the aisle: a small grey PLC electrical cabinet (plain, no text, no labels) on a steel pole with a short antenna; optionally a faint thin dashed cyan line from the robot's antenna to the cabinet.

LIGHT AND MOOD: pre-dawn blue hour, cool blue-teal ambient light, heavy dew, light mist, wet white ground cover with soft reflections; the camera's white LED ring is the only warm-white light. Sharp focus on the robot and the mildew leaves, soft background. Photorealistic, natural color, fine micro-detail.

EXCLUDE: people, logos, brand names, watermarks, any text other than the two HUD labels, spraying equipment, humanoid parts, extra legs (exactly four legs), a small or distant robot, a short mast.
```

### 1B. Versión de EDICIÓN · sube la imagen ya generada a ChatGPT y pega esto · 16:9

**EDIT-COMPLETA** (corrige el robot pequeño y el mástil corto sin cambiar el resto):

```
Edit the attached image. Keep the same greenhouse, the same blue-hour dewy atmosphere, the same blueberry bushes, the same style of HUD overlays and the same robot design (dark-grey/black quadruped), but fix the proportions and the composition:

1) SCALE: the robot is far too small (about 20 % of the image width). Re-frame as a close-up hero shot: move the camera much closer and lower (at the robot's back height, about 45 cm above the floor, slight upward tilt, wide 24 mm look) so that the robot together with its mast fills about 40 % of the image width and 85-90 % of the image height. Keep it on the aisle, slightly right of center, with its camera head turned toward the bushes on the left.
2) MAST: the mast is far too short (about half the robot's body height). Replace it with a clearly visible, slim, vertical black mast about 1.0-1.2 m long (about 2.5 times the height of the robot's body) rising from the robot's back. At its top: a compact 4K camera with a bright white LED ring, at the height of the bush leaves (about 1.2-1.4 m above the floor), pointing at the leaves and lighting them. Halfway up the mast: a temperature and humidity sensor in a white louvered radiation shield. On the robot's back: a compact dark electronics box (Jetson computer) and a short LoRaWAN whip antenna.
3) LEAVES: the leaves inside the red box must show real powdery mildew only: a matte whitish-grey powder on the upper leaf surface, absolutely no brown spots anywhere.
4) HUD: keep the red box with the label exactly "Oídio · 87%" and the label exactly "Nave 2 · Cama 3 · Planta 41 · 10,4 °C · 95 % HR", joined to the plant by a thin line. Text crisp and spelled exactly like this.
5) KEEP: black pots on white ground cover, drip lines, dew, side roll-up curtains, zenithal windows, a plain grey PLC cabinet without any text on a pole. No people, no logos, no other text.
Output 16:9 wide.
```

**EDIT-CORTA** (si solo quieres empujar tamaño y mástil, 1 iteración rápida):

```
Edit the attached image: make the robot about twice as big in the frame (close-up, low camera at the robot's back height, robot with mast filling about 40 % of the width), and replace the short mast with a tall slim vertical black mast about 2.5 times the height of the robot's body, with the 4K camera and white LED ring at the top at the height of the bush leaves and the white-shielded temperature/humidity sensor halfway up. Remove any brown spots from the leaves (powdery mildew is white powder only). Keep everything else, including the two HUD labels with their exact text. 16:9.
```

### 1C. Arreglos de una línea (se pegan sobre la imagen ya generada)

1. Robot aún pequeño: `Zoom in: make the robot and mast about 30 % bigger and crop tighter; keep everything else identical.`
2. Mástil aún corto o flaco: `Make the mast twice as tall and slightly thicker (about 4 cm), keep the camera with its white LED ring at the top at leaf height; keep everything else identical.`
3. Manchas cafés: `Remove every brown or dark spot from all leaves; the mildew leaves must have only matte white powder on the upper surface. Keep everything else identical.`
4. Texto del HUD mal escrito: `Fix only the text of the two HUD labels so they read exactly "Oídio · 87%" and "Nave 2 · Cama 3 · Planta 41 · 10,4 °C · 95 % HR" (with the accent on Í, comma in 10,4, a space before the percent sign in 95 % HR). Do not change anything else.`
5. Etiqueta sin línea a la planta: `Connect the data label to the diseased plant with a thin white line ending in a small dot on the leaves; keep everything else identical.`
6. Falta el sensor o la caja: `Add a temperature/humidity sensor in a white louvered shield halfway up the mast and a compact dark electronics box on the robot's back with a short antenna; keep everything else identical.`
7. Aparece gente o logos: `Remove all people, logos and any text other than the two HUD labels; keep everything else identical.`
8. Patas de más o robot deforme: `Make the robot have exactly four legs and a clean compact body like a quadruped robot dog; keep everything else identical.`

**Lista de chequeo (10 s):** robot ≥ 30–35 % del ancho; mástil ≥ 2× la altura del cuerpo; cámara con aro LED a la altura de las hojas; sensor T/HR con protector blanco a media altura; caja Jetson y antena LoRa corta en el lomo; solo polvo blanco, cero manchas cafés; los dos textos del HUD exactos; cuatro patas; PLC gris sin texto; sin personas ni logos.

### 1D. Versión Midjourney y versión SIN texto (para rotular en Canva) · 16:9

```
Photorealistic cinematic wide shot inside a blueberry greenhouse in the blue hour before dawn, heavy dew. Foreground hero: a compact quadruped inspection robot in the style of the AgiBot D1, matte dark-grey and black, four legs with small wheel-foot pods, 42 cm tall body, three-quarter front view, low camera at the robot's back height, wide 24 mm lens, robot with mast filling 40 % of the frame width. A tall slim vertical black mast, 2.5 times the body height, rises from its back and carries at the top a 4K camera with a bright white LED ring at the height of the bush leaves; a temperature and humidity sensor in a white louvered shield halfway up the mast; a compact electronics box and a short whip antenna on the back. Blueberry bushes in black pots on white ground cover, leaves with dew, the nearest leaves covered with matte white powdery mildew, no brown spots. Two empty flat HUD frames: a thin red-coral rectangle around the mildew leaves with a small blank label above it, and a rounded dark-glass blank label joined by a thin line to the plant. Plastic roof with open vent windows, roll-up side curtains, a plain grey PLC cabinet without text on a pole in the distance. Cool blue-teal light, mist, cinematic, sharp, natural color --ar 16:9 --style raw --stylize 150 --v 7 --no people, logo, watermark, text, brown spots, extra legs
```

Texto para Canva sobre los recuadros vacíos: caja roja `Oídio · 87%`; etiqueta `Nave 2 · Cama 3 · Planta 41 · 10,4 °C · 95 % HR`.

---

## 2. Imágenes del pitch

### IMG-2 · Portada (fondo oscuro con robot y hojas) · diapositiva 1 (eco en la 11) · 16:9 · zona libre: mitad IZQUIERDA (título blanco "BERRY GOOD IDEA" + subtítulo)

```
Photorealistic cinematic 16:9 cover image (1792x1024). A very dark forest-green night scene, a smooth near-black green gradient (#06180F to #0D3B26). On the RIGHT third of the frame: a compact quadruped inspection robot in the style of the AgiBot D1 (no logo), matte dark-grey and black, four legs with small wheel-foot pods, body about 42 cm tall, seen in a three-quarter front view from a low camera angle, with a slim vertical black mast about 2.5 times the height of its body that carries at the top a 4K camera with a glowing white LED ring, a small white-shielded temperature and humidity sensor halfway up the mast, a compact electronics box and a short antenna on its back. The robot with its mast fills about 85 % of the frame height. The LED ring lights a branch of dark glossy blueberry leaves with dew drops and a few frosty blue berries that frame the right edge of the image. Out-of-focus dark blueberry bushes and greenhouse structure behind, soft mist. Flowing luminous lime-green (#B8E04A) wave lines, like elegant light trails or topographic contour waves, sweep from the lower left across the bottom of the frame toward the robot, subtle and slightly glowing. The LEFT 50 % of the image must be clean negative space: a smooth very dark green gradient with only faint mist and very subtle waves, no objects, ready for a big white title. Mood: premium, technological, calm, agtech keynote. No text, no logos, no people, no watermark.
```

### IMG-3 · "Antes": operario con linterna y planilla de papel, de madrugada · diapositiva 3 (problema) · 16:9 · zona libre: 40 % IZQUIERDO, oscuro

Nota: ya tienes una versión en Descargas (`Dawn Inspection in the Blueberry Greenhouse.png`, amanecer). Este prompt la rehace en noche cerrada (2 a. m.), con espacio para las tres cifras.

```
Photorealistic cinematic 16:9 image (1792x1024). 2 a.m. inside a blueberry greenhouse at night. An anonymous farm worker, partly turned away, face half in shadow and not identifiable, in a dark wet rain jacket, rubber boots and a cap, walks along a narrow wet aisle holding a small flashlight in one hand, its warm-white beam lighting a few dew-covered leaves, and a paper checklist on a clipboard in the other hand (printed grid sheet, no legible text, a pen tucked in). Blueberry bushes in black pots on white ground cover on both sides, drip lines, galvanized greenhouse structure, translucent plastic roof, fog and cold breath visible in the beam. Cold, tired, lonely mood: deep blue-black night with a single pool of warm flashlight light, high contrast, slightly grainy low-light photo look. The worker stands in the RIGHT third of the frame; the LEFT 40 % of the frame is dark, soft and mostly empty (blurred rows fading into darkness) to receive large white text. Eye-level shot, 35 mm lens, shallow depth of field. No logos, no readable text, no watermark, no other people.
```

### IMG-4 · Primer plano de hoja con oídio vista por la cámara del robot (HUD) · diapositivas 4 y 5 (póster/respaldo del video de la demo) · 16:9 · zona libre: 40 % DERECHO (follaje borroso oscuro)

```
Photorealistic 16:9 image (1792x1024) simulating the first-person view from the robot's 4K camera: an extreme close-up of blueberry leaves at 20-30 cm distance, sharp focus on a leaf with real powdery mildew (oidio): a matte whitish-grey powdery film on the upper surface in irregular dusty patches, clearly different from the glossy transparent dew droplets on the neighbouring healthy green leaves; no brown spots, no necrosis. Soft cool-white LED ring light from the camera lights the leaves from the front; pre-dawn blue-teal background melting into creamy bokeh with a few out-of-focus blue berries.
Camera-view HUD overlay, flat crisp modern UI: thin white viewfinder corner brackets near the edges and a small crosshair; a red-coral rectangle tightly around the mildew patch with a label above it reading exactly "Oídio · 87%"; and a slim dark-glass data strip at the lower left reading exactly "Nave 2 · Cama 3 · Planta 41 · 10,4 °C · 95 % HR". No other text.
Composition: the diseased leaf and its box in the LEFT 55 % of the frame, the RIGHT 40 % is dark blurred foliage with low detail, kept free for slide text. Macro look, 85 mm, f/2.8.
```

**IMG-4B · Variante hoja SANA** (para mostrar el contraste sana/enferma, la rúbrica lo pide) · mismo uso y zona libre:

```
Photorealistic 16:9 image (1792x1024) simulating the first-person view from the robot's 4K camera: an extreme close-up of a perfectly healthy blueberry leaf, glossy dark green, with clean dew droplets, no powder, no spots, at 20-30 cm distance, lit softly by a cool-white LED ring, pre-dawn blue-teal creamy bokeh background. Flat crisp HUD overlay: thin white viewfinder corner brackets, a small crosshair, a green (#3DDC84) rectangle around the leaf with a label above it reading exactly "Sana · 96 %", and a slim dark-glass data strip at the lower left reading exactly "Nave 2 · Cama 3 · Planta 12 · 10,6 °C · 94 % HR". No other text. The leaf and its box in the LEFT 55 % of the frame; the RIGHT 40 % dark blurred foliage, low detail, free for slide text. Macro look, 85 mm, f/2.8.
```

### IMG-5 · Supervisor con tablet viendo el mapa de focos, operario al fondo · diapositiva 6 · 16:9 · zona libre: 35–40 % DERECHO (neblina e invernadero desenfocado)

```
Photorealistic 16:9 image (1792x1024). Early morning at the entrance of a large blueberry greenhouse. In the left foreground, an anonymous adult farm supervisor (three-quarter back and side view, not identifiable, plain dark-green fleece vest and cap) holds a modern tablet in both hands and looks at it. The tablet screen is clearly visible and glowing: a dark-themed dashboard with a top-down floor plan map of a greenhouse block (long parallel greenhouse naves seen from above, with a wide central path), two red glowing hotspot circles and one amber circle on the map, small green dots on healthy zones, and a side column of small cards with colored tags; all interface text is illegible placeholder marks, no readable words or numbers. In the background, out of focus, a field worker in a rain jacket, rubber boots and cap walks away toward the greenhouse entrance with a small flashlight, as if just dispatched. Cool blue-hour light turning into pale dawn, mist, wet ground; the tablet glow is the brightest, cleanest element. Supervisor and tablet on the left 45 % of the frame, the worker small in the middle-right distance, the RIGHT 35-40 % is soft misty greenhouse and sky, mostly empty, reserved for text. 35 mm lens, shallow depth of field. No logos, no readable text, no watermark.
```

### IMG-6 · Base de carga del robot · diapositiva 10 (junto a IMG-7) o como apoyo en la 4 · 16:9 · zona libre: 35 % IZQUIERDO

```
Photorealistic 16:9 image (1792x1024). A compact quadruped inspection robot in the style of the AgiBot D1 (no logo), dark-grey and black, four legs with small wheel-foot pods, body about 42 cm tall, with a slim vertical black mast about 1.0 m tall carrying a 4K camera with a white LED ring on top, a temperature and humidity sensor in a white louvered shield halfway up the mast, and a small electronics box and a short antenna on its back, is docked on its charging station: a low sturdy dark-metal and grey pad with side guide rails and a small green status LED glowing, a thick cable running to a weatherproof grey cabinet. Location: the head of a greenhouse block where the central gravel path meets the naves, under a small roofed lean-to with a galvanized frame, next to a steel pole carrying a plain grey PLC electrical cabinet (no text) and a short LoRaWAN antenna. Pre-dawn, cool blue ambient light; the green LED and one soft warm-white work light are the only accents; wet ground; rows of blueberry greenhouse naves fading into mist in the background. The robot is center-right and fills about 35 % of the frame width with the mast fully visible; the LEFT 35 % is low detail and dark, reserved for text. Low camera angle, 35 mm lens. No people, no logos, no text, no watermark.
```

### IMG-7 · Plano aéreo del bloque: dos bloques y camino central · diapositiva 10 (escalabilidad) · 16:9 · zona libre: cielo, franja superior 25 %, y el 30 % IZQUIERDO

Nota: proporciones esquemáticas (naves más cortas de lo real para que se lea); no la uses como plano a escala. Naves 1–2 forman el Bloque 1 y naves 3–4 el Bloque 2; el camino central (5–6 m) es perpendicular a las naves. Rotula "Bloque 1", "Bloque 2" y "Camino central" en Canva.

```
Photorealistic aerial drone photo, 16:9 (1792x1024), oblique 50-60 degree view in soft early-morning light with a little mist, looking along the length of four long greenhouse naves of a blueberry farm (translucent plastic roofs, roll-up side curtains, open roof vent windows, insect-mesh sides) arranged in TWO BLOCKS. Block 1 is two parallel naves side by side in the foreground; Block 2 is two parallel naves side by side beyond, each one continuing the line of the nave in front of it. Between the two blocks runs a wide straight light-gravel CENTRAL PATH, perpendicular to the length of the naves, about the width of a small truck lane, clearly separating the blocks. At the junction of the central path and the naves: a small roofed shelter with a robot charging station, a steel pole with a plain grey PLC cabinet, and a tiny quadruped robot with a mast walking on the path as a scale reference. Around: green highland savanna plain, a farm access road, a few trees, distant mountains, nothing else. Stylized proportions: each nave only about 5 times longer than wide so the layout reads clearly. Subtle flat graphic overlay: a thin lime-green (#B8E04A) outline around each block, two or three small glowing red dots on different naves marking disease hotspots and a few small green dots; no text. Composition: blocks centered and filling the lower 65 % of the frame; the upper 25 % is clean sky, and the left 30 % is soft, low-detail field, both kept free for text. No people, no logos, no text, no watermark.
```

**IMG-7B · Variante esquemática (isométrica limpia, para fondo oscuro):**

```
Clean isometric 3D render, 16:9 (1792x1024), on a deep forest-green background (#07200F). Two blocks of long narrow greenhouse naves, two naves per block (Block 1 on one side, Block 2 on the other), separated by a wide light-grey central path perpendicular to the naves; translucent roofs, thin white outlines, soft shadows, a small charging station and a grey cabinet at the junction, a tiny dark quadruped robot with a mast on the path; two glowing red hotspot dots and a few green dots on the naves; thin glowing lime-green (#B8E04A) outline around each block. Minimal, elegant, no text, no logos. The layout occupies the right 60 % of the frame; the left 40 % is empty dark green for text.
```

### IMG-8 · Fondos abstractos para diapositivas de datos · diapositivas 7, 8 y 9 · 16:9 · zona libre: 70–80 % del cuadro

**IMG-8A · Claro** (diapositivas de contenido en blanco: evidencia, alternativas):

```
Abstract minimalist 16:9 background (1792x1024) for business presentation slides: pure white fading to a very light mint-grey (#F6FAF7), with extremely subtle, elegant line patterns inspired by blueberry leaf veins and topographic contour waves, in very pale green (#DDEBE1) at 6-8 % contrast, concentrated in the bottom-right corner and fading to clean white toward the center and the left; a few tiny soft lime-green (#B8E04A) light dots. No objects, no text, no logos, no people, no hard edges, no strong gradients. At least 75 % of the frame is clean white space for charts and text. Flat graphic design, no photographic elements.
```

**IMG-8B · Oscuro** (negocio y ROI, o cierre; hace resaltar las tarjetas con cifras grandes):

```
Abstract minimalist 16:9 background (1792x1024) for business presentation slides: a smooth very dark forest-green gradient (#07200F to #0E3B26), with thin elegant glowing lime-green (#B8E04A) wave lines (topographic contour waves and faint leaf-vein patterns) flowing along the bottom edge and fading upward, a few soft out-of-focus lime bokeh dots, subtle grain. No objects, no text, no logos, no people. At least 70 % of the frame is clean dark space for large white numbers and cards. Flat graphic design, no photographic elements.
```

### IMG-9 · (Extra) Gancho: hoja mojada a las 2 a. m. · diapositiva 2 · 16:9 · zona libre: 45 % IZQUIERDO

```
Photorealistic macro photograph, 16:9 (1792x1024), of a single blueberry leaf inside a greenhouse at 2 a.m., covered in dew and guttation droplets along its edge and surface, glistening in a narrow warm-white flashlight beam coming from the upper left; deep blue-black out-of-focus background with faint greenhouse structure and mist; a thin film of water, tiny bright reflections on the droplets; the leaf is perfectly healthy, no spots; cold, silent, tense mood. The leaf fills the RIGHT 50 % of the frame; the LEFT 45 % is dark and blurred, reserved for large white text. 100 mm macro, f/2.8. No people, no text, no logos, no watermark.
```

---

## 3. Resumen rápido (qué pegar primero)

1. **IMG-1** (sección 1A, o 1B si ya tienes la imagen): resuelve el robot pequeño y el mástil corto.
2. **IMG-2** portada, **IMG-4** (+4B) HUD y **IMG-3** antes: las tres que más se notan.
3. Fondos (**IMG-8A/8B**) y **IMG-7** aéreo: se generan en una pasada.
4. **IMG-5**, **IMG-6** y **IMG-9**: cuando haya tiempo.
