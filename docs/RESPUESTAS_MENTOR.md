# Respuestas del mentor (AGRAR) · resumen estructurado

Fuentes: `apuntes entrevista.md` (transcripción automática), el Word de preguntas con respuestas y el PDF *Manejo Integrado de Plagas y Enfermedades del Cultivo de Arándano* (C. Torres, Lima, 2015).
Lo marcado **[interpretación]** es nuestra lectura de una transcripción confusa y hay que confirmarlo.

## 1. Quién es el cliente
- **AGRAR es una empresa de tecnología, no un productor.** Hace automatización de invernaderos: ventilación para controlar humedad y temperatura, cortinas, riego, gabinetes eléctricos con PLC y sensores por bloque, y bases de datos.
- **El manejo fitosanitario no es de AGRAR.** Lo decide el agrónomo de cada finca. AGRAR no hace aspersión ni fumigación.
- AGRAR **ya trabaja en un modelo predictivo** de enfermedad a partir de las condiciones ambientales de cada bloque, que corre en su controlador.
- **Alcance:** nacional e internacional. Se vende a varias fincas y grupos empresariales.
- **Clientes posibles:** Elite Flower, Sunshine Bouquet, Deliflor, Jardines de los Andes y GHT (no es seguro que GHT tenga arándano; hay que verificarlo). Son grupos que arriendan o compran fincas y las manejan como empresas bajo un mismo grupo, varios de ellos floricultores que se están pasando al arándano.

## 2. Negocio y presupuesto
- **Inversión por proyecto:** 90–110 millones de COP ("dato al aire").
- **Punto de equilibrio:** menos de 2 años.
- **Margen mínimo para AGRAR:** 40 %.
- **Ventas esperadas:** unos 10 proyectos de este tipo al año, porque son de nicho y específicos de cada cliente. Para comparar, su negocio de ventilación vende 40–60 unidades al mes.
- **Precio de referencia de un ventilador:** 1,5–4,5 millones de COP.

## 3. Estructura del cultivo
- **Maceta en invernadero o macrotúnel**, con techo de plástico. Los laterales tienen **malla antitrips**. El cultivo casi nunca es totalmente cerrado.
- **Nave:** 6,8 m de ancho en invernadero y 12,5–13 m en macrotúnel. Unos **80 m** de largo, con **2–3 camas por nave**.
- **Camino central:** 5–6 m de ancho.
- **Bloques:** de 0,5 ha o 1 ha (1,5 ha es raro, porque cuesta más sacar la cosecha por partes y hacer llegar el riego).
- **Finca típica:** unos 40 bloques, entre **20 y 25 ha**.
- **Altura del arbusto:** a la cadera o la costilla. Dijo "unos 50", que no queda claro si son cm sobre la maceta. **[interpretación: ~0,9–1,3 m]**
- **Las plantas crecen hacia el pasillo**, con racimos colgando. A veces hay que pasar de medio lado. **El robot no puede tumbar ni dañar el fruto.**

## 4. Enfermedades y plagas (según el mentor)
| Problema | Qué dijo | Implicación |
|---|---|---|
| **Botrytis** | La más común y la que más cuesta. Por humedad relativa muy alta y temperatura; con humedad alta sostenida, el riesgo es casi del 100 %. Ellos la controlan en parte con ventilación | Núcleo ambiental. El PDF dice: 15–24 °C con agua libre sobre el tejido, y neblina o rocío abundante |
| **Alternaria** | Por humedad y **gutación**: de noche el invernadero condensa, la hoja queda mojada y la enfermedad aparece **de una noche a otra** si no se seca | El PDF dice: lluvia > 2 mm, más de 10 h de hoja mojada y 18–28 °C, dispersión por viento. Trae una **escala de severidad de 1 a 5**. Conviene **patrullar de noche o al amanecer** |
| **Trips** | Plaga. La malla no la elimina del todo, pero entran muy pocos. **El robot debería ver el daño, no al insecto** | Clase visual "daño por trips" (falta dataset) |
| **"Velloso" y "polvoso"** **[interpretación: mildiu velloso y mildiu polvoso, es decir oídio]** | Si ya aparecen, la ventilación no sirve (incluso hay que apagarla para no mover las esporas). **La única forma de saberlo es verlos** | Justifica el robot con cámara. El oídio ya está en nuestro foco visual. El mildiu velloso en arándano hay que verificarlo |
| Roya, *D. suzukii* | No las conoce; dice que eso lo maneja el agrónomo de cada finca | Se quedan fuera del alcance |
| Phytophthora, Heliothis, arañita roja, mosca de la fruta, *Prodiplosis*, *Anomala* | Aparecen en el PDF (Perú) | Heliothis sigue en DrBerry; las demás quedan fuera |

