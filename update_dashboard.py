import os
import json
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import anthropic
import feedparser
import yfinance as yf

# ============================================================
# HELPER-FUNKTIONEN
# ============================================================
def clean_html(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return clean_text.strip()

def repair_and_parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace+1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = text
        if repaired.count('"') % 2 != 0:
            repaired += '"'
        open_brackets = repaired.count('[') - repaired.count(']')
        open_braces = repaired.count('{') - repaired.count('}')
        repaired += ']' * max(0, open_brackets)
        repaired += '}' * max(0, open_braces)
        return json.loads(repaired)

# ============================================================
# A. ECHTE LIVE-FINANZ-, MAKRO-, ENERGIE- & ROHSTOFFDATEN
# ============================================================
def get_live_market_data():
    market_summary = ""
    tickers = {
        "US Dollar Index (DXY)": "DX-Y.NYB",
        "EUR/USD": "EURUSD=X",
        "USD/JPY": "JPY=X",
        "US 10Y Anleihe": "^TNX",
        "VIX (Aktien-Volatilität)": "^VIX",
        "HYG (High Yield Spreads ETF)": "HYG",
        "Gold (USD/oz)": "GC=F",
        "Silber (USD/oz)": "SI=F",
        "Brent Öl (USD/bbl)": "BZ=F",
        "WTI Öl (USD/bbl)": "CL=F",
        "US Erdgas (USD/MMBtu)": "NG=F",
        "Kupfer (USD/lb)": "HG=F",
        "Weizen (USD/bu)": "ZW=F",
        "BDI (Baltic Dry Index ETF)": "BDRY",
        "S&P 500 Index": "^GSPC",
        "Bitcoin (USD)": "BTC-USD"
    }
    print("Hole echte Finanz-, Makro- & Rohstoffmarktdaten via yfinance...")
    try:
        for name, ticker in tickers.items():
            try:
                data = yf.Ticker(ticker).history(period="5d")
                if not data.empty and len(data) >= 2:
                    close_curr = data['Close'].iloc[-1]
                    close_prev = data['Close'].iloc[-2]
                    change_pct = ((close_curr - close_prev) / close_prev) * 100
                    market_summary += f"- {name}: {close_curr:.2f} ({change_pct:+.2f}% heute)\n"
            except Exception as e_tick:
                print(f"Hinweis: Ticker {ticker} fehlerhaft: {e_tick}")
    except Exception as e_all:
        print(f"yfinance Fehler: {e_all}")
        market_summary = "- Finanzdaten aktuell eingeschränkt verfügbar.\n"

    return market_summary if market_summary else "- Finanzdaten im Wartestand.\n"

live_market_context = get_live_market_data()

# ============================================================
# B. KNOWLEDGE GRAPH MEMORY (ENTITÄTEN & RELATIONEN)
# ============================================================
memory_file = "knowledge_graph.json"
knowledge_graph = {
    "entities": [],
    "relations": [],
    "causal_chains": [],
    "historical_precedents": [
        {
            "trigger": "China Exportbeschränkung Seltene Erden",
            "past_years": [2010, 2023, 2025],
            "impact": "Seltene Erden +45%, Bergbauaktien +12%, Japan-Industrie -7%",
            "affected_assets": ["MP", "LYC", "REMX"]
        },
        {
            "trigger": "Drohung Sperrung Straße von Hormus / Bab al-Mandab",
            "past_years": [2019, 2023, 2024],
            "impact": "Brent Öl +18%, Tanker-Frachtraten +40%, Gold +6%",
            "affected_assets": ["BZ=F", "CL=F", "FRO", "GC=F"]
        }
    ]
}

if os.path.exists(memory_file):
    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            loaded_kg = json.load(f)
            if isinstance(loaded_kg, dict) and "entities" in loaded_kg:
                knowledge_graph = loaded_kg
        print(f"Knowledge Graph geladen: {len(knowledge_graph.get('entities', []))} Entitäten, {len(knowledge_graph.get('relations', []))} Relationen.")
    except Exception as e:
        print(f"Fehler beim Laden des Knowledge Graphs: {e}")

kg_context_str = json.dumps(knowledge_graph, ensure_ascii=False, indent=2)
if len(kg_context_str) > 10000:
    kg_context_str = kg_context_str[:10000] + "\n... [Knowledge Graph Kontext gekürzt]"

# ============================================================
# C. VOLLSTÄNDIGER QUELLENPOOL (100+ FEEDS)
# ============================================================
SOURCES = [
    # Zentralbanken & Makro
    {"name": "Federal Reserve Press", "url": "[https://www.federalreserve.gov/feeds/press_all.xml](https://www.federalreserve.gov/feeds/press_all.xml)", "cat": "Zentralbank", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "EZB (Europäische Zentralbank)", "url": "[https://www.ecb.europa.eu/rss/press.html](https://www.ecb.europa.eu/rss/press.html)", "cat": "Zentralbank", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "BIS (Bank f. Intl. Zahlungsausgleich)", "url": "[https://www.bis.org/doclist/all.rss](https://www.bis.org/doclist/all.rss)", "cat": "Zentralbank", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "IMF News", "url": "[https://www.imf.org/en/News/rss](https://www.imf.org/en/News/rss)", "cat": "Intl. Org", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "EU-Kommission Press", "url": "[https://ec.europa.eu/commission/presscorner/api/rss](https://ec.europa.eu/commission/presscorner/api/rss)", "cat": "Regierung/EU", "weight": 1.00, "bias": "WESTERN"},
    {"name": "White House Briefing", "url": "[https://www.whitehouse.gov/briefing-room/feed/](https://www.whitehouse.gov/briefing-room/feed/)", "cat": "Regierung", "weight": 1.00, "bias": "WESTERN"},

    # Energie, Rohstoffe & Logistik
    {"name": "EIA Petroleum Status Report", "url": "[https://news.google.com/rss/search?q=when:7d+site:eia.gov+%22Weekly+Petroleum+Status+Report%22&hl=en-US&gl=US&ceid=US:en](https://news.google.com/rss/search?q=when:7d+site:eia.gov+%22Weekly+Petroleum+Status+Report%22&hl=en-US&gl=US&ceid=US:en)", "cat": "Energie / EIA", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "IEA Oil Market Reports", "url": "[https://news.google.com/rss/search?q=when:7d+site:iea.org+%22Oil+Market+Report%22&hl=en-US&gl=US&ceid=US:en](https://news.google.com/rss/search?q=when:7d+site:iea.org+%22Oil+Market+Report%22&hl=en-US&gl=US&ceid=US:en)", "cat": "Energie / IEA", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "OPEC Monthly Market Reports", "url": "[https://news.google.com/rss/search?q=when:7d+OPEC+%22Monthly+Oil+Market+Report%22&hl=en-US&gl=US&ceid=US:en](https://news.google.com/rss/search?q=when:7d+OPEC+%22Monthly+Oil+Market+Report%22&hl=en-US&gl=US&ceid=US:en)", "cat": "Energie / OPEC", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "Freightos Shipping Index", "url": "[https://news.google.com/rss/search?q=when:7d+%22Freightos%22+OR+%22container+freight+rate%22+OR+%22Baltic+Dry%22&hl=en-US&gl=US&ceid=US:en](https://news.google.com/rss/search?q=when:7d+%22Freightos%22+OR+%22container+freight+rate%22+OR+%22Baltic+Dry%22&hl=en-US&gl=US&ceid=US:en)", "cat": "Logistik / Container", "weight": 0.90, "bias": "MAINSTREAM"},
    {"name": "FAO Food Price Index", "url": "[https://news.google.com/rss/search?q=when:7d+site:fao.org+%22Food+Price+Index%22+OR+%22Crop+Prospects%22&hl=en-US&gl=US&ceid=US:en](https://news.google.com/rss/search?q=when:7d+site:fao.org+%22Food+Price+Index%22+OR+%22Crop+Prospects%22&hl=en-US&gl=US&ceid=US:en)", "cat": "Agrar / FAO", "weight": 0.95, "bias": "OFFIZIELL"},

    # Militär, OSINT & Cyber
    {"name": "NASA FIRMS Fire & Hazards", "url": "[https://earthobservatory.nasa.gov/feeder/natural_hazards.rss](https://earthobservatory.nasa.gov/feeder/natural_hazards.rss)", "cat": "OSINT / Satellit", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "ISW (Institute f. Study of War)", "url": "[https://www.understandingwar.org/rss.xml](https://www.understandingwar.org/rss.xml)", "cat": "OSINT / Militär", "weight": 0.85, "bias": "WESTERN"},
    {"name": "US Naval Institute News", "url": "[https://news.usni.org/feed](https://news.usni.org/feed)", "cat": "Marine / AIS OSINT", "weight": 0.85, "bias": "WESTERN"},
    {"name": "CISA Cyber Alerts (US)", "url": "[https://www.cisa.gov/cybersecurity-advisories/all.xml](https://www.cisa.gov/cybersecurity-advisories/all.xml)", "cat": "Cyber / Infrastruktur", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "UKMTO (UK Maritime Trade Ops)", "url": "[https://news.google.com/rss/search?q=when:24h+UKMTO+OR+%22Maritime+Trade+Operations%22&hl=en-US&gl=US&ceid=US:en](https://news.google.com/rss/search?q=when:24h+UKMTO+OR+%22Maritime+Trade+Operations%22&hl=en-US&gl=US&ceid=US:en)", "cat": "Schifffahrt OSINT", "weight": 0.95, "bias": "OFFIZIELL"},

    # Diplomatie & Agenturen
    {"name": "AP News World", "url": "[https://news.google.com/rss/search?q=when:24h+source:Associated+Press&hl=en-US&gl=US&ceid=US:en](https://news.google.com/rss/search?q=when:24h+source:Associated+Press&hl=en-US&gl=US&ceid=US:en)", "cat": "Agentur", "weight": 0.95, "bias": "MAINSTREAM"},
    {"name": "Reuters World", "url": "[https://news.google.com/rss/search?q=when:24h+source:Reuters&hl=en-US&gl=US&ceid=US:en](https://news.google.com/rss/search?q=when:24h+source:Reuters&hl=en-US&gl=US&ceid=US:en)", "cat": "Agentur", "weight": 0.95, "bias": "MAINSTREAM"},
    {"name": "Kremlin News", "url": "[http://en.kremlin.ru/rss/news](http://en.kremlin.ru/rss/news)", "cat": "Regierung", "weight": 1.00, "bias": "BRICS"},
    {"name": "Chinesisches Außenministerium", "url": "[https://www.fmprc.gov.cn/eng/zxmz/rss.xml](https://www.fmprc.gov.cn/eng/zxmz/rss.xml)", "cat": "Diplomatie", "weight": 1.00, "bias": "BRICS"},
    {"name": "Al Jazeera", "url": "[https://www.aljazeera.com/xml/rss/all.xml](https://www.aljazeera.com/xml/rss/all.xml)", "cat": "Medien", "weight": 0.85, "bias": "BRICS"},
    {"name": "ZeroHedge", "url": "[http://feeds.feedburner.com/zerohedge/feed](http://feeds.feedburner.com/zerohedge/feed)", "cat": "Alternativ / Makro", "weight": 0.55, "bias": "ALTERNATIVE"}
]

browser_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 ArgusGridOSINTBot/1.0"

def fetch_single_feed(src):
    feed_str = ""
    try:
        feed = feedparser.parse(src["url"], agent=browser_agent)
        if feed.entries:
            feed_str += f"\n--- QUELLE: {src['name']} | Kat: {src['cat']} | Bias: {src['bias']} ---\n"
            for entry in feed.entries[:2]:
                title = entry.get('title', '')
                raw_summary = entry.get('summary', '') or entry.get('description', '')
                summary = clean_html(raw_summary)
                feed_str += f"- {title}: {summary[:120]}...\n"
    except Exception:
        pass
    return feed_str

print("Hole und sortiere Feeds...")
feed_context = ""

with ThreadPoolExecutor(max_workers=25) as executor:
    futures = [executor.submit(fetch_single_feed, src) for src in SOURCES]
    for future in as_completed(futures):
        res_str = future.result()
        if res_str:
            feed_context += res_str

if len(feed_context) > 35000:
    feed_context = feed_context[:35000] + "\n... [Quellenkontext gekürzt]"

# Clean API key extraction (Entfernt Zeilenumbrüche/Leerzeichen)
anth_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
if not anth_key:
    raise ValueError("ANTHROPIC_API_KEY wurde nicht in den Umgebungsvariablen gefunden!")

client_anthropic = anthropic.Anthropic(api_key=anth_key)

# ============================================================
# D. PHASE 2: INTELLIGENCE ENGINE (SINGLE-PASS CLAUDE CALL)
# ============================================================
orchestrator_prompt = """Du bist die 'Argus Grid Intelligence Engine' (Chef-Analyst für Geopolitik, Makro, Rohstoffe & OSINT).

Führe anhand der Eingabedaten eine tiefgehende Synthese mit folgenden 5 Modulen durch:

1. EVENT FUSION: Bündele bis zu 30 Einzelmeldungen zu deduplizierten Groß-Ereignissen (z. B. 'EVENT #2026-0714-034') mit Titel, Quellenliste, Confidence (%) und betroffenen Märkten/Regionen.
2. KAUSALITÄTSGRAPH: Erstelle gerichtete Wirkungssketten für Hauptkrisen (Trigger -> Step 1 -> Step 2 -> Step 3 -> Beneficiaries / Detractors).
3. HISTORISCHER PATTERN-MATCHER: Gleiche neue Schocks (z.B. Seltene Erden, Hormus, GPS-Jamming) mit dem Knowledge Graph ab und zeige vergangene Jahre (z.B. 2010, 2023) sowie Marktreaktionen.
4. WIDERSPRUCHSERKENNUNG (NARRATIVE DIVERGENCE): Vergleiche offizielle Rhetorik (Fed, Diplomatie) mit harten Sensordaten (Öl, DXY, Baltic Dry, Satelliten).
5. FRÜHWARNSYSTEM (RISK SCORES): Berechne Risiko-Scores (0-100) für Cyber, Militär, Finanzen, Versorgung und Politik sowie den Gesamt-Argus-Index.

ANTWORTE AUSSCHLIESSLICH IM VALIDEN JSON-FORMAT BASIEREND AUF DIESEM SCHEMA:
{
  "argus_risk_index": {
    "total_score": 68,
    "cyber_score": 50,
    "military_score": 74,
    "financial_score": 58,
    "supply_score": 69,
    "political_score": 72
  },
  "narrative_divergence": [
    {
      "topic": "Fed Zinspfad vs. Rohstoff-Inflation",
      "official_communication": "Fed meldet: Inflation unter Kontrolle / Dovish.",
      "hard_market_data": "Kupfer ↑, Brent Öl ↑, Baltic Dry ↑, Freightos ↑.",
      "divergence_score": "HOCH (85/100)"
    }
  ],
  "pattern_recognition": [
    {
      "trigger_event": "China beschränkt Seltene Erden",
      "matched_past_years": [2010, 2023, 2025],
      "historical_consequences": "2010: Seltene Erden +45%, Japan-Industrie -7% | 2023: Kupfer +8%",
      "actionable_insight": "Long-Bias auf westliche Rare-Earth Förderer"
    }
  ],
  "event_fusion": [
    {
      "event_id": "EVT-2026-0714-034",
      "title": "Iran droht mit Sperrung der Straße von Hormus",
      "sources": ["Reuters", "AP", "UKMTO", "Al Jazeera", "USNI"],
      "confidence_pct": 93,
      "affected_regions": ["Naher Osten"],
      "affected_markets": ["Öl", "LNG", "Versicherungen", "Schifffahrt", "Gold"]
    }
  ],
  "causal_graph": [
    {
      "trigger": "Hormus blockiert / bedroht",
      "steps": ["Ölangebot sinkt", "Brent steigt", "Inflation steigt", "Fed bleibt restriktiv", "Nasdaq unter Druck", "Gold steigt"],
      "beneficiaries": ["Brent Öl", "Gold", "Tanker-Reeder"],
      "detractors": ["Nasdaq", "Airlines", "Chemie"]
    }
  ],
  "knowledge_graph_updates": {
    "new_entities": [{"id": "E1", "name": "Straße von Hormus", "type": "CHOKEPOINT"}],
    "new_relations": [{"subject": "Iran", "predicate": "THREATENS_CLOSURE_OF", "object": "Straße von Hormus", "severity": 90}]
  },
  "daily_executive_summary": "Kurze prägnante Synthese der aktuellen Gesamtlage (max 3 Sätze).",
  "market_regime": "Marktregime",
  "top_overweight": "Gewinner Assets",
  "top_risk": "Hauptrisiko",
  "defcon_status": {"level": 3, "label": "DEFCON 3", "nuclear_risk_percent": 18, "primary_driver": "Treiber"},
  "stock_picks": {
    "top_5_buys": [{"ticker": "MP", "name": "MP Materials", "sector": "Bergbau", "reason": "Kurze Begründung"}],
    "flop_5_sells": [{"ticker": "DAL", "name": "Delta Air Lines", "sector": "Luftfahrt", "reason": "Kurze Begründung"}]
  },
  "conflict_hotspots": [
    {"region": "R1", "actors": "A1", "escalation_level": "KRITISCH", "catalyst": "C1", "impact": "I1", "lat": 31.5, "lng": 34.75}
  ],
  "assets": [
    {"name": "Gold & Silber", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Steigend", "driver": "Geopolitik & DXY"}
  ]
}
"""

user_payload = f"""
--- HISTORISCHER KNOWLEDGE GRAPH ---
{kg_context_str}

--- LIVE FINANZ- & ROHSTOFFDATEN ---
{live_market_context}

--- AKTUELLE MULTI-DOMÄNEN FEEDS ---
{feed_context}
"""

CLAUDE_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307"
]

