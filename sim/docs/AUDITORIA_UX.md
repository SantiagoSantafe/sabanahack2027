# Auditoría UX/UI de Berry Sim

Revisión de la versión anterior de la interfaz con las 10 heurísticas de Nielsen y las 10 leyes de la simplicidad de John Maeda, y lo que se cambió por cada hallazgo.

Severidad: 3 = bloquea o confunde la tarea principal, 2 = molesta con frecuencia, 1 = cosmético.

## Hallazgos (Nielsen)

| # | Heurística | Hallazgo | Sev. | Cambio |
|---|---|---|---|---|
| 1 | Visibilidad del estado | Cuando el robot estaba en la base, los días pasaban rápido sin decir qué venía después. | 3 | Indicador de estado en la barra: "Robot en campo, tiempo real" o "En base, próximo recorrido: día 4, 09:00" con botón **Ir al recorrido**. |
| 1 | Visibilidad del estado | No se veía si los datos del robot habían llegado a la base de datos (no hay WiFi en el bloque). | 3 | Pestaña **Datos** del robot: registros pendientes, última sincronización e incidencias con temperatura y humedad. |
| 1 | Visibilidad del estado | La conexión con el motor era un punto de 9 px en la esquina. | 2 | Estado de conexión explícito en el indicador y pantalla de reconexión. |
| 2 | Lenguaje del usuario | "Cama 1…10" no coincide con cómo habla la finca (bloque, nave, cama). | 3 | Todo se nombra como "Nave 2 · Cama 3"; los marcadores ArUco dicen "N2 C3". |
| 2 | Lenguaje del usuario | Riesgo como 0.13 y confianza como 0.34: números sin significado para un agrónomo. | 2 | Riesgo como **Bajo/Medio/Alto** con el índice al lado; confianza en %; decimales con coma (es-CO). |
| 3 | Control y libertad | Cambiar alternativa, semilla o mástil reiniciaba la corrida sin avisar. | 3 | Diálogo de confirmación que explica qué se pierde y que la semilla (el brote) se mantiene. |
| 3 | Control y libertad | Salir del modo grabación solo aparecía al pasar el mouse. | 2 | Esc siempre sale; el botón sigue oculto para no salir en el video, y el atajo se anuncia al entrar. |
| 4 | Consistencia | `Espacio` pausaba en automático e inspeccionaba en manual. | 3 | `Espacio` siempre pausa; `E` inspecciona en manual. |
| 4 | Consistencia | Botones de solo ícono junto a botones con texto; Cámara y Capas eran dos menús para la misma pregunta ("¿qué veo?"). | 2 | Un solo menú **Vista** con texto; la configuración de la corrida va en **Corrida**. |
| 5 | Prevención de errores | El mástil estaba entre las capas visuales, pero reinicia la simulación. | 2 | Movido a **Corrida**, con confirmación. |
| 6 | Reconocer en vez de recordar | Los atajos y los colores solo se veían en un menú. | 2 | Ayuda (`?`) con leyenda de colores, controles y origen de los datos; abre sola la primera vez. Los tooltips muestran el atajo. |
| 7 | Flexibilidad y eficiencia | Cinco velocidades sin un atajo para lo que más se quiere: ver el siguiente recorrido. | 2 | Tres velocidades (1×, 10×, 50×) y **Ir al recorrido**. |
| 8 | Diseño minimalista | El panel derecho mostraba cinco secciones a la vez y el izquierdo era una columna larga. | 2 | Pestañas: Bloque (Resumen, Clima, Plantas) y Robot (Sensores, Registro, Datos). |
| 8 | Diseño minimalista | Un aviso por cama (10 por recorrido) y etiquetas de estaciones siempre visibles. | 2 | Avisos agrupados ("3 alertas nuevas"); las etiquetas de los dataloggers son una capa que se puede apagar. |
| 9 | Recuperarse de errores | "Requiere rescate" no decía qué hacer. | 1 | El mensaje indica el rescate automático y la opción de tomar el control manual. |
| 10 | Ayuda | No había ayuda. | 2 | Panel de ayuda breve, en el contexto de la escena. |

## Leyes de Maeda aplicadas

1. **Reducir:** menos velocidades, un menú en vez de dos, pestañas en vez de columnas largas, avisos agrupados.
2. **Organizar:** la barra se lee de izquierda a derecha como una frase: qué escenario, cuándo, quién controla, qué veo. El panel derecho responde "¿cómo está el bloque?" y el izquierdo "¿qué hace el robot?".
3. **Tiempo:** **Ir al recorrido** salta la espera; la tarjeta de fin de recorrido resume en un vistazo lo que tomaría leer el registro.
4. **Aprender:** ayuda la primera vez, leyenda y el mismo vocabulario de la finca en toda la interfaz.
5. **Diferencias:** la interfaz es calma (índigo y blanco) para que el rojo de una alerta y el verde de "en campo" resalten.
6. **Contexto:** la escena es lo principal; los paneles se pliegan y las etiquetas 3D aparecen solo cuando importan.
7. **Emoción:** el cultivo se ve vivo y el cierre de cada recorrido se celebra con su resumen.
8. **Confianza:** la ayuda dice de dónde sale cada dato (Open-Meteo, entrevista con la empresa, supuestos) y el robot muestra si sus datos ya llegaron a la base.
9. **Fracaso:** la vista de comparación 2×2 sigue siendo densa; se acepta porque es la que se graba.
10. **Lo único:** quitar lo obvio (números crudos, menús duplicados) y añadir lo significativo (próximo recorrido, sincronización, niveles de riesgo).
