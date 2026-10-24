-- =============================================================================
-- Berry Good Idea · Modelo de datos multi-cliente (multi-tenant)
-- Rol: arquitectura-multifinca · Sabana Hack 2026
--
-- Motor:   PostgreSQL 16 o superior + PostGIS 3.x + btree_gist (contrib).
--          Se usa UNIQUE NULLS NOT DISTINCT y vistas security_invoker (PG 15+).
-- Probado: el DDL y las semillas se ejecutaron en PostgreSQL 16 (imagen
--          postgres:16-alpine) con un sustituto mínimo de PostGIS (ver
--          arquitectura.md, sección "Cómo se probó"). Con PostGIS real NO se
--          ha ejecutado todavía: las columnas geometry y los índices GiST
--          espaciales quedan NO VERIFICADOS en ejecución.
--
-- Jerarquía: empresa (cliente que paga) → finca → bloque (= "lote" ICA)
--            → cama (unidad lineal: cama, hilera, surco o línea de macetas)
--            → planta (opcional; casi siempre basta cama + metro).
--
-- Aislamiento entre clientes:
--   1. Todas las tablas de cliente llevan empresa_id.
--   2. Row Level Security (RLS) con FORCE: la API fija app.empresas (y, si el
--      usuario solo ve algunas fincas, app.fincas) al abrir cada transacción.
--      https://www.postgresql.org/docs/current/ddl-rowsecurity.html
--   3. Llaves foráneas compuestas (id, ..., empresa_id): la base de datos
--      impide que una incidencia de la empresa B apunte a una cama de la A.
--
-- Identificadores: UUID generados en el dispositivo (app, robot, nodo de borde)
--   para poder crear registros sin conexión. Se recomienda UUIDv7 (RFC 9562,
--   sección 5.7, ordenado por tiempo). PostgreSQL 18 trae uuidv7(); en 16 se usa
--   gen_random_uuid() (v4) solo como valor por defecto del lado servidor.
--
-- Vocabularios: texto + CHECK, no ENUM, para usar el mismo vocabulario en la
--   base SQLite del celular y en el JSON Schema (schema_incidencia.json).
--
-- Cambios de la verificación técnica (2026-10-23), marcados [verificacion-tecnica]:
--   * FK compuestas (cama_id, empresa_id) en recorrido_cama y aplicacion_cama, y
--     (incidencia_origen_id, empresa_id) en incidencia. Antes eran simples y B
--     podía apuntar a camas e incidencias de A.
--   * auditoria entra a RLS (antes B leía la auditoría de A).
--   * Políticas separadas por comando en usuario, problema_sanitario,
--     modelo_version y dispositivo. Antes, con FOR ALL, un cliente podía
--     secuestrar o borrar filas globales, cambiar el dueño y la huella mTLS del
--     robot prestado y renombrar a un usuario compartido con otra empresa.
--   * Alcance por finca también en incidencia_evento, evidencia, recorrido_cama
--     y registro_cambios.
--   * Semilla del modelo de antracnosis renombrada: lo implementado es Wilson
--     1990 + Gillett y Schilder 2009, no Miles 2013.
--   Pruebas: escalabilidad/verificacion_tecnica/ataques_multiempresa.sql.
--   Abiertos: reserva de robots del proveedor por el cliente (asignacion_dispositivo)
--   y llaves simples a dispositivo y modelo_version (ver arquitectura.md §13).
-- =============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS btree_gist;   -- para EXCLUDE (un robot, una finca a la vez)

CREATE SCHEMA IF NOT EXISTS bgi;
SET search_path = bgi, public;

-- -----------------------------------------------------------------------------
-- 0. Roles de base de datos (no son los roles de usuario de la app)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
  -- API de la plataforma: siempre sujeta a RLS.
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bgi_app') THEN
    CREATE ROLE bgi_app NOLOGIN NOBYPASSRLS;
  END IF;
  -- Consola de flota del vendedor: ve dispositivos y telemetría, NO datos agronómicos.
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bgi_flota') THEN
    CREATE ROLE bgi_flota NOLOGIN NOBYPASSRLS;
  END IF;
  -- Servicio de alta de clientes (onboarding). Único con BYPASSRLS; uso auditado.
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bgi_admin') THEN
    CREATE ROLE bgi_admin NOLOGIN BYPASSRLS;
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 1. Contexto de la sesión (lo fija la API en cada transacción)
--    SET LOCAL app.empresas = '{uuid1,uuid2}';  -- empresas permitidas
--    SET LOCAL app.fincas   = '{uuidF1}';       -- opcional: restringe fincas
--    SET LOCAL app.usuario  = 'uuidU';
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION app_empresas() RETURNS uuid[]
LANGUAGE sql STABLE AS $$
  SELECT COALESCE(NULLIF(current_setting('app.empresas', true), '')::uuid[], '{}'::uuid[])
$$;

CREATE OR REPLACE FUNCTION app_fincas() RETURNS uuid[]
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.fincas', true), '')::uuid[]   -- NULL = todas las fincas de la empresa
$$;

CREATE OR REPLACE FUNCTION app_usuario() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.usuario', true), '')::uuid
$$;

-- -----------------------------------------------------------------------------
-- 2. Clientes, usuarios y roles
-- -----------------------------------------------------------------------------
CREATE TABLE empresa (
  id                         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre                     text NOT NULL,
  nit                        text,                         -- identificación tributaria del país
  pais                       char(2) NOT NULL DEFAULT 'CO',
  zona_horaria               text NOT NULL DEFAULT 'America/Bogota',
  plan                       text NOT NULL DEFAULT 'monitoreo'
                             CHECK (plan IN ('piloto','monitoreo','monitoreo_robot','robot_servicio')),
  modalidad_datos            text NOT NULL DEFAULT 'compartida'
                             CHECK (modalidad_datos IN ('compartida','dedicada')),  -- pool o silo
  region_datos               text NOT NULL DEFAULT 'por_definir', -- región de nube pactada (Ley 1581, art. 26)
  consentimiento_mejora_modelos boolean NOT NULL DEFAULT false,   -- opt-in: imágenes para reentrenar
  retencion_anios            smallint NOT NULL DEFAULT 5
                             CHECK (retencion_anios >= 2),       -- Res. ICA 824/2022, Manual §8: mínimo 2 años
  activo                     boolean NOT NULL DEFAULT true,
  creado_en                  timestamptz NOT NULL DEFAULT now(),
  UNIQUE NULLS NOT DISTINCT (pais, nit)
);

-- Identidad global (una persona puede trabajar para varias empresas, p. ej. un
-- asistente técnico que atiende varias fincas de distintos dueños).
CREATE TABLE usuario (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sub_idp        text UNIQUE,                 -- "sub" del proveedor de identidad OIDC
  nombre         text NOT NULL,
  email          text UNIQUE,
  telefono_e164  text CHECK (telefono_e164 ~ '^\+[1-9][0-9]{6,14}$'),
  idioma         text NOT NULL DEFAULT 'es',
  activo         boolean NOT NULL DEFAULT true,
  creado_en      timestamptz NOT NULL DEFAULT now()
);

-- Rol de una persona dentro de una empresa.
CREATE TABLE membresia (
  id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id                uuid NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
  usuario_id                uuid NOT NULL REFERENCES usuario(id),
  rol                       text NOT NULL
                            CHECK (rol IN ('productor','agronomo','supervisor','operario','auditor','integracion')),
  fincas                    uuid[],          -- NULL = todas las fincas de la empresa
  es_asistente_tecnico_ica  boolean NOT NULL DEFAULT false,  -- Res. ICA 824/2022, art. 3.1 y 13.2
  tarjeta_profesional       text,
  vigente_desde             date NOT NULL DEFAULT current_date,
  vigente_hasta             date,            -- auditor: acceso con fecha de fin
  UNIQUE (empresa_id, usuario_id, rol),
  CHECK (rol <> 'auditor' OR vigente_hasta IS NOT NULL)
);

-- Personal del vendedor de la solución (técnicos, soporte, equipo de ML).
CREATE TABLE personal_proveedor (
  usuario_id     uuid PRIMARY KEY REFERENCES usuario(id),
  rol_proveedor  text NOT NULL
                 CHECK (rol_proveedor IN ('tecnico_campo','soporte','ml','administrador_plataforma')),
  activo         boolean NOT NULL DEFAULT true
);

-- El técnico del vendedor solo entra a datos agronómicos de un cliente con una
-- concesión aprobada por el cliente, con motivo y fecha de fin. Queda auditada.
CREATE TABLE concesion_soporte (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id     uuid NOT NULL REFERENCES empresa(id) ON DELETE CASCADE,
  usuario_id     uuid NOT NULL REFERENCES personal_proveedor(usuario_id),
  alcance        text NOT NULL CHECK (alcance IN ('dispositivos','agronomico_lectura','agronomico_escritura')),
  motivo         text NOT NULL,
  aprobado_por   uuid NOT NULL REFERENCES usuario(id),
  vigencia       tstzrange NOT NULL,
  creado_en      timestamptz NOT NULL DEFAULT now(),
  CHECK (upper(vigencia) - lower(vigencia) <= interval '30 days')   -- SUPUESTO: tope de 30 días
);

-- -----------------------------------------------------------------------------
-- 3. Catálogos (globales; un cliente puede añadir los suyos con empresa_id)
-- -----------------------------------------------------------------------------
CREATE TABLE especie (
  codigo             text PRIMARY KEY CHECK (codigo ~ '^[a-z0-9_]+$'),
  nombre_comun       text NOT NULL,
  nombre_cientifico  text NOT NULL,
  eppo_code          text,              -- https://gd.eppo.int (p. ej. VACCO, FRAAN, PHYPE)
  ciclo_ica          text CHECK (ciclo_ica IN ('corto','medio','largo')),  -- Res. ICA 824/2022, art. 3.3-3.5
  unidad_lineal      text NOT NULL DEFAULT 'cama'
                     CHECK (unidad_lineal IN ('cama','hilera','surco','linea_macetas'))
);

CREATE TABLE problema_sanitario (
  codigo               text PRIMARY KEY CHECK (codigo ~ '^[a-z0-9_]+$'),
  empresa_id           uuid REFERENCES empresa(id),   -- NULL = catálogo global
  nombre               text NOT NULL,
  tipo                 text NOT NULL CHECK (tipo IN ('enfermedad','plaga','fisiopatia','abiotico','desconocido')),
  agente_cientifico    text,
  eppo_code            text,        -- solo si el agente está confirmado
  control_oficial_ica  boolean NOT NULL DEFAULT false
);

