# Sistema visual · Berry Good Idea (deck 16:9, LAYOUT_WIDE 13,333 × 7,5 in)

Estado: validado. Los tipos 1 a 8 y las variantes 2B, 6L y 7L (incluido el gráfico con escala logarítmica) se construyeron y renderizaron en `kit_visual.js` (misma carpeta): pasa `validate.py` y se revisó a ojo en LibreOffice. Sin renderizar, pero con los mismos números: tipo 3 claro y de 3 pasos, tipo 5 oscuro o con imagen. Probado aparte con `validate.py` y render: combo de barras apiladas con línea. Para construir el deck, copiar de `kit_visual.js`; este documento explica el porqué y fija los números. Contenido y cifras: `guion_slides.md` y `CIFRAS_CLAVE.md` (fuente de verdad), no este archivo.

## 0. Decisiones en breve

Alcance de contenido (`INSTRUCCIONES.md`, manda sobre guiones): no hay modelo de negocio; ninguna diapositiva muestra ROI, payback, margen, suscripción ni ingresos. El tipo 7 sigue existiendo como plantilla visual de "costo del hardware y lo que está en juego". Lema: "De 8 días hábiles a minutos".

1. Verde bosque dominante, lima como único acento, ámbar solo para alerta, falsas alarmas y límites. Todo lo demás es blanco y menta.
2. Dos fuentes de la lista segura: Arial (títulos y cifras, negrita, mayúsculas) y Calibri (cuerpo).
3. Un solo motivo: el anillo de hallazgo (círculo con punto), que marca "aquí, nave, cama, planta". Nada de barras ni líneas bajo títulos.
4. Sandwich oscuro-claro-oscuro: portada, demo y cierre oscuros con video; problema, evidencia y negocio claros.
5. Cada video es un rectángulo `VIDEO_<id>` que el equipo reemplaza; cada imagen generada es `IMAGEN_<id>`.
6. Gráficos siempre nativos de PowerPoint, sobre fondo claro, con la misma tipografía y colores en todos.

## 1. Paleta (hex sin `#`)

| Token | Hex | Slot del tema (`pres.SchemeColor`) | Uso | Contraste |
|---|---|---|---|---|
| BOSQUE_900 (dominante) | `0B2B1C` | `text1` (dk1) | Fondo de diapositivas oscuras; texto y títulos sobre claro | Con blanco 15,3:1 |
| BOSQUE_700 | `14452D` | `text2` (dk2) | Marco de video, nodos, superficies sobre oscuro | Con blanco 10,9:1 |
| BOSQUE_950 | `07170F` | `accent5` | Velos y tarjetas de cristal (siempre con transparencia) | n/a |
| LIMA (acento) | `B8F04A` | `accent2` | Cifras y rótulos SOBRE oscuro; anillos; pastillas. Nunca como texto sobre blanco | Sobre BOSQUE_900 11,3:1 |
| HOJA (apoyo 1) | `1E7A46` | `accent1` | Acento sobre claro: kicker, marcador, barra de "nuestro" resultado | Sobre blanco 5,3:1 |
| ÁMBAR (apoyo 2) | `F2A33A` | `accent3` | Alerta: falsas alarmas, límites, anillos de dato clave sobre gráficos. Máximo 5 % del área | Sobre BOSQUE_900 7,3:1 |
| ÁMBAR_TXT | `8F4D05` | solo hex (texto) | Texto ámbar sobre claro (rótulo de límites) | Sobre menta 5,8:1 |
| MENTA | `EAF5E1` | `background2` (lt2) | Tarjetas sobre blanco | n/a |
| BLANCO | `FFFFFF` | `background1` (lt1) | Fondo de diapositivas claras; texto sobre oscuro | n/a |
| GRIS_VERDE | `B8C7BD` | `accent4` | Texto secundario sobre oscuro; barras neutras (alternativas) | Sobre BOSQUE_900 8,7:1 |
| TEXTO_SEC | `4A5F53` | `accent6` | Texto secundario, pies y fuentes sobre claro | Sobre blanco 6,9:1 |
| REJILLA | `DCE9D5` | solo hex | Rejilla de gráficos | n/a |

Reparto: oscuras = 70 % bosque, 25 % cristal/video, 5 % lima. Claras = 80 % blanco, 15 % menta, 5 % hoja/bosque.

