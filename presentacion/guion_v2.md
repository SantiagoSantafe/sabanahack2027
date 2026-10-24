# Guion v2 · Berry Good Idea (Sabana Hack 2026)

Pitch de 5 min (300 s) con demo en vivo, 11 diapositivas. Variantes de 3 y 9 min en la sección 1. Hilo: **"Una noche en la finca" → "De 5 días a 5 minutos"**. Cifras: la fuente única es `CIFRAS_CLAVE.md`; lo que no está ahí cita su archivo o va marcado SUPUESTO / NO VERIFICADO. La numeración coincide con el mapa del deck de `presentacion/prompts_imagenes.md` (IMG-1 a IMG-9); **los tiempos de este guion mandan**. Rutas desde `/Users/santiagosantafe/Downloads/SabanaHack/`.

---

## 0. Reglas de diseño y control de afirmaciones

**Diseño (estilo Canva del equipo).**
- Portada y diapositivas con video: fondo verde bosque muy oscuro, hojas/robot, ondas verde lima, texto blanco en negrita.
- Diapositivas de datos: fondo blanco, título en MAYÚSCULAS verde oscuro, tarjetas verde claro / verde oscuro con cifra grande (≥ 80 pt) y etiqueta de ≤ 6 palabras.
- Máximo 3 elementos visibles por diapositiva. Todo lo demás va a las notas. La frase de limitaciones (diap. 7) es la única excepción y va como pie.
- Videos de fondo: sin audio, en bucle, oscurecidos 50–60 % para que el texto blanco se lea; cada uno con un fotograma fijo de respaldo (por si se exporta a PDF).
- Cifras en porcentaje siempre que se pueda; el n va en la etiqueta o en las notas, nunca se oculta.

**Lo que NO se dice (la rúbrica castiga ocultar límites y el jurado de negocios hace la cuenta):**
1. No decir "sensibilidad 80 %" ni "especificidad 95 %" (son del modelo anterior, imagen limpia). El modelo en uso es `modelo_camara`: 78 % y 29 % de falsas alarmas.
2. No mostrar "87/87 con 0/14 falsas alarmas" (recortes; alternaria se separa solo por tamaño).
3. **"5 minutos" es un objetivo de latencia, no una medición.** Significa "de que el robot ve la hoja a que el supervisor ve la alerta". "5 días" es lo que tarda una persona en revisar 12–15 bloques en papel (mentor), no el retraso en detectar un foco (el mentor no respondió esa pregunta). Medir con cronómetro en el ensayo (5 repeticiones) y, si sale distinto, cambiar la frase por el número medido.
4. No decir "detectamos 5 días antes": no hay medición de adelanto.
5. En la demo, **T y HR son simuladas** (no hay sensor físico; el sensor está en el BOM) y el enlace es Wi-Fi local, no LoRaWAN. Decirlo en voz alta, igual que todo lo teleoperado.
6. El riesgo ambiental (Botrytis con Bulger 1987 de fresa como proxy; antracnosis con Wilson 1990 + aproximación de Gillett y Schilder 2009) **no está validado contra enfermedad real**. Botrytis y roya no tienen clase visual: solo las cubre la capa ambiental.
7. Los puntos de pérdida evitados son SUPUESTO; AGRAR ya tiene un modelo predictivo en el PLC, así que parte de la mejora ya la captura la red.
8. Supervisor → operario es nuestro diseño; el mentor no confirmó el canal real ni si sirve el triage (`RESPUESTAS_MENTOR.md` §9). Decir "así lo diseñamos y lo validamos en el piloto".
9. No usar el documento del equipo en Claude Docs como fuente de cifras: aún no tiene las correcciones (HANDOFF §5).

---

## 1. Mapa de tiempos

| # | Slug | 5 min (s) | 3 min (s) | 9 min (s) | Si son 3 min | Si son 9 min |
|---|---|---|---|---|---|---|
| 1 | portada | 5 | 3 | 8 | Se queda | Se queda |
| 2 | gancho-2am | 18 | 10 | 25 | ACORTAR a una frase | AMPLIAR: Botrytis (la más común, humedad alta sostenida) |
| 3 | problema | 22 | 12 | 40 | ACORTAR a 2 cifras | AMPLIAR: 40 bloques = 10,7–16,7 jornadas; 30–40 % sin prevención |
| 4 | misma-noche | 28 | 17 | 40 | ACORTAR (sin la rama "sana") | AMPLIAR: por qué prioriza (riesgo PLC), qué viaja por LoRaWAN |
| 5 | demo-vivo | 95 | 60 | 150 | Una hoja sana + una enferma | AMPLIAR: 2.ª ronda con hojas que elige el jurado + cierre del foco |
| 6 | supervisor-registro | 17 | **CORTAR** | 35 | Se cuenta en el último gesto de la demo | AMPLIAR: vista cenital, cobertura y puntos ciegos |
| 7 | evidencia | 27 | 20 | 55 | Se queda; mantener pie de límites | AMPLIAR: matriz de confusión, 410 hojas, prueba fuera del dataset |
| 8 | alternativas-aspersion | 20 | 10 | 40 | Una frase: aspersión + "89 de 100" | AMPLIAR: matriz de 6, barrido de pesos |
| 9 | negocio-roi | 35 | 31 | 70 | Se queda (es lo más fuerte) | AMPLIAR: escenario adverso, EDU, suscripción 5 años |
| 10 | escalabilidad | 15 | **CORTAR** | 40 | Una frase dentro del cierre | AMPLIAR: etapas, planes, efecto de red |
| 11 | cierre | 18 | 17 | 37 | Se queda | AMPLIAR: lista completa de lo que falta |
| | **Total** | **300** | **180** | **540** | | |

