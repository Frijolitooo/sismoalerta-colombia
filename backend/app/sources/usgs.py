import requests
from datetime import datetime, timedelta, timezone
URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
BBOX = dict(minlatitude=-4.5, maxlatitude=13.5, minlongitude=-82.0, maxlongitude=-66.0)  # Colombia y alrededores
def fetch(days=1, timeout=20):
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    r = requests.get(URL, params=dict(format="geojson", starttime=start, orderby="time", limit=20000, **BBOX),
                     headers={"User-Agent": "SismoAlertaColombia/0.1 (proyecto academico)"}, timeout=timeout)
    r.raise_for_status()
    return r.json()
