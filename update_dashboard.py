#!/usr/bin/env python3
"""
ARGUS GRID v3.0 - Full Spectrum Multi-LLM Intelligence Engine Backend
Erfasst: Geopolitik, Spieltheorie, Sektor-Rotation (Top/Flop 5), 
Innenpolitik-Matrix, Historische Parallelen, Prädiktiver Horizont & Karten-Hotspots.
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

try:
    from sources import SOURCES
except ImportError:
    logging.warning("sources.py nicht gefunden. Verwende leere Quellenliste.")
    SOURCES = []

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

MAX_FEED_WORKERS = 40
FEED_TIMEOUT = 8
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

CURRENT_DATE_STR = datetime.now(timezone.utc).strftime("%d.%m.%Y")
CURRENT_YEAR = datetime.now(timezone.utc).year

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


def clean_expert_input(raw_text: str) -> str:
    if not raw_text:
        return ""
    error_patterns = [
        r"Error 4\d\d", r"Error 5\d\d", r"Rate limit exceeded",
        r"Unauthorized", r"Invalid API Key", r"Internal Server Error",
        r"Traceback \(most recent call last\):", r"HTTPError"
    ]
    for pattern in error_patterns:
        if re.search(pattern, raw_text, re.IGNORECASE):
            return ""
    return raw_text.strip()


def repair_and_parse_json(raw_text: str) -> dict:
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


def select_balanced_articles(articles: list, max_count: int = 120) -> list:
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
    if not isinstance(data, dict):
        data = {}

    data["ampel_status"] = data.get("ampel_status") or "GELB"
    data["ampel_reason_simple"] = data.get("ampel_reason_simple") or "Erhöhte geopolitische Spannungen."
    data["daily_executive_summary"] = data.get("daily_executive_summary") or "Lagedaten werden verarbeitet."
    data["daily_executive_summary_simple"] = data.get("daily_executive_summary_simple") or "Lagedaten werden verarbeitet."

    geoscore = data.get("overall_geoscore") or data.get("geoscore") or 50
    defcon = data.get("defcon_level") or data.get("defcon") or 3

    try:
        data["overall_geoscore"] = int(geoscore)
        data["geoscore"] = int(geoscore)
    except (ValueError, TypeError):
        data["overall_geoscore"] = 50
        data["geoscore"] = 50

    try:
        data["defcon_level"] = int(defcon)
        data["defcon"] = int(defcon)
    except (ValueError, TypeError):
        data["defcon_level"] = 3
        data["defcon"] = 3

    ds_clean = debate_summary.strip() if debate_summary else ""
    text_content = ds_clean if ds_clean else "Keine spezifische Spieltheorie-Debatte erfasst."
    data["game_theory_analysis"] = data.get("game_theory_analysis") or text_content

    # Hotspots mit Type-Sicherung
    hotspots = data.get("conflict_hotspots", [])
    if isinstance(hotspots, list):
        for h in hotspots:
            if isinstance(h, dict):
                if "lng" not in h and "lon" in h:
                    h["lng"] = h["lon"]
                if "lon" not in h and "lng" in h:
                    h["lon"] = h["lng"]
                if "type" not in h:
                    h["type"] = "conflict"
    else:
        data["conflict_hotspots"] = []

    # Graph-Netzwerk
    gn = data.get("graph_network", {})
    if isinstance(gn, dict):
        nodes = gn.get("nodes", [])
        edges = gn.get("edges", gn.get("links", []))
        
        valid_nodes = []
        if isinstance(nodes, list):
            for n in nodes:
                if isinstance(n, dict):
                    node_id = str(n.get("id", n.get("name", n.get("label", "")))).strip()
                    n["id"] = node_id
                    n["name"] = n.get("name") or n.get("label") or node_id
                    n["label"] = n.get("label") or n["name"]
                    if node_id:
                        valid_nodes.append(n)
        
        valid_edges = []
        if isinstance(edges, list):
            for e in edges:
                if isinstance(e, dict):
                    src = str(e.get("from") or e.get("source", "")).strip()
                    tgt = str(e.get("to") or e.get("target", "")).strip()
                    e["from"] = src
                    e["to"] = tgt
                    e["source"] = src
                    e["target"] = tgt
                    if src and tgt:
                        valid_edges.append(e)
        
        data["graph_network"] = {"nodes": valid_nodes, "edges": valid_edges, "links": valid_edges}
    else:
        data["graph_network"] = {"nodes": [], "edges": [], "links": []}

    # Arrays absichern
    for array_key in ["predictive_horizon", "historical_precedents", "domestic_policy_matrix", "stress_test_scenarios", "key_takeaways"]:
        if array_key not in data or not isinstance(data[array_key], list):
            data[array_key] = []

    # Market Rotation Object
    eq = data.get("equity_rotation", {})
    if not isinstance(eq, dict):
        eq = {}
    if "top5_buys" not in eq or not isinstance(eq["top5_buys"], list):
        eq["top5_buys"] = []
    if "flop5_sells" not in eq or not isinstance(eq["flop5_sells"], list):
        eq["flop5_sells"] = []
    data["equity_rotation"] = eq

    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    data["pipeline_health"] = pipeline_health

    return data


def fetch_single_feed(source: dict) -> list:
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
    pipeline_health["feeds_total"] = len(sources_list)
    all_articles = []
    successful_feeds = 0
    failed_feeds = 0

    logging.info(f"Starte Feed-Ingestion für {len(sources_list)} Quellen...")

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
    logging.info(f"Ingestion beendet: {len(all_articles)} Artikel geladen.")
    return all_articles


def baker_groq(payload: str) -> str:
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
                    "content": f"DATUM: {CURRENT_DATE_STR} (JAHR {CURRENT_YEAR}). Analysiere alle Feeds. Erstelle ein vollständiges Lagedokument inklusive Sektor-Impulsen, Innenpolitik und Geodaten.\n\nFEEDS:\n{payload}"
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
    if not DEEPSEEK_API_KEY:
        return ""
    for model_name in ["deepseek-reasoner", "deepseek-chat"]:
        try:
            res = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model_name,
                    "messages": [{
                        "role": "user",
                        "content": f"DATUM: {CURRENT_DATE_STR} (JAHR {CURRENT_YEAR}). Analysiere die Lage aus strategischer und spieltheoretischer Sicht. Identifiziere historische Parallelen und prädiktive Indikatoren.\n\nFEEDS:\n{payload[:2500]}"
                    }],
                    "max_tokens": 1800
                },
                timeout=45
            )
            if res.status_code == 200:
                pipeline_health["bakers_active"].append(f"DeepSeek ({model_name})")
                return clean_expert_input(res.json()["choices"][0]["message"]["content"])
        except Exception as e:
            logging.warning(f"DeepSeek Fehler: {e}")
    return ""


def baker_qwen_or_grok(payload: str) -> str:
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
                    "content": f"DATUM: {CURRENT_DATE_STR} (JAHR {CURRENT_YEAR}). Analysiere Makroökonomie, Chokepoints, Schifffahrt, Migration und BRICS.\n\nFEEDS:\n{payload[:3000]}"
                }],
                "max_tokens": 1800
            },
            timeout=35
        )
        if res.status_code == 200:
            pipeline_health["bakers_active"].append(f"Swarm-Partner ({model.split('/')[-1]})")
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.warning(f"Qwen/Grok Fehler: {e}")
    return ""


def run_swarm_debate(draft_groq: str, draft_deepseek: str, draft_macro: str) -> str:
    combined_drafts = f"ENTWURF GROQ/OSINT:\n{draft_groq}\n\nENTWURF DEEPSEEK:\n{draft_deepseek}\n\nENTWURF MACRO:\n{draft_macro}".strip()
    api_key = MISTRAL_API_KEY or OPENROUTER_API_KEY or ANTHROPIC_API_KEY or GROQ_API_KEY
    if not api_key or not combined_drafts:
        return combined_drafts

    endpoint = "https://api.mistral.ai/v1/chat/completions" if MISTRAL_API_KEY else ("https://openrouter.ai/api/v1/chat/completions" if OPENROUTER_API_KEY else "https://api.groq.com/openai/v1/chat/completions")
    model = "mistral-large-latest" if MISTRAL_API_KEY else ("qwen/qwen-2.5-72b-instruct" if OPENROUTER_API_KEY else "llama-3.3-70b-versatile")

    prompt = (
        f"HEUTIGES DATUM: {CURRENT_DATE_STR} (JAHR {CURRENT_YEAR}).\n"
        "Du bist der Moderator der KI-Analysten-Konferenz. Führe die Kreuzprüfung der Entwürfe durch ('Fingerklopfen'):\n\n"
        f"{combined_drafts[:3000]}\n\n"
        f"1. Halte strikt das Jahr {CURRENT_YEAR} ein.\n"
        "2. Identifiziere direkte Widersprüche, Fehlinformationen und Halluzinationen.\n"
        "3. Bilde den verifizierten KERN-KONSENS aller Modelle.\n"
        "Formuliere eine messerscharfe Synthese in gut strukturiertem Markdown mit Tabellen!"
    )

    try:
        res = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 1800},
            timeout=35
        )
        if res.status_code == 200:
            pipeline_health["swarm_debate_status"] = "SUCCESS"
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        pipeline_health["swarm_debate_status"] = f"ERROR ({e})"

    return combined_drafts


def call_synthesizer(debate_result: str, raw_payload: str) -> dict:
    api_key = MISTRAL_API_KEY or OPENROUTER_API_KEY or GROQ_API_KEY
    if not api_key:
        return {}

    endpoint = "https://api.mistral.ai/v1/chat/completions" if MISTRAL_API_KEY else "https://openrouter.ai/api/v1/chat/completions"
    model = "mistral-large-latest" if MISTRAL_API_KEY else "qwen/qwen-2.5-72b-instruct"

    prompt = (
        f"HEUTIGES DATUM: {CURRENT_DATE_STR} (JAHR {CURRENT_YEAR}).\n"
        "Generiere aus dem Konsens und den Feeds das finale JSON-Objekt. Antworte AUSSCHLIESSLICH mit validem JSON!\n\n"
        f"DEBATTE:\n{debate_result[:2500]}\n\nFEEDS:\n{raw_payload[:2500]}\n\n"
        "ERFORDERLICHE JSON-STRUKTUR:\n"
        "{\n"
        '  "overall_geoscore": int (0-100),\n'
        '  "geoscore": int (0-100),\n'
        '  "defcon_level": int (1-5),\n'
        '  "defcon": int (1-5),\n'
        '  "ampel_status": "GRÜN" | "GELB" | "ROT",\n'
        '  "ampel_reason_simple": "...",\n'
        '  "daily_executive_summary": "...",\n'
        '  "daily_executive_summary_simple": "...",\n'
        '  "key_takeaways": ["..."],\n'
        '  "equity_rotation": {\n'
        '    "top5_buys": [{"asset": "Sektor/Aktie/ETF", "reason": "..."}],\n'
        '    "flop5_sells": [{"asset": "Sektor/Aktie/ETF", "reason": "..."}]\n'
        '  },\n'
        '  "domestic_policy_matrix": [\n'
        '    {"region": "USA/EU/China/BRICS/Nahost", "stability": "ROT/GELB/GRÜN", "dynamics": "...", "spillover": "..."}\n'
        '  ],\n'
        '  "historical_precedents": [\n'
        '    {"event": "Historisches Ereignis", "period": "Jahr/Epoche", "similarity": "Parallele zu 2026", "takeaway": "Erkenntnis für heute"}\n'
        '  ],\n'
        '  "predictive_horizon": [\n'
        '    {"timeframe": "30 Tage (Taktisch)", "forecast": "...", "probability": "Hoch/Mittel/Niedrig", "early_warning_indicators": ["..."]}\n'
        '  ],\n'
        '  "conflict_hotspots": [\n'
        '    {"name": "...", "lat": float, "lon": float, "type": "chokepoint/maritime/refugee/conflict", "intensity": "ROT/GELB", "description": "..."}\n'
        '  ],\n'
        '  "graph_network": {\n'
        '    "nodes": [{"id": "...", "label": "...", "group": "...", "val": 5}],\n'
        '    "edges": [{"from": "...", "to": "...", "label": "..."}]\n'
        '  }\n'
        "}"
    )

    try:
        res = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"} if "mistral" in endpoint else None
            },
            timeout=60
        )
        if res.status_code == 200:
            return repair_and_parse_json(res.json()["choices"][0]["message"]["content"])
    except Exception as e:
        logging.warning(f"Synthesizer Exception: {e}")

    return {}


def call_haiku_refine(data_dict: dict) -> dict:
    if not ANTHROPIC_API_KEY or not data_dict:
        return data_dict

    exec_summary = data_dict.get("daily_executive_summary", "")
    ampel_reason = data_dict.get("ampel_reason_simple", "")

    if not exec_summary:
        return data_dict

    prompt = (
        f"DATUM: {CURRENT_DATE_STR} (JAHR {CURRENT_YEAR}). Formuliere für Laien verständlich:\n\n"
        f"1. Executive Summary:\n{exec_summary}\n\n2. Ampel Begründung:\n{ampel_reason}\n\n"
        'JSON: {"daily_executive_summary_simple": "...", "ampel_reason_simple": "..."}'
    )

    try:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": "claude-3-5-haiku-20241022", "max_tokens": 1000, "messages": [{"role": "user", "content": prompt}]},
            timeout=25
        )
        if res.status_code == 200:
            refined = repair_and_parse_json(res.json()["content"][0]["text"])
            data_dict.update(refined)
    except Exception as e:
        logging.warning(f"Haiku Exception: {e}")

    return data_dict


def main():
    logging.info(f"=== ARGUS GRID v3.0 Start ({CURRENT_DATE_STR}) ===")
    articles = fetch_all_feeds(SOURCES)

    final_data = {}
    debate_summary = ""

    if articles:
        try:
            selected = select_balanced_articles(articles, max_count=100)
            raw_payload = "\n".join([f"[{a['category']} | {a['bias']}] {a['source']}: {a['title']} - {a['summary']}" for a in selected])

            with ThreadPoolExecutor(max_workers=3) as executor:
                f_groq = executor.submit(baker_groq, raw_payload)
                f_ds   = executor.submit(baker_deepseek, raw_payload)
                f_macro = executor.submit(baker_qwen_or_grok, raw_payload)

                draft_groq, draft_ds, draft_macro = f_groq.result(), f_ds.result(), f_macro.result()

            debate_summary = run_swarm_debate(draft_groq, draft_ds, draft_macro)
            synthesized_data = call_synthesizer(debate_summary, raw_payload)
            final_data = call_haiku_refine(synthesized_data)

        except Exception as e:
            logging.error(f"Fehler im Schwarm: {e}")

    final_data = harmonize_and_validate_schema(final_data, debate_summary)

    output_path = "data.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        logging.info(f"Pipeline erfolgreich. Speicherung in '{output_path}'.")
    except Exception as e:
        logging.critical(f"Schreibfehler: {e}")


if __name__ == "__main__":
    main()