Tema para `applyTheme`: `dk1 0B2B1C, lt1 FFFFFF, dk2 14452D, lt2 EAF5E1, accent1 1E7A46, accent2 B8F04A, accent3 F2A33A, accent4 B8C7BD, accent5 07170F, accent6 4A5F53, hlink 1E7A46, folHlink 4A5F53`. Las opciones que solo aceptan hex (`shadow.color`, `valGridLine.color`, `chartColors` con varios colores, colores de texto de gráficos) usan el mapa `HEX` del kit.

Aviso: el panel web usa su propia paleta (azul marino, verde azulado, dorado). En las diapositivas con su video se enmarca como "producto" (marco redondeado con sombra) y no se recolorea. Los gráficos del deck NO usan ese azul: lo nuestro va en HOJA (en LIMA sobre oscuro) y las alternativas en GRIS_VERDE.

## 2. Tipografía

| Elemento | Fuente | Tamaño | Notas |
|---|---|---|---|
| Título de diapositiva | Arial (fuente de títulos del tema) | 36 pt negrita, MAYÚSCULAS | Una línea, máx. 38 caracteres. Alineado a la izquierda |
| Título de portada / cierre | Arial negrita | 72 pt (portada), 60 pt (cierre) | Salto de línea manual, interlineado 0,9 |
| Kicker (rótulo sobre el título) | Calibri negrita | 12 pt, `charSpacing: 4`, mayúsculas | 14 pt en portada |
| Cifra héroe en tarjeta | Arial negrita | 66 pt + unidad en run de 26 pt | Máx. 5 caracteres antes de la unidad |
| Cifra de KPI | Arial negrita | 48 pt + unidad 20 pt | |
| Pie de video (caption) | Arial negrita | 28 pt, máx. 8 palabras, 2 líneas | Salto de línea manual para equilibrar |
| Subtítulo de portada y cierre | Calibri | 24 pt | |
| Encabezado de bloque | Calibri negrita | 18 a 20 pt | |
| Cuerpo | Calibri | 16 pt (14 pt mínimo) | Máx. 15 palabras por bloque |
| Límites obligatorios | Calibri | 12 a 14 pt | Texto fijo de `CIFRAS_CLAVE.md` §6 |
| Pie, fuente, nota | Calibri | 10 pt | Siempre con fuente en tarjetas de cifras |
| Pie de página y número | Calibri negrita / regular | 10 pt, `charSpacing: 4` | Solo en diapositivas claras y oscuras de contenido |

Justificación: Arial negrita en mayúsculas es lo más cercano, dentro de la lista segura, al estilo Canva actual del equipo (sans geométrica, pesada) y mide igual en PowerPoint y en el render de verificación; Calibri da densidad legible en cuerpo. Dos fuentes encajan en el tema (`headFontFace`, `bodyFontFace`). Para ganar sensación premium sin otra fuente: mucho aire, cifras muy grandes, kickers espaciados y fotografía con velo, no adornos.

Reglas de longitud medidas en el render: kicker de tarjeta de cifras ≤ 20 caracteres; etiqueta de KPI ≤ 24 caracteres; título ≤ 38 caracteres; descripción de nodo (2,0 in de ancho) ≤ 12 palabras.

## 3. Lienzo, márgenes y rejilla

- Lienzo 13,333 × 7,5 in. Margen izquierdo 0,67; derecho 0,66 (borde de contenido x = 12,67); ancho útil 12,0.
- Verticales: kicker y 0,55 (h 0,28); título y 0,88 (h 0,8); zona de contenido y 1,95 a 6,45; pie y 6,75 (h 0,25), con margen inferior de 0,5.
- Rejilla de 12 columnas, canalón 0,3: tres tarjetas de 3,8 en x = 0,67 / 4,77 / 8,87; dos mitades de 5,85; 7,6 + 4,1 (gráfico + tarjeta, x = 0,67 y 8,57); 7,9 + 3,8 (gráfico + tarjeta, x = 0,67 y 8,87). Cinco nodos con paso de 2,5 (ancho 2,0, hueco 0,5).
- Espacio entre bloques: 0,3 siempre. Padding interno de tarjeta: 0,35.
- Pie (en el diseño `CLARO` y `OSCURO`): "BERRY GOOD IDEA" en x 0,67; número de diapositiva en x 11,67, w 1,0, a la derecha. En `MEDIA` (portada, video a pantalla completa, cierre) no hay pie ni número: el video los cubre.
- Diseños (`defineSlideMaster`): `CLARO` (fondo blanco), `OSCURO` (fondo BOSQUE_900), `MEDIA` (fondo BOSQUE_900, sin pie). Los placeholders `kicker` (tipo body) y `title` (tipo title) viven en el diseño con `align: 'left'` explícito (si no, el título sale centrado).