---

## 2. Cobertura de la rúbrica

| Entregable / criterio (pts) | Dónde se cubre |
|---|---|
| 1. Cómo entendió el problema y qué parte abordó (Comprensión 15) | Diap. 2 y 3: la enfermedad nace de noche con hoja mojada, se revisa a mano. Parte elegida: ver y ubicar el foco en la cama exacta (el riesgo ambiental ya lo hace AGRAR) |
| 2. Propuesta y cómo encaja en la operación (Pertinencia 20) | Diap. 4, 6, 8, 10: PLC existente + robot nocturno, supervisor → operario, sin wifi en bloques |
| 3. Demo funcional con alerta y registro (Demo 25) | Diap. 5 y 6: entra foto + T/HR + cama; sana registrada sin alerta; enferma → alerta → supervisor → operario → registro |
| 4. Evidencia y dónde falla (Evidencia 20) | Diap. 7: 78 % / 29 % / alternaria 50 %, n, IC y origen de los datos |
| 5. Limitaciones y qué falta (Justificación 10, Comunicación 10) | Diap. 7 (frase obligatoria), 8 (alternativas) y 11 (qué falta, piloto) |
| Pregunta "¿por qué no en la aspersión?" | Diap. 8 (línea de tiempo) y notas |
| Qué entra y qué sale / a quién le llega / qué queda registrado | Diap. 5 (entra/sale) y 6 (supervisor, registro) |

---

## 3. Diapositivas

### Diapositiva 1 · `portada` · 5 s
- **TÍTULO:** BERRY GOOD IDEA
- **CONTENIDO:** subtítulo "Los ojos que llegan a la cama exacta"; línea pequeña con Sabana Hack 2026 y el nombre del equipo. No usar logos de AGRAR (no implica respaldo).
- **VISUAL:** imagen: IMG-2 (portada) como fondo; opcional video V1 en bucle de 6 s encima. Ondas verde lima.
- **NOTAS:** "Buenas, somos [equipo]. Les vamos a contar una noche en una finca de arándanos."
- **FUENTE:** n/a.

### Diapositiva 2 · `gancho-2am` · 18 s
- **TÍTULO:** La enfermedad empieza de noche, sin testigos
- **CONTENIDO (3):**
  1. "2:00 a. m." / hoja mojada, nadie mirando
  2. "> 10 h" / de hoja mojada bastan
  3. "6:00 a. m." / entra el primer operario
- **VISUAL:** video de fondo V2: invernadero de noche, gotas de condensación formándose sobre una hoja de arándano, reloj en 2:00. IMG-9 como fotograma de respaldo.
- **NOTAS:** "Son las dos de la mañana. El invernadero condensa, la hoja queda mojada y la alternaria puede aparecer de una noche a otra. Los operarios entran a las seis. Hoy, ese foco se ve días después."
- **FUENTE:** `RESPUESTAS_MENTOR.md` §4 (gutación, de una noche a otra; PDF Torres 2015: más de 10 h de hoja mojada, 18–28 °C) y §7 (operarios de 6 a. m. a 2 p. m.).
- **SUPUESTO:** "2:00 a. m." es una hora narrativa, no medida.

### Diapositiva 3 · `problema` · 22 s
- **TÍTULO:** Hoy se detecta tarde y cuesta cosecha
- **CONTENIDO (3 tarjetas, estilo Canva):**
  1. "4–5 días" / revisar 12–15 bloques en papel
  2. "10–25 %" / de la cosecha se pierde
  3. "1 defecto" / y no se exporta
- **VISUAL:** imagen: IMG-3 (operario con linterna y planilla de papel); sirve también `~/Downloads/Dawn Inspection in the Blueberry Greenhouse.png` (hoja de papel, maceta, malla antitrips). Tarjetas verde claro / verde oscuro encima.
- **NOTAS:** "Hoy una persona recorre a mano, cama por cama, y tarda de cuatro a cinco días en doce o quince bloques; el agrónomo digita después. Mientras tanto se pierde entre 10 y 25 % de lo cosechado, y un solo defecto impide exportar. En una finca de 22,5 hectáreas eso son entre 690 y 1.700 millones de pesos al año."
- **FUENTE:** `RESPUESTAS_MENTOR.md` §7 (4–5 días, papel), §8 (10–25 %, 30–40 % sin prevención, un defecto impide exportar); `datos/finanzas/agrar/RESUMEN.md` §3 (688–1.720 M COP, caso central).
- **SUPUESTO:** la conversión a pesos usa 12 t/ha y 8 USD/kg (Forbes/Planasa, fuente interesada); caso conservador 390–975 M COP. Decir "caso central".