CREATE TABLE especie_problema (
  especie_codigo   text NOT NULL REFERENCES especie(codigo),
  problema_codigo  text NOT NULL REFERENCES problema_sanitario(codigo),
  monitoreo_obligatorio boolean NOT NULL DEFAULT true,   -- aparece en el registro ICA aunque el resultado sea 0
  PRIMARY KEY (especie_codigo, problema_codigo)
);

-- Estados de la incidencia y transiciones permitidas (datos, no código).
CREATE TABLE transicion_estado (
  desde  text NOT NULL,
  hasta  text NOT NULL,
  PRIMARY KEY (desde, hasta)
);

-- -----------------------------------------------------------------------------
-- 4. Geografía de la operación: finca → bloque → cama → planta
--    Geometrías en WGS 84 (EPSG:4326), igual que GeoJSON (RFC 7946, §4).
-- -----------------------------------------------------------------------------
CREATE TABLE finca (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id                  uuid NOT NULL REFERENCES empresa(id),
  nombre                      text NOT NULL,
  codigo_ica_lugar_produccion text,       -- registro ICA del lugar de producción (Res. 824/2022, art. 5)
  departamento                text,
  municipio                   text,
  vereda                      text,
  altitud_m                   numeric(6,1),
  zona_horaria                text NOT NULL DEFAULT 'America/Bogota',
  conectividad                text NOT NULL DEFAULT 'desconocida'
                              CHECK (conectividad IN ('ninguna','celular','wifi','satelital','mixta','desconocida')),
  region_perfil               text,       -- capa regional del perfil de cultivo (cultivos.md §7.3), p. ej. 'sabana_bogota'
  limite                      geometry(MultiPolygon, 4326),
  creado_en                   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (id, empresa_id)
);

CREATE TABLE bloque (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id       uuid NOT NULL,
  finca_id         uuid NOT NULL,
  codigo           text NOT NULL,            -- se exporta como "lote" en los registros ICA
  nombre           text,
  especie_codigo   text NOT NULL REFERENCES especie(codigo),
  perfil_cultivo   text CHECK (perfil_cultivo ~ '^[a-z0-9_]+@[0-9]+[.][0-9]+[.][0-9]+$'),
                   -- versión fija del perfil YAML (escalabilidad/perfiles/), p. ej. 'arandano@0.1.0'
  variedad         text,
  fecha_siembra    date,
  sistema_cultivo  text CHECK (sistema_cultivo IN ('suelo','maceta','sustrato','hidroponico')),
  cubierta         text CHECK (cubierta IN ('campo_abierto','macrotunel','invernadero')),
  area_ha          numeric(8,3) CHECK (area_ha > 0),
  geom             geometry(Polygon, 4326),
  activo           boolean NOT NULL DEFAULT true,
  UNIQUE (finca_id, codigo),
  UNIQUE (id, finca_id, empresa_id),
  FOREIGN KEY (finca_id, empresa_id) REFERENCES finca(id, empresa_id)
);

CREATE TABLE cama (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id           uuid NOT NULL,
  finca_id             uuid NOT NULL,
  bloque_id            uuid NOT NULL,
  numero               integer NOT NULL CHECK (numero > 0),
  tipo_unidad          text NOT NULL DEFAULT 'cama'
                       CHECK (tipo_unidad IN ('cama','hilera','surco','linea_macetas')),
  -- Eje de la cama, de la cabecera (metro 0) al final. Mirando desde la
  -- cabecera hacia el final, el lado A queda a la izquierda y el B a la derecha.
  eje                  geometry(LineString, 4326),
  poligono             geometry(Polygon, 4326),       -- opcional, para el mapa de calor
  longitud_m           numeric(7,2) CHECK (longitud_m > 0),
  ancho_m              numeric(4,2) CHECK (ancho_m > 0),
  distancia_plantas_m  numeric(4,2) CHECK (distancia_plantas_m > 0),
  plantas_n            integer CHECK (plantas_n >= 0),
  marcador_cabecera    text,      -- id del marcador ArUco/QR que el robot lee al entrar
  activo               boolean NOT NULL DEFAULT true,
  UNIQUE (bloque_id, numero),
  UNIQUE (id, bloque_id, finca_id, empresa_id),
  UNIQUE (id, empresa_id),   -- [verificacion-tecnica] para FK compuestas desde recorrido_cama y aplicacion_cama
  FOREIGN KEY (bloque_id, finca_id, empresa_id) REFERENCES bloque(id, finca_id, empresa_id)
);

-- Solo si el cliente marca plantas individuales (etiqueta, QR). Si no, la
-- incidencia se ubica con cama + metro + lado.
CREATE TABLE planta (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id    uuid NOT NULL,
  finca_id      uuid NOT NULL,
  bloque_id     uuid NOT NULL,
  cama_id       uuid NOT NULL,
  posicion_m    numeric(7,2) NOT NULL CHECK (posicion_m >= 0),
  etiqueta      text,
  geom          geometry(Point, 4326),
  fecha_siembra date,
  estado        text NOT NULL DEFAULT 'activa' CHECK (estado IN ('activa','resiembra','eliminada')),
  UNIQUE (cama_id, posicion_m),
  UNIQUE (id, cama_id, empresa_id),
  FOREIGN KEY (cama_id, bloque_id, finca_id, empresa_id) REFERENCES cama(id, bloque_id, finca_id, empresa_id)
);

-- -----------------------------------------------------------------------------
-- 5. Dispositivos: robots, nodos de sensores, gateways, nodo de borde
--    Un robot del vendedor (empresa_id NULL) se presta a fincas de varios
--    clientes (servicio compartido). Lo que mide en una finca es del dueño de
--    esa finca, no del dueño del robot.
-- -----------------------------------------------------------------------------
CREATE TABLE dispositivo (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id            uuid REFERENCES empresa(id),
  propietario           text NOT NULL CHECK (propietario IN ('proveedor','empresa')),
  tipo                  text NOT NULL CHECK (tipo IN ('robot','nodo_sensor','gateway','nodo_borde',
                                                      'camara_aspersora','estacion_externa','telefono')),
  fabricante            text,
  modelo                text,         -- p. ej. 'AgiBot D1 EDU' (prototipo), 'AgiBot D1 Ultra'
  serial                text NOT NULL UNIQUE,
  firmware              text,
  certificado_huella    text,         -- huella del certificado mTLS del dispositivo
  estado                text NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo','mantenimiento','baja')),
  metadatos             jsonb NOT NULL DEFAULT '{}'::jsonb,
  creado_en             timestamptz NOT NULL DEFAULT now(),
  CHECK ((propietario = 'proveedor' AND empresa_id IS NULL)
      OR (propietario = 'empresa'   AND empresa_id IS NOT NULL))
);

CREATE TABLE asignacion_dispositivo (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dispositivo_id  uuid NOT NULL REFERENCES dispositivo(id),
  empresa_id      uuid NOT NULL,
  finca_id        uuid NOT NULL,
  bloque_id       uuid,
  cama_id         uuid,
  ubicacion       geometry(Point, 4326),   -- sitio de instalación (sensores fijos)
  altura_m        numeric(4,2),            -- altura del sensor sobre el suelo
  vigencia        tstzrange NOT NULL,
  FOREIGN KEY (finca_id, empresa_id) REFERENCES finca(id, empresa_id),
  -- Un mismo robot no puede estar asignado a dos fincas al mismo tiempo.
  EXCLUDE USING gist (dispositivo_id WITH =, vigencia WITH &&)
);

CREATE TABLE telemetria_dispositivo (
  dispositivo_id  uuid NOT NULL REFERENCES dispositivo(id),
  medido_en       timestamptz NOT NULL,
  bateria_pct     numeric(5,2) CHECK (bateria_pct BETWEEN 0 AND 100),
  temperatura_c   numeric(5,2),
  estado          text,
  errores         jsonb,
  PRIMARY KEY (dispositivo_id, medido_en)
);

-- -----------------------------------------------------------------------------
-- 6. Lecturas ambientales (modelo inspirado en OGC SensorThings API:
--    Thing = dispositivo, Datastream = datastream, Observation = lectura)
--    https://docs.ogc.org/is/18-088/18-088.html
-- -----------------------------------------------------------------------------
CREATE TABLE datastream (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id         uuid NOT NULL,
  finca_id           uuid NOT NULL,
  dispositivo_id     uuid REFERENCES dispositivo(id),
  variable           text NOT NULL CHECK (variable IN ('temperatura_aire','humedad_relativa','punto_rocio',
                       'hoja_mojada','precipitacion','radiacion_solar','velocidad_viento',
                       'temperatura_suelo','humedad_suelo')),
  unidad             text NOT NULL,    -- '°C', '%', 'min/h', 'mm', 'W/m2', 'm/s'
  bloque_id          uuid,
  cama_id            uuid,
  altura_m           numeric(4,2),
  origen             text NOT NULL CHECK (origen IN ('sensor_propio','estacion_cliente','api_externa','derivado')),
  proveedor_externo  text,             -- 'metos_fieldclimate', 'open_meteo', ...
  activo             boolean NOT NULL DEFAULT true,
  UNIQUE (id, empresa_id),
  FOREIGN KEY (finca_id, empresa_id) REFERENCES finca(id, empresa_id)
);

-- Particionada por mes. La llave primaria incluye la columna de partición,
-- como exige PostgreSQL (docs, §5.12.2.3).
CREATE TABLE lectura_ambiental (
  empresa_id     uuid NOT NULL,
  datastream_id  uuid NOT NULL,
  medido_en      timestamptz NOT NULL,
  valor          double precision NOT NULL,
  calidad        smallint NOT NULL DEFAULT 0
                 CHECK (calidad IN (0,1,2,3)),  -- 0 ok · 1 sospechosa · 2 interpolada · 3 rechazada
  recibido_en    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (datastream_id, medido_en),
  FOREIGN KEY (datastream_id, empresa_id) REFERENCES datastream(id, empresa_id)
) PARTITION BY RANGE (medido_en);

CREATE TABLE lectura_ambiental_2026_10 PARTITION OF lectura_ambiental
  FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');
CREATE TABLE lectura_ambiental_2026_11 PARTITION OF lectura_ambiental
  FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');
CREATE TABLE lectura_ambiental_2026_12 PARTITION OF lectura_ambiental
  FOR VALUES FROM ('2026-12-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');
CREATE TABLE lectura_ambiental_defecto PARTITION OF lectura_ambiental DEFAULT;
-- En producción, un trabajo programado crea la partición del mes siguiente.