## 4. Motivo único: el anillo de hallazgo

Un círculo sin relleno con un punto sólido al centro: "el punto exacto donde aparece el hallazgo". Se repite así, y solo así:

| Dónde | Forma | Valores |
|---|---|---|
| Marcador del kicker (todas las diapositivas con kicker) | Anillo d 0,20 (línea 1,5 pt) + punto d 0,08 | En x 0,67, y 0,60 (y = y del kicker + 0,05 en otras posiciones). Color HOJA en claro, LIMA en oscuro |
| Marcador en tarjetas | Igual, en (x+0,35, y+0,40) | Igual |
| Decoración a sangre (portada, cierre, flujo) | 2 o 3 anillos concéntricos sin relleno | Ver fichas 1, 3 y 8. Sobresalen del borde a propósito |
| Nodo numerado (flujo y puntos) | Anillo grande con icono o número | Línea 2 pt LIMA (oscuro) o 1,75 pt HOJA (claro) |
| `PING_<id>` sobre el hallazgo | Anillo d 0,5 a 1,1, línea 2,5 a 3 pt, sin transparencia | LIMA sobre video; ÁMBAR sobre gráfico de claro. Se posiciona a mano sobre el hallazgo |

Prohibido en todo el deck: barras o franjas de color, línea bajo el título, borde en un solo lado de una tarjeta, degradados nativos (no existen en pptxgenjs).

## 5. Transparencia, líneas y sombras (valores válidos en pptxgenjs)

Transparencia: `fill: { color, transparency: 0-100 }` (0 opaco, 100 invisible). Nunca 8 dígitos en el hex. En líneas: `line: { color, width, transparency }`. Sin relleno: `fill: { type: 'none' }`; sin línea: `line: { type: 'none' }`.

| Capa | Color | Transparencia | Rango permitido |
|---|---|---|---|
| Velo de portada y cierre | BOSQUE_950 | 40 (portada), 35 (cierre) | 30 a 55; subir opacidad si el video es muy claro |
| Velo de video de demo | BOSQUE_950 | 80 | 70 a 90 (la demo debe verse limpia) |
| Velo sobre imagen de problema (variante 2B) | BOSQUE_950 | 45 | 35 a 55 |
| Tarjeta de cristal y pastilla sobre video | BOSQUE_950 | 25 (límites del cierre: 18) | 15 a 35 |
| Anillos decorativos sobre oscuro | LIMA | línea 70 / 55 / 35 (de afuera adentro); sobre flujo: 88 | 30 a 90 |
| Flecha del flujo | LIMA 1,5 pt | 30 | 20 a 40 |
| Todo lo demás (tarjetas, KPI, texto) | sólido | 0 | n/a |

Sombras (`shadow`, siempre un objeto nuevo por llamada: usar las fábricas `shCard()` y `shVideo()` del kit):

| Nombre | Valor | Dónde |
|---|---|---|
| SHADOW_CARD | `{ type: 'outer', color: '0B2B1C', blur: 16, offset: 4, angle: 90, opacity: 0.12 }` | Tarjetas y KPI sobre fondo claro |
| SHADOW_VIDEO | `{ type: 'outer', color: '000000', blur: 24, offset: 8, angle: 90, opacity: 0.30 }` | Marco de video a la mitad (tipo 5) |
| Sobre oscuro | sin sombra | Las superficies se separan por color o cristal |

Reglas: `offset` ≥ 0; `opacity` 0 a 1 (no 0 a 100); `color` en hex; un ángulo hacia arriba se escribe `angle: 270` con offset positivo; `blur` en puntos (0 a 100).

Esquinas: `ROUNDED_RECTANGLE` con `rectRadius` en pulgadas: 0,12 tarjetas y marcos; 0,14 cristal; pastillas = mitad de su alto (0,18 a 0,22). Nada de `rectRadius` en `RECTANGLE`.

## 6. Marcos `VIDEO_<id>` e `IMAGEN_<id>`

| | VIDEO_<id> | IMAGEN_<id> |
|---|---|---|
| Forma | Rectángulo (a sangre) o redondeado r 0,12 (a la mitad) | Igual |
| Relleno | BOSQUE_700 `14452D` (`text2`) | HOJA `1E7A46` (`accent1`) |
| Línea | LIMA 1,5 pt discontinua (`dashType: 'dash'`) | BLANCO 1,5 pt discontinua |
| Rótulo (dentro de la forma) | "Inserta aquí el video: <qué se ve, duración, sin audio>" | "Reemplaza con imagen: <qué se ve>" |
| Texto del rótulo | Blanco 12 pt arriba al centro (a sangre) o 16 pt centrado (a la mitad) | Igual |
| Nombre de objeto (`objectName`) | `VIDEO_portada`, `VIDEO_gancho`, `VIDEO_demoA`, `VIDEO_demoB`, `VIDEO_panel`, `VIDEO_sim`, `VIDEO_cierre` | `IMAGEN_problema`, `IMAGEN_hoja`, `IMAGEN_plataforma`, `IMAGEN_icono_pasoN` |
| Z-orden | Primero en el código (capa más baja); velo y textos encima | Igual |

