# Generalización a otros frutales: un motor, muchos perfiles de cultivo

Rol: **generalizacion-cultivos** · Sabana Hack, reto "Berry Good Idea" · 23 de octubre de 2026

**Para qué sirve.** Quien plantea el reto quiere vender la solución a muchos productores y de varios frutales. El arándano de la Sabana es solo el ejemplo de la demo. Aquí se analiza qué cambia al pasar a fresa, mora de Castilla, frambuesa, uva de mesa, aguacate Hass y gulupa. También se diseña el **perfil de cultivo**, un YAML que el sistema carga para que un frutal nuevo se agregue sin escribir código.

**Convenciones** (las mismas de `datos_aprendizaje.md` y `unit_economics_parametros.yaml`):
- **[V]**: lo leí en una URL o un archivo que abrí. Las URL están en la sección 13 y en el bloque `fuentes` de cada YAML.
- **CÁLCULO**: aritmética mía sobre cifras [V].
- **SUPUESTO**: valor de diseño, a validar con el mentor, el agrónomo o el piloto.
- **NO VERIFICADO**: solo lo vi en un resumen de búsqueda, o la página respondió 403.
- **CONTEXTO**: dato que trae el equipo y que este rol no verificó.

Ninguna línea de este documento es una recomendación de producto fitosanitario. La acción la decide el agrónomo en el triage.

---

## 0. En 30 segundos

1. **Cerca del 85 % del sistema no depende del cultivo**: el robot, la red de sensores, el registro de incidencias, el triage agrónomo→operario, el mapa de calor y el motor de riesgo. Lo que cambia por frutal cabe en un YAML de unas 180 líneas: geometría, fenología, enfermedades, modelos de riesgo con sus parámetros, clases visuales y cómo se monta la cámara. El 85 % es un SUPUESTO de diseño; la sección 1 muestra la lista de piezas.
2. **El mercado está fuera del arándano.** En 2025 Colombia tenía **906,72 ha** de arándano y **25.034 ha** de fresa, mora, uva, gulupa/cholupa y frambuesa, o sea **27,6 veces más**. Si se suma el aguacate Hass, el área fuera del arándano llega a **97.478 ha** (EVA 2025 [V], CÁLCULO). Sin perfiles de cultivo, ese mercado queda fuera.
3. **Seis motores genéricos de riesgo** corren todos los modelos publicados que encontré: el logit de humectación y temperatura (Wilson 1990, Bulger 1987, Broome 1995), el modelo genérico de infección de Magarey 2005, el índice de Gubler-Thomas, el acumulado en ventana (Aegerter 2003), las reglas de umbral (ICA, regla 3-10) y un motor que delega en un modelo externo y usa uno genérico de respaldo. Para un frutal nuevo solo se escriben parámetros. `motor_perfiles.py` lo demuestra: carga los 3 perfiles y el catálogo, corre **22 modelos** y reproduce a mano las ecuaciones publicadas.
4. **La fresa es el siguiente paso natural.** Es la misma Sabana (Cundinamarca tiene el 43 % del área [V]) y tiene los patógenos clave del arándano: *Botrytis* y *Colletotrichum*. Tiene además el único sistema de alerta con coeficientes publicados y validado en fincas comerciales, el **Strawberry Advisory System**: en algunos años redujo los fungicidas a la mitad [V]. Y existe un dataset de 7 enfermedades bajo CC BY 4.0 [V].
5. **La mora es el mercado más grande de bayas** (15.952 ha en 305 municipios [V]), pero de pequeños productores. FINAGRO calcula para mora en Huila un margen de **18 %** con un precio en finca de COP 1.300/kg (2017) [V]. Ahí se vende **un robot compartido por asociación**, no uno por finca. Tampoco hay dataset público de mora: **el robot construiría el primero**, y esa es una ventaja que no se copia.
6. **No hay modelos validados en el trópico andino** para ninguno de estos cultivos. Todos vienen de Florida, Ohio, California o Chile. Por eso cada modelo trae `estado_local: no_calibrado`, y el piloto calibra los umbrales con las detecciones confirmadas del robot. Así se responde la pregunta del jurado "¿y eso funciona aquí?" (rúbrica: Justificación).
7. **No todo frutal es para cuadrúpedo.** Encaja alto en fresa y arándano, medio en mora, gulupa y frambuesa, y medio-alto en el parral de uva, mirando hacia arriba. En aguacate Hass, con árboles a 6×6 m [V] en ladera, encaja bajo. El perfil declara `captura.plataforma` y con eso el mismo sistema funciona con un celular o un dron.

---

## 1. Qué es fijo y qué cambia por cultivo

| Capa | Qué contiene | ¿Cambia por cultivo? | Dónde vive |
|---|---|---|---|
| Plataforma | Navegación cama por cama, lectura de ArUco/QR, captura, cola de alertas, triage, registro, mapa de calor, panel | **No** | Código |
| Motor de riesgo | 6 motores genéricos (sección 5) | **No** | `motor_perfiles.py` |
| Modelo de visión base | Red compartida (ver `datos_aprendizaje.md`) | **No** | Pesos compartidos |
| **Perfil de cultivo** | Geometría, fenología, enfermedades, modelos con parámetros, clases visuales, cámaras, umbrales | **Sí** | `perfiles/<cultivo>.yaml` |
| Cabeza de visión por cultivo | Clasificador fino de las clases del perfil | **Sí** | `cabeza_modelo_vision` |
| Perfil de región/cultivar | Altitud, cultivar, fenología local (SUPUESTO: capa a construir) | Sí, por zona | `regiones/<zona>.yaml` |
| Perfil de finca/lote | Camas reales, sensores instalados, umbrales calibrados | Sí, por finca | `fincas/<finca>.yaml` |

El **registro de incidencias** usa los mismos campos en todos los cultivos (`registro_incidencia` en `arandano.yaml`). Eso es lo que permite un panel único para el vendedor con N productores y M frutales.

---

## 2. Tamaño de cada mercado en Colombia

Fuente: EVA 2019-2025 (MADR/UPRA), consulta SODA del 2026-10-23 [V]. Copia en `fuentes_cultivos/eva_2023_2025_frutales_nacional.json` y `fuentes_cultivos/eva_2025_frutales_por_departamento.json`.