### Diapositiva 4 · `misma-noche` · 28 s
- **TÍTULO:** La misma noche, la alerta llega en minutos
- **CONTENIDO (3 pasos):**
  1. PLC marca el bloque en riesgo
  2. Robot confirma en la cama exacta
  3. Supervisor envía operario; queda registro
- **VISUAL:** diagrama: tres nodos en línea. Después del 2, bifurcación: "Hoja sana → solo registro, sin alerta" / "Sospechosa → alerta LoRaWAN: nave · cama · planta + T/HR → paso 3 → operario confirma o descarta → registro + etiqueta para el modelo". Etiqueta pequeña: "objetivo ≤ 5 min de la foto al panel". Fondo: IMG-1 (robot entre arándanos) con IMG-4 (hoja vista por la cámara) como inserto. Opcional: mapa cenital del gemelo con la cama alertada en rojo (Bloque 1 = naves 1–2, Bloque 2 = naves 3–4, camino central).
- **NOTAS:** "AGRAR ya mide el ambiente en cada bloque; cuando su PLC marca riesgo, el robot sale de noche a esa cama primero. Ve la hoja y mide temperatura y humedad en el punto: si es sana, solo la registra, sin alerta; si es sospechosa, viaja por LoRaWAN una alerta con nave, cama y planta. El supervisor la ve y manda a un operario a confirmar: el robot sugiere, la persona decide."
- **FUENTE:** `RESPUESTAS_MENTOR.md` §1, §5, §6; `HANDOFF.md` §3; `dashboard/README.md` (ciclo Nuevo → Asignado → Verificado → Tratado → Cerrado); `~/Downloads/Berry Good Idea · Costo de hardware y comparación (para la presentación).pdf` (clasifica a bordo; LoRaWAN lleva mensajes de cientos de bytes, no video).
- **SUPUESTO:** "≤ 5 min" es objetivo (ver §0.3). El robot cubre unos 5 bloques por noche (14 % de la finca); por eso prioriza con el PLC (`RESUMEN.md` §4). La foto sube al volver a la base con red: diseño, no verificado en campo. Supervisor → operario: sin confirmar con el mentor.

### Diapositiva 5 · `demo-vivo` · 95 s (clímax)
- **TÍTULO:** El robot ve, el supervisor actúa
- **CONTENIDO (3):**
  1. Entra: foto de hoja + T/HR + cama
  2. Sana: se registra, sin alerta
  3. Enferma: alerta al supervisor
- **VISUAL:** video de fondo en vivo: pantalla dividida con el D1 real (cámara de sala) y el panel de cámara con su predicción; el dashboard queda en la otra ventana. Respaldo: V10 (demo completa grabada). IMG-4 como póster. Sale: clase + alerta (si aplica) + registro.
- **Guion de la demo (95 s):**
  - 0–10 s: "Dos filas de PCs son las camas, a escala de sala. El D1 sale solo por la ruta." (ruta autónoma)
  - 10–25 s: gira a la izquierda y a la derecha mirando cada "cama".
  - 25–45 s: hoja sana (la elige el jurado): el panel la marca sana, aparece un punto verde en el mapa, queda en el registro, no hay alerta.
  - 45–70 s: hoja enferma (la elige el jurado): el robot se detiene; sale la alerta con nave · cama · planta y T/HR.
  - 70–95 s: en el dashboard aparece el foco con la foto. Pasar a la diap. 6.
- **NOTAS:** "Entra una foto de la hoja, la temperatura, la humedad y la posición; sale una alerta y un registro. Aquí la hoja la muestra un PC, la T y HR son simuladas y el enlace es wifi, no LoRaWAN; en finca el sensor y la radio ya están en el kit. Miren primero una sana: no genera alerta, pero queda registrada. Ahora una enferma."
- **Si el modelo falla una hoja:** "Eso es justo el 22 % de enfermas que se nos escapa, o el 29 % de falsas alarmas de la siguiente diapositiva." No repetir más de una vez; si falla el robot o la red, pasar a V10.
- **FUENTE:** `HANDOFF.md` §3 y §6d; `datos/robot/GEMELO_DIGITAL.md` (panel :8092, sim-core :8010); `dashboard/README.md` ("Cámara D1", T/HR simuladas).
- **SUPUESTO / riesgo:** que la ruta sea autónoma y el teleop esté probado con el robot en movimiento (hoy el HANDOFF §6b dice que solo se probó el `check`): verificar en el ensayo; si no, decir "teleoperado". La navegación por pasillo real en finca es desarrollo propio por construir (el D1 no tiene ROS). Evitar mirar pantalones o sillas: usar el filtro de "¿hay hoja?" y el `--roi`.