**Dónde entra el robot en el ciclo fitosanitario:** AGRAR está en el paso 3, la **prevención**. El robot debe entrar entre los pasos 3 y 4: medir temperatura y humedad para saber qué tan propenso está el ambiente y, **si la enfermedad ya apareció, mandar una alerta**. El robot no quita hojas ni frutos.

## 5. Qué debe enviar el robot (requisito explícito)
- A la base de datos, **sí o sí**: **temperatura y humedad relativa en el punto exacto** donde detecta la incidencia, más **la zona o punto** (bloque, nave, cama, posición).
- **El robot tiene que llevar sensor de temperatura y humedad.** La temperatura y la humedad las da el ambiente; los ventiladores solo las bajan.

## 6. Conectividad
- **No hay wifi ni señal celular en los bloques.** Solo hay internet en la oficina de cada finca (Starlink o fibra).
- Hoy hay **dataloggers** en los bloques que se descargan con USB, y **PLC por bloque** con sensores (temperatura, humedad, conductividad eléctrica del suelo, etc.).
- Los PLC se comunican por **LoRaWAN, SDI-12 o Modbus RTU** hasta un controlador conectado a internet.
- **Se puede reutilizar su infraestructura si el protocolo es abierto.**
- Consecuencia: el robot debe **guardar los datos y reenviarlos** (por LoRaWAN o al llegar a la base de carga con red).

## 7. Personas y monitoreo actual
- **Roles:** gerente de finca, supervisores, **al menos 2 agrónomos por finca** (deciden sustratos, fumigación y qué hacer si la temperatura sube o baja), técnicos (mantenimiento mecánico y eléctrico, unos 4 por finca) y operarios (aplicación, cosecha, poda).
- **Tamaño de la plantilla:** una finca de arándano de 40 ha tiene unos 200–300 operarios. Una de flores de 85 ha, unos 650.
- **Monitoreo hoy:** operarios y supervisores revisan **a mano, bloque por bloque, en papel** (una hoja por cama). Una persona tarda **4–5 días de jornada completa** en recorrer una finca de 12–15 bloques. El agrónomo recibe las hojas y las digita. **Actualización 24-oct-2026:** una finca de ~20 ha la recorren **5–6 operarios en 7–8 días hábiles** (ver `CIFRAS_CLAVE.md` §1b).
- **Horario de los operarios:** 6 a. m. a 2 p. m. Es frecuente que se olvide un ventilador o que el alero quede abierto con lluvia, lo que mete humedad al invernadero.

## 8. Pérdidas
- **Pérdida por problemas fitosanitarios: 10–25 % de lo cosechado.** Sin manejo preventivo, **30–40 %**.
- **Caso real:** una finca perdió **~150 millones de COP en una cosecha**, pero en **poscosecha**, por una falla de humedad y temperatura en los cuartos fríos. No fue en campo.
- **Cualquier defecto impide exportar** y obliga a vender en el mercado nacional. Los grupos grandes quieren exportar.
- **Días entre el primer síntoma y la detección:** "depende del clima". Es distinto en Antioquia que en Bogotá.

## 9. Sin respuesta (siguen abiertas)
- Periodo de reingreso tras aplicar.
- Cuántas falsas alarmas tolerarían.
- Canal real de la alerta.
- Si sirve el triage agrónomo → operario. Probable, pero sin confirmar.
- Cómo miden hoy si un tratamiento funcionó.
- Qué significa para ellos "detectar a tiempo".
- Costo del jornal y de una aplicación.
- Si es obligatorio usar un robot: la respuesta fue "no especifica, pero sí" y "tiene que verlo".
- Ubicación y altitud de las fincas.
- Qué son exactamente "velloso" y "polvoso".