| Cultivo | Área sembrada 2023 (ha) | Área sembrada 2025 (ha) | Municipios con registro 2025 | Departamentos principales 2025 (CÁLCULO) | Tipo de productor |
|---|---|---|---|---|---|
| Aguacate Hass | 69.369,03 | **72.443,58** | 261 | Antioquia 33 %, Caldas 21 %, Valle 12 %, Quindío 9 % | Exportador mediano y grande (SUPUESTO) |
| Mora | 17.511,16 | **15.951,86** | 305 | Cundinamarca 25 %, Santander 19 %, Huila 10 %, Nariño 9 % | Pequeño productor en ladera (ICA [V]) |
| Fresa | 3.591,04 | **3.766,68** | 127 | Cundinamarca 43 %, Antioquia 17 %, Cauca 15 %, N. de Santander 10 % | Mixto (SUPUESTO) |
| Uva ("Uva" en EVA) | 3.156,92 | **3.015,02** | 57 | Valle del Cauca 56 %, Huila 41 % | Mixto. Incluye Isabella para jugo (ICA [V]) |
| Gulupa o cholupa | 2.383,29 | **2.289,69** | 122 | Antioquia 33 %, Huila 20 %, Cundinamarca 16 %, Boyacá 15 % | Exportador pequeño y mediano (SUPUESTO) |
| Arándano (demo) | 639,67 | **906,72** | 65 | Boyacá 48 %, Cundinamarca 46 % | Empresarial y exportador |
| Frambuesa | 8,90 | **11,00** | 5 | Cundinamarca 50 %, Boyacá 50 % | Nicho |

Nota: el aguacate de todas las variedades suma 141.050,63 ha en 2025 [V]; aquí solo cuento Hass. "Uva Caimarona" (219,90 ha) va aparte y no está incluida.

**Lectura.** La mora tiene más de 17 veces el área del arándano, y la fresa unas 4 veces. La frambuesa casi no existe como cultivo comercial en Colombia: comparte perfil con la mora (mismo género), así que se agrega casi gratis, pero no justifica trabajo propio. En EVA, "gulupa o cholupa" junta dos especies de *Passiflora*.

---

## 3. Tabla comparativa

### 3a. Geometría y operación

| Cultivo | Sistema | Distancias | Altura del dosel | Pasillo libre para el robot | Cubierta y terreno |
|---|---|---|---|---|---|
| **Arándano** (referencia) | Arbusto en camellón; una hilera por cama | Camellón de 1,0 × 0,5 m (INIA, Chile [V]). En Sopó: 0,7 m entre plantas y 1,2 m entre camas, en invernadero [V]. 5.000-5.500 pl/ha (Asocolblue [V]) → 2,6-2,9 m entre hileras (CÁLCULO) | 1,0-2,0 m (SUPUESTO; la simulación usa lo mismo) | 0,5-2,0 m (SUPUESTO) | Campo, macrotúnel o invernadero; plano o pendiente suave |
| **Fresa** | Cama elevada baja con acolchado, doble hilera (NO VERIFICADO) | Camas a 1,52 m entre centros y de 20-25 cm de alto (NC State [V]) | 0,35-0,55 m desde el suelo del pasillo (SUPUESTO); en mesas de sustrato, 0,9-1,3 m (SUPUESTO) | 0,5-0,9 m (CÁLCULO con ancho de cama SUPUESTO) | Campo abierto o macrotúnel (Cajicá, 2.562 msnm [V]) |
| **Mora de Castilla** | Espaldera sencilla o doble T (el ICA recomienda doble T por aireación [V]) | 2,5 × 2,8 m, 1.429 pl/ha (FINAGRO Huila [V]); el ICA pide mínimo 3 × 3 m [V] | 0,5-2,0 m (SUPUESTO) | 1,0-2,0 m (SUPUESTO); ramas con espinas | Sobre todo en zonas montañosas, de 1.200 a 3.500 msnm, óptimo 1.800-2.000 (ICA [V]) |
| **Frambuesa** | Hilera con espaldera en T | 0,6-0,9 m en la hilera, ≥1,8 m entre hileras; ejemplo con 2,1 m entre centros; T de 1,5-1,8 m (Utah State/SARE 2009 [V]) | ~1,5-1,8 m (CÁLCULO desde la altura de la T) | ~1,0-1,4 m (SUPUESTO) | Macrotúnel habitual |
| **Uva de mesa** | Emparrado (parral): el follaje forma un techo; "no existe realmente zona de gotera" (ICA [V]) | n/d | Techo a ~1,8-2,2 m (SUPUESTO / NO VERIFICADO); los racimos cuelgan bajo el techo | Debajo del parral se circula libre (SUPUESTO) | Valle del Cauca a 800-1.600 msnm; **2 cosechas al año** gracias a la poda (ICA [V]) |
| **Aguacate Hass** | Árbol | 6 × 6 m, 278 pl/ha (FINAGRO Antioquia, 1.830 msnm [V]) | Varios metros (SUPUESTO) | 4-5 m entre copas (SUPUESTO) | Ladera |
| **Gulupa** | Espaldera (tutorado) | 3,5 × 2 m, 1.428 pl/ha (Guarne, 2.150 msnm [V]) o 4 × 2,5 m, 1.000 pl/ha (La Belleza [V]) | ~1,8-2,0 m (SUPUESTO) | ~1,5-2,5 m (SUPUESTO) | 1.400-2.200 msnm; semitecho plástico en fincas tecnificadas (AGROSAVIA 2022 [V]) |

### 3b. Enfermedades principales y modelos de riesgo publicados

