# Reentreno con capturas reales de la cámara del D1 (2026-10-24)

Datos: 410 capturas nuevas (timestamp >= 2026-10-24T01): 278 train, 64 val, 68 test. Las 104 anteriores se descartaron. Descartes por vacías/oscuras: 0. Sin mancha de hoja tras corregir_color: 21 (se conservan). Los splits de capturas coinciden con los de DrBerry (mismas imágenes de origen).
Código: `resultados/ml/scripts/camara_features.py`, `camara_entrenar.py`, `camara_export.py`. Salidas: `resultados/ml/modelo_camara/` (`val_rejilla.csv`, `test_resultados.json`, caché de rasgos).

## Método
- Rasgos CLIP ViT-B-32 laion2b 3x3 de cada captura ROI, crudos y con el preprocesamiento del panel (corregir_color + recorte_por_color), más 3 aumentos leves por captura (aug_camara, fuerza 0,4).
- Tipos: **Bc** (datos de B + capturas crudas), **Lc** (datos de L4 + capturas preprocesadas), **Mc** (datos de B y de L4 + capturas crudas y preprocesadas). Familia **full** = como se pidió (incluye los originales de DrBerry val); familia **tr** = solo DrBerry train.
- Rejilla: C (7 valores), con/sin aumentos, peso de las capturas 1 o 3. Se elige con las 64 capturas de val (sens >= 0,90, mínimo de FP, desempate por exactitud). Umbral estricto alternativo: sens >= 0,80.
- **Fuga en la familia full**: B y L4 ya vieron los originales de DrBerry val, así que la val de capturas está contaminada. Ejemplo: Bc_full tiene FP 0,0 en val y 0,64 en test. Por eso el candidato a exportar sale solo de la familia tr.
- Test (68 capturas + test limpio DrBerry) se evaluó una vez, solo con los modelos ya elegidos.

## Resultados (sens = enfermas con alerta; FP = sanas con alerta; exact. = 4 clases)
| Modelo (entrada) | Umbral | Test capturado sens / FP / exact. / recall alternaria | Test limpio DrBerry sens / FP |
|---|---|---|---|
| B crudo | 0,671 | 1,00 / 1,00 / 0,50 / 0,57 | 0,815 / 0,14 |
| B preprocesado | 0,671 | 0,94 / 0,79 / 0,46 / 0,14 | 0,759 / 0,07 |
| L4 crudo | 0,728 | 0,74 / 0,71 / 0,46 / 0,29 | 1,00 / 1,00 (roto sin preproceso) |
| L4 preprocesado | 0,728 | 0,80 / 0,50 / 0,50 / 0,00 | 0,852 / 0,50 |
| Bc_tr (crudo) | 0,682 | 0,74 / 0,71 / 0,38 / 0,14 | 0,815 / 0,14 |
| Lc_tr (pp, umbral 0,791 / estricto 0,887) | | 0,85 / 0,64 / 0,47 / 0,29 ; estricto 0,80 / 0,43 / 0,50 / 0,29 | 0,78 / 0,21 ; 0,82 / 0,21 |
| **Mc_tr (pp, elegido)** | 0,986 | 0,78 / 0,29 / 0,54 / 0,21 | 0,778 / 0,00 |
| Mc_tr (crudo) | 0,986 | 0,85 / 0,43 / 0,52 / 0,36 | 0,796 / 0,29 |
| Mc_full (pp) | 0,932 | 0,82 / 0,50 / 0,49 / 0,29 | 0,870 / 0,29 |

IC95 bootstrap por grupo en test capturado (Mc_tr pp): sens 0,61–0,92 (42/54), FP 0,00–0,71 (4/14). Todos los IC son muy anchos: 14 sanas.

Matriz de confusión de Mc_tr pp en test capturado (filas = real, columnas = predicho; alternaria, heliothis, oidio, sana):
alternaria [3,2,2,7]; heliothis [1,16,0,1]; oidio [6,4,8,4]; sana [1,0,3,10].

Elección: por val, Mc_tr y Bc_tr empatan en lo esencial (FP val 0,4 frente a 0,3, una imagen de diferencia). Se eligió Mc_tr por su exactitud en val (0,80 frente a 0,72). Hay que decirlo así: la regla de mínimo de FP, aplicada literalmente, habría dado Bc_tr, que en test es el peor. Mc_tr con umbral estricto no difiere del normal: con la rejilla elegida ambos umbrales coinciden (0,986).

Votación temporal (simulada, 4 variantes sintéticas por captura, no es video): no ayuda de forma fiable. Mc_tr pp baja a sens 0,44 / FP 0,07; B sube a FP 0,93. El promedio de variantes aumentadas no equivale a 8 cuadros reales de la cámara.

## Recomendación para el panel
- Usar `modelo_camara` (Mc_tr) con corrección de color y auto-recorte activados (`"preprocesamiento": "panel"`). Es el único que baja las falsas alarmas en captura (0,29 frente a 0,50–1,00) sin romper el test limpio (FP 0,00).
- Coste: la sensibilidad cae a 0,78 frente a 0,94–1,00 de B, que alerta casi siempre (FP 1,00 en captura), así que su sensibilidad no vale nada. Si prima no perder enfermas, usar Mc_tr crudo (sens 0,85, FP 0,43).
- Verificado con `predict.py` (carga y salida válida); `predict.py` no aplica el preprocesamiento, el panel sí debe hacerlo.

## Límites honestos
1. 68 capturas y 14 sanas, de una sola sesión, con las mismas 68 hojas del test de DrBerry: IC enormes; diferencias de 1–3 imágenes no son significativas.
2. Exactitud de 4 clases ~0,5 en todos los modelos; alternaria y oídio se confunden con sana. El modelo no diagnostica bien con esta cámara; solo mejora el compromiso de alerta.
3. Umbral 0,986 extremo (probabilidades saturadas por el peso 3 en capturas) y elegido con 10 sanas de val; frágil. Los recuadros de train variaron (~30 valores) y la votación no se pudo validar sin video.
