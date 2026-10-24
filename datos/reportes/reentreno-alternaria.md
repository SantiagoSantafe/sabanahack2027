# Intento de subir alternaria y bajar falsas alarmas en cámara (2026-10-24)

**Veredicto: no hay mejora demostrable. No recomiendo reemplazar `modelo_camara` (Mc_tr).** El mejor candidato por validación cruzada (CV) sube alternaria y baja falsas alarmas en el test, pero todos los IC95 se solapan, la ganancia de CV desaparece al corregir por comparaciones múltiples y la sensibilidad global baja. Es un resultado válido y se reporta tal cual.

Código: `resultados/ml/scripts/alt_common.py`, `alt_cv.py`, `alt_exp0..3.py`, `alt_feats.py`, `alt_boot.py`, `alt_final.py`, `alt_auc.py`. Salidas: `resultados/ml/modelo_camara_v2/` (`test_resultados.json`, cachés de OOF y rasgos, modelo exportado, `PARCHE_PANEL.md`). No se tocó `modelo_camara/` ni `panel_demo.py`. Cómputo total: ~35 min (13 min de rasgos CLIP, el resto son regresiones logísticas de segundos).

## Método
- Selección SOLO por CV agrupada: 342 capturas válidas de train+val, StratifiedGroupKFold de 5 pliegues por grupo de imagen de origen de DrBerry, 3 semillas de pliegue, todo promediado. En cada pliegue se excluyen también de la base de entrenamiento las imágenes originales DrBerry (y sus aumentos) del grupo retenido, para que no haya fuga de la versión limpia. Familia "tr" (sin DrBerry val), como el modelo actual.
- Métrica de selección fijada de antemano: S = media de (recall de clase alternaria, sensibilidad global) en los umbrales que dan 20 % y 30 % de falsas alarmas OOF en sanas. Se vigilan oídio y heliothis. Referencia: receta de Mc_tr (C=0,1, peso 3, 3 aumentos) = BASE, S = 0,452.
- Test de 68 capturas (14 sanas, 21 grupos) y test limpio DrBerry: se miraron una vez, solo para el candidato elegido, el modelo actual y un control (ver abajo). No se usaron para elegir.

## Candidatos probados: ~43 (más las referencias BASE y V0)
- Pesos/hiperparámetros con rasgos en caché (12): C (3), peso extra de alternaria x1,5/2/3 (3), peso de capturas 1/5 (2), sin aumentos, solo preprocesado, sin sanas públicas, filtro de calidad de captura (brillo, contraste, sin mancha de hoja).
- Regla de decisión con costo asimétrico (desplazar la probabilidad de alternaria x k, equivale a otro intercepto): sobre BASE 1,5/2/3/5; sobre ensambles 2/3/4/5/8 y sobre 34s 2/3 (11).
- Rasgos nuevos (12): teselas 4x4, 3x3+4x4, 3x3+recortes centrados en manchas rojizas/oscuras (3 ventanas, media y máx de CLIP), 3x3+4x4+manchas, cada uno con 2 valores de C (8); manchas sintéticas pintadas sobre hojas sanas como alternaria extra, x2 pesos x2 rasgos (4).
- Ensamblar (con la receta de luz/preprocesado 4x4 y con BASE): 4 combinaciones, más 3x3+4x4 con la base completa de aumentos (4 variantes).
- No probado: aumentos de desenfoque/viraje específicos de alternaria (los aumentos de cámara ya los incluyen) ni recortes de más de 3 manchas. Ningún candidato usa tamaño de lesión.
Corrección simple: Bonferroni con alfa = 0,05/36 en el bootstrap de los 7 finalistas (con 43 la conclusión es igual; los IC95 sin corregir ya incluyen 0 salvo uno).

## Resultados en CV (OOF; objetivo FP 30 % de sanas; media de 3 semillas)
| | S | Sensibilidad | Alternaria | Oídio | Heliothis | Dif. S vs BASE, IC95 (bootstrap por grupo) | IC ajustado |
|---|---|---|---|---|---|---|---|
| BASE (receta actual) | 0,452 | 0,66 | 0,34 | 0,45 | 0,59 | | |
| BASE + peso alternaria x3 | 0,496 | 0,66 | 0,39 | 0,42 | 0,56 | +0,044 (+0,006, +0,069) | (-0,010, +0,095) |
| 3x3+4x4 base completa, peso 1 | 0,508 | 0,78 | 0,38 | 0,50 | 0,69 | +0,057 (-0,200, +0,165) | (-0,333, +0,241) |
| 3x3+4x4+manchas | 0,484 | 0,68 | 0,30 | 0,44 | 0,60 | +0,033 (-0,089, +0,129) | (-0,187, +0,203) |
| Ensamble de 3 (BASE, 34s, 34) | 0,519 | 0,74 | 0,38 | 0,48 | 0,66 | +0,067 (-0,077, +0,152) | (-0,141, +0,210) |
| **Ensamble de 3 + peso alternaria x3 (elegido)** | **0,567** | 0,75 | 0,49 | 0,43 | 0,64 | +0,116 (-0,058, +0,210) | (-0,122, +0,271) |

