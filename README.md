# SismoAlerta Colombia (Etapa 1: núcleo funcional)
Monitoreo de eventos sísmicos ya detectados. **No predice sismos ni es alerta temprana oficial.**

## Ejecutar
```
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # opcional; ajusta umbrales e intervalos
cd backend && python -m pytest -q tests                 # pruebas
uvicorn app.main:app --port 8000                        # desde la carpeta backend
```
Abre http://localhost:8000. Al iniciar carga 30 días de USGS (caja geográfica de Colombia) y consulta cada POLL_SECONDS.

## Qué hay
- Ingesta USGS (FDSN event) -> ETL (validación, rechazo contado, trazabilidad) -> SQLite (dedupe por id) -> API + SSE (/api/stream) -> mapa Leaflet.
- Alertas por umbrales configurables (.env), con aviso de que no son niveles oficiales.
- Estado de fuentes real: conectado / actualizando / error / no configurado. Sin datos de demostración.
- Exportación CSV (/api/export.csv).

## Pendiente (siguientes etapas)
SGC e IRIS/FDSN (adaptadores en `sources/pending.py`, sin endpoints inventados), PostgreSQL/PostGIS y Docker, usuarios y roles, ETL con pandas y análisis histórico, ML con división temporal, PWA, push, React/TypeScript.
Nota: las pruebas usan un fixture con estructura GeoJSON de USGS, no datos reales.

## Etapa 2: análisis histórico, comparador y ML
- Página `analisis.html` (enlace "Análisis y ML" en el panel): distribuciones por magnitud/profundidad/país, eventos por día, mayores eventos, comparador de periodos y CSV.
- Para tener más historia, antes de encender el servidor (Windows): `set BACKFILL_DAYS=365`
- Entrenar el modelo experimental (desde `backend`): `python ml/train.py` y recargar la página. Usa separación temporal con 1 día de brecha y se compara contra una línea base. Si no hay datos suficientes, lo dice en lugar de mostrar resultados.
- Las pruebas del ML usan datos sintéticos (source=TEST) solo para verificar la mecánica; nunca se muestran en la app.

## Etapa 3: PWA, sección educativa y Docker
- PWA: `manifest.webmanifest`, `sw.js` e íconos. Solo se guarda la interfaz; los datos (/api) siempre vienen del servidor. Instalable desde Chrome/Edge en `localhost` o en HTTPS.
- `educacion.html`: conceptos, diferencia predicción/alerta temprana/monitoreo, qué hacer antes/durante/después (recomendaciones generales: verificar con UNGRD y SGC) y glosario.
- Docker: `docker compose up --build` y abrir http://localhost:8000. Para producción se requiere HTTPS.