### Diapositiva 6 · `supervisor-registro` · 17 s
- **TÍTULO:** El supervisor decide; todo queda registrado
- **CONTENIDO (3 pasos):**
  1. Foco en el panel: cama, planta, T/HR
  2. Operario confirma o descarta
  3. Registro, también de sanas
- **VISUAL:** video de fondo V5 (grabación del dashboard: foco → Asignar → Verificado → Cerrado; vista cenital con puntos verdes = sanas, rojos = enfermas; KPI de falsas alarmas %). IMG-5 (supervisor con tablet) como póster. En vivo: hacer el clic de "Asignar" y "Verificar" en el dashboard.
- **NOTAS:** "La alerta le llega al supervisor, no a un robot que decide solo: ve el foco, la cama, la temperatura y la humedad, y envía a un operario. El operario confirma o descarta, y esa respuesta queda como etiqueta que enseña al modelo. Las hojas sanas también se guardan, sin alerta: dicen dónde no hay problema. Con el historial salen el mapa de focos y el porcentaje de falsas alarmas."
- **FUENTE:** `dashboard/README.md` (campos, ciclo de acción, KPI "falsas alarmas %", cobertura y puntos ciegos > 48 h); `RESPUESTAS_MENTOR.md` §5 (T/HR y zona obligatorios); `datos/ESCALABILIDAD.md` §7.
- **SUPUESTO:** que las etiquetas del operario reduzcan las falsas alarmas es hipótesis (evidencia parcial en diap. 7); aún no hay confirmaciones de operarios en campo. El dashboard muestra datos simulados más las detecciones del robot real.

### Diapositiva 7 · `evidencia` · 27 s
- **TÍTULO:** Detecta 78 % de enfermas; alternaria, la débil
- **CONTENIDO (3 tarjetas):**
  1. "78 %" / enfermas con alerta (42 de 54)
  2. "29 %" / sanas con falsa alarma (4 de 14)
  3. "50 %" / alternaria con alerta (7 de 14)
- **VISUAL:** gráfico de barras horizontales, fondo blanco o IMG-8A.
  - Panel A, "Hojas con alerta, por clase real": Heliothis 94 % (17/18); Oídio 82 % (18/22); Alternaria 50 % (7/14); en ámbar, Sanas con falsa alarma 29 % (4/14). Bigotes solo en las globales: enfermas IC95 61–92 %, falsas alarmas IC95 0–71 %.
  - Panel B, "Falsas alarmas con la cámara real (mismas 14 sanas)": modelo sin fotos de la cámara 100 % (14/14) → modelo con 278 fotos de la cámara 29 % (4/14).
  - Pie obligatorio: "Probado con 68 hojas de laboratorio mostradas a la cámara del robot, solo 14 sanas; alternaria es la clase débil; el riesgo ambiental no está validado contra enfermedad real. Por eso el robot sugiere y el supervisor manda a un operario a confirmar."
  - Mini inserto de 8 s del panel de cámara (hoja sana → sana; enferma → alerta), opcional.
- **NOTAS:** "Medimos con 68 hojas de laboratorio frente a la cámara del robot: detecta 78 % de las enfermas y falla en alternaria, donde solo la mitad dispara alerta. Marca 29 % de las sanas por error; sin fotos de la cámara era 100 %, y el piloto mide cuánto más bajan con las confirmaciones del operario. Una falsa alarma cuesta una visita; una enfermedad sin ver cuesta cosecha."
- **FUENTE:** `datos/reportes/reentreno-camara.md` (tabla, IC y matriz de confusión: alternaria [3,2,2,7], Heliothis [1,16,0,1], oídio [6,4,8,4], sana [1,0,3,10]); `CIFRAS_CLAVE.md` §1 y §6; porcentajes por clase DERIVADOS de la matriz (verificados: 7+17+18 = 42); `datos/reportes/adquisicion-drberry.md` (DrBerry, CC BY 4.0, 410 hojas: 278 entrenamiento, 64 validación, 68 prueba).
- **SUPUESTO / cuidado:**
  - Costo de error (~30 USD una falsa alarma frente a ~2.160 USD/ha por semana una no detectada, unas 72 veces) es SUPUESTO (`HANDOFF.md` §3; `agrar_roi.py` usa 5 falsas alarmas/ha/año × 30 USD).
  - 100 % → 29 % cambia a la vez fotos de cámara, corrección de color y umbral, y cuesta sensibilidad (B alertaba siempre: sensibilidad 100 % sin valor). Decir "con fotos de la cámara", no "con fotos de campo".
  - Las mismas 68 hojas del test de DrBerry, una sola sesión; con 14 sanas, diferencias de 1–3 imágenes no son significativas. `reentreno-alternaria.md` da IC 0–75 % para falsas alarmas (otra corrida); usar el 0–71 % de `CIFRAS_CLAVE.md`.
  - Fuera de DrBerry (60 hojas sanas de campo, otros países), el modelo anterior alertaba 73 %; el modelo en uso no se ha medido en campo (`resultados/ml/RESULTADOS.md` §5). Botrytis y roya no tienen clase visual.
  - Riesgo ambiental: sensibilidad por día de alerta 28–48 % frente a estación IDEAM, sin datos de incidencia (`CIFRAS_CLAVE.md` §2).

