import os
import json
import re
from datetime import datetime
from groq import Groq, RateLimitError
import feedparser
import requests
import yfinance as yf

# HTML-Tags entfernen
def clean_html(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return clean_text.strip()

# A. ECHTE LIVE-MARKTDATEN HOLEN
def get_live_market_data():
    market_summary = ""
    tickers = {
        "Gold (USD/oz)": "GC=F",
        "Brent Öl (USD/bbl)": "BZ=F",
        "S&P 500 Index": "^GSPC",
        "Bitcoin (USD)": "BTC-USD",
        "US 10Y Anleiherendite": "^TNX",
        "VIX (Angstindex)": "^VIX"
    }
    print("Hole echte Finanzmarktdaten via yfinance...")
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

# B. ERWEITERTER QUELLENSPIEGEL
rss_urls = {
    # 🌍 1. BRICS & GLOBALER SÜDEN MEDIEN
    "Economic Times (Indien)": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
    "CGTN World (China Staatl.)": "https://news.cgtn.com/rss/World.xml",
    "Xinhua World (China)": "http://www.xinhuanet.com/english/rss/worldrss.xml",
    "TASS World (Russland)": "https://tass.com/rss/v2.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "The Cradle": "https://thecradle.co/feed",
    "Geopolitical Economy Report": "https://geopoliticaleconomy.com/feed/",
    "South China Morning Post": "https://www.scmp.com/rss/91/feed",
    "Asia Times": "https://asiatimes.com/feed/",

    # 🏛️ 2. PRIMÄRQUELLEN & DIPLOMATIE / INNENPOLITIK (WESTEN & BRICS)
    "White House Briefing": "https://www.whitehouse.gov/briefing-room/feed/",
    "US Department of State": "https://www.state.gov/rss-feed/press-releases/feed/",
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "EU-Kommission Press": "https://ec.europa.eu/commission/presscorner/api/rss",
    "Europäischer Rat": "https://www.consilium.europa.eu/en/rss/",
    "World Economic Forum": "https://www.weforum.org/agenda/feed/",
    "Schweizer Bundesrat": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.rss.html",
    "Münchner Sicherheitskonferenz": "https://securityconference.org/news/rss/",
    "Kremlin News (Russland)": "http://en.kremlin.ru/rss/news",
    "Kremlin Transkripte (Russland)": "http://en.kremlin.ru/rss/transcripts",
    "Russisches Außenministerium (MID)": "https://mid.ru/en/rss.php",
    "TV BRICS Official": "https://tvbrics.com/en/rss/",
    "BRICS Info Sharing Platform": "https://www.brics-info.org/feed/",
    "Chinesisches Außenministerium (MFA)": "https://www.fmprc.gov.cn/eng/zxmz/rss.xml",
    "Indisches Außenministerium (MEA)": "https://www.mea.gov.in/rss.xml",

    # 📈 3. MAINSTREAM FINANZEN & POLITIK
    "CNBC Finance": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Foreign Policy": "https://foreignpolicy.com/feed/",
    "Nikkei Asia": "https://asia.nikkei.com/rss/feed/nar",
    "Handelsblatt": "https://www.handelsblatt.com/contentexport/feed/finanzen",
    "Finanzmarktwelt": "https://finanzmarktwelt.de/feed/",
    "NZZ": "https://www.nzz.ch/international.rss",
    "FAZ": "https://www.faz.net/rss/aktuell/politik/ausland/",
    "Tagesschau": "https://www.tagesschau.de/ausland/index.xml",
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",

    # 🔓 4. UNABHÄNGIGE, INVESTIGATIVE & ALTERNATIVE ANALYSTEN
    "Multipolar Magazin": "https://multipolar-magazin.de/feed",
    "Manova / Rubikon": "https://www.manova.news/feed",
    "Berliner Tageszeitung": "https://www.berlinertageszeitung.de/rss.xml",
    "Hintergrund Magazin": "https://www.hintergrund.de/feed/",
    "Wissensteilchen Blog": "https://wissensteilchen.com/feed/",
    "Republik (Schweiz)": "https://www.republik.ch/feed",
    "Krautreporter": "https://krautreporter.de/feed.rss",
    "The Grayzone": "https://thegrayzone.com/feed/",
    "The Intercept": "https://theintercept.com/feed/?lang=en",
    "MintPress News": "https://www.mintpressnews.com/feed/",
    "Caitlin Johnstone": "https://caitlinjohnstone.com.au/feed/",
    "Moon of Alabama": "https://www.moonofalabama.org/atom.xml",
    "ZeroHedge": "http://feeds.feedburner.com/zerohedge/feed",
    "UnHerd": "https://unherd.com/feed/",
    "Antiwar.com": "https://news.antiwar.com/feed/",
    "NachDenkSeiten": "https://www.nachdenkseiten.de/?feed=rss2",
    "Apolut": "https://apolut.net/feed/",
    "Anti-Spiegel": "https://anti-spiegel.ru/feed/",
    "Telepolis": "https://www.telepolis.de/index.rss",
    "Tichys Einblick": "https://www.tichyseinblick.de/feed/",
    "Overton Magazin": "https://overton-magazin.de/feed/"
}

browser_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
feed_context = ""

print("Hole tagesaktuelle News aus Feeds...")
for source_name, url in rss_urls.items():
    try:
        feed = feedparser.parse(url, agent=browser_agent)
        feed_context += f"\n--- {source_name} ---\n"
        for entry in feed.entries[:2]:
            title = entry.get('title', '')
            raw_summary = entry.get('summary', '') or entry.get('description', '')
            summary = clean_html(raw_summary)
            # Auf 120 Zeichen kappen pro Beitrag
            feed_context += f"- {title}: {summary[:120]}...\n"
    except Exception as e:
        print(f"Fehler bei {source_name}: {e}")

# Kappe den Gesamtkontext der Feeds auf max. 10.000 Zeichen (Tokens sparen!)
if len(feed_context) > 10000:
    feed_context = feed_context[:10000] + "\n... [Feeds gekürzt um API-Limits einzuhalten]"

# C. GROQ CLIENT INITIALISIEREN
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY nicht in den Umgebungsvariablen gefunden!")

client = Groq(api_key=api_key)

# D. DYNAMISCHER PROMPT
prompt = f"""
Du bist der Chef-Strategist des GeoPuls Dashboards.

ECHTE LIVE-FINANZDATEN VOM HEUTIGEN TAG:
{live_market_context}

TAGESAKTUELLE MEDIEN- & REGIERUNGS-FEEDS:
{feed_context}

DEIN AUFTRAG:
Werte die obigen FEEDS und FINANZDATEN tagesaktuell aus. Antworte AUSSCHLIESSLICH in folgendem JSON-Format:

{{
  "daily_executive_summary": "Synthese der geopolitischen und makroökonomischen Lage heute...",
  "global_risk_score": 75,
  "market_regime": "Aktuelles Marktregime",
  "top_overweight": "Gewinner-Assetklassen",
  "top_risk": "Größtes Risiko heute",
  "defcon_status": {{
    "level": 3,
    "label": "DEFCON Statusbezeichnung",
    "nuclear_risk_percent": 15,
    "primary_driver": "Haupttreiber laut News"
  }},
  "narrative_divergence": [
    {{
      "topic": "Brennpunkt / Schauplatz 1",
      "mainstream_view": "Einschätzung westlicher Medien",
      "brics_view": "Einschätzung der BRICS-Staaten",
      "alternative_view": "Einschätzung unabhängiger Analysten"
    }},
    {{
      "topic": "Brennpunkt / Schauplatz 2",
      "mainstream_view": "Einschätzung westlicher Medien",
      "brics_view": "Einschätzung der BRICS-Staaten",
      "alternative_view": "Einschätzung unabhängiger Analysten"
    }},
    {{
      "topic": "Brennpunkt / Schauplatz 3",
      "mainstream_view": "Einschätzung westlicher Medien",
      "brics_view": "Einschätzung der BRICS-Staaten",
      "alternative_view": "Einschätzung unabhängiger Analysten"
    }}
  ],
  "domestic_politics": [
    {{
      "country_region": "Land / Region 1",
      "topic": "Innenpolitisches Thema",
      "status": "Aktueller Stand",
      "impact": "Geopolitische Folge"
    }},
    {{
      "country_region": "Land / Region 2",
      "topic": "Innenpolitisches Thema",
      "status": "Aktueller Stand",
      "impact": "Geopolitische Folge"
    }},
    {{
      "country_region": "Land / Region 3",
      "topic": "Innenpolitisches Thema",
      "status": "Aktueller Stand",
      "impact": "Geopolitische Folge"
    }}
  ],
  "stock_picks": {{
    "top_5_buys": [
      {{ "ticker": "TICKER1", "name": "Aktienname 1", "sector": "Sektor", "reason": "Begründung laut News" }},
      {{ "ticker": "TICKER2", "name": "Aktienname 2", "sector": "Sektor", "reason": "Begründung laut News" }},
      {{ "ticker": "TICKER3", "name": "Aktienname 3", "sector": "Sektor", "reason": "Begründung laut News" }},
      {{ "ticker": "TICKER4", "name": "Aktienname 4", "sector": "Sektor", "reason": "Begründung laut News" }},
      {{ "ticker": "TICKER5", "name": "Aktienname 5", "sector": "Sektor", "reason": "Begründung laut News" }}
    ],
    "flop_5_sells": [
      {{ "ticker": "TICKER6", "name": "Verlierer-Aktie 1", "sector": "Sektor", "reason": "Gegenwind laut News" }},
      {{ "ticker": "TICKER7", "name": "Verlierer-Aktie 2", "sector": "Sektor", "reason": "Gegenwind laut News" }},
      {{ "ticker": "TICKER8", "name": "Verlierer-Aktie 3", "sector": "Sektor", "reason": "Gegenwind laut News" }},
      {{ "ticker": "TICKER9", "name": "Verlierer-Aktie 4", "sector": "Sektor", "reason": "Gegenwind laut News" }},
      {{ "ticker": "TICKER10", "name": "Verlierer-Aktie 5", "sector": "Sektor", "reason": "Gegenwind laut News" }}
    ]
  }},
  "conflict_hotspots": [
    {{
      "region": "Krisenherd 1",
      "actors": "Akteure",
      "escalation_level": "KRITISCH",
      "catalyst": "Auslöser laut News",
      "impact": "Märkte",
      "lat": 0.0,
      "lng": 0.0
    }},
    {{
      "region": "Krisenherd 2",
      "actors": "Akteure",
      "escalation_level": "HOCH",
      "catalyst": "Auslöser laut News",
      "impact": "Märkte",
      "lat": 0.0,
      "lng": 0.0
    }},
    {{
      "region": "Krisenherd 3",
      "actors": "Akteure",
      "escalation_level": "HOCH",
      "catalyst": "Auslöser laut News",
      "impact": "Märkte",
      "lat": 0.0,
      "lng": 0.0
    }},
    {{
      "region": "Krisenherd 4",
      "actors": "Akteure",
      "escalation_level": "MITTEL-HOCH",
      "catalyst": "Auslöser laut News",
      "impact": "Märkte",
      "lat": 0.0,
      "lng": 0.0
    }}
  ],
  "systemic_risks": [
    {{
      "topic": "Systemisches Risiko 1",
      "category": "Kategorie",
      "risk_level": "HOCH",
      "status": "Status",
      "impact": "Folge"
    }},
    {{
      "topic": "Systemisches Risiko 2",
      "category": "Kategorie",
      "risk_level": "HOCH",
      "status": "Status",
      "impact": "Folge"
    }},
    {{
      "topic": "Systemisches Risiko 3",
      "category": "Kategorie",
      "risk_level": "MITTEL",
      "status": "Status",
      "impact": "Folge"
    }}
  ],
  "assets": [
    {{ "name": "Gold & Silber", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Trend", "driver": "Treiber" }},
    {{ "name": "KI & Halbleiter", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Trend", "driver": "Treiber" }},
    {{ "name": "Uran & Energie", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Trend", "driver": "Treiber" }},
    {{ "name": "S&P 500 / Nasdaq", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Trend", "driver": "Treiber" }},
    {{ "name": "Bitcoin & Krypto", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Trend", "driver": "Treiber" }},
    {{ "name": "High-Yield Bonds", "signal": "RED", "signal_text": "🔴 Unattraktiv", "trend": "Trend", "driver": "Treiber" }},
    {{ "name": "Gewerbeimmobilien", "signal": "RED", "signal_text": "🔴 Meiden", "trend": "Trend", "driver": "Treiber" }}
  ],
  "scenarios": [
    {{ "title": "Szenario 1", "prob": 40 }},
    {{ "title": "Szenario 2", "prob": 30 }},
    {{ "title": "Szenario 3", "prob": 15 }},
    {{ "title": "Szenario 4", "prob": 15 }}
  ]
}}
"""

print("Rufe Groq API auf...")

# E. GROQ API AUFRUF MIT FALLBACK BEI RATE-LIMIT
selected_model = "llama-3.3-70b-versatile"

try:
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Du bist ein hochpräzises OSINT-Geopolitikmodell. Analysiere die Feeds dynamisch und antworte rein in JSON."},
            {"role": "user", "content": prompt}
        ],
        model=selected_model,
        response_format={"type": "json_object"}
    )
