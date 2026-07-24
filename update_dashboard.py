#!/usr/bin/env python3
"""
ARGUS GRID v3.0 - Systemic Intelligence Engine Backend
Automatisierte Feed-Ingestion, Multi-LLM-Synthese, Key-Harmonisierung & Data Sanitization.
Strikte Datenintegrität: Keine gefälschten oder erfundenen Inhalte.
"""

import os
import sys
import json
import re
import logging
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import feedparser

# External sources list import
try:
    from sources import SOURCES
except ImportError:
    logging.warning("sources.py nicht gefunden. Verwende leere Quellenliste.")
    SOURCES = []

# Logging Config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Configuration & Constants
MAX_FEED_WORKERS = 40  # Hohe Parallelität für I/O-Performance
FEED_TIMEOUT = 8        # Sekunden pro Feed-Anfrage
MAX_ARTICLE_AGE_HOURS = 48
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Environment Variables / API Keys
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
XAI_API_KEY = os.environ.get("XAI_API_KEY")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
NEMOTRON_API_KEY = os.environ.get("NEMOTRON_API_KEY")

# Global Health State Tracking
pipeline_health = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "feeds_total": 0,
    "feeds_successful": 0,
    "feeds_failed": 0,
    "groq_status": "PENDING",
    "deepseek_status": "PENDING",
    "synthesizer_status": "PENDING",
    "haiku_status": "PENDING",
    "errors": []
}


# --- HELPER & GUARDRAIL FUNCTIONS ---

def clean_expert_input(raw_text: str) -> str:
    """Meta-Bleed Guardrail: Filtert API-Fehler und Systemmeldungen aus Texten."""
    if not raw_text:
        return ""
    error_patterns = [
        r"Error 4\d\d", r"Error 5\d\d", r"Rate limit exceeded",
        r"Unauthorized", r"Invalid API Key", r"Internal Server Error",
        r"Traceback \(most recent call last\):", r"HTTPError"
    ]
    for pattern in error_patterns:
        if re.search(pattern, raw_text, re.IGNORECASE):
            logging.warning(f"Meta-Bleed erkannt und herausgefiltert: {pattern}")
            return ""
    return raw_text.strip()


