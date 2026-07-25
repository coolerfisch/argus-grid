#!/usr/bin/env python3
"""
ARGUS GRID v3.0 - Full Spectrum Multi-LLM Intelligence Engine Backend
Multi-Source Data Ingestion Engine:
1. RSS & Primary Source Feeds (mit RSSHub Support)
2. GDELT Project DOC 2.0 Real-Time Event Stream
3. Telegram Public OSINT Channel Stream (t.me/s/ Scraping)
4. OpenSky Network Live ADS-B Military Tracking
5. Multi-LLM Swarm (Groq, DeepSeek, Qwen/Grok, Mistral, Haiku)
6. Dynamic Knowledge Graph Memory (14-Tage-Decay)
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

# ============================================================
# KONSTANTEN & SCHLÜSSEL
# ============================================================
MAX_FEED_WORKERS = 20
FEED_TIMEOUT = 12
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
FEED_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    "Cache-Control": "no-cache",
}

CURRENT_DATE_STR = datetime.now(timezone.utc).strftime("%d.%m.%Y")
CURRENT_YEAR = datetime.now(timezone.utc).year

# API Keys
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

OPENSKY_USER = os.environ.get("OPENSKY_USER")
OPENSKY_PASSWORD = os.environ.get("OPENSKY_PASSWORD")

# Optional: Eigene Docker RSSHub Instanz (Fallback: Öffentliche Instanz)
RSSHUB_BASE_URL = os.environ.get("RSSHUB_BASE_URL", "https://rsshub.app")

pipeline_health = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "feeds_total": 0,
    "feeds_successful": 0,
    "feeds_failed": 0,
    "gdelt_articles": 0,
    "telegram_posts": 0,
    "bakers_active": [],
    "swarm_debate_status": "PENDING",
    "synthesizer_status": "PENDING",
    "haiku_status": "PENDING",
    "opensky_status": "PENDING",
    "graph_merge_status": "PENDING",
    "errors": []
}

# ÖFFENTLICHE TELEGRAM OSINT KANÄLE (Direkt-Scraping ohne Auth)
TELEGRAM_OSINT_CHANNELS = [
    {"name": "UKMTO Alerts", "channel": "ukmto_official", "cat": "Schifffahrt"},
    {"name": "Intel Slava World", "channel": "intelSlava", "cat": "OSINT/Militär"},
    {"name": "War Monitor", "channel": "warmonitor", "cat": "OSINT/Militär"},
    {"name": "Clash Report", "channel": "clashreport", "cat": "OSINT/Militär"},
    {"name": "BNO News", "channel": "bnonews", "cat": "Eilmeldungen"}
]


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


# ============================================================
# PIPELINE 1: GDELT PROJECT DOC 2.0 API INTEGRATION
# ============================================================
def fetch_gdelt_data() -> list:
    """Ruft Echtzeit-Ereignisse und Tonlagen aus dem GDELT Project ab (Kostenlos, ohne API-Key)."""
    logging.info("[GDELT] Starte Abfrage der GDELT DOC 2.0 API...")
    query = "(geopolitics OR military OR shipping OR centralbank OR sanctions OR embargo OR missile)"
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=artlist&maxrecords=35&format=json&sort=date"
    
    articles = []
    try:
        res = requests.get(url, headers=FEED_HEADERS, timeout=12)
        if res.status_code == 200:
            data = res.json()
            raw_arts = data.get("articles", [])
            for a in raw_arts:
                title = a.get("title", "").strip()
                link = a.get("url", "").strip()
                domain = a.get("domain", "GDELT Global")
                seendate = a.get("seendate", "")

                if title and link:
                    articles.append({
                        "title": title,
                        "summary": f"GDELT Realtime Event Signal von Source [{domain}] (Datum: {seendate})",
                        "link": link,
                        "source": f"GDELT ({domain})",
                        "category": "GDELT/OSINT",
                        "bias": "RAW-SIGNAL",
                        "weight": 1.1
                    })
            pipeline_health["gdelt_articles"] = len(articles)
            logging.info(f"[GDELT] {len(articles)} Signale erfolgreich geladen.")
    except Exception as e:
        logging.warning(f"[GDELT] Fehler bei Abfrage: {e}")
    
    return articles


# ============================================================
# PIPELINE 2: TELEGRAM OSINT PUBLIC CHANNEL STREAM (t.me/s/)
# ============================================================
def fetch_single_telegram_channel(item: dict) -> list:
    """Liest öffentliche Telegram-Kanäle über die t.me/s/-Webansicht als Rohdaten-Feed aus."""
    channel = item["channel"]
    source_name = item["name"]
    category = item["cat"]
    url = f"https://t.me/s/{channel}"

    posts = []
    try:
        res = requests.get(url, headers=FEED_HEADERS, timeout=10)
        if res.status_code == 200:
            # Einfaches Regex-Matching für Nachrichten-Texte in der HTML-Vorschau
            raw_texts = re.findall(r'<div class="tgme_widget_message_text[^">]*>(.*?)</div>', res.text, re.DOTALL)
            for raw_html in raw_texts[-5:]:  # Letzte 5 Beiträge
                clean_msg = re.sub(r'<[^>]+>', '', raw_html).strip()
                clean_msg = re.sub(r'\s+', ' ', clean_msg)
                
                if len(clean_msg) > 20:
                    posts.append({
                        "title": f"[{source_name}] {clean_msg[:80]}...",
                        "summary": clean_msg[:300],
                        "link": url,
                        "source": f"Telegram: @{channel}",
                        "category": category,
                        "bias": "TELEGRAM-RAW-OSINT",
                        "weight": 1.0
                    })
    except Exception as e:
        logging.debug(f"[TELEGRAM] Fehler bei @{channel}: {e}")

    return posts


def fetch_all_telegram_osint() -> list:
    """Startet parallele Ingestion für öffentliche Telegram-Kanäle."""
    logging.info(f"[TELEGRAM] Starte Ingestion für {len(TELEGRAM_OSINT_CHANNELS)} OSINT-Kanäle...")
    all_posts = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_single_telegram_channel, ch) for ch in TELEGRAM_OSINT_CHANNELS]
        for f in as_completed(futures):
            res = f.result()
            if res:
                all_posts.extend(res)

    pipeline_health["telegram_posts"] = len(all_posts)
    logging.info(f"[TELEGRAM] {len(all_posts)} Live-Meldungen erfasst.")
    return all_posts


# ============================================================
# PIPELINE 3: OPENSKY LIVE ADS-B TRACKER
# ============================================================
def fetch_opensky_flights() -> list:
    """Lädt Live-Flugdaten aus strategischen Krisenzonen via OpenSky Network API."""
    if not OPENSKY_USER or not OPENSKY_PASSWORD:
        logging.info("[OPENSKY] Keine Zugangsdaten gesetzt. Überspringe Live-Flug-Tracking.")
        pipeline_health["opensky_status"] = "SKIPPED"
        return []

    regions = [
        {"name": "Schwarzes Meer / Osteuropa", "bbox": (40.0, 25.0, 52.0, 42.0)},
        {"name": "Naher Osten / Rotes Meer", "bbox": (12.0, 32.0, 36.0, 52.0)},
        {"name": "Taiwan-Straße / Ostasien", "bbox": (15.0, 115.0, 28.0, 126.0)},
    ]

    mil_keywords = ["FORTE", "LAGR", "HOMER", "JAKE", "DUKE", "HAWK", "RRR", "NATO", "CNV", "NAVY", "USAF", "BAF", "GAF"]
    flight_hotspots = []
    total_found = 0

    for reg in regions:
        lamin, lomin, lamax, lomax = reg["bbox"]
        url = f"https://opensky-network.org/api/states/all?lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}"

        try:
            res = requests.get(url, auth=(OPENSKY_USER, OPENSKY_PASSWORD), timeout=10)
            if res.status_code == 200:
                data = res.json()
                states = data.get("states", []) or []
                
                region_count = 0
                for st in states:
                    callsign = (st[1] or "").strip()
                    longitude = st[5]
                    latitude = st[6]
                    altitude = st[7]
                    velocity = st[9]
                    on_ground = st[8]

                    if latitude is None or longitude is None or on_ground:
                        continue

                    is_mil = any(kw in callsign.upper() for kw in mil_keywords)

                    if is_mil or region_count < 2:
                        alt_km = round((altitude or 0) / 1000, 1)
                        speed_kmh = round((velocity or 0) * 3.6)
                        display_name = f"Flug {callsign}" if callsign else f"ADS-B Signal {st[0][:6].upper()}"

                        flight_hotspots.append({
                            "name": display_name,
                            "region": reg["name"],
                            "lat": float(latitude),
                            "lon": float(longitude),
                            "lng": float(longitude),
                            "type": "flight",
                            "intensity": "ROT" if is_mil else "GELB",
                            "description": f"Live ADS-B Korridor ({reg['name']}): Höhe ~{alt_km}km, Speed ~{speed_kmh}km/h. Callsign: {callsign or 'Unbekannt'}",
                            "impact": "Militärische Luftraumüberwachung / Aufklärung" if is_mil else "Luftverkehr-Korridor"
                        })
                        region_count += 1
                        total_found += 1
        except Exception as e:
            logging.warning(f"[OPENSKY] Fehler bei Abfrage von {reg['name']}: {e}")

    pipeline_health["opensky_status"] = f"SUCCESS ({total_found} Signale)"
    return flight_hotspots


# ============================================================
# PERSISTENTES GRAPHEN MERGING & DECAY
# ============================================================
def load_existing_graph(filepath="data.json") -> dict:
    if not os.path.exists(filepath):
        return {"nodes": [], "edges": []}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            old_data = json.load(f)
            gn = old_data.get("graph_network", {})
            if isinstance(gn, dict):
                return {
                    "nodes": gn.get("nodes", []),
                    "edges": gn.get("edges", gn.get("links", []))
                }
    except Exception as e:
        logging.warning(f"[GRAPH Memory] Konnte alten Graphen nicht laden: {e}")
    return {"nodes": [], "edges": []}


def merge_and_decay_graph(new_graph: dict, old_graph: dict, max_age_days: int = 14) -> dict:
    now_dt = datetime.now(timezone.utc)
    today_str = now_dt.strftime("%Y-%m-%d")

    node_dict = {}

    for n in old_graph.get("nodes", []):
        if not isinstance(n, dict): continue
        raw_id = str(n.get("id") or n.get("name") or n.get("label", "")).strip()
        nid = raw_id.lower()
        if not nid: continue

        node_dict[nid] = {
            "id": nid,
            "label": n.get("label") or n.get("name") or raw_id,
            "group": n.get("group", "actor"),
            "val": int(n.get("val", 5)),
            "first_seen": n.get("first_seen", today_str),
            "last_seen": n.get("last_seen", today_str),
            "seen_today": False
        }

    for n in new_graph.get("nodes", []):
        if not isinstance(n, dict): continue
        raw_id = str(n.get("id") or n.get("name") or n.get("label", "")).strip()
        nid = raw_id.lower()
        if not nid: continue

        new_val = int(n.get("val", 5))
        new_group = n.get("group") or "actor"
        new_label = n.get("label") or n.get("name") or raw_id

        if nid in node_dict:
            node_dict[nid]["val"] = min(22, node_dict[nid]["val"] + max(1, new_val // 2))
            node_dict[nid]["last_seen"] = today_str
            node_dict[nid]["seen_today"] = True
            if new_group and new_group != "actor":
                node_dict[nid]["group"] = new_group
        else:
            node_dict[nid] = {
                "id": nid,
                "label": new_label,
                "group": new_group,
                "val": max(5, new_val),
                "first_seen": today_str,
                "last_seen": today_str,
                "seen_today": True
            }

    final_nodes = []
    for nid, n in node_dict.items():
        if not n["seen_today"]:
            try:
                last_dt = datetime.strptime(n["last_seen"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                age_days = (now_dt - last_dt).days
            except Exception:
                age_days = 0

            if age_days > max_age_days:
                continue
            else:
                n["val"] = max(3, n["val"] - 1)

        del n["seen_today"]
        final_nodes.append(n)

    valid_node_ids = {n["id"] for n in final_nodes}
    edge_dict = {}

    for e in old_graph.get("edges", []):
        if not isinstance(e, dict): continue
        src = str(e.get("from") or e.get("source", "")).strip().lower()
        tgt = str(e.get("to") or e.get("target", "")).strip().lower()
        if not src or not tgt: continue

        edge_key = f"{src}-->{tgt}"
        edge_dict[edge_key] = {
            "from": src, "to": tgt, "source": src, "target": tgt,
            "label": e.get("label", ""), "last_seen": e.get("last_seen", today_str), "seen_today": False
        }

    for e in new_graph.get("edges", []):
        if not isinstance(e, dict): continue
        src = str(e.get("from") or e.get("source", "")).strip().lower()
        tgt = str(e.get("to") or e.get("target", "")).strip().lower()
        if not src or not tgt: continue

        edge_key = f"{src}-->{tgt}"
        lbl = e.get("label", "")

        if edge_key in edge_dict:
            edge_dict[edge_key]["last_seen"] = today_str
            edge_dict[edge_key]["seen_today"] = True
            if lbl: edge_dict[edge_key]["label"] = lbl
        else:
            edge_dict[edge_key] = {
                "from": src, "to": tgt, "source": src, "target": tgt,
                "label": lbl, "last_seen": today_str, "seen_today": True
            }

    final_edges = []
    for e_key, e in edge_dict.items():
        if e["from"] not in valid_node_ids or e["to"] not in valid_node_ids:
            continue

        if not e["seen_today"]:
            try:
                last_dt = datetime.strptime(e["last_seen"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                age_days = (now_dt - last_dt).days
            except Exception:
                age_days = 0

            if age_days > max_age_days:
                continue

        del e["seen_today"]
        final_edges.append(e)

    pipeline_health["graph_merge_status"] = f"SUCCESS ({len(final_nodes)} Nodes)"
    return {"nodes": final_nodes, "edges": final_edges, "links": final_edges}


def select_balanced_articles(articles: list, max_count: int = 140) -> list:
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


def harmonize_and_validate_schema(data: dict, debate_summary: str, live_flights: list = None, old_graph: dict = None) -> dict:
    if not isinstance(data, dict):
        data = {}

    data["ampel_status"] = (data.get("ampel_status") or "GELB").upper()
    data["ampel_reason_simple"] = data.get("ampel_reason_simple") or "Erhöhte allgemeine Volatilität im geopolitischen Raum."
    data["daily_executive_summary"] = data.get("daily_executive_summary") or "Für diesen Durchlauf liegt kein vollständiges Briefing vor."
    data["daily_executive_summary_simple"] = data.get("daily_executive_summary_simple") or data["daily_executive_summary"]

    takeaways = data.get("key_takeaways") or data.get("simple_key_takeaways") or []
    if not isinstance(takeaways, list): takeaways = []
    data["key_takeaways"] = takeaways
    data["simple_key_takeaways"] = takeaways

    geoscore_val = data.get("overall_geoscore") or data.get("geoscore") or 75
    try: geoscore_num = int(geoscore_val.get("current_score", 75)) if isinstance(geoscore_val, dict) else int(geoscore_val)
    except: geoscore_num = 75

    data["overall_geoscore"] = geoscore_num
    data["geoscore"] = {"current_score": geoscore_num, "status": "Erhöht"}

    defcon_val = data.get("defcon_level") or data.get("defcon") or 3
    try: defcon_num = int(defcon_val)
    except: defcon_num = 3

    data["defcon_level"] = defcon_num
    data["defcon"] = defcon_num
    data["defcon_status"] = {"level": defcon_num, "label": f"DEFCON {defcon_num}"}

    data["market_regime"] = data.get("market_regime") or "Geopolitische Segmentierung"
    data["top_risk"] = data.get("top_risk") or "Lieferketten & Chokepoints"

    ds_clean = debate_summary.strip() if debate_summary else ""
    data["game_theory_analysis"] = data.get("game_theory_analysis") or (ds_clean if ds_clean else "Keine Spieltheorie-Debatte erfasst.")

    hotspots = data.get("conflict_hotspots", [])
    if not isinstance(hotspots, list): hotspots = []

    for h in hotspots:
        if isinstance(h, dict):
            if "lng" not in h and "lon" in h: h["lng"] = h["lon"]
            if "lon" not in h and "lng" in h: h["lon"] = h["lng"]
            if "region" not in h and "name" in h: h["region"] = h["name"]
            if "impact" not in h and "description" in h: h["impact"] = h["description"]
            if "type" not in h: h["type"] = "conflict"

    if live_flights and isinstance(live_flights, list):
        hotspots.extend(live_flights)

    data["conflict_hotspots"] = hotspots

    raw_gn = data.get("graph_network", {})
    if not isinstance(raw_gn, dict): raw_gn = {"nodes": [], "edges": []}
    data["graph_network"] = merge_and_decay_graph(raw_gn, old_graph or {"nodes": [], "edges": []})

    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    data["pipeline_health"] = pipeline_health

    return data


def fetch_single_feed(source: dict) -> list:
    url = source.get("url")
    name = source.get("name", "Unknown")
    category = source.get("cat", source.get("category", "General"))
    bias = source.get("bias", "NEUTRAL")
    weight = source.get("weight", 1.0)

    if not url or not isinstance(url, str): return []
    url = url.strip().strip("[]()")

    # RSSHub Support: Falls URL ein RSSHub-Relay ist
    if url.startswith("/"):
        url = f"{RSSHUB_BASE_URL.rstrip('/')}{url}"

    articles = []
    try:
        response = requests.get(url, headers=FEED_HEADERS, timeout=FEED_TIMEOUT, allow_redirects=True)
        if response.status_code != 200: return []

        parsed = feedparser.parse(response.content)
        for entry in parsed.entries[:8]:
            title = (entry.get("title") or "").strip()
            summary = (entry.get("summary") or entry.get("description") or "").strip()
            link = (entry.get("link") or "").strip()
            summary_clean = re.sub(r"<[^>]+>", "", summary)[:300]

            if title:
                articles.append({
                    "title": title, "summary": summary_clean, "link": link,
                    "source": name, "category": category, "bias": bias, "weight": weight
                })
        return articles
    except Exception:
        return []


def fetch_all_feeds(sources_list: list) -> list:
    pipeline_health["feeds_total"] = len(sources_list)
    all_articles = []
    successful = 0
    failed = 0

    logging.info(f"Starte RSS-Ingestion für {len(sources_list)} Quellen...")
    with ThreadPoolExecutor(max_workers=MAX_FEED_WORKERS) as executor:
        future_to_source = {executor.submit(fetch_single_feed, src): src for src in sources_list}
        for future in as_completed(future_to_source):
            res = future.result()
            if res:
                all_articles.extend(res)
                successful += 1
            else:
                failed += 1

    pipeline_health["feeds_successful"] = successful
    pipeline_health["feeds_failed"] = failed
    return all_articles


def baker_groq(payload: str) -> str:
    if not GROQ_API_KEY: return ""
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": f"DATUM: {CURRENT_DATE_STR} ({CURRENT_YEAR}). FEEDS:\n{payload}"}],
                "max_tokens": 1800
            },
            timeout=35
        )
        if res.status_code == 200:
            pipeline_health["bakers_active"].append("Groq (Llama-3.3)")
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e: logging.warning(f"Groq Fehler: {e}")
    return ""


def baker_deepseek(payload: str) -> str:
    if not DEEPSEEK_API_KEY: return ""
    try:
        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": f"DATUM: {CURRENT_DATE_STR} ({CURRENT_YEAR}). FEEDS:\n{payload[:2500]}"}],
                "max_tokens": 1800
            },
            timeout=45
        )
        if res.status_code == 200:
            pipeline_health["bakers_active"].append("DeepSeek")
            return clean_expert_input(res.json()["choices"][0]["message"]["content"])
    except Exception as e: logging.warning(f"DeepSeek Fehler: {e}")
    return ""


def baker_qwen_or_grok(payload: str) -> str:
    api_key = OPENROUTER_API_KEY or XAI_API_KEY or QWEN_API_KEY
    if not api_key: return ""
    endpoint = "https://openrouter.ai/api/v1/chat/completions" if OPENROUTER_API_KEY else "https://api.x.ai/v1/chat/completions"
    model = "qwen/qwen-2.5-72b-instruct" if OPENROUTER_API_KEY else "grok-2-latest"

    try:
        res = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": f"DATUM: {CURRENT_DATE_STR} ({CURRENT_YEAR}). FEEDS:\n{payload[:3000]}"}], "max_tokens": 1800},
            timeout=35
        )
        if res.status_code == 200:
            pipeline_health["bakers_active"].append(model.split('/')[-1])
            return res.json()["choices"][0]["message"]["content"]
    except Exception as e: logging.warning(f"Qwen/Grok Fehler: {e}")
    return ""


def run_swarm_debate(draft_groq: str, draft_deepseek: str, draft_macro: str) -> str:
    combined = f"GROQ:\n{draft_groq}\n\nDEEPSEEK:\n{draft_deepseek}\n\nMACRO:\n{draft_macro}".strip()
    api_key = MISTRAL_API_KEY or OPENROUTER_API_KEY or GROQ_API_KEY
    if not api_key or not combined: return combined

    endpoint = "https://api.mistral.ai/v1/chat/completions" if MISTRAL_API_KEY else "https://api.groq.com/openai/v1/chat/completions"
    model = "mistral-large-latest" if MISTRAL_API_KEY else "llama-3.3-70b-versatile"

    prompt = f"DATUM: {CURRENT_DATE_STR} ({CURRENT_YEAR}). Führe Kreuzprüfung durch ('Fingerklopfen'):\n\n{combined[:3000]}"
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
    return combined


def call_synthesizer(debate_result: str, raw_payload: str) -> dict:
    api_key = MISTRAL_API_KEY or OPENROUTER_API_KEY or GROQ_API_KEY
    if not api_key: return {}

    endpoint = "https://api.mistral.ai/v1/chat/completions" if MISTRAL_API_KEY else "https://openrouter.ai/api/v1/chat/completions"
    model = "mistral-large-latest" if MISTRAL_API_KEY else "qwen/qwen-2.5-72b-instruct"

    prompt = (
        f"DATUM: {CURRENT_DATE_STR} ({CURRENT_YEAR}). Erstelle finales JSON-Objekt:\n\n"
        f"DEBATTE:\n{debate_result[:2500]}\n\nFEEDS:\n{raw_payload[:2500]}\n\n"
        'JSON: {"overall_geoscore": 75, "defcon_level": 3, "ampel_status": "GELB", "ampel_reason_simple": "...", "daily_executive_summary": "...", "daily_executive_summary_simple": "...", "key_takeaways": ["..."], "equity_rotation": {"top5_buys": [], "flop5_sells": []}, "domestic_policy_matrix": [], "historical_precedents": [], "predictive_horizon": [], "conflict_hotspots": [], "graph_network": {"nodes": [], "edges": []}}'
    )
    try:
        res = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
            timeout=60
        )
        if res.status_code == 200:
            return repair_and_parse_json(res.json()["choices"][0]["message"]["content"])
    except Exception as e: logging.warning(f"Synthesizer Exception: {e}")
    return {}


def main():
    logging.info(f"=== ARGUS GRID v3.0 Multi-Source Pipeline ({CURRENT_DATE_STR}) ===")
    
    old_graph = load_existing_graph("data.json")

    # INGESTION 1: RSS Feeds
    articles = fetch_all_feeds(SOURCES)

    # INGESTION 2: GDELT Project API
    gdelt_articles = fetch_gdelt_data()
    articles.extend(gdelt_articles)

    # INGESTION 3: Telegram OSINT
    tg_posts = fetch_all_telegram_osint()
    articles.extend(tg_posts)

    # INGESTION 4: OpenSky Live Tracking
    live_flights = fetch_opensky_flights()

    final_data = {}
    debate_summary = ""

    if articles:
        try:
            selected = select_balanced_articles(articles, max_count=120)
            raw_payload = "\n".join([f"[{a['category']}] {a['source']}: {a['title']} - {a['summary']}" for a in selected])

            with ThreadPoolExecutor(max_workers=3) as executor:
                f_groq = executor.submit(baker_groq, raw_payload)
                f_ds   = executor.submit(baker_deepseek, raw_payload)
                f_macro = executor.submit(baker_qwen_or_grok, raw_payload)

                draft_groq, draft_ds, draft_macro = f_groq.result(), f_ds.result(), f_macro.result()

            debate_summary = run_swarm_debate(draft_groq, draft_ds, draft_macro)
            synthesized_data = call_synthesizer(debate_summary, raw_payload)
            final_data = synthesized_data

        except Exception as e:
            logging.error(f"Fehler im Schwarm: {e}")

    final_data = harmonize_and_validate_schema(
        final_data, debate_summary, live_flights=live_flights, old_graph=old_graph
    )

    output_path = "data.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        logging.info(f"Pipeline erfolgreich. {len(articles)} Gesamtsignale verarbeitet -> Speicherung in '{output_path}'.")
    except Exception as e:
        logging.critical(f"Schreibfehler: {e}")


if __name__ == "__main__":
    main()
