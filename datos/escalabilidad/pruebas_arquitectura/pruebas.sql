\set ON_ERROR_STOP 1
SET search_path = bgi, public;
-- Función auxiliar: ejecuta SQL y devuelve el SQLSTATE del error esperado (o 'OK')
CREATE OR REPLACE FUNCTION public.intentar(q text) RETURNS text LANGUAGE plpgsql AS $$
BEGIN EXECUTE q; RETURN 'OK';
EXCEPTION WHEN OTHERS THEN RETURN SQLSTATE || ' ' || SQLERRM; END $$;
GRANT EXECUTE ON FUNCTION public.intentar(text) TO bgi_app, bgi_flota;

\echo '--- P1 empresa A ve lo suyo'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111}';
SELECT 'P1 incidencias' t, count(*) FROM incidencia UNION ALL
SELECT 'P1 fincas', count(*) FROM finca UNION ALL
SELECT 'P1 dispositivos (robot prestado)', count(*) FROM dispositivo UNION ALL
SELECT 'P1 usuarios visibles', count(*) FROM usuario UNION ALL
SELECT 'P1 filas vista ICA monitoreo', count(*) FROM v_ica_monitoreo_plagas;
SELECT fecha_monitoreo, cultivo, lote, plaga_monitoreada, camas_inspeccionadas, camas_con_hallazgo_confirmado, incidencia_camas_pct, alertas_sin_verificar, responsable_monitoreo, metodo
FROM v_ica_monitoreo_plagas ORDER BY plaga_monitoreada;
COMMIT;

\echo '--- P2 empresa B no ve nada de A'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
SELECT 'P2 incidencias' t, count(*) FROM incidencia UNION ALL
SELECT 'P2 fincas', count(*) FROM finca UNION ALL
SELECT 'P2 dispositivos', count(*) FROM dispositivo UNION ALL
SELECT 'P2 vista ICA', count(*) FROM v_ica_monitoreo_plagas UNION ALL
SELECT 'P2 registro_cambios', count(*) FROM registro_cambios;
COMMIT;

\echo '--- P3 sin contexto no se ve nada'
BEGIN; SET LOCAL ROLE bgi_app;
SELECT 'P3 incidencias' t, count(*) FROM incidencia UNION ALL SELECT 'P3 empresas', count(*) FROM empresa;
COMMIT;

\echo '--- P4 intentos de cruzar empresas'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
SELECT 'P4a B escribe incidencia con empresa A' t, intentar($q$INSERT INTO bgi.incidencia (empresa_id, finca_id, bloque_id, cama_id, posicion_m, fuente_tipo, reportado_por, problema_codigo, detectada_en, creada_en)
 VALUES ('11111111-1111-4111-8111-111111111111','f1000000-0000-4000-8000-000000000001','b1000000-0000-4000-8000-000000000001','c1000000-0000-4000-8000-000000000007',1,'operario','aaaaaaaa-0000-4000-8000-000000000005','oidio',now(),now())$q$);
SELECT 'P4b B apunta a cama de A' t, intentar($q$INSERT INTO bgi.incidencia (empresa_id, finca_id, bloque_id, cama_id, posicion_m, fuente_tipo, reportado_por, problema_codigo, detectada_en, creada_en)
 VALUES ('22222222-2222-4222-8222-222222222222','f2000000-0000-4000-8000-000000000001','b2000000-0000-4000-8000-000000000001','c1000000-0000-4000-8000-000000000007',1,'operario','aaaaaaaa-0000-4000-8000-000000000005','oidio',now(),now())$q$);
SELECT 'P4c B crea su propia incidencia' t, intentar($q$INSERT INTO bgi.incidencia (empresa_id, finca_id, bloque_id, cama_id, posicion_m, fuente_tipo, reportado_por, problema_codigo, detectada_en, creada_en)
 VALUES ('22222222-2222-4222-8222-222222222222','f2000000-0000-4000-8000-000000000001','b2000000-0000-4000-8000-000000000001','c2000000-0000-4000-8000-000000000001',3.5,'operario','aaaaaaaa-0000-4000-8000-000000000005','botrytis',now(),now())$q$);
ROLLBACK;

\echo '--- P5 reglas de la incidencia'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111}';
SELECT 'P5a robot sin modelo' t, intentar($q$INSERT INTO bgi.incidencia (empresa_id, finca_id, bloque_id, cama_id, posicion_m, fuente_tipo, dispositivo_id, recorrido_id, problema_codigo, confianza, detectada_en, creada_en)
 VALUES ('11111111-1111-4111-8111-111111111111','f1000000-0000-4000-8000-000000000001','b1000000-0000-4000-8000-000000000001','c1000000-0000-4000-8000-000000000008',2,'robot','d0000000-0000-4000-8000-000000000001','e0000000-0000-4000-8000-000000000001','oidio',0.7,now(),now())$q$);