def repair_and_parse_json(raw_text: str) -> dict:
    """Versucht rohes LLM-JSON robust zu parsen und Syntaxfehler zu beheben."""
    if not raw_text:
        raise ValueError("Leerer Antworttext erhalten.")

    text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        extracted = match.group(0)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            text = extracted

    repaired = re.sub(r",\s*([\]}])", r"\1", text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    text_patched = text + (']' * max(0, open_brackets)) + ('}' * max(0, open_braces))
    
    try:
        return json.loads(text_patched)
    except json.JSONDecodeError as e:
        pipeline_health["errors"].append(f"JSON Repair gescheitert: {str(e)}")
        raise ValueError(f"JSON konnte nicht repariert werden: {e}")


def sanitize_markdown(text: str) -> str:
    """Entfernt Markdown-Sonderzeichen für saubere HTML-Ausgabe."""
    if not isinstance(text, str):
        return text
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"`{1,3}(.*?)(`{1,3}|$)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    return text.strip()


def sanitize_data_structure(data):
    """Rekursive Sanitization aller Strings im Daten-Dict."""
    if isinstance(data, dict):
        return {k: sanitize_data_structure(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data_structure(item) for item in data]
    elif isinstance(data, str):
        return sanitize_markdown(data)
    return data


def select_balanced_articles(articles: list, max_count: int = 120) -> list:
    """Sortiert Artikel nach Gewichtung und stellt eine ausgewogene Auslese über alle Kategorien sicher."""
    if not articles:
        return []

    sorted_articles = sorted(articles, key=lambda x: x.get("weight", 1.0), reverse=True)
    
    cat_groups = {}
    for a in sorted_articles:
        cat = a.get("category", "General")
        if cat not in cat_groups:
            cat_groups[cat] = []
        cat_groups[cat].append(a)

    balanced = []
    while len(balanced) < max_count and any(cat_groups.values()):
        for cat in list(cat_groups.keys()):
            if cat_groups[cat]:
                balanced.append(cat_groups[cat].pop(0))
            if len(balanced) >= max_count:
                break
    return balanced


def harmonize_and_validate_schema(data: dict, deepseek_text: str) -> dict:
    """
    STRIKTE SCHEMA-HARMONISIERUNG UND DEEPSEEK-INJEKTION:
    Erzeugt KEINE erfundenen Daten, sondern übersetzt Schlüssel-Aliase,
    damit index.html die echten LLM-Daten fehlerfrei anzeigt.
    """
    if not isinstance(data, dict):
        data = {}

    # 1. KPI & Score-Aliase spiegeln
    geoscore = data.get("overall_geoscore") or data.get("geoscore")
    defcon = data.get("defcon_level") or data.get("defcon")

    if geoscore is not None:
        try:
            val = int(geoscore)
            data["overall_geoscore"] = val
            data["geoscore"] = val
        except (ValueError, TypeError):
            pass

    if defcon is not None:
        try:
            val = int(defcon)
            data["defcon_level"] = val
            data["defcon"] = val
        except (ValueError, TypeError):
            pass

    # 2. DeepSeek Spieltheorie-Text in alle erwarteten Key-Namen injizieren
    ds_clean = clean_expert_input(deepseek_text) if deepseek_text else ""
    if ds_clean:
        data["game_theory_analysis"] = ds_clean
        data["deepseek_analysis"] = ds_clean
        data["game_theory"] = ds_clean
    else:
        if "game_theory_analysis" not in data:
            data["game_theory_analysis"] = "Keine spieltheoretische Analyse für diesen Durchlauf verfügbar."

    # 3. Hotspots: Koordinaten-Aliase für Leaflet (lat/lon <-> lat/lng)
    hotspots = data.get("conflict_hotspots", [])
    if isinstance(hotspots, list):
        for h in hotspots:
            if isinstance(h, dict):
                if "lng" not in h and "lon" in h:
                    h["lng"] = h["lon"]
                if "lon" not in h and "lng" in h:
                    h["lon"] = h["lng"]
    else:
        data["conflict_hotspots"] = []

    # 4. Graph Network: Aliase für Force-Graph / Canvas (from/to <-> source/target, label <-> name)
    gn = data.get("graph_network", {})
    if isinstance(gn, dict):
        nodes = gn.get("nodes", [])
        edges = gn.get("edges", gn.get("links", []))
        
        if isinstance(nodes, list):
            for n in nodes:
                if isinstance(n, dict):
                    if "name" not in n and "label" in n:
                        n["name"] = n["label"]
                    if "label" not in n and "name" in n:
                        n["label"] = n["name"]
        
        if isinstance(edges, list):
            for e in edges:
                if isinstance(e, dict):
                    if "source" not in e and "from" in e:
                        e["source"] = e["from"]
                    if "from" not in e and "source" in e:
                        e["from"] = e["source"]
                    if "target" not in e and "to" in e:
                        e["target"] = e["to"]
                    if "to" not in e and "target" in e:
                        e["to"] = e["target"]
        
        data["graph_network"] = {"nodes": nodes, "edges": edges, "links": edges}
    else:
        data["graph_network"] = {"nodes": [], "edges": [], "links": []}

    # 5. Absicherung für sonstige Listen
    for array_key in ["predictive_horizon", "historical_precedents", "domestic_policy_matrix", "stress_test_scenarios", "key_takeaways"]:
        if array_key not in data or not isinstance(data[array_key], list):
            data[array_key] = []

    # 6. Health State anhängen
    data["feeds_total"] = pipeline_health.get("feeds_total", 0)
    data["feeds_successful"] = pipeline_health.get("feeds_successful", 0)
    data["feeds_failed"] = pipeline_health.get("feeds_failed", 0)
    data["pipeline_health"] = pipeline_health

    return data


# --- STEP 1: FEED INGESTION ---

def fetch_single_feed(source: dict) -> list:
    """Lädt einen einzelnen RSS/OSINT-Feed mit Timeout."""
    url = source.get("url")
    name = source.get("name", "Unknown")
    category = source.get("cat", source.get("category", "General"))
    bias = source.get("bias", "NEUTRAL")
    weight = source.get("weight", 1.0)

    articles = []
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=FEED_TIMEOUT)
        if response.status_code != 200:
            return []

        parsed = feedparser.parse(response.content)

        for entry in parsed.entries[:8]:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            link = entry.get("link", "").strip()
            
            summary_clean = re.sub(r"<[^>]+>", "", summary)[:300]

            if title:
                articles.append({
                    "title": title,
                    "summary": summary_clean,
                    "link": link,
                    "source": name,
                    "category": category,
                    "bias": bias,
                    "weight": weight
                })
        return articles

    except Exception:
        return []


def fetch_all_feeds(sources_list: list) -> list:
    """Startet parallele Feed-Abfragen mit 40 Workern."""
    pipeline_health["feeds_total"] = len(sources_list)
    all_articles = []
    successful_feeds = 0
    failed_feeds = 0

    logging.info(f"Starte Feed-Ingestion für {len(sources_list)} Quellen mit {MAX_FEED_WORKERS} Workern...")

    with ThreadPoolExecutor(max_workers=MAX_FEED_WORKERS) as executor:
        future_to_source = {executor.submit(fetch_single_feed, src): src for src in sources_list}
        for future in as_completed(future_to_source):
            res = future.result()
            if res:
                all_articles.extend(res)
                successful_feeds += 1
            else:
                failed_feeds += 1

    pipeline_health["feeds_successful"] = successful_feeds
    pipeline_health["feeds_failed"] = failed_feeds

    logging.info(f"Ingestion beendet: {len(all_articles)} Artikel aus {successful_feeds} Feeds geladen. ({failed_feeds} fehlgeschlagen)")
    return all_articles


# --- STEP 2: MULTI-LLM PIPELINE ---

def call_groq_denoise(articles: list) -> str:
    """Stufe 1: Groq (llama-3.3-70b-versatile) zur Entrauschung & Faktenextraktion."""
    if not GROQ_API_KEY:
        pipeline_health["groq_status"] = "SKIPPED (No API Key)"
        return json.dumps(articles[:30])

    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    selected_articles = select_balanced_articles(articles, max_count=120)
    
    raw_payload = "\n".join([
        f"[{a['category']} | {a['bias']}] {a['source']}: {a['title']} - {a['summary']}" 
        for a in selected_articles
    ])
    
    prompt = (
        "Du bist ein leitender OSINT-Analyst. Analysiere folgende Roh-Feeds aus aller Welt "
        "(Geopolitik, Zentralbanken, Schattenflotten, Agrar, Cyber, Militär).\n"
        "Filtere Rauschen, Propaganda und Duplikate heraus.\n"
        "Extrahiere die 30 wichtigsten, verifizierbaren geopolitischen, militärischen & makroökonomischen Fakten des Tages. "
        "Formatiere als sachliche Stichpunkte mit Quellenbezug.\n\n"
        f"FEEDS:\n{raw_payload}"
    )

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 2500
    }

    try:
        res = requests.post(endpoint, headers=headers, json=data, timeout=35)
        if res.status_code == 200:
            pipeline_health["groq_status"] = "SUCCESS"
            return res.json()["choices"][0]["message"]["content"]
        else:
            pipeline_health["groq_status"] = f"FAILED ({res.status_code})"
            pipeline_health["errors"].append(f"Groq API Error: {res.status_code}")
    except Exception as e:
        pipeline_health["groq_status"] = f"ERROR ({str(e)})"
        pipeline_health["errors"].append(f"Groq Exception: {str(e)}")

    return json.dumps(articles[:30])


