// build_deck.js · Berry Good Idea · pitch Sabana Hack 2026 (11 diapositivas + 2 de respaldo)
// Uso: cd presentacion && node build_deck.js  ->  BerryGoodIdea_pitch.pptx
// Parte de kit_visual.js (sistema visual validado de diseno.md). Reglas del equipo (INSTRUCCIONES.md): sin modelo de negocio.
// Marcos VIDEO_<id>: solo donde va video real (robot real, camara, dashboard, simulador). Las imagenes del equipo van incrustadas.
// Revision 24-oct-2026 (segunda ronda de QA): grafico de costos lineal y sin formato numerico del idioma, demo 16:9,
// limites mas legibles, cierre con imagen, matriz con costo solo de hardware.
// Tercera ronda de QA (24-oct-2026): demo con el robot completo visible (sin tarjetas encima), flujo de la diapositiva 4 coherente,
// diapositiva 7 mas ligera y con la decision falsa alarma / enfermedad sin ver, costo con cifras sobre las barras, escalabilidad sin franja extra.
const fs = require('fs');
const pptxgen = require('pptxgenjs');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const sharp = require('sharp');
const FA = require('react-icons/fa');

const SK = process.env.PPTX_SKILL_DIR || '/Users/santiagosantafe/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/b5ecb203-139e-4c7b-8e84-197426d77227/1aae09a7-861d-4212-a319-95ec715080b1/skills/pptx';
const { applyTheme } = require(SK + '/scripts/apply_theme.js');

const DIR = '/Users/santiagosantafe/Downloads/SabanaHack/presentacion/';
const IMG = DIR + 'imagenes/';
const REC = IMG + 'recortes/';
const OPT = IMG + 'optimizadas/';
// CON_VIDEOS=1 incrusta los videos grabados del equipo en sus marcos (archivo aparte, pesa ~120 MB)
const CON_VIDEOS = process.env.CON_VIDEOS === '1';
const OUT = DIR + (CON_VIDEOS ? 'BerryGoodIdea_pitch_con_videos.pptx' : 'BerryGoodIdea_pitch.pptx');
const VID = DIR + 'videos/';
const VIDEOS = {
  demoA_robot_real: 'demo_robot_ruta',   // D1 real caminando + simulador siguiéndolo (48 s)
  demoB_camara: 'camara_hojas',          // cámara del D1 leyendo hojas en pantalla: sana, oídio, alternaria (90 s)
  dashboard: 'panel_dashboard',          // detecciones en el gemelo, mapa cenital y focos en el panel (26 s)
  simulador: 'gemelo_simulador',         // gemelo digital: robot patrullando el bloque (38 s)
};

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
const HEX = { bosque900: '0B2B1C', bosque700: '14452D', hoja: '1E7A46', lima: 'B8F04A', ambar: 'F2A33A', gris: 'B8C7BD', ambarTxt: '8F4D05', muted: '4A5F53', menta: 'EAF5E1', grid: 'DCE9D5', blanco: 'FFFFFF' };

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = 'Berry Good Idea · Pitch Sabana Hack 2026';
pres.author = 'Equipo Berry Good Idea';
pres.subject = 'Los ojos que llegan a la cama exacta';
const C = pres.SchemeColor;
const W = 13.333, H = 7.5, L = 0.67, CW = 12.0;
const COL3 = [0.67, 4.77, 8.87], W3 = 3.8;

// ---- fabricas (nunca compartir objetos de opciones entre llamadas) ----
const shCard = () => ({ type: 'outer', color: HEX.bosque900, blur: 16, offset: 4, angle: 90, opacity: 0.12 });
const shVideo = () => ({ type: 'outer', color: '000000', blur: 24, offset: 8, angle: 90, opacity: 0.30 });

// ---- layouts (defineSlideMaster crea layouts) ----
const footer = (c) => [{ text: { text: 'BERRY GOOD IDEA', options: { x: L, y: 6.75, w: 4, h: 0.25, fontSize: 10, bold: true, charSpacing: 4, color: c, margin: 0 } } }];
const num = (c) => ({ x: 11.67, y: 6.75, w: 1.0, h: 0.25, fontSize: 10, color: c, align: 'right', margin: 0 });
const kickerPh = (c) => ({ placeholder: { options: { name: 'kicker', type: 'body', x: 0.98, y: 0.55, w: 8, h: 0.28, fontSize: 12, bold: true, charSpacing: 4, color: c, margin: 0, valign: 'middle', align: 'left' }, text: '' } });
const titlePh = (c) => ({ placeholder: { options: { name: 'title', type: 'title', x: L, y: 0.88, w: CW, h: 0.8, fontSize: 36, bold: true, color: c, margin: 0, valign: 'top', align: 'left' }, text: '' } });
function defineMasters() {
pres.defineSlideMaster({ title: 'CLARO', background: { path: OPT + 'fondo_claro.jpg' }, objects: [...footer(C.accent6), kickerPh(C.accent1), titlePh(C.text1)], slideNumber: num(C.accent6) });
pres.defineSlideMaster({ title: 'OSCURO', background: { path: OPT + 'fondo_oscuro.jpg' }, objects: [...footer(C.accent4), kickerPh(C.accent2), titlePh(C.background1)], slideNumber: num(C.accent4) });
pres.defineSlideMaster({ title: 'PORTADA', background: { path: OPT + 'fondo_oscuro.jpg' } }); // portada y cierre: sin pie ni numero
// video a pantalla completa: sin pie ni numero; el titulo (texto grande abajo a la izquierda) es un placeholder para que la diapositiva tenga titulo
pres.defineSlideMaster({ title: 'MEDIA', background: { color: C.text1 }, objects: [{ placeholder: { options: { name: 'title', type: 'title', x: 8.97, y: 3.75, w: 3.7, h: 1.65, fontSize: 24, bold: true, color: C.background1, margin: 0, valign: 'top', align: 'left' }, text: '' } }] });
}

// ---- dimensiones de las imagenes del equipo ----
const NAT = {
  'operario_noche.jpg': [1659, 948], 'operario_amanecer.jpg': [1536, 1024], 'hoja_oidio_hud.jpg': [1659, 948],
};

// ---- componentes ----
function ring(s, cx, cy, d, color, width, tr, name) {
  s.addShape(pres.ShapeType.ellipse, { objectName: name || 'ANILLO', x: cx - d / 2, y: cy - d / 2, w: d, h: d, fill: { type: 'none' }, line: { color, width, transparency: tr } });
}
function marker(s, color, y0 = 0.6, x0 = L) {
  s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_anillo', x: x0, y: y0, w: 0.2, h: 0.2, fill: { type: 'none' }, line: { color, width: 1.5 } });
  s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_punto', x: x0 + 0.06, y: y0 + 0.06, w: 0.08, h: 0.08, fill: { color }, line: { type: 'none' } });
}
// marco para el video real (se reemplaza en PowerPoint: Insertar > Video, mismo tamano y posicion). Siempre 16:9.
function videoFrame(s, id, label, x, y, w, h, opt = {}) {
  if (CON_VIDEOS && VIDEOS[id] && fs.existsSync(VID + VIDEOS[id] + '.mp4')) {
    const cover = 'data:image/png;base64,' + fs.readFileSync(VID + VIDEOS[id] + '_portada.png').toString('base64');
    s.addMedia({ type: 'video', path: VID + VIDEOS[id] + '.mp4', cover, objectName: 'VIDEO_' + id, x, y, w, h });
    return;
  }
  s.addText('▶ Inserta aquí el video: ' + label, {
    shape: opt.round ? pres.ShapeType.roundRect : pres.ShapeType.rect, rectRadius: opt.round ? 0.12 : undefined,
    objectName: 'VIDEO_' + id, x, y, w, h, fill: { color: C.text2 }, line: opt.line || { color: C.accent2, width: 1.5, dashType: 'dash' },
    color: C.background1, fontSize: opt.size || (opt.full ? 12 : 14), align: 'center', valign: opt.full ? 'top' : 'middle', margin: opt.full ? [20, 20, 0, 10] : 20, isTextBox: true, shadow: opt.shadow ? shVideo() : undefined,
  });
}
// foto que llena el marco sin deformar (cover). 'file' es la ruta absoluta del JPG/PNG optimizado o del recorte.
function photo(s, file, x, y, w, h, alt, name) {
  const base = file.split('/').pop();
  const [nw, nh] = NAT[base];
  s.addImage({ path: file, objectName: name || 'IMAGEN_' + base.replace(/\.(jpg|png)$/, ''), altText: alt, x, y, w, h: w * nh / nw, sizing: { type: 'cover', w, h } });
}
function renderTag(s, color, x = 7.6, y = 6.75, w = 3.9) {
  s.addText('Render conceptual', { objectName: 'PIE_render', x, y, w, h: 0.25, fontSize: 10, color, align: 'right', margin: 0, valign: 'top', isTextBox: true });
}
function slideFor(layout, section, kicker, title, dark) {
  const s = pres.addSlide({ masterName: layout, sectionTitle: section });
  marker(s, dark ? C.accent2 : C.accent1);
  s.addText(kicker, { placeholder: 'kicker' });
  s.addText(title, { placeholder: 'title' });
  return s;
}
function glass(s, name, x, y, w, h, tr = 25, r = 0.14) {
  s.addShape(pres.ShapeType.roundRect, { objectName: name, x, y, w, h, rectRadius: r, fill: { color: C.accent5, transparency: tr }, line: { type: 'none' } });
}
function pill(s, name, x, y, w, h, fill, text, o = {}) {
  s.addText(text, { shape: pres.ShapeType.roundRect, rectRadius: h / 2, objectName: name, x, y, w, h, fill: { color: fill }, line: { type: 'none' }, color: o.color || C.background1, fontSize: o.size || 14, bold: !!o.bold, align: o.align || 'left', valign: 'middle', margin: o.margin !== undefined ? o.margin : [14, 0, 0, 0], isTextBox: true, shadow: o.shadow ? shCard() : undefined });
}
async function iconPng(Comp, hex, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: '#' + hex, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return 'image/png;base64,' + buf.toString('base64');
}
// recorte con esquinas redondeadas (PNG con transparencia), mismo radio que las tarjetas del deck
async function roundedCrop(src, ext, out, rpx, inpaint) {
  let base = sharp(src);
  if (inpaint) base = await inpaintV(src, inpaint);
  const buf = await base.extract(ext).toBuffer();
  const mask = Buffer.from(`<svg width="${ext.width}" height="${ext.height}"><rect x="0" y="0" width="${ext.width}" height="${ext.height}" rx="${rpx}" ry="${rpx}" fill="#fff"/></svg>`);
  await sharp(buf).composite([{ input: mask, blend: 'dest-in' }]).png({ compressionLevel: 9 }).toFile(out);
}
// borra una franja (r = {x0, x1, y0, y1}) interpolando en vertical entre la fila de arriba y la de abajo
async function inpaintV(src, r) {
  const { data, info } = await sharp(src).raw().toBuffer({ resolveWithObject: true });
  const ch = info.channels, Wd = info.width, ya = r.y0 - 2, yb = r.y1 + 2;
  for (let x = r.x0; x <= r.x1; x++) {
    const a = (ya * Wd + x) * ch, b = (yb * Wd + x) * ch;
    for (let y = r.y0; y <= r.y1; y++) {
      const t = (y - ya) / (yb - ya);
      for (let c = 0; c < ch; c++) data[(y * Wd + x) * ch + c] = Math.round(data[a + c] * (1 - t) + data[b + c] * t);
    }
  }
  return sharp(data, { raw: { width: Wd, height: info.height, channels: ch } }).png();
}
// grafico de barras horizontales nativo, mismo estilo en todo el deck
function barChart(s, name, labels, values, colors, o) {
  const showValue = o.showValue !== false;
  const opts = {
    objectName: name, x: o.x, y: o.y, w: o.w, h: o.h, barDir: 'bar', barGapWidthPct: o.gap || 40, chartColors: colors,
    showTitle: true, title: o.title, titleFontSize: 12, titleColor: HEX.muted, titleFontFace: '+mn-lt', titleFontBold: false,
    showLegend: false, showValue, dataLabelFontSize: 13, dataLabelFontBold: true, dataLabelColor: HEX.bosque900, dataLabelFontFace: '+mn-lt',
    catAxisLabelFontSize: 13, catAxisLabelColor: HEX.bosque900, catAxisLabelFontFace: '+mn-lt', catAxisOrientation: 'maxMin', catGridLine: { style: 'none' },
    valAxisHidden: true, valAxisMinVal: o.min === undefined ? 0 : o.min, valAxisMaxVal: o.max, valGridLine: { style: 'none' },
  };
  if (showValue) { opts.dataLabelPosition = 'outEnd'; opts.dataLabelFormatCode = o.fmt; }
  s.addChart(pres.charts.BAR, [{ name: o.series, labels, values }], opts);
}
// frase obligatoria de limites (CIFRAS_CLAVE.md §6): se muestra completa solo en la diapositiva 7
const LIMITES = 'Probado con 68 hojas de laboratorio mostradas a la cámara del robot, solo 14 sanas; alternaria es la clase débil; el riesgo ambiental no está validado contra enfermedad real. Por eso el robot sugiere y el supervisor manda a un operario a confirmar.';