-- -----------------------------------------------------------------------------
-- 7. Modelos (riesgo y clasificador) versionados, y riesgo calculado
-- -----------------------------------------------------------------------------
CREATE TABLE modelo_version (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id       uuid REFERENCES empresa(id),     -- NULL = global; con valor = calibración de un cliente
  finca_id         uuid,                            -- calibración de una finca (precedencia finca > región > cultivo)
  perfil_origen    text,                            -- perfil YAML del que sale, p. ej. 'arandano@0.1.0'
  tipo             text NOT NULL CHECK (tipo IN ('riesgo','clasificador','planificador')),
  nombre           text NOT NULL,                   -- 'antracnosis_wilson1990_arandano', 'clasificador_hoja_arandano'
  version          text NOT NULL,
  especie_codigo   text REFERENCES especie(codigo),
  problema_codigo  text REFERENCES problema_sanitario(codigo),
  parametros       jsonb NOT NULL DEFAULT '{}'::jsonb,   -- umbrales, coeficientes (cada uno con fuente o SUPUESTO)
  metricas         jsonb,                             -- matriz de confusión, sensibilidad, conjunto de prueba
  clases           text[],                            -- clases del clasificador → códigos de problema_sanitario
  referencia       text,                              -- artículo o fuente
  licencia         text,
  estado           text NOT NULL DEFAULT 'experimental' CHECK (estado IN ('experimental','validado','retirado')),
  creado_en        timestamptz NOT NULL DEFAULT now(),
  UNIQUE NULLS NOT DISTINCT (empresa_id, finca_id, nombre, version),
  FOREIGN KEY (finca_id, empresa_id) REFERENCES finca(id, empresa_id)
);

CREATE TABLE riesgo_calculado (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id         uuid NOT NULL,
  finca_id           uuid NOT NULL,
  bloque_id          uuid NOT NULL,
  cama_id            uuid,                 -- NULL = riesgo de todo el bloque
  fecha              date NOT NULL,
  problema_codigo    text NOT NULL REFERENCES problema_sanitario(codigo),
  modelo_version_id  uuid NOT NULL REFERENCES modelo_version(id),
  valor              numeric,
  nivel              text NOT NULL CHECK (nivel IN ('bajo','medio','alto','muy_alto')),
  insumos            jsonb,                -- horas de mojadura, T media, fuente del clima
  calculado_en       timestamptz NOT NULL DEFAULT now(),
  calculado_en_borde boolean NOT NULL DEFAULT false,  -- true si lo calculó el nodo de la finca sin conexión
  UNIQUE NULLS NOT DISTINCT (bloque_id, cama_id, fecha, problema_codigo, modelo_version_id),
  FOREIGN KEY (bloque_id, finca_id, empresa_id) REFERENCES bloque(id, finca_id, empresa_id)
);

-- -----------------------------------------------------------------------------
-- 8. Recorridos (misiones del robot o rondas del monitor humano)
-- -----------------------------------------------------------------------------
CREATE TABLE recorrido (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id         uuid NOT NULL,
  finca_id           uuid NOT NULL,
  tipo               text NOT NULL CHECK (tipo IN ('robot','operario','camara_aspersora')),
  dispositivo_id     uuid REFERENCES dispositivo(id),
  responsable_id     uuid NOT NULL REFERENCES usuario(id),  -- persona responsable (el registro ICA pide un nombre)
  motivo             text NOT NULL CHECK (motivo IN ('rutina','riesgo_alto','seguimiento','verificacion','demo')),
  estado             text NOT NULL DEFAULT 'planificado'
                     CHECK (estado IN ('planificado','en_curso','pausado','completado','abortado')),
  planificado_para   timestamptz,
  inicio             timestamptz,
  fin                timestamptz,
  hoja_seca          boolean,             -- el robot va delante del aspersor, sobre hoja seca
  camara             text CHECK (camara IN ('base','mastil','ambas','telefono')),
  modelo_version_id  uuid REFERENCES modelo_version(id),    -- clasificador usado en la misión
  bateria_inicio_pct numeric(5,2),
  bateria_fin_pct    numeric(5,2),
  distancia_m        numeric(9,1),
  traza              geometry(LineString, 4326),
  version            integer NOT NULL DEFAULT 1,
  creado_en          timestamptz NOT NULL DEFAULT now(),
  actualizado_en     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (id, empresa_id),
  FOREIGN KEY (finca_id, empresa_id) REFERENCES finca(id, empresa_id),
  CHECK (tipo <> 'robot' OR dispositivo_id IS NOT NULL),
  CHECK (fin IS NULL OR inicio IS NULL OR fin >= inicio)
);

-- Plan y resultado por cama (en qué orden, con qué prioridad, qué se cubrió).
CREATE TABLE recorrido_cama (
  recorrido_id    uuid NOT NULL,
  empresa_id      uuid NOT NULL,
  cama_id         uuid NOT NULL,   -- [verificacion-tecnica] antes REFERENCES cama(id): B podía apuntar a una cama de A
  lado            text NOT NULL DEFAULT 'ambos' CHECK (lado IN ('A','B','ambos')),
  orden           integer NOT NULL,
  prioridad       numeric,                  -- riesgo que la puso primero
  estado          text NOT NULL DEFAULT 'pendiente'
                  CHECK (estado IN ('pendiente','inspeccionada','omitida','bloqueada')),
  motivo_omision  text,
  inicio          timestamptz,
  fin             timestamptz,
  cobertura_pct   numeric(5,2) CHECK (cobertura_pct BETWEEN 0 AND 100),
  cuadros_n       integer,
  hallazgos_n     integer,
  PRIMARY KEY (recorrido_id, cama_id, lado),
  FOREIGN KEY (recorrido_id, empresa_id) REFERENCES recorrido(id, empresa_id) ON DELETE CASCADE,
  FOREIGN KEY (cama_id, empresa_id) REFERENCES cama(id, empresa_id)
);

-- -----------------------------------------------------------------------------
-- 9. Incidencias (el corazón del sistema) y su historial inmutable
-- -----------------------------------------------------------------------------
CREATE TABLE incidencia (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id               uuid NOT NULL,
  finca_id                 uuid NOT NULL,
  bloque_id                uuid NOT NULL,
  cama_id                  uuid NOT NULL,
  planta_id                uuid,
  codigo_corto             text,           -- legible en campo, p. ej. 'B03-C07-0042'
  estado                   text NOT NULL DEFAULT 'detectada'
                           CHECK (estado IN ('detectada','en_triage','verificacion_asignada','confirmada',
                                             'descartada','tratamiento_recomendado','tratada',
                                             'en_seguimiento','cerrada','duplicada')),
  prioridad                text CHECK (prioridad IN ('P1','P2','P3')),

  -- Ubicación (cama + metro funciona aunque el GPS falle bajo macrotúnel)
  posicion_m               numeric(7,2) CHECK (posicion_m >= 0),   -- metros desde la cabecera
  lado                     text NOT NULL DEFAULT 'desconocido' CHECK (lado IN ('A','B','ambos','desconocido')),
  altura_dosel             text NOT NULL DEFAULT 'desconocida' CHECK (altura_dosel IN ('baja','media','alta','desconocida')),
  punto                    geometry(Point, 4326),
  precision_m              numeric(6,2),
  metodo_ubicacion         text CHECK (metodo_ubicacion IN ('marcador_odometria','gnss','gnss_rtk','manual','derivado_cama')),

  -- Origen
  fuente_tipo              text NOT NULL CHECK (fuente_tipo IN ('robot','operario','sensor_fijo',
                                                                'modelo_riesgo','camara_aspersora','externo')),
  dispositivo_id           uuid REFERENCES dispositivo(id),
  recorrido_id             uuid,
  reportado_por            uuid REFERENCES usuario(id),

  -- Detección
  problema_codigo          text NOT NULL REFERENCES problema_sanitario(codigo),   -- sospecha inicial
  problema_confirmado_codigo text REFERENCES problema_sanitario(codigo),          -- tras verificación/laboratorio
  modelo_version_id        uuid REFERENCES modelo_version(id),
  confianza                numeric(4,3) CHECK (confianza BETWEEN 0 AND 1),
  clases_top               jsonb,          -- [{"clase":"oidio","prob":0.81}, ...]
  organo                   text CHECK (organo IN ('hoja_haz','hoja_enves','flor','fruto','tallo','planta_completa','desconocido')),
  severidad                smallint CHECK (severidad BETWEEN 0 AND 5),   -- escala 0-5: SUPUESTO, la fija el agrónomo
  plantas_afectadas_est    integer CHECK (plantas_afectadas_est >= 0),
  longitud_afectada_m      numeric(6,2) CHECK (longitud_afectada_m >= 0),
  descripcion              text,

  -- Contexto ambiental en el momento de la captura
  hoja_mojada_captura      boolean,        -- la hoja mojada sube las falsas alarmas
  contexto_ambiental       jsonb,          -- {temperatura_c, humedad_relativa_pct, horas_mojadura_24h, riesgos:[...]}

  -- Triage (agrónomo) y verificación (operario)
  triage_decision          text CHECK (triage_decision IN ('verificar','tratar_directo','vigilar','descartar')),
  triage_por               uuid REFERENCES usuario(id),
  triage_en                timestamptz,
  triage_nota              text,
  asignado_a               uuid REFERENCES usuario(id),
  verificacion_resultado   text CHECK (verificacion_resultado IN ('confirmada','descartada','no_concluyente')),
  verificado_por           uuid REFERENCES usuario(id),
  verificado_en            timestamptz,
  motivo_descarte          text CHECK (motivo_descarte IN ('hoja_mojada','sombra_o_luz','dano_mecanico',
                                       'otro_problema','planta_sana','imagen_borrosa','duplicado','otro')),

  -- Cierre y relaciones
  incidencia_origen_id     uuid,   -- duplicada de / seguimiento de. [verificacion-tecnica] FK compuesta abajo (antes simple)
  resultado_cierre         text CHECK (resultado_cierre IN ('controlada','persistente','planta_eliminada','falsa_alarma')),
  cerrada_en               timestamptz,

  -- Tiempos y sincronización
  detectada_en             timestamptz NOT NULL,              -- momento de la captura
  creada_en                timestamptz NOT NULL,              -- reloj del dispositivo que la creó
  recibida_en              timestamptz NOT NULL DEFAULT now(),-- llegada al servidor
  actualizada_en           timestamptz NOT NULL DEFAULT now(),
  version                  integer NOT NULL DEFAULT 1,        -- concurrencia optimista
  origen_registro          text,                              -- 'nodo_borde:<serial>', 'app:<instalación>'
  privacidad_rostros_difuminados boolean NOT NULL DEFAULT true,
  extra                    jsonb NOT NULL DEFAULT '{}'::jsonb, -- campos propios de otro cultivo

  UNIQUE (id, empresa_id),
  FOREIGN KEY (cama_id, bloque_id, finca_id, empresa_id) REFERENCES cama(id, bloque_id, finca_id, empresa_id),
  FOREIGN KEY (planta_id, cama_id, empresa_id) REFERENCES planta(id, cama_id, empresa_id),
  FOREIGN KEY (recorrido_id, empresa_id) REFERENCES recorrido(id, empresa_id),
  FOREIGN KEY (incidencia_origen_id, empresa_id) REFERENCES incidencia(id, empresa_id),

  -- Reglas de consistencia (las mismas que el JSON Schema)
  CHECK (fuente_tipo <> 'robot' OR (dispositivo_id IS NOT NULL AND recorrido_id IS NOT NULL
                                    AND modelo_version_id IS NOT NULL AND confianza IS NOT NULL)),
  CHECK (fuente_tipo <> 'operario' OR reportado_por IS NOT NULL),
  CHECK (posicion_m IS NOT NULL OR punto IS NOT NULL),
  -- COALESCE: un CHECK con NULL pasa; sin él, 'confirmada' sin verificación entraría.
  CHECK (estado <> 'confirmada'  OR COALESCE(verificacion_resultado = 'confirmada', false)),
  CHECK (estado <> 'descartada'  OR motivo_descarte IS NOT NULL),
  CHECK (estado <> 'duplicada'   OR incidencia_origen_id IS NOT NULL),
  CHECK (estado <> 'cerrada'     OR (cerrada_en IS NOT NULL AND resultado_cierre IS NOT NULL))
);

