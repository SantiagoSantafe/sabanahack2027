# Ciclo de datos y aprendizaje: cómo el sistema mejora con cada productor

Rol: **datos-aprendizaje** · Sabana Hack, reto "Berry Good Idea" · 23 de octubre de 2026

**Para qué sirve este documento.** La organización que plantea el reto quiere vender la solución a muchos productores y de varios frutales, no a una sola finca. La Sabana de Bogotá es solo el ejemplo de la demo. Aquí se diseña la parte que hace escalable el producto: cómo cada finca nueva aporta datos, cómo esos datos mejoran el modelo de todas las fincas, con qué métricas se controla y bajo qué reglas de propiedad y de ley.

**Convenciones.**
- **[V]**: la cifra está verificada en una URL que abrí. La lista completa está en la sección 16.
- **SUPUESTO**: valor de diseño, que hay que validar con el mentor o en el piloto.
- **NO VERIFICADO**: no pude confirmarlo en una fuente primaria.
- **Cálculo**: aritmética hecha sobre supuestos declarados; se puede rehacer cambiando los supuestos.
- Este documento no es asesoría legal.

---

## 0. En 30 segundos

1. **No existe un dataset público de enfermedades de arándano tomado desde un robot y en condiciones andinas.** El más cercano, DrBerry, salió de una sola finca peruana, a mediodía con sol y con cámaras de consumo [V]. Según la ficha del equipo (`datos/resultados/ficha_drberry.md`), todo se tomó en una sola sesión de unas 2 horas y con hojas casi siempre desprendidas o en la mano. El modelo de la demo es solo un punto de partida. **El producto que se vende es el ciclo que lo mejora.**
2. **Cada confirmación o descarte del triage agrónomo→operario es una etiqueta que no cuesta nada extra.** Con el aprendizaje activo y una auditoría pequeña salen unas **70 etiquetas útiles por semana y por finca**, o sea unas **3.150 al año** (cálculo con SUPUESTOS, sección 4).
3. **Aprendizaje activo.** Cada semana el sistema le pide al agrónomo revisar **20 imágenes elegidas a propósito** (las inciertas, las nuevas, las de "pre-síntoma" y una parte al azar). Le toma unos 10 minutos (SUPUESTO).
4. **Reentrenamiento centralizado al inicio.** El federado queda como opción de pago para exportadores que no quieran sacar sus imágenes de la finca.
5. **Un modelo base compartido, con una cabeza por cultivo y una calibración por finca.** No se hace un modelo por finca, porque eso fragmenta los datos y anula el efecto de red.
6. **Métricas que se venden.** La primera son las **falsas alarmas por semana y por finca**, contra un presupuesto que acuerda el productor. La segunda es la **sensibilidad estimada con auditoría ciega**, siempre reportada con su intervalo de confianza.
7. **Gobierno de datos.** Los datos son del productor y los modelos son de la red. El productor decide si su dato entra a la red. La Ley 1581 de 2012 aplica a usuarios, operarios, productores que son personas naturales y fotos donde aparezcan personas. Los datos agronómicos se protegen por contrato y como secreto empresarial (Decisión Andina 486, art. 260).
8. **Efecto de red medible.** Una finca sola ni siquiera puede medir bien su propia sensibilidad: con 8 de 9 focos detectados en un mes, el intervalo de confianza va de 57 % a 98 %. Una red de 30 fincas lo mide con ±2 puntos (cálculo, sección 9.2).

---

## 1. Por qué el modelo no se puede quedar quieto

| Evidencia | Dato | Qué implica para escalar |
|---|---|---|
| Mohanty, Hughes y Salathé (2016), PlantVillage | 99,35 % de exactitud en el test del mismo dataset de laboratorio (54.306 imágenes, 14 cultivos); **31,40 %** en imágenes de otras fuentes y condiciones [V] | Si cambian la luz, el fondo o la cámara, el modelo se cae. Cada finca nueva es un dominio nuevo |
| DrBerry, paper KDIR 2023 | Una finca (Fundo San Roberto, Sayán, Lima, Perú), mediodía con sol, tres cámaras de consumo, 439 imágenes con una enfermedad y 105 con dos o más [V] | No representa la Sabana, ni otra región, ni la vista del robot |
| DrBerry, análisis del agente `adquisicion-drberry` | Las 410 imágenes públicas son de un solo día (2022-09-19, 12:35–14:44). El 90 % de valid y el 86 % de test comparten ráfaga (≤10 s) con train, y hay confusión entre cámara y clase (ver `datos/resultados/ficha_drberry.md`) | Las métricas publicadas (mAP50 de 94–96 %) probablemente están infladas. Hay que medir en campo |
| PlantVillage (copia local, `README_HF.md`) | Para arándano solo trae la clase `Blueberry___healthy`, con 1.502 imágenes en la copia local. Licencia CC BY-SA 3.0 | Sirve para preentrenar, no para enfermedades de arándano. La cláusula "compartir igual" hay que revisarla antes de vender (sección 12) |
| PlantDoc (Singh et al., CoDS-COMAD 2020) | 2.598 imágenes de campo sacadas de internet, 13 especies y hasta 17 clases de enfermedad [V]. Para arándano solo tiene "Blueberry leaf" sana (carpeta local) | Lo mismo: aporta diversidad de fondo, no enfermedades de arándano |
| iNaturalist (API, 23 oct 2026, registro en `raw/campo_ood/_api/_query_log.json`) | Observaciones de grado investigación con foto bajo licencia abierta: 316 de *Erysiphe vaccinii* (oídio) y 228 de royas (*Naohidemyces* / *Pucciniastrum*) [V] | Sirven para probar casos fuera de distribución y la clase "roya", no como base de entrenamiento |
| Robot del proyecto | La cámara va a unos 0,3 m del suelo, a ~0,5 m/s de inspección (especificación de `PROMPT_simulacion_camas.md`; la altura real de la cámara del D1 está NO VERIFICADA) | La vista desde abajo y el envés de la hoja no se parecen a las fotos de celular de DrBerry |

**Conclusión para el jurado (Comprensión y Justificación).** Cualquiera puede descargar DrBerry, así que la ventaja no está en el modelo inicial. Está en el **flujo continuo de etiquetas de campo, atadas a una cama, una fecha y un resultado**, que solo se consigue operando en muchas fincas.

---

## 2. El ciclo completo (una vuelta por semana)

```
 [Red fija de sensores] --riesgo por cama (antracnosis Wilson 1990 adaptada, Bulger 1987, roya)--> [Plan de ruta]
                                                                                        |
                                                                                        v
 [Robot D1: captura + inferencia en el borde] --> lo que no tiene hallazgo se queda local (no sube)
        | sube solo: hallazgos, cola de aprendizaje activo, auditoría al azar
        v
 [Alerta agregada por tramo de cama] -> [Agrónomo: triage por foto] -> [Operario: confirma en campo]
        |                                       |                              |
        +------------- cada decisión humana = una etiqueta ---------------------+
                                        v
                     [Almacén de la finca (tenant aislado)]
                                        | solo si la finca participa, seudonimizado
                                        v
                     [Pool de la red] -> reentrenamiento mensual -> evaluación por estrato
                          -> modo sombra -> canario -> despliegue (vuelve al robot)
                          -> recalibración de los modelos de riesgo por zona (vuelve a los sensores)
```

