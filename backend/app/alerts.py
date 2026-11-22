"""Reglas de notificación sobre eventos YA detectados (catálogo). No es alerta temprana anticipada."""
import os
def thresholds():
    g = lambda k, d: float(os.getenv(k, d))
    return [("significativo", g("ALERT_SIGNIFICATIVO", 6.0)), ("advertencia", g("ALERT_ADVERTENCIA", 5.0)),
            ("precaucion", g("ALERT_PRECAUCION", 4.0)), ("info", g("ALERT_INFO", 3.0))]
def classify(ev):
    for name, t in thresholds():
        if ev["mag"] >= t:
            return {"level": name, "event_id": ev["id"], "mag": ev["mag"], "place": ev["place"], "depth_km": ev["depth_km"],
                    "time_event": ev["time_event"], "source": ev["source"], "verification": ev["status"],
                    "message": f"Sismo M{ev['mag']:.1f} detectado: {ev['place']}. Regla del proyecto, no es nivel oficial de emergencia."}
    return None
