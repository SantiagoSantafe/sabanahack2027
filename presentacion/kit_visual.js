// kit_visual.js: implementacion de referencia VALIDADA del sistema visual de diseno.md (8 tipos de diapositiva).
// Los textos son EJEMPLO tomados de CIFRAS_CLAVE.md / INSTRUCCIONES.md; el grafico de linea (7L) usa datos inventados de ejemplo. Sin ROI, margen ni payback.
// Uso: NODE_PATH=<carpeta con node_modules de pptxgenjs> node kit_visual.js  ->  muestra_diseno.pptx
// Despues: python3.10+ <skill pptx>/scripts/office/validate.py muestra_diseno.pptx
const pptxgen = require('pptxgenjs');
const SK = process.env.PPTX_SKILL_DIR || '/Users/santiagosantafe/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/b5ecb203-139e-4c7b-8e84-197426d77227/1aae09a7-861d-4212-a319-95ec715080b1/skills/pptx';
const { applyTheme } = require(SK + '/scripts/apply_theme.js');

const THEME = {
  name: 'Berry Good Idea',
  headFontFace: 'Arial',
  bodyFontFace: 'Calibri',
  colors: {
    dk1: '0B2B1C', lt1: 'FFFFFF', dk2: '14452D', lt2: 'EAF5E1',
    accent1: '1E7A46', accent2: 'B8F04A', accent3: 'F2A33A',
    accent4: 'B8C7BD', accent5: '07170F', accent6: '4A5F53',
    hlink: '1E7A46', folHlink: '4A5F53',
  },
};
const HEX = { bosque900: '0B2B1C', bosque700: '14452D', hoja: '1E7A46', lima: 'B8F04A', ambar: 'F2A33A', gris: 'B8C7BD', ambarTxt: '8F4D05', muted: '4A5F53', menta: 'EAF5E1', grid: 'DCE9D5' };

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = 'Berry Good Idea (muestra del sistema visual)';
const C = pres.SchemeColor;
const W = 13.333, H = 7.5, L = 0.67, CW = 12.0;
const GAP = 0.3, COL3 = [0.67, 4.77, 8.87], W3 = 3.8; // 3 tarjetas: 3x3.8 + 2x0.3 = 12.0

// ---- fábricas (nunca compartir objetos de opciones entre llamadas) ----
const shCard = () => ({ type: 'outer', color: HEX.bosque900, blur: 16, offset: 4, angle: 90, opacity: 0.12 });
const shVideo = () => ({ type: 'outer', color: '000000', blur: 24, offset: 8, angle: 90, opacity: 0.30 });

// ---- layouts ----
const footer = (c) => [
  { text: { text: 'BERRY GOOD IDEA', options: { x: L, y: 6.75, w: 4, h: 0.25, fontSize: 10, bold: true, charSpacing: 4, color: c, margin: 0 } } },
];
const num = (c) => ({ x: 11.67, y: 6.75, w: 1.0, h: 0.25, fontSize: 10, color: c, align: 'right', margin: 0 });
pres.defineSlideMaster({
  title: 'CLARO', background: { color: C.background1 },
  objects: [
    ...footer(C.accent6),
    { placeholder: { options: { name: 'kicker', type: 'body', x: 0.98, y: 0.55, w: 8, h: 0.28, fontSize: 12, bold: true, charSpacing: 4, color: C.accent1, margin: 0, valign: 'middle', align: 'left' }, text: '' } },
    { placeholder: { options: { name: 'title', type: 'title', x: L, y: 0.88, w: CW, h: 0.8, fontSize: 36, bold: true, color: C.text1, margin: 0, valign: 'top', align: 'left' }, text: '' } },
  ],
  slideNumber: num(C.accent6),
});
pres.defineSlideMaster({
  title: 'OSCURO', background: { color: C.text1 },
  objects: [
    ...footer(C.accent4),
    { placeholder: { options: { name: 'kicker', type: 'body', x: 0.98, y: 0.55, w: 8, h: 0.28, fontSize: 12, bold: true, charSpacing: 4, color: C.accent2, margin: 0, valign: 'middle', align: 'left' }, text: '' } },
    { placeholder: { options: { name: 'title', type: 'title', x: L, y: 0.88, w: CW, h: 0.8, fontSize: 36, bold: true, color: C.background1, margin: 0, valign: 'top', align: 'left' }, text: '' } },
  ],
  slideNumber: num(C.accent4),
});
pres.defineSlideMaster({ title: 'MEDIA', background: { color: C.text1 } }); // portada, video a pantalla completa y cierre: sin pie ni numero