| Cultivo | Enfermedades principales (agente) | Modelos de riesgo con ecuación o regla publicada | Validación del modelo |
|---|---|---|---|
| **Arándano** | Roya (*Thekopsora minima*, registrada en Colombia [V]), muerte descendente de brotes (las dos más importantes en el trópico alto según Valbuena-Gaona 2025 [V]), antracnosis (*Colletotrichum*), moho gris (*Botrytis*), oídio, *Alternaria* | Antracnosis: el módulo de riesgo del equipo usa Wilson 1990 (fruto de fresa) con una aproximación en arándano de Gillett y Schilder 2009; Miles et al. 2013 [V cita] no está implementado porque sus coeficientes no se obtuvieron [verificación técnica 2026-10-23]. Botrytis: Bulger 1987, tomado de la fresa. Roya: regla SUPUESTO; periodo latente de unos 10 días a 20 °C (PNW [V]) | Ninguno validado en Colombia |
| **Fresa** | Moho gris (*B. cinerea*), antracnosis (*C. acutatum*), oídio (*Podosphaera aphanis*), mancha angular (*Xanthomonas fragariae*), mancha foliar, pudrición de cuero (*Phytophthora cactorum*) | **Wilson 1990** y **Bulger 1987** en el Strawberry Advisory System, con coeficientes [V]. Oídio: Gubler modificado por Broome (METOS [V]). *P. cactorum*: GIM de Magarey [V] | SAS: 4 temporadas de ensayo y 5 en fincas comerciales de Florida; fungicidas a la mitad en algunos años [V] |
| **Mora de Castilla** | Moho gris (*B. cinerea*, el de mayor incidencia), antracnosis o "palo negro" (*C. gloeosporioides*), mildeo velloso (*Peronospora sparsa*), mildeo polvoso (*Oidium* sp.), roya (*Gerwasia lagerheimii*), marchitez (*Verticillium*, *Fusarium*, *Rosellinia*), agalla de la corona (ICA 2011 [V]) | **Reglas del ICA** [V]: antracnosis con ~25 °C, HR > 95 % y ≥ 4 h de película de agua; mildeo velloso con HR > 80 %, 17-20 °C y lluvias continuas. Prestados: Bulger 1987 para *Botrytis*; Aegerter 2003 en rosa para *P. sparsa*, con un promedio de 8,4 h de hoja mojada al día en 10 días [V] | Ninguno validado en *Rubus glaucus* |
| **Frambuesa** | Moho gris, pudrición de raíz por *Phytophthora* (USU 2009 [V]); roya amarilla, tizón de caña y *Didymella* (NO VERIFICADO: UMN dio 403) | Los de mora (*Botrytis*, *P. sparsa*); GIM con los parámetros de *Botrytis* en uva [V] | Ninguno |
| **Uva de mesa** | Mildeo velloso (*Plasmopara viticola*, 11-30 °C), moho gris (15-25 °C y HR ≥ 92 %), pudrición negra (*Guignardia bidwellii*, 20-25 °C), pudrición blanca (*Rosellinia necatrix*) (ICA 2012 [V]); oídio (*Erysiphe necator*, UC IPM [V]) | **Gubler-Thomas** para oídio (UC IPM [V]); **Broome 1995** para *Botrytis* (UC IPM [V]); regla 3-10 para mildiú (NO VERIFICADO); GIM para *Plasmopara* y *Guignardia* [V] | Gubler-Thomas en California desde 1995 [V]. Broome: 2 temporadas en uva de mesa de Chile, con ~50 % menos fungicida [V] |
| **Aguacate Hass** | Marchitez (*Phytophthora cinnamomi* y otros agentes; la de mayor frecuencia y pérdidas en Antioquia, Ramírez-Gil 2013 [V]); antracnosis (*C. gloeosporioides*) y pudrición del pedúnculo (*Lasiodiplodia*), con 29 % y 15 % de incidencia en poscosecha (Quintero-Rodríguez 2024 [V]); peca (*Pseudocercospora purpurea*, NO VERIFICADO) | No encontré ecuaciones de campo. Hay un GIM proxy para antracnosis y una regla de suelo saturado para *Phytophthora* (SUPUESTO) | Ninguno |
| **Gulupa** | Marchitez por *Fusarium oxysporum* (3-59 % de incidencia en Tolima; el resumen dice 4-59 %), mancha aceitosa (*Xanthomonas*, hasta 36 % en fruto), roña (*Cladosporium*, 2-10 %) (AGROSAVIA 2022 [V]) | Ninguno publicado que haya encontrado. Regla de humectación y lluvia (SUPUESTO) | Ninguno |

### 3c. Datos de imágenes públicos

| Cultivo | Dataset | Tamaño y clases | Licencia | Dominio | Lo que falta |
|---|---|---|---|---|---|
| Arándano | DrBerry [V local] | 410 imágenes: *Alternaria* 289, *Heliothis* 204, oídio 162, sana 82 (anotaciones) | CC BY 4.0 | Campo, Perú, celular, 1 día | Roya, antracnosis, *Botrytis*; vista desde el robot |
| Fresa | Afzaal et al. 2021 [V] | 2.500 imágenes y 7 clases: mancha angular 435, antracnosis de fruto 97, tizón de flor 208, moho gris 477, mancha foliar 615, oídio en fruto 135, oídio en hoja 533 | CC BY 4.0 (LICENSE de DatasetNinja [V local]) | Invernadero y campo, Corea; ~20 % de internet | Andes; antracnosis tiene pocas imágenes (AP 64-71 %) |
| Fresa | Mendeley k2ptxmfjhj [V local] | 5.610 imágenes y 8 clases (incluye sana), con aumento de datos | **CC BY-NC 4.0** (API pública de Mendeley Data, consultada [verificación técnica 2026-10-23]): uso **no comercial**, no sirve para entrenar el producto que se vende | Derivado de Afzaal y StrawDI | Lo mismo |
| Fresa | PlantVillage [V local] | *Leaf scorch* 1.109, sana 456 | CC BY-SA 3.0 | Laboratorio | Campo |
| Mora | **Ninguno encontrado** (búsquedas en Kaggle, Mendeley, Roboflow y Zenodo, 2026-10-23) | — | — | — | Todo: **el robot generaría el primero** |
| Frambuesa | PlantVillage / PlantDoc [V local] | Solo sana: 371 imágenes y 539 cajas | CC BY-SA 3.0 / CC BY 4.0 | Laboratorio / internet | Todas las enfermedades |
| Uva | PlantVillage [V local] | Pudrición negra 1.180, esca 1.383, tizón foliar 1.076, sana 423 | CC BY-SA 3.0 | Laboratorio | Mildiú y oídio en campo |
| Uva | HERMOS [V] | 914 imágenes y 13.904 etiquetas; mildiú, oídio, sana y otra | CC BY 4.0 | Turquía | Trópico |
| Uva de mesa | Niphad NGLD [V] | 2.726 imágenes; mildiú, oídio, pudrición bacteriana, sana | CC BY 4.0 | Celular, India | Trópico |
| Uva | PlantDoc [V local] | Hoja sana 205 y pudrición negra 125 (cajas) | CC BY 4.0 | Internet | — |
| Aguacate | K-Kotagiri (Mendeley) [V] | 435 imágenes: 216 enfermas sin nombre de enfermedad, 219 sanas | CC BY 4.0 | No declarado | Clases por enfermedad |
| Gulupa | Ninguno encontrado | — | — | — | Todo |

