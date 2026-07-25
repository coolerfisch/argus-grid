#!/usr/bin/env python3
"""
ARGUS GRID v3.0 - Full Spectrum Multi-LLM Intelligence Engine Backend
Kollaboratives Multi-LLM-System ("Kuchenbacken-Architektur"):
- Parallele Sprints (Groq, DeepSeek, Qwen/Grok)
- Peer-Debatte & Fingerklopfen ("Kreuzprüfung")
- OpenSky Network Live-ADS-B-Tracking für Militär- & Aufklärungsflüge in Krisenzonen
- Dynamisches Kaskaden-Graphen-Merging (Akkumulation & 14-Tage-Decay historischer Beziehungen)
- Synthese für Sektor-Rotation (Top/Flop 5), Innenpolitik, Historische Parallelen & Tactical Radar.
- Erzeugt 100% abwärtskompatibles JSON für das klassische und neue Dashboard-Design (Jahr 2026).
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
    "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, */*",
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    "Cache-Control": "no-cache",
}

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

OPENSKY_USER = os.environ.get("OPENSKY_USER")
OPENSKY_PASSWORD = os.environ.get("OPENSKY_PASSWORD")

pipeline_health = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "feeds_total": 0,
    "feeds_successful": 0,
    "feeds_failed": 0,
    "bakers_active": [],
    "swarm_debate_status": "PENDING",
    "synthesizer_status": "PENDING",
    "haiku_status": "PENDING",
    "opensky_status": "PENDING",
    "graph_merge_status": "PENDING",
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


# ============================================================
# OPENSKY LIVE ADS-B TRACKER INTEGRATION
# ============================================================
def fetch_opensky_flights() -> list:
    """Lädt Live-Flugdaten aus strategischen Krisenzonen via OpenSky Network API."""
    if not OPENSKY_USER or not OPENSKY_PASSWORD:
        logging.info("[OPENSKY] Keine Zugangsdaten gesetzt. Überspringe Live-Flug-Tracking.")
        pipeline_health["opensky_status"] = "SKIPPED (No Credentials)"
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
            else:
                logging.warning(f"[OPENSKY] API HTTP {res.status_code} für {reg['name']}")
        except Exception as e:
            logging.warning(f"[OPENSKY] Fehler bei Abfrage von {reg['name']}: {e}")

    pipeline_health["opensky_status"] = f"SUCCESS ({total_found} Live-Signale)"
    logging.info(f"[OPENSKY] Ingestion beendet: {total_found} Live-Flugsignale erfasst.")
    return flight_hotspots


# ============================================================
# PERSISTENTES KASKADEN-GRAPHEN MERGING & DECAY
# ============================================================
def load_existing_graph(filepath="data.json") -> dict:
    """Lädt den bestehenden Graphen aus der letzten data.json."""
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
        logging.warning(f"[GRAPH Memory] Konnte bestehenden Graphen aus {filepath} nicht laden: {e}")
    return {"nodes": [], "edges": []}


def merge_and_decay_graph(new_graph: dict, old_graph: dict, max_age_days: int = 14) -> dict:
    """
    Akkumuliert alte und neue Graphenknoten/-kanten.
    - Knoten, die erneut auftauchen, wachsen im Wert (val) und werden visuell größer.
    - Knoten/Kanten, die > 14 Tage nicht mehr erwähnt wurden, verblassen und verschwinden.
    """
    now_dt = datetime.now(timezone.utc)
    today_str = now_dt.strftime("%Y-%m-%d")

    # 1. NODES MERGEN
    node_dict = {}

    # Altbestand laden
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

    # Neue Nodes mergen
    for n in new_graph.get("nodes", []):
        if not isinstance(n, dict): continue
        raw_id = str(n.get("id") or n.get("name") or n.get("label", "")).strip()
        nid = raw_id.lower()
        if not nid: continue

        new_val = int(n.get("val", 5))
        new_group = n.get("group") or "actor"
        new_label = n.get("label") or n.get("name") or raw_id

        if nid in node_dict:
            # Existiert bereits: Gewicht steigern & Datum aktualisieren
            node_dict[nid]["val"] = min(22, node_dict[nid]["val"] + max(1, new_val // 2))
            node_dict[nid]["last_seen"] = today_str
            node_dict[nid]["seen_today"] = True
            if new_group and new_group != "actor":
                node_dict[nid]["group"] = new_group
        else:
            # Neu
            node_dict[nid] = {
                "id": nid,
                "label": new_label,
                "group": new_group,
                "val": max(5, new_val),
                "first_seen": today_str,
                "last_seen": today_str,
                "seen_today": True
            }

    # Alterung/Decay für inaktive Nodes
    final_nodes = []
    for nid, n in node_dict.items():
        if not n["seen_today"]:
            try:
                last_dt = datetime.strptime(n["last_seen"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                age_days = (now_dt - last_dt).days
            except Exception:
                age_days = 0

            if age_days > max_age_days:
                continue  # Zu alt -> fliegt raus
            else:
                n["val"] = max(3, n["val"] - 1)  # Schrumpft leicht

        del n["seen_today"]
        final_nodes.append(n)

    valid_node_ids = {n["id"] for n in final_nodes}

    # 2. EDGES MERGEN
    edge_dict = {}

    # Altbestand Edges
    for e in old_graph.get("edges", []):
        if not isinstance(e, dict): continue
        src = str(e.get("from") or e.get("source", "")).strip().lower()
        tgt = str(e.get("to") or e.get("target", "")).strip().lower()
        if not src or not tgt: continue

        edge_key = f"{src}-->{tgt}"
        edge_dict[edge_key] = {
            "from": src,
            "to": tgt,
            "source": src,
            "target": tgt,
            "label": e.get("label", ""),
            "last_seen": e.get("last_seen", today_str),
            "seen_today": False
        }

    # Neue Edges
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
            if lbl:
                edge_dict[edge_key]["label"] = lbl
        else:
            edge_dict[edge_key] = {
                "from": src,
                "to": tgt,
                "source": src,
                "target": tgt,
                "label": lbl,
                "last_seen": today_str,
                "seen_today": True
            }

    # Decay & Filter für Edges
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

    pipeline_health["graph_merge_status"] = f"SUCCESS ({len(final_nodes)} Nodes, {len(final_edges)} Edges)"
    logging.info(f"[GRAPH Memory] Merging beendet: {len(final_nodes)} aktive Knoten, {len(final_edges)} Kanten.")

    return {
        "nodes": final_nodes,
        "edges": final_edges,
        "links": final_edges
    }


def harmonize_and_validate_schema(data: dict, debate_summary: str, live_flights: list = None, old_graph: dict = None) -> dict:
    if not isinstance(data, dict):
        data = {}

    # 1. Grundlegende Ampel & Texte
    data["ampel_status"] = (data.get("ampel_status") or "GELB").upper()
    data["ampel_reason_simple"] = data.get("ampel_reason_simple") or "Erhöhte allgemeine Volatilität im geopolitischen Raum."
    data["daily_executive_summary"] = data.get("daily_executive_summary") or "Für diesen Durchlauf liegt kein vollständiges Briefing vor."
    data["daily_executive_summary_simple"] = data.get("daily_executive_summary_simple") or data["daily_executive_summary"]

    # 2. Key Takeaways Dual-Mapping
    takeaways = data.get("key_takeaways") or data.get("simple_key_takeaways") or []
    if not isinstance(takeaways, list):
        takeaways = []
    data["key_takeaways"] = takeaways
    data["simple_key_takeaways"] = takeaways

    # 3. Geoscore & DEFCON Dual-Mapping
    geoscore_val = data.get("overall_geoscore") or data.get("geoscore") or 75
    if isinstance(geoscore_val, dict):
        geoscore_num = geoscore_val.get("current_score", 75)
    else:
        try:
            geoscore_num = int(geoscore_val)
        except (ValueError, TypeError):
            geoscore_num = 75

    data["overall_geoscore"] = geoscore_num
    data["geoscore"] = {"current_score": geoscore_num, "status": "Erhöht"}

    defcon_val = data.get("defcon_level") or data.get("defcon") or 3
    if isinstance(defcon_val, dict):
        defcon_num = 3
        defcon_label = defcon_val.get("label", "DEFCON 3")
    else:
        try:
            defcon_num = int(defcon_val)
        except (ValueError, TypeError):
            defcon_num = 3
        defcon_label = f"DEFCON {defcon_num}"

    data["defcon_level"] = defcon_num
    data["defcon"] = defcon_num
    data["defcon_status"] = {"level": defcon_num, "label": defcon_label}

    data["market_regime"] = data.get("market_regime") or "Geopolitische Segmentierung"
    data["top_risk"] = data.get("top_risk") or "Lieferketten & Chokepoints"

    # 4. Schwarm-Debatte
    ds_clean = debate_summary.strip() if debate_summary else ""
    text_content = ds_clean if ds_clean else "Keine spezifische Spieltheorie-Debatte erfasst."
    data["game_theory_analysis"] = data.get("game_theory_analysis") or text_content

    # 5. Hotspots mit Typen-Sicherung + OpenSky Integration
    hotspots = data.get("conflict_hotspots", [])
    if not isinstance(hotspots, list):
        hotspots = []

    for h in hotspots:
        if isinstance(h, dict):
            if "lng" not in h and "lon" in h:
                h["lng"] = h["lon"]
            if "lon" not in h and "lng" in h:
                h["lon"] = h["lng"]
            if "region" not in h and "name" in h:
                h["region"] = h["name"]
            if "impact" not in h and "description" in h:
                h["impact"] = h["description"]
            if "type" not in h:
                h["type"] = "conflict"

    if live_flights and isinstance(live_flights, list):
        hotspots.extend(live_flights)

    data["conflict_hotspots"] = hotspots

    # 6. GRAPH-NETZWERK PERSISTENT MERGEN
    raw_gn = data.get("graph_network", {})
    if not isinstance(raw_gn, dict):
        raw_gn = {"nodes": [], "edges": []}

    data["graph_network"] = merge_and_decay_graph(raw_gn, old_graph or {"nodes": [], "edges": []})

    # 7. Historische Parallelen Dual-Mapping
    hist = data.get("historical_precedents", [])
    if isinstance(hist, list):
        for h in hist:
            if isinstance(h, dict):
                if "current_event" not in h and "event" in h:
                    h["current_event"] = h["event"]
                if "historical_analog" not in h and "similarity" in h:
                    h["historical_analog"] = f"{h.get('period', '')}: {h['similarity']}"
    else:
        data["historical_precedents"] = []

    # 8. Stock Picks / Equity Rotation Dual-Mapping
    eq = data.get("equity_rotation", {})
    stock_picks = data.get("stock_picks", {})
    
    buys = eq.get("top5_buys") or stock_picks.get("top_5_buys") or []
    sells = eq.get("flop5_sells") or stock_picks.get("flop_5_sells") or []

    formatted_buys = []
    for b in buys:
        if isinstance(b, dict):
            formatted_buys.append({
                "ticker": b.get("ticker") or b.get("asset") or "BUY",
                "name": b.get("name") or b.get("asset") or "Sektor",
                "asset": b.get("asset") or b.get("name") or "Sektor",
                "reason": b.get("reason") or "Positiver Makro-Impuls"
            })

    formatted_sells = []
    for s in sells:
        if isinstance(s, dict):
            formatted_sells.append({
                "ticker": s.get("ticker") or s.get("asset") or "SELL",
                "name": s.get("name") or s.get("asset") or "Sektor",
                "asset": s.get("asset") or s.get("name") or "Sektor",
                "reason": s.get("reason") or "Erhöhtes Georisiko"
            })

    data["equity_rotation"] = {"top5_buys": formatted_buys, "flop5_sells": formatted_sells}
    data["stock_picks"] = {"top_5_buys": formatted_buys, "flop_5_sells": formatted_sells}

    # 9. Predictive Horizon
    ph = data.get("predictive_horizon", [])
    if isinstance(ph, dict):
        pass
    elif isinstance(ph, list) and len(ph) > 0:
        first_item = ph[0]
        indicators = first_item.get("early_warning_indicators", [])
        ind_list = [{"indicator": ind} if isinstance(ind, str) else ind for ind in indicators]
        data["predictive_horizon"] = {
            "base_case_probability_pct": 65,
            "base_case_summary": first_item.get("forecast", "Stabile Trendfortsetzung."),
            "leading_indicators_to_watch": ind_list,
            "horizon_list": ph
        }
    else:
        data["predictive_horizon"] = {
            "base_case_probability_pct": 60,
            "base_case_summary": "Lagedaten werden ausgewertet.",
            "leading_indicators_to_watch": [],
            "horizon_list": []
        }

    for array_key in ["domestic_policy_matrix", "stress_test_scenarios"]:
        if array_key not in data or not isinstance(data[array_key], list):
            data[array_key] = []

    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    data["pipeline_health"] = pipeline_health

    return data


def fetch_single_feed(source: dict) -> list:
    url = source.get("url")
    name = source.get("name", "Unknown")
    category = source.get("cat", source.get("category", "General"))
    bias = source.get("bias", "NEUTRAL")
    weight = source.get("weight", 1.0)

    if not url or not isinstance(url, str):
        logging.warning(f"[FEED] {name}: keine gültige URL")
        return []

    url = url.strip().strip("[]()")
    articles = []

    try:
        response = requests.get(url, headers=FEED_HEADERS, timeout=FEED_TIMEOUT, allow_redirects=True)

        if response.status_code != 200:
            logging.debug(f"[FEED] {name}: HTTP {response.status_code}")
            return []

        content_type = response.headers.get("Content-Type", "").lower()
        if "html" in content_type and "xml" not in content_type and "rss" not in content_type:
            logging.debug(f"[FEED] {name}: scheint HTML statt Feed zu sein")
            return []

        parsed = feedparser.parse(response.content)

        if getattr(parsed, "bozo", False) and not parsed.entries:
            logging.debug(f"[FEED] {name}: Parse-Fehler ({getattr(parsed, 'bozo_exception', '')})")
            return []

        for entry in parsed.entries[:8]:
            title = (entry.get("title") or "").strip()
            summary = (entry.get("summary") or entry.get("description") or "").strip()
            link = (entry.get("link") or "").strip()
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

    except requests.exceptions.Timeout:
        logging.debug(f"[FEED] {name}: Timeout")
        return []
    except requests.exceptions.RequestException as e:
        logging.debug(f"[FEED] {name}: Request-Fehler ({type(e).__name__})")
        return []
    except Exception as e:
        logging.debug(f"[FEED] {name}: Unerwarteter Fehler ({e})")
        return []


def fetch_all_feeds(sources_list: list) -> list:
    pipeline_health["feeds_total"] = len(sources_list)
    all_articles = []
    successful_feeds = 0
    failed_feeds = 0
    failed_names = []

    logging.info(f"Starte Feed-Ingestion für {len(sources_list)} Quellen (Workers={MAX_FEED_WORKERS}, Timeout={FEED_TIMEOUT}s)...")

    with ThreadPoolExecutor(max_workers=MAX_FEED_WORKERS) as executor:
        future_to_source = {executor.submit(fetch_single_feed, src): src for src in sources_list}

        for future in as_completed(future_to_source):
            src = future_to_source[future]
            name = src.get("name", "Unknown")
            try:
                res = future.result()
                if res:
                    all_articles.extend(res)
                    successful_feeds += 1
                else:
                    failed_feeds += 1
                    failed_names.append(name)
            except Exception as e:
                failed_feeds += 1
                failed_names.append(name)
                logging.debug(f"[FEED] {name}: Future-Exception ({e})")

    pipeline_health["feeds_successful"] = successful_feeds
    pipeline_health["feeds_failed"] = failed_feeds

    logging.info(f"Ingestion beendet: {successful_feeds}/{len(sources_list)} Feeds erfolgreich → {len(all_articles)} Artikel")

    if failed_names:
        preview = ", ".join(failed_names[:20])
        more = f" (+{len(failed_names)-20} weitere)" if len(failed_names) > 20 else ""
        logging.info(f"Fehlgeschlagene Quellen (Auszug): {preview}{more}")

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
        '  "overall_geoscore": 75,\n'
        '  "defcon_level": 3,\n'
        '  "ampel_status": "GRÜN" | "GELB" | "ROT",\n'
        '  "ampel_reason_simple": "...",\n'
        '  "daily_executive_summary": "...",\n'
        '  "daily_executive_summary_simple": "...",\n'
        '  "key_takeaways": ["Punkt 1", "Punkt 2", "Punkt 3"],\n'
        '  "market_regime": "Fragmentiert / Volatil",\n'
        '  "top_risk": "Lieferketten & Energie",\n'
        '  "equity_rotation": {\n'
        '    "top5_buys": [{"ticker": "XLE", "name": "Energy ETF", "asset": "Energie", "reason": "..."}],\n'
        '    "flop5_sells": [{"ticker": "EEM", "name": "Emerging Markets", "asset": "Schwellenländer", "reason": "..."}]\n'
        '  },\n'
        '  "domestic_policy_matrix": [\n'
        '    {"region": "USA", "stability": "GELB", "dynamics": "...", "spillover": "..."}\n'
        '  ],\n'
        '  "historical_precedents": [\n'
        '    {"event": "Kalter Krieg", "current_event": "Sanktionspolitik 2026", "period": "20. Jh.", "similarity": "Blockbildung", "historical_analog": "Kubakrise 1962", "takeaway": "Deeskalation via Kanäle"}\n'
        '  ],\n'
        '  "predictive_horizon": [\n'
        '    {"timeframe": "30 Tage (Taktisch)", "forecast": "...", "probability": "Mittel", "early_warning_indicators": ["Cyberangriffe"]}\n'
        '  ],\n'
        '  "conflict_hotspots": [\n'
        '    {"name": "Taiwan-Straße", "region": "Taiwan-Straße", "lat": 24.0, "lon": 121.0, "type": "flight" | "ship" | "refugee" | "chokepoint" | "conflict", "intensity": "ROT", "description": "...", "impact": "..."}\n'
        '  ],\n'
        '  "graph_network": {\n'
        '    "nodes": [{"id": "usa", "label": "USA", "name": "USA", "group": "staat", "val": 8}],\n'
        '    "edges": [{"from": "usa", "to": "taiwan", "label": "Allianz"}]\n'
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
    
    # 0. Vorherigen Graphen laden (Graphen-Gedächtnis)
    old_graph = load_existing_graph("data.json")

    # 1. RSS & OSINT Feeds laden
    articles = fetch_all_feeds(SOURCES)

    # 2. OpenSky Live ADS-B Tracking ausführen
    live_flights = fetch_opensky_flights()

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

    # 3. Schema harmonisieren + Graphen-Memory mergen + OpenSky Flüge integrieren
    final_data = harmonize_and_validate_schema(
        final_data, 
        debate_summary, 
        live_flights=live_flights, 
        old_graph=old_graph
    )

    output_path = "data.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        logging.info(f"Pipeline erfolgreich. Speicherung in '{output_path}'.")
    except Exception as e:
        logging.critical(f"Schreibfehler: {e}")


if __name__ == "__main__":
    main()
