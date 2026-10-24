# Pitch final · Berry Good Idea (5 min con demo)

Va con `BerryGoodIdea_pitch_con_videos.pptx` (11 diapositivas + 2 de respaldo). Corte: 24-oct-2026. Lema: **"De 8 días hábiles a minutos"**. **No hay modelo de negocio:** se muestra solo el costo del hardware (AGRAR pone su precio).

| # | Diapositiva | Tiempo | Quién |
|---|---|---|---|
| 1 | Portada | 5 s | Presentador |
| 2 | Una noche húmeda puede abrir un foco | 20 s | Presentador |
| 3 | La pérdida es alta y la ronda, lenta | 22 s | Presentador |
| 4 | La misma noche: alerta en minutos | 25 s | Presentador |
| 5 | **Demo en vivo** (con videos de respaldo) | 95 s | Técnico + robot |
| 6 | Cada hallazgo lo cierra una persona | 18 s | Técnico (clics en el dashboard) |
| 7 | 78 % detectadas · 29 % falsas alarmas | 30 s | Datos |
| 8 | El PLC anticipa, el robot sugiere | 25 s | Presentador |
| 9 | ≈ 35 M COP; las alternativas, 4 a 8× más | 25 s | Presentador |
| 10 | Registro único, diseñado para escalar | 15 s | Presentador |
| 11 | De 8 días hábiles a minutos | 20 s | Presentador |
| | **Total** | **300 s** | |

---

## 1 · Portada (5 s)
> Buenas, somos Berry Good Idea. Les vamos a contar una noche en una finca de arándanos y cómo cambia cuando un robot llega a la cama exacta.

## 2 · Una noche húmeda puede abrir un foco (20 s)
> Son las dos de la mañana. El invernadero condensa, la hoja queda mojada y puede abrirse un foco de alternaria de una noche a otra; la botrytis, la que más cuesta, avanza con varias noches de humedad alta. Los operarios entran a las seis, de día y con papel. De noche nadie revisa las camas.

## 3 · La pérdida es alta y la ronda, lenta (22 s)
> Hoy, cinco a seis operarios tardan **7 a 8 días hábiles** en recorrer una finca de 20 hectáreas, solo de día y en papel; después el agrónomo digita. Mientras tanto se pierde entre el **10 y el 25 %** de la cosecha por problemas fitosanitarios, hasta un 40 % sin prevención, y un solo defecto en la fruta impide exportar.

## 4 · La misma noche: alerta en minutos (25 s)
> AGRAR ya mide el ambiente en cada bloque. Cuando su PLC marca riesgo, el robot sale de noche y va **primero a esa cama**. Ve la hoja y mide temperatura y humedad en ese punto. Si es sana, solo la registra. Si es sospechosa, envía una alerta con **nave, cama y planta**. El supervisor la ve y manda a un operario a confirmar: **el robot sugiere y la persona decide**.

*(El sello naranja dice "se valida en el piloto": la integración con el PLC y LoRaWAN es diseño.)*

## 5 · Demo en vivo (95 s)
**Antes de empezar:** el supervisor ya eligió el **Bloque** en el dashboard, se pulsó **⟲ Inicio** en el simulador y el robot está **de pie**. Guía técnica: `GUIA_RED_ROBOT.md`.

> Entra una foto de la hoja, temperatura, humedad y posición; sale una alerta y un registro. Aquí las camas son dos filas de PCs a escala de sala, la temperatura y la humedad son simuladas y el enlace es Wi-Fi; en finca van el sensor y la radio LoRaWAN.

| s | Qué pasa | Qué decir |
|---|---|---|
| 0–10 | **Ruta real**: el D1 sale solo | "El robot sale por la ruta del bloque que eligió el supervisor." |
| 10–25 | Para y gira a izquierda y derecha | "En cada pasillo se detiene a mirar las dos camas." |
| 25–45 | Hoja **sana** | "Sana: no hay alerta, pero queda registrada. Sabemos dónde no hay problema." |
| 45–70 | Hoja **enferma** | "Enferma: el robot se detiene y sale la alerta con nave, cama y planta." |
| 70–95 | Dashboard: aparece el foco | "Y el supervisor ya lo tiene en el panel." → siguiente diapositiva |

**Plan B:** si algo falla en vivo, reproducir los videos de esta misma diapositiva (robot real y cámara leyendo hojas) y decirlo: *"este es el mismo recorrido grabado hoy"*.
**Si el modelo se equivoca con una hoja:** *"Ese es justo el error que medimos: por eso el operario confirma."*