| Paso | Quién | Qué dato produce | Dónde vive |
|---|---|---|---|
| 1. Riesgo por cama | Red de sensores y modelos de enfermedad | Riesgo diario por enfermedad y por cama | Finca, con copia agregada en la red |
| 2. Ruta priorizada | Planificador | Orden de las camas, de mayor a menor riesgo | Finca |
| 3. Captura e inferencia | Robot | Puntaje por imagen, embedding y miniatura | Robot o gateway de la finca |
| 4. Alerta por tramo | Plataforma | Evidencia agregada por tramo de 5 m (SUPUESTO) | Finca |
| 5. Triage | Agrónomo | Etiqueta L2: confirma, descarta, otra clase o "no se ve" | Finca |
| 6. Confirmación | Operario | Etiqueta L1 con vista directa (puede mirar el envés) | Finca |
| 7. Tratamiento y seguimiento | Operario y agrónomo | Qué se aplicó y cómo estaba el tramo a los 7 días | Finca (registro de incidencias) |
| 8. Pool | Plataforma | Imagen y etiqueta seudonimizadas | Red (con consentimiento) |
| 9. Reentrenamiento | Equipo de ML del vendedor | Versión nueva del modelo y su ficha | Red |
| 10. Recalibración del riesgo | Equipo de ML del vendedor | Umbrales de los modelos de clima ajustados por zona | Red |

---

## 3. Cada decisión humana es una etiqueta

### 3.1 Registro mínimo de un evento

Es el mismo registro que pide el reto ("alerta + registro"). Si se diseña bien desde la demo, sirve también para entrenar.

| Campo | Ejemplo | Por qué importa para escalar |
|---|---|---|
| `evento_id` | UUID | Trazabilidad |
| `tenant_id` | seudónimo `F-7Q2K` | Separa fincas; el nombre real vive en otra bóveda |
| `bloque / cama / tramo` | B03 / C17 / T04 | Permite etiquetas retroactivas (sección 3.3) |
| `timestamp` | 2026-10-23T07:42 | Deriva por hora, estación y fenología |
| `cultivo` (nombre científico) | *Vaccinium corymbosum* | Escalar a otros frutales sin confundir nombres comunes |
| `variedad` / `fenologia` | Biloxi / floración | Modelos por variedad y deriva por etapa |
| `zona_agroclimatica` | altitud, régimen de lluvias, campo abierto o macrotúnel | Estratos de evaluación; la Sabana es solo el primero |
| `robot_id`, `camara_id`, `calibracion_color_id` | D1-EDU-01 / cam-A / cc-2026-10-20 | Detectar deriva por cambio de equipo |
| `modelo_version` | det-arandano-v0.3 | Auditoría: qué modelo generó cada alerta |
| `clase_predicha`, `score`, `top3` | Oídio, 0,71 | Aprendizaje activo y calibración |
| `riesgo_ambiental` | oídio: alto; antracnosis: medio | Fusión sensor + imagen y recalibración del riesgo |
| `origen_muestra` | alerta / AL-incertidumbre / AL-novedad / auditoría | Separar muestras sesgadas de las aleatorias |
| `decision_agronomo` | confirma / descarta / otra clase / no se ve | Etiqueta L2 |
| `decision_operario` | confirma / descarta | Etiqueta L1 |
| `nivel_etiqueta` | L1, L2 o L3 | Peso en el entrenamiento |
| `tiempo_a_decision` | 3 h 10 min | Métrica de operación |
| `tratamiento`, `estado_7d` | aspersión dirigida; tramo sin progreso | Etiqueta de resultado: la más valiosa y la más difícil de copiar |
| `imagen_hash` | sha256 | Deduplicar y borrar a pedido |
| `nivel_participacion` | privado / red / federado | Respetar el consentimiento en cada entrenamiento |

### 3.2 Niveles de calidad de la etiqueta

| Nivel | Quién etiqueta | Fortaleza | Debilidad | Peso en el entrenamiento (SUPUESTO) |
|---|---|---|---|---|
| L0 | Modelo | Es gratis | No es una etiqueta; nunca se entrena con ella | 0 |
| L1 | Operario en campo | Ve la planta de verdad, incluido el envés | Menos formación; puede confirmar por inercia | 0,5 |
| L2 | Agrónomo, por foto y contexto | Criterio técnico | Solo ve la foto | 1,0 |
| L3 | Agrónomo senior en el panel de oro, o laboratorio | Verdad de referencia | Caro y lento | 2,0, y solo para evaluar |

Cuando L1 y L2 no coinciden, la imagen va a la cola de revisión: ese desacuerdo es justo el caso difícil que más enseña.

### 3.3 Sesgos del ciclo y cómo se corrigen

| Sesgo | Cómo aparece | Corrección |
|---|---|---|
| **Sesgo de verificación** | Solo se revisa lo que el modelo marca, así que los falsos negativos nunca se ven | Auditoría al azar de tramos que el modelo dio por sanos (sección 4.3) |
| **Fatiga o "confirmar por defecto"** | Decisiones en menos de 2 s y casi el 100 % confirmadas | Meter imágenes de oro ciegas, un 5 % de la cola (SUPUESTO), y medir el acierto de cada persona |
| **Criterios distintos entre personas** | Llega un agrónomo nuevo o cambia de finca | Medir el acuerdo de cada persona con el panel de oro y reentrenar o calibrar a la persona |
| **Una finca domina el pool** | Un exportador grande aporta el 60 % de las imágenes | Tope de peso por finca en cada lote de entrenamiento, por ejemplo 20 % (SUPUESTO) |
| **"No se ve"** | Foto borrosa, con gotas o a contraluz | Se usa para entrenar el filtro de calidad de imagen, no para la enfermedad, y nunca cuenta como "sano" |
| **El síntoma llega tarde** | Lo que hoy se ve sano estaba infectado | **Etiqueta retroactiva** (abajo) |

**La etiqueta retroactiva de "pre-síntoma" es la pieza clave de "detectar a tiempo".** Si un tramo se confirma enfermo el día *t*, las fotos del mismo tramo tomadas en los pases anteriores (*t*−7, *t*−14) pasan a ser candidatas a "pre-síntoma" y entran a la cola del agrónomo. Así el modelo aprende a ver lo que el ojo todavía no ve. Esto solo es posible con **ubicación por cama y pases repetidos**, que es una ventaja del robot frente a una app de celular con fotos sueltas.

---

## 4. Aprendizaje activo: qué imágenes pedir revisar

### 4.1 Presupuesto

