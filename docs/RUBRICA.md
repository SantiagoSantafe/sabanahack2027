# Rúbrica oficial · Berry Good Idea (Sabana Hack)

Texto del reto entregado por el usuario el 2026-10-24.

## Reto
¿Cómo podría un robot ayudar a identificar a tiempo, cama por cama, las condiciones ambientales o fisiológicas que indican o favorecen enfermedades en un cultivo de arándanos, y convertir cada hallazgo en una alerta y un registro útil para quienes manejan el cultivo?
- La solución debe incluir un robot (prototipo físico, simulación o ambos). Idea original: aprovechar el recorrido de la aspersión; se imaginó un humanoide, pero el tipo de robot es libre.
- Puede considerar otros frutales y qué cambiaría.

## Al final cada equipo debe poder
1. Explicar cómo entendió el problema y qué parte decidió abordar.
2. Presentar su propuesta y cómo encajaría en la operación de un cultivo de arándanos.
3. Mostrar una demostración funcional del robot y del núcleo de su solución, incluido cómo un hallazgo se convierte en una alerta y queda registrado.
4. Presentar evidencia de qué tan bien funciona y en qué casos falla.
5. Reconocer sus limitaciones y qué faltaría para llevarla a un cultivo real.

## Demostración y validación
Una buena demostración deja claro:
1. Qué información entra al sistema y qué sale de él.
2. Cómo se comporta frente a plantas o condiciones sanas y frente a plantas o condiciones con señales de enfermedad.
3. Cómo un hallazgo se convierte en una alerta, a quién le llega y qué queda registrado.
Sobre la evidencia:
1. Datos públicos, propios o simulaciones, explicando de dónde salen y qué tan representativos son de un cultivo real de arándanos.
2. Mostrar cómo comprobaron que funciona y qué errores comete: falsas alarmas y casos no detectados.
3. Reconocer los límites de la validación se valora; ocultarlos no.

## Preguntas guía del reto
- Señales: qué indica enfermedad o riesgo; qué se ve en la planta y qué en el ambiente; cómo distinguir enfermedad de otro daño.
- Recorrido: qué pasa durante la aspersión y qué límites impone; cómo se sabe en qué cama y planta ocurrió cada hallazgo.
- Persona: quién recibe la alerta y qué necesita para actuar; papel del personal de campo.
- Decisión: cuándo una señal merece alerta; qué cuesta más, falsa alarma o enfermedad no detectada.
- Registro: qué guardar de cada incidencia; qué se aprende del historial.

## Criterios (100 puntos)
| Criterio | Pts | Sobresaliente | Aceptable | Insuficiente |
|---|---|---|---|---|
| Comprensión del problema | 15 | 13–15: explica cómo surgen y se propagan los problemas y conecta con quienes lo viven | 8–12: vacíos sobre cultivo o personas | 0–7 |
| Pertinencia de la propuesta | 20 | 17–20: responde a una parte importante y explica cómo encaja en el cultivo | 10–16: lugar en la operación poco claro | 0–9 |
| Funcionamiento de la demostración | 25 | 21–25: robot y núcleo en vivo, estable, casos sanos y enfermos, alerta registrada | 13–20: en parte, solo casos preparados o sin cerrar ciclo | 0–12 |
| Evidencia y validación | 20 | 17–20: pruebas verificables, falsas alarmas y no detectados, representatividad | 10–16: incompletas o sin análisis de errores | 0–9 |
| Justificación de decisiones | 10 | 9–10: compara alternativas y reconoce límites | 5–8 | 0–4 |
| Comunicación | 10 | 9–10: clara para cualquier público | 5–8 | 0–4 |

## Material de referencia público
DrBerry (arándano: sana, alternaria, oídio, Heliothis), HyperspectralBlueberries (420 frutos), PlantVillage (arándano solo sano), PlantDoc (2.598 de campo), Strawberry Disease Detection (2.500, 7 enfermedades), Strawberry Hybrid Data Augmentation (5.610, 8 clases). Pocos datos de arándano; varios de laboratorio. Citar fuentes y licencias.
