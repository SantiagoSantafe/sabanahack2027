# Reentreno robusto a luz/color de pantalla (modelos L1-L4) y alineado con el preprocesamiento del panel

Fecha: 2026-10-24. Código: `resultados/ml/scripts/luz_common.py` (preprocesar + aumentos), `luz_features.py`, `luz_eval.py`, `luz_export.py`, `luz_lamina.py`. Salidas en `resultados/ml/modelo_luz/`: `tabla_comparativa.csv`, `flip_rate.csv`, `diferencias_pareadas.csv`, `matrices_confusion.json`, `modelos_resumen.json`, `publicas_split.csv`, `ejemplos_aumentos.png`. No se tocó `modelo_final/`, `modelo_aug_B/` ni `robot/panel_demo.py`. Cómputo total: unos 30 min en MPS (22 min de aumentos + rasgos, 1 min de entrenamiento/evaluación), dentro del tope de 75 min.

## 1. Qué se hizo

- **Preprocesamiento común** `preprocesar(im)` = `corregir_color` -> `recorte_por_color` (copia literal de las funciones del panel; si no hay mancha de hoja se usa la imagen corregida entera, como hace el panel). Se aplica en train, val, test, estrés, capturas y fuentes públicas. Las imágenes de DrBerry se trabajan a 640 px de lado (las capturas reales, a resolución nativa).
- **Aumentos de cámara** (`aug_camara`, antes del preprocesamiento): zoom parcial, gamma/ganancia con recorte de luces altas, contraste y saturación bajos, tinte cian/azul (45 %/25 %) con lavado hacia cian claro, hoja reducida en marco negro, franja de bisel oscuro con el cuarto detrás, perspectiva, viñeteo, discos de reflejo y velo, moiré, baja resolución, desenfoque, ruido y JPEG. Lámina de 12 ejemplos (fila de aumento y debajo su versión preprocesada): `modelo_luz/ejemplos_aumentos.png`. Calibrado mirando las capturas reales: **los aumentos son, en promedio, más fuertes que lo visto en las capturas** (a propósito, para cubrir el rango); los rangos son supuestos, no medidos.
- **Sondas** (estandarización + regresión logística balanceada, rasgos [global, media, máx] de teselas, CLIP ViT-B-32 laion2b). C por CV agrupada de 5 pliegues (las aumentadas siguen a su original), umbral por la regla de B (sensibilidad >= 0,90, mínimo de falsas alarmas) sobre OOF limpio y preprocesado de train+val.
  - **B0**: `modelo_aug_B` tal cual (umbral 0,671), evaluado crudo y con preprocesamiento.
  - **L1**: train+val preprocesados + K=6 aumentos preprocesados por imagen (C=0,01, umbral 0,627).
  - **L2**: L1 con teselas 4x4 (C=0,01, umbral 0,607).
  - **L3**: ensamble L1 + B0 (media de probabilidades, ambos sobre la imagen preprocesada; umbral 0,543 sobre OOF).
  - **L4 / L4x4**: L1 / L2 + hojas sanas públicas de entrenamiento (C=0,003; umbrales 0,728 / 0,741). El umbral se calcula solo con DrBerry (las sanas públicas no entran al cálculo del umbral).
- **L4, fuentes públicas sanas** (`publicas_split.csv`), partición 70/30 **por grupo** (hoja en PlantVillage, imagen de origen en PlantDoc, observación en iNaturalist): PlantDoc recortes verdes sin síntomas (451; 87 de entrenamiento con tope de 2 por imagen de origen, 140 retenidos de 19 imágenes), PlantVillage `Blueberry___healthy` (160 hojas; 112 de entrenamiento con 1 foto por hoja, 416 fotos retenidas de 48 hojas), iNaturalist sanas (41 de entrenamiento, 18 retenidas). Cada imagen de entrenamiento lleva 3 aumentos. Total: 240 sanas públicas (+720 aumentadas) frente a 46 sanas de DrBerry en train+val.
- **Licencias**: PlantVillage (CC BY-SA) y iNaturalist (CC con atribución en `raw/campo_ood/manifiesto.csv`) solo se usan para entrenar y evaluar. PlantDoc tiene imágenes de stock con copyright: uso interno, **no mostrarlas en la demo ni en el pitch** (la lámina de ejemplos solo usa imágenes de DrBerry).
- **Atención**: la ficha de secundarios decía "no entrenar con PlantDoc/PlantVillage/iNat". L4 lo hace por petición del usuario; por eso sus partes de entrenamiento dejan de ser externas y solo valen las partes retenidas.