Los iconos pequeños (`IMAGEN_icono_pasoN`, 0,5 × 0,5 in) no llevan rótulo; se sustituyen por PNG de react-icons en LIMA (≥ 256 px).

Cómo lo reemplaza el equipo:

1. Video: seleccionar el marco, anotar posición y tamaño (Formato de forma > Tamaño y posición). Insertar > Video > Este dispositivo. Poner el mismo tamaño y posición.
2. Organizar > Enviar al fondo, y luego borrar el marco (si no, el marco queda delante del video). El velo y los textos siguen encima. Panel de selección: Alt+F10.
3. Reproducción: fondos (portada, gancho, cierre) en "Automáticamente", "Repetir hasta detener" y silencio; demo y plan B en "Al hacer clic" para que nada arranque solo durante la demo en vivo. Formato de video > Fotograma de póster = primer cuadro.
4. Video a la mitad (tipo 5): Formato de video > Forma del video > Rectángulo: esquinas redondeadas, y ajustar el tirador amarillo para igualar r 0,12.
5. Imagen: clic derecho en el marco > Formato de forma > Relleno > Imagen o textura > Insertar (conserva la forma redondeada); si se deforma, Recortar > Rellenar.
6. Archivos: MP4 H.264, 1920 × 1080, 30 fps, sin audio, bucles de 8 a 15 s, ≤ 25 MB cada uno; incrustar (no vincular); Archivo > Información > Comprimir medios; probar en el computador que presenta. Imágenes 1920 × 1080 o 2560 × 1440, ≤ 4 MB.

## 7. Fichas por tipo de diapositiva (x, y, w, h en pulgadas)

`W3 = 3,8` y `COL3 = 0,67 / 4,77 / 8,87`. Todo texto con `margin: 0` e `isTextBox: true`; cada forma con `objectName`.

### Tipo 1 · Portada (diseño `MEDIA`)

| Capa (de abajo arriba) | Posición | Especificación |
|---|---|---|
| `VIDEO_portada` o `IMAGEN_portada` | 0, 0, 13,333, 7,5 | Marco a sangre, ver §6 |
| `CAPA_velo` | 0, 0, 13,333, 7,5 | BOSQUE_950, transparencia 40, sin línea |
| Anillos `ANILLO_3/2/1` | centro (11,4; 5,6), diámetros 6,4 / 4,4 / 2,4 | LIMA, línea 1,5 / 1,5 / 2,5 pt, transparencia 70 / 55 / 35. Sobresalen por la derecha y abajo |
| Marcador + kicker | marcador (0,67; 1,29); kicker 0,98, 1,25, 7,0, 0,28 | "SABANA HACK · 2026", 14 pt, LIMA |
| Título | 0,67, 1,75, 8,2, 2,3 | "BERRY GOOD IDEA" 72 pt negrita blanco, interlineado 0,9, arriba; cae en dos líneas |
| Subtítulo | 0,67, 4,2, 8,2, 0,55 | "Los ojos que llegan a la cama exacta", 24 pt blanco |
| Apoyo | 0,67, 4,85, 8,2, 0,4 | Una frase, 16 pt GRIS_VERDE |

Video sugerido: macro de hoja con gotas (V1) o robot caminando entre camas al amanecer, en bucle.

### Tipo 2 · Cifra-impacto, tres números (diseño `CLARO`)

- Kicker y título en placeholders. Tres tarjetas en `COL3`, y 2,1, w 3,8, h 4,2, `ROUNDED_RECTANGLE` r 0,12, sombra SHADOW_CARD. Dos tarjetas MENTA y una BOSQUE_900 (la cifra que más importa; por defecto la del centro).
- Dentro de cada tarjeta (x0, y0 = esquina):