- **Agrónomo:** 20 imágenes por semana y por finca, a unos 30 s cada una, o sea unos 10 minutos (SUPUESTO; ajustar con las preguntas 13 y 17 del mentor).
- **Finca nueva, semanas 1 a 4:** se triplica el presupuesto (60 por semana) y se revisan todas las alertas.
- Se revisan **en el mismo canal de la alerta** (WhatsApp o app, según la pregunta 18 del mentor), con un solo toque: Confirmar / Descartar / Otra / No se ve.

### 4.2 Cómo se llena la cola

| Criterio | Cómo se calcula | Parte del presupuesto (SUPUESTO) | Por qué |
|---|---|---|---|
| Incertidumbre | Margen pequeño entre las dos clases más probables, o puntaje cerca del umbral de la finca | 30 % (6 imágenes) | Pocas etiquetas bien elegidas rinden más que muchas al azar (Settles 2009 [V]) |
| Desacuerdo entre sensor e imagen | Riesgo ambiental alto con imagen "sana", o riesgo bajo con imagen "enferma" | 15 % (3) | Enseña al modelo visual y a la vez recalibra el modelo de riesgo |
| Novedad (fuera de distribución) | Distancia en el espacio de embeddings (open_clip ViT-B-32, ya instalado en `.venv`) al vecino más cercano del set de entrenamiento | 15 % (3) | Detecta enfermedades nuevas, cultivos nuevos y cámaras nuevas |
| Pre-síntoma retroactivo | Fotos anteriores de tramos que luego se confirmaron | 15 % (3) | Detección temprana (sección 3.3) |
| Diversidad | Un representante por grupo de embeddings (k-center) | 10 % (2) | Evita pedir 20 fotos casi iguales |
| Al azar, estratificado | Muestreo uniforme por bloque | 15 % (3) | Da estimaciones sin sesgo y sirve también como auditoría |

### 4.3 Auditoría ciega de sensibilidad (aparte de la cola)

El operario revisa en persona **10 tramos de 5 m por semana** que el robot dio por sanos, elegidos al azar (SUPUESTO; unos 15 minutos). Un foco encontrado ahí es un falso negativo que se observa directamente, y alimenta la métrica de sensibilidad (sección 9.2).

### 4.4 Etiquetas por semana (cálculo con SUPUESTOS)

| Fuente | Por semana y por finca | Comentario |
|---|---|---|
| Alertas revisadas en el triage | 30 | SUPUESTO; depende del brote y del presupuesto de falsas alarmas |
| Cola de aprendizaje activo | 20 | Sección 4.2 |
| Auditoría al azar | 20 | 10 tramos × ~2 imágenes |
| **Total** | **70** | **Unas 3.150 al año con 45 semanas activas** |

Para comparar: DrBerry, el dataset público de referencia para enfermedades de hoja de arándano, tiene 544 imágenes de una finca [V]. Los pocos datasets auxiliares que encontró el agente `adquisicion-drberry` derivan de él o son pequeños. **Una sola finca con el sistema supera eso en unas 8 semanas, y lo hace con imágenes desde la vista del robot.**

---

## 5. Qué se procesa en el robot y qué se sube

Cálculo con SUPUESTOS para una finca de 20 ha:
- Densidad de 5.250 plantas/ha, el punto medio del rango de 5.000–5.500 que cita Asocolblue [V].
- Una foto por planta y por lado.
- Inspección a 0,5 m/s y 0,75 m entre plantas, según el prompt de simulación (sin verificar en Colombia).

| Concepto | Valor | Cómo sale |
|---|---|---|
| Plantas en la finca | 105.000 | 5.250 × 20 |
| Fotos en un pase completo | ~210.000 | 2 lados por planta |
| Horas de un pase completo a 0,5 m/s | ~44 h | 78.750 m de cama / 0,5 m/s. Es solo orientativo; la capacidad real la calcula `escalabilidad/operacion/capacidad.py` |
| Fotos por semana si se recorre el 20 % de mayor riesgo | ~42.000 | Por eso la priorización por riesgo es obligatoria, no un adorno |
| Volumen bruto por semana (0,3 MB por foto, SUPUESTO) | ~12,6 GB | No cabe por la señal típica de una finca rural (pregunta 6 del mentor) |
| **Lo que sube por semana** | **~390 imágenes, unos 60 MB** | Recortes de hallazgos, cola de aprendizaje activo, auditoría y una muestra de contexto |
| Miniaturas y embeddings guardados en la finca 4 semanas (20 KB por foto) | ~3,4 GB | Hacen falta para las etiquetas retroactivas |

**Decisión de diseño.**
- La inferencia corre **en el borde**, en el robot o en un gateway de la finca conectado por wifi en la base de carga. La capacidad de cómputo a bordo del D1 está NO VERIFICADA.
- **Solo sube lo que enseña algo.** Esto es lo que vuelve escalable el costo de nube y de conectividad: el costo crece con el número de etiquetas, no con las hectáreas.

---

## 6. Reentrenamiento: centralizado frente a federado

| Dimensión | Centralizado | Federado (FedAvg; Flower) |
|---|---|---|
| Dónde quedan las imágenes | En la nube del vendedor, seudonimizadas | En la finca; solo viajan los pesos o gradientes |
| Revisar etiquetas malas | Fácil: se ven las imágenes | Difícil: no se ven los datos de la finca |
| Costo de ingeniería | Bajo | Alto: orquestación, versiones y fallas de red |
| Cómputo en la finca | Solo para inferir | Para entrenar: GPU o un equipo potente en el gateway |
| Datos distintos entre fincas (no IID) | Se mezclan y se balancean | FedAvg es robusto a datos no IID y desbalanceados, y reduce las rondas de comunicación entre 10 y 100 veces frente al SGD sincronizado [V] |
| Privacidad y confianza | Depende del contrato y de la seudonimización | Mayor: el dato no sale de la finca |
| Ley 1581 y transmisión internacional | Exige contrato con el encargado de la nube (Decreto 1377, arts. 24-25) [V] | Menor exposición, aunque los pesos podrían filtrar información (NO VERIFICADO para este caso) |
| Herramienta | Cualquier pipeline de entrenamiento | Flower, un framework de código abierto con licencia Apache-2.0 [V] |
| Encaja con | Piloto y crecimiento | Exportadores grandes con política de datos estricta |

**Recomendación por fase.**

| Fase | Fincas | Esquema | Por qué |
|---|---|---|---|
| 1. Piloto | 1–5 | **Centralizado**, con consentimiento explícito y revisión de todas las etiquetas por un agrónomo del equipo | Hace falta ver los datos para entender qué falla |
| 2. Crecimiento | 5–50 | **Centralizado con pool seudonimizado.** Las fincas que no comparten reciben el modelo y aportan solo **evaluación federada**: el modelo se mide en sus datos sin sacarlos | Mantiene el efecto de red sin excluir a nadie; medir es mucho más barato que entrenar |
| 3. Escala | 50+ o exportadores exigentes | **Federado opcional** (Flower) para ajustar las cabezas de cultivo y variedad; el backbone sigue central | Se vende como servicio premium "su dato no sale de su finca" |