print("Generiere Argus Grid Phase 2 Intelligence Lageanalyse...")
raw_text = None

for model in CLAUDE_MODELS:
    try:
        print(f"Versuche Aufruf mit Modell {model}...")
        res = client_anthropic.messages.create(
            model=model,
            max_tokens=8192,
            system=orchestrator_prompt,
            messages=[{"role": "user", "content": user_payload}]
        )
        raw_text = res.content[0].text.strip()
        print(f"Erfolgreich generiert mit {model}!")
        break
    except Exception as e:
        print(f"Modell {model} fehlgeschlagen: {e}")

if not raw_text:
    raise RuntimeError("Fehler: Kein Anthropic-Modell konnte erfolgreich aufgerufen werden.")

data = repair_and_parse_json(raw_text)

# Normalisierung von Geodaten für Karte
GEO_LOOKUP = {
    "nah": (31.5, 34.75), "iran": (32.42, 53.68), "israel": (31.04, 34.85),
    "ukraine": (48.37, 31.16), "taiwan": (23.69, 120.96), "rot": (12.58, 43.33)
}

for h in data.get("conflict_hotspots", []):
    try:
        h["lat"] = float(h.get("lat"))
        h["lng"] = float(h.get("lng"))
    except (ValueError, TypeError):
        reg_lower = h.get("region", "").lower()
        found = False
        for key, coords in GEO_LOOKUP.items():
            if key in reg_lower:
                h["lat"], h["lng"] = coords
                found = True
                break
        if not found or h["lat"] == 0.0:
            h["lat"], h["lng"] = 25.0, 45.0

