import os
import json
import re
from datetime import datetime
from groq import Groq
import feedparser
import requests
import yfinance as yf

# HTML-Tags entfernen
def clean_html(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return clean_text.strip()

# A. ECHTE LIVE-MARKTDATEN HOLEN (yfinance)
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
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period="2d")
            if len(data) >= 2:
                close_curr = data['Close'].iloc[-1]
                close_prev = data['Close'].iloc[-2]
                change_pct = ((close_curr - close_prev) / close_prev) * 100
                market_summary += f"- {name}: {close_curr:.2f} ({change_pct:+.2f}% heute)\n"
            elif len(data) == 1:
                market_summary += f"- {name}: {data['Close'].iloc[-1]:.2f}\n"
        except Exception as e:
            print(f"Fehler bei Ticker {ticker}: {e}")
    return market_summary

live_market_context = get_live_market_data()

# B. 35+ RSS-QUELLEN
rss_urls = {
    # 🌍 BRICS & GLOBALER SÜDEN
    "Economic Times (Indien)": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
    "CGTN World (China Staatl.)": "https://news.cgtn.com/rss/World.xml",
    "Xinhua World (China)": "http://www.xinhuanet.com/english/rss/worldrss.xml",
    "TASS World (Russland)": "https://tass.com/rss/v2.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "The Cradle": "https://thecradle.co/feed",
    "Geopolitical Economy Report": "https://geopoliticaleconomy.com/feed/",
    "South China Morning Post": "https://www.scmp.com/rss/91/feed",
    "Asia Times": "https://asiatimes.com/feed/",

    # 🏛️ PRIMÄRQUELLEN & DIPLOMATIE
    "White House": "https://www.whitehouse.gov/briefing-room/feed/",
    "US Department of State": "https://www.state.gov/rss-feed/press-releases/feed/",
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "EU-Kommission": "https://ec.europa.eu/commission/presscorner/api/rss",
    "Europäischer Rat": "https://www.consilium.europa.eu/en/rss/",
    "World Economic Forum": "https://www.weforum.org/agenda/feed/",
    "Schweizer Bundesrat": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.rss.html",
    "Münchner Sicherheitskonferenz": "https://securityconference.org/news/rss/",

    # 📈 MAINSTREAM FINANZEN
    "CNBC Finance": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Foreign Policy": "https://foreignpolicy.com/feed/",
    "Nikkei Asia": "https://asia.nikkei.com/rss/feed/nar",
    "Handelsblatt": "https://www.handelsblatt.com/contentexport/feed/finanzen",
    "Finanzmarktwelt": "https://finanzmarktwelt.de/feed/",
    "NZZ": "https://www.nzz.ch/international.rss",
    "FAZ": "https://www.faz.net/rss/aktuell/politik/ausland/",
    "Tagesschau": "https://www.tagesschau.de/ausland/index.xml",
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",

    # 🔓 UNABHÄNGIGE ANALYSTEN
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
            feed_context += f"- Titel: {title}\n  Inhalt: {summary[:200]}...\n"
    except Exception as e:
        print(f"Fehler bei {source_name}: {e}")

# C. GROQ CLIENT INITIALISIEREN
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY nicht in den Umgebungsvariablen gefunden!")

client = Groq(api_key=api_key)

# D. PROMPT FÜR KOMPLETTE SYNTHESE
prompt = f"""
Du bist der Chef-Strategist des GeoPuls Dashboards.

ECHTE TAGESAKTUELLE FINANZDATEN (BERÜCKSICHTIGE DIESE BEI DEN ASSETS):
{live_market_context}

FEEDS DER MEDIEN & PRIMÄRQUELLEN:
{feed_context}

DEIN AUFTRAG (NUR VALIDES JSON ZURÜCKGEBEN):
1. 'defcon_status': Bewerte das weltweite Atomkriegs-/Weltkriegsrisiko (Level 1-5, Label, nuclear_risk_percent, primary_driver).
2. 'narrative_divergence': Vergleiche das am stärksten unterschiedlich berichtete Thema des Tages zwischen Mainstream, BRICS und Alternativmedien.
3. 'conflict_hotspots': MINDESTENS 4 ECHTE BRANDHERDE mit exakten Koordinaten ("lat", "lng") für eine Weltkarte.
4. 'systemic_risks': 3 Pflicht-Risiken (Territorial/Geopolitisch wie Moldawien, Digitale/Monetäre Kontrolle, Strategischer Rohstoff/Infrastruktur-Hebel).

Exaktes Schema:
{{
  "defcon_status": {{
    "level": 3,
    "label": "DEFCON 3 - Erhöhte Alarmstufe",
    "nuclear_risk_percent": 15,
    "primary_driver": "Nukleardoktrin-Anpassungen & Militärmanöver der Supermächte"
  }},
  "narrative_divergence": {{
    "topic": "Das am stärksten gespaltene Thema des Tages",
    "mainstream_view": "Einschätzung westlicher Leitmedien",
    "brics_view": "Einschätzung von TASS, CGTN, Al Jazeera",
    "alternative_view": "Einschätzung unabhängiger Analysten"
  }},
  "conflict_hotspots": [
    {{
      "region": "Naher Osten / Iran & Israel",
      "actors": "USA / Israel vs. Iran / Achse",
      "escalation_level": "KRITISCH",
      "catalyst": "Militärische Schläge oder Angriffe auf Seewege",
      "impact": "Brent-Öl und Frachtrouten",
      "lat": 31.5,
      "lng": 34.75
    }},
    {{
      "region": "Ukraine / NATO-Ostflanke",
      "actors": "Russland vs. Ukraine / NATO",
      "escalation_level": "HOCH",
      "catalyst": "Frontverlauf und Rüstung",
      "impact": "Europäische Energiemärkte",
      "lat": 48.37,
      "lng": 31.16
    }},
    {{
      "region": "Taiwan-Straße & Indopazifik",
      "actors": "China vs. Taiwan / USA",
      "escalation_level": "MITTEL-HOCH",
      "catalyst": "Militärmanöver und Chip-Sanktionen",
      "impact": "Halbleiter-Lieferketten (TSMC)",
      "lat": 23.69,
      "lng": 120.96
    }},
    {{
      "region": "Rotes Meer / Bab al-Mandab",
      "actors": "Houthi vs. Marine-Allianz",
      "escalation_level": "HOCH",
      "catalyst": "Schiffsangriffe",
      "impact": "Frachtraten und Lieferketten",
      "lat": 12.58,
      "lng": 43.33
    }}
  ],
  "systemic_risks": [
    {{
      "topic": "Moldawien & Transnistrien",
      "category": "Geopolitische Region",
      "risk_level": "HOCH",
      "status": "Diplomatische Spannungen",
      "impact": "Gefahr einer zweiten Front im Schwarzmeerraum"
    }},
    {{
      "topic": "EU-Chatkontrolle & Verschlüsselung",
      "category": "Digitale Kontrolle",
      "risk_level": "HOCH",
      "status": "Gesetzgebungsprozess EU",
      "impact": "Risiken für Ende-zu-Ende-Verschlüsselung"
    }},
    {{
      "topic": "Seltene Erden Monopol",
      "category": "Strategischer Hebel",
      "risk_level": "MITTEL-HOCH",
      "status": "Exportkontrollen",
      "impact": "Versorgungsrisiken High-Tech"
    }}
  ],
  "timestamp": "",
  "global_risk_score": 79,
  "market_regime": "Multipolare Stagflation & Zins-Unsicherheit",
  "top_overweight": "Gold, Energie, Rohstoffe & Verteidigung",
  "top_risk": "Versorgungsschock / Geopolitische Blockbildung",
  "daily_executive_summary": "Ausführliche Synthese...",
  "assets": [
    {{ "name": "Gold & Silber", "signal": "GREEN", "signal_text": "🟢 Sehr Attraktiv", "trend": "Stark Steigend", "driver": "BRICS-Käufe & Sichere Häfen" }},
    {{ "name": "KI & Halbleiter", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Steigend", "driver": "Hardware-Boom" }},
    {{ "name": "Uran & Energie", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Stark Steigend", "driver": "Angebotsdefizit" }},
    {{ "name": "S&P 500 / Nasdaq", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Volatil", "driver": "Zinsaussichten" }},
    {{ "name": "Bitcoin & Krypto", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Volatil", "driver": "Liquiditätsumfeld" }},
    {{ "name": "High-Yield Bonds", "signal": "RED", "signal_text": "🔴 Unattraktiv", "trend": "Fallend", "driver": "Refinanzierungsdruck" }},
    {{ "name": "Gewerbeimmobilien", "signal": "RED", "signal_text": "🔴 Meiden", "trend": "Stark Fallend", "driver": "Zinsniveau" }}
  ],
  "regions": [
    {{ "name": "USA", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Einschätzung" }},
    {{ "name": "BRICS & Globaler Süden", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Einschätzung" }},
    {{ "name": "Japan & Indien / ASEAN", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Einschätzung" }},
    {{ "name": "Kern-Europa (DE/FR/CH)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Einschätzung" }},
    {{ "name": "China (Binnenmarkt)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Einschätzung" }}
  ],
  "scenarios": [
    {{ "title": "Ausweitung Nahost-Konflikt (Ölschock >100$)", "prob": 40 }},
    {{ "title": "Zweite Inflationswelle / Stagflation", "prob": 30 }},
    {{ "title": "Direkte NATO-Eskalation", "prob": 15 }},
    {{ "title": "BRICS-Dedollarisierung", "prob": 15 }}
  ]
}}
"""

print("Rufe Groq API auf...")
chat_completion = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "Du bist ein hochpräzises OSINT-Geopolitik- und Risikomodell, das strikt valides JSON generiert."},
        {"role": "user", "content": prompt}
    ],
    model="llama-3.3-70b-versatile",
    response_format={"type": "json_object"}
)