### Diapositiva 8 · `alternativas-aspersion` · 20 s
- **TÍTULO:** Híbrido nocturno: la mejor de seis alternativas
- **CONTENIDO (3 chips):**
  1. Aspersión: ni diaria ni nocturna
  2. "1,5 %" / del costo de cubrir con cámaras fijas (≈ 35 M frente a ≈ 2.300 M COP)
  3. "89 de 100" / híbrido; el segundo saca 75
- **VISUAL:** gráfico: línea de tiempo de 24 h con 4 filas (la respuesta a la aspersión). Fila "Hoja mojada y riesgo": noche y madrugada. Fila "Aspersión (la decide el agrónomo; AGRAR no asperja)": 6:00–14:00, no diaria. Fila "Patrulla del robot": ventana nocturna de 8 h. Fila "Operarios": 6:00–14:00. Horas ilustrativas, rotular así. A la derecha, mini barras del ranking: Híbrido 89,0; Solo sensores fijos 75,0; Solo robot 70,0; Kit en aspersora 57,0; Ruedas 56,0; Humanoide 42,0 (4–8 veces el costo). Si queda saturada, pasar las barras al anexo A2. Fondo: IMG-8A; opcional V8 de 12 s (noche del híbrido frente a aspersora de día).
- **NOTAS:** "La idea original era ir con la aspersión. La descartamos porque AGRAR no asperja (lo decide el agrónomo de cada finca), porque la aspersión no es diaria ni nocturna y el riesgo aparece de noche con la hoja mojada, y porque llega después de aplicar, no antes. No la botamos: la misma plataforma recibe hallazgos de una cámara en la aspersora. Frente a seis alternativas, el híbrido saca 89 de 100."
- **FUENTE:** `datos/finanzas/agrar/RESUMEN.md` §5 (matriz; F primero en 91 % de 11.628 combinaciones de pesos; C = 57,0 con Anticipa = 2); `RESPUESTAS_MENTOR.md` §1 (AGRAR no asperja), §4 (alternaria nocturna), §7; `datos/ESCALABILIDAD.md` §3.1 (cámara en aspersora = otra fuente); `CIFRAS_CLAVE.md` §5; `~/Downloads/Berry Good Idea · Costo de hardware y comparación (para la presentación).pdf` (2.300 M = ≈ 7.200 cámaras × 100 USD × TRM 3.185; kit 34,85 M sin IVA).
- **SUPUESTO / cuidado:**
  - "La aspersión no es diaria" NO está documentada (el mentor no respondió frecuencia ni periodo de reingreso): confirmar con un agrónomo o decir "según nuestro entendimiento". El horario 6–14 h de la aspersión es SUPUESTO (es el horario de los operarios).
  - 2.300 M depende de "una cámara cada 10 m de cama a 100 USD" (SUPUESTO del equipo); las cámaras tampoco ven el envés.
  - "4–8 veces" es el precio del robot (X2 Ultra 39.999 frente a D1 Ultra 7.499 USD FOB ≈ 5,3 veces); en el proyecto completo `RESUMEN.md` §2 da ~294 M frente a ~100 M (≈ 2,9 veces).
  - La matriz usa pesos del equipo, y F incluye a B, así que casi siempre gana; lo que prueba el negocio es el ROI (diap. 9).
  - Hardware 34,85 M (documento) frente a 35,40 M (`RESUMEN.md`): diferencia explicada, usar "≈ 35 M sin IVA".

### Diapositiva 9 · `negocio-roi` · 35 s
- **TÍTULO:** Evitar 1 % de pérdida paga el kit
- **CONTENIDO (3 tarjetas):**
  1. "~0,9 %" / de la cosecha: costo anual
  2. "24 meses" / se paga con 1 % evitado
  3. "40 %" / margen de AGRAR, ~100 M COP