| Elemento | Posición | Especificación |
|---|---|---|
| Marcador | (x0+0,35; y0+0,40) | Anillo + punto |
| Rótulo | x0+0,68, y0+0,35, 2,75, 0,30 | 12 pt negrita, `charSpacing: 3`, mayúsculas, HOJA (LIMA en oscura), ≤ 20 caracteres |
| Cifra | x0+0,35, y0+0,90, 3,1, 1,6 | Dos runs: cifra 66 pt + unidad 26 pt, Arial negrita, BOSQUE_900 (LIMA en oscura) |
| Descriptor | x0+0,35, y0+2,75, 3,1, 0,9 | 16 pt, ≤ 14 palabras |
| Fuente | x0+0,35, y0+3,65, 3,1, 0,3 | 10 pt, TEXTO_SEC (GRIS_VERDE en oscura) |

- Variante 2B, cifras sobre imagen (diapositiva "Problema"): diseño `OSCURO`; `IMAGEN_problema` a sangre; velo transparencia 45; kicker y título en blanco/LIMA; tres tarjetas de cristal en `COL3`, y 2,3, w 3,8, h 3,4 (BOSQUE_950, transparencia 25); cifra en LIMA en x0+0,35, y0+0,45, 3,1, 1,6; descriptor 18 pt blanco en x0+0,35, y0+2,2, 3,1, 0,9; nota de imagen generada (10 pt GRIS_VERDE) en 0,67, 6,2, 8,0, 0,3.

### Tipo 3 · Diagrama de flujo de 5 pasos (diseño `OSCURO`)

| Elemento | Posición | Especificación |
|---|---|---|
| Anillo decorativo | centro (12,9; 1,0), d 5,2 | LIMA 1,5 pt, transparencia 88 |
| Número "01" | x, 2,15, 1,0, 0,25 | 12 pt negrita, `charSpacing: 3`, LIMA |
| Nodo | x, 2,5, 1,0, 1,0 | Elipse BOSQUE_700, línea LIMA 2 pt |
| Icono | x+0,25, 2,75, 0,5, 0,5 | `IMAGEN_icono_pasoN` |
| Flecha | x+1,15, 3,0, 1,2, 0 | Línea LIMA 1,5 pt, transparencia 30, `endArrowType: 'triangle'` (solo entre nodos, 4 en total) |
| Título del paso | x, 3,8, 2,0, 0,4 | 20 pt negrita blanco |
| Descripción | x, 4,35, 2,0, 1,2 | 16 pt GRIS_VERDE, ≤ 12 palabras |
| Chip de tiempo | x, 5,75, 1,1, 0,36 | Pastilla (r 0,18) LIMA, texto BOSQUE_900 12 pt negrita: "+0 min" a "+5 min" |

`x = 0,67 + 2,5 · (paso − 1)`. Variante clara (no renderizada): nodo MENTA con línea HOJA 2 pt, flecha HOJA, títulos BOSQUE_900, descripciones TEXTO_SEC, chip HOJA con texto blanco. Variante de 3 pasos: nodos en `COL3`, flecha de x+1,15 con w 2,8, y textos con w 3,4. El chip de tiempo refuerza "a minutos": la alerta llega en minutos desde que el robot ve la hoja (objetivo de latencia, no medición).

### Tipo 4 · Video a pantalla completa con rótulo y capa de texto (diseño `MEDIA`)

Para demo A, demo B, plan B, simulador, dashboard, robot real y gancho.

| Capa | Posición | Especificación |
|---|---|---|
| `VIDEO_<id>` | 0, 0, 13,333, 7,5 | Marco a sangre, ver §6 |
| `CAPA_velo` | 0, 0, 13,333, 7,5 | BOSQUE_950, transparencia 80 |
| Pastilla de estado | 0,67, 0,6, 2,4, 0,45 | BOSQUE_950 transparencia 25, r 0,22; punto LIMA d 0,16 en (0,87; 0,74); texto en 1,17, 0,6, 1,8, 0,45: "DEMO EN VIVO", 12 pt negrita, `charSpacing: 4`, blanco |
| Capa de texto (`CAPA_texto`) | 0,67, 5,0, 7,4, 1,7 | Cristal: BOSQUE_950 transparencia 25, r 0,14 |
| Kicker del pie | 1,02, 5,2, 6,7, 0,3 | 12 pt negrita LIMA, `charSpacing: 4`: "PASO 4 · ALERTA" |
| Texto del pie | 1,02, 5,55, 6,7, 1,0 | Arial 28 pt negrita blanco, ≤ 8 palabras, dos líneas con salto manual |
| `PING_hallazgo` | d 1,1 | Anillo LIMA 3 pt, se coloca a mano sobre el hallazgo |

La capa de texto ocupa solo el 55 % izquierdo inferior; el resto del video queda limpio. Esta diapositiva sirve también como plan B de la demo en vivo.

