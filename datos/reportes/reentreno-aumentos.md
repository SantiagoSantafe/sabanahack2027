# Reentreno con aumentos "pantalla vista por cámara" (sonda CLIP teselas 3x3)

Fecha: 2026-10-24. Todo lo nuevo está en `resultados/ml/modelo_aug/`; el modelo final (`modelo_final/`) no se tocó. Código: `pipeline/augment_screen.py`, `resultados/ml/scripts/reentreno_aug.py` y `reentreno_aug_export.py`. Tablas: `tabla_comparativa.csv`, `flip_rate.csv`, `diferencias_pareadas_vs_final.csv`, `matrices_confusion.json`, `modelos_resumen.json`.

## 1. Qué se hizo

- **Aumentos** (`augment_screen.py`, semilla fija por (semilla, imagen, versión)): brillo 0,6–1,4, contraste, gamma 0,6–1,6, saturación, tono ±12°, tinte azul/blanco/cálido y balance de blancos, hoja pequeña (reducir al 15–40 % del lado y re-ampliar), desenfoque gaussiano y de movimiento, moiré suave, viñeteo, reflejo especular, ruido, JPEG q30–80 y, con 30 %, marco de pantalla negro. Todos los parámetros son supuestos, no medidos con la cámara real.
- **K = 5** versiones por imagen (train: 278 → 1.390 aumentadas; val: 64 → 320). Cómputo total de aumentos y rasgos: unos 10 min en MPS (el límite era 45).
- **Sonda**: misma arquitectura (estandarización + regresión logística balanceada, rasgos [global, media, máx] de 9 teselas). C elegido por CV agrupada de 5 pliegues (aumentadas siempre en el mismo pliegue que su original; puntuación en originales). Se amplió la rejilla de C hacia abajo (0,0003–3); todos los modelos aumentados eligieron C = 0,003 (el final usa 0,3).
- **Umbral**: `choose_threshold` del pipeline (sensibilidad de enfermedad ≥ 0,90, mínimo de falsas alarmas, desempate al umbral más bajo; igual que el final).
- **Variantes entrenadas** (todas con el mismo test congelado, 68 imágenes, 54 enfermas y 14 sanas, 22 grupos):
  - **A** (lo pedido): train + aumentadas; umbral en val limpio (0,614).
  - **A0** (control): train sin aumentos, umbral en val limpio (0,728). Separa el efecto de los aumentos del de usar menos datos.
  - **Au**: el mismo modelo A, umbral en val limpio + val aumentado (0,763). Extra.
  - **B**: train+val + aumentadas, C y umbral por CV agrupada fuera de pliegue sobre dev limpio (0,671). Es el único comparable punto a punto con el final (mismos datos y mismo protocolo; cambia solo el aumento).
  - **F**: modelo final (train+val, C = 0,3, umbral 0,737).

## 2. Comparación (test congelado)

Sens = enfermas con alerta; FP = sanas con alerta; Acc = exactitud de 4 clases con la regla de umbral. IC95 bootstrap por grupo (1.000 réplicas). Con solo 14 sanas (unos 5 grupos) los IC de FP son enormes: la diferencia entre modelos casi nunca es significativa en FP.

| Condición | Modelo | Sens [IC] | FP [IC] | Acc |
|---|---|---|---|---|
| Test limpio | F final | 0,796 [0,57–0,98] | 0,357 [0,00–0,74] | 0,662 |
| | A | 0,815 [0,59–1,00] | 0,214 [0,00–0,40] | 0,662 |
| | Au | 0,815 [0,59–1,00] | 0,071 [0,00–0,23] | 0,691 |
| | **B** | 0,796 [0,57–0,98] | 0,286 [0,00–0,71] | 0,676 |
| | A0 (control) | 0,815 [0,59–1,00] | 0,286 [0,00–0,55] | 0,632 |
| Estrés sintético de `tabla_stress` (8 pert. x 68) | F | 0,783 [0,59–0,95] | 0,337 [0,00–0,64] | 0,649 |
| | A | 0,868 [0,70–1,00] | 0,490 [0,18–0,79] | 0,628 |
| | Au | 0,820 [0,60–1,00] | 0,194 [0,06–0,39] | 0,672 |
| | **B** | 0,810 [0,59–0,98] | 0,367 [0,06–0,71] | 0,676 |
| | A0 | 0,794 [0,60–0,95] | 0,347 [0,00–0,58] | 0,588 |
| Estrés "combinada" (la más dura) | F | 0,648 [0,41–0,87] | 0,643 | 0,426 |
| | A / Au / **B** | 0,870 / 0,796 / 0,796 | 0,643 / 0,429 / 0,429 | 0,529 / 0,559 / 0,574 |
| Test con aumentos propios (x3, semilla 9001) | F | 0,802 [0,63–0,95] | 0,548 | 0,515 |
| | A / Au / **B** | 0,852 / 0,796 / 0,796 | 0,619 / 0,452 / 0,548 | 0,598 / 0,618 / 0,632 |

Exactitud por clase (diagnóstico correcto), test limpio / estrés sintético: alternaria F 0,29 / 0,32, B 0,21 / 0,15; heliothis F 0,89 / 0,91, B 1,00 / 0,96; oídio F 0,73 / 0,64, B 0,68 / 0,81; sana F 0,64 / 0,66, B 0,71 / 0,63. Las matrices de confusión por modelo y condición están en `matrices_confusion.json` (p. ej. limpio, B: alternaria 3/14, heliothis 18/18, oídio 15/22, sana 10/14).