- **VISUAL:** gráfico de líneas, "Meses para recuperar la inversión según % de pérdida evitado". Eje x: 0,5 / 1,0 / 2,0 / 3,0 puntos. Conservador: 913, 58, 20, 12. Central: 74, 24, 10, 6. Alto: 49, 18, 8, 5. Línea horizontal en 24 meses ("meta del mentor: menos de 2 años"). Eje y recortado en 60 con flecha "913" para el primer punto conservador. Rótulo: "Puntos evitados: SUPUESTO, se mide en el piloto con camas testigo". Fondo blanco o IMG-8B.
- **NOTAS:** "El kit completo cuesta unos 100 millones, dentro de los 90 a 110 del presupuesto de AGRAR, con 40 % de margen. Para la finca, el sistema cuesta cerca de 1 % de lo que cosecha al año. Si evita un punto de pérdida se paga en unos 24 meses; con dos puntos, en 10. Esos puntos son nuestro supuesto más importante y el piloto con camas testigo existe para medirlo."
- **FUENTE:** `datos/finanzas/agrar/RESUMEN.md` §1–3 (100,4 M COP, 40 %; 24 y 10 meses; tabla de payback; reducción relativa 7 % y 13 % si la pérdida base es 15 %) y §6 (867 USD/ha/año ≈ 2,76 M COP); `agrar_roi.py`. **DERIVADO (calculado aquí):** 867 / 96.000 USD/ha (12 t/ha × 8 USD/kg) = 0,90 %; rango 0,72 % (alto) a 1,59 % (conservador, 9,07 t/ha × 6 USD/kg).
- **SUPUESTO / cuidado:**
  - Puntos evitados, rendimiento y precio son SUPUESTOS; con 0,5 puntos no se paga en ningún escenario; con 1 punto el central está justo en el límite de 24 meses.
  - AGRAR ya predice con sus PLC: parte de esa mejora ya existe, lo incremental del robot se mide en el piloto.
  - Colchón corto: D1 a precio de tienda (9.600 USD), IVA como costo o TRM 3.900 llevan el precio a 111–113 M, sobre el techo. Con IVA al cliente serían 119,5 M.
  - 867 USD/ha/año es la única cifra de costo por ha (no usar 722, 820, 520 ni 430).
  - Si se amplía: 10 proyectos al año = 1.004 M COP facturados y 402 M de margen bruto; suscripción de 17 M COP por finca que suma 585 M en el año 5 (retención 90 %, SUPUESTO).

### Diapositiva 10 · `escalabilidad` · 15 s
- **TÍTULO:** Una plataforma, muchas fincas, muchos frutales
- **CONTENIDO (3):**
  1. "5 fuentes" / un solo registro
  2. "3 cultivos" / 3 archivos, 0 robots nuevos
  3. "< 2 %" / del arándano de 4 países está en Colombia
- **VISUAL:** diagrama: al centro "registro de incidencias"; a la izquierda cinco fuentes (robot, celular del operario, cámara en la aspersora, sensores LoRaWAN, pronóstico por coordenada); a la derecha varias fincas aisladas y tres cultivos (arándano, fresa, mora). Fondo: IMG-7 (plano aéreo de dos bloques) e IMG-6 (base de carga).
- **NOTAS:** "La Sabana es solo nuestro ejemplo: lo que se vende es una plataforma. El mismo registro recibe hallazgos del robot, del celular del operario o de una cámara en la aspersora, y otro frutal es un archivo de configuración, no un robot nuevo. Colombia es menos del 2 % del arándano de cuatro países, así que nace lista para otras fincas y regiones."
- **FUENTE:** `datos/ESCALABILIDAD.md` §3.1 (mismo formato de incidencia; 20 de 20 casos del esquema), §4 (perfiles arándano, fresa y mora; 22 modelos y 6 motores) y §8.1 (≈ 1.000 de ≈ 54.500 ha, CÁLCULO).
- **SUPUESTO / cuidado:** los perfiles de fresa y mora se validan en el motor, no en campo; "cada finca mejora a todas" es hipótesis (§7.5); el multi-cliente tiene 2 casos de ataque abiertos documentados: no decir "seguro". Los precios de plan (130 y 520 USD/ha/año) son PROPUESTA y no se mezclan con 867.

### Diapositiva 11 · `cierre` · 18 s
- **TÍTULO:** De 5 días a 5 minutos
- **CONTENIDO (3):**
  1. Piloto: 1 finca, camas con y sin robot
  2. Falta: fotos y clima de campo real
  3. "Los ojos que llegan a la cama exacta"
- **VISUAL:** video de fondo V9 (amanecer en el invernadero, el D1 vuelve a la base de carga); IMG-2 o IMG-1 como eco de la portada. Ondas verde lima.
- **NOTAS:** "Esto no está terminado y lo decimos: probamos con hojas de laboratorio, no con una finca. El siguiente paso es un piloto con un cliente de AGRAR y camas testigo, para medir cuántas alertas confirma el operario, cuántos puntos de pérdida se evitan y cuánto tarda la alerta. Falta también navegar pasillos reales, la carga automática y validar el riesgo ambiental con incidencia real. De 5 días a 5 minutos."
- **FUENTE:** `datos/ESCALABILIDAD.md` §8.2 (criterios de paso del piloto); `datos/finanzas/agrar/RESUMEN.md` §8 (pendientes); `CIFRAS_CLAVE.md` §6; `HANDOFF.md` §3–4.
- **SUPUESTO:** los criterios de paso (≥ 70 % de alertas confirmadas, adelanto ≥ 3 días en ≥ 50 % de los focos, ≥ 90 % de camas recorridas, robot operativo ≥ 85 %) son SUPUESTO. "5 minutos" es objetivo (ver §0.3).
- **Si se amplía (9 min):** lista completa de lo que falta: fotos de campo andino y reentreno con confirmaciones; navegación en pasillos de 6,8 m, carga automática y línea de vista del manual (no verificados); IP54 y autonomía de 1–2 h; cotización formal del D1 (7.499 USD FOB frente a 9.600 en tienda); medir puntos de pérdida evitados.

