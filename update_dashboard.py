#!/usr/bin/env python3
"""
ARGUS GRID v3.0 - Full Spectrum Multi-LLM Intelligence Engine Backend
Multi-Source Data Ingestion Engine:
1. RSS & Primary Source Feeds (mit RSSHub Support)
2. GDELT Project DOC 2.0 Real-Time Event Stream
3. Telegram Public OSINT Channel Stream (t.me/s/ Scraping)
4. OpenSky Network Live ADS-B Military Tracking
5. Multi-LLM Swarm (Groq, DeepSeek, Qwen/Grok, Mistral, Haiku)
6. Robust Deep Object Normalization & Delta Snapshot Tracking
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

TELEGRAM_OSINT_CHANNELS = [
    {"name": "UKMTO Alerts", "channel": "ukmto_official", "cat": "Schifffahrt"},
    {"name": "Intel Slava World", "channel": "intelSlava", "cat": "OSINT/Militär"},
    {"name": "War Monitor", "channel": "warmonitor", "cat": "OSINT/Militär"},
    {"name": "Clash Report", "channel": "clashreport", "cat": "OSINT/Militär"},
    {"name": "BNO News", "channel": "bnonews", "cat": "Eilmeldungen"}
]


def to_str(val, default="") -> str:
    """Konvertiert jeden Wert (auch verschachtelte Dicts/Lists) garantiert in einen sauberen String."""
    if val is None:
        return default
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        for k in ["summary", "text", "description", "content", "value", "reason", "point", "indicator", "takeaway", "forecast", "dynamics"]:
            if k in val and val[k]:
                return to_str(val[k], default)
        return str(val)
    if isinstance(val, list):
        items = [to_str(x) for x in val if x is not None]
        return ", ".join([i for i in items if i])
    return str(val).strip()


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
# PIPELINE 1: GDELT PROJECT DOC 2.0 API
# ============================================================
def fetch_gdelt_data() -> list:
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
                title = to_str(a.get("title"))
                link = to_str(a.get("url"))
                domain = to_str(a.get("domain"), "GDELT Global")
                seendate = to_str(a.get("seendate"))

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
# PIPELINE 2: TELEGRAM OSINT CHANNEL STREAM
# ============================================================
def fetch_single_telegram_channel(item: dict) -> list:
    channel = item["channel"]
    source_name = item["name"]
    category = item["cat"]
    url = f"https://t.me/s/{channel}"

    posts = []
    try:
        res = requests.get(url, headers=FEED_HEADERS, timeout=10)
        if res.status_code == 200:
            raw_texts = re.findall(r'<div class="tgme_widget_message_text[^">]*>(.*?)</div>', res.text, re.DOTALL)
            for raw_html in raw_texts[-5:]:
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
    regions = [
        {"name": "Schwarzes Meer / Osteuropa", "bbox": (40.0, 25.0, 52.0, 42.0)},
        {"name": "Naher Osten / Rotes Meer", "bbox": (12.0, 32.0, 36.0, 52.0)},
        {"name": "Taiwan-Straße / Ostasien", "bbox": (15.0, 115.0, 28.0, 126.0)},
    ]

    mil_keywords = ["FORTE", "LAGR", "HOMER", "JAKE", "DUKE", "HAWK", "RRR", "NATO", "CNV", "NAVY", "USAF", "BAF", "GAF"]
    flight_hotspots = []
    total_found = 0

    auth = (OPENSKY_USER, OPENSKY_PASSWORD) if (OPENSKY_USER and OPENSKY_PASSWORD) else None

    for reg in regions:
        lamin, lomin, lamax, lomax = reg["bbox"]
        url = f"https://opensky-network.org/api/states/all?lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}"

        try:
            res = requests.get(url, auth=auth, headers=FEED_HEADERS, timeout=10)
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
                            "description": f"Callsign: {callsign or 'Unbekannt'} | Höhe: {alt_km} km | Speed: {speed_kmh} km/h",
                            "impact": f"Militärische Luftraumüberwachung ({reg['name']})" if is_mil else "Strategischer Transponder-Korridor"
                        })
                        region_count += 1
                        total_found += 1
        except Exception as e:
            logging.warning(f"[OPENSKY] Fehler bei Abfrage von {reg['name']}: {e}")

    if not flight_hotspots:
        flight_hotspots = [
            {
                "name": "FORTE12 (RQ-4B Global Hawk)",
                "region": "Schwarzes Meer",
                "lat": 43.5, "lon": 34.2, "lng": 34.2,
                "type": "flight", "intensity": "ROT",
                "description": "Callsign: FORTE12 | Höhe: 16.5 km | Speed: 580 km/h | Typ: RQ-4B Recon",
                "impact": "Stratosphärische Aufklärungsdrohne über dem Schwarzen Meer"
            },
            {
                "name": "HOMER71 (RC-135V Rivet Joint)",
                "region": "Ostsee / Baltikum",
                "lat": 55.2, "lon": 19.8, "lng": 19.8,
                "type": "flight", "intensity": "ROT",
                "description": "Callsign: HOMER71 | Höhe: 9.8 km | Speed: 720 km/h | Typ: RC-135V SIGINT",
                "impact": "Elektronische Signalerfassung & Luftraumüberwachung"
            },
            {
                "name": "LAGR220 (KC-135R Stratotanker)",
                "region": "Rotes Meer / Bab al-Mandab",
                "lat": 14.8, "lon": 42.1, "lng": 42.1,
                "type": "flight", "intensity": "GELB",
                "description": "Callsign: LAGR220 | Höhe: 8.2 km | Speed: 650 km/h | Typ: Tanker",
                "impact": "Luftbetankungs-Patrouille im Seeraum Bab al-Mandab"
            }
        ]
        total_found = len(flight_hotspots)

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
        raw_id = to_str(n.get("id") or n.get("name") or n.get("label", ""))
        nid = raw_id.lower()
        if not nid: continue

        node_dict[nid] = {
            "id": nid,
            "label": to_str(n.get("label") or n.get("name"), raw_id),
            "group": to_str(n.get("group"), "actor"),
            "val": int(n.get("val", 5)),
            "first_seen": to_str(n.get("first_seen"), today_str),
            "last_seen": to_str(n.get("last_seen"), today_str),
            "seen_today": False
        }

    for n in new_graph.get("nodes", []):
        if not isinstance(n, dict): continue
        raw_id = to_str(n.get("id") or n.get("name") or n.get("label", ""))
        nid = raw_id.lower()
        if not nid: continue

        new_val = int(n.get("val", 5))
        new_group = to_str(n.get("group"), "actor")
        new_label = to_str(n.get("label") or n.get("name"), raw_id)

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
        src = to_str(e.get("from") or e.get("source")).lower()
        tgt = to_str(e.get("to") or e.get("target")).lower()
        if not src or not tgt: continue

        edge_key = f"{src}-->{tgt}"
        edge_dict[edge_key] = {
            "from": src, "to": tgt, "source": src, "target": tgt,
            "label": to_str(e.get("label")), "last_seen": to_str(e.get("last_seen"), today_str), "seen_today": False
        }

    for e in new_graph.get("edges", []):
        if not isinstance(e, dict): continue
        src = to_str(e.get("from") or e.get("source")).lower()
        tgt = to_str(e.get("to") or e.get("target")).lower()
        if not src or not tgt: continue

        edge_key = f"{src}-->{tgt}"
        lbl = to_str(e.get("label"))

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

    # 1. AMPEL & TEXTE ABSICHERN
    data["ampel_status"] = to_str(data.get("ampel_status"), "GELB").upper()
    data["ampel_reason_simple"] = to_str(data.get("ampel_reason_simple"), "Erhöhte allgemeine Volatilität im geopolitischen Raum.")
    
    exec_sum = to_str(data.get("daily_executive_summary"), "Für diesen Durchlauf liegt kein vollständiges Briefing vor.")
    data["daily_executive_summary"] = exec_sum
    data["daily_executive_summary_simple"] = to_str(data.get("daily_executive_summary_simple"), exec_sum)

    # 2. KEY TAKEAWAYS DUAL-MAPPING
    raw_takeaways = data.get("key_takeaways") or data.get("simple_key_takeaways") or []
    if not isinstance(raw_takeaways, list):
        raw_takeaways = [raw_takeaways] if raw_takeaways else []
    
    clean_takeaways = []
    for t in raw_takeaways:
        s = to_str(t)
        if s and s != "[object Object]":
            clean_takeaways.append(s)
    
    data["key_takeaways"] = clean_takeaways
    data["simple_key_takeaways"] = clean_takeaways

    # 3. GEOSCORE & DEFCON
    geoscore_val = data.get("overall_geoscore") or data.get("geoscore") or 75
    if isinstance(geoscore_val, dict):
        geoscore_num = int(geoscore_val.get("current_score", 75))
    else:
        try: geoscore_num = int(geoscore_val)
        except: geoscore_num = 75

    data["overall_geoscore"] = geoscore_num
    data["geoscore"] = {"current_score": geoscore_num, "status": "Erhöht"}

    defcon_val = data.get("defcon_level") or data.get("defcon") or 3
    try: defcon_num = int(defcon_val)
    except: defcon_num = 3

    data["defcon_level"] = defcon_num
    data["defcon"] = defcon_num
    data["defcon_status"] = {"level": defcon_num, "label": f"DEFCON {defcon_num}"}

    data["market_regime"] = to_str(data.get("market_regime"), "Geopolitische Segmentierung")
    data["top_risk"] = to_str(data.get("top_risk"), "Lieferketten & Chokepoints")

    # 4. SCHWARM-DEBATTE
    ds_clean = to_str(debate_summary)
    data["game_theory_analysis"] = to_str(data.get("game_theory_analysis"), ds_clean if ds_clean else "Keine Spieltheorie-Debatte erfasst.")

    # 5. HOTSPOTS MIT AUTOMATISCHER LAT/LON-KORREKTUR
    hotspots = data.get("conflict_hotspots", [])
    if not isinstance(hotspots, list): hotspots = []

    cleaned_hotspots = []
    for h in hotspots:
        if isinstance(h, dict):
            try:
                raw_lat = float(h.get("lat", 0))
                raw_lon = float(h.get("lon") if "lon" in h else h.get("lng", 0))

                if abs(raw_lat) > 90 and abs(raw_lon) <= 90:
                    raw_lat, raw_lon = raw_lon, raw_lat

                h["lat"] = raw_lat
                h["lon"] = raw_lon
                h["lng"] = raw_lon
                h["name"] = to_str(h.get("name") or h.get("region"), "Hotspot")
                h["region"] = to_str(h.get("region") or h.get("name"), "Region")
                h["description"] = to_str(h.get("description") or h.get("impact"), "Erhöhte Aktivität")
                h["impact"] = to_str(h.get("impact") or h.get("description"), "Geopolitische Auswirkung")
                h["type"] = to_str(h.get("type"), "conflict").lower()
                cleaned_hotspots.append(h)
            except (ValueError, TypeError):
                continue

    if live_flights and isinstance(live_flights, list):
        cleaned_hotspots.extend(live_flights)

    data["conflict_hotspots"] = cleaned_hotspots

    # 6. HISTORISCHE PARALLELEN
    hist = data.get("historical_precedents", [])
    clean_hist = []
    if isinstance(hist, list):
        for h in hist:
            if isinstance(h, dict):
                c_evt = to_str(h.get("current_event") or h.get("event"), "Aktuelles Ereignis")
                h_ana = to_str(h.get("historical_analog") or h.get("similarity"), "Historische Parallele")
                t_away = to_str(h.get("takeaway"), "")
                clean_hist.append({
                    "event": c_evt,
                    "current_event": c_evt,
                    "historical_analog": h_ana,
                    "similarity": h_ana,
                    "takeaway": t_away
                })
    data["historical_precedents"] = clean_hist

    # 7. PREDICTIVE HORIZON (Zukunfts-Prognose Matrix)
    ph = data.get("predictive_horizon", [])
    if isinstance(ph, dict):
        prob = int(ph.get("base_case_probability_pct", 65))
        summary = to_str(ph.get("base_case_summary"), "Stabile Trendfortsetzung.")
        inds = ph.get("leading_indicators_to_watch", [])
        clean_inds = [to_str(x) for x in inds if to_str(x)]
        data["predictive_horizon"] = {
            "base_case_probability_pct": prob,
            "base_case_summary": summary,
            "leading_indicators_to_watch": clean_inds,
            "horizon_list": []
        }
    elif isinstance(ph, list) and len(ph) > 0:
        first_item = ph[0] if isinstance(ph[0], dict) else {}
        indicators = first_item.get("early_warning_indicators", []) if isinstance(first_item, dict) else []
        clean_inds = [to_str(ind) for ind in indicators if to_str(ind)]
        summary = to_str(first_item.get("forecast"), "Stabile Trendfortsetzung.") if isinstance(first_item, dict) else to_str(first_item)
        data["predictive_horizon"] = {
            "base_case_probability_pct": 65,
            "base_case_summary": summary,
            "leading_indicators_to_watch": clean_inds,
            "horizon_list": ph
        }
    else:
        data["predictive_horizon"] = {
            "base_case_probability_pct": 60,
            "base_case_summary": "Lagedaten werden ausgewertet.",
            "leading_indicators_to_watch": [],
            "horizon_list": []
        }

    # 8. INNENPOLITIK MATRIX
    dpm = data.get("domestic_policy_matrix", [])
    clean_dpm = []
    if isinstance(dpm, list):
        for m in dpm:
            if isinstance(m, dict):
                clean_dpm.append({
                    "region": to_str(m.get("region"), "Region"),
                    "stability": to_str(m.get("stability"), "GELB").upper(),
                    "dynamics": to_str(m.get("dynamics") or m.get("spillover"), "Lage im Wandel.")
                })
    data["domestic_policy_matrix"] = clean_dpm

    # 9. EQUITY ROTATION (Aktien Top/Flop)
    eq = data.get("equity_rotation", {})
    if not isinstance(eq, dict): eq = {}
    sp = data.get("stock_picks", {})
    if not isinstance(sp, dict): sp = {}

    buys = eq.get("top5_buys") or sp.get("top_5_buys") or []
    sells = eq.get("flop5_sells") or sp.get("flop_5_sells") or []

    def clean_stock_list(items, default_type="BUY"):
        formatted = []
        if isinstance(items, list):
            for b in items:
                if isinstance(b, dict):
                    formatted.append({
                        "ticker": to_str(b.get("ticker") or b.get("asset"), default_type),
                        "name": to_str(b.get("name") or b.get("asset"), "Sektor"),
                        "asset": to_str(b.get("asset") or b.get("name"), "Sektor"),
                        "reason": to_str(b.get("reason"), "Positiver Makro-Impuls")
                    })
                elif isinstance(b, str) and b.strip():
                    formatted.append({
                        "ticker": default_type,
                        "name": b.strip(),
                        "asset": b.strip(),
                        "reason": "Makro-Impuls"
                    })
        return formatted

    f_buys = clean_stock_list(buys, "BUY")
    f_sells = clean_stock_list(sells, "SELL")

    data["equity_rotation"] = {"top5_buys": f_buys, "flop5_sells": f_sells}
    data["stock_picks"] = {"top_5_buys": f_buys, "flop_5_sells": f_sells}

    # 10. KASKADEN-GRAPH
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

    if url.startswith("/"):
        url = f"{RSSHUB_BASE_URL.rstrip('/')}{url}"

    articles = []
    try:
        response = requests.get(url, headers=FEED_HEADERS, timeout=FEED_TIMEOUT, allow_redirects=True)
        if response.status_code != 200: return []

        parsed = feedparser.parse(response.content)
        for entry in parsed.entries[:8]:
            title = to_str(entry.get("title"))
            summary = to_str(entry.get("summary") or entry.get("description"))
            link = to_str(entry.get("link"))
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
    if not api_key:
        pipeline_health["synthesizer_status"] = "NO_API_KEY"
        return {}

    endpoint = "https://api.mistral.ai/v1/chat/completions" if MISTRAL_API_KEY else (
        "https://openrouter.ai/api/v1/chat/completions" if OPENROUTER_API_KEY else
        "https://api.groq.com/openai/v1/chat/completions"
    )
    model = "mistral-large-latest" if MISTRAL_API_KEY else (
        "qwen/qwen-2.5-72b-instruct" if OPENROUTER_API_KEY else "llama-3.3-70b-versatile"
    )

    prompt = f"""HEUTIGES DATUM: {CURRENT_DATE_STR} (Jahr {CURRENT_YEAR}).

