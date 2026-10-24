# Reporte: escala-clima-global

Fecha: 2026-10-23. Rol: clima-global (capa ambiental agnóstica a ubicación y multi-finca).

Entregable principal: `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/clima_global.md`

## Qué hice

1. Leí la documentación de Open-Meteo (pronóstico, histórico, histórico de pronósticos, elevación, precios y términos), de ERA5-Land (CDS), de NASA POWER y los metadatos IDEAM de datos.gov.co. Cada cifra del entregable lleva su URL o está marcada como CALCULADO, SUPUESTO o NO VERIFICADO.
2. Descargué para 6 estaciones IDEAM de 2025 las series de Open-Meteo (best_match, ecmwf_ifs, era5, era5_land, histórico de pronósticos, más era5_land e ifs sin corrección por altura) y de NASA POWER. No usé cuentas ni claves. Las respuestas quedaron en `escalabilidad/clima_global/cache/`.
3. Validé cada fuente contra T y HR horarias de IDEAM. Los datos IDEAM los leí de `raw/ideam_datosgov_2025/`, de otro agente, sin modificarlos.
4. Corrí un experimento de calibración: ventanas de 7, 14, 28 y 42 días al inicio de cada mes, prueba en el resto del año, comparado con "sin corrección" y con "promedio de las estaciones vecinas".
5. Escribí el prototipo `escalabilidad/clima_global/clima_global.py` con los subcomandos `dia1`, `lote` y `calibrar`, y los perfiles de cultivo (arándano, fresa, mora). Lo probé con 7 puntos de 4 países en una sola petición.
6. Revisé `clima/clima_client.py` en modo solo lectura y documenté 14 cambios (sección 7 del entregable).

## Hallazgos principales (detalle y fuentes en el entregable)

- En 5 de las 6 estaciones IDEAM `fechaobservacion` viene en **UTC**; en la de la CAR (Salitre) viene en hora local. Sin corregir esto, el MAE de T se multiplica por ~3. El agente de clima encontró lo mismo por su cuenta.
- IFS 9 km con corrección por altura (DEM) da la T horaria con un MAE de 1,15 a 1,58 °C. NASA POWER falla hasta +4,5 °C por su celda gruesa y multiplica por 2,5 los días favorables.
- El error de horas mojadas (proxy HR ≥ 90 %) del modelo va de 3,0 a 4,8 h/día. En Duitama el sesgo es de −4,25 h/día y con **14 días** de sensor baja a −0,62 h/día.
- La corrección promedio de las estaciones vecinas empeora Duitama (−5,66 h/día). La calibración tiene que ser por finca, lo que lleva a proponer un **kit itinerante** (~155 AUD por finca, SUPUESTO de rotación).
- Sensores con problemas: HR truncada en Tunguavita (p99 86 %) y en Guasca (p99 93 %); altura del catálogo de Salitre probablemente errónea (2.637 m frente a 3.284 m del DEM); caída de la red en febrero de 2025; filas duplicadas.
- La `leaf_wetness_probability` horaria de Open-Meteo no está documentada y concuerda poco con el proxy de estación.
- La lluvia diaria del modelo frente al pluviómetro de Guasca tiene r de 0,20 a 0,33. Hace falta pluviómetro en la finca.
- La API gratuita de Open-Meteo es **solo no comercial**. Para vender se necesita un plan comercial (precios no publicados) o un servidor propio (AGPLv3).

## Límites

Solo 6 estaciones andinas (4 con HR válida) y un año. El "mojado" de referencia es HR de estación y no un sensor de hoja. Los umbrales de enfermedad de los perfiles son SUPUESTO. Fuera de Colombia no hay validación; allí la demo solo comprueba que el código corre.

## Archivos

- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/clima_global.md`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/clima_global/clima_global.py`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/clima_global/perfiles/` (arandano, fresa, mora, fincas_demo)
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/clima_global/scripts/descargar_validacion.py`, `validar_y_calibrar.py`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/clima_global/resultados/` (CSV de validación, QC, calibración, LWP, lluvia y salidas del prototipo)