**Cadencia y compuertas de publicación** (todo SUPUESTO):

| Compuerta | Regla |
|---|---|
| Frecuencia | Un reentrenamiento al mes, y uno extraordinario cuando aparece una clase nueva |
| 1. Evaluación fuera de línea | Set fijo por estrato (cultivo × zona × cámara). El recall no puede bajar más de 2 puntos en ningún estrato |
| 2. Modo sombra | Una semana en 3 fincas: corre en paralelo sin alertar, y se comparan las decisiones |
| 3. Canario | Una semana en el 10 % de las fincas, con las falsas alarmas por semana dentro del presupuesto |
| 4. Despliegue y reversión | Se revierte automáticamente si las falsas alarmas superan 1,5 veces el presupuesto dos semanas seguidas |
| Trazabilidad | Cada alerta guarda su `modelo_version` y cada versión tiene una ficha de modelo (datos, métricas por estrato, límites). Eso sirve en auditorías BPA y GlobalG.A.P. |

---

## 7. Un modelo, muchas fincas: modelos por cultivo, región y variedad

| Nivel | Qué se entrena | Cuándo se crea | Datos |
|---|---|---|---|
| **Backbone visual compartido** | Extractor de rasgos de hoja, flor y fruto | Desde el día 1 | Todas las fincas y cultivos del pool, más los datasets públicos (DrBerry y PlantDoc, CC BY 4.0; PlantVillage, CC BY-SA 3.0, revisar) |
| **Cabeza por cultivo** | Clases de cada cultivo: arándano primero; después fresa, mora, frambuesa, uchuva, etc. | Al vender el primer cliente de ese cultivo, después de una campaña de datos semilla de 2 a 4 semanas (SUPUESTO) | La taxonomía usa el nombre científico del patógeno, así "oídio" no significa lo mismo en dos cultivos |
| **Adaptador por zona agroclimática o variedad** | Ajuste fino pequeño | Solo si el estrato tiene **300 o más etiquetas confirmadas por clase** y el modelo general rinde **5 o más puntos peor** ahí (SUPUESTO) | Estrato con datos suficientes |
| **Calibración por finca** | Umbral y prior de riesgo ambiental | Siempre, en el onboarding | Etiquetas de esa finca |

**Por qué no un modelo por finca.**
- Fragmenta los datos, que es lo contrario del efecto de red.
- Multiplica el mantenimiento: N modelos por M versiones.
- Una finca sola no tiene datos ni para medirse (sección 9.2).
- Lo que sí cambia por finca es **el umbral**, porque cada productor tolera un número distinto de falsas alarmas (pregunta 28 del mentor).

**Fusión entre sensor e imagen.**
- La probabilidad final de que un tramo esté enfermo combina el puntaje visual con el riesgo ambiental de ese día, mediante una regresión logística por zona entrenada con las confirmaciones.
- Esa misma regresión es la que **recalibra por zona** los modelos de clima (antracnosis: Wilson 1990 adaptado a arándano, no Miles 2013 [verificación técnica 2026-10-23]; Bulger 1987 para Botrytis y la regla de roya).
- Así, la red de sensores y la cámara aprenden juntas.

**Onboarding de una finca nueva (arranque en frío)**

| Semana | Qué pasa | Etiquetas |
|---|---|---|
| 0 | Se cargan los metadatos: cultivo, variedades, mapa de bloques y camas, zona. La cámara se calibra con una carta de color fija en la base de carga | 0 |
| 1–2 | Modelo base de la red con umbral conservador. Se revisan todas las alertas y el presupuesto de aprendizaje activo se triplica | ~100 por semana |
| 3–4 | Se calibra el umbral para cumplir el presupuesto de falsas alarmas acordado y se ajusta el prior de riesgo de la zona | ~100 por semana |
| 5 en adelante | Operación normal | ~70 por semana |

**Cultivo nuevo.** El zero-shot con CLIP sirve solo como triage de "algo raro" y nunca como diagnóstico. Hace falta una campaña de datos semilla con agrónomo antes de prometer detección.

---

## 8. Control de deriva

La deriva se mide **por estrato** (cultivo × zona × cámara × variedad), no en el promedio global, porque el promedio la esconde.

| Fuente de deriva | Ejemplo | Señal automática | Umbral (SUPUESTO) | Acción |
|---|---|---|---|---|
| Cambio de cámara o robot | Paso del D1 EDU al D1 Ultra, lente nuevo, firmware | Color de la carta en la base fuera de tolerancia; salto en la distancia media de embeddings | ΔE de color > 5; distancia > p95 histórico | Abrir un estrato nuevo, dos semanas en sombra y recalibrar color |
| Lente sucio, rocío o gotas | El robot pasa justo después del rocío o cerca del aspersor | Baja la nitidez (varianza del Laplaciano); sube la tasa de "no se ve" | "No se ve" > 10 % por pase | Aviso de mantenimiento; esas fotos no cuentan como negativo |
| Luz y clima | Nublado frente a sol, hora del día | Histograma de brillo; índice de estabilidad (PSI) de la distribución de puntajes | PSI > 0,2 (regla práctica de la industria, NO VERIFICADO) | Priorizar aprendizaje activo en ese estrato |
| Fenología y estación | Brotación, floración, cosecha; senescencia confundida con enfermedad | Tasa de positivos por clase frente al mismo periodo anterior; sube la tasa de descartes | Descartes +50 % mes a mes | Revisar con el agrónomo y agregar ejemplos de la etapa |
| Variedad nueva | La finca siembra otra variedad | Metadato; desempeño por variedad | Recall por variedad < general − 5 puntos | Adaptador de variedad si hay datos (sección 7) |
| Enfermedad o plaga nueva | Aparece roya donde no había | Sube "otra clase" y sube la novedad (OOD) en una zona | 3 o más "otra" confirmadas por zona y mes | Protocolo de clase nueva y aviso al productor (sección 12, ICA) |
| Deriva del etiquetado | Cambia el agrónomo o cambia el criterio | Acuerdo con el panel de oro | < 85 % | Recalibrar a la persona; revisar sus etiquetas recientes |
| Deriva del modelo de riesgo | El clima "alto" ya no anticipa casos | Tasa de confirmación en camas de riesgo alto frente a bajo | Razón < 1,5 | Recalibrar la regresión de riesgo de la zona |

---

## 9. Métricas de operación

