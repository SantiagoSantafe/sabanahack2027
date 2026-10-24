# Reporte: escala / mercado-go-to-market

Fecha: 2026-10-23. Entregable principal: `datos/escalabilidad/mercado.md`.

## Qué hice
1. Consulté la API de EVA 2019–2025 en datos.gov.co (uejq-wxrr) para arándano, fresa, mora, uchuva, frambuesa y aguacate, por año, departamento y municipio. Guardé las respuestas en `escalabilidad/mercado/eva_*.json`.
2. Busqué y abrí fuentes de 2023 a 2026 sobre área, productores, gremios y competidores en Perú, Chile y México. Son 31 fuentes y están listadas en la sección 11 de mercado.md.
3. Saqué precios de fresa y mora de los boletines DANE SIPSA de junio de 2026 y la TRM vigente del 2026-10-23.
4. Hice el TAM/SAM/SOM con un script que se puede volver a correr: `python3 -I escalabilidad/mercado/calc_mercado.py`.

## Resultados clave
- Arándano en los 4 países: ~54.500 ha (rango 45.900–57.300). Colombia tiene ~1.000 ha, menos del 2 %.
- Colombia: fresa 3.767 ha y mora 15.952 ha (EVA 2025).
- TAM ≈ 26,0 M USD/año. SAM ≈ 7,9 M USD/año. SOM a 5 años ≈ 0,45 M USD/año (~1.242 ha, ~50 robots). Los porcentajes de SAM y SOM y el precio de 60 USD del plan Vigía son SUPUESTOS.
- La mora no paga el robot: con 430 USD/ha el equilibrio es 3,5 % de la cosecha. Hace falta el plan sin robot (Vigía).
- Etapas: piloto en el altiplano cundiboyacense → Colombia comercial con fresa y mora → Perú, Chile y México con socio local y plan Flota.

## Alertas para otros roles
- **Finanzas:** la tienda oficial de AgiBot lista el D1 Ultra a 9.600 USD (sin envío ni aranceles). El equipo usa 7.499 USD FOB México.
- **Técnico y finanzas:** la ficha del D1 Ultra dice batería de 1–2 h y 0–40 °C. El supuesto de 20 ha por robot hay que validarlo.
- **Pitch:** las cifras de producción de arándano en Colombia no cuadran entre fuentes (EVA 6.031 t, Forbes 12.000 t, Asocolblue ~20.000 t). Conviene no citar toneladas.

## No verificado
Hay cosas que solo vi en resultados de búsqueda o en páginas que no abrieron (402/403):
- el programa de arándano de la Gobernación de Cundinamarca;
- la disputa del FNFH/Asohofrucol;
- la lista de aseguradoras del ISA;
- el detalle de la Res. ICA 824 de 2022;
- el número de productores en Chile y México.

No creé cuentas ni inicié sesión. No modifiqué archivos de otros agentes.