## 2. Resultados

Test congelado: 68 imágenes (54 enfermas, 14 sanas, 21 grupos). Estrés realista = 3 variantes de `aug_camara` por imagen con semilla distinta a la de entrenamiento (204 filas); estrés fijo = las 8 perturbaciones sueltas del manifiesto de estrés de `modelo_aug` (476 filas), preprocesadas. Capturas = las 41 de 104 cuyo top-3 CLIP coincide con su origen (**todas son imágenes de train**: sirven solo de evaluación de dominio, nunca para elegir umbral). Todos los IC (en `tabla_comparativa.csv`) son bootstrap por grupo y son anchos; con 14 sanas y 5 sanas en capturas, casi ninguna diferencia es significativa.

| Modelo (entrada) | Test limpio: sens / FP / exact. | Estrés realista: sens / FP / exact. | Estrés fijo: sens / FP | Capturas (41): sens / FP / exact. | Alternaria recall (limpio / estrés realista / capturas) |
|---|---|---|---|---|---|
| B0 crudo | 44/54, 2/14, 0,735 | 146/162, 33/42, 0,466 | 308/378, 30/98 | 36/36, 5/5, 0,829 | 0,21 / 0,05 / 0,88 |
| **B0 preprocesado (como el panel)** | 41/54, 1/14, 0,618 | 128/162, 23/42, 0,456 | 298/378, 23/98 | 36/36, 4/5, 0,780 | 0,00 / 0,12 / 0,50 |
| L1 | 46/54, 4/14, 0,735 | 132/162, 29/42, 0,500 | 315/378, 44/98 | 35/36, 3/5, 0,756 | 0,36 / 0,33 / 0,13 |
| L2 (4x4) | 45/54, 6/14, 0,706 | 141/162, 29/42, 0,534 | 318/378, 51/98 | 36/36, 4/5, 0,780 | 0,14 / 0,26 / 0,63 |
| L3 (L1+B0) | 43/54, 6/14, 0,647 | 135/162, 27/42, 0,510 | 314/378, 47/98 | 36/36, 4/5, 0,805 | 0,07 / 0,21 / 0,50 |
| **L4** (L1 + sanas públicas) | 46/54, 7/14, 0,691 | 124/162, 25/42, 0,485 | 323/378, 53/98 | 36/36, **2/5**, 0,829 | 0,36 / 0,33 / 0,38 |
| L4x4 | 45/54, 7/14, 0,691 | 124/162, 25/42, 0,490 | 325/378, 55/98 | 36/36, 3/5, 0,805 | 0,29 / 0,33 / 0,50 |

**Flip rate** (% de las 10 variantes por imagen cuya clase difiere de la predicha sobre la imagen limpia; B original: 16 % con sus propios aumentos suaves; aquí los aumentos son bastante más duros): con aumentos de cámara `flip_aug` y con el estrés independiente (de `reentreno_aug.py`) `flip_ind`:

| | B0 crudo | B0 pre. | L1 | L2 | L3 | L4 | L4x4 |
|---|---|---|---|---|---|---|---|
| flip_aug | 37,5 % | 43,2 % | 40,0 % | 39,1 % | **34,6 %** | 38,7 % | 42,1 % |
| flip_ind | **22,9 %** | 34,9 % | 28,1 % | 28,5 % | 23,5 % | 27,1 % | 32,8 % |

**Falsas alarmas en las partes retenidas de las fuentes públicas** (hojas sanas; nunca vistas por ningún modelo):

