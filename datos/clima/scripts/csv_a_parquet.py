"""Convierte los CSV de clima/cache (histórico y pronóstico) a Parquet usando polars (del .venv del equipo).
Uso: /Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I csv_a_parquet.py"""
import glob, os
import polars as pl
CACHE = "/Users/santiagosantafe/Downloads/SabanaHack/datos/clima/cache"
out = os.path.join(CACHE, "parquet")
os.makedirs(out, exist_ok=True)
n = 0
for f in sorted(glob.glob(os.path.join(CACHE, "*.csv"))):
    df = pl.read_csv(f, try_parse_dates=False, infer_schema_length=10000)
    if "time" in df.columns:
        df = df.with_columns(pl.col("time").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M"))
    df.write_parquet(os.path.join(out, os.path.basename(f)[:-4] + ".parquet"))
    n += 1
print("parquet escritos:", n, "->", out)