| # | Métrica | Definición | Frecuencia | Meta inicial (SUPUESTO) | Quién la ve |
|---|---|---|---|---|---|
| 1 | **Falsas alarmas al agrónomo por semana y por finca** | Alertas descartadas en el triage por foto | Semanal | ≤ 15 | Agrónomo |
| 2 | **Falsas alarmas al operario por semana y por finca** | Alertas que el agrónomo envió a campo y el operario descartó | Semanal | ≤ 3 (lo fija la pregunta 28 del mentor) | Productor y operario |
| 3 | Precisión de la alerta | Confirmadas / enviadas | Semanal | ≥ 50 % al inicio | Agrónomo |
| 4 | **Sensibilidad estimada** | Focos detectados / (detectados + escapados). Los escapados se encuentran en la auditoría o los hallan humanos en tramos que el robot dio por sanos en los 7 días anteriores | Mensual, por estrato y con intervalo de confianza | ≥ 80 % | Productor y vendedor |
| 5 | Días a detección | Fecha de la alerta − fecha estimada del primer síntoma (retroactiva) | Mensual | Bajar mes a mes | Productor |
| 6 | Cobertura | Tramos inspeccionados / tramos planificados por riesgo | Semanal | ≥ 90 % | Operación |
| 7 | Tiempo a decisión | Alerta → triage → campo | Semanal | Mediana < 24 h | Agrónomo |
| 8 | Tasa de "no se ve" | Calidad de imagen | Por pase | < 10 % | Mantenimiento |
| 9 | Etiquetas útiles y cola respondida | Etiquetas L1/L2 y % de la cola de aprendizaje activo respondida | Semanal | ≥ 80 % respondida | Vendedor |
| 10 | Deriva | PSI de puntajes y distancia de embeddings por estrato | Semanal | Sección 8 | Vendedor |
| 11 | Acuerdo con el panel de oro | Por persona que etiqueta | Mensual | ≥ 85 % | Vendedor |

### 9.1 El presupuesto de falsas alarmas obliga a agregar la evidencia

Con 42.000 fotos por semana (sección 5) y un presupuesto de 5 falsas alarmas por semana, cada foto suelta tendría que equivocarse menos de **1,2 veces en 10.000** (5 / 42.000). En un pase completo (210.000 fotos) con presupuesto de 3, haría falta menos de **1,4 veces en 100.000** (cálculo).

[Verificación técnica 2026-10-23] Las 42.000 fotos suponen recorrer el 20 % de las camas por semana. La política que usa `operacion.md` (30 % de camas en riesgo alto cada semana y el resto cada 14 días) equivale a 0,65 visitas por cama y semana, o sea ~136.500 fotos/semana con una foto por planta y lado, y `arquitectura.md` §7.3 supone 2 cuadros por metro y lado (~61.000 por día). Con 136.500 fotos, el error por foto tendría que ser menor de 3,7 en 100.000. La conclusión no cambia y se refuerza: la alerta tiene que agregarse por tramo.

Que un clasificador de hojas alcance esa tasa por foto en campo es NO VERIFICADO y poco realista. Por eso:
- La alerta se emite **por tramo o foco**, no por foto. Exige 2 o más detecciones en un tramo de 5 m, o persistencia en 2 pases, ponderado por el riesgo ambiental (SUPUESTO).
- El **agrónomo filtra por foto antes** de mover al operario. La falsa alarma que más cuesta es la que saca a una persona al campo.
- **El umbral de cada finca se ajusta solo** para cumplir el presupuesto acordado.
- Bajar las falsas alarmas sube los falsos negativos. Por eso **siempre se reporta el par**: falsas alarmas por semana junto con la sensibilidad estimada.

### 9.2 Sensibilidad con intervalo de confianza (Wilson 95 %, cálculo)

| Escenario | Detectados / focos totales | Sensibilidad | IC 95 % |
|---|---|---|---|
| 1 finca, 1 mes | 8 / 9 | 89 % | **57 %–98 %**: no sirve para decidir |
| 1 finca, 1 temporada | 46 / 52 | 88 % | 77 %–95 % |
| Red de 30 fincas, 1 mes | 920 / 1.040 | 88 % | **86 %–90 %** |

Para conocer la sensibilidad con ±10 puntos hacen falta unos 96 focos en el peor caso (p = 0,5), o unos 62 si p ≈ 0,8 (cálculo: n = z²·p(1−p)/0,1²). **Una finca sola tarda una temporada en juntarlos; la red los junta en semanas.** Ese es un argumento de venta: "sensibilidad medida en N fincas de su zona y su cultivo".

---

## 10. Gobierno y propiedad de los datos entre productores

**Principio:** *los datos son del productor; el modelo es de la red; el productor decide si su dato entra a la red.* Esto sigue la idea del "originador del dato" del Código de Conducta de la UE para compartir datos agrícolas. Ese código lo lanzaron en Bruselas, el 23 de abril de 2018, Copa-Cogeca, CEMA y otras organizaciones; no es vinculante y da al originador el control sobre el acceso y el uso [V]. También sigue los "Core Principles" de Ag Data Transparent de EE. UU., que tratan la propiedad y la portabilidad; su texto revisado de 2024 está NO VERIFICADO porque no lo abrí.

### 10.1 Categorías de datos

| Dato | Ejemplo | Dueño | Régimen | ¿Entra al pool? | Retención (SUPUESTO) |
|---|---|---|---|---|---|
| Imágenes de hoja o planta sin personas | Recorte de una lesión | Productor | Contrato y secreto empresarial | Solo si la finca participa, seudonimizado | Mientras dure el contrato; borrado a pedido |
| Etiquetas y decisiones agronómicas | "Oídio confirmado, T04" | Productor | Contrato y secreto empresarial | Igual que las imágenes | Igual |
| Ubicación exacta (GPS de la cama) | Coordenadas | Productor | Contrato. Si el productor es persona natural, también Ley 1581 | **Nunca**; en el pool queda solo la zona agroclimática y el municipio | Solo en el tenant |
| Clima de los sensores | HR, temperatura, horas de hoja mojada | Productor | Contrato | Sí, agregado por zona, para recalibrar el riesgo | 5 años (series para los modelos) |
| Rendimiento, costos y pérdidas | kg/ha, gasto en fungicida | Productor | **Secreto empresarial** | **Nunca**; solo comparativos agregados con k ≥ 5 | Solo en el tenant |
| Datos de usuarios | Nombre, celular, rol, quién confirmó | Cada persona (titular) | **Ley 1581** | No | Mientras la cuenta esté activa |
| Personas que salen en una foto por accidente | Un operario en el cuadro | Cada persona (titular) | **Ley 1581**; si se usara para identificar, sería dato biométrico, o sea sensible | No: se descarta o se difumina en el robot | 0 |
| Modelo entrenado | Pesos v0.3 | Vendedor | Propiedad intelectual del vendedor | No aplica | Versionado |

### 10.2 Niveles de participación (cómo se vende)

| Nivel | Qué aporta el productor | Qué recibe | Precio (SUPUESTO) |
|---|---|---|---|
| **Privado** | Nada sale de su tenant. Solo métricas anónimas de uso | El modelo de la red y su calibración propia | Tarifa completa |
| **Red** (recomendado por defecto, con opción de salir) | Imágenes y etiquetas seudonimizadas al pool | Modelo de la red, alertas regionales de riesgo y benchmark de su zona | Descuento por aportar datos |
| **Federado** | Entrena dentro de su infraestructura (fase 3) | Lo mismo que Red, sin que el dato salga | Premium |