-- Historial: cada cambio es un evento inmutable. Si dos personas actúan sin
-- conexión sobre la misma incidencia, los dos eventos se guardan y el servidor
-- marca el conflicto para que lo resuelva el agrónomo.
CREATE TABLE incidencia_evento (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id           uuid NOT NULL,
  incidencia_id        uuid NOT NULL,
  tipo                 text NOT NULL CHECK (tipo IN ('creada','evidencia_agregada','triage','asignada',
                         'verificada','recomendacion','tratamiento_registrado','reinspeccion',
                         'comentario','estado_cambiado','fusionada','exportada','conflicto')),
  estado_anterior      text,
  estado_nuevo         text,
  actor_usuario_id     uuid REFERENCES usuario(id),
  actor_dispositivo_id uuid REFERENCES dispositivo(id),
  datos                jsonb NOT NULL DEFAULT '{}'::jsonb,
  ocurrido_en          timestamptz NOT NULL,           -- reloj del dispositivo
  recibido_en          timestamptz NOT NULL DEFAULT now(),
  aplicado             boolean NOT NULL DEFAULT true,  -- false si se rechazó por conflicto
  FOREIGN KEY (incidencia_id, empresa_id) REFERENCES incidencia(id, empresa_id),
  CHECK (actor_usuario_id IS NOT NULL OR actor_dispositivo_id IS NOT NULL)
);

CREATE TABLE evidencia (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id           uuid NOT NULL,
  incidencia_id        uuid NOT NULL,
  tipo                 text NOT NULL CHECK (tipo IN ('imagen_original','recorte','miniatura','video',
                                                    'nota_voz','imagen_verificacion')),
  uri                  text NOT NULL,     -- objeto bajo el prefijo de la empresa: <bucket>/<empresa_id>/...
  sha256               char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  bytes                bigint,
  mime                 text,
  ancho_px             integer,
  alto_px              integer,
  camara               text CHECK (camara IN ('base','mastil','telefono','aspersora')),
  bbox                 jsonb,             -- {"x":0.41,"y":0.22,"w":0.10,"h":0.08} normalizado 0-1
  capturada_en         timestamptz NOT NULL,
  subida_estado        text NOT NULL DEFAULT 'pendiente' CHECK (subida_estado IN ('pendiente','miniatura','completa')),
  rostros_difuminados  boolean NOT NULL DEFAULT true,
  uso_entrenamiento_autorizado boolean NOT NULL DEFAULT false,
  FOREIGN KEY (incidencia_id, empresa_id) REFERENCES incidencia(id, empresa_id)
);

-- -----------------------------------------------------------------------------
-- 10. Recomendación del agrónomo, tareas y aplicaciones fitosanitarias
--     Campos de la Res. ICA 824/2022, Manual §8.2.6 (visitas del asistente
--     técnico) y §8.2.7 (aplicación de plaguicidas), y de la Res. ICA
--     30021/2017 (BPA).
-- -----------------------------------------------------------------------------
CREATE TABLE producto_fitosanitario (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id               uuid NOT NULL REFERENCES empresa(id),
  nombre_comercial         text NOT NULL,
  ingrediente_activo       text NOT NULL,
  concentracion            text,
  registro_ica             text,          -- registro ICA del producto
  tipo                     text NOT NULL CHECK (tipo IN ('quimico','bioinsumo','otro')),
  periodo_carencia_dias    numeric(5,1) NOT NULL CHECK (periodo_carencia_dias >= 0),
  periodo_reentrada_horas  numeric(6,1) NOT NULL CHECK (periodo_reentrada_horas >= 0),
  blancos_autorizados      text[],        -- códigos de problema_sanitario de la etiqueta
  activo                   boolean NOT NULL DEFAULT true,
  UNIQUE (id, empresa_id)
);

CREATE TABLE recomendacion (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id           uuid NOT NULL,
  finca_id             uuid NOT NULL,
  tipo                 text NOT NULL CHECK (tipo IN ('tratamiento','labor_cultural','vigilancia','eliminacion_plantas')),
  emitida_por          uuid NOT NULL REFERENCES usuario(id),   -- agrónomo / asistente técnico
  emitida_en           timestamptz NOT NULL,
  estado_fitosanitario text,                                   -- ICA §8.2.6
  producto_id          uuid,
  dosis                numeric,
  dosis_unidad         text,
  volumen_mezcla_l     numeric,
  metodo_aplicacion    text,
  alcance              jsonb,          -- [{"cama_id":"...","desde_m":10,"hasta_m":18}]
  justificacion        text NOT NULL,
  firma                jsonb,          -- {"metodo":"otp","hash":"...","momento":"..."}
  estado               text NOT NULL DEFAULT 'emitida' CHECK (estado IN ('emitida','en_ejecucion','ejecutada','anulada')),
  UNIQUE (id, empresa_id),
  FOREIGN KEY (finca_id, empresa_id) REFERENCES finca(id, empresa_id),
  FOREIGN KEY (producto_id, empresa_id) REFERENCES producto_fitosanitario(id, empresa_id),
  CHECK (tipo <> 'tratamiento' OR (producto_id IS NOT NULL AND dosis IS NOT NULL AND dosis_unidad IS NOT NULL))
);

CREATE TABLE recomendacion_incidencia (
  recomendacion_id  uuid NOT NULL,
  incidencia_id     uuid NOT NULL,
  empresa_id        uuid NOT NULL,
  PRIMARY KEY (recomendacion_id, incidencia_id),
  FOREIGN KEY (recomendacion_id, empresa_id) REFERENCES recomendacion(id, empresa_id),
  FOREIGN KEY (incidencia_id, empresa_id) REFERENCES incidencia(id, empresa_id)
);

CREATE TABLE tarea (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id        uuid NOT NULL,
  finca_id          uuid NOT NULL,
  tipo              text NOT NULL CHECK (tipo IN ('verificar_incidencia','aplicar_tratamiento','reinspeccionar',
                                                 'mantenimiento_dispositivo','resolver_conflicto')),
  incidencia_id     uuid,
  recomendacion_id  uuid,
  asignada_a        uuid REFERENCES usuario(id),
  creada_por        uuid REFERENCES usuario(id),
  vence_en          timestamptz,
  estado            text NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','en_curso','hecha','cancelada')),
  completada_en     timestamptz,
  nota              text,
  version           integer NOT NULL DEFAULT 1,
  actualizado_en    timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (finca_id, empresa_id) REFERENCES finca(id, empresa_id),
  FOREIGN KEY (incidencia_id, empresa_id) REFERENCES incidencia(id, empresa_id),
  FOREIGN KEY (recomendacion_id, empresa_id) REFERENCES recomendacion(id, empresa_id)
);

CREATE TABLE aplicacion_fitosanitaria (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id               uuid NOT NULL,
  finca_id                 uuid NOT NULL,
  bloque_id                uuid NOT NULL,
  recomendacion_id         uuid,
  producto_id              uuid NOT NULL,
  blanco_biologico_codigo  text NOT NULL REFERENCES problema_sanitario(codigo),
  lote_producto            text,
  dosis_aplicada           numeric NOT NULL CHECK (dosis_aplicada > 0),
  dosis_unidad             text NOT NULL,
  volumen_total_l          numeric,
  metodo_aplicacion        text NOT NULL CHECK (metodo_aplicacion IN ('bomba_espalda','estacionaria_manguera',
                             'tractor','dron','aspersion_dirigida','otro')),
  equipo_id                uuid REFERENCES dispositivo(id),
  inicio                   timestamptz NOT NULL,
  fin                      timestamptz,
  periodo_carencia_dias    numeric(5,1) NOT NULL,   -- copiado del producto al momento de aplicar
  periodo_reentrada_horas  numeric(6,1) NOT NULL,
  aplicado_por             uuid NOT NULL REFERENCES usuario(id),
  recomendado_por          uuid REFERENCES usuario(id),
  firma_aplicador          jsonb,
  condiciones              jsonb,                   -- clima al aplicar
  area_tratada_m2          numeric,
  version                  integer NOT NULL DEFAULT 1,
  UNIQUE (id, empresa_id),
  FOREIGN KEY (bloque_id, finca_id, empresa_id) REFERENCES bloque(id, finca_id, empresa_id),
  FOREIGN KEY (recomendacion_id, empresa_id) REFERENCES recomendacion(id, empresa_id),
  FOREIGN KEY (producto_id, empresa_id) REFERENCES producto_fitosanitario(id, empresa_id),
  CHECK (fin IS NULL OR fin >= inicio)
);

-- Tramos tratados (aspersión dirigida: solo los metros con hallazgo).
CREATE TABLE aplicacion_cama (
  aplicacion_id  uuid NOT NULL,
  empresa_id     uuid NOT NULL,
  cama_id        uuid NOT NULL,   -- [verificacion-tecnica] antes REFERENCES cama(id): B podía apuntar a una cama de A
  desde_m        numeric(7,2) NOT NULL DEFAULT 0,
  hasta_m        numeric(7,2),
  PRIMARY KEY (aplicacion_id, cama_id, desde_m),
  FOREIGN KEY (aplicacion_id, empresa_id) REFERENCES aplicacion_fitosanitaria(id, empresa_id) ON DELETE CASCADE,
  FOREIGN KEY (cama_id, empresa_id) REFERENCES cama(id, empresa_id),
  CHECK (hasta_m IS NULL OR hasta_m >= desde_m)
);