---

## 4. Diapositivas de respaldo (anexo, no se presentan)

- **A1 Fuentes y licencias:** DrBerry CC BY 4.0; PlantVillage CC BY-SA; dataset de fresa de Mendeley CC BY-NC (solo evaluación, no comercial); YOLO/ultralytics AGPL-3.0; Open-Meteo gratuita solo no comercial, con atribución "Weather data by Open-Meteo.com".
- **A2 Matriz de las 6 alternativas** con puntajes y variantes de pesos (`RESUMEN.md` §5).
- **A3 Sensibilidad del ROI:** tabla de payback por escenario y caso adverso (`RESUMEN.md` §2–3).
- **A4 Matriz de confusión** de `modelo_camara` (`reentreno-camara.md`).
- **A5 Capacidad:** 19 ha/semana, ~7 noches por vuelta de 40 bloques, rango 3–12 (`RESUMEN.md` §4).
- **A6 Arquitectura multi-finca y sin conexión** (`ESCALABILIDAD.md` §3.2).
- **A7 Criterios del piloto** (`ESCALABILIDAD.md` §8.2).

---

## 5. Videos a grabar (prioridad en ese orden para iterar rápido)

Formato común: 1080p, 30 fps, MP4 H.264, 16:9, sin audio, ≤ 25 MB cada uno, nombre `V#_slug.mp4`. Grabar siempre 3 tomas completas.

| ID | Va en | Duración | Qué mostrar | Cómo / plan B |
|---|---|---|---|---|
| V10 | Respaldo de la 5 | 90 s | Demo completa: ruta del D1, hoja sana (registrada sin alerta), hoja enferma (robot se detiene, alerta), supervisor asigna, operario confirma, registro | Grabar primero: es el seguro contra fallas de robot o red. Con cronómetro visible (medir el "5 minutos") |
| V3 | 5 | 60–75 s | Toma amplia del D1 real: sale de la base, avanza entre las dos filas de PCs, gira a izquierda y derecha frente a cada hoja | Celular en trípode a la altura del robot; plan B: teleop declarado |
| V4 | 5 y 7 | 30 s | Panel de cámara (puerto 8092): predicción en vivo; hoja sana (sin alerta) y hoja enferma (alerta); etiqueta real frente a la del robot | Captura de pantalla; usar hojas del test del jurado |
| V5 | 6 | 40 s | Dashboard (localhost:5180): entra la detección "Cámara D1" al mapa, abre el foco, supervisor asigna, operario verifica, se cierra; puntos verdes de sanas | Captura de pantalla; mostrar capa de humedad en la vista cenital |
| V6 | 5 (opcional) | 30 s | Pantalla dividida: D1 real y su avatar en el gemelo digital moviéndose a la vez | Puente en modo `juanda`; plan B: modo `mock` |
| V1 | 1 | 6 s en bucle | D1 de frente caminando por un pasillo de arándanos, de noche | Render del gemelo (berry-sim), cámara baja |
| V2 | 2 | 12–15 s | Gotas de condensación en una hoja, luz fría, reloj en 2:00 | No hay plantas físicas: render con partículas o stock con licencia (citarla) |
| V9 | 11 | 10 s | Amanecer, el D1 vuelve a la base de carga | Render del gemelo o mover IMG-1 (efecto Ken Burns) |
| V8 | 8 (opcional) | 12 s (40 s completos al anexo) | Pantalla dividida: patrulla nocturna del híbrido frente a aspersora de día, mismo brote | Solo si las métricas salen de `batch.py` con semilla; no hay resultados de "día de detección" en los archivos, no inventarlos |

---

## 6. Imágenes y gráficos necesarios

**Ya tienen prompt en `presentacion/prompts_imagenes.md`:** IMG-1 robot entre arándanos (diap. 4 y 11); IMG-2 portada (1 y 11); IMG-3 operario con linterna y planilla (3); IMG-4 hoja con HUD vista por la cámara (4 y 5); IMG-5 supervisor con tablet (6); IMG-6 base de carga (10); IMG-7 plano aéreo de dos bloques (10); IMG-8 fondos abstractos para datos (7, 8, 9); IMG-9 gancho 2 a. m. (2).

