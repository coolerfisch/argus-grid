#!/usr/bin/env python3
"""
ARGUS GRID v3.0 - Systemic Intelligence Engine Backend
Automatisierte Feed-Ingestion, Multi-LLM-Synthese & Data Sanitization Pipeline.
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
MAX_FEED_WORKERS = 40  # Erhöht zur Vermeidung von I/O-Flaschenhälsen
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

# Vollständiges Fallback-Template (alle von index.html erwarteten Keys)
FALLBACK_DATA = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "overall_geoscore": 50,
    "defcon_level": 3,
    "ampel_status": "GELB",
    "ampel_reason_simple": "Daten-Pipeline im Notfallmodus. Automatische Synthese derzeit eingeschränkt.",
    "daily_executive_summary": "Die automatisierte Datenanalyse konnte aufgrund temporärer API-Störungen oder Synthesefehler nicht vollständig durchgeführt werden. Das System läuft im abgesicherten Fallback-Betrieb.",
    "daily_executive_summary_simple": "Das Dashboard läuft aktuell im Notbetrieb. Neue Analysen werden beim nächsten automatischen Durchlauf generiert.",
    "key_takeaways": [
        "System befindet sich im automatischen Fallback-Modus.",
        "Feed-Ingestion läuft stabil; Synthese-APIs meldeten Teilausfälle.",
        "Nächster automatischer Retry erfolgt zum geplanten Cronjob-Zeitpunkt (06:00 UTC)."
    ],
    "predictive_horizon": [
        {
            "timeframe": "30-90 Tage",
            "forecast": "Erhöhte allgemeine Volatilität im geopolitischen Raum.",
            "probability": "Mittel",
            "early_warning_indicators": ["API-Health-Check", "Pipeline-Retry Status"]
        }
    ],
    "historical_precedents": [
        {
            "event": "Temporäre Datenunterbrechung",
            "period": "System-Archiv",
            "similarity": "Hoch",
            "takeaway": "Keine dauerhafte Beeinträchtigung der historischen Datenbasis."
        }
    ],
    "conflict_hotspots": [
        {
            "name": "Global Surveillance Grid",
            "lat": 20.0,
            "lon": 0.0,
            "intensity": "GELB",
            "description": "Fallback-Modus aktiv.",
            "military_activity": "Normal"
        }
    ],
    "graph_network": {
        "nodes": [
            {"id": "ARGUS_CORE", "label": "Argus System", "group": "Core", "val": 10}
        ],
        "edges": []
    },
    "game_theory_matrices": [],
    "domestic_policy_matrix": [],
    "stress_test_scenarios": [],
    "equity_rotation": {"buys": [], "sells": []},
    "digital_sovereignty_index": {"score": 50, "status": "Neutral"},
    "pipeline_health": pipeline_health
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
    """
    Versucht rohes LLM-JSON robust zu parsen.
    Entfernt Code-Zäune, repariert Trailing Commas und schließt offene Klammern.
    """
    if not raw_text:
        raise ValueError("Leerer Antworttext erhalten.")

    # 1. Strippe Markdown-Codeblocks
    text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE).strip()

    # 2. Versuch: Standard-Parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Versuch: Äußersten JSON-Block { ... } extrahieren
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        extracted = match.group(0)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            text = extracted

    # 4. Versuch: Trailing Commas vor ] oder } entfernen
    repaired = re.sub(r",\s*([\]}])", r"\1", text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # 5. Versuch: Offene Klammern bei abgeschnittenem Output schließen
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


def ensure_fallback_structures(data: dict) -> dict:
    """Garantiert, dass Pflichtfelder vorhanden sind."""
    if "graph_network" not in data or not data["graph_network"].get("nodes"):
        data["graph_network"] = FALLBACK_DATA["graph_network"]
    if "conflict_hotspots" not in data or not data["conflict_hotspots"]:
        data["conflict_hotspots"] = FALLBACK_DATA["conflict_hotspots"]
    return data


# --- STEP 1: FEED INGESTION ---

def fetch_single_feed(source: dict) -> list:
    """Lädt einen einzelnen RSS/OSINT-Feed mit Timeout und Altersfilter."""
    url = source.get("url")
    name = source.get("name", "Unknown")
    category = source.get("category", "General")
    weight = source.get("weight", 1.0)

    articles = []
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=FEED_TIMEOUT)
        if response.status_code != 200:
            return []

        parsed = feedparser.parse(response.content)
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=MAX_ARTICLE_AGE_HOURS)

        for entry in parsed.entries[:10]:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            link = entry.get("link", "").strip()
            
            # HTML-Tags aus Summary entfernen
            summary_clean = re.sub(r"<[^>]+>", "", summary)[:300]

            if title:
                articles.append({
                    "title": title,
                    "summary": summary_clean,
                    "link": link,
                    "source": name,
                    "category": category,
                    "weight": weight
                })
        return articles

    except Exception as e:
        return []


def fetch_all_feeds(sources_list: list) -> list:
    """Startet parallele Feed-Abfragen mit optimierter Worker-Anzahl."""
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
    
    # Komprimierten Input erstellen
    raw_payload = "\n".join([f"[{a['category']}] {a['source']}: {a['title']} - {a['summary']}" for a in articles[:100]])
    
    prompt = (
        "Du bist ein leitender OSINT-Analyst. Analysiere folgende Roh-Feeds. "
        "Filtere Rauschen, Propaganda und Duplikate heraus. "
        "Extrahiere nur die 25 wichtigsten, verifizierbaren geopolitischen & makroökonomischen Fakten des Tages. "
        "Formatiere als sachliche Stichpunkte mit Quellenbezug.\n\n"
        f"FEEDS:\n{raw_payload}"
    )

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 2000
    }

    try:
        res = requests.post(endpoint, headers=headers, json=data, timeout=30)
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
        return "Spieltheoretische Analyse aufgrund fehlender API-Konfiguration übersprungen."

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

    return "Keine spieltheoretische Analyse verfügbar."


def call_synthesizer(facts: str, game_theory: str) -> dict:
    """Stufe 3: Synthese & Erstellung des finalen JSON-Objekts."""
    api_key = MISTRAL_API_KEY or OPENROUTER_API_KEY or GROQ_API_KEY
    if not api_key:
        pipeline_health["synthesizer_status"] = "SKIPPED (No Key)"
        raise ValueError("Kein gültiger API-Key für Synthesizer vorhanden.")

    # Standard-Endpoint (Mistral Native)
    endpoint = "https://api.mistral.ai/v1/chat/completions"
    model = "mistral-large-latest"

    if not MISTRAL_API_KEY and OPENROUTER_API_KEY:
        endpoint = "https://openrouter.ai/api/v1/chat/completions"
        model = "qwen/qwen-2.5-72b-instruct"
        api_key = OPENROUTER_API_KEY

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    prompt = (
        "Du bist das ARGUS GRID Synthese-Modul. Generiere aus den vorliegenden Daten "
        "ein valides JSON-Objekt gemäß der festgelegten Struktur.\n"
        "Antworte AUSSCHLIESSLICH mit dem puren JSON-Objekt, ohne Markdown-Formatierung!\n\n"
        f"FAKTEN:\n{facts}\n\nSPIELTHEORIE:\n{game_theory}\n\n"
        "ERFORDERLICHE JSON-STRUKTUR:\n"
        "{\n"
        '  "overall_geoscore": int (0-100),\n'
        '  "defcon_level": int (1-5),\n'
        '  "ampel_status": "GRÜN" | "GELB" | "ROT",\n'
        '  "ampel_reason_simple": "Kurze Begründung",\n'
        '  "daily_executive_summary": "Ausführliche Analyse...",\n'
        '  "daily_executive_summary_simple": "Einfache Zusammenfassung...",\n'
        '  "key_takeaways": ["Punkt 1", "Punkt 2", "Punkt 3"],\n'
        '  "predictive_horizon": [{"timeframe": "30-90 Tage", "forecast": "...", "probability": "Hoch/Mittel/Niedrig", "early_warning_indicators": ["..."]}],\n'
        '  "historical_precedents": [{"event": "...", "period": "...", "similarity": "...", "takeaway": "..."}],\n'
        '  "conflict_hotspots": [{"name": "...", "lat": float, "lon": float, "intensity": "ROT/GELB", "description": "...", "military_activity": "..."}],\n'
        '  "graph_network": {"nodes": [{"id": "...", "label": "...", "group": "...", "val": 5}], "edges": [{"from": "...", "to": "...", "label": "..."}]},\n'
        '  "game_theory_matrices": [],\n'
        '  "domestic_policy_matrix": [],\n'
        '  "stress_test_scenarios": [],\n'
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

    if not articles:
        logging.error("Keine Artikel geladen. Verwende Notfall-Fallback.")
        final_data = FALLBACK_DATA
    else:
        try:
            # 2. Stage 1: Denoise via Groq
            logging.info("Stufe 1: Denoising via Groq...")
            facts = call_groq_denoise(articles)

            # 3. Stage 2: DeepSeek Reasoner
            logging.info("Stufe 2: Game-Theory via DeepSeek...")
            game_theory = call_deepseek_reasoner(facts)

            # 4. Stage 3: Synthesizer (Mistral/Qwen)
            logging.info("Stufe 3: Synthesizing JSON...")
            synthesized_data = call_synthesizer(facts, game_theory)

            # 5. Stage 4: Refine via Claude Haiku
            logging.info("Stufe 4: Refining prose via Claude Haiku...")
            final_data = call_haiku_refine(synthesized_data)

        except Exception as e:
            logging.error(f"Fehler in der LLM-Pipeline: {e}. Aktiviere Notfall-Fallback.")
            pipeline_health["errors"].append(f"Pipeline Critical Error: {str(e)}")
            final_data = FALLBACK_DATA

    # Metadata & Health Injektion
    final_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    final_data["pipeline_health"] = pipeline_health

    # Guaranteed Structure Check
    final_data = ensure_fallback_structures(final_data)

    # Data Sanitization (Markdown Stripping)
    logging.info("Stufe 5: Data Sanitization...")
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