**Advertencia general.** Un modelo entrenado en PlantVillage logró 99,35 % en su propio test y **31,4 %** con imágenes de otras condiciones (Mohanty et al. 2016 [V]). Ningún dataset de esta tabla reemplaza las fotos tomadas por el robot en cada cultivo. Por eso el perfil siempre tiene la clase `desconocido` y un umbral de confianza para mandar la imagen a revisión.

---

## 4. Fichas cortas por cultivo

**Fresa: el primer paso de expansión.**
- Encaja bien con el cuadrúpedo. El cuerpo del D1 Ultra mide 0,42 m de alto [V], la misma altura del dosel de fresa, así que la cámara va encima del cuerpo y mira hacia abajo, sin mástil. Hay que vigilar dos cosas: no pisar el borde del acolchado y tener en cuenta que los frutos quedan tapados por las hojas. El perfil registra la cobertura de vista de cada cama.
- Con macrotúnel bajan las pudriciones y sube el oídio (Grijalba et al. 2015, Cajicá [V]). Por eso el perfil cambia el peso de cada modelo según la cubierta (`peso_por_variante`, SUPUESTO).
- Competencia: Saga Thorvald trata oídio con UV-C como servicio y no diagnostica (CONTEXTO); que opere en fresa no lo verifiqué en esta sesión. Las estaciones METOS ya venden modelos de enfermedad para fresa [V]. Nuestra diferencia es la confirmación visual cama por cama, el registro y la priorización.

**Mora de Castilla: el mercado grande, como servicio.**
- Hoy el ICA pide recorrer la finca cada semana o cada 15 días, en zigzag, en X o en W, y revisar el 10 % de las plantas, anotando todo en un formato [V]. El robot hace ese recorrido sobre el 100 % de las hileras de riesgo alto y llena el formato solo.
- Una misma planta tiene botones, flores, frutos verdes y maduros a la vez, así que la susceptibilidad nunca se apaga. El perfil usa `modo: continuo_por_planta`, y el robot cuenta por planta los órganos susceptibles para ponderar el riesgo.
- La ladera favorece al cuadrúpedo frente a una plataforma con ruedas: el D1 Ultra sube 30° de forma estándar y hasta 40° como máximo [V]. [Verificación técnica 2026-10-23: esos ángulos son de la ficha, medidos en laboratorio y sin mástil. El manual pide no girar en pendientes fuertes ("avoid making direct turns at large climbing angles") y no usar el robot en suelo resbaloso. Con un mástil de 1,4 m el centro de gravedad sube, así que el límite real con el kit puesto está **NO VERIFICADO** y hay que medirlo en el piloto. Mientras tanto conviene declarar no aptas las laderas de más de ~15° (SUPUESTO).] Las espinas y la batería de 1-2 h [V] lo limitan. Va más lento (0,3 m/s, SUPUESTO) y con más holgura lateral (0,3 m, SUPUESTO).

**Uva de mesa: modelos maduros y cámara hacia arriba.**
- Tiene los modelos mejor validados de la lista (UC IPM, y Broome probado en uva de mesa de Chile [V]).
- En parral, los racimos cuelgan bajo el techo de hojas. El robot circula por debajo con la cámara apuntando 60-90° hacia arriba (SUPUESTO). Es la geometría opuesta a la fresa, y solo cambia `captura.camaras` en el YAML.
- En el trópico hay dos ciclos al año disparados por la poda (ICA [V]). La fenología se lleva por lote con `disparador: fecha_poda`, no por calendario. La regla 3-10 necesita la longitud del brote, un dato que el motor marca como faltante si la visión no lo entrega (`validacion_perfiles.json`).

**Aguacate Hass: encaje bajo para el cuadrúpedo, perfil igual de útil.**
- El problema principal es la marchitez por *Phytophthora* y otros agentes de suelo [V], que se vigila con sensores de humedad del suelo, no con fotos de hojas. La antracnosis pesa sobre todo en poscosecha [V].
- Plataforma sugerida: sensores y app, con captura por celular del monitor o por dron (`captura.plataforma`). El cuadrúpedo solo cubriría el tronco y el tercio bajo de la copa.

**Gulupa: parecida a la mora.** Va en espaldera, tiene enfermedades de suelo (*Fusarium*) y de fruto (mancha aceitosa, roña) [V], y no tiene dataset ni modelos publicados. Sería un perfil que hereda la operación de la mora con clases propias.

**Frambuesa.** Usaría la misma cabeza de visión `rubus_v0` que la mora y el mismo motor. Por mercado, se agrega solo si un cliente de mora la pide.

---

## 5. Modelos de riesgo: los seis motores cubren todo lo encontrado

