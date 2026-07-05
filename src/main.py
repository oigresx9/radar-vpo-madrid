import sys
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db
import notifier
from adapters import generic_html, bocm

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"
DASHBOARD_DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "data"

ADAPTERS = {
    "generic_html": generic_html.check,
    "bocm": bocm.check,
}


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def clasificar_urgencia(texto: str, cfg: dict) -> str:
    texto_lower = texto.lower()
    for kw in cfg.get("urgencia_keywords_critico", []):
        if kw.lower() in texto_lower:
            return "CRITICO"
    for kw in cfg.get("urgencia_keywords_importante", []):
        if kw.lower() in texto_lower:
            return "IMPORTANTE"
    return "INFORMATIVO"


def resumen_corto(texto: str, max_chars: int = 400) -> str:
    return texto[:max_chars] + ("…" if len(texto) > max_chars else "")


def export_dashboard_data(conn, cfg):
    """Escribe docs/data/status.json y docs/data/alerts.json para que el
    dashboard estático (GitHub Pages) pueda mostrar el estado sin backend."""
    DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)

    sources = cfg.get("sources", [])
    status = []
    for source in sources:
        row = conn.execute(
            "SELECT content_hash, last_checked FROM source_state WHERE source_id = ?",
            (source["id"],)
        ).fetchone()
        status.append({
            "id": source["id"],
            "nombre": source["nombre"],
            "municipio": source.get("municipio"),
            "url": source["url"],
            "last_checked": row[1] if row else None,
        })

    alerts_rows = conn.execute("""
        SELECT source_name, municipio, urgencia, resumen, url, detected_at
        FROM alerts ORDER BY detected_at DESC LIMIT 200
    """).fetchall()
    alerts = [
        {
            "source_name": r[0], "municipio": r[1], "urgencia": r[2],
            "resumen": r[3], "url": r[4], "detected_at": r[5],
        }
        for r in alerts_rows
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": status,
        "alerts": alerts,
    }

    with open(DASHBOARD_DATA_DIR / "status.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def run():
    cfg = load_config()
    conn = db.get_conn()
    sources = cfg.get("sources", [])

    detected = 0

    for source in sources:
        source_id = source["id"]
        adapter_fn = ADAPTERS.get(source["tipo"])
        if adapter_fn is None:
            print(f"[WARN] Tipo de adapter desconocido para {source_id}: {source['tipo']}")
            continue

        try:
            result = adapter_fn(source)
        except Exception as e:
            print(f"[ERROR] Fallo consultando {source_id}: {e}")
            continue

        text = result["text"]
        if not text:
            print(f"[WARN] {source_id} devolvió contenido vacío, se omite.")
            continue

        h = db.content_hash(text)
        is_first_seen = db.has_changed(conn, source_id, h)

        if is_first_seen:
            row = conn.execute(
                "SELECT 1 FROM source_state WHERE source_id = ?", (source_id,)
            ).fetchone()
            es_baseline_inicial = row is None

            db.update_state(conn, source_id, h)

            if es_baseline_inicial:
                print(f"[INFO] Baseline inicial guardada para {source_id}, sin alerta.")
                continue

            urgencia = clasificar_urgencia(text, cfg)
            resumen = resumen_corto(text)

            db.record_alert(
                conn, source_id, source["nombre"], source.get("municipio"),
                urgencia, resumen, result["url"], h
            )
            notifier.send_alert(source["nombre"], source.get("municipio"), urgencia, resumen, result["url"])
            detected += 1
            print(f"[ALERTA] {urgencia} - {source['nombre']}")
        else:
            print(f"[OK] Sin cambios en {source_id}")

    print(f"\nResumen ejecución: {detected} novedad(es) detectada(s) sobre {len(sources)} fuente(s).")
    export_dashboard_data(conn, cfg)


if __name__ == "__main__":
    run()
