#!/usr/bin/env python3
"""
ARGUS GRID v3.0 - Collective Swarm Intelligence Engine Backend
Kollaboratives Multi-LLM-System ("Kuchenbacken-Architektur"):
1. Parallele Entwurfserstellung aller KI-Modelle auf der Gesamtlage
2. Gegenseitiges Peer-Review & Fingerklopfen (Debatte & Korrektur)
3. Konsens-Synthese & Daten-Harmonisierung für data.json
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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

# Global Health State Tracking
pipeline_health = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "feeds_total": 0,
    "feeds_successful": 0,
    "feeds_failed": 0,
    "bakers_active": [],
    "swarm_debate_status": "PENDING",
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
    """Sortiert Artikel nach Gewichtung und stellt eine ausgewogene Auslese sicher."""
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


def harmonize_and_validate_schema(data: dict, debate_summary: str) -> dict:
    """
    SCHEMA-HARMONISIERUNG:
    Verbindet Aliase (geoscore, defcon, lat/lng, source/target), 
    ohne Daten frei zu erfinden.
    """
    if not isinstance(data, dict):
        data = {}

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

    # Debatten- & Spieltheorie-Injektion für Expertenansicht
    ds_clean = clean_expert_input(debate_summary)
    if ds_clean:
        data["game_theory_analysis"] = ds_clean
        data["deepseek_analysis"] = ds_clean
        data["game_theory"] = ds_clean

    # Hotspots & Leaflet Koordinaten-Aliase
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

    # Graph Network Aliase
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

    for array_key in ["predictive_horizon", "historical_precedents", "domestic_policy_matrix", "stress_test_scenarios", "key_takeaways"]:
        if array_key not in data or not isinstance(data[array_key], list):
            data[array_key] = []

    data["pipeline_health"] = pipeline_health
    return data


# --- STEP 1: FEED INGESTION ---

def fetch_single_feed(source: dict) -> list:
    """Lädt einen einzelnen RSS/OSINT-Feed."""
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

    logging.info(f"Ingestion beendet: {len(all_articles)} Artikel aus {successful_feeds} Feeds geladen.")
    return all_articles


# --- STEP 2: THE SWARM BAKER COMMITTEE (PARALLELE GESAMT-ENTWÜRFE) ---

def baker_groq(payload: str) -> str:
    """Bäcker 1: Groq (Llama 3.3 70B) - Schnell, faktenorientiert."""
    if not GROQ_API_KEY:
        return ""
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{
                    "role": "user",
                    "content": f"Analysiere die Gesamtlage der weltweiten Feeds. Erstelle ein vollständiges Lagedokument: Key-Fakten, Geoscore-Einschätzung, DEFCON-Level, Hauptakteure und Risiko-Hotspots.\n\nFEEDS:\n{payload}"
                }],
                "max_tokens": 1800
            },
            timeout=35
        )
        if res.status_code == 200:
            pipeline_health["bakers_active"].append("Groq (Llama-3.3)")
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.warning(f"Groq Baker Fehler: {e}")
    return ""


def baker_deepseek(payload: str) -> str:
    """Bäcker 2: DeepSeek-R1 - Strategisch, spieltheoretisch, tiefgründig."""
    if not DEEPSEEK_API_KEY:
        return ""
    try:
        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-reasoner",
                "messages": [{
                    "role": "user",
                    "content": f"Analysiere die Gesamtlage aus strategischer und spieltheoretischer Sicht. Welche Akteure befinden sich in Zugzwängen, wo drohen Eskalationen und wie ist die globale Stabilität zu bewerten?\n\nFEEDS:\n{payload[:3000]}"
                }],
                "max_tokens": 1800
            },
            timeout=45
        )
        if res.status_code == 200:
            pipeline_health["bakers_active"].append("DeepSeek-R1")
            return clean_expert_input(res.json()["choices"][0]["message"]["content"])
    except Exception as e:
        logging.warning(f"DeepSeek Baker Fehler: {e}")
    return ""


def baker_qwen_or_grok(payload: str) -> str:
    """Bäcker 3: Qwen 2.5 / Grok / OpenRouter - Multipolare Makro-Perspektive."""
    api_key = OPENROUTER_API_KEY or XAI_API_KEY or QWEN_API_KEY
    if not api_key:
        return ""
    
    endpoint = "https://openrouter.ai/api/v1/chat/completions" if OPENROUTER_API_KEY else "https://api.x.ai/v1/chat/completions"
    model = "qwen/qwen-2.5-72b-instruct" if OPENROUTER_API_KEY else "grok-2-latest"

    try:
        res = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": f"Analysiere die Lage aus makroökonomischer und multipolarer Sicht (BRICS, Lieferketten, Chokepoints, Währungen). Erstelle eine vollständige Lagebeurteilung.\n\nFEEDS:\n{payload[:3000]}"
                }],
                "max_tokens": 1800
            },
            timeout=35
        )
        if res.status_code == 200:
            pipeline_health["bakers_active"].append(f"Swarm-Partner ({model.split('/')[-1]})")
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.warning(f"Qwen/Grok Baker Fehler: {e}")
    return ""


# --- STEP 3: PEER DEBATE & FINGERKLOPFEN (CROSS-VALIDATION) ---

def run_swarm_debate(draft_groq: str, draft_deepseek: str, draft_macro: str) -> str:
    """
    DAS FINGERKLOPFEN:
    Die Modelle prüfen die Entwürfe der jeweils anderen auf Halluzinationen, 
    Widersprüche und blinde Flecken.
    """
    api_key = MISTRAL_API_KEY or GROQ_API_KEY or OPENROUTER_API_KEY
    if not api_key:
        pipeline_health["swarm_debate_status"] = "SKIPPED"
        return "Keine Debatte möglich."

    endpoint = "https://api.groq.com/openai/v1/chat/completions" if GROQ_API_KEY else "https://api.mistral.ai/v1/chat/completions"
    model = "llama-3.3-70b-versatile" if GROQ_API_KEY else "mistral-large-latest"

    prompt = (
        "Du bist der Moderator der KI-Analysten-Konferenz. Dir liegen die Lagedokumente von 3 verschiedenen KI-Systemen vor:\n\n"
        f"ENTWURF 1 (Groq/OSINT):\n{draft_groq[:1500]}\n\n"
        f"ENTWURF 2 (DeepSeek/Spieltheorie):\n{draft_deepseek[:1500]}\n\n"
        f"ENTWURF 3 (Makro/BRICS):\n{draft_macro[:1500]}\n\n"
        "FÜHRE DIE KREUZPRÜFUNG DURCH ('Fingerklopfen'):\n"
        "1. Wo widersprechen sich die Modelle direkt? (z.B. Risikoeinschätzungen, Fakten)\n"
        "2. Welche Halluzinationen oder unbegründeten Behauptungen müssen gestrichen werden?\n"
        "3. Was ist der eimütige, verifizierte KERN-KONSENS aller Modelle?\n"
        "Formuliere eine messerscharfe Synthese dieser Debatte."
    )

    try:
        res = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1500
            },
            timeout=35
        )
        if res.status_code == 200:
            pipeline_health["swarm_debate_status"] = "SUCCESS"
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        pipeline_health["swarm_debate_status"] = f"ERROR ({e})"

    return "Konsens-Debatte mit reduzierten Daten durchgeführt."


# --- STEP 4: CONSENSUS SYNTHESIS & JSON BAKE ---

def call_synthesizer(debate_result: str, draft_groq: str, draft_deepseek: str) -> dict:
    """Synthesizer baut das finale JSON auf Basis der gemeinsam gegengelesenen Ergebnisse."""
    api_key = MISTRAL_API_KEY or OPENROUTER_API_KEY or GROQ_API_KEY
    if not api_key:
        pipeline_health["synthesizer_status"] = "SKIPPED"
        raise ValueError("Kein Key für Synthesizer.")

    endpoint = "https://api.mistral.ai/v1/chat/completions" if MISTRAL_API_KEY else "https://openrouter.ai/api/v1/chat/completions"
    model = "mistral-large-latest" if MISTRAL_API_KEY else "qwen/qwen-2.5-72b-instruct"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    prompt = (
        "Du bist das finale ARGUS GRID Synthese-Modul. Bilde aus dem gemeinsamen Konsens "
        "und der Debatte der KI-Analysten das finale JSON-Objekt.\n"
        "WICHTIG: Antworte AUSSCHLIESSLICH mit dem puren JSON-Objekt, ohne Markdown!\n"
        "Nutze AUSSCHLIESSLICH verifizierte, in der Debatte bestätigte Fakten. Keine erfundene Daten!\n\n"
        f"KONSENS & DEBATTE:\n{debate_result}\n\nSPIELTHEORIE-INPUT:\n{draft_deepseek[:1200]}\n\n"
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

    try:
        res = requests.post(
            endpoint,
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"} if "mistral" in endpoint else None
            },
            timeout=60
        )
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            parsed_json = repair_and_parse_json(content)
            pipeline_health["synthesizer_status"] = "SUCCESS"
            return parsed_json
        else:
            pipeline_health["synthesizer_status"] = f"FAILED ({res.status_code})"
            raise ValueError(f"Synthesizer HTTP {res.status_code}")
    except Exception as e:
        pipeline_health["synthesizer_status"] = f"ERROR ({e})"
        raise e


# --- STEP 5: REDAKTIONELLER SCHLIFF ---

def call_haiku_refine(data_dict: dict) -> dict:
    """Claude 3.5 Haiku schliffelt die Sprache der einfachen Ansicht."""
    if not ANTHROPIC_API_KEY:
        pipeline_health["haiku_status"] = "SKIPPED"
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
        "Klares Deutsch, flüssig, präzise, frei von KI-Floskeln.\n\n"
        f"1. Executive Summary:\n{exec_summary}\n\n"
        f"2. Ampel Begründung:\n{ampel_reason}\n\n"
        'Antworte im JSON-Format: {"daily_executive_summary_simple": "...", "ampel_reason_simple": "..."}'
    )

    try:
        res = requests.post(
            endpoint,
            headers=headers,
            json={"model": "claude-3-5-haiku-20241022", "max_tokens": 1000, "messages": [{"role": "user", "content": prompt}]},
            timeout=25
        )
        if res.status_code == 200:
            raw_content = res.json()["content"][0]["text"]
            refined = repair_and_parse_json(raw_content)
            if "daily_executive_summary_simple" in refined:
                data_dict["daily_executive_summary_simple"] = refined["daily_executive_summary_simple"]
            if "ampel_reason_simple" in refined:
                data_dict["ampel_reason_simple"] = refined["ampel_reason_simple"]
            pipeline_health["haiku_status"] = "SUCCESS"
    except Exception as e:
        pipeline_health["haiku_status"] = f"ERROR ({e})"

    return data_dict


# --- MAIN PIPELINE EXECUTION ---

def main():
    logging.info("=== ARGUS GRID v3.0 Collective Swarm Pipeline Start ===")

    articles = fetch_all_feeds(SOURCES)

    if not articles:
        logging.error("Keine Artikel geladen. Pipeline stoppt.")
        final_data = {}
    else:
        try:
            # Komprimierten Payload erzeugen
            selected = select_balanced_articles(articles, max_count=100)
            raw_payload = "\n".join([f"[{a['category']} | {a['bias']}] {a['source']}: {a['title']} - {a['summary']}" for a in selected])

            # 1. SWARM BAKER COMMITTEE (Parallele Lage-Analysen)
            logging.info("Phase 1: Das Kollektiv rührt gemeinsam den Teig (Parallele Sprints von Groq, DeepSeek, Qwen/Grok)...")
            with ThreadPoolExecutor(max_workers=3) as executor:
                f_groq = executor.submit(baker_groq, raw_payload)
                f_ds   = executor.submit(baker_deepseek, raw_payload)
                f_macro = executor.submit(baker_qwen_or_grok, raw_payload)

                draft_groq = f_groq.result()
                draft_ds   = f_ds.result()
                draft_macro = f_macro.result()

            # 2. DEBATTE & FINGERKLOPFEN (Peer Review)
            logging.info("Phase 2: Das Fingerklopfen (Kreuzprüfung & Halluzinations-Check)...")
            debate_summary = run_swarm_debate(draft_groq, draft_ds, draft_macro)

            # 3. KONSENS-SYNTHESE (Mistral / Qwen)
            logging.info("Phase 3: Der Kuchen kommt aus dem Ofen (JSON-Synthese)...")
            synthesized_data = call_synthesizer(debate_summary, draft_groq, draft_ds)

            # 4. REDAKTIONELLER SCHLIFF (Claude Haiku)
            logging.info("Phase 4: Redaktionelle Veredelung via Claude Haiku...")
            final_data = call_haiku_refine(synthesized_data)

        except Exception as e:
            logging.error(f"Fehler im Schwarm-Kollektiv: {e}")
            pipeline_health["errors"].append(f"Pipeline Critical Error: {str(e)}")
            final_data = {}

    final_data["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Schema Validation & Aliasing (ohne Erfindungen)
    logging.info("Phase 5: Schema Harmonization...")
    final_data = harmonize_and_validate_schema(final_data, debate_summary if 'debate_summary' in locals() else "")

    # Data Sanitization (Markdown Stripping)
    logging.info("Phase 6: Data Sanitization...")
    sanitized_data = sanitize_data_structure(final_data)

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