| Motor | Forma | Parámetros que pone el YAML | Modelos que lo usan |
|---|---|---|---|
| `logit_polinomico` | f = Σ coef·W^w·T^t; salida p = 1/(1+e^(−f)) o el logit tal cual | Lista de términos y umbrales | Wilson 1990, Bulger 1987, Broome 1995 |
| `gim_magarey2005` | f(T) = ((Tmax−T)/(Tmax−Topt))·((T−Tmin)/(Topt−Tmin))^((Topt−Tmin)/(Tmax−Topt)); W(T) = Wmin/f(T) ≤ Wmax [V] | Tmin, Topt, Tmax, Wmin, Wmax | Respaldo para cualquier hongo foliar sin modelo propio |
| `indice_gubler_thomas` | Índice 0-100: +20 por día con ≥ 6 h seguidas en la ventana, −10 si no; arranca tras 3 días seguidos [V] | Ventana térmica, horas, puntos, temperatura letal | Oídio de uva (UC IPM) y de fresa (METOS) |
| `regla_umbral` | Todas las condiciones se cumplen durante N días | Variable, operador, valor | Reglas del ICA para mora; regla 3-10; reglas SUPUESTO |
| `acumulado_ventana` | Promedio de una variable en una ventana de días ≥ umbral | Variable, días, umbral | Aegerter 2003 (*P. sparsa*) |
| `referencia_externa` | Delega en otro módulo (p. ej. la antracnosis de arándano de `riesgo/risk.py`: Wilson 1990 + Gillett y Schilder 2009, no Miles 2013 [verificación técnica 2026-10-23]) y usa un respaldo genérico | Referencia y bloque `respaldo_generico` | Antracnosis de arándano |

**Ecuaciones verificadas (las mismas que están en los YAML):**

| Modelo | Ecuación | Umbrales | Fuente |
|---|---|---|---|
| Antracnosis de fresa (Wilson 1990, FLSAS) | f = −3,7 + 0,33·W − 0,069·W·T + 0,005·W·T² − 9,3×10⁻⁵·W·T³ | p < 0,15 bajo; 0,15-0,50 moderado; ≥ 0,50 alto | Imagen de la ecuación en la página de NC State [V] |
| Botrytis de fresa (Bulger 1987, FLSAS) | f = −4,268 − 0,0901·W + 0,0294·W·T − 2,35×10⁻⁵·W·T³ | p < 0,50 bajo; 0,50-0,70 moderado; ≥ 0,70 alto | Ídem [V] |
| Botrytis de uva (Broome 1995) | Índice = ln(Y/(1−Y)) = −2,647866 − 0,374927·W + 0,061601·W·T − 0,001511·W·T² | ≤ 0 sin riesgo; < 0,5 bajo; 0,5-1 moderado; ≥ 1 alto. T se limita a 12-32 °C; HR ≥ 95 % cuenta como hora mojada; 4 h secas cortan el evento | UC IPM [V] |
| Evento de humectación (fresa) | Empieza con lluvia o rocío y termina tras 4 h secas; T es el promedio de las horas mojadas | — | NC State [V] |

W = horas de hoja mojada del evento; T = temperatura media durante el evento (°C).

**Parámetros GIM de Magarey et al. 2005, Tabla 2 [V] (los que sirven para estos cultivos):**

| Patógeno | Hospedero del estudio | Tmin | Topt | Tmax | Wmin (h) | Wmax (h) | r del ajuste |
|---|---|---|---|---|---|---|---|
| *Botrytis cinerea* | Uva | 10 | 20 | 35 | 4 | 10 | 0,94 |
| *Botrytis cinerea* | Flores de fresa | 5 | 25 | 35 | 8 | 18 | 0,13 (ajuste pobre) |
| *Botrytis cinerea* | Flores de uva | 1 | 25 | 34 | 1 | 12 | 0,99 |
| *Colletotrichum acutatum* | Fruto de fresa | 7 | 27,5 | 35 | 6 | 36 | 0,93 |
| *Guignardia bidwellii* | Uva | 7 | 27 | 35 | 6 | 24 | 0,74 |
| *Plasmopara viticola* | Uva | 1 | 20 | 30 | 2 | 14 | 0,99 |
| *Phytophthora cactorum* | Fruto de fresa | 6 | 20,5 | 35 | 1 | 3 | 0,85 |

**Control de las ecuaciones** (`motor_perfiles.py`, puntos calculados a mano): Wilson con W = 12 h y T = 25 °C da un logit de −0,3775 (p = 0,41, moderado). Bulger con W = 16 h y T = 20 °C da 0,6904 (p = 0,67, moderado). Broome con W = 12 h y T = 20 °C da un índice de 0,384 (bajo). El GIM da f(Topt) = 1 y f(Tmin) = 0. Los cinco controles pasan.

**Límites honestos de los modelos:**
- **Ninguno está validado en el trópico andino.** Todos traen `estado_local: no_calibrado`. Plan de calibración (SUPUESTO): en el piloto, cada alerta del modelo se cruza con lo que el robot confirma en las camas y con lo que confirma el agrónomo. Con eso se ajustan los umbrales por finca (`fincas/<finca>.yaml`), y el ajuste se versiona.
- **El índice de Gubler-Thomas se puede saturar en el trópico.** En el Valle del Cauca muchos días caen dentro de 21-29 °C, y el índice se quedaría en 100. Hay que calibrar la ventana.
- **Los modelos prestados** (Bulger en mora, Aegerter de rosa) son del mismo patógeno pero de otro hospedero. Sirven para ordenar el riesgo relativo entre camas, no para fijar una dosis ni un momento exacto.
- **La humectación foliar es la variable crítica.** El sensor va dentro del dosel, a la altura de los órganos susceptibles, y esa altura cambia por cultivo: 10-20 cm sobre la cama en fresa, 0,5-1,2 m en arándano, 1,0-1,5 m en mora. Si falta el sensor, HR ≥ 95 % cuenta como hora mojada (regla de UC IPM [V]), y hay que calibrarlo.

---

## 6. Qué cambia en el robot, la cámara y los sensores

Datos del robot: **D1 Ultra**: 630 × 360 × 420 mm, 16 kg, IP54, autonomía de 1-2 h, pendiente estándar de 30° y máxima de 40°, carga útil de 5 kg, de 0 a 40 °C (datasheet del fabricante, copia local en `raw/agibot_docs` [V]). **D1 MaxPro**: 1.230 × 530 × 730 mm, 64 kg, IP67, 45°, 5,5 h sin carga (Generation Robots [V]).