SELECT 'P5b salto detectada->cerrada' t, intentar($q$UPDATE bgi.incidencia SET estado='cerrada', cerrada_en=now(), resultado_cierre='controlada' WHERE codigo_corto='B03-C07-0042'$q$);
SELECT 'P5c pasa a verificacion_asignada' t, intentar($q$UPDATE bgi.incidencia SET estado='verificacion_asignada' WHERE codigo_corto='B03-C07-0042'$q$);
SELECT 'P5c2 confirmada sin verificacion' t, intentar($q$UPDATE bgi.incidencia SET estado='confirmada' WHERE codigo_corto='B03-C07-0042'$q$);
SELECT 'P5d confirmada con verificacion' t, intentar($q$UPDATE bgi.incidencia SET estado='confirmada', verificacion_resultado='confirmada', verificado_por='aaaaaaaa-0000-4000-8000-000000000003', verificado_en=now() WHERE codigo_corto='B03-C07-0042'$q$);
SELECT 'P5e version tras 2 updates' t, version::text FROM incidencia WHERE codigo_corto='B03-C07-0042';
SELECT 'P5f vista ICA: oidio confirmado' t, camas_con_hallazgo_confirmado || ' camas, ' || incidencia_camas_pct || ' %' FROM v_ica_monitoreo_plagas WHERE plaga_monitoreada='Oídio';
SELECT 'P5g editar evento (bgi_app)' t, intentar($q$UPDATE bgi.incidencia_evento SET tipo='comentario'$q$);
SELECT 'P5h robot asignado 2 veces' t, intentar($q$INSERT INTO bgi.asignacion_dispositivo (dispositivo_id, empresa_id, finca_id, vigencia) VALUES ('d0000000-0000-4000-8000-000000000001','11111111-1111-4111-8111-111111111111','f1000000-0000-4000-8000-000000000001', tstzrange('2026-11-01','2026-11-02'))$q$);
SELECT 'P5i cambios registrados para sync' t, count(*)::text FROM registro_cambios WHERE tabla='incidencia';
ROLLBACK;

\echo '--- P6 inmutabilidad para cualquier rol'
SELECT 'P6 superusuario edita evento' t, intentar($q$UPDATE bgi.incidencia_evento SET tipo='comentario'$q$);

\echo '--- P7 particiones de lecturas'
BEGIN;
INSERT INTO datastream (id, empresa_id, finca_id, variable, unidad, origen) VALUES
 ('5d000000-0000-4000-8000-000000000001','11111111-1111-4111-8111-111111111111','f1000000-0000-4000-8000-000000000001','humedad_relativa','%','sensor_propio');
SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111}';
INSERT INTO lectura_ambiental (empresa_id, datastream_id, medido_en, valor) VALUES
 ('11111111-1111-4111-8111-111111111111','5d000000-0000-4000-8000-000000000001','2026-10-24 06:00-05',91.0),
 ('11111111-1111-4111-8111-111111111111','5d000000-0000-4000-8000-000000000001','2027-02-01 06:00-05',80.0);
SELECT 'P7a particion' t, tableoid::regclass::text, count(*) FROM lectura_ambiental GROUP BY 2 ORDER BY 2;
SELECT 'P7b leer particion directo' t, intentar($q$SELECT * FROM bgi.lectura_ambiental_2026_10$q$);
SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
SELECT 'P7c empresa B ve lecturas de A' t, count(*) FROM lectura_ambiental;
ROLLBACK;

\echo '--- P8 alcance por finca (politica restrictiva)'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111}';
SET LOCAL app.fincas = '{f9999999-0000-4000-8000-000000000001}';
SELECT 'P8 operario de otra finca ve incidencias' t, count(*) FROM incidencia;
COMMIT;

\echo '--- P9 consola de flota del vendedor'
BEGIN; SET LOCAL ROLE bgi_flota;
SELECT 'P9a flota ve dispositivos' t, count(*)::text FROM dispositivo;
SELECT 'P9b flota lee incidencias' t, intentar($q$SELECT count(*) FROM bgi.incidencia$q$);
COMMIT;

\echo '--- P10 GeoJSON de camas (bloque A)'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111}';
SELECT jsonb_pretty(geojson_camas('b1000000-0000-4000-8000-000000000001', '2026-10-24'));
SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
SELECT 'P10b B pide GeoJSON del bloque de A' t, geojson_camas('b1000000-0000-4000-8000-000000000001', '2026-10-24')::text;
COMMIT;

\echo '--- P11 agronomo con dos empresas (asistente tecnico)'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111,22222222-2222-4222-8222-222222222222}';
SELECT 'P11 fincas visibles' t, count(*) FROM finca;
COMMIT;