// ---- componentes ----
function ring(s, cx, cy, d, color, width, tr, name) {
  s.addShape(pres.ShapeType.ellipse, { objectName: name || 'ANILLO', x: cx - d / 2, y: cy - d / 2, w: d, h: d, fill: { type: 'none' }, line: { color, width, transparency: tr } });
}
function marker(s, color, y0 = 0.6) { // marcador kicker: anillo 0.2 + punto 0.08; y0 = y del kicker - 0.02
  s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_anillo', x: L, y: y0, w: 0.2, h: 0.2, fill: { type: 'none' }, line: { color, width: 1.5 } });
  s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_punto', x: L + 0.06, y: y0 + 0.06, w: 0.08, h: 0.08, fill: { color }, line: { type: 'none' } });
}
function videoFrame(s, id, label, x, y, w, h, opt = {}) {
  s.addText('Inserta aquí el video: ' + label, {
    shape: opt.round ? pres.ShapeType.roundRect : pres.ShapeType.rect, rectRadius: opt.round ? 0.12 : undefined,
    objectName: 'VIDEO_' + id, x, y, w, h, fill: { color: C.text2 }, line: { color: C.accent2, width: 1.5, dashType: 'dash' },
    color: C.background1, fontSize: opt.full ? 12 : 16, align: 'center', valign: opt.full ? 'top' : 'middle', margin: opt.full ? [10, 20, 0, 20] : 20, isTextBox: true, shadow: opt.shadow ? shVideo() : undefined,
  });
}
function imageFrame(s, id, label, x, y, w, h, opt = {}) {
  s.addText(label ? 'Reemplaza con imagen: ' + label : '', {
    shape: opt.full ? pres.ShapeType.rect : pres.ShapeType.roundRect, rectRadius: opt.full ? undefined : 0.12, objectName: 'IMAGEN_' + id, x, y, w, h,
    fill: { color: C.accent1 }, line: { color: C.background1, width: 1.5, dashType: 'dash' },
    color: C.background1, fontSize: opt.full ? 12 : 16, align: 'center', valign: opt.full ? 'top' : 'middle', margin: opt.full ? [10, 20, 0, 20] : 20, isTextBox: true,
  });
}
function slideFor(layout, section, kicker, title, dark) {
  const s = pres.addSlide({ masterName: layout, sectionTitle: section });
  marker(s, dark ? C.accent2 : C.accent1);
  s.addText(kicker, { placeholder: 'kicker' });
  s.addText(title, { placeholder: 'title' });
  return s;
}