**Falta producirlas (gráficos y diagramas, en el estilo verde del equipo):**
1. **G1 Evidencia (diap. 7):** barras horizontales con los datos exactos de la sección 3, panel A y panel B; falsas alarmas en ámbar; porcentajes y n en cada barra; sin 3D.
2. **G2 Payback (diap. 9):** tres líneas con los datos exactos; línea de 24 meses; el 913 con flecha fuera de escala.
3. **G3 Línea de tiempo de 24 h (diap. 8):** 4 filas rotuladas "horas ilustrativas".
4. **G4 Ranking de alternativas (diap. 8 y A2):** 6 barras con los puntajes; el híbrido en verde oscuro, el resto en gris.
5. **D1 Diagrama de la alerta (diap. 4):** 3 pasos con la bifurcación sana / sospechosa, vectorial, con íconos de PLC, robot y persona.
6. **D2 Diagrama de plataforma (diap. 10):** 5 fuentes → registro → fincas y cultivos.
7. **I1 Mapa cenital del gemelo (diap. 4):** Bloque 1 (naves 1–2), Bloque 2 (naves 3–4), camino central de 5–6 m, cama alertada en rojo; exportar de la vista cenital del dashboard.
8. **I2 Panel de cuatro hojas DrBerry** (sana, oídio, alternaria, Heliothis), citando CC BY 4.0, para la diap. 5 y el anexo.
9. **I3 Foto propia del D1 con cámara y mástil** (anexo y diap. 8 si se necesita).

---

## 7. Cinco preguntas probables del jurado de negocios

1. **¿Cuánto cuesta y en cuánto se paga?**
   El kit completo son ~100 M COP (40 % de margen para AGRAR), dentro de los 90–110 M. Para una finca de 22,5 ha cuesta ~0,9 % de la cosecha al año; evitar 1 % de pérdida lo paga en ~24 meses y 2 % en ~10. Con 0,5 % no se paga en ningún escenario, por eso el piloto con camas testigo mide ese número primero.
2. **¿Qué pasa con las falsas alarmas y con lo que no detecta?**
   Medimos 29 % de falsas alarmas y 22 % de enfermas sin alerta (alternaria es la peor), con solo 68 hojas y 14 sanas: los intervalos son anchos y lo decimos. Una falsa alarma cuesta una visita (~30 USD, supuesto) y una enfermedad no vista mucho más (~2.160 USD/ha por semana, supuesto), por eso preferimos alertar de más y que una persona confirme. Cuántas tolera el cliente lo fija el piloto; el mentor no lo respondió.
3. **Si AGRAR ya predice con sus PLC, ¿qué agrega el robot?**
   El PLC dice qué bloque está en riesgo; no ve la planta ni ubica la cama. El mentor lo dijo: oídio y mildiu "solo se saben viéndolos", y una alerta sin cama, planta, T/HR y foto no se puede actuar. Parte de la mejora ya la captura el PLC: lo incremental del robot es un supuesto que el piloto mide. Botrytis, la principal, la cubre la capa ambiental, no la cámara.
4. **¿Un solo robot alcanza? ¿Y si se daña?**
   De noche cubre ~19 ha por semana: una vuelta de 40 bloques en ~7 noches (3–12 según supuestos), unos 5 bloques por noche, empezando por los que el PLC marca en riesgo. Con dos robots el precio sale del rango (~171 M). Si falla (~7 días hábiles de reparación) los PLC siguen protegiendo; carga automática y línea de vista del manual están por verificar.
5. **¿Cómo gana plata AGRAR y qué tan firme es el precio?**
   10 proyectos al año son ~1.004 M COP facturados y ~402 M de margen bruto, más una suscripción de 17 M por finca que llega a ~585 M anuales en el año 5 (retención 90 %, supuesto). El colchón es corto: D1 a precio de tienda, IVA como costo o dólar a 3.900 lo suben a 111–113 M; con D1 EDU baja a ~91 M. El hardware son ~35 M; las horas de ingeniería pesan casi lo mismo.

---

## 8. Supuestos y pendientes antes de subir al Canva

1. Cronometrar "foto → alerta en el panel" (5 repeticiones) y ajustar "5 minutos" al número medido.
2. Confirmar que la ruta autónoma y el giro del D1 funcionan; si no, decir "teleoperado" (HANDOFF §6b).
3. Confirmar con un agrónomo que la aspersión no es diaria ni nocturna y su horario.
4. Cotización formal del D1 y si los 90–110 M incluyen IVA (`RESUMEN.md` §8).
5. Costos de error (30 USD / 2.160 USD/ha/semana) y puntos de pérdida evitados: SUPUESTOS a medir en el piloto.
6. Cámaras fijas (2.300 M) y "4–8 veces": estimaciones del equipo, rotular "estimación".
7. T/HR simuladas y wifi en la demo: decirlo en voz alta.
8. Reemplazar cualquier cifra del documento del equipo por las de `CIFRAS_CLAVE.md`.