### Tipo 5 · Video a la mitad + tres puntos (`CLARO`, o `OSCURO` con textos blancos y sin sombra)

| Elemento | Posición | Especificación |
|---|---|---|
| Fila de punto n (n = 1, 2, 3) | y = 2,0 + 1,5 · (n − 1) | Tres filas, paso 1,5 |
| Número | 0,67, y, 0,55, 0,55 | Anillo HOJA 1,75 pt; cifra 16 pt negrita HOJA centrada dentro |
| Título del punto | 1,45, y−0,02, 3,75, 0,4 | 18 pt negrita |
| Descripción | 1,45, y+0,45, 3,75, 0,8 | 14 pt TEXTO_SEC, ≤ 12 palabras |
| `VIDEO_<id>` | 5,62, 2,0, 7,05, 3,97 | 16:9, redondeado r 0,12, SHADOW_VIDEO |
| Pie del video | 5,62, 6,1, 7,05, 0,3 | 10 pt TEXTO_SEC: origen del video y si son datos simulados |

Con imagen en lugar de video (por ejemplo la plataforma multicultivo) se usa `IMAGEN_<id>` en el mismo rectángulo.

### Tipo 6 · Gráfico de barras comparativo (`CLARO`)

| Elemento | Posición | Especificación |
|---|---|---|
| Gráfico nativo `GRAFICO_barras` | 0,67, 1,95, 7,6, 4,2 | Barras horizontales, una serie, color por barra (§8) |
| Nota | 0,67, 6,2, 7,6, 0,3 | 10 pt: n, fuente, "escala logarítmica" si aplica |
| Tarjeta destacada | 8,57, 2,1, 4,1, 4,2 | BOSQUE_900, r 0,12, SHADOW_CARD |
| Cifra | 8,92, 2,5, 3,4, 1,3 | 66 pt negrita, ÁMBAR si es una falsa alarma o límite; LIMA si es una ventaja |
| Descriptor | 8,92, 3,95, 3,4, 1,6 | 16 pt blanco |
| Fuente | 8,92, 5,9, 3,4, 0,3 | 10 pt GRIS_VERDE |

Variante 6L (evidencia, con límites obligatorios): gráfico h 3,25; tarjeta h 3,1 (cifra en 8,92, 2,3, 3,4, 1,2; descriptor en 8,92, 3,6; fuente en 8,92, 4,75); panel de límites en 0,67, 5,45, 12,0, 1,05, MENTA r 0,12 con SHADOW_CARD; marcador ámbar en (0,97; 5,62); rótulo "LÍMITES QUE DECLARAMOS" en 1,37, 5,58, 6,0, 0,28 (11 pt negrita, ÁMBAR_TXT, `charSpacing: 3`); texto en 0,97, 5,92, 11,4, 0,5 (12 pt BOSQUE_900, la frase de `CIFRAS_CLAVE.md` §6 sin cambiar).

Si una barra es más de 20 veces otra (kit D1 frente a cámaras fijas), usar `valAxisLogScaleBase: 10`, decirlo en el título del gráfico ("escala logarítmica") y rotular todos los valores; o mostrar el cociente en la tarjeta ("66×") en lugar de barras lineales.

### Tipo 7 · Costo y finanzas: tres KPI + gráfico (`CLARO`)

Uso según `INSTRUCCIONES.md`: costo del hardware (kit ≈ 35 M COP frente a cámaras fijas y humanoides) y lo que está en juego para la finca. Sin ROI, payback ni margen.

| Elemento | Posición | Especificación |
|---|---|---|
| KPI n (n = 1, 2, 3) | `COL3`, y 1,95, w 3,8, h 1,5 | Tarjeta r 0,12 con SHADOW_CARD; MENTA, y BOSQUE_900 para el KPI central (el dato que se defiende) |
| Rótulo del KPI | x+0,35, y+0,20, 3,1, 0,28 | 11 pt negrita, `charSpacing: 3`, ≤ 24 caracteres |
| Valor del KPI | x+0,35, y+0,55, 3,1, 0,8 | 48 pt + unidad 20 pt, BOSQUE_900 (LIMA en el oscuro) |
| Gráfico `GRAFICO_barras` o `GRAFICO_linea` | 0,67, 3,75, 7,9, 2,8 | Barras horizontales (costos, escala logarítmica) o línea: `lineSize` 3, símbolo círculo 8; serie propia en HOJA, referencia en GRIS_VERDE |
| Tarjeta de supuestos | 8,87, 3,75, 3,8, 2,7 | MENTA con SHADOW_CARD; rótulo "SUPUESTOS" 11 pt HOJA en 9,17, 3,95; viñetas 14 pt (`bullet: true`, `paraSpaceAfter: 8`) en 9,17, 4,35, 3,2, 1,9 |
| `PING_<id>` | d 0,5 | Anillo ÁMBAR 2,5 pt sobre el dato clave del gráfico; posición manual tras renderizar |

