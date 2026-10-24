# Reporte del agente escala / datos-aprendizaje

Fecha: 2026-10-23. Entregable: `/Users/santiagosantafe/Downloads/SabanaHack/datos/escalabilidad/datos_aprendizaje.md`. No escribí en ninguna otra carpeta.

## Qué hice

1. **Revisé los archivos del equipo**: la ficha de DrBerry, el reporte del entorno, el prompt de simulación, las preguntas del mentor, las copias locales de PlantVillage y PlantDoc, el registro de iNaturalist y `operacion/capacidad.py`.
2. **Verifiqué en la web** la Ley 1581 de 2012 y el Decreto 1377 de 2013 (los dos en alcaldiabogota.gov.co), además de:
   - Decisión 486 (secreto empresarial) y Ley 256 de 1996, art. 16.
   - Decreto 090 de 2018 y Circular 005 de 2017 de la SIC, ambos en fuentes secundarias.
   - FedAvg y Flower; Mohanty 2016; Hestness 2017; a16z 2019.
   - Código de Conducta de la UE (2018) y densidad de siembra de Asocolblue.
3. **Diseñé el ciclo de datos**, que cubre:
   - Esquema del evento y niveles de etiqueta L1–L3.
   - Sesgos del ciclo y aprendizaje activo con presupuesto de 20 imágenes por semana.
   - Subida selectiva desde el borde.
   - Comparación entre entrenamiento centralizado y federado, con las fases de adopción.
   - Jerarquía de modelos: backbone, cultivo, zona o variedad, y calibración por finca.
   - Control de deriva por estrato y métricas de operación.
   - Gobierno de datos, anonimización, marco legal y efecto de red, con sus límites.

## Hallazgos clave

- **No hay datos públicos de enfermedades de arándano desde la vista de un robot ni en condiciones andinas.** DrBerry es una finca peruana en un solo día. PlantVillage y PlantDoc solo traen hoja de arándano sana. La ventaja competitiva tiene que ser el flujo de etiquetas de campo.
- **Etiqueta retroactiva de pre-síntoma.** Cuando un tramo se confirma, las fotos de pases anteriores del mismo tramo se vuelven candidatas a "pre-síntoma". Solo es posible con ubicación por cama y pases repetidos, así que una app de celular no puede hacerlo.
- **El presupuesto de falsas alarmas obliga a agregar la evidencia por tramo.** Con unas 42.000 fotos por semana y un presupuesto de 5 falsas alarmas, cada foto tendría que equivocarse menos de 1,2 veces en 10.000. Por eso la alerta va por tramo, con el filtro del agrónomo antes de mover al operario (cálculo con SUPUESTOS).
- **Una finca sola no puede medir su sensibilidad.** Con 8 de 9 focos, el intervalo de confianza va de 57 % a 98 %; una red de 30 fincas la mide entre 86 % y 90 % (Wilson 95 %). Es un argumento de efecto de red que se puede vender.
- **Subida selectiva.** Se suben unos 60 MB por semana y por finca en vez de unos 12,6 GB brutos. El costo de nube crece con las etiquetas, no con las hectáreas.
- **Riesgos de licencia para vender.** Ultralytics es AGPL-3.0 y PlantVillage es CC BY-SA 3.0; hay que resolverlos antes de comercializar.

## Pendientes

- Confirmar con el mentor las preguntas 6, 13, 17, 18, 20, 27 y sobre todo la 28 (falsas alarmas que tolerarían por semana).
- Texto oficial vigente del Decreto 090 de 2018 y la lista actual de países adecuados de la SIC.
- Requisitos de registro BPA del ICA y obligación de reportar plagas de control oficial (NO VERIFICADO).
- Capacidad de cómputo a bordo del D1 (NO VERIFICADO).
- Exponente real de la curva de aprendizaje, que se medirá en el piloto.
- Revisión legal antes de vender.
