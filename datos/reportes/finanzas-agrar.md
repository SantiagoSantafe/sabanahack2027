# Reporte del analista financiero: economía del kit robot para AGRAR

Fecha de corte: 2026-10-23. TRM: 3.185,01 COP/USD (FUENTE: datos.gov.co, vigente el 23-oct-2026; la TRM del 24 al 26 de octubre es 3.158,43). Moneda del modelo: COP, con importaciones en USD.

Entregables en `/Users/santiagosantafe/Downloads/SabanaHack/datos/finanzas/agrar/`:
- `agrar_roi.py`: modelo completo con la biblioteca estándar. Se corre con `python3 -I agrar_roi.py` o con `.venv/bin/python -I`; dan el mismo `RESUMEN.md` (mismo md5). Los parámetros están en el dict `PAR`, cada uno con valor, rango, tipo (FUENTE / DERIVADO / SUPUESTO / NO VERIFICADO) y nota. También salen en `parametros.csv`.
- `RESUMEN.md`: tablas de BOM, AGRAR, cliente final con payback, capacidad, matriz en dos versiones y las 5 frases del pitch. Lo genera el script.
- 19 CSV de salida y `payback_vs_puntos.png`.

## 1. Qué hice

1. Leí `RESPUESTAS_MENTOR.md`, `finanzas/parametros.yaml`, `reportes/finanzas.md`, las secciones de negocio de `ESCALABILIDAD.md` y la verificación adversaria. Reutilicé la cadena de importación del modelo previo: flete 5 USD/kg + 150, seguro 1 %, arancel 5 %, IVA 19 %, agencia 350.
2. Verifiqué la TRM en datos.gov.co (no usé el supuesto de 4.000).
3. Construí el BOM, la economía de AGRAR y la del cliente, la capacidad por geometría, la matriz y el puente de costo por ha.

## 2. Cifras clave

| Tema | Resultado |
|---|---|
| Costo del kit D1 Ultra para AGRAR | 60,2 M COP (hardware puesto 35,4 M; 238 h de ingeniería, viáticos, desarrollo base y garantía 24,8 M) |
| Precio con 40 % de margen | **100,4 M COP**, dentro de 90-110 M (con IVA al cliente: 119,5 M) |
| Variante D1 EDU | 91,5 M COP |
| Margen de maniobra | Corto. D1 a 9.600 (tienda), IVA como costo o TRM 3.900, cada uno por separado, lleva el precio a 111-113 M. El escenario adverso combinado da 152 M. Con 2 robots: 170,6 M |
| Recortes que devuelven el adverso a rango | EDU (−30,1 M), horas −30 % (−11,9 M), NRE a la suscripción (−3,6 M), batería opcional (−4,0 M), garantía en la suscripción (−2,9 M): termina en 99,6 M |
| 10 proyectos/año | 1.004 M COP de ingreso, 402 M COP de margen bruto |
| Suscripción (software + soporte 7,0 M, consumibles 10,0 M) | 17,0 M COP/finca/año, margen 42 %. En el año 5, con 34 fincas activas: 585 M COP/año, 1.589 M COP de ingreso total |
| Cliente, 22,5 ha, caso central (12 t/ha, 8 USD/kg) | Cosecha 6.880 M COP/año. Payback: ~24 meses con 1 punto de pérdida evitada, 10 con 2, 6 con 3 |
| Puntos mínimos para payback < 24 meses | 0,8 (alto, 10 USD/kg), 1,0 (central), 1,75 (conservador, 9,07 t/ha y 6 USD/kg) |
| Ahorro de monitoreo | 173 jornadas/año = 10,5 M COP (0,15 % de la cosecha): no justifica el sistema por sí solo |
| Capacidad de 1 robot | 5,4 bloques por noche; vuelta de 40 bloques en ~7 noches (3-12) frente a 11-17 jornadas de una persona; ~19 ha/semana |
| Matriz (6 criterios) | A 70, B 75, C 57, D 42, E 56, **F 89**. Con escalabilidad 15 %: 65,5 / 75,8 / 57,5 / 38,7 / 53,6 / **87,7**. Con costo al 30 %: F sigue primero (85,4 y 83,3) |
| Costo del híbrido por ha (cifra unificada) | **~867 USD/ha/año (2,76 M COP)** con falsas alarmas; ~717 sin ellas |