### 10.3 Cláusulas mínimas del contrato

1. **Finalidad cerrada.** Los datos solo se usan para detectar, alertar, registrar y mejorar el modelo. Nunca se venden ni se ceden datos de una finca individual a terceros (casas de insumos, compradores, aseguradoras, bancos) sin un consentimiento escrito aparte.
2. **Portabilidad.** El productor puede exportar en cualquier momento su historial por cama: CSV, GeoJSON e imágenes.
3. **Salida.** Al terminar el contrato se borran sus imágenes y etiquetas del pool, y **ya no participan en el siguiente reentrenamiento mensual**. Límite honesto: no se "desaprende" de inmediato lo que ya está en los pesos de versiones anteriores. Se reemplaza con la siguiente versión.
4. **Confidencialidad, cifrado y registro de accesos.** Forman parte de las "medidas razonables" que el productor necesita para conservar la protección de su secreto empresarial (sección 12).
5. **Alertas regionales sin delatar a nadie.** Un aviso del tipo "sube la roya en su zona" solo se emite si hay 5 o más fincas en la zona y ninguna aporta más del 50 % de los casos (SUPUESTO).
6. **Comité de datos.** Cada trimestre se reúnen representantes de los productores y se publica un informe de transparencia: qué se entrenó, con cuántas fincas y qué cambió.

### 10.4 Quién ve qué

| Rol | Ve |
|---|---|
| Productor o administrador | Todo lo de su finca |
| Agrónomo | Alertas, imágenes y métricas de las fincas que atiende |
| Operario | Sus alertas asignadas |
| Equipo de ML del vendedor | El pool seudonimizado; el tenant identificado solo con un ticket de soporte autorizado |
| Otros productores | Solo agregados con k ≥ 5 |
| Terceros | Nada sin un consentimiento aparte |

---

## 11. Anonimización y seudonimización

| Dato | Técnica | Dónde se aplica | Riesgo residual |
|---|---|---|---|
| Nombre de la finca o del productor | Seudónimo por tenant; la tabla de correspondencia vive en una bóveda separada | Plataforma | Bajo |
| GPS de la cama | Se generaliza a zona agroclimática y municipio en el pool | Al exportar al pool | Medio, si la zona tiene pocas fincas (por eso k ≥ 5) |
| EXIF de las imágenes (GPS, número de serie) | Se elimina | En el robot, antes de subir | Bajo |
| Personas en la imagen | Detector de personas en el borde: se descarta el cuadro o se difumina. **Nunca reconocimiento facial** | En el robot | Bajo; además se evita el dato biométrico, que es sensible (Ley 1581, art. 5) |
| Fechas exactas | En el pool, semana ISO | Al exportar | Bajo |
| Combinaciones raras (variedad poco común + zona + semana) | Supresión o generalización si el grupo tiene menos de 5 fincas | Al exportar | Medio |
| Rendimientos y costos | No salen del tenant | No aplica | Nulo |
| Quién etiquetó | ID de rol en el pool; el nombre solo en el tenant | Al exportar | Bajo |

---

## 12. Marco legal colombiano

Este resumen no reemplaza una revisión de un abogado antes de vender.

| Norma | Qué dice | Qué nos aplica | Cómo cumplimos |
|---|---|---|---|
| Ley 1581 de 2012, art. 3 [V] | Dato personal es "cualquier información vinculada o que pueda asociarse a una o varias personas naturales determinadas o determinables". También define responsable, encargado y autorización | Usuarios, operarios, productores que son personas naturales (los datos de su finca pueden asociarse a ellos) y personas que salen en fotos | Inventario de bases de datos personales separado de los datos agronómicos |
| Ley 1581, art. 4 [V] | Principios de legalidad, finalidad, libertad, veracidad, transparencia, acceso y circulación restringida, seguridad y confidencialidad | Todo el tratamiento | Finalidad cerrada en el contrato; cifrado; registro de accesos |
| Ley 1581, art. 5 [V] | Son datos sensibles, entre otros, los de salud, vida sexual y **los biométricos** | El reconocimiento facial de operarios sería biométrico | No se identifica a nadie; las personas se difuminan o se descartan en el robot |
| Ley 1581, art. 9 [V] | Hace falta autorización previa e informada del titular, obtenida por un medio que se pueda consultar después | Registro de usuarios y número de WhatsApp | Aceptación en el onboarding de la app o del canal, guardada con fecha y versión de la política |
| Decreto 1377 de 2013, art. 13 [V] | Contenido mínimo de la política de tratamiento: identidad del responsable, finalidad, derechos, área de atención, procedimiento y vigencia | El vendedor como responsable de las cuentas | Publicar la política antes del piloto |
| Decreto 1377, arts. 24-25 [V] | La transmisión al encargado, dentro o fuera del país, no necesita consentimiento del titular si hay un contrato que fije el alcance, la seguridad y la confidencialidad | Productor (responsable de sus trabajadores) → vendedor (encargado); vendedor → proveedor de nube (encargado) | Contrato de transmisión con cada productor y con la nube |
| Ley 1581, art. 26, y Circular Externa 005 de 2017 de la SIC | Se prohíbe transferir datos a países sin nivel adecuado de protección, salvo excepciones [V]. La circular publicó una lista de 36 países con nivel adecuado, que incluye EE. UU. [V] | Servidores en la nube fuera de Colombia | Elegir una región de nube en un país de la lista vigente y verificar la lista actual de la SIC (puede haber cambiado; NO VERIFICADO a 2026) |
| Ley 1581, art. 25, y Decreto 090 de 2018 | Registro Nacional de Bases de Datos ante la SIC [V]. Están obligadas las sociedades con activos totales de más de 100.000 UVT [V, resumen de Brigard Urrutia] | Es probable que la empresa vendedora no esté obligada al inicio; los productores grandes sí pueden estarlo | Revisar el umbral cada año; los demás deberes aplican igual |
| Ley 1581, art. 23 [V] | La SIC puede imponer multas de hasta 2.000 salarios mínimos mensuales | Riesgo de incumplir | Cumplir los puntos anteriores |
| Decisión Andina 486, art. 260 [V, vía Tribunal Andino 508-IP-2016] | Es secreto empresarial la información no divulgada que tiene valor comercial por ser secreta y cuyo poseedor tomó **medidas razonables** para mantenerla así | Mapas de enfermedad, rendimientos, costos, historial de tratamientos | El contrato y los controles técnicos son parte de esas "medidas razonables" |
| Decisión 486, art. 265 [V, misma fuente] | Quien accede a un secreto por su trabajo o por una relación de negocios, y fue advertido de que es confidencial, debe abstenerse de usarlo o revelarlo | Empleados y contratistas del vendedor | Acuerdos de confidencialidad y acceso por roles |
| Ley 256 de 1996, art. 16 [V] | Es competencia desleal divulgar o explotar sin autorización secretos empresariales a los que se accedió con deber de reserva | Uso indebido de los datos de una finca para favorecer a otra | Agregados con k ≥ 5 y finalidad cerrada |
| Resolución ICA 30021 de 2017 | Requisitos de la certificación en Buenas Prácticas Agrícolas (BPA) (solo por búsqueda, NO VERIFICADO en el texto) | El registro de incidencias puede alimentar los registros BPA y GlobalG.A.P. | Los requisitos exactos de registro de monitoreo están NO VERIFICADOS; hay que confirmarlos con el mentor (pregunta 27) |
| Plagas de control oficial (ICA) | La obligación de reportar es del productor; el alcance exacto está NO VERIFICADO | Si el sistema sugiere una plaga cuarentenaria, por ejemplo roya en una zona nueva | Protocolo pactado: la plataforma avisa al productor y al agrónomo, y no reporta a nombre de nadie sin contrato |
| Licencias de datos y software para un producto que se vende | DrBerry y PlantDoc tienen licencia CC BY 4.0 (exigen atribución) [V]. PlantVillage tiene CC BY-SA 3.0 (`README_HF.md` local). Ultralytics es AGPL-3.0 (`reportes/preparacion-entorno.md`) | Un modelo comercial cerrado | Atribución. Revisar si la cláusula "compartir igual" de PlantVillage afecta los pesos. Comprar la licencia comercial de Ultralytics o usar una arquitectura Apache o MIT antes de vender (NO VERIFICADO) |