async function main() {
  // ---- optimizacion (JPG) y recortes de las imagenes del equipo (el logo STIHL queda fuera del archivo) ----
  fs.mkdirSync(REC, { recursive: true }); fs.mkdirSync(OPT, { recursive: true });
  const jpg = { quality: 88, mozjpeg: true };
  for (const f of ['fondo_claro', 'fondo_oscuro', 'operario_noche', 'operario_amanecer', 'hoja_oidio_hud']) await sharp(IMG + f + '.png').jpeg(jpg).toFile(OPT + f + '.jpg');
  await sharp(IMG + 'supervisor_tablet.png').extract({ left: 0, top: 250, width: 1030, height: 667 }).jpeg(jpg).toFile(REC + 'supervisor_sin_logo.jpg');
  await sharp(IMG + 'robot_heroe_mastil_alto.png').extract({ left: 1090, top: 150, width: 446, height: 289 }).jpeg(jpg).toFile(REC + 'plc_sensores_bloque.jpg');
  await sharp(IMG + 'robot_heroe_mastil_alto.png').extract({ left: 285, top: 0, width: 793, height: 1024 }).jpeg(jpg).toFile(REC + 'robot_portada.jpg');
  await sharp(IMG + 'hoja_oidio_hud.png').extract({ left: 0, top: 0, width: 1465, height: 948 }).jpeg(jpg).toFile(REC + 'hoja_oidio_hud_recorte.jpg');
  // portada y cierre: dos recortes distintos del mismo render, con esquinas redondeadas
  await roundedCrop(IMG + 'robot_heroe_mastil_alto.png', { left: 285, top: 0, width: 793, height: 1024 }, REC + 'robot_portada_r.png', 28);
  // el recorte del cierre empieza en x=690: se borra el final de la etiqueta HUD (x 690-716, y 196-240) para que no asome una 'R'
  await roundedCrop(IMG + 'robot_heroe_mastil_alto.png', { left: 690, top: 0, width: 630, height: 1024 }, REC + 'robot_cierre_r.png', 28, { x0: 688, x1: 721, y0: 192, y1: 246 });
  NAT['supervisor_sin_logo.jpg'] = [1030, 667]; NAT['plc_sensores_bloque.jpg'] = [446, 289]; NAT['robot_portada.jpg'] = [793, 1024]; NAT['hoja_oidio_hud_recorte.jpg'] = [1465, 948];
  NAT['robot_portada_r.png'] = [793, 1024]; NAT['robot_cierre_r.png'] = [630, 1024];
  defineMasters();

  const iRobot = await iconPng(FA.FaRobot, HEX.lima), iPhone = await iconPng(FA.FaMobileAlt, HEX.lima), iSpray = await iconPng(FA.FaSprayCan, HEX.lima);
  const iLora = await iconPng(FA.FaBroadcastTower, HEX.lima), iClima = await iconPng(FA.FaCloudSun, HEX.lima);

  // secciones
  ['Apertura', 'Problema', 'Solución', 'Demo', 'Evidencia', 'Costo', 'Escalabilidad y cierre', 'Respaldo'].forEach((t) => pres.addSection({ title: t }));

  // =============== 1 PORTADA ===============
  {
    const s = pres.addSlide({ masterName: 'PORTADA', sectionTitle: 'Apertura' });
    // el anillo se desplaza a la derecha y arriba: no cruza el titulo ni la leyenda; la foto lo tapa en parte
    ring(s, 11.2, 3.0, 7.2, C.accent2, 1.5, 55, 'ANILLO_1');
    photo(s, REC + 'robot_portada_r.png', 8.1, 0.75, 4.57, 5.9, 'Render conceptual del robot cuadrúpedo con mástil patrullando una nave de arándanos de noche, con la alerta de oídio, nave, cama, planta y T/HR', 'IMAGEN_robot_heroe');
    renderTag(s, C.accent4, 8.1, 6.72, 4.57);
    marker(s, C.accent2, 1.29);
    s.addText('SABANA HACK  ·  2026', { objectName: 'portada_kicker', x: 0.98, y: 1.25, w: 7, h: 0.28, fontSize: 14, bold: true, charSpacing: 5, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('BERRY GOOD\nIDEA', { objectName: 'portada_titulo', x: L, y: 1.75, w: 7.3, h: 2.3, fontSize: 72, bold: true, color: C.background1, margin: 0, valign: 'top', lineSpacingMultiple: 0.9, isTextBox: true, fontFace: 'Arial' });
    s.addText('Los ojos que llegan a la cama exacta', { objectName: 'portada_subtitulo', x: L, y: 4.2, w: 7.3, h: 0.55, fontSize: 24, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
    s.addText('Detección temprana de enfermedades en arándano, cama por cama', { objectName: 'portada_apoyo', x: L, y: 4.85, w: 7.3, h: 0.4, fontSize: 16, color: C.accent4, margin: 0, valign: 'top', isTextBox: true });
    s.addNotes(`Buenas, somos el equipo de Berry Good Idea. Les vamos a contar una noche en una finca de arándanos y cómo cambia cuando un robot llega a la cama exacta.

Recordatorio: no usar logos de AGRAR (no implica respaldo). La imagen es un render conceptual; el D1 real no tiene ruedas y se muestra con mástil y cámara.

TIEMPO · 5 min: 5 s · 3 min: 3 s (se queda) · 9 min: 8 s (se queda).`);
  }

  // =============== 2 GANCHO 2 A. M. ===============
  {
    const s = pres.addSlide({ masterName: 'OSCURO', sectionTitle: 'Apertura' });
    photo(s, OPT + 'operario_noche.jpg', 0, 0, W, H, 'Render conceptual: operario con linterna y planilla de papel en una nave de arándanos, de noche', 'IMAGEN_operario_noche');
    s.addShape(pres.ShapeType.rect, { objectName: 'CAPA_velo', x: 0, y: 0, w: W, h: H, fill: { color: C.accent5, transparency: 55 }, line: { type: 'none' } });
    marker(s, C.accent2);
    s.addText('UNA NOCHE EN LA FINCA', { placeholder: 'kicker' });
    s.addText('UNA NOCHE HÚMEDA PUEDE ABRIR UN FOCO', { placeholder: 'title' });
    [['2:00 a. m.', 'Hoja mojada y sin nadie revisando las camas'], ['> 10 h', 'de hoja mojada a 18–28 °C: puede brotar la alternaria'], ['6:00 a. m.', 'Entra el primer operario, con papel']].forEach((r, i) => {
      const y = 2.0 + i * 1.2;
      glass(s, 'CAPA_hora_' + (i + 1), L, y, 6.4, 1.05);
      s.addText(r[0], { x: L + 0.35, y, w: 2.75, h: 1.05, fontSize: 36, bold: true, fontFace: 'Arial', color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(r[1], { x: L + 3.2, y, w: 2.95, h: 1.05, fontSize: 16, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    });
    // las dos vias de propagacion (rubrica: como surgen y se propagan): alternaria por hoja mojada, Botrytis por humedad alta sostenida
    glass(s, 'CAPA_vias', L, 5.65, 6.4, 0.9);
    s.addText([{ text: 'Dos vías. ', options: { bold: true, color: C.accent2 } }, { text: 'Alternaria: hoja mojada de noche. Botrytis: humedad alta sostenida, varias noches.', options: { color: C.background1 } }], { objectName: 'TEXTO_vias', x: L + 0.3, y: 5.65, w: 5.8, h: 0.9, fontSize: 16, margin: 0, valign: 'middle', isTextBox: true });
    // la foto tapa el pie del layout: se repite como texto de la propia diapositiva
    s.addText('BERRY GOOD IDEA', { objectName: 'PIE_marca', x: L, y: 6.75, w: 4, h: 0.25, fontSize: 10, bold: true, charSpacing: 4, color: C.accent4, margin: 0, isTextBox: true });
    renderTag(s, C.accent4);
    s.addNotes(`Son las dos de la mañana. El invernadero condensa, la hoja queda mojada y puede abrirse un foco de alternaria de una noche a otra; el Botrytis, la más común y la que más cuesta, pide humedad alta sostenida durante varias noches. Los operarios entran a las seis, de día y con papel, y de noche nadie revisa las camas.

Precisión: el título dice "puede abrir un foco", no "basta una noche". La alternaria por hoja mojada está respaldada por el mentor de AGRAR (gutación: de noche el invernadero condensa y la enfermedad puede aparecer de una noche a otra) y por el manual de Torres 2015 (más de 10 h de hoja mojada a 18–28 °C). El Botrytis responde a humedad alta sostenida, no a una sola noche: por eso la diapositiva nombra las dos vías (así cubre cómo surgen y se propagan). No decir cuántos días tarda en verse un foco: el mentor dijo que depende del clima y no hay medición. "2:00 a. m." es una hora narrativa, no medida.

Honestidad con el gancho: la alternaria es la clase que peor mide el modelo (7 de 14 con alerta; ver diapositiva 7). Si preguntan: "la que mejor vemos no es esta; por eso el operario confirma", y el Botrytis no tiene clase visual: lo cubre el riesgo ambiental.

TIEMPO · 5 min: 18 s · 3 min: 10 s, ACORTAR a una sola frase · 9 min: 25 s, AMPLIAR con Botrytis (humedad alta sostenida, no una noche).`);
  }

  // =============== 3 PROBLEMA ===============
  {
    const s = pres.addSlide({ masterName: 'OSCURO', sectionTitle: 'Problema' });
    photo(s, OPT + 'operario_amanecer.jpg', 0, 0, W, H, 'Render conceptual: operario con linterna y planilla de papel recorriendo un pasillo mojado al amanecer', 'IMAGEN_operario_amanecer');
    s.addShape(pres.ShapeType.rect, { objectName: 'CAPA_velo', x: 0, y: 0, w: W, h: H, fill: { color: C.accent5, transparency: 40 }, line: { type: 'none' } });
    marker(s, C.accent2);
    s.addText('EL PROBLEMA', { placeholder: 'kicker' });
    s.addText('LA PÉRDIDA ES ALTA Y LA RONDA, LENTA', { placeholder: 'title' });
    const data = [
      ['7–8', ' días', 'hábiles para recorrer 20 ha: 5 a 6 operarios, solo de día y en papel'],
      ['10–25', ' %', 'de la cosecha se pierde por problemas fitosanitarios; hasta 40\u00A0% sin prevención'],
      ['1', ' defecto', 'en la fruta basta para que no se exporte'],
    ];
    data.forEach((c, i) => {
      const x = 6.9, y = 2.0 + i * 1.4, w = 5.77, h = 1.2;
      glass(s, 'CAPA_cifra_' + (i + 1), x, y, w, h);
      s.addText([{ text: c[0], options: { fontSize: 48, bold: true, fontFace: 'Arial' } }, { text: c[1], options: { fontSize: 22, bold: true, fontFace: 'Arial' } }], { x: x + 0.3, y, w: 2.6, h, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(c[2], { x: x + 3.0, y, w: 2.55, h, fontSize: 15, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    });
    glass(s, 'CAPA_fuentes', 6.9, 6.25, 5.77, 0.45, 35, 0.08);
    s.addText('Fuentes: dato del equipo con AGRAR (24-oct-2026) y mentor de AGRAR. El 10–25\u00A0% es todo lo fitosanitario, no solo lo que evita el robot; el piloto mide cuánto evita.', { objectName: 'PIE_fuentes', x: 7.05, y: 6.25, w: 5.5, h: 0.45, fontSize: 11, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    // la foto tapa el pie del layout: se repite como texto de la propia diapositiva
    s.addText('BERRY GOOD IDEA', { objectName: 'PIE_marca', x: L, y: 6.75, w: 4, h: 0.25, fontSize: 10, bold: true, charSpacing: 4, color: C.accent4, margin: 0, isTextBox: true });
    renderTag(s, C.accent4);
    s.addNotes(`Hoy, 5 a 6 operarios tardan de 7 a 8 días hábiles en recorrer una finca de unas 20 hectáreas: solo de día, en papel, y el agrónomo digita después. Mientras tanto se pierde entre 10 y 25\u00A0% de lo cosechado, hasta 40\u00A0% si no hay prevención, y un solo defecto en la fruta impide exportar. Eso es lo que está en juego para la finca.

Fuente: CIFRAS_CLAVE §1b (dato del equipo con AGRAR, 24-oct-2026: 7–8 días hábiles, 5–6 operarios, equivale a 9–11 días calendario) y RESPUESTAS_MENTOR §8 (10–25\u00A0%, 30–40\u00A0% sin prevención, un defecto impide exportar). Aplicar el porcentaje al valor de la cosecha sería un supuesto: aquí solo se muestra el porcentaje.

Alcance del 10–25\u00A0%: es la pérdida por todos los problemas fitosanitarios (incluidos Botrytis, trips y otros que este robot no ve). No decir que el robot evita todo ese porcentaje: es la parte que se pueda adelantar, y el piloto mide cuánto es. "1 defecto" se refiere a defectos de la fruta (no distingue su causa).

TIEMPO · 5 min: 22 s · 3 min: 12 s, ACORTAR a 2 cifras (7–8 días y 10–25\u00A0%) · 9 min: 40 s, AMPLIAR: 35–48 jornadas-persona por vuelta (5–6 operarios × 7–8 días) y 30–40\u00A0% de pérdida sin prevención.`);
  }

  // =============== 4 LA MISMA NOCHE ===============
  {
    const s = slideFor('CLARO', 'Solución', 'DEL PLC AL SUPERVISOR', 'LA MISMA NOCHE: ALERTA EN MINUTOS', false);
    // un solo sello para las tres columnas (todo el flujo es diseño y el tiempo es un objetivo): arriba a la derecha, sin tapar ninguna foto
    pill(s, 'SELLO_objetivo', 8.57, 0.5, 4.1, 0.34, C.accent3, 'OBJETIVO · SE VALIDA EN EL PILOTO', { color: C.text1, size: 12, bold: true, align: 'center', margin: 0 });
    const steps = [
      [REC + 'plc_sensores_bloque.jpg', 'PLC: bloque en riesgo', 'Los sensores de AGRAR marcan el bloque en riesgo (Botrytis, alternaria).', 'IMAGEN_paso1_plc', 'Render conceptual: gabinete PLC y sensor de temperatura y humedad en el poste de un bloque'],
      [REC + 'hoja_oidio_hud_recorte.jpg', 'Robot: cama exacta', 'La cámara ve oídio, alternaria y Heliothis; para Botrytis aporta T y HR de la cama.', 'IMAGEN_paso2_hoja', 'Render conceptual: hoja con oídio vista por la cámara del robot, con nave, cama, planta, temperatura y humedad'],
      [REC + 'supervisor_sin_logo.jpg', 'Supervisor: decide', 'Envía a un operario a confirmar o descartar; queda registro.', 'IMAGEN_paso3_supervisor', 'Render conceptual: supervisor con tablet viendo el mapa de focos del invernadero'],
    ];
    steps.forEach((st, i) => {
      const x = COL3[i], y = 1.95;
      s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_paso_' + (i + 1), x, y, w: W3, h: 3.8, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: 'none' }, shadow: shCard() });
      photo(s, st[0], x + 0.2, y + 0.2, 3.4, 2.05, st[4], st[3]);
      s.addShape(pres.ShapeType.ellipse, { objectName: 'NUM_' + (i + 1), x: x + 0.2, y: y + 2.4, w: 0.5, h: 0.5, fill: { type: 'none' }, line: { color: C.accent1, width: 1.75 } });
      s.addText(String(i + 1), { x: x + 0.2, y: y + 2.4, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: C.accent1, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
      s.addText(st[1], { x: x + 0.85, y: y + 2.4, w: 2.75, h: 0.5, fontSize: 18, bold: true, color: C.text1, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(st[2], { x: x + 0.2, y: y + 3.0, w: 3.4, h: 0.72, fontSize: 14, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
      if (i < 2) s.addShape(pres.ShapeType.chevron, { objectName: 'FLECHA_' + (i + 1), x: x + W3 + 0.05, y: y + 1.9, w: 0.2, h: 0.35, fill: { color: C.accent1 }, line: { type: 'none' } });
    });
    ['~5 bloques por noche; el PLC prioriza', 'Hoja sana: solo se registra, sin alerta', 'Objetivo: alerta en ≤ 5 min (por medir)'].forEach((t, i) => {
      pill(s, 'PASTILLA_' + (i + 1), COL3[i], 6.05, W3, 0.4, C.background1, t, { color: C.text1, size: 13, bold: true, shadow: true });
    });
    renderTag(s, C.accent6, 7.6, 6.75, 3.9);
    s.addNotes(`AGRAR ya mide el ambiente en cada bloque: cuando su PLC marca riesgo, el robot sale de noche a esa cama primero. Ve la hoja y mide temperatura y humedad en el punto: si es sana, solo la registra, sin alerta; si es sospechosa, viaja por LoRaWAN una alerta con nave, cama y planta. El supervisor la ve y manda a un operario a confirmar: el robot sugiere, la persona decide.

Cuidado con las afirmaciones (todo el flujo es diseño que se valida en el piloto: lo dice el sello naranja de arriba a la derecha, que cubre las tres columnas; el título ya no lleva "(objetivo)"):
• Estado del modelo predictivo de AGRAR: el mentor dijo que AGRAR "ya trabaja en" un modelo predictivo que corre en su controlador. No dijimos que ya marque bloques en producción; la demo usa clima de Open-Meteo o simulado, no un PLC. Decir "los sensores de AGRAR marcan el bloque" como diseño, no como algo ya integrado.
• "Minutos" es un OBJETIVO de latencia (de que el robot ve la hoja a que el supervisor ve la alerta), no una medición: cronometrar 5 repeticiones en el ensayo y, si sale distinto, cambiar el título por el número medido.
• Cómo sabe la cama: marcador en la cabecera + odometría; ambos NO están verificados en campo (el D1 no tiene ROS). Ya no está escrito en la tarjeta 2 (el sello "se valida en el piloto" cubre todo el flujo), pero hay que decirlo en voz alta si preguntan por la ubicación de la cama.
• Qué ve la cámara: oídio, alternaria y Heliothis (3 clases visuales). Botrytis, la principal, NO tiene clase visual: el PLC la marca por riesgo ambiental y el robot solo aporta T y HR de la cama. Por eso la tarjeta 2 no dice que el robot "confirma".
• Las pastillas de abajo van en el orden del flujo: 1 (PLC) ~5 bloques por noche y el PLC prioriza; 2 (robot) hoja sana solo se registra; 3 (supervisor) objetivo de alerta en ≤ 5 min, por medir.
• Cobertura: el robot cubre unos 5 bloques por noche (14\u00A0% de la finca). En una noche húmeda como la del gancho podrían estar en riesgo todos los bloques a la vez: el PLC prioriza por nivel de riesgo (cola de prioridad) y, si no alcanza, se necesita un segundo robot o la ronda del día siguiente. La vuelta de 40 bloques toma ~7 noches (3–12 según supuestos).
• Canal supervisor → operario: no hay wifi ni celular en los bloques (solo internet en la oficina) y el mentor no confirmó el canal real. Decir "así lo diseñamos y lo validamos en el piloto".
• Clasificar a bordo (Jetson) evita subir video: LoRaWAN lleva mensajes de cientos de bytes (por ejemplo "N2 C3 P41 · oídio · 87\u00A0% · 10,4 °C · 95\u00A0% HR"); las fotos se descargan por Wi-Fi local al volver a la base de carga (diseño, sin verificar en campo).
• Las tres imágenes son renders conceptuales. La del supervisor está recortada para no mostrar la marca de la fumigadora.

TIEMPO · 5 min: 28 s · 3 min: 17 s, ACORTAR (sin la rama "sana") · 9 min: 40 s, AMPLIAR: por qué prioriza (riesgo del PLC) y qué viaja por LoRaWAN.`);
  }

  // =============== 5 DEMO EN VIVO ===============
  {
    const s = pres.addSlide({ masterName: 'MEDIA', sectionTitle: 'Demo' });
    // A: robot real, 16:9 grande a la izquierda y SIN nada encima (el D1 camina por el suelo). B: panel de la camara, 16:9, a la derecha, apilado con el aviso.
    videoFrame(s, 'demoA_robot_real', 'el D1 real sale solo por la ruta entre dos filas de PCs (camas a escala de sala) y gira a izquierda y derecha. 16:9, sin audio; en vivo o plan B de 90 s', L, 0.9, 8.0, 4.5, { round: true, size: 14, shadow: true });
    videoFrame(s, 'demoB_camara', 'panel de cámara (16:9): hoja sana sin alerta; hoja enferma con alerta, T y HR', 8.97, 0.9, 3.7, 2.08, { round: true, size: 12, line: { color: C.background1, width: 1.25 } });
    pill(s, 'AVISO_demo', 8.97, 3.1, 3.7, 0.4, C.accent5, 'T y HR simuladas · Wi-Fi local', { size: 14, bold: true, align: 'center', margin: 0 });
    s.addShape(pres.ShapeType.roundRect, { objectName: 'ROTULO_pastilla', x: L, y: 0.3, w: 2.9, h: 0.45, rectRadius: 0.22, fill: { color: C.accent5, transparency: 25 }, line: { type: 'none' } });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'ROTULO_punto', x: L + 0.2, y: 0.445, w: 0.16, h: 0.16, fill: { color: C.accent2 }, line: { type: 'none' } });
    s.addText('DEMO EN VIVO', { x: L + 0.5, y: 0.3, w: 2.3, h: 0.45, fontSize: 14, bold: true, charSpacing: 4, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    // la unica frase grande es el titulo (placeholder, 24 pt, columna derecha bajo el aviso)
    s.addText('Hoja + T y HR + cama:\nsale alerta y registro', { placeholder: 'title' });
    // banda inferior delgada (0,65 in): entra / sale
    glass(s, 'CAPA_entra_sale', L, 5.65, CW, 0.65, 25, 0.12);
    s.addText([
      { text: 'ENTRA  ', options: { fontSize: 14, bold: true, charSpacing: 3, color: C.accent2 } },
      { text: 'foto de la hoja, T y HR y posición', options: { fontSize: 16, color: C.background1 } },
      { text: '      →      ', options: { fontSize: 16, bold: true, color: C.accent2 } },
      { text: 'SALE  ', options: { fontSize: 14, bold: true, charSpacing: 3, color: C.accent2 } },
      { text: 'alerta con nave · cama · planta, y registro', options: { fontSize: 16, color: C.background1 } },
    ], { objectName: 'TEXTO_entra_sale', x: L + 0.35, y: 5.65, w: CW - 0.7, h: 0.65, margin: 0, valign: 'middle', isTextBox: true });
    // declarar lo que NO es el kit (una linea; el detalle completo esta en las notas)
    s.addText('Demo con D1 EDU, cámara 1080p y modelo en portátil; el kit de finca (D1 Ultra, 4K con luz, Jetson) no se probó.', { objectName: 'PIE_demo_no_es_kit', x: L, y: 6.5, w: CW, h: 0.4, fontSize: 14, color: C.accent4, margin: 0, valign: 'middle', isTextBox: true });
    s.addNotes(`Entra una foto de la hoja, la temperatura, la humedad y la posición; sale una alerta y un registro. Aquí la hoja la muestra un PC, la T y HR son simuladas y el enlace es wifi, no LoRaWAN; en finca el sensor y la radio ya están en el kit. Miren primero una sana: no genera alerta, pero queda registrada. Ahora una enferma.

DECLARAR LO QUE NO ES EL KIT (en pantalla queda una línea; el detalle va aquí). ESTA DEMO: D1 EDU, cámara frontal de 1080p, el modelo corre en el portátil (no en el Jetson) y las hojas son fotos mostradas en pantalla; T y HR simuladas y enlace Wi-Fi local. KIT DE FINCA: D1 Ultra, cámara 4K con luz, Jetson a bordo, LoRaWAN, mástil. El mástil y la cámara 4K con iluminación no se probaron. El 78\u00A0% de la diapositiva 7 se midió con la cámara y la configuración de la demo, no con las del kit.

GUION DE LA DEMO (95 s):
• 0–10 s: "Dos filas de PCs son las camas, a escala de sala. El D1 sale por la ruta."
• 10–25 s: gira a la izquierda y a la derecha mirando cada "cama".
• 25–45 s: hoja sana (la elige el jurado): el panel la marca sana, punto verde en el mapa, queda en el registro, sin alerta.
• 45–70 s: hoja enferma (la elige el jurado): el robot se detiene; sale la alerta con nave · cama · planta y T/HR.
• 70–95 s: en el dashboard aparece el foco con la foto. Pasar a la diapositiva 6.

Si el modelo falla una hoja: "Eso es justo el 22\u00A0% de enfermas que se nos escapa, o el 29\u00A0% de falsas alarmas de la diapositiva 7." No repetirlo más de una vez. Si falla el robot o la red, pasar al video de respaldo (demo completa grabada, con cronómetro visible).

Riesgo: la ruta es autónoma o teleoperada: se decide en el ensayo y se dice en voz alta ("teleoperado" si lo es). La navegación por pasillo real en finca es desarrollo por construir (el D1 no tiene ROS). Evitar mirar pantalones o sillas: usar el filtro "¿hay hoja?" y el recorte de la región de interés.

ANTES DE PRESENTAR (pendiente del equipo, no está hecho): cronometrar la demo con 5 repeticiones y llevar la mediana de segundos de la foto al panel; añadir ese número al aviso de T y HR simuladas (a la derecha de la diapositiva). Sin ese número, "minutos" del lema de la diapositiva 11 sigue siendo un objetivo y se dice como objetivo. Los marcos no tienen video aún: probar el plan B completo con cronómetro visible.

Reemplazo de los marcos (ambos 16:9): VIDEO_demoA_robot_real es el marco grande de la izquierda (8,0 × 4,5 in, en x 0,67 y 0,90) y no lleva nada encima: el robot completo y la ruta entre las dos filas de PCs quedan a la vista. VIDEO_demoB_camara es el recuadro de 3,7 × 2,08 in arriba a la derecha, con el aviso de T y HR simuladas debajo. Seleccionar el marco, Insertar > Video (sin audio, reproducción "Al hacer clic"), mismo tamaño y posición, y borrar el marco. Añadir además un fotograma fijo de cada video (Formato de video > Fotograma de carátula) por si se exporta a PDF: ninguno existe todavía, así que el PDF saldrá con los marcos vacíos hasta que se inserten los videos.

TIEMPO · 5 min: 95 s (clímax) · 3 min: 60 s, una hoja sana y una enferma · 9 min: 150 s, AMPLIAR con una 2.ª ronda con hojas que elige el jurado y el cierre del foco.`);
  }

  // =============== 6 SUPERVISOR Y REGISTRO ===============
  {
    const s = slideFor('CLARO', 'Demo', 'EL PANEL', 'CADA HALLAZGO LO CIERRA UNA PERSONA', false);
    const pts = [['Foco localizado', 'Nave, cama, planta, T y HR en el mapa del bloque.'], ['Un clic envía al operario', 'Confirma o descarta; su respuesta queda como etiqueta para el modelo.'], ['Registro, también de sanas', 'Foto, clase, confianza, hora, ubicación, T y HR, estado y quién confirmó.']];
    pts.forEach((p, i) => {
      const y = 2.0 + i * 1.3;
      s.addShape(pres.ShapeType.ellipse, { objectName: 'NUM_' + (i + 1), x: L, y, w: 0.55, h: 0.55, fill: { type: 'none' }, line: { color: C.accent1, width: 1.75 } });
      s.addText(String(i + 1), { x: L, y, w: 0.55, h: 0.55, fontSize: 16, bold: true, color: C.accent1, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
      s.addText(p[0], { x: 1.45, y: y - 0.02, w: 3.9, h: 0.4, fontSize: 18, bold: true, color: C.text1, margin: 0, valign: 'top', isTextBox: true });
      s.addText(p[1], { x: 1.45, y: y + 0.42, w: 3.9, h: 0.7, fontSize: 14, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
    });
    videoFrame(s, 'dashboard', 'grabación del panel web (16:9, 20 a 40 s, sin audio): entra el foco "Cámara D1", el supervisor asigna, el operario verifica y se cierra; puntos verdes = sanas', 5.95, 1.95, 6.72, 3.78, { round: true, shadow: true });
    s.addText('Panel web con datos simulados más las detecciones del robot real.', { x: 5.95, y: 5.8, w: 6.72, h: 0.25, fontSize: 11, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
    s.addText('CICLO DE CADA HALLAZGO', { x: L, y: 5.8, w: 4.6, h: 0.25, fontSize: 11, bold: true, charSpacing: 3, color: C.accent1, margin: 0, valign: 'top', isTextBox: true });
    ['Nuevo', 'Asignado', 'Verificado', 'Tratado', 'Cerrado'].forEach((t, i) => {
      const x = L + i * 2.45, last = i === 4;
      pill(s, 'ESTADO_' + (i + 1), x, 6.15, 2.2, 0.4, last ? C.accent1 : C.background2, t, { color: last ? C.background1 : C.text1, size: 14, bold: true, align: 'center', margin: 0 });
      if (i < 4) s.addShape(pres.ShapeType.chevron, { objectName: 'FLECHA_estado_' + (i + 1), x: x + 2.2 + 0.03, y: 6.225, w: 0.19, h: 0.25, fill: { color: C.accent1 }, line: { type: 'none' } });
    });
    s.addNotes(`La alerta le llega al supervisor, no a un robot que decide solo: ve el foco, la cama, la temperatura y la humedad, y envía a un operario. El operario confirma o descarta, y esa respuesta queda como etiqueta. Las hojas sanas también se guardan, sin alerta: dicen dónde no hay problema. Cada hallazgo recorre cinco estados, y lo cierra una persona.

Qué se guarda por incidencia: foto, clase, confianza, hora, nave/cama/planta, T y HR, estado y quién confirmó. Ciclo: Nuevo → Asignado → Verificado → Tratado → Cerrado. Con el historial salen el mapa de focos y el porcentaje de falsas alarmas.

En vivo: hacer el clic de "Asignar" y "Verificar" en el dashboard.

Cuidado: la etiqueta del operario está DISEÑADA para reentrenar el modelo y reducir las falsas alarmas, pero eso es una hipótesis: aún no hay confirmaciones de operarios en campo y el piloto mide cuánto baja. No decir "su respuesta enseña al modelo" como algo ya demostrado. El dashboard muestra datos simulados más las detecciones del robot real.

El marco VIDEO_dashboard (16:9, 6,72 × 3,78 in) está vacío: insertar la grabación del panel, sin audio, reproducción "Al hacer clic", y añadir un fotograma fijo por si se exporta a PDF.

TIEMPO · 5 min: 17 s · 3 min: CORTAR (se cuenta en el último gesto de la demo) · 9 min: 35 s, AMPLIAR: vista cenital, cobertura y puntos ciegos.`);
  }

  // =============== 7 EVIDENCIA ===============
  {
    const s = slideFor('CLARO', 'Evidencia', 'EVIDENCIA Y LÍMITES', '78\u00A0% DETECTADAS · 29\u00A0% FALSAS ALARMAS', false);
    barChart(s, 'GRAFICO_evidencia', ['Heliothis (17/18)', 'Oídio (18/22)', 'Alternaria (7/14)', 'Falsa alarma en sanas (4/14)'], [94, 82, 50, 29], [HEX.hoja, HEX.hoja, HEX.ambar, HEX.muted], {
      x: L, y: 1.9, w: 7.6, h: 2.6, series: 'Hojas con alerta (%)', title: 'Hojas con alerta (%): en enfermas, más es mejor; en sanas, menos es mejor', fmt: '0" %"', max: 100, gap: 40,
    });
    // pie de n: las 68 son FOTOS en 21 grupos de rafagas (no 68 hojas independientes); una finca de Peru, un dia
    s.addText('n = 68 fotos (54 enfermas, 14 sanas) en 21 grupos de ráfagas · IC95 por grupo: 61–92\u00A0% y 0–71\u00A0% · DrBerry (CC BY 4.0): una finca de Perú, un día · sin prueba en finca', { objectName: 'PIE_n', x: L, y: 4.58, w: CW, h: 0.4, fontSize: 11, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
    s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_destacado', x: 8.57, y: 1.9, w: 4.1, h: 2.6, rectRadius: 0.12, fill: { color: C.text1 }, line: { type: 'none' }, shadow: shCard() });
    s.addText('78\u00A0%', { x: 8.92, y: 1.98, w: 3.4, h: 0.78, fontSize: 48, bold: true, fontFace: 'Arial', color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('de las enfermas con alerta (42 de 54)', { x: 8.92, y: 2.8, w: 3.5, h: 0.3, fontSize: 14, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
    s.addText('Falsas alarmas: 29\u00A0% (4 de 14)', { x: 8.92, y: 3.2, w: 3.5, h: 0.3, fontSize: 14, bold: true, color: C.accent3, margin: 0, valign: 'top', isTextBox: true });
    s.addText('Aprende de cada confirmación; el piloto mide cuánto baja.', { x: 8.92, y: 3.7, w: 3.5, h: 0.6, fontSize: 14, color: C.accent4, margin: 0, valign: 'top', isTextBox: true });
    s.addShape(pres.ShapeType.roundRect, { objectName: 'LIMITES_panel', x: L, y: 5.05, w: CW, h: 1.55, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: 'none' }, shadow: shCard() });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_anillo', x: L + 0.3, y: 5.17, w: 0.2, h: 0.2, fill: { type: 'none' }, line: { color: C.accent3, width: 1.5 } });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_punto', x: L + 0.36, y: 5.23, w: 0.08, h: 0.08, fill: { color: C.accent3 }, line: { type: 'none' } });
    s.addText('LÍMITES QUE DECLARAMOS', { x: L + 0.7, y: 5.13, w: 6, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: HEX.ambarTxt, margin: 0, valign: 'middle', isTextBox: true });
    s.addText([
      { text: '68 hojas de laboratorio, solo 14 sanas', options: { bullet: { indent: 14 }, breakLine: true } },
      { text: 'Alternaria es la clase débil', options: { bullet: { indent: 14 }, breakLine: true } },
      { text: 'Riesgo ambiental sin validar contra enfermedad real (única vía para Botrytis)', options: { bullet: { indent: 14 } } },
    ], { objectName: 'LIMITES_lista', x: L + 0.3, y: 5.43, w: 7.2, h: 0.78, fontSize: 14, color: C.text1, margin: 0, valign: 'top', isTextBox: true });
    s.addText('Por eso el robot sugiere y el supervisor manda a un operario a confirmar.', { x: L + 0.3, y: 6.25, w: 7.2, h: 0.28, fontSize: 14, bold: true, color: C.text1, margin: 0, valign: 'middle', isTextBox: true });
    // la decision que mas pregunta un jurado de negocios: que cuesta mas, falsa alarma o enfermedad sin ver
    s.addText('LA DECISIÓN', { x: L + 7.8, y: 5.13, w: 3.9, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: HEX.ambarTxt, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('Falsa alarma = una visita; enfermedad sin ver = una cama perdida. Hoy priorizamos menos visitas; el piloto fija el punto con el cliente y mide las alertas falsas por noche.', { objectName: 'DECISION_texto', x: L + 7.8, y: 5.43, w: 3.9, h: 1.1, fontSize: 14, color: C.text1, margin: 0, valign: 'top', isTextBox: true });
    s.addNotes(`Medimos con 68 fotos de hojas de laboratorio frente a la cámara del robot: de las enfermas, 42 de 54 disparan alerta (78 %) y 12 se nos escapan; falla sobre todo en alternaria, donde solo la mitad dispara alerta. Y marca 29 % de las sanas por error (4 de 14). La decisión es de negocio, no de modelo: una falsa alarma es una visita del operario; una enfermedad sin ver es una cama perdida. Hoy priorizamos menos visitas, y el piloto fija el punto con el cliente midiendo las alertas falsas por noche.

Datos (modelo en uso: modelo_camara): enfermas con alerta 42/54 = 78 % (IC95 por grupo 61–92 %); falsas alarmas 4/14 = 29 % (IC95 0–71 %); por clase: Heliothis 17/18, oídio 18/22, alternaria 7/14 (derivado de la matriz de confusión). Datos: DrBerry, CC BY 4.0, 410 hojas (278 entrenamiento, 64 validación, 68 prueba). Ojo con "68 hojas": son 68 FOTOS en 21 grupos de ráfagas (entrenamiento-evaluacion.md), con las 14 sanas en unos 5 grupos. Un 29 % puede ser una sola ráfaga, y diferencias de 1 a 3 imágenes no son significativas. Los datos son de una finca de Perú, de un día, y las hojas casi siempre desprendidas o en la mano: representan poco una planta en pie en Colombia. El pie de la diapositiva lo dice ("una finca de Perú, un día · sin prueba en finca").

El compromiso, dicho claro (y por qué NO se dice que una visita sale más barata que una cama perdida): el punto de operación elegido (umbral 0,986, corrección de color y auto-recorte) da 78 % de sensibilidad con 29 % de falsas alarmas. La versión cruda del mismo modelo da 85 % con 43 %: deja pasar menos enfermas (8 de 54 frente a 12 de 54) pero genera más visitas de más. Se eligió el primer punto para reducir visitas, a costa de dejar pasar 4 enfermas más sobre 54. Si el cliente valora más una cama perdida que una visita de más, el punto elegido le conviene menos que la versión cruda; por eso no está cerrado: el cliente define cuántas falsas alarmas por noche tolera (el mentor no lo respondió) y el piloto fija el punto, incluso volviendo a la versión cruda. La métrica que mide el piloto es "alertas falsas por noche" (y camas perdidas por semana), que es el costo real de la finca. Traducir el 29 % a carga operativa: con 5 bloques por noche, cuántas de las camas visitadas serían falsa alarma depende de la prevalencia real, que no está medida. No presentar el punto elegido como "preferimos alertar de más": es lo contrario.

Lo que NO se dice:
• No decir "sensibilidad 80 %" ni "especificidad 95 %": son del modelo anterior con imagen limpia.
• No mostrar "87/87 con 0/14 falsas alarmas": son recortes; alternaria se separa solo por tamaño.
• Con 14 sanas, diferencias de 1–3 imágenes no son significativas; el umbral 0,986 se eligió con solo 10 sanas de validación y es frágil; hay una sola sesión de fotos de cámara.
• El paso de 100 % a 29 % (un modelo que alertaba siempre daba 100 % de falsas alarmas) cambia a la vez fotos de la cámara, corrección de color y umbral, y cuesta sensibilidad: decir "con fotos de la cámara", no "con fotos de campo". Esa frase ya no está en pantalla.
• Que las falsas alarmas bajen con las confirmaciones del operario es una hipótesis (no hay confirmaciones de campo): decir "diseñado para aprender; el piloto mide cuánto baja".
• La enfermedad exacta se acierta ~54 %: la cámara sugiere, no diagnostica. El clasificador tiene 4 clases (alternaria, Heliothis, oídio, sana): trips, deficiencias u otros daños no tienen clase y pueden salir como falsa alarma. Reconoce 3 enfermedades, no otros daños.
• Fuera de DrBerry (60 hojas sanas de campo, otros países) el modelo anterior alertaba 73 %; el modelo en uso no se ha medido en campo.
• Botrytis, la enfermedad principal según el mentor, y la roya no tienen clase visual: solo las cubre la capa ambiental, que tampoco está validada contra enfermedad real. El 28–48 % de CIFRAS_CLAVE (que allí se llama "sensibilidad por día de alerta") es, según backtest-riesgo.md, la coincidencia entre el riesgo calculado con clima de modelo (Open-Meteo) y el calculado con 3 estaciones del IDEAM, en días de riesgo alto: NO es sensibilidad frente a enfermedad real, que no está medida (no hay datos de incidencia). Por eso ya no está en pantalla.

TIEMPO · 5 min: 27 s · 3 min: 20 s, se queda con el pie de límites · 9 min: 55 s, AMPLIAR: matriz de confusión, 410 hojas, prueba fuera del dataset y el 28–48 % con su definición correcta.`);
  }

  // =============== 8 POR QUÉ ESTA SOLUCIÓN ===============
  {
    const s = slideFor('CLARO', 'Evidencia', 'POR QUÉ ESTA SOLUCIÓN', 'EL PLC ANTICIPA, EL ROBOT SUGIERE', false);
    barChart(s, 'GRAFICO_alternativas', ['Híbrido: PLC + robot', 'Solo sensores fijos', 'Solo robot (D1 con mástil)', 'Kit en la aspersora', 'Robot con ruedas', 'Humanoide X2 Ultra'], [89, 75, 70, 57, 56, 42], [HEX.hoja, HEX.gris, HEX.gris, HEX.gris, HEX.gris, HEX.gris], {
      x: L, y: 1.95, w: 5.6, h: 3.8, series: 'Puntaje (0–100)', title: 'Puntaje del equipo, de 0 a 100 (híbrido: 89)', fmt: '0', max: 100, gap: 35,
    });
    s.addText('Puntajes del equipo, sin medir: «ubica la cama» y «robustez» se validan en el piloto.', { objectName: 'PIE_matriz', x: L, y: 5.85, w: 5.6, h: 0.7, fontSize: 14, color: C.accent6, margin: 0, valign: 'bottom', isTextBox: true });
    videoFrame(s, 'simulador', 'gemelo digital (16:9, 12 a 40 s, sin audio): la misma noche simulada; el PLC marca el bloque y el avatar del D1 va primero a esa cama', 6.47, 1.95, 6.2, 3.49, { round: true, shadow: true });
    s.addText('Gemelo digital: el PLC marca el bloque y el avatar va primero a esa cama. Datos simulados.', { x: 6.47, y: 5.48, w: 6.2, h: 0.3, fontSize: 12, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
    s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_aspersion', x: 6.47, y: 5.85, w: 6.2, h: 0.7, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: 'none' }, shadow: shCard() });
    s.addText([{ text: '¿Y la aspersión? ', options: { bold: true, color: C.accent1 } }, { text: 'Descartada: la decide el agrónomo de cada finca y el riesgo más fuerte aparece de noche.', options: { color: C.text1 } }], { x: 6.77, y: 5.85, w: 5.65, h: 0.7, fontSize: 14, margin: 0, valign: 'middle', isTextBox: true });
    s.addNotes(`La razón de fondo: el PLC de AGRAR anticipa con lo que ya existe, el robot llega a la cama exacta y sugiere con la cámara, y el operario confirma; juntos cubren lo que cada uno no ve. El título dice "sugiere" y no "confirma" porque el robot no diagnostica (enfermedad exacta ~54\u00A0%; Botrytis no tiene clase visual) y cada hallazgo lo cierra una persona (diapositivas 6 y 7). La idea original era ir con la aspersión. La descartamos porque AGRAR no asperja (lo decide el agrónomo de cada finca), porque el riesgo más fuerte aparece de noche con la hoja mojada y porque la aspersión llega después de aplicar, no antes. No la botamos: la misma plataforma recibe hallazgos de una cámara en la aspersora. Frente a seis alternativas, el híbrido saca 89 de 100. El video es el gemelo digital: la misma noche simulada, donde el PLC marca el bloque y el avatar va primero a esa cama (así lo dice el pie del video; si la grabación no lo muestra, cambiar el pie).

Los pesos por criterio (para quien pregunte; en pantalla solo queda el pie corto): anticipa, ubica la cama, costo, encaje, robustez y registro, con pesos del equipo. El híbrido incluye la red fija y queda primero en 91\u00A0% de las combinaciones de pesos probadas (10.560 de 11.628). Eso NO prueba que el híbrido sea mejor: prueba que el resultado no depende de un solo peso. Los puntajes son autoevaluación sin medir: "ubica la cama" (5/5 para el híbrido) depende de marcador y odometría, por verificar, y "robustez" (4) se asume sin ROS ni pasillos reales probados; ambos se validan en el piloto. Si preguntan por Ubica: bajarla a 4 le resta pocos puntos y el híbrido sigue primero (89 frente a 75 de la red fija).

Cómo se puntuó el Costo (recalculado solo con costo de hardware, consistente con la diapositiva 9; sin precios de venta): 5 = sin hardware nuevo (la red fija que AGRAR ya tiene); 4 = hasta 0,75 veces el costo del kit; 3 = alrededor de 1 vez; 2 = de 1,5 a 4 veces; 1 = más de 4 veces. Resultado: solo sensores fijos 5 (hardware nuevo 0); kit en la aspersora 4 (≈ 18 M COP, 5.679 USD × TRM 3.185); solo robot y híbrido 3 (kit de 34,85 M; en el híbrido la red ya existe); robot con ruedas 2 (≈ 89 M: Amiga de 22.500 USD FOB, factor de importación 1,14, más el resto del kit); humanoide X2 Ultra 1 (151 M, 4,3 veces). Los umbrales son del equipo y se fijaron DESPUÉS de ver los puntajes (el costo se puntuaba antes contra el presupuesto anterior y los nuevos umbrales de solo hardware reproducen los mismos puntajes): si un jurado de negocios lo lee como una regla ajustada a posteriori, la respuesta honesta es sí, y por eso el resultado no se apoya solo en el costo. Con el X2 Ultra en 2 (si se usara un corte de 5 veces) el híbrido sigue primero (humanoide 46 en vez de 42). Los puntajes de Costo no cambian respecto a la matriz anterior, y el 89 y el 91\u00A0% (10.560 de 11.628 combinaciones de pesos, en múltiplos de 5 con mínimo 5) tampoco. Las justificaciones de Costo del archivo datos/finanzas/agrar/matriz_justificaciones.csv son anteriores a esta regla y NO se citan; si preguntan cómo se puntuó el costo, la respuesta es el costo del hardware de la diapositiva 9.

Cuidado:
• Es una matriz AUTOEVALUADA con pesos del equipo; el híbrido incluye la red fija, así que casi siempre gana (primero en 91\u00A0% de 11.628 combinaciones de pesos; la red fija queda sobre el híbrido en 8\u00A0%). No usar el 91\u00A0% como prueba de que el híbrido es mejor. Puntajes: híbrido 89; solo sensores fijos 75; solo robot 70; kit en aspersora 57; ruedas 56; humanoide X2 Ultra 42. Con el costo al 30\u00A0% el híbrido saca 85,4.
• La diapositiva 9 compara el costo con alternativas que NO están en la matriz (cuadrúpedo D1 MaxPro, humanoide A3 Ultra, cámaras fijas): son referencias de costo, no puntuadas. De la diapositiva 9 solo el X2 Ultra está en la matriz. Las cámaras fijas tampoco son la "red fija" de esta matriz (que son sensores).
• "La aspersión no es diaria ni nocturna" NO está documentada (el mentor no respondió frecuencia ni cuánto hay que esperar tras aplicar): confirmar con un agrónomo o decir "según nuestro entendimiento". El horario de aspersión 6–14 h es un supuesto. El riesgo "nace de noche" solo está respaldado para la alternaria; Botrytis responde a humedad sostenida.
• El video de simulación solo debe mostrar métricas que salgan de batch.py con semilla; no hay resultados de "día de detección" en los archivos, no inventarlos. El marco VIDEO_simulador es 16:9 (6,2 × 3,49 in): insertar el video sin audio y añadir un fotograma fijo por si se exporta a PDF.

TIEMPO · 5 min: 20 s · 3 min: 10 s, una frase: aspersión descartada y "89 de 100" · 9 min: 40 s, AMPLIAR: matriz de 6 alternativas y barrido de pesos.`);
  }

  // =============== 9 COSTO DEL HARDWARE ===============
  {
    const s = slideFor('CLARO', 'Costo', 'COSTO DEL HARDWARE', '≈ 35 M COP; LAS ALTERNATIVAS, 4 A 8× MÁS', false);
    const x0 = L, y0 = 1.9;
    s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_kit', x: x0, y: y0, w: 4.3, h: 4.6, rectRadius: 0.12, fill: { color: C.text1 }, line: { type: 'none' }, shadow: shCard() });
    s.addText('KIT D1 ULTRA  ·  SIN IVA', { x: x0 + 0.3, y: y0 + 0.2, w: 3.7, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText([{ text: '≈ 34,85', options: { fontSize: 48, bold: true, fontFace: 'Arial' } }, { text: ' M COP', options: { fontSize: 20, bold: true, fontFace: 'Arial' } }], { x: x0 + 0.3, y: y0 + 0.48, w: 3.7, h: 0.8, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('≈ 41,5 M COP con IVA', { x: x0 + 0.3, y: y0 + 1.28, w: 3.7, h: 0.3, fontSize: 16, color: C.accent4, margin: 0, valign: 'middle', isTextBox: true });
    const bom = [['Robot D1 Ultra (IP54)', '27,22'], ['Batería de repuesto', '1,63'], ['Cámara 4K con iluminación', '1,27'], ['Base de carga', '2,20'], ['Jetson, T/HR, LoRaWAN, mástil, cableado', '2,53']];
    const rows = bom.map((r, i) => [
      { text: r[0], options: { color: i === 0 ? HEX.lima : HEX.blanco, bold: i === 0, fontSize: 14, fontFace: 'Calibri', align: 'left', valign: 'middle' } },
      { text: r[1], options: { color: i === 0 ? HEX.lima : HEX.blanco, bold: i === 0, fontSize: 14, fontFace: 'Calibri', align: 'right', valign: 'middle' } },
    ]);
    s.addTable(rows, { objectName: 'TABLA_desglose', x: x0 + 0.3, y: y0 + 1.7, w: 3.7, colW: [3.0, 0.7], rowH: [0.38, 0.38, 0.38, 0.38, 0.62], margin: 0, border: { type: 'none' } });
    s.addText('M COP sin IVA. Solo hardware: sin instalación, software ni mantenimiento.', { x: x0 + 0.3, y: y0 + 3.85, w: 3.7, h: 0.5, fontSize: 12, color: C.accent4, margin: 0, valign: 'top', isTextBox: true });
    // grafico: solo el kit y los robots (1x a 7x), con la cifra sobre cada barra (enteros: no dependen del separador decimal del idioma);
    // las veces van en el nombre de la categoria. Las camaras fijas (66x) se muestran aparte como cifra grande: aplastaban las demas barras.
    barChart(s, 'GRAFICO_costos', ['Kit D1 Ultra · 1×', 'Humanoide X2 Ultra · 4,3×', 'Cuadrúpedo industrial · 7×'], [34.85, 151, 253], [HEX.hoja, HEX.gris, HEX.gris], {
      x: 5.27, y: 1.9, w: 7.4, h: 2.3, series: 'Costo del hardware (M COP)', title: 'Costo del hardware (M COP, sin IVA) y veces el costo del kit', fmt: '0" M"', min: 0, max: 340, gap: 35,
    });
    s.addText('Humanoides: de 4 a 8 veces el costo (A3 Ultra ≈ 278 M, 8×: precio por confirmar).', { objectName: 'TEXTO_humanoides', x: 5.27, y: 4.22, w: 7.4, h: 0.32, fontSize: 14, bold: true, color: C.text1, margin: 0, valign: 'middle', isTextBox: true });
    // camaras fijas: cifra grande aparte (cota de orden de magnitud; cobertura no equivalente)
    s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_camaras', x: 5.27, y: 4.68, w: 7.4, h: 1.38, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: 'none' }, shadow: shCard() });
    s.addText('66×', { x: 5.6, y: 4.78, w: 1.9, h: 0.8, fontSize: 54, bold: true, fontFace: 'Arial', color: HEX.ambarTxt, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('≈ 2.300 M COP', { x: 5.6, y: 5.55, w: 2.1, h: 0.35, fontSize: 16, bold: true, color: C.text1, margin: 0, valign: 'middle', isTextBox: true });
    s.addText([
      { text: 'Cámaras fijas, una cada 10 m de cama: cota de orden de magnitud. Vigilan siempre; el robot pasa una vez por noche.', options: { fontSize: 14, color: C.text1, breakLine: true } },
      { text: '≈ 7.200 × 100 USD con cable, PoE y montaje; sin red ni almacenamiento.', options: { fontSize: 12, color: C.accent6 } },
    ], { objectName: 'TEXTO_camaras', x: 7.85, y: 4.78, w: 4.6, h: 1.18, margin: 0, valign: 'middle', paraSpaceAfter: 3, isTextBox: true });
    pill(s, 'ETIQUETA_estimaciones', 5.27, 6.2, 2.85, 0.3, C.accent3, 'ESTIMACIONES DEL EQUIPO', { color: C.text1, size: 11, bold: true, align: 'center', margin: 0 });
    s.addText('FOB de referencia · TRM 3.185 · sin IVA', { objectName: 'PIE_costos', x: 8.3, y: 6.2, w: 4.37, h: 0.3, fontSize: 12, color: C.accent6, margin: 0, valign: 'middle', isTextBox: true });
    s.addNotes(`Todo el hardware de una finca cuesta unos 35 millones de pesos sin IVA, unos 41,5 con IVA: el robot, una batería de repuesto, la cámara 4K con iluminación para la noche, el computador a bordo, el sensor de temperatura y humedad, el módulo LoRaWAN, el mástil y la base de carga. Es solo hardware: sin instalación, software ni mantenimiento. La fuente y la caja ya las tiene AGRAR. Para comparar: un humanoide cuesta entre 4 y 8 veces más y un cuadrúpedo industrial, 7 veces; cubrir la finca con cámaras fijas costaría unos 2.300 millones, 66 veces el kit. Decirlo en voz alta: es una cota de orden de magnitud y la cobertura no es equivalente (las cámaras vigilan siempre; el robot pasa por una cama cada ~7 noches). El precio al que se ofrezca el sistema lo define AGRAR: aquí mostramos solo el costo del hardware.

Cifras (M COP sin IVA; estimaciones del equipo, precios FOB de referencia sin cotización formal, TRM 3.185): kit D1 Ultra 34,85; humanoide X2 Ultra 151 (4,3×); cuadrúpedo D1 MaxPro 253 (7×); cámaras fijas 2.300 (66×); cámaras por planta 4.600–11.500 (no se muestra). Humanoide A3 Ultra ≈ 278 (8×): SIN BARRA y marcado "precio por confirmar", porque el repositorio no trae precio del A3 ("a consultar") y el 278 coincide con el D1 MaxPro puesto con IVA (277,4 M) y con el G1: puede ser un rótulo cruzado. Antes de mostrarlo como dato, confirmar con finanzas a qué robot corresponde. Desglose del kit en M COP: robot 27,22; batería de repuesto 1,63; cámara 4K con iluminación 1,27; base de carga (caseta, cargador, UPS, punto de acceso) 2,20; y, juntos, 2,53 de Jetson 0,90 + sensor T/HR 0,22 + LoRaWAN/Modbus 0,29 + mástil 0,80 + cableado 0,32. Suma 34,85. Opcional: cámara térmica, +0,9 M. Con el D1 EDU el kit baja a ~29,8 M (34,85 menos 5,07 M de diferencia en el robot), pero no declara protección IP.

Cuidado:
• Cambios de esta ronda: el gráfico ya no incluye las cámaras (66× aplastaba las demás barras y el kit era una raya); ahora muestra kit, X2 Ultra y cuadrúpedo con la cifra sobre cada barra, y las cámaras van como cifra grande aparte. Las cifras de las barras son enteros (formato 0 "M"; el título del gráfico dice M COP) para que se lean igual en cualquier idioma del computador; las veces (1×, 4,3×, 7×) van en el nombre de la categoría. El título dice "4 a 8×" y no "1,5 % de las cámaras".
• El título se apoya en lo más sólido: el kit frente a humanoides y cuadrúpedo. Las cámaras (2.300 M) son la cifra menos respaldada del deck: supuesto de 7.200 cámaras × 100 USD con cable, PoE y montaje (documento de costos del equipo; no está en el repositorio) y excluye red y almacenamiento. Una cámara de 100 USD no equivale a la 4K con luz del kit (unos 350 USD) y vigila todas las camas de forma continua, no una pasada por noche: no son comparables uno a uno. "Cámaras fijas" no es una alternativa evaluada en la matriz de la diapositiva 8 (allí la red fija son sensores).
• Las cifras de humanoides y cuadrúpedo industrial son estimaciones del equipo; el FOB del X2 Ultra (39.999 USD) y del MaxPro (67.999 USD) no está verificado. De la comparación solo el X2 Ultra está en la matriz de la diapositiva 8; el resto son referencias de costo.
• "66×" significa: cubrir con cámaras costaría 66 veces el kit (2.300 / 34,85); el kit es el 1,5 % de esa cifra. No decir "66 veces menos".
• 34,85 M frente a 35,40 M del modelo interno: la diferencia (~0,55 M) es la fuente DC-DC, SSD y caja del cómputo que AGRAR ya tiene. Decir "≈ 35 M sin IVA".
• Un solo D1 recorre la finca en ~7 noches (rango 3–12); dos robots cambian el costo. El D1 a precio de tienda cuesta 9.600 USD frente a 7.499 FOB: falta la cotización formal.
• No hay modelo comercial en este deck: si preguntan, el precio lo fija AGRAR.

TIEMPO · 5 min: 35 s (10 s el kit, 25 s la comparación) · 3 min: 31 s, se queda · 9 min: 70 s, AMPLIAR: variantes de hardware (D1 EDU, cámara térmica) y cuánto cuesta cada alternativa por finca.`);
  }

  // =============== 10 ESCALABILIDAD ===============
  {
    const s = slideFor('OSCURO', 'Escalabilidad y cierre', 'ESCALABILIDAD', 'REGISTRO ÚNICO, DISEÑADO PARA ESCALAR', true);
    const fuentes = [[iRobot, 'Robot cuadrúpedo', 'HOY'], [iPhone, 'Celular del operario', 'DISEÑO'], [iSpray, 'Cámara en la aspersora', 'DISEÑO'], [iLora, 'Sensores LoRaWAN de los PLC', 'DISEÑO'], [iClima, 'Pronóstico por coordenada', 'DISEÑO']];
    fuentes.forEach((f, i) => {
      const y = 1.95 + i * 0.52;
      s.addShape(pres.ShapeType.roundRect, { objectName: 'FUENTE_' + (i + 1), x: L, y, w: 3.7, h: 0.44, rectRadius: 0.22, fill: { color: C.text2 }, line: { type: 'none' } });
      s.addImage({ data: f[0], objectName: 'ICONO_fuente_' + (i + 1), altText: f[1], x: L + 0.14, y: y + 0.09, w: 0.26, h: 0.26 });
      s.addText(f[1], { x: L + 0.5, y, w: 2.3, h: 0.44, fontSize: 13, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
      const hoy = f[2] === 'HOY';
      pill(s, 'ESTADO_fuente_' + (i + 1), L + 2.8, y + 0.09, 0.84, 0.26, hoy ? C.accent2 : C.accent5, f[2], { color: hoy ? C.text1 : C.accent3, size: 11, bold: true, align: 'center', margin: 0 });
    });
    s.addText('HOY = funciona en la demo · DISEÑO = se valida en el piloto', { objectName: 'LEYENDA_estado', x: L, y: 4.6, w: 4.9, h: 0.3, fontSize: 14, color: C.accent4, margin: 0, valign: 'middle', isTextBox: true });
    s.addShape(pres.ShapeType.rightArrow, { objectName: 'FLECHA_entrada', x: 4.6, y: 3.0, w: 0.65, h: 0.4, fill: { color: C.accent2 }, line: { type: 'none' } });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'NODO_registro', x: 5.45, y: 2.0, w: 2.5, h: 2.5, fill: { color: C.text2 }, line: { color: C.accent2, width: 2 } });
    s.addText([{ text: 'REGISTRO DE\nINCIDENCIAS', options: { fontSize: 16, bold: true, fontFace: 'Arial', color: C.background1, breakLine: true } }, { text: 'un solo formato', options: { fontSize: 12, color: C.accent2 } }], { x: 5.45, y: 2.0, w: 2.5, h: 2.5, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
    s.addShape(pres.ShapeType.rightArrow, { objectName: 'FLECHA_salida', x: 8.2, y: 3.0, w: 0.65, h: 0.4, fill: { color: C.accent2 }, line: { type: 'none' } });
    s.addText('FINCAS, CADA UNA AISLADA', { x: 9.05, y: 1.95, w: 3.62, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    ['Finca A · bloques, naves, camas', 'Finca B · otra región (ejemplo)', 'Finca C · otro cultivo (ejemplo)'].forEach((t, i) => {
      pill(s, 'FINCA_' + (i + 1), 9.05, 2.35 + i * 0.5, 3.62, 0.4, C.text2, t, { size: 13 });
    });
    s.addText('CULTIVOS: UN PERFIL CADA UNO', { x: 9.05, y: 3.98, w: 3.62, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    ['Arándano', 'Fresa', 'Mora'].forEach((t, i) => {
      pill(s, 'CULTIVO_' + (i + 1), 9.05 + i * 1.26, 4.35, 1.1, 0.4, C.accent2, t, { color: C.text1, size: 13, bold: true, align: 'center', margin: 0 });
    });
    // la marca del pie cae sobre las ondas brillantes: se repite en blanco como texto de la diapositiva para que mantenga el contraste
    s.addText('BERRY GOOD IDEA', { objectName: 'PIE_marca', x: L, y: 6.75, w: 4, h: 0.25, fontSize: 10, bold: true, charSpacing: 4, color: C.background1, margin: 0, isTextBox: true });
    glass(s, 'CAPA_hero', L, 5.15, CW, 1.1, 10);
    s.addText([{ text: '< 2', options: { fontSize: 48, bold: true, fontFace: 'Arial' } }, { text: ' %', options: { fontSize: 24, bold: true, fontFace: 'Arial' } }], { x: L + 0.4, y: 5.15, w: 2.6, h: 1.1, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('del arándano de Colombia, Perú, Chile y México está en Colombia (cálculo del equipo): crecer es llegar a otras fincas y regiones.', { x: L + 3.1, y: 5.15, w: 8.6, h: 1.1, fontSize: 16, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    s.addNotes(`La Sabana es solo nuestro ejemplo: la solución está pensada para otras fincas y otras regiones. El diseño es un mismo registro de incidencias que recibe hallazgos del robot, del celular del operario, de una cámara en la aspersora, de los sensores de los PLC y del pronóstico, y cada finca es una empresa aislada de las demás. Colombia es menos del 2\u00A0% del arándano de cuatro países, así que esto nace pensado para otras fincas y regiones.

Qué existe hoy y qué es diseño: el formato de incidencia es un esquema JSON validado con 20 casos sintéticos. Hoy solo el robot genera datos; el celular del operario, la cámara en la aspersora y los sensores de los PLC son diseño (por eso la etiqueta DISEÑO). Las fincas B y C son ejemplos, no clientes.

Qué cambiaría con otro frutal (la pregunta de la rúbrica; antes iba en una franja al pie y ahora vive solo aquí y en la diapositiva 13): no es solo un archivo de configuración. Hace falta un perfil de riesgo del cultivo, fotos y clases visuales nuevas, reentrenar el modelo y un ciclo de cultivo de piloto para validarlo (ESCALABILIDAD §4). Los perfiles de fresa y mora existen en el motor de riesgo (22 modelos y 6 motores), pero se validan en el motor, no en campo.

Sobre el 2\u00A0%: ≈ 1.000 de ≈ 54.500 ha (Colombia, Perú, Chile y México; cálculo del equipo, ESCALABILIDAD §8.1; las hectáreas salieron de la pantalla para aligerarla). Otro frutal: perfil de riesgo + fotos y clases nuevas + un ciclo de piloto; fresa y mora: solo en el motor de riesgo, sin validar en campo. Quiere decir que casi todo el arándano de esos países está fuera de Colombia; no prueba por sí solo que haya demanda: eso lo mide el piloto.

Cuidado: "cada finca mejora a todas" es una hipótesis. El multi-cliente tiene 2 casos de ataque abiertos documentados: no decir "seguro". Esta diapositiva no muestra precios ni planes: eso lo define AGRAR.

Dos bloques de la finca de ejemplo: Bloque 1 (naves 1–2) y Bloque 2 (naves 3–4), con camino central de 5–6 m.

TIEMPO · 5 min: 15 s · 3 min: CORTAR (una frase dentro del cierre) · 9 min: 40 s, AMPLIAR: etapas del piloto y efecto de los datos de varias fincas.`);
  }

  // =============== 11 CIERRE ===============
  {
    const s = pres.addSlide({ masterName: 'PORTADA', sectionTitle: 'Escalabilidad y cierre' });
    ring(s, 10.9, 3.65, 6.0, C.accent2, 1.5, 55, 'ANILLO_1');
    photo(s, REC + 'robot_cierre_r.png', 9.1, 0.75, 3.57, 5.8, 'Render conceptual del robot cuadrúpedo con mástil patrullando una nave de arándanos de noche, con un gabinete PLC y un sensor al fondo', 'IMAGEN_robot_cierre');
    renderTag(s, C.accent4, 9.1, 6.62, 3.57);
    marker(s, C.accent2);
    s.addText('CIERRE', { objectName: 'cierre_kicker', x: 0.98, y: 0.55, w: 7, h: 0.28, fontSize: 12, bold: true, charSpacing: 4, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('DE 8 DÍAS HÁBILES\nA MINUTOS', { objectName: 'cierre_titulo', x: L, y: 1.0, w: 8.2, h: 1.8, fontSize: 56, bold: true, fontFace: 'Arial', color: C.background1, margin: 0, valign: 'top', lineSpacingMultiple: 0.9, isTextBox: true });
    s.addText('Alerta en minutos donde hay riesgo;\nvuelta completa en ~7 noches.', { objectName: 'cierre_aclaracion', x: L, y: 2.9, w: 7.4, h: 0.75, fontSize: 20, bold: true, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
    s.addText('A las 2:00 a. m. el robot ya está en la cama;\na las 6:00 a. m. el operario sabe adónde ir.', { objectName: 'cierre_gancho', x: L, y: 3.72, w: 7.4, h: 0.75, fontSize: 18, color: C.accent2, margin: 0, valign: 'top', isTextBox: true });
    glass(s, 'CAPA_piloto', L, 4.6, 6.9, 2.0, 18);
    s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_anillo', x: L + 0.3, y: 4.78, w: 0.2, h: 0.2, fill: { type: 'none' }, line: { color: C.accent3, width: 1.5 } });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_punto', x: L + 0.36, y: 4.84, w: 0.08, h: 0.08, fill: { color: C.accent3 }, line: { type: 'none' } });
    s.addText('PILOTO EN 1 FINCA, CON Y SIN ROBOT · POR VALIDAR', { x: L + 0.7, y: 4.74, w: 6, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent3, margin: 0, valign: 'middle', isTextBox: true });
    ['Navegar pasillos reales', 'Carga y autonomía (1–2 h)', 'Quién acompaña de noche', 'Fotos y clima de campo'].forEach((t, i) => {
      pill(s, 'PENDIENTE_' + (i + 1), L + 0.3 + (i % 2) * 3.2, 5.15 + Math.floor(i / 2) * 0.46, 3.05, 0.38, C.text2, t, { size: 13, bold: true, margin: [12, 0, 0, 0] });
    });
    s.addText('Éxito: falsas alarmas por noche ≤ X, acordado con el cliente; adelanto medido frente a camas testigo; ≥ 90\u00A0% de camas recorridas; robot ≥ 85\u00A0% operativo.', { objectName: 'CRITERIOS_piloto', x: L + 0.3, y: 6.08, w: 6.4, h: 0.48, fontSize: 13, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    s.addNotes(`Esto no está terminado y lo decimos: probamos con hojas de laboratorio, no con una finca. Volvamos a las dos de la mañana: hoy nadie revisa las camas hasta que entra el primer operario, de día y con papel. Con el robot, a las dos de la mañana el robot ya está en la cama en riesgo y a las seis el operario sabe adónde ir. Y lo decimos en voz alta: hoy el D1 pide línea de vista; el piloto define quién acompaña de noche y a qué costo. Hoy, 7 a 8 días hábiles; con el robot, la cama en riesgo se revisa esa misma noche y la alerta llega en minutos. De 8 días hábiles a minutos.

Honestidad sobre el lema (por eso la línea visible, ahora a 20 pt, "Alerta en minutos donde hay riesgo; vuelta completa en ~7 noches"; decirla en voz alta): "minutos" es la latencia de la alerta (objetivo de ≤ 5 min de la foto al panel, aún sin cronometrar; mostrar el número medido de la demo si ya está). Un D1 recorre la vuelta completa de 40 bloques en ~7 noches (3–12 según supuestos), unos 5 bloques por noche, pero cada noche empieza por las camas de mayor riesgo; el contraste no es "cubre todo en minutos" sino alerta en minutos donde hay riesgo, todas las noches, sin papel ni digitación. Un jurado de negocios hará la cuenta: 7 noches contra 9–11 días calendario de hoy no es "minutos"; por eso se dice así. No decir cuántos días de adelanto da la alerta: no hay medición de adelanto.

Qué falta para una finca real (los cuatro pendientes de la pantalla): navegar pasillos reales (el D1 no tiene ROS; pasillos de 6,8 m); carga automática y autonomía de 1–2 h; quién acompaña de noche (el manual del D1 exige línea de vista: si hace falta una persona, cambia el mensaje de "robot sin gente" y el costo operativo; RESUMEN.md deja la pregunta abierta); fotos y clima de campo para reentrenar y para validar el riesgo ambiental con incidencia real. También: IP54, cotización formal del D1 y medir cuántas pérdidas se evitan.

Criterios de éxito del piloto (supuestos del equipo, a acordar con el cliente): falsas alarmas por noche ≤ X, con X acordado con el cliente (la unidad es la alerta por cama, que puede agregar varias fotos); adelanto medido frente a camas testigo, sin fijar días porque hoy nadie midió cuánto tarda en verse un foco; ≥ 90\u00A0% de camas recorridas; robot operativo ≥ 85\u00A0%. Se quitó el "≥ 70\u00A0% de alertas confirmadas": con sensibilidad de 78\u00A0% y 29\u00A0% de falsas alarmas solo se alcanza si cerca de la mitad de lo que mira el robot está enfermo, y con una prevalencia realista de pocos puntos la precisión por foto sería muy baja. La frase obligatoria de límites está en la diapositiva 7.

TIEMPO · 5 min: 18 s · 3 min: 17 s, se queda · 9 min: 37 s, AMPLIAR: lista completa de lo que falta (fotos de campo andino y reentreno con confirmaciones; navegación en pasillos de 6,8 m, carga automática y línea de vista del manual; IP54 y autonomía de 1–2 h; cotización formal del D1; medir cuántas pérdidas se evitan).`);
  }

  // =============== 12 RESPALDO · SUPUESTOS Y FUENTES ===============
  {
    const s = slideFor('CLARO', 'Respaldo', 'RESPALDO', 'SUPUESTOS Y FUENTES', false);
    const hdr = (t) => ({ text: t, options: { bold: true, color: HEX.blanco, fill: { color: HEX.bosque900 }, fontSize: 12, fontFace: 'Calibri', valign: 'middle' } });
    const cell = (t, o = {}) => ({ text: t, options: Object.assign({ color: HEX.bosque900, fontSize: 11, fontFace: 'Calibri', valign: 'middle' }, o) });
    const data = [
      ['Kit D1 Ultra', '≈ 34,85 M COP sin IVA (≈ 41,5 M con IVA)', 'Documento de costo del equipo. Solo hardware. FOB de referencia, sin cotización formal, TRM 3.185. Fuente y caja: las tiene AGRAR'],
      ['Cámaras fijas (1 cada 10 m de cama)', '≈ 2.300 M COP (66×)', 'ESTIMACIÓN del equipo: ≈ 7.200 cámaras × 100 USD con cable, PoE y montaje; sin red ni almacenamiento. No equivalen a la cámara del kit y vigilan siempre, no una pasada por noche'],
      ['Humanoides y cuadrúpedo industrial', '151 · 253 M COP; A3 Ultra ≈ 278 por confirmar', 'ESTIMACIÓN del equipo; FOB sin verificar (X2 Ultra, D1 MaxPro). El A3 Ultra no tiene precio propio en el repositorio: no se grafica'],
      ['Matriz de alternativas', '89 de 100 (híbrido); primero en 91\u00A0% de los pesos', 'Autoevaluación del equipo, 6 criterios, sin medir (Ubica y Robustez se validan en el piloto). El 91\u00A0% indica que no depende de un solo peso; costo solo con hardware'],
      ['Monitoreo manual hoy', '5–6 operarios, 7–8 días hábiles, ~20 ha', 'Dato del equipo con AGRAR, 24-oct-2026. Solo de día, en papel'],
      ['Pérdida fitosanitaria', '10–25\u00A0% (hasta 40\u00A0% sin prevención)', 'Mentor de AGRAR; no es medición propia ni lo que evita el robot'],
      ['Clasificador', '78\u00A0% de enfermas con alerta; 29\u00A0% de falsas alarmas', '68 fotos de laboratorio en 21 grupos de ráfagas (DrBerry, CC BY 4.0) frente a la cámara; 14 sanas; IC95 61–92\u00A0% y 0–71\u00A0%. Una finca de Perú, un día; sin prueba en finca'],
      ['Riesgo ambiental', 'Botrytis y antracnosis', 'Modelos de fresa como proxy; sin validar contra enfermedad real. El 28–48\u00A0% es la coincidencia con una estación IDEAM, no sensibilidad. Botrytis solo se cubre por esta vía'],
      ['Latencia de la alerta', '"Minutos" (objetivo ≤ 5 min)', 'Objetivo de diseño, aún sin cronometrar; se mide en el piloto'],
      ['Capacidad de un robot', '~19 ha por semana; 40 bloques en ~7 noches', 'Modelo del equipo (rango 3–12 noches); sin medir en finca'],
      ['Demo', 'D1 EDU, cámara frontal 1080p, modelo en portátil; fotos en pantalla; T y HR simuladas; Wi-Fi local', 'El kit de finca (D1 Ultra, cámara 4K con luz, Jetson a bordo) no se probó. Ruta autónoma o teleoperada: se declara'],
    ];
    const rows = [[hdr('Dato en el deck'), hdr('Valor'), hdr('De dónde sale y qué tan firme es')]].concat(data.map((r, i) => r.map((t, j) => cell(t, { bold: j === 0, fill: { color: i % 2 === 0 ? HEX.menta : HEX.blanco } }))));
    s.addTable(rows, { objectName: 'TABLA_supuestos', x: L, y: 1.75, w: CW, colW: [2.4, 3.4, 6.2], rowH: 0.36, margin: [2, 6, 2, 6], border: { type: 'solid', color: HEX.grid, pt: 0.75 } });
    s.addNotes(`Diapositiva de respaldo: solo se muestra si el jurado pregunta por una cifra. Estado de cada dato: FUENTE (mentor o documento), ESTIMACIÓN del equipo (sin cotización ni medición propia) o SIN VALIDAR.

Esta ronda: las cámaras citan ya el supuesto del documento del equipo (100 USD con cable, PoE y montaje; sin red ni almacenamiento); el A3 Ultra no se grafica; los "68" son fotos en 21 grupos de ráfagas; el 28–48\u00A0% se define como coincidencia con una estación del IDEAM (backtest-riesgo.md), no como sensibilidad.

Este deck no presenta modelo comercial: AGRAR define su precio. Lo que se muestra es el costo del hardware y lo que está en juego para la finca (pérdidas de 10–25\u00A0%, hasta 40\u00A0% sin prevención; monitoreo manual de 7–8 días hábiles para 20 ha).

Licencias: DrBerry CC BY 4.0; PlantVillage CC BY-SA; dataset de fresa de Mendeley CC BY-NC (solo evaluación); YOLO/ultralytics AGPL-3.0; Open-Meteo gratuita solo para uso no comercial, con atribución "Weather data by Open-Meteo.com".`);
  }

  // =============== 13 RESPALDO · PREGUNTAS DEL JURADO ===============
  {
    const s = slideFor('CLARO', 'Respaldo', 'RESPALDO', 'PREGUNTAS DEL JURADO', false);
    const qa = [
      ['¿Cuánto cuesta y quién fija el precio?', 'Hardware de una finca: ≈ 34,85 M COP sin IVA (≈ 41,5 M con IVA), FOB sin cotización formal. El precio lo fija AGRAR. En juego: 10–25\u00A0% de pérdidas.'],
      ['¿Y las falsas alarmas y lo que no detecta?', '29\u00A0% de sanas con alerta (4 de 14) y 22\u00A0% de enfermas sin alerta. Versión cruda: 85\u00A0% con 43\u00A0%. Son 68 hojas: intervalos anchos. Debe bajar con las confirmaciones; el piloto lo mide.'],
      ['Si AGRAR ya predice con sus PLC, ¿qué agrega el robot?', 'El PLC marca el bloque en riesgo; no ve la planta ni ubica la cama. Oídio y mildiu solo se saben viéndolos. Lo que suma sobre el PLC se mide en el piloto.'],
      ['¿Un solo robot alcanza? ¿Y si se daña?', 'De noche cubre ~19 ha por semana: 40 bloques en ~7 noches (3–12), empezando por las camas en riesgo. Si falla, los PLC siguen vigilando.'],
      ['¿Sirve en otra finca u otro frutal?', 'El registro tiene el mismo formato venga de robot, celular o cámara. Otro frutal pide perfil de riesgo, fotos y clases nuevas y un ciclo de piloto.'],
    ];
    qa.forEach((q, i) => {
      const col = i % 3, row = Math.floor(i / 3);
      const x = COL3[col], y = 1.95 + row * 2.3;
      s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_pregunta_' + (i + 1), x, y, w: W3, h: 2.15, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: 'none' }, shadow: shCard() });
      s.addText(q[0], { x: x + 0.25, y: y + 0.15, w: 3.3, h: 0.5, fontSize: 14, bold: true, color: C.accent1, margin: 0, valign: 'top', isTextBox: true });
      s.addText(q[1], { x: x + 0.25, y: y + 0.68, w: 3.3, h: 1.4, fontSize: 14, color: C.text1, margin: 0, valign: 'top', isTextBox: true });
    });
    s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_regla', x: COL3[2], y: 1.95 + 2.3, w: W3, h: 2.15, rectRadius: 0.12, fill: { color: C.text1 }, line: { type: 'none' }, shadow: shCard() });
    s.addText('SI NO SABEMOS', { x: COL3[2] + 0.25, y: 4.4, w: 3.3, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('Lo decimos y lo medimos en el piloto: cuántas falsas alarmas tolera el cliente, cuántas pérdidas se evitan y cuánto tarda la alerta no están medidos aún.', { x: COL3[2] + 0.25, y: 4.78, w: 3.3, h: 1.3, fontSize: 14, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
    s.addNotes(`Diapositiva de respaldo con las preguntas más probables de un jurado de negocios, sin modelo comercial.

1. ¿Cuánto cuesta y quién fija el precio? El hardware es ≈ 34,85 M COP sin IVA. El precio al que se ofrezca lo define AGRAR; nosotros mostramos el costo del hardware y lo que está en juego para la finca.
2. Falsas alarmas y no detectadas: 29\u00A0% y 22\u00A0%, con solo 68 hojas y 14 sanas; los intervalos son anchos y lo decimos. El compromiso es explícito: el punto elegido da 78\u00A0% de sensibilidad con 29\u00A0% de falsas alarmas; la versión cruda del modelo da 85\u00A0% con 43\u00A0%. La decisión es de negocio: una falsa alarma es una visita del operario y una enfermedad sin ver es una cama perdida; hoy priorizamos menos visitas (el punto elegido deja pasar 12 de 54 enfermas, más que la versión cruda con 8), y el piloto fija el punto con el cliente midiendo las alertas falsas por noche. Cuántas falsas alarmas tolera el cliente lo fija el piloto (el mentor no lo respondió). Que bajen con cada confirmación del operario es una hipótesis: el piloto mide cuánto.
3. PLC frente a robot: el mentor dijo que oídio y mildiu "solo se saben viéndolos". Botrytis, la principal, la cubre la capa ambiental, no la cámara. AGRAR ya trabaja en un modelo predictivo en su controlador: parte de la mejora ya la captura el PLC y lo que suma el robot se mide en el piloto.
4. Capacidad: ~19 ha por semana de noche, 40 bloques en ~7 noches (3–12 según supuestos), unos 5 bloques por noche. Si el robot falla, los PLC siguen protegiendo. Carga automática y línea de vista: por verificar.
5. Escalabilidad: el registro tiene el mismo formato venga de robot, celular o cámara; hoy solo el robot genera datos. Otro frutal necesita un perfil de riesgo, fotos y clases visuales nuevas, reentreno y un ciclo de cultivo de piloto; fresa y mora se validan en el motor, no en campo. El multi-cliente tiene 2 casos de ataque abiertos documentados; no decir "seguro".`);
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log('ok ' + OUT);
}

main().catch((e) => { console.error(e); process.exit(1); });
