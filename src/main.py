import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db
import notifier
from adapters import generic_html, bocm

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"

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
                # Primera ejecución para esta fuente: guardamos baseline, NO alertamos
                # (si no, la primera corrida del bot generaría una alerta falsa por cada fuente)
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


if __name__ == "__main__":
    run()