def call_deepseek_reasoner(facts: str) -> str:
    """Stufe 2: DeepSeek-R1 zur spieltheoretischen Analyse."""
    if not DEEPSEEK_API_KEY:
        pipeline_health["deepseek_status"] = "SKIPPED (No API Key)"
        return ""

    endpoint = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        "Analysiere folgende verifizierte Faktenlage aus spieltheoretischer Sicht. "
        "Identifiziere Akteure, Handlungsoptionen, Payoff-Matrizen und Eskalationspfade.\n\n"
        f"FAKTEN:\n{facts}"
    )

    data = {
        "model": "deepseek-reasoner",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000
    }

    try:
        res = requests.post(endpoint, headers=headers, json=data, timeout=45)
        if res.status_code == 200:
            pipeline_health["deepseek_status"] = "SUCCESS"
            return clean_expert_input(res.json()["choices"][0]["message"]["content"])
        else:
            pipeline_health["deepseek_status"] = f"FAILED ({res.status_code})"
            pipeline_health["errors"].append(f"DeepSeek API Error: {res.status_code}")
    except Exception as e:
        pipeline_health["deepseek_status"] = f"ERROR ({str(e)})"
        pipeline_health["errors"].append(f"DeepSeek Exception: {str(e)}")

    return ""


def call_synthesizer(facts: str, game_theory: str) -> dict:
    """Stufe 3: Synthese & Erstellung des finalen JSON-Objekts."""
    api_key = MISTRAL_API_KEY or OPENROUTER_API_KEY or GROQ_API_KEY
    if not api_key:
        pipeline_health["synthesizer_status"] = "SKIPPED (No Key)"
        raise ValueError("Kein gültiger API-Key für Synthesizer vorhanden.")

    endpoint = "https://api.mistral.ai/v1/chat/completions"
    model = "mistral-large-latest"

    if not MISTRAL_API_KEY and OPENROUTER_API_KEY:
        endpoint = "https://openrouter.ai/api/v1/chat/completions"
        model = "qwen/qwen-2.5-72b-instruct"
        api_key = OPENROUTER_API_KEY

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    prompt = (
        "Du bist das ARGUS GRID Synthese-Modul. Generiere aus den vorliegenden Fakten ein valides JSON-Objekt.\n"
        "WICHTIG: Antworte AUSSCHLIESSLICH mit dem puren JSON-Objekt, ohne Markdown-Formatierung!\n"
        "Erstelle auf Basis der realen Fakten möglichst präzise Einträge für alle Felder.\n\n"
        f"FAKTEN:\n{facts}\n\nSPIELTHEORIE:\n{game_theory}\n\n"
        "ERFORDERLICHE JSON-STRUKTUR:\n"
        "{\n"
        '  "overall_geoscore": int (0-100),\n'
        '  "geoscore": int (0-100),\n'
        '  "defcon_level": int (1-5),\n'
        '  "defcon": int (1-5),\n'
        '  "ampel_status": "GRÜN" | "GELB" | "ROT",\n'
        '  "ampel_reason_simple": "Kurze Begründung",\n'
        '  "daily_executive_summary": "Ausführliche Analyse...",\n'
        '  "daily_executive_summary_simple": "Einfache Zusammenfassung...",\n'
        '  "key_takeaways": ["Punkt 1", "Punkt 2", "Punkt 3"],\n'
        '  "predictive_horizon": [{"timeframe": "30 Tage (Taktisch)", "forecast": "...", "probability": "Hoch/Mittel/Niedrig", "early_warning_indicators": ["..."]}],\n'
        '  "historical_precedents": [{"event": "...", "period": "...", "similarity": "...", "takeaway": "..."}],\n'
        '  "conflict_hotspots": [{"name": "...", "lat": float, "lon": float, "lng": float, "intensity": "ROT/GELB", "description": "...", "military_activity": "..."}],\n'
        '  "graph_network": {"nodes": [{"id": "...", "label": "...", "name": "...", "group": "...", "val": 5}], "edges": [{"from": "...", "to": "...", "source": "...", "target": "...", "label": "..."}]},\n'
        '  "domestic_policy_matrix": [{"region": "...", "dynamics": "...", "stability": "GELB", "spillover": "..."}],\n'
        '  "stress_test_scenarios": [{"scenario": "...", "impact": "...", "probability": "...", "mitigation": "..."}],\n'
        '  "equity_rotation": {"buys": [], "sells": []},\n'
        '  "digital_sovereignty_index": {"score": int, "status": "..."}\n'
        "}"
    )

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"} if "mistral" in endpoint else None
    }

    try:
        res = requests.post(endpoint, headers=headers, json=data, timeout=60)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            parsed_json = repair_and_parse_json(content)
            pipeline_health["synthesizer_status"] = "SUCCESS"
            return parsed_json
        else:
            pipeline_health["synthesizer_status"] = f"FAILED ({res.status_code})"
            pipeline_health["errors"].append(f"Synthesizer API Error: {res.status_code}")
            raise ValueError(f"Synthesizer HTTP {res.status_code}")
    except Exception as e:
        pipeline_health["synthesizer_status"] = f"ERROR ({str(e)})"
        pipeline_health["errors"].append(f"Synthesizer Exception: {str(e)}")
        raise e


