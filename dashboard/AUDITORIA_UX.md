# Auditoría UX/UI — Dashboard de incidencias agrícolas

Método: inspección del código (`src/`) y de la página real en escritorio (1440 px) y móvil (375 px) con datos en vivo (sim-core :8010) y con `VITE_FORCE_MOCK=true`. Severidad Nielsen: 0 = no es problema, 1 = cosmético, 2 = menor, 3 = mayor, 4 = catastrófico. N1–N10 = heurísticas de Nielsen; "Maeda" = leyes de simplicidad (reducir, organizar, tiempo, aprender, diferencias, contexto, emoción, confianza, fracaso, la única).

## Hallazgos (estado inicial)

| # | Problema concreto (componente) | Heurística / Maeda | Sev. | Corrección propuesta | Estado |
|---|---|---|---|---|---|
| 1 | No hay respuesta de un vistazo a "¿hay alertas, dónde, qué enfermedad?": solo un KPI "154" y una tabla de 500 filas (`App.tsx`) | N1, N6; Maeda: organizar, la única | 4 | Banda de estado principal: nº de alertas, enfermedad dominante, camas con más alertas, última alerta | Hecho (`StatusBanner`) |
| 2 | KPIs sin contexto: "9,3 °C" y "99 %" no dicen si es bueno o malo; flechas "▲ 0.0" sin significado (`Kpi.tsx`) | N1, N2; Maeda: contexto, aprender | 3 | Semáforo con icono+texto, rango ideal/meta visible, "Ahora" vs promedio, "= Estable" en vez de ▲ 0.0 | Hecho (`lib/umbrales.ts`) |
| 3 | Tabla ordenada por hora: lo urgente no va primero; con 500 alertas iguales no hay prioridad (`IncidentTable`) | N7; Maeda: tiempo, organizar | 3 | Orden por defecto "más urgentes primero" (alertas, gravedad, recientes) + selector de orden | Hecho |
| 4 | Ubicación "N2 C3 P17" sin explicación (tabla, heatmap) | N2, N10; Maeda: aprender | 3 | Cabecera con tooltip "N = nave · C = cama · P = planta", formato "N2 · C3 · P17", texto completo en el detalle | Hecho |
| 5 | Sin detalle ni acción: el operario no sabe qué hacer ante "Oídio" | N6, N10; Maeda: aprender, confianza | 3 | Panel de detalle al hacer clic: qué es, qué hacer, T/HR evaluadas, confianza, fuente | Hecho (`DetailPanel`) |
| 6 | Color como único diferenciador: oídio y alternaria casi idénticos (rojo/rojo), heatmap solo por intensidad (`Badge.tsx`, `Charts.tsx`) | N1, WCAG 1.4.1; Maeda: diferencias | 3 | Glifo por clase (● ■ ▲ ✓), columna "Urgencia" con icono + texto, números en el heatmap, celda máxima con borde dorado | Hecho |
| 7 | "En vivo" sin feedback: no se ve cuándo llegó el último dato; si el stream se congela sigue diciendo "En vivo" | N1, N9; Maeda: confianza, fracaso | 3 | "En vivo · hace N s"; tras 6 s sin datos pasa a "Sin señal" (ámbar) con aviso | Hecho |
| 8 | Aviso "Sin conexión" también salía con `VITE_FORCE_MOCK` (mensaje falso); mock poco destacado | N9, N1 | 2 | Aviso distinto para modo forzado vs fallo de red; rol `alert`; "no son datos reales" | Hecho |
| 9 | Estado "cargando": KPIs en "—" y tabla vacía sin explicación | N1; Maeda: emoción | 2 | Skeletons en KPIs, banda y tabla | Hecho |
| 10 | Estado vacío "Sin incidencias para este filtro" sin salida | N9, N3 | 2 | Mensaje + botón "Limpiar filtros"; texto distinto si aún no hay datos | Hecho |
| 11 | Filtros: el estado activo no es visible; sin "limpiar"; contador sin referencia | N1, N3, N7 | 3 | Segmentado Todas/Alertas/Saludables con conteos, chips de filtros activos con ✕, "Limpiar filtros", "mostrando X de Y" | Hecho |
| 12 | Heatmap/zona: no se podía pasar de "dónde" a la lista | N7; Maeda: tiempo | 2 | Clic en cama o en chip de zona filtra la tabla y baja a ella | Hecho |
| 13 | Títulos de gráficos descriptivos, no concluyentes ("Distribución de detecciones") | N2; Maeda: contexto | 2 | Títulos con conclusión calculada ("Oídio domina: 35 % de las alertas", "Nave 2 · Cama 2 concentra más alertas", "Humedad muy alta…") + subtítulo con ejes/unidades | Hecho |
| 14 | Distribución contaba solo las últimas 500 filas, no el total del resumen (inconsistente) | N4; Maeda: confianza | 2 | Usa `resumen.por_clase`; heatmap indica "en las últimas N detecciones" | Hecho |
| 15 | Gráfico T/HR: doble eje sin vínculo visual, tooltip sin unidades, tipografía 11 px | N2, N4 | 2 | Eje T en color de su línea, trazo continuo/discontinuo, tooltip con unidades y coma decimal, 12–13 px | Hecho |
| 16 | Tipografía pequeña para pantalla grande del pitch (11–14 px) | Maeda: reducir/diferencias | 3 | Escala tipográfica en rem + "Modo presentación" (raíz 19 px; 22 px en ≥1700 px), recordado en localStorage | Hecho |
| 17 | Contraste: `text-slate-400` sobre fondos tintados; brand `#293378` usado como texto/ícono (1,5:1) | WCAG 1.4.3; N1 | 3 | Tokens de texto fg / muted / subtle (≥6:1) y `brand-300` para texto de marca; brand solo como superficie | Hecho |
| 18 | Foco solo con outline global; botones de ordenar/paginación <44 px en móvil | WCAG 2.4.7, 2.5.5 | 2 | Clases `.ctl`/`.btn` con 44 px en móvil, foco dorado de 2 px, enlace "Saltar a la tabla" | Hecho |
| 19 | Roles/ARIA: filas no accionables por teclado; `role=status` anunciaba todo | WCAG 4.1.2, 2.1.1 | 2 | Botón real en cada fila; panel `role=dialog` con foco atrapado/Esc/restaura foco; `role=status` solo en el estado de conexión | Hecho |
| 20 | `prefers-reduced-motion` solo cubría 2 animaciones | WCAG 2.3.3 | 1 | Cubre skeleton, panel y scroll suave | Hecho |
| 21 | Responsive: tabla con `min-w-[720px]` y scroll horizontal en 375 px | N7; Maeda: reducir | 3 | En <768 px la tabla pasa a tarjetas; sin scroll horizontal (verificado scrollWidth = 375) | Hecho |
| 22 | Tokens dispersos: hex en CSS, TS y Tailwind; radios/sombras ad hoc | N4; Maeda: organizar | 2 | Tokens como variables CSS en `src/index.css` + `tailwind.config.js` (colores, radios, sombras, espaciado, tipografía); gráficos usan las mismas variables | Hecho |
| 23 | Microcopy: "Promedio de lecturas", "HR" sin definir, "(simulado)" ambiguo, "Estado" duplicado con "Detección" | N2, N4; Maeda: reducir | 2 | "Humedad relativa (HR)", "simulación: día 12", columna Estado sustituida por "Urgencia" (Alta/Media), frases sin jerga | Hecho |
| 24 | "Incidencias activas" (154), alertas cargadas (500) y detecciones (2176) conviven sin definición | N2, N4 | 3 | Etiquetado ("alertas recientes", "detecciones en total") para no mezclar | Parcial: falta confirmar con backend qué es "activa" |
| 25 | Formato de hora "D12 05:12" | N2 | 1 | "Día 12 · 05:12" | Hecho |
| 26 | Paginación con 500 filas en vivo: la página 1 cambia sola | N7 | 2 | Muestra "1–10 de 500"; filtros/orden persistentes | Parcial: no se congela la vista |

