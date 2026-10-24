-- Pruebas adversarias del aislamiento multi-empresa (rol: verificacion-tecnica).
-- Se corren DESPUES de modelo_datos.sql (con o sin el sustituto de PostGIS) y de
-- en una base recien creada. Resultado esperado tras la correccion: ver resultado_ataques.txt.
-- Cada caso dice qué deberia pasar si el aislamiento fuera completo.
\set ON_ERROR_STOP 1
SET search_path = bgi, public;
-- Devuelve 'OK n filas' o el SQLSTATE del error. RLS filtra en silencio: un
-- UPDATE/DELETE bloqueado por RLS da 'OK 0 filas', no un error.
CREATE OR REPLACE FUNCTION public.intentar_filas(q text) RETURNS text LANGUAGE plpgsql AS $$
DECLARE n bigint;
BEGIN EXECUTE q; GET DIAGNOSTICS n = ROW_COUNT; RETURN 'OK ' || n || ' filas';
EXCEPTION WHEN OTHERS THEN RETURN SQLSTATE || ' ' || SQLERRM; END $$;
GRANT EXECUTE ON FUNCTION public.intentar_filas(text) TO bgi_app, bgi_flota;

-- Fila de auditoria de la empresa A (la crea el superusuario, como haria la API)
INSERT INTO auditoria (empresa_id, accion, objeto_tipo, objeto_id, ip, detalle)
VALUES ('11111111-1111-4111-8111-111111111111','exportar','exporte','x','10.0.0.1','{"tipo":"ica_aplicaciones"}');

\echo '--- V1 B lee la auditoria de A (deberia dar 0)'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
SELECT 'V1 filas de auditoria de A visibles para B' t, count(*) FROM auditoria WHERE empresa_id = '11111111-1111-4111-8111-111111111111';
ROLLBACK;

\echo '--- V2 A se apropia del robot prestado por el proveedor (deberia fallar)'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111}';
SELECT 'V2 A cambia dueno y huella mTLS del robot del proveedor' t, intentar_filas($q$UPDATE bgi.dispositivo
  SET empresa_id='11111111-1111-4111-8111-111111111111', propietario='empresa', certificado_huella='huella-falsa'
  WHERE id='d0000000-0000-4000-8000-000000000001'$q$);
ROLLBACK;

\echo '--- V3 B secuestra una fila del catalogo global (deberia fallar)'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
SELECT 'V3a B marca roya global como propia' t, intentar_filas($q$UPDATE bgi.problema_sanitario SET empresa_id='22222222-2222-4222-8222-222222222222' WHERE codigo='roya'$q$);
SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111}';
SELECT 'V3b filas ICA de A despues (antes 6)' t, count(*) FROM v_ica_monitoreo_plagas;
ROLLBACK;

\echo '--- V4 B secuestra o borra un modelo global (deberia fallar)'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
SELECT 'V4a B se apropia del modelo global roya_regla y cambia parametros' t, intentar_filas($q$UPDATE bgi.modelo_version SET empresa_id='22222222-2222-4222-8222-222222222222', parametros='{"umbral":99}' WHERE id='00000000-0000-4000-8000-0000000000a3'$q$);
SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111}';
SELECT 'V4b A todavia ve roya_regla' t, count(*) FROM modelo_version WHERE id='00000000-0000-4000-8000-0000000000a3';
ROLLBACK;
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
SELECT 'V4c B borra el problema global desconocido' t, intentar_filas($q$DELETE FROM bgi.problema_sanitario WHERE codigo='desconocido'$q$);
ROLLBACK;

\echo '--- V5 B referencia filas de A con llaves simples (deberia fallar)'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
INSERT INTO recorrido (id, empresa_id, finca_id, tipo, responsable_id, motivo, estado)
VALUES ('e2000000-0000-4000-8000-000000000001','22222222-2222-4222-8222-222222222222','f2000000-0000-4000-8000-000000000001','operario','aaaaaaaa-0000-4000-8000-000000000005','rutina','completado');
SELECT 'V5a recorrido_cama de B apunta a cama de A' t, intentar_filas($q$INSERT INTO bgi.recorrido_cama (recorrido_id, empresa_id, cama_id, orden, estado)
  VALUES ('e2000000-0000-4000-8000-000000000001','22222222-2222-4222-8222-222222222222','c1000000-0000-4000-8000-000000000007',1,'inspeccionada')$q$);
INSERT INTO producto_fitosanitario (id, empresa_id, nombre_comercial, ingrediente_activo, tipo, periodo_carencia_dias, periodo_reentrada_horas)
VALUES ('a2000000-0000-4000-8000-000000000001','22222222-2222-4222-8222-222222222222','Producto ficticio','ia ficticio','quimico',3,12);
INSERT INTO aplicacion_fitosanitaria (id, empresa_id, finca_id, bloque_id, producto_id, blanco_biologico_codigo, dosis_aplicada, dosis_unidad,
  metodo_aplicacion, inicio, periodo_carencia_dias, periodo_reentrada_horas, aplicado_por)