## 6 · Cada hallazgo lo cierra una persona (18 s)
> La alerta le llega al supervisor, no a un robot que decide solo. Ve el foco, la cama, la temperatura y la humedad, y envía a un operario. El operario confirma o descarta, y queda registrado: **Nuevo, Asignado, Verificado, Tratado y Cerrado**. Las hojas sanas también quedan, sin alerta.

*(En vivo: clic en **Enviar operario** y en **Registrar confirmación**. Video de respaldo: el panel.)*

## 7 · 78 % detectadas · 29 % falsas alarmas (30 s)
> Lo medimos con fotos de laboratorio frente a la cámara del robot. El **78 %** de las hojas enfermas dispara alerta, y falla sobre todo en alternaria, donde la detecta la mitad de las veces. El **29 %** de las sanas sale como falsa alarma. Una falsa alarma es una visita del operario; una enfermedad sin ver es una cama perdida. Cada confirmación del operario queda como dato para reentrenar, y el piloto con fotos de la Sabana mide cuánto bajan las falsas alarmas.

*(Honestidad: son 68 fotos de una finca de Perú, solo 14 sanas; los intervalos son anchos y está escrito en el pie.)*

## 8 · El PLC anticipa, el robot sugiere (25 s)
> El PLC de AGRAR anticipa con lo que ya existe, el robot llega a la cama exacta y sugiere, y el operario confirma: juntos cubren lo que cada uno no ve. La idea original era ir en la aspersión, pero la descartamos: AGRAR no asperja, el riesgo aparece de noche con la hoja mojada y la aspersión llega después de aplicar. Frente a seis alternativas, el híbrido saca **89 de 100**.

*(Video: gemelo digital.)*

## 9 · ≈ 35 M COP; las alternativas, 4 a 8× más (25 s)
> Todo el hardware de una finca cuesta unos **35 millones sin IVA**: el robot, una batería de repuesto, la cámara 4K con luz, el computador a bordo, el sensor de temperatura y humedad, el módulo LoRaWAN, el mástil y la base de carga. Un humanoide cuesta entre 4 y 8 veces más; cubrir la finca con cámaras fijas, unos 2.300 millones, 66 veces más. El precio final lo define AGRAR.

*(Son estimaciones del equipo con precios de referencia, sin cotización formal.)*

## 10 · Registro único, diseñado para escalar (15 s)
> La Sabana es solo nuestro ejemplo. El mismo registro recibe hallazgos del robot, del celular del operario, de los sensores y del pronóstico, y cada finca queda aislada. Para otro frutal hacen falta su perfil de riesgo, sus fotos y un piloto.

## 11 · De 8 días hábiles a minutos (20 s)
> No está terminado, y lo decimos: probamos con hojas de laboratorio, no en una finca. Pero vuelvan a las dos de la mañana: hoy nadie revisa hasta las seis. Con el robot, esa noche ya está en la cama en riesgo y a las seis el operario sabe adónde ir. Hoy, 7 a 8 días hábiles; con el robot, la cama en riesgo se revisa esa misma noche y la alerta llega en minutos. **De 8 días hábiles a minutos.** Gracias.

*(Si preguntan: la vuelta completa a los 40 bloques toma ~7 noches. "Minutos" es la alerta donde hay riesgo, no cubrir toda la finca.)*

---

## Si solo hay 3 minutos
Corta la 6 y la 10. Deja la 2 en una frase, la 3 con dos cifras (7–8 días y 10–25 %) y la demo en 60 s (sana → enferma → foco en el panel).

## Preguntas probables del jurado
| Pregunta | Respuesta corta |
|---|---|
| ¿Cuánto cuesta? | Hardware ≈ 34,85 M COP sin IVA (≈ 41,5 M con IVA). El precio lo fija AGRAR. |
| ¿Y las falsas alarmas? | 29 % hoy, con pocas sanas medidas. Cada confirmación del operario es un dato para reentrenar; el piloto mide cuánto bajan. |
| ¿Por qué no en la aspersión? | AGRAR no asperja, la aspersión no es nocturna y el riesgo aparece de noche. La plataforma sí puede recibir una cámara en la aspersora. |
| ¿Un robot alcanza? | Da la vuelta a 40 bloques en ~7 noches, pero cada noche empieza por las camas en riesgo que marcan los PLC. |
| ¿Cómo sabe la cama exacta? | Marcadores en la cabecera más la odometría del robot. Se valida en el piloto. |
| ¿Y la botrytis? | No tiene clase visual: la cubre la capa de riesgo ambiental (clima del PLC). |
| ¿Qué falta para una finca real? | Fotos locales, prueba en cama real, Jetson a bordo, integración con PLC/LoRaWAN y sensor de temperatura y humedad a bordo. |
