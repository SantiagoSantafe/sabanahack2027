# Reporte: escala / generalizacion-cultivos

Fecha: 2026-10-23 · Rol: generalizacion-cultivos · Reto "Berry Good Idea" (Sabana Hack)

## Qué hice

1. Bajé de EVA 2019-2025 (datos.gov.co, API SODA) el área de fresa, mora, frambuesa, uva, aguacate Hass, gulupa y arándano para 2023-2025, a nivel nacional y por departamento. Lo guardé en `escalabilidad/fuentes_cultivos/`.
2. Revisé fuentes primarias para cada cultivo: ICA (mora 2011, vid 2012), FINAGRO (marcos de referencia de mora, aguacate Hass y gulupa), UC IPM (Broome y Gubler-Thomas), NC State/UF (Strawberry Advisory System), Magarey 2005 (GIM, Tabla 2), AGROSAVIA (gulupa), USU (frambuesa) y la monografía BBCH. Las ecuaciones del Strawberry Advisory System estaban como imágenes; las descargué y las leí.
3. Conté en las copias locales las clases útiles de PlantVillage, PlantDoc, DrBerry y Afzaal y sus licencias. También confirmé que no existe un dataset público de mora ni de gulupa.
4. Diseñé el esquema `perfil_cultivo/v0.1` y escribí tres perfiles: `arandano.yaml`, `fresa.yaml` y `mora.yaml`. Sumé un catálogo de modelos para uva, frambuesa, aguacate y gulupa.
5. Escribí `motor_perfiles.py`. Carga los perfiles con herencia, los valida (fuentes, estados, clase `desconocido`, si el robot cabe en el pasillo, pendiente y altura de cámara) y corre 22 modelos con 6 motores genéricos en dos escenarios **sintéticos**. Las ecuaciones publicadas se comprueban contra puntos calculados a mano. Sale con código 0.
6. Escribí `escalabilidad/cultivos.md`: tablas comparativas, motores, cambios en robot y cámara, diseño del YAML, prioridad de expansión, niveles de producto, límites y frases para el pitch.

## Hallazgos principales

- **El mercado está fuera del arándano.** En 2025: arándano 906,72 ha; fresa, mora, uva, gulupa/cholupa y frambuesa suman 25.034 ha (27,6 veces más); con aguacate Hass, 97.478 ha más. Mora: 15.951,86 ha en 305 municipios. Fresa: 3.766,68 ha, el 43 % en Cundinamarca [EVA, V].
- **La fresa es el siguiente cultivo.** Comparte región y patógenos con el arándano. Tiene modelos con coeficientes y validados en fincas (en algunos años, el SAS de Florida redujo los fungicidas a la mitad) y el dataset de Afzaal 2021 (2.500 imágenes, 7 clases, CC BY 4.0).
- **La mora es el mercado grande, pero de pequeños productores.** El margen es de 18 % (FINAGRO Huila 2017). Va como robot compartido por asociación. No hay dataset público y el robot generaría el primero. El ICA ya pide recorrer el 10 % de las plantas en zigzag cada 1-2 semanas, y el robot reemplaza y documenta ese recorrido.
- **Seis motores genéricos** cubren todos los modelos encontrados: logit de humectación y temperatura (Wilson, Bulger, Broome), GIM de Magarey, Gubler-Thomas, reglas de umbral, acumulado en ventana y referencia externa. Un cultivo nuevo no requiere código.
- **Ningún modelo está validado en el trópico andino.** Cada uno lleva `estado_local: no_calibrado` y un plan de calibración por finca con las confirmaciones del triage.
- **El encaje del cuadrúpedo varía**: alto en fresa y arándano, medio en mora, gulupa, frambuesa y uva (en parral, con la cámara hacia arriba), bajo en aguacate Hass. Por eso el perfil declara `captura.plataforma` y el producto se ofrece en tres niveles: sensores y app, robot como servicio y robot en la finca.
- **Error de diseño encontrado y corregido.** La herencia total entre perfiles le pasaba la geometría del arándano a la fresa. Ahora solo se hereda lo operativo (fuentes, sensores, captura, alertas y registro).

## Archivos

- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/cultivos.md`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/perfiles/arandano.yaml`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/perfiles/fresa.yaml`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/perfiles/mora.yaml`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/perfiles/_modelos_otros_cultivos.yaml`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/motor_perfiles.py`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/validacion_perfiles.json`
- `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/fuentes_cultivos/` (EVA en JSON y LEEME)

## Límites

- Varias páginas respondieron 403 (APSnet, UMN, Ontario y Contexto Ganadero). Lo que sale solo de ellas está marcado NO VERIFICADO.
- Las geometrías de camas de fresa y de camellón de arándano vienen de EE.UU. y Chile; las de mora, aguacate y gulupa vienen de FINAGRO (Colombia). Las alturas de dosel, los pasillos y los ángulos de cámara son SUPUESTO.
- No implementé los coeficientes de Miles 2013 (antracnosis de arándano). El perfil los delega al módulo de riesgo del equipo y trae un respaldo GIM marcado como proxy.
- Los escenarios de clima del motor son sintéticos: prueban el código, no predicen nada.
- No toqué archivos de otros agentes. Leí `raw/`, `datos_aprendizaje.md`, `unit_economics_parametros.yaml` y `PROMPT_simulacion_camas.md`.

## Pendientes para el equipo

- Preguntar al mentor: ¿qué frutales venden hoy y con qué tipo de cliente (exportador o asociación)? Con eso se confirma la prioridad: fresa, luego mora y uva.
- Conectar `geometria` del YAML con `config/*.yaml` de la simulación de camas, para que la demo cambie de cultivo con un solo archivo.
- Que el módulo de riesgo exponga Miles 2013 como `referencia_externa` con el mismo contrato de entradas (W, T).
