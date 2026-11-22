"""ETL: validación, normalización y trazabilidad. Lo inválido se descarta y se cuenta; nada se inventa."""
from datetime import datetime, timezone

def parse_usgs(geojson: dict, received_at: str | None = None):
    received_at = received_at or datetime.now(timezone.utc).isoformat()
    ok, rejected = [], 0
    for f in geojson.get("features", []):
        try:
            p, (lon, lat, depth) = f["properties"], f["geometry"]["coordinates"][:3]
            mag = p.get("mag")
            if mag is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("registro incompleto")
            ok.append({
                "id": f"usgs:{f['id']}", "source": "USGS", "source_id": f["id"],
                "time_event": datetime.fromtimestamp(p["time"] / 1000, timezone.utc).isoformat(),
                "time_received": received_at, "mag": float(mag),
                "depth_km": float(depth) if depth is not None else None,
                "lat": float(lat), "lon": float(lon), "place": p.get("place") or "Sin descripción",
                "url": p.get("url"), "status": p.get("status", "desconocido"), "is_demo": 0})
        except (KeyError, TypeError, ValueError):
            rejected += 1
    return ok, rejected
