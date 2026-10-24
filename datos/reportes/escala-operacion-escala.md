# Reporte: escala · operacion-escala

Fecha: 23-oct-2026. Rol: diseñar la operación cuando la solución se vende a muchos productores. La Sabana de Bogotá es solo el ejemplo.

## Entregables

| Archivo | Qué es |
|---|---|
| `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/operacion.md` | Documento principal: los tres modelos operativos y la regla para elegir entre ellos, rutas dentro de la finca y entre fincas, caseta de carga, transporte, conectividad sin conexión primero, mantenimiento preventivo, técnicos por N robots, onboarding paso a paso con diagrama mermaid, métricas del piloto, soporte y SLA, otros frutales y climas, riesgos |
| `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/operacion/capacidad.py` | Cálculo reproducible (`python3 -I capacidad.py`). Cada parámetro trae su URL o la marca SUPUESTO |
| `.../operacion/capacidad.csv` | Hectáreas por robot por semana en 6 escenarios (D1 Ultra y MaxPro) |
| `.../operacion/flota.csv` | Capacidad de una cuadrilla itinerante con 1, 2 o 3 robots |
| `.../operacion/repuestos.csv` | Pool de reserva por tamaño de flota (Poisson) |
| `.../operacion/tecnicos.csv` | Técnicos de campo necesarios por N robots y por ritmo de onboarding |
| `.../operacion/costo_tecnico_ha.csv` | Costo del técnico en USD/ha/año para los modelos fijo, rotación y cuadrilla |

## Hallazgos que cambian la propuesta

1. **Capacidad del D1 Ultra.** En el escenario base, un robot cubre ~10,8 ha por semana con una visita semanal por cama, y ~16,6 ha si los sensores priorizan. **La finca de 20 ha del ROI necesita 2 robots**, salvo que el piloto mida ~0,8 m/s de inspección (21,5 / 33 ha). El rango total va de 2 a 33 ha. La velocidad efectiva es el primer número que hay que medir.
2. **"MaxPro ~60 ha" es optimista.** Da 26 ha en el escenario base y 53 ha en el optimista. Conviene decir "25–50 ha".
3. **La batería es extraíble y carga en una base externa.** Lo dice el manual del D1 Edu ("Insert the battery into the charging dock"). La carga toma ~1 h y la autonomía es de 1–2 h, según el manual del D1 Ultra. Esto **resuelve el NO VERIFICADO de `bateria_intercambiable` y `carga_h`** en `escalabilidad/unit_economics_parametros.yaml`. Sigue sin verificar que el cambio sea en caliente: el procedimiento del manual apaga el robot.
4. **Las baterías son un insumo.** En el escenario base se gastan ~1.230 ciclos por robot al año. La garantía es de 6 meses o 200 ciclos. Con una vida supuesta de 500 ciclos salen ~2,5 baterías por robot al año, con precio NO VERIFICADO.
5. **Costo del técnico por hectárea.** Robot fijo: 72–101 USD/ha/año. Rotación: ~276. Cuadrilla operada por el técnico: 768–846, por encima del beneficio de ~430 USD/ha/año. El operario de la finca tiene que hacer lo diario.
6. **Límites del manual que afectan la operación.** Pide línea de vista. No se puede limpiar con líquidos ni alcohol, lo que obliga a una bioseguridad en seco con almohadillas por finca. Solo opera entre 0 y 40 °C, es IP54 y no se debe usar en superficies resbalosas. Abrir el robot anula la garantía. Las reparaciones van al centro de AgiBot: 7 días hábiles más logística. Por eso hace falta un pool de reserva del 6–20 %.
7. **Las baterías no viajan en avión de pasajeros.** Cada una tiene ~199 Wh, y por encima de 160 Wh la IATA exige enviarlas como carga peligrosa. Para abrir otra región hay que mandarlas por tierra o como carga.
8. **El mercado está fragmentado.** EVA 2025: 906,7 ha en 65 municipios; 34 municipios tienen menos de 5 ha; 8 municipios concentran el 64 % del área. De ahí los tres modelos: robot fijo, rotación y solo sensores.
9. **Precio del D1 Ultra.** La tienda oficial lo lista en 9.600 USD (23-oct-2026), frente a los ~7.499 FOB México de la propuesta. El modelo de negocio ya lo registra.

## Coherencia con otros roles

- `unit_economics_parametros.yaml` (modelo-negocio) usa 0,8 m/s, 1,25 h de autonomía y 0,80 de disponibilidad. Agregué ese escenario a mi tabla para que los dos números sean comparables: da 21,5 ha por semana. Mi escenario base es más conservador (0,4 m/s).
- `reportes/finanzas.md` llega a la misma conclusión por otro camino: un D1 Ultra cubre ~12,5 ha por semana, así que 20 ha necesitan 2 robots, y ~25 ha si la red lo dirige. Mi escenario base da 10,8 / 16,6.
- Las proporciones de técnicos que usa el modelo de negocio (15 robots dedicados y 6 en ruta por técnico) coinciden con las mías (12–17 fijos; ~4,6 en rotación).
- No encontré un plan de mantenimiento del equipo en `datos/reportes/`. Hice uno con el manual del fabricante y supuestos marcados. Si otro rol publica uno, hay que reconciliarlos.

## Pendientes y supuestos más sensibles

- Velocidad efectiva de inspección, ventana diaria con hoja seca y política de revisita: preguntas 3, 5 y 20 al mentor y semana 1 del piloto.
- Precio y vida en ciclos de la batería del D1 Ultra.
- Si AgiBot permite operar sin línea de vista en producción.
- Si las almohadillas se cambian sin herramientas, y si la limpieza en seco basta como bioseguridad, lo que tiene que validar un fitopatólogo.
- Distancias reales entre fincas de cada clúster.
- Jornada de 42 h: solo la vi en prensa, no en el texto oficial de la Ley 2101.

## Fuentes principales

- EVA 2019-2025: https://www.datos.gov.co/d/uejq-wxrr
- Manual del D1 Ultra: https://www.agibot.com/file/ueditor/php/upload/file/20260911/1789114774395970.pdf
- Manual del D1 Edu: https://www.agibot.com/file/ueditor/php/upload/file/20260825/1787630185233501.pdf
- Tienda del D1 Ultra: https://store.agibot.com/products/d1-ultra
- D1 MaxPro: https://www.generationrobots.com/en/404440-agibot-d1-max-pro-quadruped-robot.html
- IATA, baterías de litio: https://www.iata.org/contentassets/6fea26dd84d24b26a7a1fd5788561d6e/passenger-lithium-battery.pdf
- LoRaWAN, alcance rural: https://www.electronicdesign.com/markets/automation/article/21806072/11-myths-about-lorawan
- Conectividad rural (ECV del DANE vía Blu Radio): https://www.bluradio.com/tecnologia/mas-de-3-5-millones-de-nuevos-hogares-rurales-cuentan-con-internet-segun-el-dane-rg10
- La lista completa está al final de `operacion.md`.