| Cultivo | Encaje del D1 | Cámaras (SUPUESTO) | Velocidad (SUPUESTO) | Riesgos físicos | Sensores extra | Plataforma alternativa |
|---|---|---|---|---|---|---|
| Arándano | **Alto** | 3 laterales: 0,35 m, 0,8 m (+30°, envés) y 1,2 m en mástil | 0,5 m/s | Dosel cerrado en pasillos de 1,2 m | — | — |
| Fresa | **Alto** en campo; **medio** en mesas | Cenital a 0,55 m (−50°) y lateral baja a 0,25 m (+20°, envés) | 0,4 m/s | Pisar el acolchado; frutos tapados | Humectación a ras de cama | Carro sobre rieles en mesas |
| Mora | **Medio** | 0,6 m, 1,0 m (+30°, envés) y 1,4 m en mástil | 0,3 m/s | Espinas, ladera > 30°, batería | Humedad del suelo (marchitez) | Celular del monitor si la pendiente > 30° |
| Frambuesa | **Medio** | Como mora, mástil hasta 1,6 m | 0,3-0,4 m/s | Macrotúnel estrecho | Humedad del suelo (*Phytophthora*) | — |
| Uva de mesa (parral) | **Medio-alto** | Hacia arriba, 60-90°, a 0,4-0,6 m | 0,5 m/s | Sin hileras que guíen la ruta: navegar con QR en postes | — | — |
| Aguacate Hass | **Bajo** | Tronco y tercio bajo de la copa | — | Árboles altos y ladera | **Humedad del suelo** (*Phytophthora*) | Dron o celular, con sensores y app |
| Gulupa | **Medio** | Como mora; mástil hasta 1,8 m | 0,3 m/s | Semitecho, ladera | Humedad del suelo (*Fusarium*) | — |

**La regla que hace escalable este punto:** la carga útil del D1 Ultra es de 5 kg [V], así que el mástil y las cámaras se diseñan como **un kit modular con soportes en 3 alturas y ángulo ajustable**. El perfil dice qué soportes usar en cada cultivo. No hay que fabricar un robot distinto por frutal.

El validador del motor ya revisa esto de forma automática con la geometría del YAML. Hoy marca que en arándano y fresa un pasillo de 0,5 m es menor que los 0,56 m que necesita el D1 (0,36 m más 0,10 m de holgura por lado), así que las camas con dosel cerrado se declaran no aptas. También avisaría si la pendiente supera 30° o si la cámara más alta queda por debajo del 60 % del dosel.

---

## 7. Diseño del perfil de cultivo (YAML)

### 7.1 Bloques del esquema `perfil_cultivo/v0.1`

| Bloque | Para qué lo usa el sistema | Ejemplo |
|---|---|---|
| `id`, `version`, `estado_perfil`, `hereda_de` | Identidad, versión y nivel de madurez (`borrador_demo` / `piloto` / `validado`) | `fresa`, `0.1.0` |
| `fuentes` | Diccionario id → URL. Toda cifra cita un id | `flsas_ncsu` |
| `mercado_colombia` | Priorizar la venta (no lo usa el robot) | 3.766,68 ha |
| `geometria` | Ruta del robot, aptitud de pasillos, mapa de calor por "unidad de inspección" (cama, hilera, árbol) | `sistema: camas_bajas` |
| `fenologia` | Qué órganos son susceptibles hoy; reloj por lote; disparador (`fecha_poda`, `fecha_trasplante`) | BBCH 55-59 → flor |
| `sensores_ambientales` | Variables requeridas, dónde va el sensor, definición de evento de humectación | `fin_tras_horas_secas: 4` |
| `modelos_riesgo` | Lista de modelos: `motor` y parámetros, umbrales, origen y `estado_local` | Wilson 1990 |
| `clases_visuales` | Clases de la cabeza de visión, mapeo a etiquetas de datasets públicos, clase `desconocido`, umbral de confianza | `afzaal2021: gray_mold` |
| `captura` | Plataforma, encaje, cámaras (altura y ángulo), velocidad, holgura, estrategia de muestreo | `cenital_cama 0,55 m` |
| `alertas` | Matriz de riesgo ambiental × hallazgo visual → prioridad, destino y plazo | P1 al agrónomo en 4 h |
| `registro_incidencia` | Campos comunes: finca, lote, cama, posición, órgano, clase, foto, estado del triage | Igual en todos |

Cada número lleva `estado: VERIFICADO | CALCULO | SUPUESTO | NO_VERIFICADO`. Así el agrónomo del cliente ve qué está probado y qué hay que medir, y el validador cuenta cuántos supuestos tiene cada perfil (hoy: 10 en arándano, 9 en fresa y 13 en mora).

### 7.2 Herencia: solo se hereda lo operativo

`hereda_de: arandano` en fresa y mora trae **solo** `fuentes`, `sensores_ambientales`, `captura`, `alertas` y `registro_incidencia`. La geometría, la fenología, los modelos y las clases son siempre propios del cultivo. Lo aprendí corriendo el validador: con herencia total, la fresa recibía la altura de dosel del arándano (2 m) y el validador avisaba que la cámara no cubría el tercio superior, un error que no existía. Ahora el motor tiene una lista blanca de bloques heredables (`HEREDABLES` en `motor_perfiles.py`).

### 7.3 Capas por encima del cultivo (para vender a muchos productores)

```yaml
# fincas/finca_ejemplo.yaml   (SUPUESTO: estructura propuesta, no implementada)
finca: finca_ejemplo
cultivo: fresa@0.1.0              # versión fija del perfil; se actualiza a propósito
region: sabana_bogota             # capa regional: altitud, cultivar, fenología local
lotes:
  - id: L1
    variante: macrotunel
    camas: {n: 24, largo_m: 40, pasillo_libre_m: 0.65}
    sensores: [est-07, hum-07a]
calibracion:                      # sale del piloto; versionada y firmada por el agrónomo
  botrytis_bulger1987_flsas: {umbrales: {moderado: 0.55, alto: 0.75}}
```

El orden de precedencia es **finca > región > cultivo**. Sale de cada confirmación del triage, que es una etiqueta (`datos_aprendizaje.md`). Esas etiquetas recalibran la finca y, sumadas entre fincas, el perfil del cultivo.

### 7.4 Cómo se agrega un cultivo nuevo (lista de trabajo)