Elección: mayor S con la regla "el mayor k con que oídio y heliothis no bajen más de 0,05 frente a k=1" (k=3; k=5 y 8 dan más S pero cuestan oídio). S crece con k por construcción, porque solo premia alternaria: parte de lo ganado es reasignar oídio -> alternaria, no detectar más. Lo que sí es independiente del peso: el ensamble 3x3+4x4+manchas sube la sensibilidad global OOF de 0,66 a ~0,75 (IC también solapado).
Lo que no funcionó: filtro de calidad, peso extra de capturas, quitar aumentos, manchas sintéticas (S 0,43-0,45, por debajo de BASE), 4x4 solo. Ningún candidato resolvió que alternaria se parezca a sana: las lesiones son puntos rojizos diminutos que en pantalla->cámara casi no se ven.

## Resultados en test (UNA vez; 68 capturas, IC95 bootstrap por grupo)
Modelo exportado (`modelo_camara_v2/`): ensamble de 3 sondas, entrenado con capturas train+val (342; el actual solo con 278), umbral 0,959 = FP OOF 30 %. **Control**: la receta actual reajustada con train+val y el mismo método de umbral OOF (0,993), para separar el efecto de la receta del de los datos extra y del umbral.

| Test capturado | Actual Mc_tr (umbral 0,986) | Control (receta actual, train+val, umbral OOF) | Candidato v2 (ensamble, alt x3) |
|---|---|---|---|
| Sensibilidad global | 42/54 = 0,78 (0,61-0,92) | 37/54 = 0,69 (0,51-0,84) | 38/54 = 0,70 (0,53-0,86) |
| Falsas alarmas | 4/14 = 0,29 (0,00-0,75) | 2/14 = 0,14 (0,00-0,27) | 1/14 = 0,07 (0,00-0,23) |
| Alternaria (clase exacta) | 3/14 = 0,21 (0,00-0,73) | 3/14 = 0,21 (0,00-0,73) | 4/14 = 0,29 (0,00-0,73) |
| Alternaria marcada como enferma (cualquier clase) | 7/14 | 6/14 | 6/14 |
| Oídio | 8/22 | 7/22 | 7/22 |
| Heliothis | 16/18 | 14/18 | 14/18 |
| Exactitud 4 clases | 37/68 = 0,54 | 36/68 = 0,53 | 38/68 = 0,56 |
| AUC enferma vs sana (umbral libre) | 0,84 (0,68-0,94) | 0,86 (0,74-0,95) | 0,91 (0,81-0,98) |
| AUC alternaria vs sana | 0,70 (0,46-1,00) | 0,75 (0,56-1,00) | 0,79 (0,59-1,00) |
| Test limpio DrBerry: sens / FP / alternaria | 42/54, 0/14, 2/14 | 38/54, 0/14, 1/14 | 39/54, 0/14, 0/14 |

Lectura honesta:
1. Alternaria pasa de 3/14 a 4/14: una imagen, IC 0-0,73 en ambos. No es una mejora. Marcada como enferma baja de 7/14 a 6/14.
2. Las falsas alarmas bajan de 4/14 a 1/14, pero a costa de sensibilidad (0,78 a 0,70): es un punto de operación distinto, no un modelo mejor. El umbral de CV apuntaba a FP 0,30 y en test salió 0,07: con 14 sanas el umbral no se puede calibrar. El control (receta vieja con ese mismo umbral) hace casi lo mismo (2/14 y 0,69), así que la caída de falsas alarmas viene del umbral, no del ensamble.
3. El único indicio real a favor es el AUC (umbral libre) 0,84 -> 0,91 y 0,70 -> 0,79 en alternaria, pero los IC se solapan por completo y no se midió con corrección múltiple.
4. En test limpio DrBerry alternaria cae a 0/14 en el candidato: el peso x3 no se traduce en reconocer lesiones reales.

## Recomendación
No adoptar. Mantener Mc_tr con su umbral. Si se prioriza no perder enfermas, usar Mc_tr crudo (sens 0,85, FP 0,43 según reentreno-camara.md), no el v2. Si se quisiera seguir, el único camino con señal es 3x3+4x4+manchas, que exigiría más capturas de alternaria (hoy 41 en train, 13 en val, 14 en test) o video real. El candidato v2 queda exportado solo para pruebas.

## Límites
1. Test de 68 capturas y 14 sanas, de una sesión, con las mismas hojas que el test de DrBerry; las diferencias de 1-3 imágenes no son significativas.
2. S se optimizó sobre la misma OOF que se usó para ordenar ~43 candidatos: el ganador está sesgado hacia arriba (por eso la corrección y el IC solapado). El CV no es anidado.
3. La CV da sensibilidades más bajas que la validación original (64 capturas) con la misma receta, porque aquí se excluye de la base el original limpio del grupo retenido; los números absolutos no son comparables entre ambos informes.
4. Los recortes de manchas dependen de umbrales de color supuestos; la clase alternaria se ve en tamaños de pocos píxeles tras pantalla->cámara.
5. El candidato triplica el cómputo CLIP por cuadro y requiere el parche (`PARCHE_PANEL.md`, no aplicado). La votación temporal no se evaluó.