// =============== 1 PORTADA ===============
pres.addSection({ title: 'Apertura' });
{
  const s = pres.addSlide({ masterName: 'MEDIA', sectionTitle: 'Apertura' });
  videoFrame(s, 'portada', 'robot D1 patrullando entre camas de arándano de noche (loop 10-15 s, sin audio)', 0, 0, W, H, { full: true });
  s.addShape(pres.ShapeType.rect, { objectName: 'CAPA_velo', x: 0, y: 0, w: W, h: H, fill: { color: C.accent5, transparency: 40 }, line: { type: 'none' } });
  ring(s, 11.4, 5.6, 6.4, C.accent2, 1.5, 70, 'ANILLO_3');
  ring(s, 11.4, 5.6, 4.4, C.accent2, 1.5, 55, 'ANILLO_2');
  ring(s, 11.4, 5.6, 2.4, C.accent2, 2.5, 35, 'ANILLO_1');
  marker(s, C.accent2, 1.29);
  s.addText('SABANA HACK  ·  2026', { objectName: 'portada_kicker', x: 0.98, y: 1.25, w: 7, h: 0.28, fontSize: 14, bold: true, charSpacing: 5, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
  s.addText('BERRY GOOD IDEA', { objectName: 'portada_titulo', x: L, y: 1.75, w: 8.2, h: 2.3, fontSize: 72, bold: true, color: C.background1, margin: 0, valign: 'top', lineSpacingMultiple: 0.9, isTextBox: true, fontFace: 'Arial' });
  s.addText('Los ojos que llegan a la cama exacta', { objectName: 'portada_subtitulo', x: L, y: 4.2, w: 8.2, h: 0.55, fontSize: 24, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
  s.addText('Detección temprana de enfermedades en arándano', { objectName: 'portada_apoyo', x: L, y: 4.85, w: 8.2, h: 0.4, fontSize: 16, color: C.accent4, margin: 0, valign: 'top', isTextBox: true });
}

// =============== 2 CIFRA-IMPACTO ===============
pres.addSection({ title: 'Problema' });
{
  const s = slideFor('CLARO', 'Problema', 'EL PROBLEMA', 'TRES CIFRAS QUE DUELEN', false);
  const data = [
    { lab: 'RECORRER 20 HA', n: '7–8', u: ' días', d: 'Hábiles, con 5 a 6 operarios, solo de día y en papel.', f: 'Fuente: dato de AGRAR, 24-oct-2026' },
    { lab: 'PÉRDIDA DE COSECHA', n: '10–25', u: ' %', d: 'Pérdida fitosanitaria, según el mentor de AGRAR.', f: 'Fuente: RESPUESTAS_MENTOR.md', hero: true },
    { lab: 'SIN PREVENCIÓN', n: '40', u: ' %', d: 'Pérdida máxima citada sin manejo preventivo.', f: 'Fuente: RESPUESTAS_MENTOR.md' },
  ];
  data.forEach((c, i) => {
    const x = COL3[i], y = 2.1, h = 4.2, dark = !!c.hero;
    s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_' + (i + 1), x, y, w: W3, h, rectRadius: 0.12, fill: { color: dark ? C.text1 : C.background2 }, line: { type: 'none' }, shadow: shCard() });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_anillo', x: x + 0.35, y: y + 0.4, w: 0.2, h: 0.2, fill: { type: 'none' }, line: { color: dark ? C.accent2 : C.accent1, width: 1.5 } });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_punto', x: x + 0.41, y: y + 0.46, w: 0.08, h: 0.08, fill: { color: dark ? C.accent2 : C.accent1 }, line: { type: 'none' } });
    s.addText(c.lab, { x: x + 0.68, y: y + 0.35, w: 2.75, h: 0.3, fontSize: 12, bold: true, charSpacing: 3, color: dark ? C.accent2 : C.accent1, margin: 0, valign: 'middle', isTextBox: true });
    s.addText([{ text: c.n, options: { fontSize: 66, bold: true, fontFace: 'Arial' } }, { text: c.u, options: { fontSize: 26, bold: true, fontFace: 'Arial' } }],
      { x: x + 0.35, y: y + 0.9, w: 3.1, h: 1.6, color: dark ? C.accent2 : C.text1, margin: 0, valign: 'middle', isTextBox: true });
    s.addText(c.d, { x: x + 0.35, y: y + 2.75, w: 3.1, h: 0.9, fontSize: 16, color: dark ? C.background1 : C.text1, margin: 0, valign: 'top', isTextBox: true });
    s.addText(c.f, { x: x + 0.35, y: y + 3.65, w: 3.1, h: 0.3, fontSize: 10, color: dark ? C.accent4 : C.accent6, margin: 0, valign: 'top', isTextBox: true });
  });
}

pres.addSection({ title: 'Solución' });
{
  const s = slideFor('OSCURO', 'Solución', 'LA MISMA NOCHE', 'UNA ALERTA, CINCO PASOS', true);
  ring(s, 12.9, 1.0, 5.2, C.accent2, 1.5, 88, 'ANILLO_deco');
  const steps = [
    ['01', 'Patrulla', 'El D1 recorre la cama que marca el riesgo.', '+0 min'],
    ['02', 'Clasifica', 'El Jetson lee la hoja: oídio, alternaria o sana.', '+1 min'],
    ['03', 'Localiza', 'Nave, cama y planta, con T y HR del punto.', '+2 min'],
    ['04', 'Alerta', 'Llega al panel del supervisor por LoRaWAN.', '+3 min'],
    ['05', 'Confirma', 'El operario revisa y queda en el registro.', '+5 min'],
  ];
  steps.forEach((st, i) => {
    const x = 0.67 + i * 2.5;
    s.addText(st[0], { x, y: 2.15, w: 1.0, h: 0.25, fontSize: 12, bold: true, charSpacing: 3, color: C.accent2, margin: 0, isTextBox: true });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'NODO_' + (i + 1), x, y: 2.5, w: 1.0, h: 1.0, fill: { color: C.text2 }, line: { color: C.accent2, width: 2 } });
    imageFrame(s, 'icono_paso' + (i + 1), null, x + 0.25, 2.75, 0.5, 0.5); // sustituir por PNG de react-icons
    if (i < 4) s.addShape(pres.ShapeType.line, { objectName: 'FLECHA_' + (i + 1), x: x + 1.15, y: 3.0, w: 1.2, h: 0, line: { color: C.accent2, width: 1.5, endArrowType: 'triangle', transparency: 30 } });
    s.addText(st[1], { x, y: 3.8, w: 2.0, h: 0.4, fontSize: 20, bold: true, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
    s.addText(st[2], { x, y: 4.35, w: 2.0, h: 1.2, fontSize: 16, color: C.accent4, margin: 0, valign: 'top', isTextBox: true });
    s.addText(st[3], { shape: pres.ShapeType.roundRect, rectRadius: 0.18, x, y: 5.75, w: 1.1, h: 0.36, fill: { color: C.accent2 }, line: { type: 'none' }, color: C.text1, fontSize: 12, bold: true, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
  });
}

// =============== 4 VIDEO PANTALLA COMPLETA ===============
pres.addSection({ title: 'Demo' });
{
  const s = pres.addSlide({ masterName: 'MEDIA', sectionTitle: 'Demo' });
  videoFrame(s, 'demo', 'grabación de la demo: el D1 gira, ve la hoja y la alerta aparece en el panel', 0, 0, W, H, { full: true });
  s.addShape(pres.ShapeType.rect, { objectName: 'CAPA_velo', x: 0, y: 0, w: W, h: H, fill: { color: C.accent5, transparency: 80 }, line: { type: 'none' } });
  // rótulo superior
  s.addShape(pres.ShapeType.roundRect, { objectName: 'ROTULO_pastilla', x: L, y: 0.6, w: 2.4, h: 0.45, rectRadius: 0.22, fill: { color: C.accent5, transparency: 25 }, line: { type: 'none' } });
  s.addShape(pres.ShapeType.ellipse, { x: L + 0.2, y: 0.74, w: 0.16, h: 0.16, fill: { color: C.accent2 }, line: { type: 'none' } });
  s.addText('DEMO EN VIVO', { x: L + 0.5, y: 0.6, w: 1.8, h: 0.45, fontSize: 12, bold: true, charSpacing: 4, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
  // tarjeta de cristal con el texto
  s.addShape(pres.ShapeType.roundRect, { objectName: 'CAPA_texto', x: L, y: 5.0, w: 7.4, h: 1.7, rectRadius: 0.14, fill: { color: C.accent5, transparency: 25 }, line: { type: 'none' } });
  s.addText('PASO 4  ·  ALERTA', { x: L + 0.35, y: 5.2, w: 6.7, h: 0.3, fontSize: 12, bold: true, charSpacing: 4, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
  s.addText('La alerta llega con nave, cama y planta', { x: L + 0.35, y: 5.55, w: 6.7, h: 1.0, fontSize: 28, bold: true, color: C.background1, margin: 0, valign: 'top', isTextBox: true, fontFace: 'Arial' });
  ring(s, 9.6, 3.0, 1.1, C.accent2, 3, 0, 'PING_hallazgo');
}

// =============== 5 VIDEO MITAD + 3 PUNTOS ===============
{
  const s = slideFor('CLARO', 'Solución', 'EL PANEL', 'EL SUPERVISOR VE Y ENVÍA', false);
  const pts = [['Foco localizado', 'Nave, cama y planta en el mapa del bloque.'], ['Un clic para enviar', 'El supervisor asigna a un operario a confirmar.'], ['Todo queda registrado', 'Hojas enfermas y sanas, con T y HR.']];
  pts.forEach((p, i) => {
    const y = 2.0 + i * 1.5;
    s.addShape(pres.ShapeType.ellipse, { objectName: 'NUM_' + (i + 1), x: L, y, w: 0.55, h: 0.55, fill: { type: 'none' }, line: { color: C.accent1, width: 1.75 } });
    s.addText(String(i + 1), { x: L, y, w: 0.55, h: 0.55, fontSize: 16, bold: true, color: C.accent1, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
    s.addText(p[0], { x: 1.45, y: y - 0.02, w: 3.75, h: 0.4, fontSize: 18, bold: true, color: C.text1, margin: 0, valign: 'top', isTextBox: true });
    s.addText(p[1], { x: 1.45, y: y + 0.45, w: 3.75, h: 0.8, fontSize: 14, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
  });
  videoFrame(s, 'panel', 'grabación de pantalla del dashboard (16:9, 10-20 s, sin audio)', 5.62, 2.0, 7.05, 3.97, { round: true, shadow: true });
  s.addText('Panel web en tiempo real. Datos de la simulación.', { x: 5.62, y: 6.1, w: 7.05, h: 0.3, fontSize: 10, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
}

// =============== 6 BARRAS COMPARATIVO ===============
pres.addSection({ title: 'Evidencia' });
{
  const s = slideFor('CLARO', 'Evidencia', 'EVIDENCIA', 'LO QUE MIDIÓ LA CÁMARA DEL ROBOT', false);
  s.addChart(pres.charts.BAR, [{ name: 'Resultado (%)', labels: ['Enfermas con alerta', 'Sanas sin alarma', 'Enfermedad exacta', 'Falsas alarmas'], values: [78, 71, 54, 29] }], {
    objectName: 'GRAFICO_barras', x: L, y: 1.95, w: 7.6, h: 4.2, barDir: 'bar', barGapWidthPct: 45,
    chartColors: [HEX.hoja, HEX.hoja, HEX.gris, HEX.ambar],
    showTitle: true, title: 'Porcentaje sobre 68 hojas de laboratorio', titleFontSize: 12, titleColor: HEX.muted, titleFontFace: '+mn-lt', titleFontBold: false,
    showLegend: false, showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0" %"', dataLabelFontSize: 14, dataLabelFontBold: true, dataLabelColor: HEX.bosque900, dataLabelFontFace: '+mn-lt',
    catAxisLabelFontSize: 14, catAxisLabelColor: HEX.bosque900, catAxisLabelFontFace: '+mn-lt', catAxisOrientation: 'maxMin', catGridLine: { style: 'none' },
    valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 100, valGridLine: { style: 'none' },
  });
  s.addText('n = 54 enfermas y 14 sanas. Intervalos de confianza en el anexo.', { x: L, y: 6.2, w: 7.6, h: 0.3, fontSize: 10, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
  s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_destacado', x: 8.57, y: 2.1, w: 4.1, h: 4.2, rectRadius: 0.12, fill: { color: C.text1 }, line: { type: 'none' }, shadow: shCard() });
  s.addText('29 %', { x: 8.92, y: 2.5, w: 3.4, h: 1.3, fontSize: 66, bold: true, fontFace: 'Arial', color: C.accent3, margin: 0, valign: 'middle', isTextBox: true });
  s.addText('de falsas alarmas. Baja con cada confirmación del operario y con fotos locales en el piloto.', { x: 8.92, y: 3.95, w: 3.4, h: 1.6, fontSize: 16, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
  s.addText('Fuente: reentreno-camara.md', { x: 8.92, y: 5.9, w: 3.4, h: 0.3, fontSize: 10, color: C.accent4, margin: 0, valign: 'top', isTextBox: true });
}

// =============== 7 COSTO / FINANZAS: 3 KPI + GRAFICO (sin ROI ni margen, ver INSTRUCCIONES.md) ===============
pres.addSection({ title: 'Costo' });
function kpiRow(s, k) {
  k.forEach((c, i) => {
    const x = COL3[i], y = 1.95, dark = i === 1;
    s.addShape(pres.ShapeType.roundRect, { objectName: 'KPI_' + (i + 1), x, y, w: W3, h: 1.5, rectRadius: 0.12, fill: { color: dark ? C.text1 : C.background2 }, line: { type: 'none' }, shadow: shCard() });
    s.addText(c[0], { x: x + 0.35, y: y + 0.2, w: 3.1, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: dark ? C.accent2 : C.accent1, margin: 0, valign: 'middle', isTextBox: true });
    s.addText([{ text: c[1], options: { fontSize: 48, bold: true, fontFace: 'Arial' } }, { text: c[2], options: { fontSize: 20, bold: true, fontFace: 'Arial' } }], { x: x + 0.35, y: y + 0.55, w: 3.1, h: 0.8, color: dark ? C.accent2 : C.text1, margin: 0, valign: 'middle', isTextBox: true });
  });
}
function supuestos(s, bullets) {
  s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_supuestos', x: 8.87, y: 3.75, w: 3.8, h: 2.7, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: 'none' }, shadow: shCard() });
  s.addText('SUPUESTOS', { x: 9.17, y: 3.95, w: 3.2, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent1, margin: 0, valign: 'middle', isTextBox: true });
  s.addText(bullets.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < bullets.length - 1 } })), { x: 9.17, y: 4.35, w: 3.2, h: 1.9, fontSize: 14, color: C.text1, margin: 0, valign: 'top', paraSpaceAfter: 8, isTextBox: true });
}
{
  const s = slideFor('CLARO', 'Costo', 'COSTO DEL HARDWARE', 'EL ROBOT ES 66× MÁS BARATO', false);
  kpiRow(s, [['KIT D1 ULTRA SIN IVA', '≈ 35', ' M COP'], ['FRENTE A CÁMARAS FIJAS', '66×', ' menos'], ['FRENTE A HUMANOIDES', '4–8×', ' menos']]);
  s.addChart(pres.charts.BAR, [{ name: 'Costo (M COP)', labels: ['Cámaras fijas (por cama)', 'Humanoide A3 Ultra', 'Cuadrúpedo D1 MaxPro', 'Humanoide X2 Ultra', 'Kit D1 Ultra'], values: [2300, 278, 253, 151, 35] }], {
    objectName: 'GRAFICO_barras', x: L, y: 3.75, w: 7.9, h: 2.8, barDir: 'bar', barGapWidthPct: 35, chartColors: [HEX.gris, HEX.gris, HEX.gris, HEX.gris, HEX.hoja],
    showTitle: true, title: 'Millones de COP, escala logarítmica', titleFontSize: 12, titleColor: HEX.muted, titleFontFace: '+mn-lt', titleFontBold: false,
    showLegend: false, showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '#,##0', dataLabelFontSize: 12, dataLabelFontBold: true, dataLabelColor: HEX.bosque900, dataLabelFontFace: '+mn-lt',
    catAxisLabelFontSize: 12, catAxisLabelColor: HEX.bosque900, catAxisLabelFontFace: '+mn-lt', catAxisOrientation: 'maxMin', catGridLine: { style: 'none' },
    valAxisHidden: true, valAxisLogScaleBase: 10, valGridLine: { style: 'none' },
  });
  supuestos(s, ['Estimaciones del equipo, precios FOB de referencia', 'Sin cotización formal, TRM 3.185']);
}

// =============== 7L VARIANTE LINEA (datos de EJEMPLO, sin cifra real asignada) ===============
{
  const s = slideFor('CLARO', 'Costo', 'EJEMPLO DE LÍNEA', 'TRES KPI Y UNA SERIE EN EL TIEMPO', false);
  kpiRow(s, [['MÉTRICA A', '00', ' u.'], ['MÉTRICA B', '00', ' %'], ['MÉTRICA C', '00', ' u.']]);
  s.addChart(pres.charts.LINE, [
    { name: 'Serie propia (ejemplo)', labels: ['0', '1', '2', '3', '4', '5', '6'], values: [10, 20, 35, 45, 60, 72, 85] },
    { name: 'Referencia (ejemplo)', labels: ['0', '1', '2', '3', '4', '5', '6'], values: [10, 15, 20, 25, 30, 35, 40] },
  ], {
    objectName: 'GRAFICO_linea', x: L, y: 3.75, w: 7.9, h: 2.8, chartColors: [HEX.hoja, HEX.gris], lineSize: 3, lineDataSymbol: 'circle', lineDataSymbolSize: 8,
    showTitle: true, title: 'Unidad (ejemplo) por periodo', titleFontSize: 12, titleColor: HEX.muted, titleFontFace: '+mn-lt',
    showLegend: true, legendPos: 'b', legendFontSize: 12, legendColor: HEX.bosque900, legendFontFace: '+mn-lt',
    catAxisLabelFontSize: 12, catAxisLabelColor: HEX.muted, catAxisLabelFontFace: '+mn-lt', catGridLine: { style: 'none' },
    showCatAxisTitle: true, catAxisTitle: 'Periodo', catAxisTitleColor: HEX.muted, catAxisTitleFontSize: 12, catAxisTitleFontFace: '+mn-lt',
    valAxisLabelFontSize: 12, valAxisLabelColor: HEX.muted, valAxisLabelFontFace: '+mn-lt', valGridLine: { color: HEX.grid, size: 0.75 },
  });
  supuestos(s, ['Cada supuesto visible, nunca en las notas', 'Se mide en el piloto']);
  ring(s, 6.0, 4.9, 0.5, C.accent3, 2.5, 0, 'PING_dato_clave'); // posicion manual sobre el dato clave
}

// =============== VARIANTE 2B: CIFRAS SOBRE IMAGEN (diapositiva 2 del guion) ===============
{
  const s = pres.addSlide({ masterName: 'OSCURO', sectionTitle: 'Problema' });
  imageFrame(s, 'problema', 'operario con linterna y planilla en pasillo mojado al amanecer', 0, 0, W, H, { full: true });
  s.addShape(pres.ShapeType.rect, { objectName: 'CAPA_velo', x: 0, y: 0, w: W, h: H, fill: { color: C.accent5, transparency: 45 }, line: { type: 'none' } });
  marker(s, C.accent2);
  s.addText('EL PROBLEMA', { placeholder: 'kicker' });
  s.addText('LA PÉRDIDA ES ALTA Y LA RONDA, LENTA', { placeholder: 'title' });
  [['7–8', ' días', 'hábiles para recorrer 20 ha, en papel'], ['10–25', ' %', 'de la cosecha, pérdida fitosanitaria'], ['1', ' noche', 'para que alternaria aparezca']].forEach((c, i) => {
    const x = COL3[i], y = 2.3;
    s.addShape(pres.ShapeType.roundRect, { objectName: 'CAPA_cifra_' + (i + 1), x, y, w: W3, h: 3.4, rectRadius: 0.14, fill: { color: C.accent5, transparency: 25 }, line: { type: 'none' } });
    s.addText([{ text: c[0], options: { fontSize: 66, bold: true, fontFace: 'Arial' } }, { text: c[1], options: { fontSize: 26, bold: true, fontFace: 'Arial' } }], { x: x + 0.35, y: y + 0.45, w: 3.1, h: 1.6, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText(c[2], { x: x + 0.35, y: y + 2.2, w: 3.1, h: 0.9, fontSize: 18, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
  });
  s.addText('Ilustración generada. Fuente: mentor de AGRAR.', { x: L, y: 6.2, w: 8, h: 0.3, fontSize: 10, color: C.accent4, margin: 0, valign: 'top', isTextBox: true });
}

// =============== VARIANTE 6L: GRAFICO + DESTACADO + LIMITES (diapositiva 6 del guion) ===============
{
  const s = slideFor('CLARO', 'Evidencia', 'EVIDENCIA Y LÍMITES', '78 % DE ENFERMAS ALERTADAS', false);
  s.addChart(pres.charts.BAR, [{ name: 'Hojas con alerta (%)', labels: ['Heliothis', 'Oídio', 'Alternaria', 'Sanas (falsa alarma)'], values: [94, 82, 50, 29] }], {
    objectName: 'GRAFICO_barras', x: L, y: 1.95, w: 7.6, h: 3.25, barDir: 'bar', barGapWidthPct: 40,
    chartColors: [HEX.hoja, HEX.hoja, HEX.gris, HEX.ambar],
    showTitle: true, title: 'Hojas con alerta por clase (%)', titleFontSize: 12, titleColor: HEX.muted, titleFontFace: '+mn-lt', titleFontBold: false,
    showLegend: false, showValue: true, dataLabelPosition: 'outEnd', dataLabelFormatCode: '0" %"', dataLabelFontSize: 14, dataLabelFontBold: true, dataLabelColor: HEX.bosque900, dataLabelFontFace: '+mn-lt',
    catAxisLabelFontSize: 14, catAxisLabelColor: HEX.bosque900, catAxisLabelFontFace: '+mn-lt', catAxisOrientation: 'maxMin', catGridLine: { style: 'none' },
    valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 100, valGridLine: { style: 'none' },
  });
  s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_destacado', x: 8.57, y: 2.1, w: 4.1, h: 3.1, rectRadius: 0.12, fill: { color: C.text1 }, line: { type: 'none' }, shadow: shCard() });
  s.addText('29 %', { x: 8.92, y: 2.3, w: 3.4, h: 1.2, fontSize: 66, bold: true, fontFace: 'Arial', color: C.accent3, margin: 0, valign: 'middle', isTextBox: true });
  s.addText('de sanas con falsa alarma. Es la cifra que el piloto busca bajar.', { x: 8.92, y: 3.6, w: 3.4, h: 1.0, fontSize: 16, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
  s.addText('Fuente: reentreno-camara.md', { x: 8.92, y: 4.75, w: 3.4, h: 0.3, fontSize: 10, color: C.accent4, margin: 0, valign: 'top', isTextBox: true });
  s.addShape(pres.ShapeType.roundRect, { objectName: 'LIMITES_panel', x: L, y: 5.45, w: CW, h: 1.05, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: 'none' }, shadow: shCard() });
  s.addShape(pres.ShapeType.ellipse, { x: L + 0.3, y: 5.62, w: 0.2, h: 0.2, fill: { type: 'none' }, line: { color: C.accent3, width: 1.5 } });
  s.addShape(pres.ShapeType.ellipse, { x: L + 0.36, y: 5.68, w: 0.08, h: 0.08, fill: { color: C.accent3 }, line: { type: 'none' } });
  s.addText('LÍMITES QUE DECLARAMOS', { x: L + 0.7, y: 5.58, w: 6, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: HEX.ambarTxt, margin: 0, valign: 'middle', isTextBox: true });
  s.addText('Probado con 68 hojas de laboratorio mostradas a la cámara del robot, solo 14 sanas; alternaria es la clase débil; el riesgo ambiental no está validado contra enfermedad real. Por eso el robot sugiere y el supervisor manda a un operario a confirmar.',
    { x: L + 0.3, y: 5.92, w: 11.4, h: 0.5, fontSize: 12, color: C.text1, margin: 0, valign: 'top', isTextBox: true });
}

pres.addSection({ title: 'Cierre' });
{
  const s = pres.addSlide({ masterName: 'MEDIA', sectionTitle: 'Cierre' });
  videoFrame(s, 'cierre', 'plano abierto de la finca al amanecer o el robot alejándose (loop 10-15 s)', 0, 0, W, H, { full: true });
  s.addShape(pres.ShapeType.rect, { objectName: 'CAPA_velo', x: 0, y: 0, w: W, h: H, fill: { color: C.accent5, transparency: 35 }, line: { type: 'none' } });
  ring(s, 11.6, 1.6, 5.4, C.accent2, 1.5, 70, 'ANILLO_2');
  ring(s, 11.6, 1.6, 3.0, C.accent2, 2.5, 40, 'ANILLO_1');
  marker(s, C.accent2);
  s.addText('CIERRE', { x: 0.98, y: 0.55, w: 7, h: 0.28, fontSize: 12, bold: true, charSpacing: 4, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
  s.addText('DE 8 DÍAS HÁBILES\nA MINUTOS', { x: L, y: 1.1, w: 10.0, h: 1.9, fontSize: 60, bold: true, fontFace: 'Arial', color: C.background1, margin: 0, valign: 'top', lineSpacingMultiple: 0.9, isTextBox: true });
  s.addText('Los ojos que llegan a la cama exacta', { x: L, y: 3.15, w: 9.0, h: 0.5, fontSize: 24, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
  const steps = ['Piloto en la finca de AGRAR', 'Camas testigo y fotos locales', 'Operario confirma cada alerta'];
  steps.forEach((t, i) => {
    const x = COL3[i], y = 4.0;
    s.addShape(pres.ShapeType.roundRect, { objectName: 'CAPA_paso_' + (i + 1), x, y, w: W3, h: 1.05, rectRadius: 0.14, fill: { color: C.accent5, transparency: 25 }, line: { type: 'none' } });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: y + 0.4, w: 0.2, h: 0.2, fill: { type: 'none' }, line: { color: C.accent2, width: 1.5 } });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.36, y: y + 0.46, w: 0.08, h: 0.08, fill: { color: C.accent2 }, line: { type: 'none' } });
    s.addText(t, { x: x + 0.7, y, w: 2.8, h: 1.05, fontSize: 16, bold: true, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
  });
  s.addShape(pres.ShapeType.roundRect, { objectName: 'CAPA_limites', x: L, y: 5.3, w: CW, h: 1.3, rectRadius: 0.14, fill: { color: C.accent5, transparency: 18 }, line: { type: 'none' } });
  s.addShape(pres.ShapeType.ellipse, { x: L + 0.3, y: 5.5, w: 0.2, h: 0.2, fill: { type: 'none' }, line: { color: C.accent3, width: 1.5 } });
  s.addShape(pres.ShapeType.ellipse, { x: L + 0.36, y: 5.56, w: 0.08, h: 0.08, fill: { color: C.accent3 }, line: { type: 'none' } });
  s.addText('LÍMITES QUE DECLARAMOS', { x: L + 0.7, y: 5.46, w: 6, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent3, margin: 0, valign: 'middle', isTextBox: true });
  s.addText('Probado con 68 hojas de laboratorio mostradas a la cámara del robot, solo 14 sanas; alternaria es la clase débil; el riesgo ambiental no está validado contra enfermedad real. Por eso el robot sugiere y el supervisor manda a un operario a confirmar.',
    { x: L + 0.3, y: 5.8, w: 11.4, h: 0.72, fontSize: 14, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
}

(async () => {
  await pres.writeFile({ fileName: 'muestra_diseno.pptx' });
  await applyTheme('muestra_diseno.pptx', THEME);
  console.log('ok');
})();
