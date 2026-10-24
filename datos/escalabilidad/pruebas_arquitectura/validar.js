// Valida schema_incidencia.json con Ajv 2020-12 (copia local ya instalada en la caché de npx).
const base = process.argv[2];
const Ajv2020 = require(base + '/ajv/dist/2020').default;
const addFormats = require(base + '/ajv-formats').default;
const fs = require('fs');
const schema = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const ajv = new Ajv2020({ allErrors: true, strict: true, strictRequired: false, strictTuples: false });
addFormats(ajv);
const validate = ajv.compile(schema);
const clone = o => JSON.parse(JSON.stringify(o));
const ej = schema.examples[0];
const U = (n) => `0192f1a0-7c00-7000-8000-${String(n).padStart(12,'0')}`;
const AG = 'aaaaaaaa-0000-4000-8000-000000000002', OP = 'aaaaaaaa-0000-4000-8000-000000000003';

// Ciclo completo: confirmada -> tratada -> cerrada
const cerrada = clone(ej);
cerrada.estado = 'cerrada';
cerrada.triage = { decision: 'verificar', por: AG, en: '2026-10-24T07:05:00-05:00', asignado_a: OP };
cerrada.verificacion = { resultado: 'confirmada', por: OP, en: '2026-10-24T09:40:00-05:00' };
cerrada.deteccion.problema_confirmado = 'oidio';
cerrada.tratamiento = { recomendacion_ids: [U(100)], aplicacion_ids: [U(200)], reinspeccion_programada_en: '2026-10-31T06:00:00-05:00' };
cerrada.cierre = { resultado: 'controlada', por: AG, en: '2026-11-01T10:00:00-05:00' };
cerrada.sync.version = 7;

const casos = [
  ['valido: ejemplo detectada (robot)', ej, true],
  ['valido: ciclo completo cerrada', cerrada, true],
];
const mal = (nombre, f) => { const o = clone(ej); f(o); casos.push([nombre, o, false]); };
mal('robot sin modelo ni confianza', o => { delete o.deteccion.modelo; delete o.deteccion.confianza; });
mal('robot sin evidencias', o => { delete o.evidencias; });
mal('robot con dispositivo_id null', o => { o.origen.dispositivo_id = null; });
mal('descartada sin descarte', o => { o.estado = 'descartada'; });
mal('confirmada sin verificacion', o => { o.estado = 'confirmada'; });
mal('confirmada con verificacion descartada', o => { o.estado = 'confirmada'; o.verificacion = { resultado: 'descartada', por: OP, en: '2026-10-24T09:40:00-05:00' }; });
mal('verificacion_asignada sin asignado', o => { o.estado = 'verificacion_asignada'; o.triage = { decision: 'verificar', por: AG, en: '2026-10-24T07:05:00-05:00' }; });
mal('sin posicion_m ni punto', o => { delete o.ubicacion.posicion_m; delete o.ubicacion.punto; });
mal('latitud fuera de rango', o => { o.ubicacion.punto.coordinates = [-74.06, 95]; });
mal('operario sin reportado_por', o => { o.origen = { tipo: 'operario' }; delete o.evidencias; });
mal('fecha sin zona horaria', o => { o.tiempos.detectada_en = '2026-10-24T06:21:13'; });
mal('propiedad desconocida', o => { o.color = 'rojo'; });
mal('estado inventado', o => { o.estado = 'resuelta'; });
mal('tratada sin aplicacion', o => { o.estado = 'tratada'; o.tratamiento = { recomendacion_ids: [U(100)] }; });
mal('cerrada sin cierre', o => { o.estado = 'cerrada'; });
mal('sha256 invalido', o => { o.evidencias[0].sha256 = 'abc'; });
mal('confianza > 1', o => { o.deteccion.confianza = 1.3; });

// Caso valido extra: operario sin robot (finca sin robot: la plataforma igual sirve)
const manual = clone(ej);
manual.origen = { tipo: 'operario', reportado_por: OP };
delete manual.evidencias; delete manual.deteccion.modelo; delete manual.deteccion.confianza; delete manual.deteccion.clases_top;
delete manual.ubicacion.punto; manual.ubicacion.metodo = 'manual';
manual.sync.origen_registro = 'app:3f9c2a';
casos.push(['valido: reporte manual de operario (sin robot)', manual, true]);

let fallos = 0;
for (const [nombre, obj, esperado] of casos) {
  const ok = validate(obj);
  const bien = ok === esperado;
  if (!bien) fallos++;
  const err = ok ? '' : ' -> ' + validate.errors.map(e => `${e.instancePath || '/'} ${e.message}`).slice(0, 2).join(' | ');
  console.log(`${bien ? 'PASA ' : 'FALLA'} [esperado ${esperado ? 'valido' : 'invalido'}] ${nombre}${err}`);
}
console.log(`\n${casos.length - fallos}/${casos.length} casos con el resultado esperado`);
process.exit(fallos ? 1 : 0);