Los supuestos van siempre visibles (la rúbrica castiga ocultar límites): precios FOB de referencia, sin cotización formal, TRM 3.185. Variante línea (datos de ejemplo en el kit, diapositiva "7L"): mismas posiciones. Para barras apiladas con línea (probado): combo `[{ type: pres.charts.BAR, options: { barGrouping: 'stacked' } }, { type: pres.charts.LINE }]` sobre el mismo eje, sin eje secundario. En apiladas `dataLabelPosition` solo puede ser `ctr`, `inEnd` o `inBase` (`outEnd` corrompe el archivo). Con `ctr` las etiquetas chocan con la línea: usar `inBase` y `dataLabelFormatCode: '#,##0;-#,##0;;'` (oculta ceros), o mejor `showValue: false` y dejar los números en los KPI. Colores: serie 1 GRIS_VERDE, serie 2 HOJA, línea ÁMBAR; el texto oscuro de etiquetas no se lee sobre HOJA.

### Tipo 8 · Cierre (diseño `MEDIA`)

| Capa | Posición | Especificación |
|---|---|---|
| `VIDEO_cierre` / `IMAGEN_cierre` | 0, 0, 13,333, 7,5 | Marco a sangre |
| `CAPA_velo` | 0, 0, 13,333, 7,5 | BOSQUE_950, transparencia 35 |
| Anillos | centro (11,6; 1,6), d 5,4 y 3,0 | LIMA, 1,5 pt transparencia 70; 2,5 pt transparencia 40 |
| Marcador + kicker | (0,67; 0,6) y 0,98, 0,55, 7,0, 0,28 | "CIERRE", 12 pt LIMA |
| Título | 0,67, 1,1, 10,0, 1,9 | "DE 8 DÍAS HÁBILES" / "A MINUTOS", 60 pt negrita blanco, salto manual, interlineado 0,9 |
| Subtítulo | 0,67, 3,15, 10,0, 0,5 | 24 pt blanco, ≤ 40 caracteres |
| Tres próximos pasos | `COL3`, y 4,0, w 3,8, h 1,05 | Cristal r 0,14 transparencia 25; marcador en (x+0,3; y+0,4); texto en x+0,7, y, 2,8, 1,05: 16 pt negrita blanco, ≤ 6 palabras |
| Panel de límites | 0,67, 5,3, 12,0, 1,3 | Cristal transparencia 18; marcador ÁMBAR en (0,97; 5,5); rótulo 11 pt ÁMBAR en 1,37, 5,46; texto en 0,97, 5,8, 11,4, 0,72, 14 pt blanco (frase de `CIFRAS_CLAVE.md` §6) |

La frase de límites debe aparecer completa en la diapositiva 6 o en la 11; en las dos si el tiempo lo permite.

## 8. Gráficos nativos (iguales en todo el deck)

- Siempre sobre fondo claro (tipos 6 y 7). Tipografía: `catAxisLabelFontFace`, `valAxisLabelFontFace`, `dataLabelFontFace`, `titleFontFace` y `legendFontFace` = `'+mn-lt'` (Calibri del tema; por defecto saldrían en Arial).
- Barras: `barDir: 'bar'`, `barGapWidthPct` 40 a 45, `catAxisOrientation: 'maxMin'` (primera categoría arriba), eje de valores oculto con `valAxisMinVal: 0` y máximo fijo (100 para porcentajes), `valGridLine` y `catGridLine` con `style: 'none'`, etiquetas `outEnd` con `dataLabelFormatCode: '0" %"'`.
- Texto: etiquetas de categoría 14 pt BOSQUE_900; etiquetas de dato 14 pt negrita BOSQUE_900; título del gráfico = unidad, 12 pt TEXTO_SEC sin negrita ("Porcentaje sobre 68 hojas de laboratorio"); leyenda abajo, 12 pt; en líneas, ejes 12 pt TEXTO_SEC, rejilla `DCE9D5` a 0,75 pt solo en el eje de valores, y título del eje de categorías ("Meses").
- Color: lo nuestro/positivo HOJA; alternativas y neutros GRIS_VERDE; falsas alarmas, límites y pérdidas ÁMBAR. Una serie con varios colores por barra: `chartColors` con un color por punto.
- Cifras en porcentajes (el jurado es de negocios); el número y la fuente siempre visibles; sin gráficos 3D.