except RateLimitError:
    print(f"Rate Limit für {selected_model} erreicht! Wechsle auf Fallback-Modell llama-3.1-8b-instant...")
    selected_model = "llama-3.1-8b-instant"
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Du bist ein hochpräzises OSINT-Geopolitikmodell. Analysiere die Feeds dynamisch und antworte rein in JSON."},
            {"role": "user", "content": prompt}
        ],
        model=selected_model,
        response_format={"type": "json_object"}
    )
except Exception as e:
    print(f"Allgemeiner Groq-Fehler mit {selected_model}: {e}. Versuche Fallback...")
    selected_model = "llama-3.1-8b-instant"
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Du bist ein hochpräzises OSINT-Geopolitikmodell. Analysiere die Feeds dynamisch und antworte rein in JSON."},
            {"role": "user", "content": prompt}
        ],
        model=selected_model,
        response_format={"type": "json_object"}
    )

data = json.loads(chat_completion.choices[0].message.content)

# --- NORMALISIERUNG ALLER FELDER ---

if not data.get("daily_executive_summary"):
    data["daily_executive_summary"] = data.get("executive_summary") or data.get("summary") or "Die geopolitische Lage bleibt durch multidimensionale Krisen im Nahen Osten, in Osteuropa und Ostasien angespannt."

