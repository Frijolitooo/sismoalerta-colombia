"""Análisis histórico sobre eventos reales almacenados. Funciones puras (sin red)."""
from collections import Counter
MAG_EDGES = [(0, 3), (3, 4), (4, 5), (5, 6), (6, 10)]
DEPTH_EDGES = [(0, 30), (30, 70), (70, 150), (150, 300), (300, 1000)]

def region(place: str) -> str:
    return place.rsplit(",", 1)[-1].strip() if "," in place else "Otra / sin país"

def _bins(vals, edges):
    return [{"label": f"{a}-{b}", "n": sum(1 for v in vals if v is not None and a <= v < b)} for a, b in edges]

def summary(rows):
    mags = [r["mag"] for r in rows]; deps = [r["depth_km"] for r in rows if r["depth_km"] is not None]
    return {"n": len(rows), "max_mag": max(mags) if mags else None,
            "mean_mag": round(sum(mags) / len(mags), 2) if mags else None,
            "mean_depth": round(sum(deps) / len(deps), 1) if deps else None}

def stats(rows):
    by_day = Counter(r["time_event"][:10] for r in rows)
    return {**summary(rows),
            "by_day": [{"label": k, "n": by_day[k]} for k in sorted(by_day)],
            "mag_dist": _bins([r["mag"] for r in rows], MAG_EDGES),
            "depth_dist": _bins([r["depth_km"] for r in rows], DEPTH_EDGES),
            "by_region": [{"label": k, "n": n} for k, n in Counter(region(r["place"]) for r in rows).most_common(10)],
            "top_events": sorted(rows, key=lambda r: -r["mag"])[:10]}

def compare(cur, prev):
    a, b = summary(cur), summary(prev)
    ch = None if not b["n"] else round((a["n"] - b["n"]) / b["n"] * 100, 1)
    return {"current": a, "previous": b, "count_change_pct": ch}
