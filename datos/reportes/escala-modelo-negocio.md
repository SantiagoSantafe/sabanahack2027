# Reporte: escala-modelo-negocio

Fecha: 2026-10-23. Rol: modelo de negocio para vender la solución a muchos productores.
Documento principal: `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/modelo_negocio.md`.

## Qué hice

1. **Busqué precios de referencia y abrí las páginas cuando pude:**
   - METOS/Pessl: 96 EUR/año por modelo de enfermedad de 1 cultivo; 336 EUR/año por la estación virtual.
   - Davis WeatherLink Pro+: 8,95 USD/mes por equipo.
   - Taranis: 15-20 USD/acre por temporada (2018).
   - Saga Thorvald: cobra por ha y no publica la tarifa; tiene 150 robots para 1.300 acres en EE. UU.
   - Trapview: una trampa cada 20 ha.
   - Dragino LLMS01: 129 USD.
   - AgiBot D1 Ultra: 9.600 USD de lista en store.agibot.com. Ficha: 1-2 h de batería, IP54, 5 kg de carga.
   - Manual del D1 Ultra: batería extraíble, celda garantizada por "6 months / 200 cycles", y la instrucción "Keep the robot within your line of sight".
   - D1 MaxPro: 65.999 USD, IP67, 5,5 h de batería, 50 kg de carga.
   - SMMLV 2026: 1.750.905 COP. TRM del 2026-10-23: 3.185,01 COP/USD.
   - EVA 2025 de arándano y otros frutales. Exportación de arándano 2024. Área de arándano en Perú.
2. **Escribí `unit_economics_parametros.yaml`:** 111 parámetros, cada uno con `valor` y `fuente` (FUENTE con URL, CALCULADO, CONTEXTO, SUPUESTO, PROPUESTA o NO VERIFICADO).
3. **Escribí `unit_economics.py`:**
   - Usa solo la biblioteca estándar e incluye un lector YAML mínimo, porque el `python3` del sistema (3.9.6) no tiene PyYAML. Con PyYAML (venv) da la misma salida.
   - Lo corrí con `python3 -I`.
   - **Qué calcula:**
     - hectáreas por robot a la semana;
     - CAPEX y costo anual del robot, con la reposición de baterías por ciclos;
     - red de sensores por finca;
     - valor para el productor y precio máximo con ROI 3x;
     - ventana de precio por segmento;
     - desglose del costo;
     - palancas para la finca pequeña;
     - tablas para 10, 50, 200 y 1.000 ha con cinco modelos (venta, RaaS, SaaS + kit, híbrido y MaxPro);
     - escala mínima con EBIT ≥ 0;
     - sensibilidades y riesgos operativos;
     - mercado alcanzable.
4. **Guardé la salida** en `unit_economics_salida.txt`, con el anexo de fuentes, y en `unit_economics_resultados.json`.
5. **Leí `operacion.md` y `mercado.md`**, de otros agentes, sin modificarlos. Verifiqué en el manual los datos de batería y de línea de vista que citaba `operacion.md`, y los incorporé.

## Hallazgos principales

