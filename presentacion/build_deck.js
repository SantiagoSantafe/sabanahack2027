// build_deck.js · Berry Good Idea · pitch Sabana Hack 2026 (11 diapositivas + 2 de respaldo)
// Uso: cd presentacion && node build_deck.js  ->  BerryGoodIdea_pitch.pptx
// Parte de kit_visual.js (sistema visual validado de diseno.md). Reglas del equipo (INSTRUCCIONES.md): sin modelo de negocio.
// Marcos VIDEO_<id>: solo donde va video real (robot real, camara, dashboard, simulador). Las imagenes del equipo van incrustadas.
// Revision 24-oct-2026 (segunda ronda de QA): grafico de costos lineal y sin formato numerico del idioma, demo 16:9,
// limites mas legibles, cierre con imagen, matriz con costo solo de hardware.
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
const OUT = DIR + 'BerryGoodIdea_pitch.pptx';

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
pres.defineSlideMaster({ title: 'MEDIA', background: { color: C.text1 }, objects: [{ placeholder: { options: { name: 'title', type: 'title', x: L + 0.35, y: 5.55, w: 6.0, h: 1.0, fontSize: 28, bold: true, color: C.background1, margin: 0, valign: 'top', align: 'left' }, text: '' } }] });
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
    s.addText('LA ALTERNARIA PUEDE NACER DE NOCHE', { placeholder: 'title' });
    [['2:00 a. m.', 'Hoja mojada y casi nadie mirando'], ['> 10 h', 'de hoja mojada: la alternaria puede aparecer'], ['6:00 a. m.', 'Entra el primer operario, con papel']].forEach((r, i) => {
      const y = 2.3 + i * 1.35;
      glass(s, 'CAPA_hora_' + (i + 1), L, y, 6.4, 1.15);
      s.addText(r[0], { x: L + 0.35, y, w: 2.75, h: 1.15, fontSize: 36, bold: true, fontFace: 'Arial', color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(r[1], { x: L + 3.2, y, w: 2.95, h: 1.15, fontSize: 16, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    });
    // la foto tapa el pie del layout: se repite como texto de la propia diapositiva
    s.addText('BERRY GOOD IDEA', { objectName: 'PIE_marca', x: L, y: 6.75, w: 4, h: 0.25, fontSize: 10, bold: true, charSpacing: 4, color: C.accent4, margin: 0, isTextBox: true });
    renderTag(s, C.accent4);
    s.addNotes(`Son las dos de la mañana. El invernadero condensa, la hoja queda mojada y la alternaria puede aparecer de una noche a otra. Los operarios entran a las seis. Hoy, ese foco se ve días después.

Precisión: el título habla de la alternaria porque es lo que respaldan el mentor de AGRAR (gutación: de noche el invernadero condensa y la enfermedad puede aparecer de una noche a otra) y el manual de Torres 2015 (más de 10 h de hoja mojada, 18–28 °C). Botrytis, la más común y la que más cuesta, responde a humedad alta sostenida, no a una sola noche: no generalizar el "nace de noche" a todas las enfermedades. "2:00 a. m." es una hora narrativa, no medida.

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
    const s = slideFor('CLARO', 'Solución', 'LA MISMA NOCHE', 'ALERTA EN MINUTOS (OBJETIVO)', false);
    const steps = [
      [REC + 'plc_sensores_bloque.jpg', 'PLC: bloque en riesgo', 'Los sensores de AGRAR marcan el bloque en riesgo (Botrytis, alternaria).', 'IMAGEN_paso1_plc', 'Render conceptual: gabinete PLC y sensor de temperatura y humedad en el poste de un bloque', 'Diseño · se valida en el piloto'],
      [REC + 'hoja_oidio_hud_recorte.jpg', 'Robot: cama exacta', 'Mira la hoja y alerta con T y HR. Cama por marcador + odometría (por verificar).', 'IMAGEN_paso2_hoja', 'Render conceptual: hoja con oídio vista por la cámara del robot, con nave, cama, planta, temperatura y humedad', null],
      [REC + 'supervisor_sin_logo.jpg', 'Supervisor: decide', 'Envía a un operario a confirmar o descartar; queda registro.', 'IMAGEN_paso3_supervisor', 'Render conceptual: supervisor con tablet viendo el mapa de focos del invernadero', 'Diseño · se valida en el piloto'],
    ];
    steps.forEach((st, i) => {
      const x = COL3[i], y = 1.95;
      s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_paso_' + (i + 1), x, y, w: W3, h: 3.8, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: 'none' }, shadow: shCard() });
      photo(s, st[0], x + 0.2, y + 0.2, 3.4, 2.05, st[4], st[3]);
      if (st[5]) pill(s, 'ETIQUETA_estado_' + (i + 1), x + 0.3, y + 0.3, 2.5, 0.3, C.accent3, st[5], { color: C.text1, size: 11, bold: true, margin: [9, 0, 0, 0] });
      s.addShape(pres.ShapeType.ellipse, { objectName: 'NUM_' + (i + 1), x: x + 0.2, y: y + 2.4, w: 0.5, h: 0.5, fill: { type: 'none' }, line: { color: C.accent1, width: 1.75 } });
      s.addText(String(i + 1), { x: x + 0.2, y: y + 2.4, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: C.accent1, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
      s.addText(st[1], { x: x + 0.85, y: y + 2.4, w: 2.75, h: 0.5, fontSize: 18, bold: true, color: C.text1, margin: 0, valign: 'middle', isTextBox: true });
      s.addText(st[2], { x: x + 0.2, y: y + 3.0, w: 3.4, h: 0.7, fontSize: 14, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
      if (i < 2) s.addShape(pres.ShapeType.chevron, { objectName: 'FLECHA_' + (i + 1), x: x + W3 + 0.05, y: y + 1.9, w: 0.2, h: 0.35, fill: { color: C.accent1 }, line: { type: 'none' } });
    });
    ['Hoja sana: solo se registra, sin alerta', 'Objetivo: alerta en ≤ 5 min (por medir)', '~5 bloques por noche; el PLC prioriza'].forEach((t, i) => {
      pill(s, 'PASTILLA_' + (i + 1), COL3[i], 6.05, W3, 0.4, C.background1, t, { color: C.text1, size: 13, bold: true, shadow: true });
    });
    renderTag(s, C.accent6, 7.6, 6.75, 3.9);
    s.addNotes(`AGRAR ya mide el ambiente en cada bloque: cuando su PLC marca riesgo, el robot sale de noche a esa cama primero. Ve la hoja y mide temperatura y humedad en el punto: si es sana, solo la registra, sin alerta; si es sospechosa, viaja por LoRaWAN una alerta con nave, cama y planta. El supervisor la ve y manda a un operario a confirmar: el robot sugiere, la persona decide.

Cuidado con las afirmaciones (todo el flujo es diseño que se valida en el piloto, y así dice la diapositiva):
• Estado del modelo predictivo de AGRAR: el mentor dijo que AGRAR "ya trabaja en" un modelo predictivo que corre en su controlador. No dijimos que ya marque bloques en producción; la demo usa clima de Open-Meteo o simulado, no un PLC. Decir "los sensores de AGRAR marcan el bloque" como diseño, no como algo ya integrado.
• "Minutos" es un OBJETIVO de latencia (de que el robot ve la hoja a que el supervisor ve la alerta), no una medición: cronometrar 5 repeticiones en el ensayo y, si sale distinto, cambiar el título por el número medido.
• Cómo sabe la cama: marcador en la cabecera + odometría; ambos NO están verificados en campo (el D1 no tiene ROS). Es la etiqueta "por verificar" de la foto 2.
• Cobertura: el robot cubre unos 5 bloques por noche (14\u00A0% de la finca). En una noche húmeda como la del gancho podrían estar en riesgo todos los bloques a la vez: el PLC prioriza por nivel de riesgo (cola de prioridad) y, si no alcanza, se necesita un segundo robot o la ronda del día siguiente. La vuelta de 40 bloques toma ~7 noches (3–12 según supuestos).
• Canal supervisor → operario: no hay wifi ni celular en los bloques (solo internet en la oficina) y el mentor no confirmó el canal real. Decir "así lo diseñamos y lo validamos en el piloto".
• Clasificar a bordo (Jetson) evita subir video: LoRaWAN lleva mensajes de cientos de bytes (por ejemplo "N2 C3 P41 · oídio · 87\u00A0% · 10,4 °C · 95\u00A0% HR"); las fotos se descargan por Wi-Fi local al volver a la base de carga (diseño, sin verificar en campo).
• Las tres imágenes son renders conceptuales. La del supervisor está recortada para no mostrar la marca de la fumigadora.

TIEMPO · 5 min: 28 s · 3 min: 17 s, ACORTAR (sin la rama "sana") · 9 min: 40 s, AMPLIAR: por qué prioriza (riesgo del PLC) y qué viaja por LoRaWAN.`);
  }

  // =============== 5 DEMO EN VIVO ===============
  {
    const s = pres.addSlide({ masterName: 'MEDIA', sectionTitle: 'Demo' });
    // A: robot real, 16:9 exacto a pantalla completa. B: panel de la camara, 16:9, recuadro arriba a la derecha.
    videoFrame(s, 'demoA_robot_real', 'el D1 real sale solo por la ruta entre dos filas de PCs (camas a escala de sala) y gira a izquierda y derecha. 16:9, sin audio; en vivo o plan B de 90 s', 0, 0, W, H, { full: true });
    videoFrame(s, 'demoB_camara', 'panel de cámara (16:9): hoja sana sin alerta; hoja enferma con alerta, T y HR', 8.07, 0.85, 4.6, 2.59, { round: true, size: 12, line: { color: C.background1, width: 1.25 } });
    s.addShape(pres.ShapeType.roundRect, { objectName: 'BORDE_camara', x: 8.07, y: 0.85, w: 4.6, h: 2.59, rectRadius: 0.12, fill: { type: 'none' }, line: { color: C.background1, width: 1.25 } });
    pill(s, 'AVISO_demo', 8.07, 3.6, 4.6, 0.4, C.accent5, 'T y HR simuladas · enlace Wi-Fi local', { size: 12, bold: true, align: 'center', margin: 0 });
    s.addShape(pres.ShapeType.roundRect, { objectName: 'ROTULO_pastilla', x: L, y: 0.85, w: 2.4, h: 0.45, rectRadius: 0.22, fill: { color: C.accent5, transparency: 25 }, line: { type: 'none' } });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'ROTULO_punto', x: L + 0.2, y: 0.99, w: 0.16, h: 0.16, fill: { color: C.accent2 }, line: { type: 'none' } });
    s.addText('DEMO EN VIVO', { x: L + 0.5, y: 0.85, w: 1.8, h: 0.45, fontSize: 12, bold: true, charSpacing: 4, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    glass(s, 'CAPA_texto', L, 5.0, 6.6, 1.7);
    s.addText('ENTRA  ·  SALE', { x: L + 0.35, y: 5.2, w: 5.9, h: 0.3, fontSize: 12, bold: true, charSpacing: 4, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('Hoja + T y HR + cama:\nsale alerta y registro', { placeholder: 'title' });
    glass(s, 'CAPA_aviso', 7.5, 5.0, 5.17, 1.7);
    s.addText([
      { text: 'ESTA DEMO', options: { fontSize: 11, bold: true, charSpacing: 3, color: C.accent2, breakLine: true } },
      { text: 'D1 EDU, cámara frontal 1080p, modelo en portátil, fotos de hojas mostradas en pantalla.', options: { fontSize: 12, color: C.background1, breakLine: true } },
      { text: 'KIT DE FINCA', options: { fontSize: 11, bold: true, charSpacing: 3, color: C.accent2, breakLine: true } },
      { text: 'D1 Ultra, cámara 4K con luz, Jetson a bordo, LoRaWAN.', options: { fontSize: 12, color: C.background1 } },
    ], { x: 7.8, y: 5.1, w: 4.6, h: 1.5, margin: 0, valign: 'middle', paraSpaceAfter: 3, isTextBox: true });
    s.addNotes(`Entra una foto de la hoja, la temperatura, la humedad y la posición; sale una alerta y un registro. Aquí la hoja la muestra un PC, la T y HR son simuladas y el enlace es wifi, no LoRaWAN; en finca el sensor y la radio ya están en el kit. Miren primero una sana: no genera alerta, pero queda registrada. Ahora una enferma.

DECLARAR LO QUE NO ES EL KIT: el robot de la demo es el D1 EDU con su cámara frontal de 1080p, y el modelo corre en el portátil, no en el Jetson. El mástil y la cámara 4K con iluminación del kit de finca no se probaron. Las hojas son fotos mostradas en pantalla. El 78\u00A0% de la diapositiva 7 se midió con esa cámara y esa configuración.

GUION DE LA DEMO (95 s):
• 0–10 s: "Dos filas de PCs son las camas, a escala de sala. El D1 sale por la ruta."
• 10–25 s: gira a la izquierda y a la derecha mirando cada "cama".
• 25–45 s: hoja sana (la elige el jurado): el panel la marca sana, punto verde en el mapa, queda en el registro, sin alerta.
• 45–70 s: hoja enferma (la elige el jurado): el robot se detiene; sale la alerta con nave · cama · planta y T/HR.
• 70–95 s: en el dashboard aparece el foco con la foto. Pasar a la diapositiva 6.

Si el modelo falla una hoja: "Eso es justo el 22\u00A0% de enfermas que se nos escapa, o el 29\u00A0% de falsas alarmas de la diapositiva 7." No repetirlo más de una vez. Si falla el robot o la red, pasar al video de respaldo (demo completa grabada, con cronómetro visible).

Riesgo: la ruta es autónoma o teleoperada: se decide en el ensayo y se dice en voz alta ("teleoperado" si lo es). La navegación por pasillo real en finca es desarrollo por construir (el D1 no tiene ROS). Evitar mirar pantalones o sillas: usar el filtro "¿hay hoja?" y el recorte de la región de interés.

ANTES DE PRESENTAR: cronometrar la demo con 5 repeticiones y llevar la mediana de segundos de la foto al panel; si se quiere mostrar en pantalla, añadir ese número al aviso de abajo a la derecha. Los marcos no tienen video aún: probar el plan B completo con cronómetro visible.

Reemplazo de los marcos (ambos 16:9): VIDEO_demoA_robot_real ocupa toda la diapositiva (13,333 × 7,5 in) y VIDEO_demoB_camara es el recuadro de 4,6 × 2,59 in arriba a la derecha. Seleccionar el marco, Insertar > Video (sin audio, reproducción "Al hacer clic"), mismo tamaño y posición, y borrar el marco. El video del robot va al fondo; el video de la cámara va por encima del robot pero debajo del borde blanco. Añadir además un fotograma fijo de cada video por si se exporta a PDF.

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
      x: L, y: 1.95, w: 7.6, h: 2.7, series: 'Hojas con alerta (%)', title: 'Hojas con alerta (%): en enfermas, más es mejor; en sanas, menos es mejor', fmt: '0" %"', max: 100, gap: 40,
    });
    s.addText('n = 68 hojas (54 enfermas, 14 sanas) · IC95: 61–92\u00A0% en enfermas, 0–71\u00A0% en falsas alarmas · Fuente: prueba del equipo; DrBerry (CC BY 4.0)', { x: L, y: 4.7, w: CW, h: 0.22, fontSize: 11, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
    s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_destacado', x: 8.57, y: 1.95, w: 4.1, h: 2.7, rectRadius: 0.12, fill: { color: C.text1 }, line: { type: 'none' }, shadow: shCard() });
    s.addText('78\u00A0%', { x: 8.92, y: 2.03, w: 3.4, h: 0.78, fontSize: 48, bold: true, fontFace: 'Arial', color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('de las enfermas con alerta (42 de 54);\n12 de 54 sin alerta', { x: 8.92, y: 2.85, w: 3.5, h: 0.5, fontSize: 14, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
    s.addText('Falsas alarmas: 29\u00A0% (4 de 14; IC 0–71\u00A0%)', { x: 8.92, y: 3.4, w: 3.5, h: 0.5, fontSize: 14, bold: true, color: C.accent3, margin: 0, valign: 'top', isTextBox: true });
    s.addText('Un modelo que alertaba siempre daba 100\u00A0%. Diseñado para aprender de cada confirmación; el piloto mide cuánto baja.', { x: 8.92, y: 3.95, w: 3.5, h: 0.62, fontSize: 12, color: C.accent4, margin: 0, valign: 'top', isTextBox: true });
    s.addShape(pres.ShapeType.roundRect, { objectName: 'LIMITES_panel', x: L, y: 5.05, w: CW, h: 1.55, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: 'none' }, shadow: shCard() });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_anillo', x: L + 0.3, y: 5.2, w: 0.2, h: 0.2, fill: { type: 'none' }, line: { color: C.accent3, width: 1.5 } });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_punto', x: L + 0.36, y: 5.26, w: 0.08, h: 0.08, fill: { color: C.accent3 }, line: { type: 'none' } });
    s.addText('LÍMITES QUE DECLARAMOS', { x: L + 0.7, y: 5.16, w: 6, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: HEX.ambarTxt, margin: 0, valign: 'middle', isTextBox: true });
    s.addText([
      { text: '68 hojas de laboratorio, solo 14 sanas', options: { bullet: true, breakLine: true } },
      { text: 'Alternaria es la clase débil', options: { bullet: true, breakLine: true } },
      { text: 'Riesgo ambiental sin validar contra enfermedad real', options: { bullet: true } },
    ], { objectName: 'LIMITES_lista', x: L + 0.3, y: 5.46, w: 6.4, h: 0.76, fontSize: 14, color: C.text1, margin: 0, valign: 'top', isTextBox: true });
    s.addText('Por eso el robot sugiere y el supervisor manda a un operario a confirmar.', { x: L + 0.3, y: 6.25, w: 6.6, h: 0.28, fontSize: 14, bold: true, color: C.text1, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('Botrytis, la enfermedad principal, solo la cubre el riesgo ambiental (28–48\u00A0% por día de alerta), sin validar. La cámara reconoce 3 enfermedades, no otros daños, y acierta la exacta ~54\u00A0%: sugiere, no diagnostica.', { objectName: 'LIMITES_otros', x: L + 7.2, y: 5.2, w: 4.5, h: 1.3, fontSize: 12, color: C.accent6, margin: 0, valign: 'middle', isTextBox: true });
    s.addNotes(`Medimos con 68 hojas de laboratorio frente a la cámara del robot: de las enfermas, 42 de 54 disparan alerta (78\u00A0%) y 12 se nos escapan; falla sobre todo en alternaria, donde solo la mitad dispara alerta. Y marca 29\u00A0% de las sanas por error (4 de 14); un modelo que alertaba siempre daba 100\u00A0%. Una falsa alarma cuesta una visita; una enfermedad sin ver cuesta cosecha: la regla es que una visita cuesta menos que una cama perdida.

Datos (modelo en uso: modelo_camara): enfermas con alerta 42/54 = 78\u00A0% (IC95 61–92\u00A0%); falsas alarmas 4/14 = 29\u00A0% (IC95 0–71\u00A0%); por clase: Heliothis 17/18, oídio 18/22, alternaria 7/14 (derivado de la matriz de confusión). Datos: DrBerry, CC BY 4.0, 410 hojas (278 entrenamiento, 64 validación, 68 prueba). Las hojas son fotos de laboratorio de DrBerry mostradas en pantalla a la cámara del D1.

El compromiso, dicho claro: el punto de operación elegido (umbral 0,986, corrección de color y auto-recorte) da 78\u00A0% de sensibilidad con 29\u00A0% de falsas alarmas. La versión cruda del mismo modelo da 85\u00A0% de sensibilidad con 43\u00A0% de falsas alarmas. Se eligió la primera porque reduce las visitas de más, a costa de dejar pasar 12 de 54 enfermas. Si el cliente prefiere no perder enfermas, el piloto puede pasar a la versión cruda. No presentar el punto elegido como "preferimos alertar de más": es lo contrario.

Lo que NO se dice:
• No decir "sensibilidad 80\u00A0%" ni "especificidad 95\u00A0%": son del modelo anterior con imagen limpia.
• No mostrar "87/87 con 0/14 falsas alarmas": son recortes; alternaria se separa solo por tamaño.
• Con 14 sanas, diferencias de 1–3 imágenes no son significativas; el umbral 0,986 se eligió con solo 10 sanas de validación y es frágil; hay una sola sesión de fotos de cámara.
• El paso de 100\u00A0% a 29\u00A0% cambia a la vez fotos de la cámara, corrección de color y umbral, y cuesta sensibilidad: decir "con fotos de la cámara", no "con fotos de campo".
• Que las falsas alarmas bajen con las confirmaciones del operario es una hipótesis (no hay confirmaciones de campo): decir "diseñado para aprender; el piloto mide cuánto baja".
• La enfermedad exacta se acierta ~54\u00A0%: la cámara sugiere, no diagnostica. El clasificador tiene 4 clases (alternaria, Heliothis, oídio, sana): trips, deficiencias u otros daños no tienen clase y pueden salir como falsa alarma.
• Fuera de DrBerry (60 hojas sanas de campo, otros países) el modelo anterior alertaba 73\u00A0%; el modelo en uso no se ha medido en campo.
• Botrytis, la enfermedad principal según el mentor, y la roya no tienen clase visual: solo las cubre la capa ambiental, que tampoco está validada contra enfermedad real (sensibilidad por día de alerta 28–48\u00A0% frente a la estación IDEAM, sin datos de incidencia).

TIEMPO · 5 min: 27 s · 3 min: 20 s, se queda con el pie de límites · 9 min: 55 s, AMPLIAR: matriz de confusión, 410 hojas y prueba fuera del dataset.`);
  }

  // =============== 8 POR QUÉ ESTA SOLUCIÓN ===============
  {
    const s = slideFor('CLARO', 'Evidencia', 'POR QUÉ ESTA SOLUCIÓN', 'EL PLC ANTICIPA, EL ROBOT CONFIRMA', false);
    barChart(s, 'GRAFICO_alternativas', ['Híbrido: PLC + robot', 'Solo sensores fijos', 'Solo robot (D1 con mástil)', 'Kit en la aspersora', 'Robot con ruedas', 'Humanoide X2 Ultra'], [89, 75, 70, 57, 56, 42], [HEX.hoja, HEX.gris, HEX.gris, HEX.gris, HEX.gris, HEX.gris], {
      x: L, y: 1.95, w: 5.6, h: 3.5, series: 'Puntaje (0–100)', title: 'Puntaje del equipo, de 0 a 100 (híbrido: 89)', fmt: '0', max: 100, gap: 35,
    });
    s.addText('Autoevaluación con seis criterios y pesos del equipo (anticipa, ubica la cama, costo, encaje, robustez y registro). El costo se puntúa solo con el hardware (diapositiva 9). El híbrido incluye la red fija y queda primero en 91\u00A0% de las combinaciones de pesos probadas.', { x: L, y: 5.6, w: 5.6, h: 0.9, fontSize: 12, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
    videoFrame(s, 'simulador', 'gemelo digital (16:9, 12 a 40 s, sin audio): la misma noche simulada, el D1 real y su avatar moviéndose a la vez', 6.47, 1.95, 6.2, 3.49, { round: true, shadow: true });
    s.addText('Gemelo digital en simulador. Datos simulados.', { x: 6.47, y: 5.5, w: 6.2, h: 0.25, fontSize: 11, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
    s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_aspersion', x: 6.47, y: 5.85, w: 6.2, h: 0.7, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: 'none' }, shadow: shCard() });
    s.addText([{ text: '¿Y la aspersión? ', options: { bold: true, color: C.accent1 } }, { text: 'Descartada: la decide el agrónomo de cada finca y el riesgo más fuerte aparece de noche.', options: { color: C.text1 } }], { x: 6.77, y: 5.85, w: 5.65, h: 0.7, fontSize: 14, margin: 0, valign: 'middle', isTextBox: true });
    s.addNotes(`La razón de fondo: el PLC de AGRAR anticipa con lo que ya existe y el robot confirma con la cámara en la cama exacta; juntos cubren lo que cada uno no ve. La idea original era ir con la aspersión. La descartamos porque AGRAR no asperja (lo decide el agrónomo de cada finca), porque el riesgo más fuerte aparece de noche con la hoja mojada y porque la aspersión llega después de aplicar, no antes. No la botamos: la misma plataforma recibe hallazgos de una cámara en la aspersora. Frente a seis alternativas, el híbrido saca 89 de 100. El video es el gemelo digital: la misma noche, simulada.

Cómo se puntuó el Costo (recalculado solo con costo de hardware, consistente con la diapositiva 9; sin precios de venta): 5 = sin hardware nuevo (la red fija que AGRAR ya tiene); 4 = hasta 0,75 veces el costo del kit; 3 = alrededor de 1 vez; 2 = de 1,5 a 4 veces; 1 = más de 4 veces. Resultado: solo sensores fijos 5 (hardware nuevo 0); kit en la aspersora 4 (≈ 18 M COP, 5.679 USD × TRM 3.185); solo robot y híbrido 3 (kit de 34,85 M; en el híbrido la red ya existe); robot con ruedas 2 (≈ 89 M: Amiga de 22.500 USD FOB, factor de importación 1,14, más el resto del kit); humanoide X2 Ultra 1 (151 M, 4,3 veces). Los umbrales son del equipo: con el X2 Ultra en 2 (si se usara un corte de 5 veces) el híbrido sigue primero (humanoide 46 en vez de 42). Los puntajes de Costo no cambian respecto a la matriz anterior, y el 89 y el 91\u00A0% (10.560 de 11.628 combinaciones de pesos, en múltiplos de 5 con mínimo 5) tampoco. Las justificaciones de Costo del archivo datos/finanzas/agrar/matriz_justificaciones.csv son anteriores a esta regla y NO se citan; si preguntan cómo se puntuó el costo, la respuesta es el costo del hardware de la diapositiva 9.

Cuidado:
• Es una matriz AUTOEVALUADA con pesos del equipo; el híbrido incluye la red fija, así que casi siempre gana (primero en 91\u00A0% de 11.628 combinaciones de pesos; la red fija queda sobre el híbrido en 8\u00A0%). Puntajes: híbrido 89; solo sensores fijos 75; solo robot 70; kit en aspersora 57; ruedas 56; humanoide X2 Ultra 42. Con el costo al 30\u00A0% el híbrido saca 85,4.
• La diapositiva 9 compara el costo con alternativas que NO están en la matriz (cuadrúpedo D1 MaxPro, humanoide A3 Ultra, cámaras fijas): son referencias de costo, no puntuadas. De la diapositiva 9 solo el X2 Ultra está en la matriz.
• "La aspersión no es diaria ni nocturna" NO está documentada (el mentor no respondió frecuencia ni cuánto hay que esperar tras aplicar): confirmar con un agrónomo o decir "según nuestro entendimiento". El horario de aspersión 6–14 h es un supuesto. El riesgo "nace de noche" solo está respaldado para la alternaria; Botrytis responde a humedad sostenida.
• El video de simulación solo debe mostrar métricas que salgan de batch.py con semilla; no hay resultados de "día de detección" en los archivos, no inventarlos. El marco VIDEO_simulador es 16:9 (6,2 × 3,49 in): insertar el video sin audio y añadir un fotograma fijo por si se exporta a PDF.

TIEMPO · 5 min: 20 s · 3 min: 10 s, una frase: aspersión descartada y "89 de 100" · 9 min: 40 s, AMPLIAR: matriz de 6 alternativas y barrido de pesos.`);
  }

  // =============== 9 COSTO DEL HARDWARE ===============
  {
    const s = slideFor('CLARO', 'Costo', 'COSTO DEL HARDWARE', '≈ 35 M COP: 1,5\u00A0% DE LAS CÁMARAS FIJAS', false);
    const x0 = L, y0 = 1.95;
    s.addShape(pres.ShapeType.roundRect, { objectName: 'TARJETA_kit', x: x0, y: y0, w: 4.3, h: 4.55, rectRadius: 0.12, fill: { color: C.text1 }, line: { type: 'none' }, shadow: shCard() });
    s.addText('KIT D1 ULTRA  ·  SIN IVA', { x: x0 + 0.3, y: y0 + 0.2, w: 3.7, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText([{ text: '≈ 34,85', options: { fontSize: 48, bold: true, fontFace: 'Arial' } }, { text: ' M COP', options: { fontSize: 20, bold: true, fontFace: 'Arial' } }], { x: x0 + 0.3, y: y0 + 0.48, w: 3.7, h: 0.8, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('≈ 41,5 M COP con IVA', { x: x0 + 0.3, y: y0 + 1.28, w: 3.7, h: 0.3, fontSize: 16, color: C.accent4, margin: 0, valign: 'middle', isTextBox: true });
    const bom = [['Robot D1 Ultra (IP54)', '27,22'], ['Batería de repuesto', '1,63'], ['Cámara 4K con iluminación', '1,27'], ['Base de carga', '2,20'], ['Jetson, T/HR, LoRaWAN, mástil, cableado', '2,53']];
    const rows = bom.map((r, i) => [
      { text: r[0], options: { color: i === 0 ? HEX.lima : HEX.blanco, bold: i === 0, fontSize: 14, fontFace: 'Calibri', align: 'left', valign: 'middle' } },
      { text: r[1], options: { color: i === 0 ? HEX.lima : HEX.blanco, bold: i === 0, fontSize: 14, fontFace: 'Calibri', align: 'right', valign: 'middle' } },
    ]);
    s.addTable(rows, { objectName: 'TABLA_desglose', x: x0 + 0.3, y: y0 + 1.7, w: 3.7, colW: [3.0, 0.7], rowH: [0.38, 0.38, 0.38, 0.38, 0.62], margin: 0, border: { type: 'none' } });
    s.addText('M COP sin IVA. Solo hardware: sin instalación, software ni mantenimiento.', { x: x0 + 0.3, y: y0 + 3.95, w: 3.7, h: 0.5, fontSize: 12, color: C.accent4, margin: 0, valign: 'top', isTextBox: true });
    // escala LINEAL en "veces el costo del kit"; las cifras van en el nombre de la categoria (formato fijo, no depende del idioma de la maquina)
    const kit = 34.85;
    barChart(s, 'GRAFICO_costos', ['Kit D1 Ultra · 34,85 M · 1×', 'Humanoide X2 Ultra · 151 M · 4,3×', 'Cuadrúpedo industrial · 253 M · 7×', 'Humanoide A3 Ultra · 278 M · 8×', 'Cámaras fijas, 1 cada 10 m de cama · 2.300 M · 66×'], [1, +(151 / kit).toFixed(2), +(253 / kit).toFixed(2), +(278 / kit).toFixed(2), +(2300 / kit).toFixed(2)], [HEX.hoja, HEX.gris, HEX.gris, HEX.gris, HEX.gris], {
      x: 5.27, y: 1.95, w: 7.4, h: 2.85, series: 'Veces el costo del kit', title: 'Veces el costo del kit (escala lineal, desde 0)', showValue: false, min: 0, max: 70, gap: 35,
    });
    s.addText('Equivale al 1,5\u00A0% de las cámaras fijas y al 23\u00A0% de un humanoide.', { x: 5.27, y: 4.88, w: 7.4, h: 0.35, fontSize: 14, bold: true, color: C.text1, margin: 0, valign: 'middle', isTextBox: true });
    pill(s, 'ETIQUETA_estimaciones', 5.27, 5.35, 3.0, 0.3, C.accent3, 'ESTIMACIONES DEL EQUIPO', { color: C.text1, size: 11, bold: true, align: 'center', margin: 0 });
    s.addText('Precios FOB de referencia, sin cotización formal, TRM 3.185, sin IVA. Cámaras: ≈ 7.200 × 100 USD, sin instalación ni red. Cuadrúpedo industrial: D1 MaxPro. Precio del A3 Ultra por confirmar. Solo el X2 Ultra está en la matriz de la diapositiva 8.', { x: 5.27, y: 5.75, w: 7.4, h: 0.75, fontSize: 12, color: C.accent6, margin: 0, valign: 'top', isTextBox: true });
    s.addNotes(`Todo el hardware de una finca cuesta unos 35 millones de pesos sin IVA, unos 41,5 con IVA: el robot, una batería de repuesto, la cámara 4K con iluminación para la noche, el computador a bordo, el sensor de temperatura y humedad, el módulo LoRaWAN, el mástil y la base de carga. Es solo hardware: sin instalación, software ni mantenimiento. La fuente y la caja ya las tiene AGRAR. Para comparar: cubrir la finca con cámaras fijas costaría unos 2.300 millones, 66 veces el kit; un cuadrúpedo industrial, 7 veces; un humanoide, entre 4 y 8 veces. Y las cámaras no ven el envés de la hoja. El precio al que se ofrezca el sistema lo define AGRAR: aquí mostramos solo el costo del hardware.

Cifras (M COP sin IVA; estimaciones del equipo, precios FOB de referencia sin cotización formal, TRM 3.185): kit D1 Ultra 34,85; humanoide X2 Ultra 151 (4,3×); cuadrúpedo D1 MaxPro 253 (7×); humanoide A3 Ultra 278 (8×); cámaras fijas 2.300 (66×); cámaras por planta 4.600–11.500. Desglose del kit en M COP: robot 27,22; batería de repuesto 1,63; cámara 4K con iluminación 1,27; base de carga (caseta, cargador, UPS, punto de acceso) 2,20; y, juntos, 2,53 de Jetson 0,90 + sensor T/HR 0,22 + LoRaWAN/Modbus 0,29 + mástil 0,80 + cableado 0,32. Suma 34,85. Opcional: cámara térmica, +0,9 M. Con el D1 EDU el kit baja a ~29,8 M (34,85 menos 5,07 M de diferencia en el robot), pero no declara protección IP.

Cuidado:
• El gráfico está en escala LINEAL, en veces el costo del kit: la barra minúscula del kit ES el mensaje. Las cifras están escritas en el nombre de cada barra (no en etiquetas numéricas del gráfico) para que se lean igual en cualquier computador.
• "1,5\u00A0%" significa: el kit cuesta el 1,5\u00A0% de lo que costaría cubrir la finca con cámaras fijas (34,85 / 2.300). No decir "66 veces menos".
• Las cifras de humanoides, cuadrúpedo industrial y cámaras son estimaciones del equipo; el FOB del X2 Ultra (39.999 USD) y del MaxPro (67.999 USD) no está verificado, y el precio del A3 Ultra no tiene respaldo propio (por confirmar). Las cámaras suponen 7.200 unidades (una cada 10 m de cama) a 100 USD: es un supuesto del documento de costos del equipo, no está en el repositorio. Una cámara de 100 USD no equivale a la 4K con luz del kit (unos 350 USD) y la cifra excluye instalación, energía y red: si preguntan, es una cota de orden de magnitud.
• 34,85 M frente a 35,40 M del modelo interno: la diferencia (~0,55 M) es la fuente DC-DC, SSD y caja del cómputo que AGRAR ya tiene. Decir "≈ 35 M sin IVA".
• Un solo D1 recorre la finca en ~7 noches (rango 3–12); dos robots cambian el costo. El D1 a precio de tienda cuesta 9.600 USD frente a 7.499 FOB: falta la cotización formal.
• De la comparación solo el X2 Ultra está en la matriz de la diapositiva 8; el resto son referencias de costo. Allí el costo se puntúa solo con este hardware.
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
      pill(s, 'ESTADO_fuente_' + (i + 1), L + 2.85, y + 0.09, 0.78, 0.26, hoy ? C.accent2 : C.accent5, f[2], { color: hoy ? C.text1 : C.accent3, size: 10, bold: true, align: 'center', margin: 0 });
    });
    s.addText('HOY = funciona en la demo · DISEÑO = se valida en el piloto', { objectName: 'LEYENDA_estado', x: L, y: 4.55, w: 4.6, h: 0.25, fontSize: 11, color: C.accent4, margin: 0, valign: 'middle', isTextBox: true });
    s.addShape(pres.ShapeType.rightArrow, { objectName: 'FLECHA_entrada', x: 4.55, y: 2.95, w: 0.7, h: 0.5, fill: { color: C.accent2, transparency: 30 }, line: { type: 'none' } });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'NODO_registro', x: 5.45, y: 2.0, w: 2.5, h: 2.5, fill: { color: C.text2 }, line: { color: C.accent2, width: 2 } });
    s.addText([{ text: 'REGISTRO DE\nINCIDENCIAS', options: { fontSize: 16, bold: true, fontFace: 'Arial', color: C.background1, breakLine: true } }, { text: 'un solo formato', options: { fontSize: 12, color: C.accent2 } }], { x: 5.45, y: 2.0, w: 2.5, h: 2.5, align: 'center', valign: 'middle', margin: 0, isTextBox: true });
    s.addShape(pres.ShapeType.rightArrow, { objectName: 'FLECHA_salida', x: 8.15, y: 2.95, w: 0.7, h: 0.5, fill: { color: C.accent2, transparency: 30 }, line: { type: 'none' } });
    s.addText('FINCAS, CADA UNA AISLADA', { x: 9.05, y: 1.95, w: 3.62, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    ['Finca A · bloques, naves, camas', 'Finca B · otra región (ejemplo)', 'Finca C · otro cultivo (ejemplo)'].forEach((t, i) => {
      pill(s, 'FINCA_' + (i + 1), 9.05, 2.35 + i * 0.5, 3.62, 0.4, C.text2, t, { size: 13 });
    });
    s.addText('CULTIVOS: UN PERFIL CADA UNO', { x: 9.05, y: 3.98, w: 3.62, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    ['Arándano', 'Fresa', 'Mora'].forEach((t, i) => {
      pill(s, 'CULTIVO_' + (i + 1), 9.05 + i * 1.26, 4.35, 1.1, 0.4, C.accent2, t, { color: C.text1, size: 13, bold: true, align: 'center', margin: 0 });
    });
    glass(s, 'CAPA_hero', L, 5.05, CW, 1.05, 10);
    s.addText([{ text: '< 2', options: { fontSize: 48, bold: true, fontFace: 'Arial' } }, { text: ' %', options: { fontSize: 24, bold: true, fontFace: 'Arial' } }], { x: L + 0.4, y: 5.05, w: 2.6, h: 1.05, color: C.accent2, margin: 0, valign: 'middle', isTextBox: true });
    s.addText('del arándano de Colombia, Perú, Chile y México está en Colombia (≈ 1.000 de ≈ 54.500 ha, cálculo del equipo): crecer es llegar a otras fincas y regiones.', { x: L + 3.1, y: 5.05, w: 8.6, h: 1.05, fontSize: 16, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    glass(s, 'CAPA_nota', L, 6.33, CW, 0.34, 10, 0.1);
    s.addText('Otro frutal: perfil de riesgo + fotos y clases nuevas + un ciclo de piloto. Fresa y mora: solo en el motor de riesgo, sin validar en campo.', { objectName: 'PIE_nota', x: L + 0.2, y: 6.33, w: CW - 0.4, h: 0.34, fontSize: 11, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    s.addNotes(`La Sabana es solo nuestro ejemplo: la solución está pensada para otras fincas y otras regiones. El diseño es un mismo registro de incidencias que recibe hallazgos del robot, del celular del operario, de una cámara en la aspersora, de los sensores de los PLC y del pronóstico, y cada finca es una empresa aislada de las demás. Colombia es menos del 2\u00A0% del arándano de cuatro países, así que esto nace pensado para otras fincas y regiones.

Qué existe hoy y qué es diseño: el formato de incidencia es un esquema JSON validado con 20 casos sintéticos. Hoy solo el robot genera datos; el celular del operario, la cámara en la aspersora y los sensores de los PLC son diseño (por eso la etiqueta DISEÑO). Las fincas B y C son ejemplos, no clientes.

Qué cambiaría con otro frutal (la pregunta de la rúbrica): no es solo un archivo de configuración. Hace falta un perfil de riesgo del cultivo, fotos y clases visuales nuevas, reentrenar el modelo y un ciclo de cultivo de piloto para validarlo (ESCALABILIDAD §4). Los perfiles de fresa y mora existen en el motor de riesgo (22 modelos y 6 motores), pero se validan en el motor, no en campo.

Sobre el 2\u00A0%: ≈ 1.000 de ≈ 54.500 ha (Colombia, Perú, Chile y México; cálculo del equipo, ESCALABILIDAD §8.1). Quiere decir que casi todo el arándano de esos países está fuera de Colombia; no prueba por sí solo que haya demanda: eso lo mide el piloto.

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
    s.addText('Alerta en minutos donde hay riesgo; vuelta completa en ~7 noches.', { objectName: 'cierre_aclaracion', x: L, y: 2.95, w: 7.1, h: 0.7, fontSize: 18, bold: true, color: C.background1, margin: 0, valign: 'top', isTextBox: true });
    s.addText('A las 2:00 a. m. el robot ya está en la cama; a las 6:00 a. m. el operario sabe adónde ir.', { objectName: 'cierre_gancho', x: L, y: 3.7, w: 7.1, h: 0.7, fontSize: 18, color: C.accent2, margin: 0, valign: 'top', isTextBox: true });
    glass(s, 'CAPA_piloto', L, 4.6, 6.9, 2.0, 18);
    s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_anillo', x: L + 0.3, y: 4.78, w: 0.2, h: 0.2, fill: { type: 'none' }, line: { color: C.accent3, width: 1.5 } });
    s.addShape(pres.ShapeType.ellipse, { objectName: 'MARCADOR_punto', x: L + 0.36, y: 4.84, w: 0.08, h: 0.08, fill: { color: C.accent3 }, line: { type: 'none' } });
    s.addText('PILOTO EN 1 FINCA, CON Y SIN ROBOT · POR VALIDAR', { x: L + 0.7, y: 4.74, w: 6, h: 0.28, fontSize: 11, bold: true, charSpacing: 3, color: C.accent3, margin: 0, valign: 'middle', isTextBox: true });
    ['Navegar pasillos reales', 'Carga y autonomía (1–2 h)', 'Línea de vista de noche', 'Fotos y clima de campo'].forEach((t, i) => {
      pill(s, 'PENDIENTE_' + (i + 1), L + 0.3 + (i % 2) * 3.2, 5.15 + Math.floor(i / 2) * 0.46, 3.05, 0.38, C.text2, t, { size: 13, bold: true, margin: [12, 0, 0, 0] });
    });
    s.addText('Éxito: ≥ 70\u00A0% de alertas confirmadas, adelanto ≥ 3 días, ≥ 90\u00A0% de camas recorridas, robot ≥ 85\u00A0% operativo.', { objectName: 'CRITERIOS_piloto', x: L + 0.3, y: 6.1, w: 6.4, h: 0.42, fontSize: 13, color: C.background1, margin: 0, valign: 'middle', isTextBox: true });
    s.addNotes(`Esto no está terminado y lo decimos: probamos con hojas de laboratorio, no con una finca. Volvamos a las dos de la mañana: hoy, el foco se ve a las seis y se confirma días después. Con el robot, a las dos de la mañana el robot ya está en la cama en riesgo y a las seis el operario sabe adónde ir. Hoy, 7 a 8 días hábiles; con el robot, la cama en riesgo se revisa esa misma noche y la alerta llega en minutos. De 8 días hábiles a minutos.

Honestidad sobre el lema (por eso la línea visible "Alerta en minutos donde hay riesgo; vuelta completa en ~7 noches"): "minutos" es la latencia de la alerta (objetivo de ≤ 5 min de la foto al panel, aún sin cronometrar; mostrar el número medido de la demo si ya está). Un D1 recorre la vuelta completa de 40 bloques en ~7 noches (3–12 según supuestos), unos 5 bloques por noche, pero cada noche empieza por las camas de mayor riesgo; el contraste no es "cubre todo en minutos" sino alerta en minutos donde hay riesgo, todas las noches, sin papel ni digitación. Un jurado de negocios hará la cuenta: 7 noches contra 9–11 días calendario de hoy no es "minutos"; por eso se dice así. No decir cuántos días de adelanto da la alerta: no hay medición de adelanto.

Qué falta para una finca real (los cuatro pendientes de la pantalla): navegar pasillos reales (el D1 no tiene ROS; pasillos de 6,8 m); carga automática y autonomía de 1–2 h; línea de vista de noche que pide el manual del D1; fotos y clima de campo para reentrenar y para validar el riesgo ambiental con incidencia real. También: IP54, cotización formal del D1 y medir cuántas pérdidas se evitan.

Criterios de éxito del piloto (supuestos del equipo): ≥ 70\u00A0% de alertas confirmadas, adelanto ≥ 3 días en ≥ 50\u00A0% de los focos, ≥ 90\u00A0% de camas recorridas, robot operativo ≥ 85\u00A0%. La frase obligatoria de límites está en la diapositiva 7.

TIEMPO · 5 min: 18 s · 3 min: 17 s, se queda · 9 min: 37 s, AMPLIAR: lista completa de lo que falta (fotos de campo andino y reentreno con confirmaciones; navegación en pasillos de 6,8 m, carga automática y línea de vista del manual; IP54 y autonomía de 1–2 h; cotización formal del D1; medir cuántas pérdidas se evitan).`);
  }

  // =============== 12 RESPALDO · SUPUESTOS Y FUENTES ===============
  {
    const s = slideFor('CLARO', 'Respaldo', 'RESPALDO', 'SUPUESTOS Y FUENTES', false);
    const hdr = (t) => ({ text: t, options: { bold: true, color: HEX.blanco, fill: { color: HEX.bosque900 }, fontSize: 12, fontFace: 'Calibri', valign: 'middle' } });
    const cell = (t, o = {}) => ({ text: t, options: Object.assign({ color: HEX.bosque900, fontSize: 11, fontFace: 'Calibri', valign: 'middle' }, o) });
    const data = [
      ['Kit D1 Ultra', '≈ 34,85 M COP sin IVA (≈ 41,5 M con IVA)', 'Documento de costo del equipo. Solo hardware. FOB de referencia, sin cotización formal, TRM 3.185. Fuente y caja: las tiene AGRAR'],
      ['Cámaras fijas (1 cada 10 m de cama)', '≈ 2.300 M COP', 'ESTIMACIÓN del equipo: ≈ 7.200 cámaras × 100 USD; no equivalen a la cámara del kit y excluyen instalación, energía y red'],
      ['Humanoides y cuadrúpedo industrial', '151 · 253 · 278 M COP', 'ESTIMACIÓN del equipo; FOB sin verificar (X2 Ultra, D1 MaxPro); precio del A3 Ultra por confirmar'],
      ['Matriz de alternativas', '89 de 100 (híbrido); primero en 91\u00A0% de los pesos', 'Autoevaluación del equipo, 6 criterios. El costo se puntúa solo con hardware (diapositiva 9)'],
      ['Monitoreo manual hoy', '5–6 operarios, 7–8 días hábiles, ~20 ha', 'Dato del equipo con AGRAR, 24-oct-2026. Solo de día, en papel'],
      ['Pérdida fitosanitaria', '10–25\u00A0% (hasta 40\u00A0% sin prevención)', 'Mentor de AGRAR; no es medición propia ni lo que evita el robot'],
      ['Clasificador', '78\u00A0% de enfermas con alerta; 29\u00A0% de falsas alarmas', '68 hojas de laboratorio (DrBerry, CC BY 4.0) frente a la cámara; 14 sanas; IC95 61–92\u00A0% y 0–71\u00A0%. Sin prueba en finca'],
      ['Riesgo ambiental', 'Botrytis y antracnosis', 'Modelos de fresa como proxy; sin validar contra enfermedad real (28–48\u00A0% por día de alerta). Botrytis solo se cubre por esta vía'],
      ['Latencia de la alerta', '"Minutos" (objetivo ≤ 5 min)', 'Objetivo de diseño, aún sin cronometrar; se mide en el piloto'],
      ['Capacidad de un robot', '~19 ha por semana; 40 bloques en ~7 noches', 'Modelo del equipo (rango 3–12 noches); sin medir en finca'],
      ['Demo', 'D1 EDU, cámara frontal 1080p, modelo en portátil; fotos en pantalla; T y HR simuladas; Wi-Fi local', 'El kit de finca (D1 Ultra, cámara 4K con luz, Jetson a bordo) no se probó. Ruta autónoma o teleoperada: se declara'],
    ];
    const rows = [[hdr('Dato en el deck'), hdr('Valor'), hdr('De dónde sale y qué tan firme es')]].concat(data.map((r, i) => r.map((t, j) => cell(t, { bold: j === 0, fill: { color: i % 2 === 0 ? HEX.menta : HEX.blanco } }))));
    s.addTable(rows, { objectName: 'TABLA_supuestos', x: L, y: 1.75, w: CW, colW: [2.5, 3.6, 5.9], rowH: 0.36, margin: [2, 6, 2, 6], border: { type: 'solid', color: HEX.grid, pt: 0.75 } });
    s.addNotes(`Diapositiva de respaldo: solo se muestra si el jurado pregunta por una cifra. Estado de cada dato: FUENTE (mentor o documento), ESTIMACIÓN del equipo (sin cotización ni medición propia) o SIN VALIDAR.

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
2. Falsas alarmas y no detectadas: 29\u00A0% y 22\u00A0%, con solo 68 hojas y 14 sanas; los intervalos son anchos y lo decimos. El compromiso es explícito: el punto elegido da 78\u00A0% de sensibilidad con 29\u00A0% de falsas alarmas; la versión cruda del modelo da 85\u00A0% con 43\u00A0%. La regla de decisión: una visita cuesta menos que una cama perdida; si el cliente prefiere no perder enfermas, el piloto puede pasar a la versión cruda. Cuántas falsas alarmas tolera el cliente lo fija el piloto (el mentor no lo respondió). Que bajen con cada confirmación del operario es una hipótesis: el piloto mide cuánto.
3. PLC frente a robot: el mentor dijo que oídio y mildiu "solo se saben viéndolos". Botrytis, la principal, la cubre la capa ambiental, no la cámara. AGRAR ya trabaja en un modelo predictivo en su controlador: parte de la mejora ya la captura el PLC y lo que suma el robot se mide en el piloto.
4. Capacidad: ~19 ha por semana de noche, 40 bloques en ~7 noches (3–12 según supuestos), unos 5 bloques por noche. Si el robot falla, los PLC siguen protegiendo. Carga automática y línea de vista: por verificar.
5. Escalabilidad: el registro tiene el mismo formato venga de robot, celular o cámara; hoy solo el robot genera datos. Otro frutal necesita un perfil de riesgo, fotos y clases visuales nuevas, reentreno y un ciclo de cultivo de piloto; fresa y mora se validan en el motor, no en campo. El multi-cliente tiene 2 casos de ataque abiertos documentados; no decir "seguro".`);
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log('ok ' + OUT);
}

main().catch((e) => { console.error(e); process.exit(1); });