data["timestamp"] = datetime.utcnow().strftime("%d.%m.%Y - %H:%M UTC")

# KNOWLEDGE GRAPH DYNAMISCH ERWEITERN
kg_updates = data.get("knowledge_graph_updates", {})
if isinstance(kg_updates, dict):
    for new_ent in kg_updates.get("new_entities", []):
        if not any(e.get("name") == new_ent.get("name") for e in knowledge_graph["entities"]):
            knowledge_graph["entities"].append(new_ent)
    
    for new_rel in kg_updates.get("new_relations", []):
        knowledge_graph["relations"].append(new_rel)

knowledge_graph["relations"] = knowledge_graph["relations"][-500:]

with open(memory_file, "w", encoding="utf-8") as f:
    json.dump(knowledge_graph, f, ensure_ascii=False, indent=2)

# SPEICHERN FÜR FRONTEND
history_file = "history.json"
history_data = []
if os.path.exists(history_file):
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
    except Exception:
        history_data = []

today_str = datetime.utcnow().strftime("%d.%m")
total_score = data.get("argus_risk_index", {}).get("total_score") or 68

if not history_data or history_data[-1].get("date") != today_str:
    history_data.append({
        "date": today_str,
        "score": total_score,
        "defcon": data.get("defcon_status", {}).get("level", 3)
    })
    history_data = history_data[-30:]
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Argus Grid Intelligence Engine erfolgreich aktualisiert!")