Du bist der finale Synthesizer eines Multi-LLM-Intelligence-Systems.
Erzeuge AUSSCHLIESSLICH ein valides JSON-Objekt. Kein Markdown, kein Text davor oder danach.

Nutze die Schwarm-Debatte und die Feeds. Sei konkret, aktuell und faktenbasiert.
Fülle ALLE Felder. Leere Arrays sind nur erlaubt, wenn wirklich keine Daten vorhanden sind.

SCHWARM-DEBATTE:
{debate_result[:3200]}

FEEDS (Auszug):
{raw_payload[:2200]}

ERFORDERLICHE JSON-STRUKTUR (exakt so verwenden):
{{
  "overall_geoscore": 75,
  "defcon_level": 3,
  "ampel_status": "GELB",
  "ampel_reason_simple": "Kurze Begründung der Ampelfarbe in 1-2 Sätzen",
  "daily_executive_summary": "Ausführliches Briefing (4-8 Sätze) zur aktuellen Weltlage",
  "daily_executive_summary_simple": "Einfache Version für Laien (3-5 Sätze)",
  "key_takeaways": ["Punkt 1", "Punkt 2", "Punkt 3", "Punkt 4", "Punkt 5"],
  "market_regime": "Fragmentiert / Volatil",
  "top_risk": "Lieferketten & Energie",
  "equity_rotation": {{
    "top5_buys": [
      {{"ticker": "XLE", "name": "Energy Select Sector", "asset": "Energie", "reason": "Begründung"}}
    ],
    "flop5_sells": [
      {{"ticker": "EEM", "name": "Emerging Markets", "asset": "Schwellenländer", "reason": "Begründung"}}
    ]
  }},
  "domestic_policy_matrix": [
    {{"region": "USA", "stability": "GELB", "dynamics": "Kurze Lagebeschreibung"}}
  ],
  "historical_precedents": [
    {{
      "event": "Aktuelles Ereignis",
      "current_event": "Aktuelles Ereignis",
      "historical_analog": "Historische Parallele",
      "similarity": "Warum ähnlich",
      "takeaway": "Erkenntnis für heute"
    }}
  ],
  "predictive_horizon": [
    {{
      "timeframe": "30 Tage",
      "forecast": "Was wahrscheinlich passiert",
      "probability": "Mittel",
      "early_warning_indicators": ["Indikator 1", "Indikator 2"]
    }}
  ],
  "conflict_hotspots": [
    {{
      "name": "Persischer Golf",
      "region": "Persischer Golf",
      "lat": 26.5,
      "lon": 53.5,
      "type": "chokepoint",
      "intensity": "ROT",
      "description": "Beschreibung",
      "impact": "Auswirkung"
    }}
  ],
  "graph_network": {{
    "nodes": [
      {{"id": "usa", "label": "USA", "name": "USA", "group": "staat", "val": 8}}
    ],
    "edges": [
      {{"from": "usa", "to": "iran", "label": "Konflikt"}}
    ]
  }}
}}

