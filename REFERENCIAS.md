# Referencias

Las citas completas y su uso están en los documentos del proyecto: `datos/riesgo/README.md` (modelos de riesgo), `datos/REPORTE_DATOS.md`, `datos/reportes/` y `docs/CIFRAS_CLAVE.md`.

## Datasets (no se redistribuyen; descargar para reproducir)
| Dataset | Dónde | Licencia | Uso |
|---|---|---|---|
| **DrBerry** (hojas de arándano: sana, oídio, alternaria, Heliothis) | Roboflow Universe, workspace `drberry` (script: `datos/reportes/adquisicion-drberry_scripts/rf_download.py`, requiere `ROBOFLOW_API_KEY` propia) | CC BY 4.0 | Entrenamiento y test del clasificador |
| PlantDoc | Roboflow `joseph-nelson/plantdoc` / repositorio PlantDoc | CC BY 4.0 | Prueba fuera de distribución |
| PlantVillage (arándano sano) | PlantVillage | ver fuente | Prueba fuera de distribución |
| Strawberry Disease Detection | Dataset Ninja (Supervisely) | ver fuente | Prueba con fresa |
| Mendeley Data (fresa/frutales) | data.mendeley.com (`6zy6wxhf2v`, `8nnd2ypcv3`, `j4xs3kh3fd`, `k2ptxmfjhj`) | ver cada ficha | Prueba con fresa/frutales |
| iNaturalist / Wikimedia Commons | APIs públicas | licencia por imagen (CC) | Fotos de campo para prueba |

## Clima
- Open-Meteo (archivo histórico y pronóstico): `archive-api.open-meteo.com`, `api.open-meteo.com` — CC BY 4.0.

## Modelos de riesgo y literatura
- Wilson, Madden & Ellis (1990), *Phytopathology* — antracnosis (temperatura × horas de hoja mojada); con el ajuste de Gillett & Schilder. **Aproximación** (ver `datos/riesgo/README.md`).
- Bulger, Ellis & Madden (1987), *Phytopathology* — Botrytis en flor de fresa, usado como **proxy** para arándano (resumen: strawberrycenterblog.com, 2022; NC State IPM).
- Magarey et al. (2005), *Phytopathology* 95:92 — modelo genérico de infección (roya).
- Mastin et al. (2019) — sensibilidad de la inspección humana (otra enfermedad/hospedante; solo contexto).
- Guías de extensión: UF/IFAS AE450, MSU E3039, PNW Plant Disease Handbook (roya del arándano).

## Hardware y SDK
- AgiBot D1 (EDU/Ultra): ficha y repositorio `github.com/AgibotTech/agibot_D1_Edu-Ultra`. **El SDK (`mc_sdk_zsl_1_py`) y la guía de uso no se incluyen** (licencia del fabricante); se obtienen de AgiBot o del repositorio oficial.

## Software
Python (PyTorch, OpenCLIP, scikit-learn, NumPy, OpenCV, FastAPI, Uvicorn, pytest), TypeScript/React (Vite, Tailwind, Recharts, Three.js/React Three Fiber, Zustand), Docker/OrbStack, pptxgenjs.

## Fuentes del cliente
Entrevistas con el mentor de AGRAR (oct-2026), resumidas en `docs/RESPUESTAS_MENTOR.md` y `docs/CIFRAS_CLAVE.md`.