VALUES ('a2000000-0000-4000-8000-0000000000f1','22222222-2222-4222-8222-222222222222','f2000000-0000-4000-8000-000000000001','b2000000-0000-4000-8000-000000000001',
  'a2000000-0000-4000-8000-000000000001','botrytis',1,'ml/l','bomba_espalda',now(),3,12,'aaaaaaaa-0000-4000-8000-000000000005');
SELECT 'V5b aplicacion_cama de B apunta a cama de A' t, intentar_filas($q$INSERT INTO bgi.aplicacion_cama (aplicacion_id, empresa_id, cama_id, desde_m, hasta_m)
  VALUES ('a2000000-0000-4000-8000-0000000000f1','22222222-2222-4222-8222-222222222222','c1000000-0000-4000-8000-000000000007',0,5)$q$);
SELECT 'V5c incidencia de B "duplicada de" una incidencia de A' t, intentar_filas($q$INSERT INTO bgi.incidencia (empresa_id, finca_id, bloque_id, cama_id, posicion_m, fuente_tipo, reportado_por, problema_codigo, detectada_en, creada_en, incidencia_origen_id)
  VALUES ('22222222-2222-4222-8222-222222222222','f2000000-0000-4000-8000-000000000001','b2000000-0000-4000-8000-000000000001','c2000000-0000-4000-8000-000000000001',1,'operario','aaaaaaaa-0000-4000-8000-000000000005','botrytis',now(),now(),'0192f1a0-7c00-7000-8000-000000000042')$q$);
SELECT 'V5d recorrido de B usa el robot asignado hoy a A' t, intentar_filas($q$INSERT INTO bgi.recorrido (empresa_id, finca_id, tipo, dispositivo_id, responsable_id, motivo)
  VALUES ('22222222-2222-4222-8222-222222222222','f2000000-0000-4000-8000-000000000001','robot','d0000000-0000-4000-8000-000000000001','aaaaaaaa-0000-4000-8000-000000000005','rutina')$q$);
ROLLBACK;

\echo '--- V6 B renombra al agronomo compartido y cambia el registro ICA de A (deberia fallar)'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
SELECT 'V6 B edita el nombre del agronomo que tambien trabaja para A' t, intentar_filas($q$UPDATE bgi.usuario SET nombre='Nombre cambiado por B' WHERE id='aaaaaaaa-0000-4000-8000-000000000002'$q$);
ROLLBACK;

\echo '--- W1 usuario limitado a otra finca de la MISMA empresa (todo deberia dar 0)'
BEGIN;
INSERT INTO evidencia (empresa_id, incidencia_id, tipo, uri, sha256, capturada_en) VALUES
('11111111-1111-4111-8111-111111111111','0192f1a0-7c00-7000-8000-000000000042','recorte','s3://b/111/x.jpg', repeat('a',64), now());
SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111}';
SET LOCAL app.fincas = '{f9999999-0000-4000-8000-000000000001}';
SELECT 'W1 incidencias' t, count(*) FROM incidencia UNION ALL
SELECT 'W1 eventos de incidencias de otra finca', count(*) FROM incidencia_evento UNION ALL
SELECT 'W1 evidencias (fotos) de otra finca', count(*) FROM evidencia UNION ALL
SELECT 'W1 recorrido_cama de otra finca', count(*) FROM recorrido_cama UNION ALL
SELECT 'W1 registro_cambios de otra finca', count(*) FROM registro_cambios WHERE finca_id IS NOT NULL;
ROLLBACK;

\echo '--- X1 B se reserva para 2027 el robot compartido del proveedor (deberia fallar; ABIERTO)'
BEGIN; SET LOCAL ROLE bgi_app; SET LOCAL app.empresas = '{22222222-2222-4222-8222-222222222222}';
SELECT 'X1 B reserva el robot del proveedor para todo 2027' t, intentar_filas($q$INSERT INTO bgi.asignacion_dispositivo (dispositivo_id, empresa_id, finca_id, vigencia) VALUES ('d0000000-0000-4000-8000-000000000001','22222222-2222-4222-8222-222222222222','f2000000-0000-4000-8000-000000000001', tstzrange('2027-01-01','2027-12-31'))$q$);
ROLLBACK;

-- V5d (robot del proveedor asignado a A usado en un recorrido de B) sigue
-- abierto: dispositivo del proveedor tiene empresa_id NULL y no admite FK
-- compuesta. Propuesta: disparador que exija una asignacion vigente a la
-- empresa en la fecha del recorrido o del hallazgo.