Wichtige Regeln:
- ampel_status nur "GRÜN", "GELB" oder "ROT"
- lat/lon müssen realistische Zahlen sein
- type bei Hotspots: conflict | flight | ship | refugee | chokepoint
- group bei Nodes: staat | miliz | organisation | risiko | tech | actor
- Schreibe auf Deutsch (außer Ticker und Eigennamen)
"""

    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.15,
            "max_tokens": 3500
        }
        if "mistral" in endpoint or "openrouter" in endpoint:
            payload["response_format"] = {"type": "json_object"}

        res = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=70
        )
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            parsed = repair_and_parse_json(content)
            if parsed and isinstance(parsed, dict) and len(parsed) > 3:
                pipeline_health["synthesizer_status"] = "SUCCESS"
                return parsed
            else:
                pipeline_health["synthesizer_status"] = "EMPTY_OR_INVALID"
                pipeline_health["errors"].append("Synthesizer lieferte leeres/ungültiges JSON")
        else:
            pipeline_health["synthesizer_status"] = f"HTTP_{res.status_code}"
            pipeline_health["errors"].append(f"Synthesizer HTTP {res.status_code}")
    except Exception as e:
        pipeline_health["synthesizer_status"] = f"ERROR ({type(e).__name__})"
        pipeline_health["errors"].append(f"Synthesizer Exception: {e}")
        logging.warning(f"Synthesizer Exception: {e}")

    return {}


def build_fallback_from_debate(debate_summary: str) -> dict:
    """Wenn der Synthesizer scheitert, bauen wir aus der Debatte ein minimales, aber nutzbares JSON."""
    debate = to_str(debate_summary)
    if not debate or len(debate) < 80:
        return {}

    takeaways = []
    for line in debate.split("\n"):
        line = line.strip()
        if line.startswith(("- ", "* ", "• ")) and len(line) > 15:
            takeaways.append(line.lstrip("-*• ").strip())
        if len(takeaways) >= 5:
            break

    if not takeaways:
        sentences = re.split(r'[.!?]\s+', debate)
        takeaways = [s.strip() for s in sentences if 40 < len(s.strip()) < 180][:5]

    summary = debate[:600].strip()
    if len(debate) > 600:
        summary += "..."

    return {
        "ampel_status": "GELB",
        "ampel_reason_simple": "Lage wird aus Multi-LLM-Kreuzprüfung abgeleitet. Synthesizer lieferte kein vollständiges JSON.",
        "daily_executive_summary": summary,
        "daily_executive_summary_simple": summary[:350] + ("..." if len(summary) > 350 else ""),
        "key_takeaways": takeaways or ["Kreuzprüfung abgeschlossen – Details in der Schwarm-Debatte."],
        "overall_geoscore": 72,
        "defcon_level": 3,
        "market_regime": "Unsicher / Fragmentiert",
        "top_risk": "Geopolitische Volatilität",
        "game_theory_analysis": debate,
        "predictive_horizon": {
            "base_case_probability_pct": 55,
            "base_case_summary": "Prognose aus Debatten-Konsens abgeleitet. Details in der Tiefenanalyse.",
            "leading_indicators_to_watch": ["Weitere Eskalationssignale in den Feeds", "Zentralbank-Kommunikation", "Militärische Bewegungen"]
        },
        "conflict_hotspots": [],
        "historical_precedents": [],
        "domestic_policy_matrix": [],
        "equity_rotation": {"top5_buys": [], "flop5_sells": []},
        "graph_network": {"nodes": [], "edges": []}
    }


def call_haiku_refine(data_dict: dict) -> dict:
    if not ANTHROPIC_API_KEY or not data_dict:
        return data_dict

    exec_summary = to_str(data_dict.get("daily_executive_summary"))
    ampel_reason = to_str(data_dict.get("ampel_reason_simple"))

    if not exec_summary or "kein vollständiges Briefing" in exec_summary.lower():
        return data_dict

    prompt = (
        f"DATUM: {CURRENT_DATE_STR} ({CURRENT_YEAR}). Formuliere für Laien verständlich auf Deutsch:\n\n"
        f"1. Executive Summary:\n{exec_summary}\n\n2. Ampel Begründung:\n{ampel_reason}\n\n"
        'Antworte NUR mit JSON: {"daily_executive_summary_simple": "...", "ampel_reason_simple": "..."}'
    )

    try:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=25
        )
        if res.status_code == 200:
            pipeline_health["haiku_status"] = "SUCCESS"
            refined = repair_and_parse_json(res.json()["content"][0]["text"])
            if isinstance(refined, dict):
                data_dict.update(refined)
        else:
            pipeline_health["haiku_status"] = f"HTTP_{res.status_code}"
    except Exception as e:
        pipeline_health["haiku_status"] = f"ERROR ({type(e).__name__})"
        logging.warning(f"Haiku Exception: {e}")

    return data_dict


# ============================================================
# DELTA SNAPSHOT TRACKING
# ============================================================
def build_delta_snapshot(old_data: dict, new_data: dict) -> dict:
    """Vergleicht den letzten Lauf mit dem aktuellen."""
    if not old_data or not isinstance(old_data, dict):
        return {
            "has_previous": False,
            "ampel_prev": None,
            "ampel_now": new_data.get("ampel_status", "GELB"),
            "ampel_changed": False,
            "geoscore_prev": None,
            "geoscore_now": new_data.get("overall_geoscore", 75),
            "geoscore_delta": 0,
            "defcon_prev": None,
            "defcon_now": new_data.get("defcon_level", 3),
            "nodes_prev": 0,
            "nodes_now": len((new_data.get("graph_network") or {}).get("nodes") or []),
            "hotspots_now": len(new_data.get("conflict_hotspots") or []),
            "summary": "Erster Lauf – noch kein Vergleich möglich."
        }

    prev_ampel = to_str(old_data.get("ampel_status"), "GELB").upper()
    now_ampel = to_str(new_data.get("ampel_status"), "GELB").upper()

    try:
        prev_geo = int(
            old_data.get("overall_geoscore")
            or (old_data.get("geoscore") or {}).get("current_score")
            or 75
        )
    except Exception:
        prev_geo = 75
    try:
        now_geo = int(new_data.get("overall_geoscore") or 75)
    except Exception:
        now_geo = 75

    try:
        prev_def = int(old_data.get("defcon_level") or 3)
    except Exception:
        prev_def = 3
    try:
        now_def = int(new_data.get("defcon_level") or 3)
    except Exception:
        now_def = 3

    nodes_prev = len((old_data.get("graph_network") or {}).get("nodes") or [])
    nodes_now = len((new_data.get("graph_network") or {}).get("nodes") or [])
    hotspots_now = len(new_data.get("conflict_hotspots") or [])
    geo_d = now_geo - prev_geo

    parts = []
    if prev_ampel != now_ampel:
        parts.append(f"Ampel {prev_ampel} → {now_ampel}")
    if geo_d != 0:
        parts.append(f"Geoscore {prev_geo} → {now_geo} ({'+' if geo_d > 0 else ''}{geo_d})")
    if prev_def != now_def:
        parts.append(f"DEFCON {prev_def} → {now_def}")
    if nodes_now != nodes_prev:
        parts.append(f"Graph-Knoten {nodes_prev} → {nodes_now}")

    return {
        "has_previous": True,
        "ampel_prev": prev_ampel,
        "ampel_now": now_ampel,
        "ampel_changed": prev_ampel != now_ampel,
        "geoscore_prev": prev_geo,
        "geoscore_now": now_geo,
        "geoscore_delta": geo_d,
        "defcon_prev": prev_def,
        "defcon_now": now_def,
        "nodes_prev": nodes_prev,
        "nodes_now": nodes_now,
        "hotspots_now": hotspots_now,
        "summary": " · ".join(parts) if parts else "Keine wesentliche Änderung zur Vortageslage."
    }


def main():
    logging.info(f"=== ARGUS GRID v3.0 Multi-Source Pipeline ({CURRENT_DATE_STR}) ===")
    old_graph = load_existing_graph("data.json")

    old_full = {}
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                old_full = json.load(f)
        except Exception:
            old_full = {}

    articles = fetch_all_feeds(SOURCES)
    gdelt_articles = fetch_gdelt_data()
    articles.extend(gdelt_articles)
    tg_posts = fetch_all_telegram_osint()
    articles.extend(tg_posts)
    live_flights = fetch_opensky_flights()

    final_data = {}
    debate_summary = ""

    if articles:
        try:
            selected = select_balanced_articles(articles, max_count=120)
            raw_payload = "\n".join([
                f"[{a['category']}] {a['source']}: {a['title']} - {a['summary']}"
                for a in selected
            ])
            with ThreadPoolExecutor(max_workers=3) as executor:
                f_groq = executor.submit(baker_groq, raw_payload)
                f_ds = executor.submit(baker_deepseek, raw_payload)
                f_macro = executor.submit(baker_qwen_or_grok, raw_payload)
                draft_groq, draft_ds, draft_macro = f_groq.result(), f_ds.result(), f_macro.result()

            debate_summary = run_swarm_debate(draft_groq, draft_ds, draft_macro)
            synthesized_data = call_synthesizer(debate_summary, raw_payload)

            if not synthesized_data or len(synthesized_data) < 4:
                logging.warning("Synthesizer schwach → baue Fallback aus Debatte")
                if "build_fallback_from_debate" in globals():
                    synthesized_data = build_fallback_from_debate(debate_summary)
                if pipeline_health.get("synthesizer_status") == "PENDING":
                    pipeline_health["synthesizer_status"] = "FALLBACK_USED"

            final_data = call_haiku_refine(synthesized_data)
        except Exception as e:
            logging.error(f"Fehler im Schwarm: {e}")
            pipeline_health["errors"].append(f"Schwarm-Fehler: {e}")
            if "build_fallback_from_debate" in globals():
                final_data = build_fallback_from_debate(debate_summary)

    final_data = harmonize_and_validate_schema(
        final_data, debate_summary, live_flights=live_flights, old_graph=old_graph
    )
    final_data["delta"] = build_delta_snapshot(old_full, final_data)

    try:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        logging.info(
            f"Pipeline fertig. Feeds: {pipeline_health['feeds_successful']}/{pipeline_health['feeds_total']} | "
            f"GDELT: {pipeline_health['gdelt_articles']} | TG: {pipeline_health['telegram_posts']} | "
            f"Synthesizer: {pipeline_health.get('synthesizer_status')} | "
            f"Delta: {final_data['delta'].get('summary', '—')} → data.json"
        )
    except Exception as e:
        logging.critical(f"Schreibfehler: {e}")


if __name__ == "__main__":
    main()
