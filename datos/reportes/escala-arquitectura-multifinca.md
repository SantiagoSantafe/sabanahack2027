# Reporte: escala · arquitectura-multifinca

Fecha: 2026-10-23. Rol: diseñar la arquitectura de software multi-cliente para que la organización venda la solución a muchos productores y a otros frutales. La Sabana de Bogotá es solo el ejemplo de la demo.

## Entregables

| Archivo | Contenido |
|---|---|
| `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/arquitectura.md` | Documento principal con 4 diagramas mermaid (componentes, entidades, estados de la incidencia y flujo de una incidencia con y sin conexión). Incluye la tabla hackathon frente a producción, roles, offline-first, APIs, formatos, ICA/BPA/GLOBALG.A.P., integraciones, seguridad, alternativas y límites |
| `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/modelo_datos.sql` | DDL PostgreSQL 16+/PostGIS: 38 tablas, 4 particiones, 2 vistas de exporte ICA, una función GeoJSON del mapa de calor, RLS, disparadores y semillas con 2 empresas ficticias |
| `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/schema_incidencia.json` | JSON Schema 2020-12 de la incidencia, con reglas condicionales por estado y por fuente |
| `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/pruebas_arquitectura/` | `transformar.py` (sustituto de PostGIS para probar), `pruebas.sql`, `validar.js` y los resultados en `.txt` |

## Qué se probó

- **DDL.** Corrió en un contenedor desechable de PostgreSQL 16.14 (imagen local, sin descargas), que se eliminó al terminar. Pasaron los 11 grupos de pruebas:
  - Aislamiento entre empresas por RLS.
  - Llaves foráneas compuestas que impiden apuntar a una cama de otra empresa.
  - Máquina de estados.
  - Historial inmutable, incluso para el superusuario.
  - Exclusión: un robot no puede estar en dos fincas a la vez.
  - Particiones.
  - Alcance por finca.
  - Consola de flota sin acceso agronómico.
  - GeoJSON del mapa de calor.
  - Agrónomo con dos empresas.
- **JSON Schema.** 20/20 casos con Ajv 8.20 en modo estricto: 3 válidos y 17 inválidos rechazados.
- **Un error encontrado y corregido.** Un `CHECK` con NULL dejaba pasar una incidencia "confirmada" sin verificación. Se corrigió con `COALESCE` (prueba P5c2).

## Hallazgos clave

1. Lo que escala es la plataforma: la incidencia tiene el mismo contrato si viene del robot, del operario con celular, de una cámara en la aspersora o de un sistema externo. Se puede vender a fincas sin robot y a otros cultivos.
2. El aislamiento por cliente lo garantiza la base de datos: RLS con FORCE, llaves compuestas y vistas `security_invoker`. Está probado.
3. La Res. ICA 824/2022 (texto y manual leídos completos) fija los campos del registro de monitoreo de plagas (§8.2.4), de aplicación de plaguicidas (§8.2.7) y de visitas del asistente técnico (§8.2.6). Exige conservarlos al menos 2 años y tener copia si son digitales. El modelo los produce como subproducto (vistas `v_ica_monitoreo_plagas` y `v_ica_aplicaciones`). El registro ICA pide el nombre de una persona, así que el recorrido del robot tiene un responsable humano.
4. Clasificar en la finca es obligatorio. Con los supuestos de capacidad de `operacion/capacidad.csv`, subir todo serían unos 92 GB/día por finca de 20 ha; subir solo los hallazgos, unos 3,5 MB/día por celular.
5. Ley 1581: el productor es Responsable y el vendedor Encargado del tratamiento (art. 3 d y e). Si la nube está fuera del país, aplica el art. 26 (transferencia internacional).
6. El modelo se enlaza con los perfiles de cultivo del rol generalización-cultivos: `bloque.perfil_cultivo` ('arandano@0.1.0'), `finca.region_perfil` y calibración por finca en `modelo_version`.

## Límites y pendientes

- PostGIS real no se ejecutó (en la máquina no había imagen con PostGIS). Las columnas espaciales y los índices GiST quedan NO VERIFICADOS en ejecución.
- Sin API conocida del ICA (NO VERIFICADO). Los puntos de control de GLOBALG.A.P. IFA v6 solo vienen de un resumen de proveedor (NO VERIFICADO).
- La licencia AGPL de ultralytics/YOLO (reporte `preparacion-entorno.md`) obliga a licenciar o cambiar de modelo para vender.
- SUPUESTOS: escala de severidad 0-5, búfer de 30 días en el nodo, tope de 30 días por concesión de soporte, borrado a 90 días tras el contrato, tamaños de imagen.
- Dependen del mentor: conectividad (pregunta 6), roles (12, 15, 17), canal de alerta (18) y falsas alarmas tolerables (28). En el diseño todos son configuración.
- No pude validar el render de los diagramas mermaid: la vista previa externa fue bloqueada por el clasificador de permisos. Revisé la sintaxis a mano.

## Frases para el pitch

- "Vendemos una plataforma, no un perro robot: el mismo registro sirve si el hallazgo lo trae el robot, el celular del operario o la cámara del aspersor, en arándano, fresa o uchuva."
- "Cada productor ve solo lo suyo, y eso lo garantiza la base de datos, no una promesa: lo probamos con dos empresas."
- "El registro de monitoreo que pide el ICA sale solo, con cama, fecha, plaga y responsable, aunque la finca no tenga internet."