---

## 13. El efecto de red como ventaja competitiva

### 13.1 Cuatro ruedas que se alimentan con cada finca

| Rueda | Cómo gira | Qué gana el productor número N+1 |
|---|---|---|
| **1. Visual** | Más fincas → más etiquetas de más condiciones (cámaras, luz, variedades, zonas) → menos falsas alarmas con la misma sensibilidad → más adopción | Un modelo que ya vio su zona y su variedad antes de que él llegue |
| **2. Riesgo calibrado** | Las confirmaciones de campo de muchas fincas recalibran por zona los modelos de clima (Wilson adaptado, Bulger, roya) → mejor priorización de camas → el robot rinde más por hora | Una ruta que empieza por las camas correctas desde la primera semana |
| **3. Medición** | Solo una red junta los focos suficientes para conocer la sensibilidad con ±2 puntos (sección 9.2) | Una garantía de desempeño medida, no prometida |
| **4. Alerta temprana regional** | Sube la tasa de confirmaciones de una enfermedad en una zona → aviso a las fincas de la zona, con k ≥ 5 | Días de ventaja antes de que el brote llegue a su finca |

### 13.2 Frente a las alternativas

| Alternativa | ¿Genera etiquetas de enfermedad por cama? | ¿Aprende de muchas fincas? | Nuestra diferencia |
|---|---|---|---|
| Saga Thorvald (trata oídio con UV-C, se vende como servicio) | No: trata sin diagnosticar, según el contexto del equipo | Su producto no aprende el diagnóstico | Diagnosticamos y registramos; podemos complementar, por ejemplo con UV-C solo en los tramos confirmados |
| Estaciones tipo Pessl o Metos con modelos de enfermedad | No: tienen el clima pero no la verdad de campo cama por cama | Sus modelos son genéricos | Nuestras confirmaciones recalibran el riesgo por zona (rueda 2) |
| Apps de celular tipo DrBerry | Fotos sueltas, sin cama ni pases repetidos | Poco: sin ubicación ni seguimiento | Etiquetas retroactivas de pre-síntoma y resultado del tratamiento a 7 días |
| Monitoreo manual | Hay criterio, pero queda en papel | No | El mismo criterio humano, convertido en datos que se acumulan |

### 13.3 Curva ilustrativa (no es una predicción)

Hestness et al. (2017) muestran que el error de generalización baja como una ley de potencia del tamaño del dataset [V]. Con un exponente ilustrativo de 0,3 (SUPUESTO; el exponente real depende de la tarea y se mide en el piloto):

| Fincas en la red | Etiquetas por año (cálculo, 3.150 por finca) | Error relativo frente a 1 finca |
|---|---|---|
| 1 | 3.150 | 1,00 |
| 10 | 31.500 | 0,50 |
| 50 | 157.500 | 0,31 |
| 200 | 630.000 | 0,20 |

**Lectura honesta (Justificación):**
- Los rendimientos son decrecientes: pasar de 1 a 10 fincas vale más que pasar de 50 a 200.
- Casado y Lauten (a16z, 2019) advierten que el valor de cada dato adicional baja mientras el costo de conseguir datos únicos sube [V]. El volumen por sí solo no es un foso.
- **Nuestro foso real es la combinación de cuatro cosas:**
  1. Etiquetas atadas a cama, fecha y resultado.
  2. Modelos de riesgo calibrados por zona.
  3. Integración con el registro diario de la finca: el historial por cama es costoso de abandonar.
  4. Cobertura de varios cultivos con un backbone compartido.

### 13.4 Efectos de red negativos y cómo se mitigan

| Riesgo | Mitigación |
|---|---|
| Una finca con etiquetas malas contamina el pool | Panel de oro, acuerdo por persona y tope de peso por finca |
| Polizones: fincas que reciben el modelo sin aportar | Precio diferencial por nivel (sección 10.2) |
| Desconfianza: "mi dato ayuda a mi vecino competidor" | Agregados con k ≥ 5, sin datos de rendimiento en el pool, comité de datos y opción federada |
| Concentración: un exportador grande sesga el modelo hacia su zona | Evaluación y compuertas por estrato, y tope de peso |
| Arranque en frío en cada cultivo y región nuevos | Campaña de datos semilla y venta "por ola" por zona, no fincas aisladas |

---

## 14. Qué mostrar en la demo

Ayuda a los criterios de Pertinencia y Comprensión, y a los 25 puntos de demo:
1. **Pantalla de triage** con cuatro botones (Confirmar / Descartar / Otra / No se ve) y un contador de "etiquetas de esta semana".
2. **Cola de aprendizaje activo** de 20 imágenes, cada una con su motivo: "incierta", "nueva", "pre-síntoma", "al azar".
3. **Panel de la finca**: falsas alarmas por semana frente al presupuesto, sensibilidad estimada con su intervalo y semáforo de deriva.
4. **Diapositiva del efecto de red**: "1 finca: 57–98 %; 30 fincas: 86–90 %".
5. **Sugerencia al equipo de simulación** (`PROMPT_simulacion_camas.md`): agregar a la salida batch dos métricas, "etiquetas generadas" y "falsas alarmas al operario por semana". Así el ciclo de datos también produce evidencia medible.

---

## 15. Preguntas del mentor que cambian este diseño

