import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.etl import parse_usgs
from app.db import DB
from app.alerts import classify
# FIXTURE de prueba con la estructura GeoJSON de USGS. No son datos reales y nunca se muestran en la app.
FIX = {"features": [
 {"id": "t1", "properties": {"mag": 4.6, "time": 1700000000000, "place": "Prueba A", "url": "u", "status": "reviewed"}, "geometry": {"coordinates": [-74.0, 4.6, 12.0]}},
 {"id": "t2", "properties": {"mag": None, "time": 1700000000000}, "geometry": {"coordinates": [-74.0, 4.6, 5.0]}},
 {"id": "t3", "properties": {"mag": 3.1, "time": 1700000100000}, "geometry": {"coordinates": [-74.0, 99.0, 5.0]}}]}
def test_parse_valida_y_rechaza():
    rows, rej = parse_usgs(FIX); assert len(rows) == 1 and rej == 2
    assert rows[0]["id"] == "usgs:t1" and rows[0]["is_demo"] == 0
def test_dedupe():
    db = DB(":memory:"); rows, _ = parse_usgs(FIX)
    assert len(db.upsert(rows)) == 1 and len(db.upsert(rows)) == 0 and db.count() == 1
def test_alert_levels():
    ev = lambda m: {"id": "x", "mag": m, "place": "p", "depth_km": 1, "time_event": "t", "source": "USGS", "status": "s"}
    assert classify(ev(2.0)) is None and classify(ev(3.2))["level"] == "info"
    assert classify(ev(4.5))["level"] == "precaucion" and classify(ev(5.5))["level"] == "advertencia" and classify(ev(6.5))["level"] == "significativo"

def test_analysis_y_comparador():
    from app.analysis import stats, compare, region
    r = lambda m, d, t, p: {"mag": m, "depth_km": d, "time_event": t, "place": p}
    rows = [r(4.5, 10, "2026-01-02T00:00:00", "5 km N of X, Colombia"), r(2.5, 80, "2026-01-02T05:00:00", "Y, Panama")]
    s = stats(rows); assert s["n"] == 2 and s["max_mag"] == 4.5 and s["by_day"][0]["n"] == 2 and region(rows[1]["place"]) == "Panama"
    assert compare(rows, rows[:1])["count_change_pct"] == 100.0 and compare(rows, [])["count_change_pct"] is None

def test_ml_sin_fuga_temporal():
    # Datos SINTÉTICOS (source=TEST) solo para verificar la mecánica del pipeline; no se usan ni se muestran en la app.
    import tempfile, random, os
    from datetime import datetime, timedelta, timezone
    from ml.train import train
    random.seed(1); d = tempfile.mkdtemp(); db = DB(os.path.join(d, "t.db")); t0 = datetime(2025, 1, 1, tzinfo=timezone.utc); rows = []
    for i in range(400):
        for j in range(random.randint(0, 3)):
            rows.append({"id": f"T{i}-{j}", "source": "TEST", "source_id": f"{i}-{j}", "time_event": (t0 + timedelta(days=i, hours=j)).isoformat(), "time_received": "x",
                         "mag": random.choice([2.6, 3.0, 3.5, 4.2]), "depth_km": 10.0, "lat": 4.0, "lon": -74.0, "place": "t, Colombia", "url": None, "status": "t", "is_demo": 0})
    db.upsert(rows); m = train(os.path.join(d, "t.db"), os.path.join(d, "m"))
    assert m["status"] == "entrenado" and m["train_end"] < m["test_start"] and "linea_base_persistencia" in m["results"]
    r = train(os.path.join(d, "vacia.db"), os.path.join(d, "m2")) if False else None
