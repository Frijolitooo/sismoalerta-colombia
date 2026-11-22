import asyncio, json, os, time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from .db import DB
from .etl import parse_usgs
from .alerts import classify
from .sources import usgs, pending

db = DB(os.getenv("DB_PATH", "sismoalerta.db"))
subs: set = set()
alerts_log: list = []
status = {"USGS": {"state": "actualizando", "last_poll": None, "last_ok": None, "error": None, "processed": 0, "rejected": 0, "latency_ms": None}}

async def poll_once(days):
    st = status["USGS"]; st["state"] = "actualizando"; t0 = time.time()
    try:
        rows, rej = parse_usgs(await asyncio.to_thread(usgs.fetch, days))
        new = db.upsert(rows)
        st.update(state="conectado", last_ok=datetime.now(timezone.utc).isoformat(), error=None, processed=st["processed"] + len(rows),
                  rejected=st["rejected"] + rej, latency_ms=int((time.time() - t0) * 1000))
        return new
    except Exception as e:  # la app sigue viva y comunica el error
        st.update(state="error", error=f"{type(e).__name__}: {e}"); return []
    finally:
        st["last_poll"] = datetime.now(timezone.utc).isoformat()

async def loop():
    first = True
    while True:
        new = await poll_once(int(os.getenv("BACKFILL_DAYS", 30)) if first else 1)
        if not first:  # el backfill inicial no genera notificaciones
            for ev in new:
                a = classify(ev)
                if a: alerts_log.append(a); del alerts_log[:-200]
                for q in list(subs): q.put_nowait({"event": ev, "alert": a})
        first = False
        await asyncio.sleep(max(60, int(os.getenv("POLL_SECONDS", 120))))

@asynccontextmanager
async def lifespan(app):
    t = asyncio.create_task(loop()); yield; t.cancel()

app = FastAPI(title="SismoAlerta Colombia", lifespan=lifespan)

@app.get("/api/events")
def events(hours: int = Query(24, ge=1, le=24 * 365), min_mag: float = 0.0):
    return db.query((datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(), min_mag)

@app.get("/api/alerts")
def get_alerts(): return alerts_log[::-1]

@app.get("/api/sources")
def sources():
    out = [{"name": k, **v, "frequency": "consulta periódica de catálogo (no instantáneo)", "demo": False} for k, v in status.items()]
    out += [{"name": k, "state": "no configurado", "error": v, "demo": False} for k, v in pending.PENDING.items()]
    return {"sources": out, "db_records": db.count(), "backend": "ok", "db": "ok"}

@app.get("/api/export.csv")
def export(hours: int = 720, min_mag: float = 0.0):
    cols = ["id","source","time_event","mag","depth_km","lat","lon","place","url","status"]
    body = "\n".join(",".join('"%s"' % str(r[c]).replace('"', "'") for c in cols) for r in events(hours, min_mag))
    return Response(",".join(cols) + "\n" + body, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sismos.csv"})

@app.get("/api/stream")
async def stream():
    q: asyncio.Queue = asyncio.Queue(); subs.add(q)
    async def gen():
        try:
            while True:
                try: yield f"data: {json.dumps(await asyncio.wait_for(q.get(), 25))}\n\n"
                except asyncio.TimeoutError: yield ": keepalive\n\n"
        finally: subs.discard(q)
    return StreamingResponse(gen(), media_type="text/event-stream")


# ---- Etapa 2: análisis histórico, comparador y ML (rutas añadidas antes del montaje estático) ----
from . import analysis
import json as _json
_MODELS = Path(__file__).resolve().parents[1] / "models" / "latest_metrics.json"

@app.get("/api/stats")
def api_stats(hours: int = Query(720, ge=1, le=24 * 3650)): return analysis.stats(events(hours, 0.0))

@app.get("/api/compare")
def api_compare(hours: int = Query(168, ge=1, le=24 * 3650)):
    now = datetime.now(timezone.utc); cut = (now - timedelta(hours=hours)).isoformat()
    both = db.query((now - timedelta(hours=2 * hours)).isoformat(), 0.0, 100000)
    return analysis.compare([r for r in both if r["time_event"] >= cut], [r for r in both if r["time_event"] < cut])

@app.get("/api/ml")
def api_ml():
    return _json.loads(_MODELS.read_text()) if _MODELS.exists() else {"status": "sin_entrenar"}

app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend", html=True), name="web")