-- -----------------------------------------------------------------------------
-- 11. Notificaciones, exportes, integraciones, consumo, auditoría y sync
-- -----------------------------------------------------------------------------
CREATE TABLE notificacion (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id       uuid NOT NULL REFERENCES empresa(id),
  usuario_id       uuid NOT NULL REFERENCES usuario(id),
  canal            text NOT NULL CHECK (canal IN ('en_app','push','whatsapp','sms','email','local_borde')),
  plantilla        text NOT NULL,
  referencia_tipo  text NOT NULL,
  referencia_id    uuid NOT NULL,
  estado           text NOT NULL DEFAULT 'en_cola' CHECK (estado IN ('en_cola','enviada','entregada','leida','fallida')),
  creada_en        timestamptz NOT NULL DEFAULT now(),
  enviada_en       timestamptz,
  error            text
);

CREATE TABLE exporte (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id    uuid NOT NULL REFERENCES empresa(id),
  finca_id      uuid,
  tipo          text NOT NULL CHECK (tipo IN ('ica_monitoreo_plagas','ica_aplicaciones','ica_visitas_asistente',
                  'ica_informe_trimestral','bpa_aplicaciones','globalgap_ppp','geojson_camas',
                  'geojson_incidencias','csv_lecturas','isoxml_prescripcion','paquete_auditoria',
                  'dataset_entrenamiento','exporte_total_cliente')),
  formato       text NOT NULL CHECK (formato IN ('csv','xlsx','pdf','geojson','zip','xml','json')),
  desde         date,
  hasta         date,
  uri           text,
  sha256        char(64),
  generado_por  uuid REFERENCES usuario(id),
  generado_en   timestamptz NOT NULL DEFAULT now(),
  parametros    jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE integracion (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id   uuid NOT NULL REFERENCES empresa(id),
  tipo         text NOT NULL CHECK (tipo IN ('webhook','farmos','metos_fieldclimate','open_meteo',
                                             'erp_generico','sftp','sensorthings')),
  config       jsonb NOT NULL DEFAULT '{}'::jsonb,   -- URL, eventos suscritos, mapeo de campos
  secreto_ref  text,                                 -- referencia al gestor de secretos; nunca el secreto
  activo       boolean NOT NULL DEFAULT true,
  creado_por   uuid REFERENCES usuario(id),
  creado_en    timestamptz NOT NULL DEFAULT now()
);

-- Medición de uso para cobrar por plan (ha monitoreadas, horas de robot...).
CREATE TABLE consumo (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id  uuid NOT NULL REFERENCES empresa(id),
  finca_id    uuid,                     -- NULL = total de la empresa
  periodo     date NOT NULL,            -- primer día del mes
  metrica     text NOT NULL CHECK (metrica IN ('ha_monitoreadas','m_cama_inspeccionados','horas_robot',
                                              'dispositivos_activos','incidencias','gb_imagenes')),
  valor       numeric NOT NULL,
  UNIQUE NULLS NOT DISTINCT (empresa_id, periodo, metrica, finca_id)
);

CREATE TABLE auditoria (
  id                    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  empresa_id            uuid,
  actor_usuario_id      uuid,
  actor_dispositivo_id  uuid,
  accion                text NOT NULL,     -- 'leer','crear','actualizar','exportar','concesion_soporte',...
  objeto_tipo           text NOT NULL,
  objeto_id             text,
  ip                    inet,
  detalle               jsonb,
  ocurrido_en           timestamptz NOT NULL DEFAULT now()
);

-- Registro de cambios para la sincronización "pull": cada cliente pide
-- "dame lo de mi empresa con seq > mi cursor".
CREATE TABLE registro_cambios (
  seq         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  empresa_id  uuid NOT NULL,
  finca_id    uuid,
  tabla       text NOT NULL,
  fila_id     uuid NOT NULL,
  operacion   text NOT NULL CHECK (operacion IN ('insert','update','delete')),
  version     integer,
  cambiado_en timestamptz NOT NULL DEFAULT now()
);

-- Lotes de sincronización "push" ya procesados: reintentar el mismo lote no
-- duplica nada (idempotencia por id de lote).
CREATE TABLE sync_lote (
  id              uuid PRIMARY KEY,          -- lo genera el dispositivo
  empresa_id      uuid NOT NULL REFERENCES empresa(id),
  origen          text NOT NULL,             -- 'nodo_borde:<serial>' | 'app:<instalación>'
  operaciones_n   integer NOT NULL,
  resultado       jsonb,                     -- aceptadas, conflictos, rechazadas
  recibido_en     timestamptz NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- 12. Índices
-- -----------------------------------------------------------------------------
CREATE INDEX finca_empresa_idx            ON finca (empresa_id);
CREATE INDEX bloque_finca_idx             ON bloque (empresa_id, finca_id);
CREATE INDEX cama_bloque_idx              ON cama (empresa_id, bloque_id);
CREATE INDEX incidencia_abiertas_idx      ON incidencia (empresa_id, finca_id, estado, detectada_en DESC)
  WHERE estado NOT IN ('cerrada','descartada','duplicada');
CREATE INDEX incidencia_cama_idx          ON incidencia (cama_id, detectada_en DESC);
CREATE INDEX incidencia_problema_idx      ON incidencia (empresa_id, problema_codigo, detectada_en DESC);
CREATE INDEX incidencia_evento_inc_idx    ON incidencia_evento (incidencia_id, ocurrido_en);
CREATE INDEX evidencia_inc_idx            ON evidencia (incidencia_id);
CREATE INDEX riesgo_bloque_fecha_idx      ON riesgo_calculado (empresa_id, bloque_id, fecha DESC);
CREATE INDEX recorrido_finca_idx          ON recorrido (empresa_id, finca_id, inicio DESC);
CREATE INDEX lectura_empresa_idx          ON lectura_ambiental (empresa_id, medido_en DESC);
CREATE INDEX registro_cambios_empresa_idx ON registro_cambios (empresa_id, seq);
CREATE INDEX tarea_asignada_idx           ON tarea (asignada_a, estado);
-- Índices espaciales (GiST de PostGIS)
CREATE INDEX finca_limite_gix   ON finca USING gist (limite);
CREATE INDEX bloque_geom_gix    ON bloque USING gist (geom);
CREATE INDEX cama_eje_gix       ON cama USING gist (eje);
CREATE INDEX incidencia_pto_gix ON incidencia USING gist (punto);

-- -----------------------------------------------------------------------------
-- 13. Disparadores
-- -----------------------------------------------------------------------------
-- 13.1 Versión y fecha de actualización (concurrencia optimista:
--      UPDATE ... WHERE id = $1 AND version = $2)
CREATE OR REPLACE FUNCTION tg_version() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.version := OLD.version + 1;
  IF to_jsonb(NEW) ? 'actualizada_en' THEN NEW := jsonb_populate_record(NEW, jsonb_build_object('actualizada_en', now())); END IF;
  IF to_jsonb(NEW) ? 'actualizado_en' THEN NEW := jsonb_populate_record(NEW, jsonb_build_object('actualizado_en', now())); END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER incidencia_version BEFORE UPDATE ON incidencia FOR EACH ROW EXECUTE FUNCTION tg_version();
CREATE TRIGGER recorrido_version  BEFORE UPDATE ON recorrido  FOR EACH ROW EXECUTE FUNCTION tg_version();
CREATE TRIGGER tarea_version      BEFORE UPDATE ON tarea      FOR EACH ROW EXECUTE FUNCTION tg_version();
CREATE TRIGGER aplicacion_version BEFORE UPDATE ON aplicacion_fitosanitaria FOR EACH ROW EXECUTE FUNCTION tg_version();

-- 13.2 Máquina de estados de la incidencia (las transiciones son datos)
CREATE OR REPLACE FUNCTION tg_incidencia_transicion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.estado IS DISTINCT FROM OLD.estado
     AND NOT EXISTS (SELECT 1 FROM transicion_estado t WHERE t.desde = OLD.estado AND t.hasta = NEW.estado) THEN
    RAISE EXCEPTION 'Transición no permitida: % -> %', OLD.estado, NEW.estado
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER incidencia_transicion BEFORE UPDATE OF estado ON incidencia
  FOR EACH ROW EXECUTE FUNCTION tg_incidencia_transicion();

-- 13.3 Tablas de solo inserción (historial y auditoría)
CREATE OR REPLACE FUNCTION tg_solo_insercion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'La tabla % es de solo inserción', TG_TABLE_NAME USING ERRCODE = 'insufficient_privilege';
END $$;

CREATE TRIGGER incidencia_evento_inmutable BEFORE UPDATE OR DELETE ON incidencia_evento
  FOR EACH ROW EXECUTE FUNCTION tg_solo_insercion();
CREATE TRIGGER auditoria_inmutable BEFORE UPDATE OR DELETE ON auditoria
  FOR EACH ROW EXECUTE FUNCTION tg_solo_insercion();

-- 13.4 Registro de cambios para la sincronización
CREATE OR REPLACE FUNCTION tg_registrar_cambio() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r jsonb;
BEGIN
  r := CASE WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD) ELSE to_jsonb(NEW) END;
  INSERT INTO registro_cambios (empresa_id, finca_id, tabla, fila_id, operacion, version)
  VALUES ((r->>'empresa_id')::uuid, (r->>'finca_id')::uuid, TG_TABLE_NAME, (r->>'id')::uuid,
          lower(TG_OP), (r->>'version')::int);
  RETURN NULL;
END $$;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['finca','bloque','cama','incidencia','incidencia_evento','evidencia',
                           'recorrido','tarea','recomendacion','aplicacion_fitosanitaria','riesgo_calculado']
  LOOP
    EXECUTE format('CREATE TRIGGER %I AFTER INSERT OR UPDATE OR DELETE ON %I
                    FOR EACH ROW EXECUTE FUNCTION tg_registrar_cambio()', t || '_cambios', t);
  END LOOP;
END $$;

-- 13.5 Longitud de la cama calculada desde su eje (PostGIS, en metros)
CREATE OR REPLACE FUNCTION tg_cama_longitud() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.eje IS NOT NULL AND NEW.longitud_m IS NULL THEN
    NEW.longitud_m := round(ST_Length(NEW.eje::geography)::numeric, 2);
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER cama_longitud BEFORE INSERT OR UPDATE OF eje ON cama
  FOR EACH ROW EXECUTE FUNCTION tg_cama_longitud();

-- -----------------------------------------------------------------------------
-- 14. Row Level Security
-- -----------------------------------------------------------------------------
DO $$
DECLARE t text;
BEGIN
  -- Tablas con empresa_id obligatorio
  FOREACH t IN ARRAY ARRAY['finca','bloque','cama','planta','asignacion_dispositivo','datastream',
                           'lectura_ambiental','riesgo_calculado','recorrido','recorrido_cama',
                           'incidencia','incidencia_evento','evidencia','producto_fitosanitario',
                           'recomendacion','recomendacion_incidencia','tarea','aplicacion_fitosanitaria',
                           'aplicacion_cama','notificacion','exporte','integracion','consumo',
                           'registro_cambios','sync_lote','membresia','concesion_soporte',
                           'auditoria']   -- [verificacion-tecnica] auditoria no tenía RLS: B leía la de A
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY aislamiento_empresa ON %I TO bgi_app
                    USING (empresa_id = ANY (app_empresas()))
                    WITH CHECK (empresa_id = ANY (app_empresas()))', t);
  END LOOP;

  -- Alcance por finca (restrictiva: se suma con AND a la anterior)
  FOREACH t IN ARRAY ARRAY['finca','bloque','cama','planta','datastream','riesgo_calculado','recorrido',
                           'incidencia','recomendacion','tarea','aplicacion_fitosanitaria']
  LOOP
    EXECUTE format('CREATE POLICY alcance_finca ON %I AS RESTRICTIVE TO bgi_app
                    USING (app_fincas() IS NULL OR %s = ANY (app_fincas()))',
                   t, CASE WHEN t = 'finca' THEN 'id' ELSE 'finca_id' END);
  END LOOP;
END $$;

-- [verificacion-tecnica] Alcance por finca también en las tablas hijas sin finca_id.
-- Antes, un usuario limitado a la finca X veía eventos, fotos (evidencia) y camas
-- recorridas de las otras fincas de la misma empresa.
CREATE POLICY alcance_finca ON incidencia_evento AS RESTRICTIVE TO bgi_app
  USING (app_fincas() IS NULL OR EXISTS (SELECT 1 FROM incidencia i
         WHERE i.id = incidencia_evento.incidencia_id AND i.finca_id = ANY (app_fincas())));
CREATE POLICY alcance_finca ON evidencia AS RESTRICTIVE TO bgi_app
  USING (app_fincas() IS NULL OR EXISTS (SELECT 1 FROM incidencia i
         WHERE i.id = evidencia.incidencia_id AND i.finca_id = ANY (app_fincas())));
CREATE POLICY alcance_finca ON recorrido_cama AS RESTRICTIVE TO bgi_app
  USING (app_fincas() IS NULL OR EXISTS (SELECT 1 FROM recorrido r
         WHERE r.id = recorrido_cama.recorrido_id AND r.finca_id = ANY (app_fincas())));
CREATE POLICY alcance_finca ON registro_cambios AS RESTRICTIVE TO bgi_app
  USING (app_fincas() IS NULL OR finca_id IS NULL OR finca_id = ANY (app_fincas()));

-- La empresa: solo las propias.
ALTER TABLE empresa ENABLE ROW LEVEL SECURITY;
ALTER TABLE empresa FORCE ROW LEVEL SECURITY;
CREATE POLICY empresa_propia ON empresa TO bgi_app USING (id = ANY (app_empresas()));

-- Usuarios: uno mismo y quienes comparten empresa.
ALTER TABLE usuario ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuario FORCE ROW LEVEL SECURITY;
-- [verificacion-tecnica] Lectura y escritura separadas. Antes la política valía
-- para ALL: la empresa B podía renombrar al agrónomo que comparte con A, y ese
-- nombre sale en el registro ICA de A. Ahora cada persona edita solo su ficha;
-- altas y cambios de terceros los hace el servicio de onboarding (bgi_admin).
CREATE POLICY usuario_visible ON usuario FOR SELECT TO bgi_app USING (
  id = app_usuario()
  OR EXISTS (SELECT 1 FROM membresia m WHERE m.usuario_id = usuario.id AND m.empresa_id = ANY (app_empresas()))
);
CREATE POLICY usuario_propio ON usuario FOR UPDATE TO bgi_app
  USING (id = app_usuario()) WITH CHECK (id = app_usuario());

-- Catálogos: globales visibles para todos; los propios, solo para su empresa.
-- [verificacion-tecnica] Antes una sola política FOR ALL con USING que incluía
-- las filas globales: B podía hacer UPDATE ... SET empresa_id = B sobre una fila
-- global (la "secuestraba" y desaparecía para A) o borrarla. Ahora las filas
-- globales son de solo lectura para bgi_app.
ALTER TABLE problema_sanitario ENABLE ROW LEVEL SECURITY;
ALTER TABLE problema_sanitario FORCE ROW LEVEL SECURITY;
CREATE POLICY problema_visible ON problema_sanitario FOR SELECT TO bgi_app
  USING (empresa_id IS NULL OR empresa_id = ANY (app_empresas()));
CREATE POLICY problema_propio_ins ON problema_sanitario FOR INSERT TO bgi_app
  WITH CHECK (empresa_id = ANY (app_empresas()));
CREATE POLICY problema_propio_upd ON problema_sanitario FOR UPDATE TO bgi_app
  USING (empresa_id = ANY (app_empresas())) WITH CHECK (empresa_id = ANY (app_empresas()));
CREATE POLICY problema_propio_del ON problema_sanitario FOR DELETE TO bgi_app
  USING (empresa_id = ANY (app_empresas()));

ALTER TABLE modelo_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE modelo_version FORCE ROW LEVEL SECURITY;
CREATE POLICY modelo_visible ON modelo_version FOR SELECT TO bgi_app
  USING (empresa_id IS NULL OR empresa_id = ANY (app_empresas()));
CREATE POLICY modelo_propio_ins ON modelo_version FOR INSERT TO bgi_app
  WITH CHECK (empresa_id = ANY (app_empresas()));
CREATE POLICY modelo_propio_upd ON modelo_version FOR UPDATE TO bgi_app
  USING (empresa_id = ANY (app_empresas())) WITH CHECK (empresa_id = ANY (app_empresas()));
CREATE POLICY modelo_propio_del ON modelo_version FOR DELETE TO bgi_app
  USING (empresa_id = ANY (app_empresas()));

-- Dispositivos: los de la empresa, y los del proveedor mientras estén asignados a ella.
-- [verificacion-tecnica] La visibilidad del robot prestado es solo de LECTURA.
-- Antes la política era FOR ALL: el cliente que tenía el robot prestado podía
-- cambiarle el dueño (empresa_id) y la huella del certificado mTLS.
ALTER TABLE dispositivo ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispositivo FORCE ROW LEVEL SECURITY;
CREATE POLICY dispositivo_visible ON dispositivo FOR SELECT TO bgi_app USING (
  empresa_id = ANY (app_empresas())
  OR EXISTS (SELECT 1 FROM asignacion_dispositivo a
             WHERE a.dispositivo_id = dispositivo.id
               AND a.empresa_id = ANY (app_empresas())
               AND a.vigencia @> now())
);
CREATE POLICY dispositivo_propio_ins ON dispositivo FOR INSERT TO bgi_app
  WITH CHECK (empresa_id = ANY (app_empresas()));
CREATE POLICY dispositivo_propio_upd ON dispositivo FOR UPDATE TO bgi_app
  USING (empresa_id = ANY (app_empresas())) WITH CHECK (empresa_id = ANY (app_empresas()));
CREATE POLICY dispositivo_propio_del ON dispositivo FOR DELETE TO bgi_app
  USING (empresa_id = ANY (app_empresas()));
-- Telemetría: el cliente ve la de los dispositivos que puede ver.
ALTER TABLE telemetria_dispositivo ENABLE ROW LEVEL SECURITY;
ALTER TABLE telemetria_dispositivo FORCE ROW LEVEL SECURITY;
CREATE POLICY telemetria_visible ON telemetria_dispositivo TO bgi_app
  USING (EXISTS (SELECT 1 FROM dispositivo d WHERE d.id = telemetria_dispositivo.dispositivo_id));
-- Consola de flota del vendedor: todos los dispositivos y su telemetría...
CREATE POLICY flota_ve_dispositivos ON dispositivo TO bgi_flota USING (true);
CREATE POLICY flota_ve_asignaciones ON asignacion_dispositivo TO bgi_flota USING (true);
CREATE POLICY flota_ve_telemetria ON telemetria_dispositivo TO bgi_flota USING (true) WITH CHECK (true);
-- ...pero ningún permiso sobre incidencias, lecturas ni evidencias (ver GRANT abajo).

-- -----------------------------------------------------------------------------
-- 15. Permisos
-- -----------------------------------------------------------------------------
GRANT USAGE ON SCHEMA bgi TO bgi_app, bgi_flota, bgi_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA bgi TO bgi_app;
REVOKE UPDATE, DELETE ON incidencia_evento, auditoria, registro_cambios, sync_lote FROM bgi_app;
REVOKE INSERT, UPDATE, DELETE ON especie, especie_problema, transicion_estado, personal_proveedor FROM bgi_app;
-- La app solo usa la tabla padre de lecturas; las particiones no se tocan directo.
REVOKE ALL ON lectura_ambiental_2026_10, lectura_ambiental_2026_11, lectura_ambiental_2026_12,
              lectura_ambiental_defecto FROM bgi_app;
GRANT SELECT ON dispositivo, asignacion_dispositivo, telemetria_dispositivo TO bgi_flota;
GRANT INSERT ON telemetria_dispositivo TO bgi_flota;
GRANT ALL ON ALL TABLES IN SCHEMA bgi TO bgi_admin;

-- -----------------------------------------------------------------------------
-- 16. Vistas para exportes regulatorios y mapas (respetan RLS: security_invoker)
-- -----------------------------------------------------------------------------
-- 16.1 Registro de monitoreo de plagas. Res. ICA 824/2022, Manual §8.2.4:
--      fecha de monitoreo, cultivo, lote, plaga monitoreada, resultado
--      cuantitativo y nombre de quien realiza la actividad. Incluye los
--      monitoreos con resultado 0 (también son registro).
CREATE VIEW v_ica_monitoreo_plagas WITH (security_invoker = true) AS
SELECT r.empresa_id,
       f.nombre                                   AS lugar_produccion,
       f.codigo_ica_lugar_produccion,
       (r.inicio AT TIME ZONE f.zona_horaria)::date AS fecha_monitoreo,
       e.nombre_comun                             AS cultivo,
       b.codigo                                   AS lote,
       ps.nombre                                  AS plaga_monitoreada,
       count(DISTINCT rc.cama_id)                 AS camas_inspeccionadas,
       count(DISTINCT i.cama_id) FILTER (WHERE i.verificacion_resultado = 'confirmada') AS camas_con_hallazgo_confirmado,
       round(100.0 * count(DISTINCT i.cama_id) FILTER (WHERE i.verificacion_resultado = 'confirmada')
             / NULLIF(count(DISTINCT rc.cama_id), 0), 1) AS incidencia_camas_pct,
       count(DISTINCT i.id) FILTER (WHERE i.estado IN ('detectada','en_triage','verificacion_asignada'))
                                                  AS alertas_sin_verificar,
       u.nombre                                   AS responsable_monitoreo,
       r.tipo                                     AS metodo,
       mv.nombre || ' ' || mv.version             AS modelo_clasificador,
       r.id                                       AS recorrido_id
FROM recorrido r
JOIN finca f            ON f.id = r.finca_id
JOIN recorrido_cama rc  ON rc.recorrido_id = r.id AND rc.estado = 'inspeccionada'
JOIN cama c             ON c.id = rc.cama_id
JOIN bloque b           ON b.id = c.bloque_id
JOIN especie e          ON e.codigo = b.especie_codigo
JOIN especie_problema ep ON ep.especie_codigo = b.especie_codigo AND ep.monitoreo_obligatorio
JOIN problema_sanitario ps ON ps.codigo = ep.problema_codigo
LEFT JOIN incidencia i  ON i.recorrido_id = r.id AND i.cama_id = rc.cama_id
                       AND COALESCE(i.problema_confirmado_codigo, i.problema_codigo) = ps.codigo
LEFT JOIN usuario u     ON u.id = r.responsable_id
LEFT JOIN modelo_version mv ON mv.id = r.modelo_version_id
WHERE r.estado = 'completado'
GROUP BY r.empresa_id, f.nombre, f.codigo_ica_lugar_produccion, r.inicio, f.zona_horaria,
         e.nombre_comun, b.codigo, ps.nombre, u.nombre, r.tipo, mv.nombre, mv.version, r.id;

-- 16.2 Registro de aplicación de plaguicidas. Res. ICA 824/2022, Manual §8.2.7
--      (+ lote y registro ICA del producto, que pide la Res. 30021/2017 BPA).
CREATE VIEW v_ica_aplicaciones WITH (security_invoker = true) AS
SELECT a.empresa_id,
       f.nombre                       AS lugar_produccion,
       f.codigo_ica_lugar_produccion,
       e.nombre_comun                 AS cultivo,
       b.codigo                       AS lote,
       ps.nombre                      AS blanco_biologico,
       p.nombre_comercial,
       p.ingrediente_activo,
       p.registro_ica                 AS registro_ica_producto,
       a.lote_producto,
       (a.inicio AT TIME ZONE f.zona_horaria)::date AS fecha_aplicacion,
       a.dosis_aplicada,
       a.dosis_unidad,
       a.metodo_aplicacion,
       a.periodo_carencia_dias,
       a.periodo_reentrada_horas,
       ua.nombre                      AS responsable_aplicacion,
       ur.nombre                      AS quien_recomendo,
       (a.firma_aplicador IS NOT NULL) AS firmado,
       (SELECT count(*) FROM aplicacion_cama ac WHERE ac.aplicacion_id = a.id) AS camas_tratadas
FROM aplicacion_fitosanitaria a
JOIN finca f               ON f.id = a.finca_id
JOIN bloque b              ON b.id = a.bloque_id
JOIN especie e             ON e.codigo = b.especie_codigo
JOIN producto_fitosanitario p ON p.id = a.producto_id
JOIN problema_sanitario ps ON ps.codigo = a.blanco_biologico_codigo
JOIN usuario ua            ON ua.id = a.aplicado_por
LEFT JOIN usuario ur       ON ur.id = a.recomendado_por;

-- 16.3 Mapa de calor por cama como GeoJSON (RFC 7946): FeatureCollection con
--      el riesgo más alto del día y las incidencias abiertas de cada cama.
CREATE OR REPLACE FUNCTION geojson_camas(p_bloque uuid, p_fecha date DEFAULT current_date)
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER AS $$
  SELECT jsonb_build_object(
    'type', 'FeatureCollection',
    'features', COALESCE(jsonb_agg(jsonb_build_object(
      'type', 'Feature',
      'id', c.id,
      'geometry', ST_AsGeoJSON(c.eje)::jsonb,
      'properties', jsonb_build_object(
        'bloque', b.codigo,
        'cama', c.numero,
        'longitud_m', c.longitud_m,
        'riesgo_nivel', rk.nivel,
        'riesgo_problema', rk.problema_codigo,
        'incidencias_abiertas', (SELECT count(*) FROM incidencia i
                                 WHERE i.cama_id = c.id
                                   AND i.estado NOT IN ('cerrada','descartada','duplicada')))
    ) ORDER BY c.numero), '[]'::jsonb))
  FROM cama c
  JOIN bloque b ON b.id = c.bloque_id
  LEFT JOIN LATERAL (
    SELECT r.nivel, r.problema_codigo
    FROM riesgo_calculado r
    WHERE r.bloque_id = c.bloque_id AND (r.cama_id = c.id OR r.cama_id IS NULL) AND r.fecha = p_fecha
    ORDER BY array_position(ARRAY['muy_alto','alto','medio','bajo'], r.nivel)
    LIMIT 1) rk ON true
  WHERE c.bloque_id = p_bloque AND c.activo
$$;

GRANT SELECT ON v_ica_monitoreo_plagas, v_ica_aplicaciones TO bgi_app;

-- -----------------------------------------------------------------------------
-- 17. Datos de referencia
-- -----------------------------------------------------------------------------
INSERT INTO transicion_estado (desde, hasta) VALUES
  ('detectada','en_triage'), ('detectada','verificacion_asignada'), ('detectada','descartada'),
  ('detectada','duplicada'),
  ('en_triage','verificacion_asignada'), ('en_triage','tratamiento_recomendado'),
  ('en_triage','en_seguimiento'), ('en_triage','descartada'), ('en_triage','duplicada'),
  ('verificacion_asignada','confirmada'), ('verificacion_asignada','descartada'),
  ('verificacion_asignada','en_triage'),                 -- no concluyente: vuelve al agrónomo
  ('confirmada','tratamiento_recomendado'), ('confirmada','en_seguimiento'), ('confirmada','cerrada'),
  ('tratamiento_recomendado','tratada'), ('tratamiento_recomendado','en_triage'),
  ('tratada','en_seguimiento'), ('tratada','cerrada'),
  ('en_seguimiento','cerrada'), ('en_seguimiento','tratamiento_recomendado'), ('en_seguimiento','confirmada'),
  ('descartada','en_triage'), ('cerrada','en_triage');    -- reabrir

-- Especies (códigos EPPO verificados en https://gd.eppo.int/taxon/<código>).
-- ciclo_ica: clasificación de la Res. ICA 824/2022, art. 3.3-3.5. La uchuva la
-- nombra la norma como ciclo corto; la del arándano y la fresa es SUPUESTO.
INSERT INTO especie (codigo, nombre_comun, nombre_cientifico, eppo_code, ciclo_ica, unidad_lineal) VALUES
  ('arandano', 'Arándano', 'Vaccinium corymbosum', 'VACCO', 'largo', 'cama'),
  ('fresa',    'Fresa',    'Fragaria x ananassa',  'FRAAN', 'corto', 'cama'),
  ('uchuva',   'Uchuva',   'Physalis peruviana',   'PHYPE', 'corto', 'hilera');

-- Problemas sanitarios. eppo_code solo cuando el agente es el nombrado; el
-- agente real en cada finca se confirma con laboratorio.
INSERT INTO problema_sanitario (codigo, nombre, tipo, agente_cientifico, eppo_code) VALUES
  ('oidio',       'Oídio',                 'enfermedad', 'Erysiphe vaccinii (u otro; confirmar)', NULL),  -- MCRSVA si se confirma E. vaccinii
  ('alternaria',  'Mancha por Alternaria', 'enfermedad', 'Alternaria spp.', NULL),
  ('heliothis',   'Daño por Heliothis',    'plaga',      'Heliothinae (clase "Heliothis" de DrBerry; especie sin confirmar)', NULL),
  ('antracnosis', 'Antracnosis',           'enfermedad', 'Colletotrichum acutatum s.l.', 'COLLAC'),
  ('botrytis',    'Moho gris (Botrytis)',  'enfermedad', 'Botrytis cinerea', 'BOTRCI'),
  ('roya',        'Roya del arándano',     'enfermedad', 'Pucciniastrum minimum (syn. Thekopsora minima)', 'THEKMI'),
  ('desconocido', 'Síntoma no clasificado','desconocido', NULL, NULL);

INSERT INTO especie_problema (especie_codigo, problema_codigo) VALUES
  ('arandano','oidio'), ('arandano','alternaria'), ('arandano','heliothis'),
  ('arandano','antracnosis'), ('arandano','botrytis'), ('arandano','roya'),
  ('fresa','botrytis'), ('fresa','oidio');

-- Modelos globales. Parámetros de la demo: ver datos/riesgo y el prompt de
-- simulación; los que no tienen fuente van marcados SUPUESTO.
INSERT INTO modelo_version (id, tipo, nombre, version, especie_codigo, problema_codigo, parametros, referencia, licencia, estado, clases) VALUES
  ('00000000-0000-4000-8000-0000000000a1', 'riesgo', 'antracnosis_wilson1990_arandano', 'demo-0.1', 'arandano', 'antracnosis',
   '{"nota":"envolvente max(Wilson 1990, aproximación Gillett y Schilder 2009) de datos/riesgo/risk.py. [verificacion-tecnica] Antes decia Miles 2013, que NO esta implementado: sus coeficientes no se obtuvieron"}',
   'Wilson, Madden y Ellis 1990, Phytopathology 80:111 (fruto de fresa) + Gillett y Schilder 2009, Acta Hortic. 810:355 (arandano)', NULL, 'experimental', NULL),
  ('00000000-0000-4000-8000-0000000000a2', 'riesgo', 'botrytis_bulger1987', 'demo-0.1', 'arandano', 'botrytis',
   '{"nota":"modelo de fresa usado como aproximación en arándano"}',
   'Bulger, Ellis y Madden 1987, Phytopathology 77:1225', NULL, 'experimental', NULL),
  ('00000000-0000-4000-8000-0000000000a3', 'riesgo', 'roya_regla', 'demo-0.1', 'arandano', 'roya',
   '{"nota":"19-25 °C con mojadura prolongada (regla empírica, SUPUESTO)"}',
   'Regla empírica del equipo', NULL, 'experimental', NULL),
  ('00000000-0000-4000-8000-0000000000c1', 'clasificador', 'clasificador_hoja_arandano', 'demo-0.1', 'arandano', NULL,
   '{"umbral":0.5,"nota":"umbral PROVISIONAL; favorece sensibilidad"}',
   'Entrenado con DrBerry (Roboflow Universe, CC BY 4.0)', 'AGPL-3.0 (Ultralytics); revisar antes de vender', 'experimental',
   ARRAY['alternaria','heliothis','oidio','sana']);

COMMIT;

-- =============================================================================
-- 18. Semillas de demostración (OPCIONAL). Dos empresas FICTICIAS para mostrar
--     el aislamiento. Coordenadas inventadas cerca de Chía (solo ejemplo de
--     la Sabana; el modelo no depende de la región).
--     Ejecutar con un rol que salte RLS (superusuario o bgi_admin): con FORCE
--     ROW LEVEL SECURITY, ni el dueño de las tablas inserta sin política.
-- =============================================================================
BEGIN;
SET search_path = bgi, public;

INSERT INTO empresa (id, nombre, nit, plan) VALUES
  ('11111111-1111-4111-8111-111111111111', 'Agrícola Demo Sabana S.A.S. (ficticia)', '900000001', 'monitoreo_robot'),
  ('22222222-2222-4222-8222-222222222222', 'Frutales Demo Boyacá S.A.S. (ficticia)', '900000002', 'monitoreo');

INSERT INTO usuario (id, nombre, email) VALUES
  ('aaaaaaaa-0000-4000-8000-000000000001', 'Productora Demo',  'productora@demo.invalid'),
  ('aaaaaaaa-0000-4000-8000-000000000002', 'Agrónomo Demo',    'agronomo@demo.invalid'),
  ('aaaaaaaa-0000-4000-8000-000000000003', 'Operario Demo',    'operario@demo.invalid'),
  ('aaaaaaaa-0000-4000-8000-000000000004', 'Técnico Proveedor','tecnico@demo.invalid'),
  ('aaaaaaaa-0000-4000-8000-000000000005', 'Productor B Demo', 'productorb@demo.invalid');

-- El mismo agrónomo asesora a las dos empresas (caso real de un asistente técnico).
INSERT INTO membresia (empresa_id, usuario_id, rol, es_asistente_tecnico_ica) VALUES
  ('11111111-1111-4111-8111-111111111111', 'aaaaaaaa-0000-4000-8000-000000000001', 'productor', false),
  ('11111111-1111-4111-8111-111111111111', 'aaaaaaaa-0000-4000-8000-000000000002', 'agronomo',  true),
  ('11111111-1111-4111-8111-111111111111', 'aaaaaaaa-0000-4000-8000-000000000003', 'operario',  false),
  ('22222222-2222-4222-8222-222222222222', 'aaaaaaaa-0000-4000-8000-000000000005', 'productor', false),
  ('22222222-2222-4222-8222-222222222222', 'aaaaaaaa-0000-4000-8000-000000000002', 'agronomo',  true);

INSERT INTO personal_proveedor (usuario_id, rol_proveedor) VALUES
  ('aaaaaaaa-0000-4000-8000-000000000004', 'tecnico_campo');

INSERT INTO finca (id, empresa_id, nombre, municipio, departamento, conectividad, region_perfil) VALUES
  ('f1000000-0000-4000-8000-000000000001', '11111111-1111-4111-8111-111111111111', 'Finca Demo A', 'Chía', 'Cundinamarca', 'celular', 'sabana_bogota'),
  ('f2000000-0000-4000-8000-000000000001', '22222222-2222-4222-8222-222222222222', 'Finca Demo B', NULL, 'Boyacá', 'ninguna', NULL);

INSERT INTO bloque (id, empresa_id, finca_id, codigo, especie_codigo, perfil_cultivo, variedad, sistema_cultivo, cubierta, area_ha) VALUES
  ('b1000000-0000-4000-8000-000000000001', '11111111-1111-4111-8111-111111111111', 'f1000000-0000-4000-8000-000000000001',
   'B03', 'arandano', 'arandano@0.1.0', 'por definir', 'maceta', 'macrotunel', 0.5),
  ('b2000000-0000-4000-8000-000000000001', '22222222-2222-4222-8222-222222222222', 'f2000000-0000-4000-8000-000000000001',
   'L01', 'fresa', 'fresa@0.1.0', 'por definir', 'suelo', 'macrotunel', 0.3);

-- Ejes de cama: LineString en lon/lat (RFC 7946, §3.1.1). Coordenadas ficticias.
INSERT INTO cama (id, empresa_id, finca_id, bloque_id, numero, eje, ancho_m, marcador_cabecera) VALUES
  ('c1000000-0000-4000-8000-000000000007', '11111111-1111-4111-8111-111111111111', 'f1000000-0000-4000-8000-000000000001',
   'b1000000-0000-4000-8000-000000000001', 7,
   ST_GeomFromText('LINESTRING(-74.06000 4.86000, -74.06000 4.86027)', 4326), 1.0, 'aruco:107'),
  ('c1000000-0000-4000-8000-000000000008', '11111111-1111-4111-8111-111111111111', 'f1000000-0000-4000-8000-000000000001',
   'b1000000-0000-4000-8000-000000000001', 8,
   ST_GeomFromText('LINESTRING(-74.05997 4.86000, -74.05997 4.86027)', 4326), 1.0, 'aruco:108'),
  ('c2000000-0000-4000-8000-000000000001', '22222222-2222-4222-8222-222222222222', 'f2000000-0000-4000-8000-000000000001',
   'b2000000-0000-4000-8000-000000000001', 1,
   ST_GeomFromText('LINESTRING(-73.36000 5.53000, -73.36000 5.53020)', 4326), 0.8, 'qr:L01-C1');

-- Robot del proveedor prestado a la Finca A durante la demo.
INSERT INTO dispositivo (id, empresa_id, propietario, tipo, fabricante, modelo, serial) VALUES
  ('d0000000-0000-4000-8000-000000000001', NULL, 'proveedor', 'robot', 'AgiBot', 'D1 EDU (prototipo)', 'DEMO-D1-0001');
INSERT INTO asignacion_dispositivo (dispositivo_id, empresa_id, finca_id, vigencia) VALUES
  ('d0000000-0000-4000-8000-000000000001', '11111111-1111-4111-8111-111111111111', 'f1000000-0000-4000-8000-000000000001',
   tstzrange('2026-10-01', '2026-12-31'));

INSERT INTO recorrido (id, empresa_id, finca_id, tipo, dispositivo_id, responsable_id, motivo, estado,
                       inicio, fin, hoja_seca, camara, modelo_version_id) VALUES
  ('e0000000-0000-4000-8000-000000000001', '11111111-1111-4111-8111-111111111111', 'f1000000-0000-4000-8000-000000000001',
   'robot', 'd0000000-0000-4000-8000-000000000001', 'aaaaaaaa-0000-4000-8000-000000000003', 'riesgo_alto', 'completado',
   '2026-10-24 06:10-05', '2026-10-24 06:40-05', true, 'mastil', '00000000-0000-4000-8000-0000000000c1');

INSERT INTO recorrido_cama (recorrido_id, empresa_id, cama_id, orden, prioridad, estado, cobertura_pct, cuadros_n, hallazgos_n) VALUES
  ('e0000000-0000-4000-8000-000000000001', '11111111-1111-4111-8111-111111111111', 'c1000000-0000-4000-8000-000000000007', 1, 0.82, 'inspeccionada', 96.0, 120, 1),
  ('e0000000-0000-4000-8000-000000000001', '11111111-1111-4111-8111-111111111111', 'c1000000-0000-4000-8000-000000000008', 2, 0.40, 'inspeccionada', 94.5, 118, 0);

INSERT INTO incidencia (id, empresa_id, finca_id, bloque_id, cama_id, codigo_corto, estado, prioridad,
                        posicion_m, lado, altura_dosel, metodo_ubicacion,
                        fuente_tipo, dispositivo_id, recorrido_id,
                        problema_codigo, modelo_version_id, confianza, clases_top, organo,
                        hoja_mojada_captura, contexto_ambiental, detectada_en, creada_en, origen_registro) VALUES
  ('0192f1a0-7c00-7000-8000-000000000042', '11111111-1111-4111-8111-111111111111', 'f1000000-0000-4000-8000-000000000001',
   'b1000000-0000-4000-8000-000000000001', 'c1000000-0000-4000-8000-000000000007', 'B03-C07-0042', 'detectada', 'P1',
   14.5, 'A', 'media', 'marcador_odometria',
   'robot', 'd0000000-0000-4000-8000-000000000001', 'e0000000-0000-4000-8000-000000000001',
   'oidio', '00000000-0000-4000-8000-0000000000c1', 0.810,
   '[{"clase":"oidio","prob":0.81},{"clase":"sana","prob":0.12},{"clase":"alternaria","prob":0.07}]', 'hoja_haz',
   false, '{"temperatura_c":16.2,"humedad_relativa_pct":78,"horas_mojadura_24h":9,"fuente":"nodo_sensor"}',
   '2026-10-24 06:21:13-05', '2026-10-24 06:21:13-05', 'nodo_borde:DEMO-NB-01');

-- Riesgo del día calculado por el nodo de borde para todo el bloque (cama NULL).
INSERT INTO riesgo_calculado (empresa_id, finca_id, bloque_id, cama_id, fecha, problema_codigo, modelo_version_id,
                              valor, nivel, insumos, calculado_en_borde) VALUES
  ('11111111-1111-4111-8111-111111111111', 'f1000000-0000-4000-8000-000000000001', 'b1000000-0000-4000-8000-000000000001',
   NULL, '2026-10-24', 'botrytis', '00000000-0000-4000-8000-0000000000a2', NULL, 'alto',
   '{"horas_mojadura_24h":9,"temperatura_media_c":15.8,"nota":"valores de ejemplo, no medidos"}', true);

INSERT INTO incidencia_evento (empresa_id, incidencia_id, tipo, estado_nuevo, actor_dispositivo_id, ocurrido_en) VALUES
  ('11111111-1111-4111-8111-111111111111', '0192f1a0-7c00-7000-8000-000000000042', 'creada', 'detectada',
   'd0000000-0000-4000-8000-000000000001', '2026-10-24 06:21:13-05');

COMMIT;

-- =============================================================================
-- 19. Cómo usar el aislamiento desde la API (ejemplo)
-- =============================================================================
-- BEGIN;
--   SET LOCAL ROLE bgi_app;
--   SET LOCAL app.empresas = '{11111111-1111-4111-8111-111111111111}';
--   SET LOCAL app.usuario  = 'aaaaaaaa-0000-4000-8000-000000000002';
--   SELECT codigo_corto, estado FROM bgi.incidencia;        -- solo ve la empresa A
--   SELECT * FROM bgi.v_ica_monitoreo_plagas;                -- registro ICA §8.2.4
--   SELECT bgi.geojson_camas('b1000000-0000-4000-8000-000000000001', '2026-10-24');
-- COMMIT;