## Contraste de los pares nuevos, tema oscuro (calculado, WCAG 2.x)

| Par | Ratio | Criterio |
|---|---|---|
| Texto principal / tarjeta | 15,6 | AAA |
| Texto secundario / tarjeta | 9,7 | AAA |
| Texto terciario / tarjeta | 6,1 | AA |
| brand-300 / header (#1C2356) | 7,1 | AAA |
| brand-300 / brand | 5,5 | AA |
| Blanco / brand (botón) | 11,4 | AAA |
| danger-300 / chip alerta | 7,3 | AAA |
| warn-300 / chip atención | 8,9 | AAA |
| pos-300 / chip positivo | 7,8 | AAA |
| gold-300 / fondo | 11,6 | AAA |
| Texto en heatmap máximo (tras bajar la opacidad; antes 4,23) | 6,1 | AA |
| Foco dorado / fondo | 7,7 | AA no texto (≥3) |

Notas: oídio vs alternaria en barras tienen poco contraste entre sí (1,4:1; rojo vs coral); se distinguen por etiqueta, posición y glifo, no por color. El borde `brand` sobre tarjeta (1,5:1) es decorativo.

---

## Antes / después

**Antes:** cabecera con "En vivo" estático, 4 KPI sin umbrales ni significado, tabla de 500 filas por hora (7 columnas, `min-w` 720), gráficos con título descriptivo, colores definidos en 4 sitios, fuente de 11–14 px, sin detalle ni acciones, filtros sin estado visible, scroll horizontal en móvil.

**Después:**
- Banda de estado: "154 alertas activas · Oídio 35 % · Nave 2 Cama 2 (71) · última hace N min · Ver alertas".
- KPIs con semáforo (icono + texto), rango ideal, ahora vs promedio, estable/delta y sparkline coloreado por estado.
- Orden por urgencia, columnas Urgencia y Confianza, filtros con chips/limpiar/contadores, selector de orden.
- Panel de detalle con qué es / qué hacer / T-HR / confianza / fuente.
- Estados: cargando (skeleton), vacío (con salida), "En vivo · hace N s", "Sin señal", "Datos de ejemplo" (forzado vs sin conexión).
- Gráficos con conclusión en el título, heatmap clicable con leyenda, T/HR con ejes coloreados y tooltips con unidades.
- Modo presentación (rem escalado), móvil con tarjetas, 44 px táctiles, skip-link, foco atrapado en el panel, reduced-motion.
- Tokens en `src/index.css` (variables) + `tailwind.config.js`; umbrales en `src/lib/umbrales.ts`; catálogo de enfermedades en `src/lib/catalogo.ts`.
- `npm run build`: sin errores de TS ni warnings (`chunkSizeWarningLimit` a 700 kB por recharts).

**Pendiente:**
1. Validar con el agrónomo de AGRAR los umbrales (T 12–26 °C, HR 60–85 %, crítica >92 %, meta de plantas sanas 95 %) y los textos de "qué hacer"; hoy son orientativos y así se rotulan.
2. Confirmar con backend la definición de "incidencias activas" (154) frente a alertas totales (2176) y exponer el conteo por cama completo (el heatmap usa las últimas 500 detecciones).
3. Congelar la vista de la tabla mientras el usuario pagina (la lista se desplaza en vivo).
4. Pruebas con lector de pantalla real y simulación de daltonismo; no se anuncian por voz las alertas nuevas a propósito (1 Hz saturaría).
5. Diferenciar mejor oídio/alternaria en gráficos si se imprime en blanco y negro (hoy: glifo + etiqueta).
6. Reiniciar una vez el dev server de :5180 (`npm run dev`): Tailwind cachea `tailwind.config.js` y la recarga en caliente muestra "text-fg class does not exist" hasta reiniciar. El build y una instancia nueva (:5181, ya apagada) funcionan bien.

---

## Tema claro (predeterminado)

Cambio centralizado en `src/index.css`: `:root` define el tema claro y `html[data-theme='dark']` conserva el oscuro como alternativa (botón "Tema claro/oscuro" en el encabezado, guardado en `localStorage`, aplicado antes del primer pintado desde `index.html`). `tailwind.config.js` no cambió (sigue leyendo las mismas variables). Los nombres de token son roles (`ink-800` = tarjeta, `*-300` = color legible de texto/icono), así que ningún componente cambió de clases salvo ajustes puntuales.

| Rol | Claro | Notas |
|---|---|---|
| Fondo página / tarjeta / borde | #F3F4F6 / #FFFFFF / #E5E7EB | sombra suave `--sh-card`, línea superior dorada sutil |
| Texto principal / secundario / terciario | #111827 / #4B5563 / #656C7C | el terciario se oscureció desde #6B7280 (4,39:1 sobre el fondo de página) |
| Marca | #293378 (encabezado, botones, enlaces, iconos, foco) | dorado solo en líneas finas e icono del encabezado; texto dorado = #856404 |
| Positivo | #15803D, texto #166534 sobre tinte verde | |
| Advertencia / alerta | #B45309 (texto #92400E) / #B91C1C (texto #991B1B) | solo en badges con tinte claro + texto oscuro + icono |
| Heatmap | rojo 10–52 % de opacidad sobre blanco, texto oscuro, celda máxima con borde azul | leyenda de gradiente |
| Gráficos | oídio #B91C1C, alternaria #EA580C, heliothis #C27803, T #A16207 (continua), HR #293378 (discontinua) | variables `--c-cl-*`, `--c-line-*` |
| Modo presentación | solo escala la raíz (rem): funciona igual en ambos temas | |

Contrastes (WCAG 2.x, calculados):

| Par | Ratio | Criterio |
|---|---|---|
| Texto principal / tarjeta; / fondo página | 17,7; 16,1 | AAA |
| Secundario / tarjeta; / fondo página | 7,6; 6,9 | AAA/AA |
| Terciario #656C7C / tarjeta; / fondo página; / #F9FAFB | 5,0; 4,8; 5,0 | AA |
| Blanco / brand (header, botones) | 11,4 | AAA |
| Subtítulo blanco 80 % / brand | 7,9 | AAA |
| Brand / tarjeta (enlaces, iconos, foco) | 11,4 | AAA |
| Rojo #991B1B / tinte rojo 15 %; / banner 7 % | 6,4; 7,4 | AA |
| Ámbar #92400E / tinte ámbar 15 % | 5,8 | AA |
| Verde #166534 / tinte verde 25 %; / 15 % | 5,0; 5,8 | AA |
| Dorado #856404 / blanco | 5,5 | AA |
| Texto / heatmap máximo; / mínimo | 6,7; 15,0 | AA |
| Pills del encabezado (verde, ámbar) / #F3F4F6 | 6,5; 6,4 | AA |
| Gráficos (no texto, ≥3): T 4,9; HR 11,4; oídio 6,5; alternaria 3,6; heliothis 3,5 | | AA 1.4.11 |
| Borde de controles #89919E / blanco | 3,2 | AA 1.4.11 |
| Borde de tarjeta #E5E7EB / blanco | 1,2 | decorativo (la tarjeta se separa por sombra y fondo) |

Pendiente del tema claro: revisar impresión/blanco y negro; el tema oscuro no se reauditó pixel a pixel tras el cambio de tokens (se comprobó que el toggle funciona y que el fondo cambia).

---

## Rediseño visual (referencias)

Referencias: visionOS (vidrio esmerilado, radios grandes, bento), DeerFlow (tarjetas numeradas, tipografía técnica pequeña, números grandes, un solo acento), crédito (saludo grande, píldoras con la activa rellena, degradés suaves), MARK91 (cápsulas y botones circulares) y Finance Overview (gris claro, tarjetas blancas de radio ~28 px, nav en píldoras, chips de acento, número grande con decimales pequeños). Todo centralizado en `src/index.css` (tokens y clases `.card`, `.glass`, `.tag`, `.num`, `.btn`, `.icon-btn`, `.pill`); no se tocó `tailwind.config.js` ni se añadieron fuentes (la etiqueta técnica usa la monoespaciada del sistema).

| Referencia | Qué se tomó | Dónde |
|---|---|---|
| Finance Overview / crédito | Header sin barra plana: logo (punto dorado mínimo) + "Hola, AGRAR" grande + subtítulo gris; navegación en píldoras (Resumen · Incidencias · Mapa · Clima) con scroll a cada sección y píldora activa rellena #293378 (scroll-spy); chip "En vivo" y botones circulares (alertas con contador, tema, presentación) con `aria-label` y tooltip | `App.tsx` |
| visionOS | Vidrio (blanco 72 % + blur) en el header sticky y en el panel de detalle; radios de 28 px; sombra grande y suave `0 8px 30px rgb(17 24 39/.06)`; bento: banda de alertas ancha, KPIs de 4 columnas (el de plantas sanas con anillo), mapa 7/5 columnas, clima a todo el ancho | `Card`, `StatusBanner`, `App.tsx` |
| DeerFlow | Etiquetas numeradas en mayúsculas espaciadas y monoespaciadas ("01 · ALERTAS" … "08 · CLIMA"), botón circular ↗ que abre el detalle (tabla o gráfico), anillo punteado de progreso | `Tag`, `ArrowBtn`, `Anillo` |
| Finance / MARK91 | Números de 52–56 px, gruesos y tabulares, con decimales y unidad pequeños y grises (9<small>,3</small> °C); deltas y estado en chips; controles en cápsula | `Big`, `Kpi`, `.btn`, `.ctl` |
| Fondo | Gris #F2F3F5 con dos degradés radiales muy sutiles (azul #293378 al 8 %, teal al 6 %) | `html` |

Decisión de color: el acento fresco es **menta** (fondo #CDEFE3 / texto #0F5E59, 6,2:1) con teal #0F766E en iconos y gráficos; convive mejor con el azul real que la lima, que choca con el dorado. #0F766E sobre menta da solo 4,44:1, por eso el texto usa #0F5E59. Azul #293378 = acción y estado activo; rojo y ámbar solo en chips claros de alerta; dorado solo en el punto del logo y filtros de aviso de ejemplo. El tema oscuro usa los mismos patrones (vidrio oscuro, menta #16403C / #82EAD6).

Contrastes nuevos (calculados): menta texto/fondo 6,2 · texto terciario #656C7C sobre fondo de página 4,7 y sobre tarjeta 5,3 · blanco sobre azul (píldora activa, botón primario) 11,4 · azul sobre blanco (etiqueta numérica) 11,4 · rojo/ámbar oscuros sobre su tinte 7,0 / 5,8 · contador rojo con texto blanco 6,5 · texto del header sobre vidrio 7,4 · oscuro: menta 8,0, terciario 6,1, brand-300 8,2.

Verificado: `npm run build` sin errores ni warnings; escritorio 1440 px y móvil 375 px (sin scroll horizontal, objetivos táctiles de 44 px, nav en píldoras con scroll horizontal), tema claro y oscuro, datos en vivo. Se conserva todo lo funcional: filtros, panel de detalle, estados, modo presentación, tarjetas en móvil y `prefers-reduced-motion`.

Cambios de contenido: se retiró la tarjeta "Incidencias activas" (duplicaba el número de la banda de alertas) y el orden de la página sigue ahora a la navegación (Resumen, Incidencias, Mapa, Clima). Pendiente: el bell del header filtra a alertas (no abre un cajón de notificaciones); revisar el vidrio en navegadores sin `backdrop-filter`.


---

## Prevención y acción

Objetivo: que alguien en la finca **detecte a tiempo, prevenga y actúe**. Se respetó el sistema de diseño vigente (tema claro, tokens de `src/index.css`, etiquetas numeradas, píldoras, panel lateral); no se tocó `tailwind.config.js`.

| Pieza | Dónde | Decisión de diseño |
|---|---|---|
| 09 · Qué atender hoy | `FocosCard`, pastilla "Atender" | 3-5 focos con ubicación, tipo, nº de plantas, antigüedad (semáforo icono+texto), riesgo de la cama, tendencia con sparkline, "por qué" y un botón primario con la siguiente acción del ciclo. El número grande de la banda 01 pasa a "focos abiertos" con las detecciones como dato secundario (cierra el hallazgo 24: qué es "activa"). |
| Ciclo de acción | `FocoPanel` (diálogo con foco atrapado, Esc, restaura foco) | Estados Nuevo → Asignado → Verificado → Tratado → Cerrado en una lista con `aria-current="step"`; formulario con etiquetas visibles, botones de 44 px, errores del servidor en `role="alert"`, historial con marca de tiempo. Se evitó un error de foco: el panel no debe re-registrar su manejador de teclado en cada render (robaba el foco cada segundo). |
| Etiquetas para el modelo | KPI en `FocosCard` | Verificado en campo = etiqueta (confirmado o falsa alarma); se muestra nº y % de falsas alarmas. |
| 10 · Riesgo próximo | `RiesgoCard`, pastilla "Riesgo" | Mapa nave × cama por ventana (Ahora, 0-24, 24-48, 48-72 h). Nivel = icono + texto (✓ Bajo, ◆ Medio, ▲ Alto), no solo color. Rotulado ESTIMADO y orientativo; si todo es bajo lo dice y muestra el mayor índice y desde qué valor pasa a "medio". |
| 11 · Cobertura | `CoberturaCard` | Mini-mapa de horas desde la última inspección; "puntos ciegos" con ◆ y lista textual "Sin revisar". |
| Foto de la detección | `Foto` (detalle de incidencia y de foco) | Foto del D1 si existe; si no, placeholder honesto "Sin foto (simulación)". |
| Copiar aviso | `CopiarAviso` | Texto corto; confirma con texto y `role="status"`. |

Qué es estimado u orientativo: (1) el riesgo de 24-72 h se proyecta con el clima horario del escenario, sin azar de ventilación/alero; (2) las recomendaciones preventivas son reglas fijas, a validar con el agrónomo; (3) la antigüedad y la cobertura están en horas del escenario simulado (con el robot real serían horas reales); (4) los umbrales por enfermedad vienen de `config/risk.yaml` y varios son SUPUESTO; (5) la tendencia "baja" solo se afirma tras un tratamiento, porque las detecciones no miden plantas que se recuperan.

Pendiente: probar con lector de pantalla real; si un foco se fusiona con otro que ya tenía acciones, queda el id del que comparte más incidencias; no hay reapertura de focos cerrados; integración real de avisos (WhatsApp/pantalla de oficina) sin hacer.

---

## Vista cenital

Responde "¿dónde está pasando?" sobre el plano real del bloque (coordenadas del motor, a escala). Se integra en la sección Mapa con el sistema claro/bento (tarjeta numerada 12, píldoras, controles de 44 px en móvil).

| Decisión | Motivo |
|---|---|
| Escalas continuas sin arcoíris: temperatura azul→amarillo→rojo, HR blanco→azul, riesgo menta→ámbar→rojo | Legible y apta para daltonismo; leyenda con valores numéricos mín/medio/máx |
| Radio ∝ confianza (4–14 px, leyenda 50/75/95 %), borde blanco o grueso oscuro (foco sin cerrar) | El tamaño y el borde no dependen del color; el halo blanco da contraste sobre cualquier capa |
| Rojo oídio/alternaria, ámbar Heliothis, verde sana; en la leyenda, glifo + texto | Misma semántica que badges y tabla |
| Rótulo explícito "interpoladas a partir de N lecturas, datos simulados" y marcas ◇ en las lecturas reales | No presentar un campo suave como si fuera medido |
| Riesgo por cama con ▲ ◆ ✓ además del color | WCAG 1.4.1 |
| Orientación automática (eje largo a lo ancho en pantallas anchas, vertical en móvil) y "Girar 90°"; brújula y barra de escala | Pantalla del jurado y móvil sin scroll horizontal |
| Zoom/pan con rueda, pellizco y botones +/−/Restablecer | Alternativa por botón a los gestos |
| Círculos enfocables con teclado (Enter/Espacio abre el detalle) solo si hay ≤ 120 visibles; si hay más, se pide acercar o filtrar y la tabla de incidencias tiene todas | Evitar cientos de paradas de tabulación |

Pendiente: lector de pantalla real; el campo se calcula con lecturas de las últimas 24 h (ventana fija en el cliente); con muchas detecciones juntas los círculos se solapan (acercar o filtrar); el modo presentación solo escala texto, no los círculos.

## Simplificación (Maeda + Nielsen), 2026-10-24

Problema: con la simulación corriendo días, la página mostraba 100+ focos en tarjetas altas, 400+ círculos encimados en el mapa y mensajes que se contradecían. Respaldo del código anterior: `src.antes_maeda.tgz`.

| Hallazgo | Principio | Cambio |
|---|---|---|
| Numeración de tarjetas 01, 09, 02… 12 sin seguir el orden de la página | Maeda · Reducir; Nielsen #4 consistencia | Se quitó el número; queda solo la etiqueta (`Card.tsx`) |
| El número grande saltaba de "405 alertas" a "26 focos" al cargar | Nielsen #1 visibilidad del estado | El banner espera a los focos en vivo; muestra "N llevan más de 24 h sin atender" (`StatusBanner.tsx`) |
| Botón "Ver alertas ↓" llevaba a "Qué atender"; flecha ↗ duplicada | Nielsen #2 lenguaje del usuario | Un solo botón: "Ver qué atender ↓" |
| Focos: 6 filtros de estado (5 en 0), tarjetas de ~110 px con 3 botones, "Por qué" y fórmula siempre visibles | Maeda · Reducir y Organizar; Nielsen #8 minimalismo | 3 grupos (Por atender / En curso / Cerrados); fila compacta: orden con color de prioridad, cama, enfermedad, plantas, tiempo, una acción; detalle al tocar la fila; "Ver 10 más"; fórmula en "¿Cómo se ordena?" (`FocosCard.tsx`) |
| "Etiquetas para el modelo: 0 nuevas · —" | Maeda · Reducir | Solo aparece cuando hay verificaciones |
| Mapa con cientos de círculos encimados y el rastro de 24 h del robot | Maeda · Organizar; Nielsen #8 | Vista "Focos" por defecto (un círculo por foco con su número de detecciones); "Cada detección" y "Ocultar" a un toque; rastro reciente y lecturas más tenues (`MapaCenital.tsx`) |
| "Alertas por cama" con una columna Cama 4 en 0 que no existe | Nielsen #2 correspondencia con el mundo real | Columnas y filas salen de los datos (`Charts.tsx`) |
| "Oídio domina: 34 %" con tres clases empatadas | Honestidad del dato | Si la primera no le saca más de 5 puntos a la segunda, el título dice "Parejas: …"; "Hoja sana 0" se oculta |
| Clima decía "riesgo de hongos" y Riesgo próximo decía "riesgo bajo" | Nielsen #4 consistencia | Clima solo describe T y HR; el riesgo lo dice una sola tarjeta, que explica por qué da bajo con hoja mojada y frío (`Riesgo.tsx`) |
| Tabla: "Saludables 0" clicable; "mostrando 602 de 602" | Nielsen #5 prevención de errores | Segmento deshabilitado si está vacío; título "Todas las detecciones · N" |

Verificado en el navegador a 1440 px y 375 px (móvil, sin scroll horizontal); `npm run build` pasa. Pendiente: probar con lector de pantalla y en tema oscuro.
