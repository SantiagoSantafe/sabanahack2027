"""Convierte modelo_datos.sql en una versión ejecutable sin PostGIS (sustituto mínimo)."""
import re, sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
shim = r"""
CREATE DOMAIN public.geom_shim AS text;
CREATE FUNCTION public.ST_GeomFromText(text, integer) RETURNS public.geom_shim
  LANGUAGE sql IMMUTABLE AS $f$ SELECT $1::public.geom_shim $f$;
CREATE FUNCTION public.ST_AsGeoJSON(public.geom_shim) RETURNS text LANGUAGE sql IMMUTABLE AS $f$
  SELECT CASE WHEN $1 LIKE 'LINESTRING(%' THEN
    '{"type":"LineString","coordinates":[[' ||
    replace(replace(regexp_replace($1, '^LINESTRING\((.*)\)$', '\1'), ', ', '],['), ' ', ',') || ']]}'
  ELSE NULL END $f$;
-- Longitud aproximada (equirectangular) de una línea de 2 puntos, en metros.
CREATE FUNCTION public.ST_Length(public.geom_shim) RETURNS double precision LANGUAGE plpgsql IMMUTABLE AS $f$
DECLARE p text[]; x1 float8; y1 float8; x2 float8; y2 float8;
BEGIN
  p := regexp_split_to_array(regexp_replace($1, '^LINESTRING\((.*)\)$', '\1'), '[ ,]+');
  x1 := p[1]::float8; y1 := p[2]::float8; x2 := p[3]::float8; y2 := p[4]::float8;
  RETURN 6371008.8 * sqrt(power(radians(x2-x1)*cos(radians((y1+y2)/2)),2) + power(radians(y2-y1),2));
END $f$;
"""
s = s.replace("CREATE EXTENSION IF NOT EXISTS postgis;", shim)
s, n1 = re.subn(r"geometry\(\s*\w+\s*,\s*4326\s*\)", "public.geom_shim", s)
s, n2 = re.subn(r"::geography", "", s)
s, n3 = re.subn(r"(_gix\s+ON\s+\w+\s+USING\s+)gist", r"\1btree", s)
open(dst, 'w', encoding='utf-8').write(s)
print(f"geometry->shim: {n1}, ::geography: {n2}, gix->btree: {n3}")