def call_haiku_refine(data_dict: dict) -> dict:
    """Stufe 4: Claude 3.5 Haiku zur redaktionellen Veredelung der einfachen Textfelder."""
    if not ANTHROPIC_API_KEY:
        pipeline_health["haiku_status"] = "SKIPPED (No API Key)"
        return data_dict

    endpoint = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }

    exec_summary = data_dict.get("daily_executive_summary", "")
    ampel_reason = data_dict.get("ampel_reason_simple", "")

    prompt = (
        "Formuliere die folgenden zwei Texte für ein allgemeines Publikum um. "
        "Verwende klares, präzises Deutsch ohne Fachjargon oder Phrasen wie 'basierend auf den Daten'.\n\n"
        f"1. Executive Summary:\n{exec_summary}\n\n"
        f"2. Ampel Begründung:\n{ampel_reason}\n\n"
        'Antworte im JSON-Format: {"daily_executive_summary_simple": "...", "ampel_reason_simple": "..."}'
    )

    payload = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        res = requests.post(endpoint, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            raw_content = res.json()["content"][0]["text"]
            refined = repair_and_parse_json(raw_content)
            if "daily_executive_summary_simple" in refined:
                data_dict["daily_executive_summary_simple"] = refined["daily_executive_summary_simple"]
            if "ampel_reason_simple" in refined:
                data_dict["ampel_reason_simple"] = refined["ampel_reason_simple"]
            pipeline_health["haiku_status"] = "SUCCESS"
        else:
            pipeline_health["haiku_status"] = f"FAILED ({res.status_code})"
    except Exception as e:
        pipeline_health["haiku_status"] = f"ERROR ({str(e)})"
        pipeline_health["errors"].append(f"Haiku Refine Exception: {str(e)}")

    return data_dict


# --- MAIN PIPELINE EXECUTION ---

def main():
    logging.info("=== ARGUS GRID v3.0 Pipeline Start ===")

    # 1. Feed Ingestion
    articles = fetch_all_feeds(SOURCES)

    game_theory_text = ""

    if not articles:
        logging.error("Keine Artikel geladen. Erzeuge leeres Status-JSON.")
        final_data = {}
    else:
        try:
            logging.info("Stufe 1: Denoising via Groq...")
            facts = call_groq_denoise(articles)

            logging.info("Stufe 2: Game-Theory via DeepSeek...")
            game_theory_text = call_deepseek_reasoner(facts)

            logging.info("Stufe 3: Synthesizing JSON...")
            synthesized_data = call_synthesizer(facts, game_theory_text)

            logging.info("Stufe 4: Refining prose via Claude Haiku...")
            final_data = call_haiku_refine(synthesized_data)

        except Exception as e:
            logging.error(f"Fehler in der LLM-Pipeline: {e}.")
            pipeline_health["errors"].append(f"Pipeline Critical Error: {str(e)}")
            final_data = {}

    # Timestamp Injection
    final_data["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Schema Validation & Key-Harmonization (Löst leere Frontend-Felder ohne Datenfälschung)
    logging.info("Stufe 5: Schema Harmonization & Validation...")
    final_data = harmonize_and_validate_schema(final_data, game_theory_text)

    # Data Sanitization (Markdown Stripping)
    logging.info("Stufe 6: Data Sanitization...")
    sanitized_data = sanitize_data_structure(final_data)

    # Save to data.json
    output_path = "data.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sanitized_data, f, ensure_ascii=False, indent=2)
        logging.info(f"Pipeline erfolgreich abgeschlossen. Output in '{output_path}' gespeichert.")
    except Exception as e:
        logging.critical(f"Kritischer Fehler beim Schreiben von {output_path}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