| Modelo | PlantDoc (140 recortes, 19 imágenes) | PlantVillage (416 fotos, 48 hojas) | iNaturalist (18) | Todas (574) |
|---|---|---|---|---|
| B0 crudo | 73/140 | 5/416 | 12/18 | 90 |
| B0 preprocesado | 88/140 | 1/416 | 6/18 | 95 |
| L1 | 87/140 | 6/416 | 3/18 | 96 |
| L2 | 97/140 | 1/416 | 5/18 | 103 |
| L3 | 91/140 | 4/416 | 5/18 | 100 |
| **L4** | **10/140** | 0/416 | **0/18** | **10** |
| L4x4 | 8/140 | 0/416 | 0/18 | 8 |

Comparación pareada con B0 preprocesado (`diferencias_pareadas.csv`, bootstrap por grupo; solo lo significativo, IC 95 % que no cruza 0): L3 baja el flip -0,087 (IC -0,15 a -0,03) con aumentos de cámara y -0,113 (-0,20 a -0,03) con estrés independiente; L2 sube la sensibilidad en estrés realista +0,08 (0,02 a 0,14); L4 y L4x4 bajan las falsas alarmas en PlantDoc retenido -0,56 (-0,63 a -0,47) y en iNaturalist retenido -0,33 (-0,56 a -0,11). **Nada más es significativo**; en particular las falsas alarmas del test de DrBerry empeoran con L1-L4 respecto a B0 preprocesado (1/14 -> 4-7/14, no significativo con 14 sanas y 5 grupos de sanas).

## 3. Lectura honesta

1. **El desajuste importa**: el modelo B con el preprocesamiento del panel pierde sensibilidad en test limpio (41/54 = 0,76 frente a 44/54 = 0,81 crudo; ambas bajo el 0,90 de la regla) y su umbral deja de estar calibrado. Los modelos L restauran la sensibilidad con preprocesamiento (46/54 = 0,85 en L1/L4) y rescatan algo de alternaria (0,36 frente a 0,00-0,21 en test limpio).
2. **Nada supera a B de forma clara y uniforme.** B crudo sigue mejor en flip con estrés independiente y en capturas (alternaria 0,88, aunque con 0/5 sanas correctas y n=8). L1-L4 mejoran sensibilidad y alternaria bajo estrés, pero pagan falsas alarmas en las sanas de DrBerry (test y estrés fijo: 44-55/98 frente a 23-30/98). Ni el flip se resolvió: sigue en 35-43 % con aumentos duros.
3. **L4 es el único con una mejora estadísticamente clara, y es en falsas alarmas sobre hojas sanas públicas** (PlantDoc 88 -> 10/140, iNaturalist 6 -> 0/18). Cautela: la parte retenida de PlantDoc comparte dominio con la de entrenamiento (mismos sitios/estilo de stock; la partición es por imagen de origen, pero puede haber imágenes casi iguales de distinta fuente), así que esa mejora es en buena parte de dominio; iNaturalist (observadores distintos, n=18) es la señal más creíble. En DrBerry (finca) L4 no mejora las falsas alarmas (7/14) y en las capturas reales pasa de 4/5 a 2/5 (n=5, sin significancia).
4. Las capturas son solo 41, de train (fuga), y 5 sanas: sirven para descartar roturas, no para elegir.
5. El estrés realista mío es más duro que las capturas (B0 crudo: 33/42 falsas alarmas en estrés realista frente a 5/5 con n=5 en capturas, y sens 0,90 frente a 1,00). Conviene no tomar los números absolutos de estrés como predicción de la demo.
6. `recorte_por_color` falla a menudo en hojas lavadas (poca saturación tras el balance): en la lámina se ve que cae al encuadre completo o a un trozo. Eso limita a cualquier modelo.

## 4. Exportado y recomendación

Exportado **L4** (sonda 3x3; declara `"tiles": 3`) en `resultados/ml/modelo_luz/clip_probe_tiles3_luz.joblib` + `umbral.json` (0,728). `predict.load_classifier` lo carga; verificado con `pipeline/predict.py --weights ... --threshold umbral.json` sobre 3 imágenes del test congelado (salidas válidas, ~60 ms por imagen; ojo: `predict.py` no aplica `preprocesar`, el panel sí). L3 no se exportó (ensamble de dos sondas, no cabe en un único joblib sklearn). Las sondas sueltas de L1, L2, L4x4 están en `modelo_luz/cache/sk_*.joblib`.

