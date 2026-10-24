# Cifras clave · Berry Good Idea (fuente única de verdad)

Corte: 24-oct-2026. Si otro documento contradice esta tabla, vale esta. Cada cifra apunta a su archivo fuente (rutas desde la raíz del proyecto).

## 1. Clasificador (modelo EN USO: `modelo_camara`, Mc_tr, medido con la cámara del robot)

| Cifra | Valor | n / IC95 | Fuente | Nota |
|---|---|---|---|---|
| Sensibilidad (enfermas con alerta) | **0,78** | 42/54 · IC por grupo 0,61–0,92 | `datos/reportes/reentreno-camara.md`; `datos/resultados/ml/modelo_camara/test_resultados.json` | 68 hojas de laboratorio mostradas a la cámara del D1 |
| Falsas alarmas (sanas con alerta) | **0,29** | 4/14 · IC 0,00–0,71 | ídem | Especificidad medida 10/14 = 0,71 (reemplaza el 0,95 supuesto) |
| Enfermedad exacta (4 clases) | 0,54 | IC no reportado en el resumen | ídem | Alternaria y oídio se confunden con sana |
| Alternaria (clase débil) | 3/14 diagnosticadas | 0,21 | ídem (matriz de confusión) | 7 de 14 se leen como sana |
| Umbral / preprocesamiento | 0,986 · corrección de color + auto-recorte (`"panel"`) | elegido con 10 sanas de val: frágil | `datos/resultados/ml/modelo_camara/umbral.json` | |
| Referencia con B en cámara | falsas alarmas 1,00 | 14/14 | `reentreno-camara.md` | B alertaba siempre |
| *Modelo anterior / imagen limpia* (`modelo_final`) | sens 0,80 · falsas alarmas 0,36 | 43/54 · 5/14 (IC 0,66–0,89 · 0,13–0,65) | `datos/resultados/ml/RESULTADOS.md` §3.2 | Test limpio de DrBerry, SIN cámara. No citar como rendimiento del robot |
| *Modelo B (aumentos), imagen limpia* | sens 0,80 · falsas alarmas 0,29 | test limpio DrBerry | `datos/reportes/reentreno-aumentos.md` | Anterior a `modelo_camara`; el 0,29 coincide por casualidad con el de cámara |
| Recortes oídio + Heliothis (cota superior) | 52/52 · 0/14 falsas alarmas | localización perfecta; grupos: límite inferior ~0,82 | `datos/reportes/verificacion-ml.md` §4.3 | Sustituye al "87/87 con 0/14", que NO se muestra: las lesiones de alternaria (~96 px) se separan solo por tamaño |

## 1b. Monitoreo manual HOY (dato empresa, actualizado 24-oct-2026) — USAR ESTE en el pitch

| Cifra | Valor | Fuente | Nota |
|---|---|---|---|
| Recorrido completo de una finca de ~20 ha | **7–8 días hábiles con 5–6 operarios** | Dato del equipo/AGRAR, 24-oct-2026 (mensaje del usuario) | **Reemplaza** en el pitch el "4–5 días por 12–15 bloques" (ese era 1 persona, finca pequeña; queda solo como dato de la entrevista) |
| Equivalente calendario | ≈ **9–11 días calendario** (1,5–2 semanas) | cálculo: días hábiles lun–vie + fin de semana | Solo de día (6 a.m.–2 p.m.); de noche y fines de semana nadie revisa |
| Esfuerzo por vuelta | **35–48 jornadas-persona** por vuelta de 20 ha (≈ 1,8–2,4 jornadas/ha) | cálculo: 5–6 × 7–8 | SUPUESTO de costo por jornada ≈ 2,8 M COP/mes ÷ ~24 días ≈ 117 mil COP → **≈ 4,1–5,6 M COP por vuelta** (≈ 205–280 mil COP/ha por vuelta). Marcar como estimación |
| Comparación honesta con el robot | 1 D1 recorre los 40 bloques en ~7 noches (rango 3–12 noches; 12–42 ha/semana), pero **cada noche empieza por las camas de mayor riesgo** y la alerta llega en minutos | `datos/finanzas/agrar/RESUMEN.md` §4; ver fila "19 ha" abajo | El contraste no es "cubre todo en minutos": es **alerta en minutos donde hay riesgo** + todas las noches, sin papel ni digitación |

Frase sugerida: *"Hoy, 5 a 6 operarios tardan 7 a 8 días hábiles en recorrer una finca de 20 ha, solo de día y en papel. Con el robot, la cama en riesgo se revisa esa misma noche y la alerta llega en minutos."*
Lema: **"De 8 días hábiles a minutos"** (en vez de "de 5 días a 5 minutos").

## 2. Riesgo ambiental

