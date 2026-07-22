import os
import json
import re
from datetime import datetime
from groq import Groq
import feedparser

# HTML-Tags entfernen
def clean_html(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return clean_text.strip()

# 1. Erweiterter Quellenspiegel (Primärquellen + Schweiz + MSC + Medien)
rss_urls = {
    # --- PRIMÄRQUELLEN & REGIERUNGSSEITEN ---
    "White House (US-Präsident)": "https://www.whitehouse.gov/briefing-room/feed/",
    "US Department of State": "https://www.state.gov/rss-feed/press-releases/feed/",
    "Federal Reserve (US Fed)": "https://www.federalreserve.gov/feeds/press_all.xml",
    "EU-Kommission (Press Corner)": "https://ec.europa.eu/commission/presscorner/api/rss",
    "Europäischer Rat (Consilium)": "https://www.consilium.europa.eu/en/rss/",
    "World Economic Forum (WEF)": "https://www.weforum.org/agenda/feed/",
    "Kreml (Russland Offiziell)": "http://en.kremlin.ru/events/president/news/feed",
    "Xinhua World (China Offiziell)": "http://www.xinhuanet.com/english/rss/worldrss.xml",

    # --- SCHWEIZ, NEUTRALITÄT & STRATEGIE-DIPLOMATIE ---
    "Schweizer Bundesrat (Admin.ch)": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.rss.html",
    "Münchner Sicherheitskonferenz (MSC)": "https://securityconference.org/news/rss/",
    "Swissinfo (SWI Neutralität & Märkte)": "https://www.swissinfo.ch/ger/rss",

    # --- MAINSTREAM FINANZ- & GEOPOLITIKMEDIEN ---
    "CNBC (US Finance)": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Foreign Policy": "https://foreignpolicy.com/feed/",
    "Economic Times (Indien/BRICS)": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
    "Nikkei Asia": "https://asia.nikkei.com/rss/feed/nar",
    "Handelsblatt": "https://www.handelsblatt.com/contentexport/feed/finanzen",
    "Finanzmarktwelt (FMW)": "https://finanzmarktwelt.de/feed/",
    "NZZ (International)": "https://www.nzz.ch/international.rss",
    "FAZ (Ausland)": "https://www.faz.net/rss/aktuell/politik/ausland/",

    # --- UNABHÄNGIGE & ALTERNATIVE ANALYSTEN ---
    "ZeroHedge": "http://feeds.feedburner.com/zerohedge/feed",
    "UnHerd": "https://unherd.com/feed/",
    "The Cradle (Nahost)": "https://thecradle.co/feed",
    "Geopolitical Economy Report": "https://geopoliticaleconomy.com/feed/",
    "NachDenkSeiten": "https://www.nachdenkseiten.de/?feed=rss2",
    "Apolut": "https://apolut.net/feed/",
    "Anti-Spiegel": "https://anti-spiegel.ru/feed/",
    "Telepolis": "https://www.telepolis.de/index.rss",
    "Tichys Einblick": "https://www.tichyseinblick.de/feed/"
}

browser_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
feed_context = ""

print("Hole tagesaktuelle Primärdaten, Schweiz & Medien aus weltweiten Feeds...")
for source_name, url in rss_urls.items():
    try:
        feed = feedparser.parse(url, agent=browser_agent)
        feed_context += f"\n--- Aktuelle Publikationen von {source_name} ---\n"
        for entry in feed.entries[:2]:
            title = entry.get('title', '')
            raw_summary = entry.get('summary', '') or entry.get('description', '')
            summary = clean_html(raw_summary)
            feed_context += f"- Titel: {title}\n  Inhalt: {summary[:220]}...\n"
    except Exception as e:
        print(f"Fehler bei {source_name}: {e}")

# 2. Groq Client initialisieren
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY nicht in den Umgebungsvariablen gefunden!")

client = Groq(api_key=api_key)

# 3. Prompt für Primärquellen-, Diplomatie- & Asymmetrie-Synthese
prompt = f"""
Du bist der Chef-Strategist und OSINT-Analyst des GeoPuls Frühwarn-Dashboards.

DEIN AUFTRAG:
Analysiere die folgenden direkten PRIMÄRQUELLEN (US White House, EU-Kommission, WEF, Fed, Kreml, Schweizer Bundesrat, Münchner Sicherheitskonferenz/MSC) sowie weltweite Medienmeldungen. Denke UM DIE ECKE.
Identifiziere direkte Absichts-Erklärungen, schleichende Gesetzesinitiativen, bilaterale Spannungen, asymmetrische Risiken und geostrategische Pulverfässer.

STRIKTER NEGATIV-FILTER (STRENG VERBOTENE INHALTE):
Generiere UNTER KEINEN UMSTÄNDEN generische Standard-Floskeln wie "Klimawandel", "allgemeine Cybersicherheit", "allgemeiner Währungskrieg" oder schwammige ESG-Themen. 

FOKUS FÜR 'systemic_risks' (SCHAUE AUF OFFIZIELLE INITIATIVEN, DIPLOMATIE & UNTERSCHÄTZTE ZÜNDSCHNÜRE):
Analysiere konkret:
1. Latente Geopolitische Pulverfässer & Diplomatie (z. B. Moldawien/Transnistrien, Suwalki-Lücke, Westbalkan, Schweizer Neutralität/Bilaterale Verträge, MSC-Strategiepapiere, Seekabel-Sicherheit).
2. Schleichende System- & Kontroll-Schocks aus Primärquellen (z. B. offizielle Vorstöße der EU zu Verschlüsselungsverboten/Chatkontrolle, CBDC/Digitaler Euro Testphasen der EZB/Fed, Bargeldgrenzen, Finanz-Debanking).
3. Asymmetrische Wirtschafts- & Rohstoffhebel (z. B. Monopole bei Seltenen Erden, Schattenflotten, Zinsspanne im Schattenbankensektor, Derivate-Risiken).

Meldungen und Primärquellen:
{feed_context}

GIB DAS ERGEBNIS AUSSCHLIESSLICH ALS VALIDES JSON ZURÜCK.

Exaktes Schema:
{{
  "conflict_hotspots": [
    {{
      "region": "Region / Akute Krisenzone",
      "actors": "Beteiligte Mächte & Akteure",
      "escalation_level": "KRITISCH / HOCH / MITTEL",
      "catalyst": "Konkreter Auslöser oder Militäraktion der letzten Tage",
      "impact": "Märkte, Rohstoffe, Seewege oder Schifffahrt"
    }}
  ],
  "systemic_risks": [
    {{
      "topic": "Konkretes Risikofeld aus Regierungs-/Diplomatiequellen oder Geostrategie",
      "category": "Kategorie (z. B. Geostrategie, Digitalrechte, Finanzarchitektur, Bilaterale Verträge)",
      "risk_level": "HOCH / MITTEL-HOCH",
      "status": "Aktueller Stand / Offizielle Gesetzgebung / Diplomatische Verhandlung",
      "impact": "Konkrete asymmetrische Folgen und Domino-Effekte"
    }}
  ],
  "timestamp": "",
  "global_risk_score": 79,
  "market_regime": "Aktuelles Makro-Regime",
  "top_overweight": "Empfohlene defensive Sektoren",
  "top_risk": "Größtes Einzelrisiko für Märkte und Stabilität",
  "daily_executive_summary": "Tagesaktuelle, tiefgründige Synthese aus Primärquellen, Schweiz/MSC-Diplomatie und Medien.",
  "assets": [
    {{ "name": "Gold & Silber", "signal": "GREEN", "signal_text": "🟢 Sehr Attraktiv", "trend": "Stark Steigend", "driver": "Haupttreiber" }},
    {{ "name": "KI & Halbleiter", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Steigend", "driver": "Haupttreiber" }},
    {{ "name": "Uran & Energie", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Stark Steigend", "driver": "Haupttreiber" }},
    {{ "name": "S&P 500 / Nasdaq", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Volatil", "driver": "Haupttreiber" }},
    {{ "name": "Bitcoin & Krypto", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Volatil", "driver": "Haupttreiber" }},
    {{ "name": "High-Yield Bonds", "signal": "RED", "signal_text": "🔴 Unattraktiv", "trend": "Fallend", "driver": "Haupttreiber" }},
    {{ "name": "Gewerbeimmobilien", "signal": "RED", "signal_text": "🔴 Meiden", "trend": "Stark Fallend", "driver": "Haupttreiber" }}
  ],
  "regions": [
    {{ "name": "USA", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Einschätzung" }},
    {{ "name": "BRICS & Globaler Süden", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Einschätzung" }},
    {{ "name": "Japan & Indien / ASEAN", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Einschätzung" }},
    {{ "name": "Kern-Europa (DE/FR/CH)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Einschätzung" }},
    {{ "name": "China (Binnenmarkt)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Einschätzung" }}
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
chat_completion = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "Du bist ein hochpräzises OSINT-Geopolitik- und Risikomodell. Du wertest Regierungs-, Schweizer Neutralitäts- und MSC-Quellen unvoreingenommen aus."},
        {"role": "user", "content": prompt}
    ],
    model="llama-3.3-70b-versatile",
    response_format={"type": "json_object"}
)

data = json.loads(chat_completion.choices[0].message.content)
data["timestamp"] = datetime.utcnow().strftime("%d.%m.%Y - %H:%M UTC")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("GeoPuls data.json mit Schweiz-, MSC- und Primärquellen erfolgreich aktualisiert!")