| Tema | Resultado |
|---|---|
| Capacidad del D1 Ultra | 35,8 ha por robot a 0,8 m/s inspeccionando el 60 % de las camas por semana. Baja a 17,9 ha a 0,4 m/s, que es la base de `operacion.md` |
| Robot puesto en finca | 11.599 USD de CAPEX y 7.084 USD/año de costo, con unas **4,3 baterías repuestas por año** |
| RaaS dedicado a 520 USD/ha/año | Finca de 30 ha: costo 401 USD/ha, margen 23 %, payback 23 meses. Finca de 120 ha: margen 30 %. ROI del productor 3,1x; equilibrio en 90 kg/ha |
| Precio máximo del productor (ROI 3x) | 548 USD/ha con robot y 256 USD/ha solo con la red, suponiendo 2 % y 1 % de pérdida evitada |
| Velocidad, la variable que decide | A 0,4 m/s el RaaS pierde dinero (-14 % con la flota repartida). A 0,6 m/s el margen es 16 %; a 0,8 m/s, 32 % |
| Línea de vista | Si alguien nuevo tiene que acompañar al robot, el ROI del productor cae a 1,7x |
| Finca pequeña | Con robot en ruta el margen es 2 %. Con SaaS vendido por canal y kit autoinstalable, 31 % y ROI 3,4x |
| Venta de equipo | Cierra desde 30 ha (ROI 3,2x). En 5 ha el ROI es 0,8x |
| MaxPro solo como inspector | Costo 820 USD/ha, margen -32 %. Se descarta |
| 1.000 ha con el híbrido | EBIT -7.997, CAPEX 333.675, payback 24 meses, ROI del productor 3,2x. Con RaaS puro: EBIT -10.848, CAPEX 657.555, ROI 2,9x |
| Escala mínima del híbrido | 1.071 ha, el 118 % del arándano colombiano. El negocio necesita otros frutales y Perú |

## Frases para el pitch

- "Un D1 Ultra cubre unas 36 ha. Al productor le cuesta 520 USD/ha/año y recupera lo que paga si salva 90 kg/ha, menos del 1 % de su cosecha."
- "Finca pequeña: sensores y celular a 130 USD/ha/año, a través de su asociación. Mediana: robot como servicio. Grande: compra. Cada una recibe al menos 3 dólares por cada dólar que paga."
- "El negocio se paga desde unas 1.100 ha, más que todo el arándano del país. Por eso el software sirve para cualquier frutal y el robot va solo donde rinde."

## Límites

- 94 de los 111 parámetros son SUPUESTO, PROPUESTA o NO VERIFICADO. Los que más mueven el resultado:
  - la velocidad efectiva y el porcentaje de camas por semana;
  - si hace falta acompañar al robot (línea de vista);
  - los ciclos y el precio de la batería (450 USD, NO VERIFICADO);
  - la distancia entre camas;
  - la pérdida evitada real;
  - la vida del robot.
- El precio de 7.499 USD FOB México del D1 Ultra y el de 67.999 del MaxPro vienen del contexto; no los verifiqué.
- La página de fin24 sobre Aerobotics redirige; su precio queda NO VERIFICADO. Saga y Trapview no publican tarifas.
- Faltan el costo colombiano de fungicida por ha (usé 600 USD, NO VERIFICADO) y el precio al productor en Colombia (usé 6 USD/kg, coherente con el equipo; la exportación de 2024 da 5,25).
- Fuera del modelo: impuestos, costo financiero, churn explícito y el MaxPro haciendo aspersión.

## Diferencias con otros agentes

- **Velocidad base.** `operacion.md` usa 0,4 m/s y este modelo 0,8 m/s. Con 0,4 m/s el RaaS a 520 USD/ha no es rentable, así que hay que medirla en el piloto antes de comprometer el precio. La tabla 9b de la salida muestra los dos casos.
- **Mercado.** `mercado.md` usa otros precios (Vigía a 60 USD/ha, Centinela a 430) y calcula un SOM de unos 0,45 M USD/año. Este modelo usa 130 y 520 USD/ha. Conviene que el equipo elija una sola lista de precios para el pitch.

## Archivos

- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/modelo_negocio.md`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/unit_economics.py`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/unit_economics_parametros.yaml`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/unit_economics_salida.txt`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/unit_economics_resultados.json`

No modifiqué archivos de otros agentes.

## Pendientes

- Confirmar con AgiBot o su distribuidor:
  - el precio de una batería extra y su vida en ciclos;
  - el precio FOB del robot;
  - si la línea de vista aplica a la operación autónoma.
- Medir en el piloto: velocidad con fotos útiles, horas por batería con el mástil, minutos diarios del operario y pérdida evitada en camas testigo.
- Unificar la lista de precios con `mercado.md` y con el agente de finanzas, y volver a correr el script.