Recomendación: **si el objetivo de la demo es reducir falsas alarmas con hojas sanas de otro origen, usar L4 con el preprocesamiento del panel; si lo que prima es no perder enfermas y consistencia entre cuadros, mantener B y votar varios cuadros.** Ninguno justifica afirmar que "ya es robusto a la cámara". El mejor candidato para un siguiente paso es L4 más votación temporal.

## 5. Desviaciones del encargo

- Rejilla de C reducida a 0,001-0,3 (6 valores) para ahorrar tiempo; B usó 0,0003-3 (L1/L2 eligieron C=0,01, L4 C=0,003).
- Sin remuestreo del umbral con las sanas públicas (umbral solo con DrBerry, regla de B).
- Sin L3 para 4x4 ni exportable; flip calculado con 10 variantes con dos generadores (aumentos de cámara y estrés independiente de `reentreno_aug.py`).
- Las capturas verificadas son 41 (criterio top-3 de `entrenar_capturas.py`, con mis rasgos globales).

## 6. Qué más mejorar (priorizado; sin depender de nuevas fotos propias)

| # | Propuesta | Costo | ¿Robot? |
|---|---|---|---|
| 1 | **Votación temporal en el panel** (media de probabilidades o mediana de los últimos 5-8 cuadros + histéresis para cambiar de clase). Ataca directamente "la clase cambia entre cuadros" sin reentrenar; se puede probar sin robot con las 10 variantes por imagen ya generadas. | 0,5 día | Solo para validarlo en vivo; el diseño y la prueba offline no |
| 2 | **Arreglar `recorte_por_color` para hojas lavadas** (bajar el umbral de saturación tras `corregir_color`, o usar un recorte por saliencia/CLIP/detector en lugar de HSV) y **decidir con datos si el panel preprocesa o no** según el modelo cargado (B crudo vs L preprocesado: no mezclar). Hoy la mitad de los recortes caen al cuadro entero. | 0,5-1 día | No (basta con las 104 capturas y el test) |
| 3 | **Calibrar los aumentos con medidas de las 104 capturas** (estadísticos de color/contraste/saturación y nivel de reflejos de la pantalla frente al original, comparación original-captura emparejada) en vez de a ojo, y volver a entrenar L4 con K mayor. Ahora los aumentos son más duros que la realidad, lo que quizá explica el costo en falsas alarmas de DrBerry. | 1 día | No |
| 4 | **Más sanas y más alternaria de fuentes públicas con licencia**, agrupadas, y un conjunto de validación de campo que no sea de la misma fuente (más iNaturalist con el mismo protocolo: hoy solo 60 sanas y 3 alternarias). También subir la parte retenida de iNaturalist a n>=50 para IC útiles. Alternaria es la clase débil (recall 0,0-0,4). | 1-2 días | No |
| 5 | **Cámara/pantalla del demo**: bajar el brillo de la pantalla, fijar un encuadre tight del ROI sobre la pantalla (hoja a pantalla completa, sin bisel ni cuarto), evitar reflejos de luminarias con el ángulo, y **sincronizar la captura con el cambio de imagen** (las 63 capturas desfasadas se vuelven datos válidos para entrenar/evaluar). Es la mejora de datos de dominio de mayor valor por costo. | 2-3 h de ajuste + repetir la corrida de 104 capturas | **Sí** |
| 6 | **Modelo**: ajuste fino parcial (últimas capas) o backbone mayor (ViT-L/14 o DINOv2) con los mismos aumentos, y TTA ligero (promediar con/sin `corregir_color`). Probable ganancia en alternaria (lesiones de ~25 px). | 1-2 días GPU | No |
| 7 | **Operación**: umbral y regla por clase (alternaria con umbral propio) y un criterio de rechazo "incierto, reintentar" cuando el flip entre cuadros es alto, en vez de forzar clase. | 0,5 día | No |