| Cifra | Valor | n / IC | Fuente | Nota |
|---|---|---|---|---|
| Botrytis | Bulger 1987 (fresa, proxy) | sin validar en arándano | `datos/riesgo/risk.py`; `datos/reportes/modelos-riesgo.md` | **Es la enfermedad principal según el mentor** |
| Antracnosis | Wilson 1990 + aproximación Gillett y Schilder 2009 | sin validar | ídem | NO es Miles 2013 (coeficientes no obtenidos) |
| Sensibilidad por día de alerta | 28–48 % | un año de clima, sin datos de incidencia | `datos/reportes/backtest-riesgo.md` | El riesgo ambiental no está validado contra enfermedad real |

## 3. Finanzas AGRAR (22,5 ha, vida 3 años)

| Cifra | Valor | n / supuesto | Fuente | Nota |
|---|---|---|---|---|
| **Costo del híbrido por ha (VIGENTE)** | **~867 USD/ha/año** (~2,76 M COP); 717 sin falsas alarmas | 22,5 ha, con falsas alarmas | `datos/finanzas/agrar/RESUMEN.md` §6; `agrar_roi.py` | Es la única cifra de costo para AGRAR |
| 722 | 722 USD/ha/año | 20 ha, productor que compra y arma todo (1 D1 + 20 nodos + gateway) | `datos/reportes/finanzas.md` | Solo para un cliente sin infraestructura |
| 820 | 820 USD/ha/año | opción A: D1 con mástil SIN red, 2 robots, filas de campo | ídem | No aplica a AGRAR |
| 520 | 520 USD/ha/año | precio de servicio RaaS (otro modelo de negocio) | `datos/ESCALABILIDAD.md` | No se mezcla con el costo |
| 430 | obsoleta | costo viejo, sin falsas alarmas ni mantenimiento | `RESUMEN.md` §6 | No usar |
| Kit para AGRAR | 100,4 M COP antes de IVA (119,5 con IVA); costo 60,2 M | margen 40 %; cabe en 90–110 M | `RESUMEN.md` §1–2 | Colchón corto |
| Payback del cliente | ~24 meses con 1 punto de pérdida evitado; ~10 con 2 | central; los puntos son SUPUESTO | `RESUMEN.md` §3 | A medir en piloto con camas testigo |
| Matriz de alternativas (F híbrido) | **89,0** (6 criterios) | B 75,0 · A 70,0 · C 57,0 · E 56,0 · D 42,0 | `RESUMEN.md` §5; `matriz_totales.csv` | Variantes: 87,7 con Escalabilidad 15 %; 85,4 / 83,3 con costo 30 %. El **83** de versiones viejas era la matriz anterior al contexto AGRAR |

## 4. Capacidad por robot (ha/semana)

| Cifra | Supuesto al que corresponde | Fuente |
|---|---|---|
| **19 (VIGENTE para AGRAR)** | patrulla NOCTURNA de riesgo, 0,5 m/s, 1,5 h de batería, carga 1 h; vuelta de 40 bloques en ~7 noches (rango 3–12 noches; 12–42 ha/semana) | `RESUMEN.md` §4; `capacidad.csv` |
| 12,5 | finanzas opción A: de día, cada cama 1 vez por semana, 36 h/semana, 0,5 m/s, sin red | `datos/reportes/finanzas.md` |
| 16,6 | operación, 0,4 m/s, con la red priorizando camas (10,8 sin red) | `ESCALABILIDAD.md` §6.2 |
| 24,9 | finanzas opción F: misma cuenta que 12,5 pero la red prioriza (fracción 0,5) | `datos/reportes/verificacion-finanzas-robots-documento.md` |
| 35,8 ≈ 36 | modelo de negocio, optimista: 0,8 m/s, entrecalle 3,0 m | `ESCALABILIDAD.md` §2.7 |
| Frase segura de pitch | "Un D1 Ultra cubre entre 16 y 36 ha según la velocidad medida; en AGRAR, ~19 ha/semana de noche" | |

## 5. Hardware del robot

| Cifra | Valor | Fuente | Nota |
|---|---|---|---|
| Kit D1 Ultra (documento de presentación) | ≈ 34,85 M COP sin IVA (≈ 41,5 M con IVA) | documento del equipo | D1 Ultra, 1 batería de repuesto, Jetson a bordo, LoRaWAN |
| Hardware en `RESUMEN.md` | 35,40 M COP puesto, sin IVA | `RESUMEN.md` §1 | Diferencia 0,55 M ≈ SSD + fuente DC-DC + caja del cómputo (0,54 M) que AGRAR ya tiene. `RESUMEN.md` ya cuenta 1 batería (no 2). Además incluye base de carga y mástil, que el kit de presentación no desglosa |
| Cámaras fijas equivalentes | ≈ 2.300 M COP | documento del equipo | Comparación de escala |
| Humanoides | 4–8 veces el costo | documento del equipo | |

## 6. Frase de limitaciones (obligatoria en la diapositiva)

> Probado con 68 hojas de laboratorio mostradas a la cámara del robot, solo 14 sanas; alternaria es la clase débil; el riesgo ambiental no está validado contra enfermedad real. Por eso el robot sugiere y el supervisor manda a un operario a confirmar.