| Pregunta (PDF del mentor) | Qué parámetro cambia |
|---|---|
| 6. Señal de celular o wifi en los bloques | Qué se sube y cuándo (sección 5) |
| 13. Personas por hectárea y por rol | Presupuesto de aprendizaje activo y de auditoría |
| 16–18. Formación, uso de celular y canal de la alerta | Interfaz de etiquetado y niveles L1/L2 |
| 17. Quién recibe y quién confirma | Peso de cada nivel de etiqueta |
| 20. Cada cuánto se revisa la misma cama | Ventana de las etiquetas retroactivas |
| 22 y 26. Días entre síntoma y detección; qué es "a tiempo" | Meta de la métrica "días a detección" |
| 27. Cómo registran (ICA, BPA, GlobalG.A.P.) | Esquema del evento (sección 3.1) |
| **28. Cuántas falsas alarmas por semana tolerarían** | **Presupuesto de falsas alarmas y umbral por finca** |

---

## 16. Fuentes

Las URL marcadas como abiertas las abrí en esta sesión (23 de octubre de 2026). Las marcadas "por búsqueda" se confirmaron solo con resultados del buscador.

| # | Fuente | Qué se tomó | Estado |
|---|---|---|---|
| 1 | Mohanty, Hughes y Salathé (2016), *Frontiers in Plant Science* 7:1419. https://pmc.ncbi.nlm.nih.gov/articles/PMC5032846 (DOI 10.3389/fpls.2016.01419) | 99,35 % en el test del mismo dataset; 31,40 % (dataset 1) y 31,69 % (dataset 2) en imágenes de otras fuentes; 54.306 imágenes, 14 cultivos, 26 enfermedades | Abierto |
| 2 | Morales, Cavero y Ugarte (2023), DrBerry, KDIR 2023, DOI 10.5220/0012207100003598. Copia local en `datos/raw/drberry_paper/122071.pdf` | Una finca en Perú, sol a mediodía, 3 cámaras, 439 + 105 imágenes, precisión 84 % y recall 91 % | Abierto (PDF local) |
| 3 | DrBerry en Roboflow, https://universe.roboflow.com/drberry/drberry-original-data/dataset/1, y la ficha `datos/resultados/ficha_drberry.md` | 410 imágenes, CC BY 4.0, un solo día de captura, fuga entre splits | Archivos locales del agente `adquisicion-drberry` |
| 4 | PlantDoc, Singh et al. (2020), https://arxiv.org/abs/1911.10317 (README local) | 2.598 imágenes, 13 especies, hasta 17 clases; arándano solo sano; CC BY 4.0 | Abierto (local) |
| 5 | PlantVillage, `datos/raw/plantvillage/PlantVillage-Dataset/README_HF.md` | Arándano solo `Blueberry___healthy`; licencia CC BY-SA 3.0; 1.502 imágenes locales | Abierto (local) |
| 6 | API de iNaturalist (URLs en `datos/raw/campo_ood/_api/_query_log.json`) | 316 observaciones de *Erysiphe vaccinii* y 228 de royas | Abierto (registro local) |
| 7 | McMahan et al. (2017), FedAvg, AISTATS. https://arxiv.org/abs/1602.05629 | Robustez a datos no IID; de 10 a 100 veces menos rondas | Abierto |
| 8 | Flower, https://github.com/flwrlabs/flower | Framework federado, Apache-2.0 | Abierto |
| 9 | Settles (2009), *Active Learning Literature Survey*, TR 1648, UW-Madison. https://bibbase.org/network/publication/settles-activelearningliteraturesurvey-2009 (PDF: https://research.cs.wisc.edu/techreports/2009/TR1648.pdf) | Más exactitud con menos etiquetas cuando el algoritmo elige qué etiquetar | Abierta la ficha; PDF no abierto |
| 10 | Hestness et al. (2017), *Deep Learning Scaling is Predictable, Empirically*. https://arxiv.org/abs/1712.00409 | El error baja como ley de potencia de los datos | Abierto |
| 11 | Casado y Lauten (2019), *The Empty Promise of Data Moats*, a16z. https://a16z.com/2019/05/09/data-network-effects-moats/ | Rendimientos decrecientes de los datos | Abierto |
| 12 | Código de Conducta de la UE para compartir datos agrícolas (2018). https://www.cema-agri.org/publication/news/46-code-of-conduct-on-agricultural-data-sharing-sets-the-scene-for-digital-farming | 23 de abril de 2018 en Bruselas; nueve firmantes iniciales; el originador decide quién accede; no vinculante (según búsqueda) | Abierto |
| 13 | Ag Data Transparent, Core Principles. https://www.precisionfarmingdealer.com/blogs/1-from-the-virtual-terminal/post/5953-updating-the-core-principles-for-ag-data | Propiedad y portabilidad | NO VERIFICADO (texto de 2024 no abierto) |
| 14 | Ley 1581 de 2012. https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=49981 | Arts. 2, 3, 4, 5, 9, 23, 25 y 26 | Abierto |
| 15 | Decreto 1377 de 2013. https://www.alcaldiabogota.gov.co/sisjurMantenimiento/normas/Norma1.jsp?i=53646 | Arts. 3, 6, 13, 24 y 25 | Abierto |
| 16 | Decreto 090 de 2018 (umbral del RNBD), resumen de Brigard Urrutia. https://www.bu.com.co/es/insights/noticias/empresas-bajo-la-lupa-de-la-sic-para-el-registro-de-bases-de-datos | 100.000 UVT | Abierto (fuente secundaria) |
| 17 | Circular Externa 005 de 2017 de la SIC, análisis de Holland & Knight. https://www.hklaw.com/en/insights/publications/2017/08/cambios-en-la-transferencia-de-datos-personales-a | 36 países, incluido EE. UU. | Abierto (fuente secundaria) |
| 18 | Decisión 486, arts. 260 y 265, vía la Interpretación Prejudicial 508-IP-2016. https://www.wipo.int/wipolex/es/text/583330 | Requisitos del secreto empresarial; deber de reserva | Abierto |
| 19 | Ley 256 de 1996, art. 16. http://colombia.justia.com/nacionales/leyes/ley-256-de-1996/gdoc/ | Violación de secretos como competencia desleal | Abierto |
| 20 | Resolución ICA 30021 de 2017. https://normograma.invima.gov.co/normograma/docs/pdf/resolucion_ica_30021_2017.pdf | Certificación BPA | Por búsqueda |
| 21 | Densidad de siembra según Asocolblue, Agronegocios (14 sep 2022). https://www.agronegocios.co/agricultura/las-exportaciones-de-arandanos-superaron-us-1-millon-durante-el-primer-semestre-3446716 | 5.000–5.500 plantas/ha | Abierto |
| 22 | Archivos del equipo: `PROMPT_simulacion_camas.md`, `Preguntas_mentor_BerryGoodIdea.pdf`, `datos/reportes/preparacion-entorno.md` y `datos/escalabilidad/operacion/capacidad.py` | Especificaciones del robot y la simulación, preguntas del mentor, licencias del entorno, capacidad | Abiertos (locales) |
