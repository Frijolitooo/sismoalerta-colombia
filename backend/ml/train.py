"""Modelo EXPERIMENTAL: ¿habrá al menos un evento M>=umbral en el día siguiente? (zona: caja geográfica de Colombia)
Separación TEMPORAL (sin mezcla aleatoria) con 1 día de brecha. Se compara con una línea base de persistencia.
No es predicción de terremotos: con pocos datos las métricas son inestables y no constituyen evidencia científica."""
import json, os, sqlite3, sys
from datetime import datetime, timezone
import joblib, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
FEATURES = ["n1", "n7", "n30", "mx7", "dp7"]

def build(df, thr):
    df = df.copy(); df["day"] = pd.to_datetime(df["time_event"], utc=True).dt.floor("D")
    d = df.groupby("day").agg(n=("mag", "size"), mx=("mag", "max"), dp=("depth_km", "mean"))
    d = d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="D", tz="UTC"))
    d["n"] = d["n"].fillna(0); d["mx"] = d["mx"].fillna(0); d["dp"] = d["dp"].fillna(0)
    f = pd.DataFrame(index=d.index)
    f["n1"] = d["n"]; f["n7"] = d["n"].rolling(7).sum(); f["n30"] = d["n"].rolling(30, min_periods=7).sum()
    f["mx7"] = d["mx"].rolling(7).max(); f["dp7"] = d["dp"].rolling(7).mean()
    f["y"] = (d["mx"] >= thr).astype(int).shift(-1)  # objetivo: el DÍA SIGUIENTE
    return f.dropna()

def metrics(y, p, s=None):
    m = {"precision": float(precision_score(y, p, zero_division=0)), "recall": float(recall_score(y, p, zero_division=0)),
         "f1": float(f1_score(y, p, zero_division=0)), "confusion_matrix": confusion_matrix(y, p, labels=[0, 1]).tolist()}
    m["roc_auc"] = float(roc_auc_score(y, s)) if s is not None and len(set(y)) == 2 else None
    return m

def train(db_path, out_dir, thr=4.0):
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_sql("SELECT time_event, mag, depth_km FROM events WHERE is_demo=0", sqlite3.connect(db_path))
    out = {"version": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"), "trained_at": datetime.now(timezone.utc).isoformat(),
           "task": f"Evento M>={thr} en el día siguiente", "features": FEATURES, "experimental": True,
           "warning": "Modelo experimental con datos de catálogo. No predice terremotos ni es evidencia científica."}
    if len(df) < 50: return {**out, "status": "datos_insuficientes", "n_events": len(df)}
    f = build(df, thr); cut = int(len(f) * 0.8)
    tr, te = f.iloc[:max(cut - 1, 0)], f.iloc[cut:]  # brecha de 1 día: sin fuga temporal
    if tr.empty or te.empty or tr["y"].nunique() < 2 or te["y"].nunique() < 2:
        return {**out, "status": "datos_insuficientes", "n_events": len(df), "days": len(f),
                "detail": "Se necesitan días con y sin eventos grandes en entrenamiento y prueba. Aumenta BACKFILL_DAYS."}
    out.update(status="entrenado", n_events=len(df), n_train=len(tr), n_test=len(te), train_end=str(tr.index[-1].date()),
               test_start=str(te.index[0].date()), positive_rate_test=float(te["y"].mean()))
    models = {"random_forest": RandomForestClassifier(300, class_weight="balanced", min_samples_leaf=3, random_state=0),
              "regresion_logistica": make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000))}
    res = {"linea_base_persistencia": metrics(te["y"], (te["mx7"] >= thr).astype(int))}
    for name, m in models.items():
        m.fit(tr[FEATURES], tr["y"]); res[name] = metrics(te["y"], m.predict(te[FEATURES]), m.predict_proba(te[FEATURES])[:, 1])
    best = max(models, key=lambda k: res[k]["f1"])
    out.update(results=res, best_model=best,
               feature_importance=dict(zip(FEATURES, map(float, models["random_forest"].feature_importances_))))
    joblib.dump(models[best], os.path.join(out_dir, f"model_{out['version']}.joblib"))
    json.dump(out, open(os.path.join(out_dir, "latest_metrics.json"), "w"), indent=2)
    return out

if __name__ == "__main__":
    r = train(os.getenv("DB_PATH", "sismoalerta.db"), "models"); print(json.dumps(r, indent=2, ensure_ascii=False))