raw_nd = data.get("narrative_divergence", [])
if isinstance(raw_nd, dict):
    raw_nd = [raw_nd]

normalized_nd = []
for item in raw_nd:
    if isinstance(item, dict):
        normalized_nd.append({
            "topic": item.get("topic") or "Geopolitischer Schauplatz",
            "mainstream_view": item.get("mainstream_view") or item.get("mainstream") or "Fokus auf westliche Ordnung und Bündnisse.",
            "brics_view": item.get("brics_view") or item.get("brics") or "Fokus auf multipolare Perspektive und Souveränität.",
            "alternative_view": item.get("alternative_view") or item.get("alternative") or "Fokus auf verdeckte Kaskadeneffekte."
        })

data["narrative_divergence"] = normalized_nd

GEO_LOOKUP = {
    "nah": (31.5, 34.75), "iran": (32.42, 53.68), "israel": (31.04, 34.85),
    "ukraine": (48.37, 31.16), "taiwan": (23.69, 120.96), "rot": (12.58, 43.33),
    "bab": (12.58, 43.33), "moldaw": (47.01, 28.86), "transnistrien": (46.84, 29.63),
    "balkan": (43.85, 18.35), "kaukasus": (41.71, 44.78), "suwalki": (54.1, 22.9),
    "china": (35.86, 104.19), "korea": (38.31, 127.23)
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

# Historie tracken
history_file = "history.json"
history_data = []
if os.path.exists(history_file):
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
    except Exception:
        history_data = []

today_str = datetime.utcnow().strftime("%d.%m")
if not history_data or history_data[-1].get("date") != today_str:
    history_data.append({
        "date": today_str,
        "score": data.get("global_risk_score", 75),
        "defcon": data.get("defcon_status", {}).get("level", 3)
    })
    history_data = history_data[-30:]
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"GeoPuls Dashboard erfolgreich mit Modell '{selected_model}' aktualisiert!")