## 3. Cómo se relacionan las cifras de costo por ha (430 / 722 / 820 / 867)

- **430:** cifra vieja del documento. Es un costo sin falsas alarmas ni mantenimiento completo. Queda obsoleta.
- **722:** híbrido del modelo de finanzas para un productor que compra y arma todo (D1 + 20 nodos + gateway). No incluye ingeniería de integración ni margen de un integrador.
- **820:** opción A, D1 con mástil y sin red (2 robots en filas de campo). No aplica al invernadero ni es la oferta de AGRAR.
- **867:** el híbrido de AGRAR. Puente: 722, menos la red nueva (−235), más el precio de AGRAR en lugar del equipo comprado (a 826), más suscripción y consumibles en lugar de nube y mantenimiento (a 957), menos dilución a 22,5 ha. Queda 20 % sobre 722 porque entran la ingeniería, la base de carga y el margen de 40 %, que el modelo previo no contaba. La red sí sale gratis para AGRAR.
- **520:** precio de servicio del modelo de negocio; es otro modelo y no se mezcla.

## 4. Observaciones que el equipo debe tener presentes

1. **El resultado depende más de la ingeniería que del robot.** El 41 % del costo son horas, viáticos, desarrollo y garantía (238 h a 80.000 COP/h, ambas SUPUESTO). El primer proyecto debe medirlas.
2. **El payback del cliente está en el límite.** Con 1 punto de pérdida evitada en el caso central da 23,8 meses; en el conservador no cumple hasta ~1,75 puntos. Parte de la mejora ya la captura el modelo predictivo del PLC, así que el aporte incremental del robot (0,5-2 puntos) es un SUPUESTO sin dato. Con 0,5 puntos no cumple en ningún escenario.
3. **La matriz favorece a F casi por construcción:** F incluye a B (la red). En el barrido de pesos F queda primero en 91 % de las combinaciones, frente a 74 % en la matriz verificada anterior. La razón es el contexto nuevo (la red ya existe, AGRAR no asperja, D y E quedan fuera de presupuesto). La matriz no prueba que el robot valga 100 M; eso lo muestra el payback.
4. **Capacidad:** 1 robot cubre una vuelta completa en ~7 noches y una ronda de riesgo de ~5 bloques por noche (14 % de la finca). Si el cliente exige una vuelta en ≤ 5 noches, hacen falta 2 robots y el proyecto sale del presupuesto; la alternativa es priorizar con el PLC. Los pasillos por nave (camas − 1) y la distancia a la base son DERIVADOS/SUPUESTOS que deben medirse en el levantamiento.
5. **Cálculo del jornal:** el equipo indicó 19 USD; el modelo previo calculaba 23,82 USD con prestaciones. Con 23,82 el payback baja de 24 a 23 meses.

## 5. Límites

- Precios NO VERIFICADOS: D1 Ultra 7.499 FOB (la tienda lista 9.600), D1 EDU, batería de repuesto (450), X2 Ultra y Amiga. El precio del Jetson (249 USD) es de lista anunciada y no lo reverifiqué hoy.
- Todos los componentes de cámara, T/HR, LoRa, base de carga, mástil y cableado son SUPUESTOS de compra.
- IVA: se supone recuperable por AGRAR; no se verificó con un contador, ni si los 90-110 M incluyen IVA (si lo incluyeran, el precio neto máximo es 92,4 M y el kit base no cabría sin recortes).
- Margen del 40 %: leído como margen bruto sobre el precio (si fuera recargo sobre costo, el precio baja a ~84 M).
- Pérdida: se aplica sobre el valor cosechado (lectura del dato del mentor). No incluye costos de estructura de AGRAR ni impuesto de renta, financiación ni valor residual.
- Carga automática en base, línea de vista del manual y autonomía real con cámara y cómputo no están verificadas.
- El D1 EDU: la ficha no declara IP; se toma IP54 de la guía SDK.

## 6. Pendientes

1. Cotización formal del D1 Ultra y de la batería puestos en Colombia.
2. Confirmar con el contador el tratamiento del IVA y la base de los 90-110 M.
3. Medir horas reales de ingeniería en el primer proyecto.
4. Piloto con camas testigo para estimar los puntos de pérdida evitados.
5. Preguntar al mentor cuántas falsas alarmas tolera el cliente y quién acompaña al robot de noche.