| Paso | Quién | Esfuerzo (SUPUESTO) |
|---|---|---|
| 1. Copiar la plantilla y llenar `geometria`, `fenologia` y `mercado` con fuentes | Agrónomo del vendedor | 1-2 días |
| 2. Buscar modelos publicados y llevarlos a un motor. Si no hay, usar un GIM con los parámetros del género o reglas de la guía del ICA | Agrónomo y datos | 2-3 días |
| 3. Mapear las clases visuales a datasets públicos y declarar los huecos | Datos | 1 día |
| 4. Elegir soportes de cámara del kit y velocidad, y correr el validador | Ingeniería | 1 día |
| 5. Piloto de una temporada: capturar, etiquetar en el triage, calibrar umbrales y pasar a `estado_perfil: piloto` | Equipo y cliente | 1 ciclo de cultivo |

El código no cambia en ningún paso, salvo que aparezca un tipo de modelo que no encaje en los 6 motores.

---

## 8. Prioridad de expansión

Puntaje de 1 (bajo) a 3 (alto). Los criterios y los pesos iguales son SUPUESTO; los datos detrás de cada nota están en las secciones 2 a 6.

| Cultivo | Mercado (EVA) | Encaje del robot | Madurez de modelos | Datos visuales | Sinergia con la Sabana | **Total** | Cómo entrar |
|---|---|---|---|---|---|---|---|
| **Fresa** | 2 | 3 | 3 | 3 | 3 | **14** | Mismo producto que en arándano; primer cliente fuera de la demo |
| **Mora** | 3 | 2 | 1 | 1 | 3 | **10** | Robot como servicio por asociación; el dataset propio es la ventaja |
| **Uva de mesa** | 2 | 2 | 3 | 2 | 1 | **10** | Valle del Cauca y Huila; con los modelos de UC IPM |
| **Gulupa** | 2 | 2 | 1 | 1 | 2 | **8** | Después de la mora, heredando su operación |
| **Aguacate Hass** | 3 | 1 | 1 | 1 | 1 | **7** | Solo sensores y app con dron o celular; vender el perfil, no el cuadrúpedo |
| **Frambuesa** | 1 | 2 | 1 | 1 | 3 | **8** | Va "gratis" con el perfil Rubus de la mora |

---

## 9. Qué significa para el modelo comercial (sin cifras de precio)

Los precios y el retorno están en el trabajo de finanzas y modelo de negocio (`unit_economics.py`). Este rol solo propone **tres niveles de producto**, que salen de la tabla de encaje:

| Nivel | Qué incluye | Cultivos donde aplica |
|---|---|---|
| **A. Sensores y modelos** | Estación y perfil de cultivo con modelos de riesgo, alertas, registro y app para fotos del monitor | Todos, incluido el aguacate Hass y los pequeños productores de mora |
| **B. Robot como servicio** | Nivel A más visitas del robot, compartido entre fincas de una asociación | Mora, gulupa, frambuesa |
| **C. Robot en la finca** | Nivel A más robot dedicado delante del aspersor | Arándano, fresa de exportación, uva de mesa |

El perfil de cultivo es lo mismo en los tres niveles. Lo único que cambia es `captura.plataforma`.

---

## 10. Límites y riesgos (rúbrica: Justificación)

| Riesgo | Por qué importa | Mitigación |
|---|---|---|
| Modelos sin validar en el trópico andino | Pueden subestimar o sobreestimar el riesgo | `estado_local: no_calibrado`, calibración por finca en el piloto y uso de los modelos para **priorizar camas**, no para decidir dosis |
| Fenología continua (arándano, fresa, mora) y cosechas por poda (uva) | Los modelos de clima templado asumen una sola temporada | Reloj fenológico por lote o por planta; la visión cuenta los órganos susceptibles |
| Datasets de laboratorio o de otro país | Exactitud de 99 % en laboratorio y 31 % fuera de él (Mohanty 2016 [V]) | Clase `desconocido`, umbral alto al inicio (0,7 en mora) y ciclo de etiquetado en el triage |
| No hay dataset de mora ni de gulupa | El modelo arranca débil | Transferencia (*Botrytis* de fresa, hojas de *Rubus*) y meta de 2.000 imágenes propias para la v1 (SUPUESTO) |
| Licencia CC BY-SA 3.0 de PlantVillage | La cláusula "compartir igual" puede chocar con un modelo comercial cerrado | Usarla solo para preentrenar y revisar con un abogado (`datos_aprendizaje.md`) |
| Geometrías fuera del alcance del D1 (pendiente > 30°, árboles, pasillos < 0,56 m) | El robot no pasa o no ve | El validador lo detecta desde el YAML; se pasa a nivel A o B |
| Fuentes de geometría de otro país (Chile y EE.UU. para camas) | Pueden no coincidir con las fincas colombianas | Están marcadas, y el perfil de finca las sobrescribe con medidas reales |

---

## 11. Frases para el pitch

- "Lo que cambia entre un arándano y una fresa cabe en un archivo de configuración: el robot, los sensores, el registro y el triage son los mismos. Hoy tenemos tres perfiles que el motor ya carga y valida."
- "Fuera del arándano hay 27 veces más hectáreas de fresa, mora, uva y gulupa en Colombia. Nuestra solución entra a ellas cambiando un YAML, no el robot."
- "En mora no existe un solo dataset público de enfermedades. El primer productor que use el robot construye el primero, y esa ventaja no se copia."

---

## 12. Archivos entregados

| Archivo | Qué es |
|---|---|
| `escalabilidad/cultivos.md` | Este documento |
| `escalabilidad/perfiles/arandano.yaml` | Perfil base (demo) |
| `escalabilidad/perfiles/fresa.yaml` | Primer cultivo de expansión, con modelos SAS y METOS |
| `escalabilidad/perfiles/mora.yaml` | Mora de Castilla, con reglas del ICA y modelos prestados |
| `escalabilidad/perfiles/_modelos_otros_cultivos.yaml` | Catálogo de modelos para uva, frambuesa, aguacate y gulupa |
| `escalabilidad/motor_perfiles.py` | Cargador, validador y motor genérico de riesgo; se corre con `datos/.venv/bin/python -I` |
| `escalabilidad/validacion_perfiles.json` | Salida del motor: validación y 22 modelos en dos escenarios **sintéticos** (húmedo y seco) |
| `escalabilidad/fuentes_cultivos/` | Consultas EVA 2023-2025 guardadas (JSON) y su LEEME |