## 9. Mapa de uso (guion v2, 11 diapositivas, ~5 min)

Numeración y tiempos de `guion_v2.md` §1 (ahí están los segundos de 3, 5 y 9 min; aquí solo qué se corta o se amplía). Si `INSTRUCCIONES.md` cambia el contenido de una diapositiva, el tipo visual se mantiene. Títulos cortos propuestos (≤ 38 caracteres); el guion puede ajustarlos mientras respete el límite.

| # | Slug | Tipo | Marcos de medios | Título corto propuesto | 3 min | 9 min |
|---|---|---|---|---|---|---|
| 1 | portada | 1 | `VIDEO_portada` o `IMAGEN_hoja` | BERRY GOOD IDEA | se queda (3 s) | se queda |
| 2 | gancho-2am | 4 | `VIDEO_gancho` (macro de hoja con gotas) | caption: "¿Cuándo se entera el agrónomo?" | ACORTAR a una frase | AMPLIAR: Botrytis |
| 3 | problema | 2B (o 2) | `IMAGEN_problema` | LA PÉRDIDA ES ALTA Y LA RONDA, LENTA | ACORTAR a 2 cifras | AMPLIAR: 40 bloques, 30 a 40 % sin prevención |
| 4 | misma-noche | 3 (3 pasos) | `IMAGEN_icono_paso1..3` | RIESGO, ROBOT Y DECISIÓN HUMANA | ACORTAR | AMPLIAR: por qué prioriza, qué viaja por LoRaWAN |
| 5 | demo-vivo | 4 | `VIDEO_demoA` (plan B, 90 s) | EN VIVO: EL ROBOT MIRA Y ALERTA | una hoja sana y una enferma | AMPLIAR: 2.ª ronda con hojas del jurado |
| 6 | supervisor-registro | 5 | `VIDEO_panel` (grabación del panel) | EL SUPERVISOR VE, ENVÍA Y REGISTRA | CORTAR | AMPLIAR: vista cenital, puntos ciegos |
| 7 | evidencia | 6L | ninguno | 78 % DE ENFERMAS ALERTADAS | se queda, con límites | AMPLIAR: matriz de confusión |
| 8 | alternativas-aspersion | 6 | `VIDEO_sim` (opcional) | EL HÍBRIDO GANA, 89 DE 100 | una frase | AMPLIAR: matriz de 6, pesos |
| 9 | negocio-roi (según instrucciones: costo) | 7 | ninguno | EL ROBOT ES 66× MÁS BARATO | se queda | AMPLIAR: escenarios de hardware |
| 10 | escalabilidad | 5 (imagen) | `IMAGEN_plataforma` | OTRO FRUTAL, UN PERFIL NUEVO | CORTAR | AMPLIAR: etapas |
| 11 | cierre | 8 | `VIDEO_cierre` | DE 8 DÍAS HÁBILES A MINUTOS | se queda | AMPLIAR: lista de lo que falta |

Ritmo de fondos: oscuras 1, 2, 3 (apertura, la 3 en variante 2B), 5 (demo) y 11; claras 4 (variante clara del tipo 3, para separar la apertura de la demo) y 6 a 9 (panel, evidencia, alternativas, costo); la 10 puede ir en `OSCURO` (tipo 5 oscuro) para preparar el cierre. Nunca más de cuatro claras seguidas.

## 10. Construcción y verificación

- `NODE_PATH=<node_modules con pptxgenjs> node kit_visual.js` genera `muestra_diseno.pptx` (11 diapositivas de muestra: tipos 1 a 8 más 2B, 6L y 7L; textos tomados de `CIFRAS_CLAVE.md` e `INSTRUCCIONES.md`; el gráfico de línea 7L usa datos inventados de ejemplo).
- Orden: `pres.theme`, `defineSlideMaster` (`CLARO`, `OSCURO`, `MEDIA`), `addSection` antes de las diapositivas, `writeFile`, luego `applyTheme`.
- Verificar con `validate.py` del skill pptx (necesita Python 3.10 o superior; en este equipo `/opt/homebrew/bin/python3.11`) y con render a PDF e imágenes. Mirar siempre: título en una línea, cifras sin partir, rótulos de KPI sin envolver, gráficos con la misma tipografía.
- Cada diapositiva lleva notas del orador con `addNotes`; nada de texto de notas dentro de la diapositiva.