**Estabilidad (flip rate).** Para cada imagen de test se generan 10 variantes y se mide el % de variantes cuya clase decidida (con el umbral de cada modelo) difiere de la que da la imagen limpia. "Estrés independiente" = cadena de perturbaciones de `stress_pantalla.py` con parámetros aleatorios, programada aparte (no usa `augment_screen.py`, así que no favorece al modelo aumentado por construcción). "Aumentos propios" = `augment_screen` con semilla distinta de la de entrenamiento.

| Modelo | Flip estrés independiente [IC95] | Flip aumentos propios [IC95] | Cambio de sospecha sí/no (estrés indep.) | Imágenes con clase inconsistente (estrés indep.) |
|---|---|---|---|---|
| F final | 29,3 % [16–45] | 32,1 % [21–46] | 14,1 % | 60,3 % |
| A0 (sin aumentos) | 32,1 % | 36,3 % | 22,2 % | 66,2 % |
| A | 20,4 % [12–30] | 24,4 % | 12,5 % | 51,5 % |
| Au | 15,7 % [9–24] | 18,8 % | 8,4 % | 47,1 % |
| **B** | 16,5 % [8–27] | 18,7 % | 8,8 % | 41,2 % |

Diferencia pareada vs. el final (bootstrap por grupo, `diferencias_pareadas_vs_final.csv`): flip B −12,8 puntos [−25,1; −2,0] en estrés independiente y −13,4 [−23,2; −3,9] en aumentos propios; Au −13,5 [−26,8; −1,5] y −13,2 [−25,2; −2,3]; A −8,8 [−22,8; +3,3] (no significativo). En el test limpio B no cambia la sensibilidad (dif. 0,000) y la FP baja 7 puntos [−18; 0] (no significativo). En el estrés de 8 perturbaciones, B sube la sensibilidad +2,6 puntos [−2,1; +8,6] y la FP +3,1 [−9,5; +14,3] (ambas dentro del ruido).

## 3. Qué dice y qué no dice

- Los aumentos **no empeoran el test limpio** (B y Au iguales o mejores que F en sens, FP y exactitud, dentro del ruido) y **reducen el cambio de clase entre cuadros casi a la mitad** (29 % a 16–17 % en B/Au), con diferencia pareada que excluye el cero. Este es el resultado sólido.
- La mejora en **sensibilidad y FP bajo estrés es modesta y no significativa** para B; la mayor ganancia está en la perturbación "combinada" (sens 0,65 a 0,80, exactitud 0,43 a 0,57) y en ruido y JPEG, donde F y A0 caen (sens 0,65–0,69 en ruido).
- A (umbral en val limpio de solo 10 sanas) da el umbral más bajo (0,614) y se paga en FP bajo estrés (0,49). El umbral de val es ruidoso (10 sanas, 25 grupos), como ya ocurría con el modelo final.
- El control A0 demuestra que las mejoras vienen de los aumentos y no de otra cosa: sin ellos, con el mismo protocolo, el flip sube a 32 %.
- **Alternaria sigue siendo el punto débil y empeora un poco** (acierto 0,29 a 0,21 en limpio con B): 10 de 14 alternarias salen "sana" en limpio en ambos modelos. Los aumentos ganan en heliothis y oídio, no en alternaria. No hay evidencia de que arreglen la confusión heliothis/oídio/alternaria entre cuadros más allá de la bajada del flip.
- Salvedades: test de 68 imágenes y 14 sanas (IC muy anchos); el estrés es sintético y el evaluador independiente comparte ideas con los aumentos (los dos suponen reducción de resolución, ruido, tinte, JPEG); no se ha medido nada con la cámara real del D1 ni con pantalla real. En las 3 fotos de `imagenes_prueba/` usadas para verificar la carga, B clasifica 1_sana como sana (p_enf 0,46), pero A la marca como alternaria (0,63).

## 4. Recomendación

**Reemplazar el final por B (`clip_probe_tiles3_aug_dev.joblib` + `umbral_dev.json`), con la condición de aceptar que la ganancia comprobada es de estabilidad.** Cumple el criterio pedido: el test limpio no empeora (sens 0,796 igual, FP 0,286 frente a 0,357, exactitud 0,676 frente a 0,662) y el flip baja de forma significativa (−13 puntos). No promete más sensibilidad bajo estrés de forma demostrada, ni mejora alternaria. Antes de dejarlo como definitivo conviene medir 20–30 capturas reales de la pantalla con el D1 (en especial hojas sanas y alternaria), porque con 14 sanas de test no se puede afirmar que baje las falsas alarmas.

El `clip_probe_tiles3_aug.joblib` + `umbral.json` de la carpeta es el modelo A (lo pedido literalmente: train aumentado, umbral en val). No lo recomiendo: su umbral de val es el peor de las variantes bajo estrés. `Au` (`clip_probe_tiles3_aug_umbralaug.joblib`) es la alternativa si se prefiere menos falsas alarmas en estrés (FP 0,19), a cambio de menos datos de entrenamiento y de un umbral que depende de mis propios aumentos.

## 5. Archivos

- `resultados/ml/modelo_aug/clip_probe_tiles3_aug.joblib`, `umbral.json` (A, spec), `clip_probe_tiles3_aug_dev.joblib`, `umbral_dev.json` (B, recomendado), `clip_probe_tiles3_aug_umbralaug.joblib`, `umbral_umbralaug.json` (Au). Mismo formato que el final; verificado con `predict.py` (`--weights` y `--threshold`) sobre `1_sana`, `3_alternaria`, `4_heliothis`.
- Caché de rasgos en `resultados/ml/modelo_aug/cache/*.npz`; registro en `reentreno.log`.