Para reproducir: `/Users/santiagosantafe/Downloads/SabanaHack/datos/.venv/bin/python -I /Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/motor_perfiles.py` (sale con código 0 si no hay errores).

---

## 13. Fuentes

Abiertas en esta sesión [V], salvo donde se indica:

- EVA 2019-2025, Base Agrícola (MADR/UPRA), API SODA: https://www.datos.gov.co/resource/uejq-wxrr.json
- NC State, modelos de riesgo de antracnosis y *Botrytis* en fresa (ecuaciones FLSAS, umbrales, GIM): https://ipm.ces.ncsu.edu/development-of-anthacnose-and-botrytis-strawberry-fruit-infection-risk-models
- UF/IFAS AE450, Strawberry Advisory System: https://ask.ifas.ufl.edu/publication/AE450
- NC State, camas de fresa en plasticultura: https://strawberries.ces.ncsu.edu/strawberries-plasticulture-considerations-soil
- Grijalba et al. 2015, macrotúnel en Cajicá, Agronomía Colombiana 33(2): https://revistas.unal.edu.co/index.php/agrocol/article/view/52000
- METOS, modelos de enfermedad en fresa: https://metos.global/en/?p=49800
- Afzaal et al. 2021, Sensors 21:6565: https://pmc.ncbi.nlm.nih.gov/articles/PMC8513076/
- Dataset de fresa con aumento de datos (Mendeley k2ptxmfjhj; metadatos locales): https://data.mendeley.com/datasets/k2ptxmfjhj
- UC IPM, *Botrytis* en uva (Broome 1995): https://ipm.ucanr.edu/DISEASE/DATABASE/grapebotrytis.html
- UC IPM, oídio de la vid (Gubler-Thomas): https://ipm.ucanr.edu/DISEASE/DATABASE/grapepowderymildew.html
- Magarey, Sutton y Thayer 2005, Phytopathology 95:92-100 (GIM, Tabla 2): https://www.suddenoakdeath.org/wp-content/uploads/pdf/PHYTO-95-0092%20Magarey%20nappfast.pdf
- Aegerter, Nuñez y Davis 2003, Plant Disease 87:732-738 (registro AGRIS): https://agris.fao.org/search/en/records/65dedbd26eef00c2cea15648
- ICA 2011, Manejo fitosanitario del cultivo de la mora: https://www.ica.gov.co/getattachment/b7e061eb-ebd3-4f80-9518-c771712405eb/-nbsp3bmanejo-fitosanitario-delcultivo-de-la-mora.aspx
- ICA 2012, Manejo fitosanitario del cultivo de la vid: https://www.ica.gov.co/getattachment/cfd74811-9005-41ca-87b3-57b7984c5afb/Manejo-fitosanitario-del-cultivo-de-la-vid.pdf
- FINAGRO, MRA de mora de Castilla (Huila): https://www.finagro.com.co/sites/default/files/2022-05/mora_castilla_huila.pdf
- FINAGRO, MRA de aguacate Hass (Antioquia): https://www.finagro.com.co/sites/default/files/2022-05/aguacate_hass_mra.pdf
- FINAGRO, MRA de gulupa (Santander): https://www.finagro.com.co/sites/default/files/2022-05/gulupa.pdf
- FINAGRO, MRA de gulupa (Antioquia): https://www.finagro.com.co/sites/default/files/2022-05/gulupa_antioquia.pdf
- Rodríguez-Polanco et al. 2022 (AGROSAVIA), gulupa en Tolima: https://portal.amelica.org/ameli/journal/130/1302674007/html/
- Ramírez-Gil 2013, marchitez del aguacate (UNAL): https://repositorio.unal.edu.co/handle/unal/11847
- Quintero-Rodríguez et al. 2024, poscosecha de aguacate Hass, Revista Politécnica: https://www.redalyc.org/journal/6078/607878976011/607878976011.pdf
- Rowley, Black y Drost 2009, frambuesa en macrotúnel (USU/SARE): https://sare.org/wp-content/uploads/Fall-bearing-Raspberries-in-High-Tunnels.pdf
- Mohanty, Hughes y Salathé 2016: https://pmc.ncbi.nlm.nih.gov/articles/PMC5032846/
- HERMOS (uva): https://data.mendeley.com/datasets/j4xs3kh3fd/2
- Niphad NGLD (uva de mesa): https://data.mendeley.com/datasets/8nnd2ypcv3/1
- K-Kotagiri (aguacate): https://data.mendeley.com/datasets/6zy6wxhf2v/1
- Monografía BBCH, 2.ª ed. 2001: https://www.daera-ni.gov.uk/sites/default/files/2026-07/BBCH-Skala_en.pdf
- AgiBot D1 MaxPro (Generation Robots): https://www.generationrobots.com/en/404440-agibot-d1-max-pro-quadruped-robot.html
- Archivos locales leídos (de otros agentes, sin modificar): `raw/agibot_docs/D1_Ultra_Datasheet_*.pdf`, `raw/drberry/_export_meta.json`, `raw/plantvillage/hf_splits/*`, `raw/plantdoc/PlantDoc-Object-Detection-Dataset/train_labels.csv`, `raw/fresa_afzaal2021_datasetninja/*.tar` (LICENSE.md), `raw/fresa_mendeley_k2ptxmfjhj_test/_mendeley_metadata.json`, `raw/ciencia_uptc_valbuena2025`, `raw/ciencia_rfnam_royas2012`, `raw/ciencia_ucundinamarca_tesis_sopo`, `raw/paramsim_*` (Asocolblue, INIA, PNW, PMC11333449), `PROMPT_simulacion_camas.md`.

**Solo vistas en resultados de búsqueda o con respuesta 403 (NO VERIFICADO):** la regla 3-10 (https://www.agric.wa.gov.au/table-grapes/downy-mildew-grapevines), las enfermedades de frambuesa de UMN Extension (https://extension.umn.edu/raspberry-farming/raspberry-diseases), los resúmenes de Bulger 1987 y Aegerter 2003 en APSnet, la peca del aguacate (Contexto Ganadero), las dimensiones de la espaldera de mora (Infoagro) y la doble hilera por cama en fresa (UF/IFAS).
