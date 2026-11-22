import sqlite3, threading
COLS = ["id","source","source_id","time_event","time_received","mag","depth_km","lat","lon","place","url","status","is_demo"]
class DB:
    def __init__(self, path):
        self.c = sqlite3.connect(path, check_same_thread=False); self.c.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.c.execute("CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, source TEXT, source_id TEXT, time_event TEXT, time_received TEXT, mag REAL, depth_km REAL, lat REAL, lon REAL, place TEXT, url TEXT, status TEXT, is_demo INTEGER)")
        self.c.execute("CREATE INDEX IF NOT EXISTS ix_t ON events(time_event)")
    def upsert(self, rows):
        """Devuelve solo los eventos NUEVOS (dedupe por id); los existentes se actualizan (USGS revisa magnitudes)."""
        new = []
        with self.lock:
            for r in rows:
                exists = self.c.execute("SELECT 1 FROM events WHERE id=?", (r["id"],)).fetchone()
                self.c.execute(f"INSERT OR REPLACE INTO events({','.join(COLS)}) VALUES({','.join('?'*len(COLS))})", [r[k] for k in COLS])
                if not exists: new.append(r)
            self.c.commit()
        return new
    def query(self, since_iso, min_mag=0.0, limit=5000):
        with self.lock:
            return [dict(r) for r in self.c.execute("SELECT * FROM events WHERE time_event>=? AND mag>=? ORDER BY time_event DESC LIMIT ?", (since_iso, min_mag, limit))]
    def count(self):
        with self.lock: return self.c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