data = json.loads(chat_completion.choices[0].message.content)
data["timestamp"] = datetime.utcnow().strftime("%d.%m.%Y - %H:%M UTC")

# E. HISTORISCHEN RISIKO-TRACKER AKTUALISIEREN (history.json)
history_file = "history.json"
history_data = []
if os.path.exists(history_file):
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
    except Exception:
        history_data = []

today_str = datetime.utcnow().strftime("%d.%m")
# Nur einen Eintrag pro Tag
if not history_data or history_data[-1].get("date") != today_str:
    history_data.append({
        "date": today_str,
        "score": data.get("global_risk_score", 75),
        "defcon": data.get("defcon_status", {}).get("level", 3)
    })
    history_data = history_data[-30:] # Max. 30 Tage aufbewahren
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

# F. TELEGRAM PUSH-ALERT BEI HOHEM RISIKO (OPTIONAL)
tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
risk_score = data.get("global_risk_score", 0)
defcon_lvl = data.get("defcon_status", {}).get("level", 5)

if tg_token and tg_chat_id and (risk_score >= 80 or defcon_lvl <= 2):
    try:
        alert_msg = (
            f"🚨 *GeoPuls WARNMELDUNG* 🚨\n\n"
            f"⚠️ *Global Risk Score:* {risk_score} / 100\n"
            f"☢️ *DEFCON Status:* Level {defcon_lvl} ({data.get('defcon_status', {}).get('label')})\n\n"
            f"📌 *Hauptrisiko:* {data.get('top_risk')}\n"
            f"💡 *Treiber:* {data.get('defcon_status', {}).get('primary_driver')}\n\n"
            f"🌐 [GeoPuls Dashboard öffnen](https://coolerfisch.github.io/histamin/)"
        )
        requests.post(
            f"https://api.telegram.org/bot{tg_token}/sendMessage",
            data={"chat_id": tg_chat_id, "text": alert_msg, "parse_mode": "Markdown"}
        )
        print("Telegram Push-Alert erfolgreich gesendet!")
    except Exception as e:
        print(f"Fehler beim Senden des Telegram-Alerts: {e}")

# G. SPEICHERN DER DASHBOARD-DATEN
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("GeoPuls Dashboard mit allen Modulen erfolgreich aktualisiert!")
