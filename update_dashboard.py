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

# 1. Systematisch strukturierter Quellenspiegel (BRICS, Primärquellen, West-Mainstream, Alternativ)
rss_urls = {
    # ==========================================
    # 🌍 1. BRICS & GLOBALER SÜDEN (Offiziell & Unabhängig)
    # ==========================================
    "Economic Times (Indien & BRICS)": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
    "CGTN World (China Staatl.)": "https://news.cgtn.com/rss/World.xml",
    "Xinhua World (China Staatl.)": "http://www.xinhuanet.com/english/rss/worldrss.xml",
    "TASS World (Russland Staatl.)": "https://tass.com/rss/v2.xml",
    "Al Jazeera (Global South & Nahost)": "https://www.aljazeera.com/xml/rss/all.xml",
    "The Cradle (Nahost Geopolitik)": "https://thecradle.co/feed",
    "Geopolitical Economy Report (BRICS-Fokus)": "https://geopoliticaleconomy.com/feed/",
    "South China Morning Post (SCMP Asien)": "https://www.scmp.com/rss/91/feed",
    "Asia Times (Indopazifik & BRICS)": "https://asiatimes.com/feed/",

    # ==========================================
    # 🏛️ 2. WESTLICHE PRIMÄRQUELLEN & DIPLOMATIE
    # ==========================================
    "White House (US-Präsident)": "https://www.whitehouse.gov/briefing-room/feed/",
    "US Department of State": "https://www.state.gov/rss-feed/press-releases/feed/",
    "Federal Reserve (US Fed)": "https://www.federalreserve.gov/feeds/press_all.xml",
    "EU-Kommission (Press Corner)": "https://ec.europa.eu/commission/presscorner/api/rss",
    "Europäischer Rat (Consilium)": "https://www.consilium.europa.eu/en/rss/",
    "World Economic Forum (WEF)": "https://www.weforum.org/agenda/feed/",
    "Schweizer Bundesrat (Admin.ch)": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.rss.html",
    "Münchner Sicherheitskonferenz (MSC)": "https://securityconference.org/news/rss/",

    # ==========================================
    # 📈 3. WESTLICHER MAINSTREAM & FINANZMEDIEN
    # ==========================================
    "CNBC (US Finance)": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Foreign Policy (US Geopolitik)": "https://foreignpolicy.com/feed/",
    "Nikkei Asia (Japan/Tech)": "https://asia.nikkei.com/rss/feed/nar",
    "Handelsblatt (DE Finanzen)": "https://www.handelsblatt.com/contentexport/feed/finanzen",
    "Finanzmarktwelt (FMW)": "https://finanzmarktwelt.de/feed/",
    "NZZ (International)": "https://www.nzz.ch/international.rss",
    "FAZ (Ausland)": "https://www.faz.net/rss/aktuell/politik/ausland/",
    "Tagesschau (Ausland)": "https://www.tagesschau.de/ausland/index.xml",
    "BBC World News": "http://feeds.bbci.co.uk/news/world/rss.xml",

    # ==========================================
    # 🔓 4. UNABHÄNGIGE & ALTERNATIVE ANALYSTEN
    # ==========================================
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

print("Hole tagesaktuelle News aus allen 4 Säulen (BRICS, Primärquellen, Mainstream, Alternativ)...")
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

# 3. Prompt für multipolare Synthese inkl. BRICS, Primärquellen & Asymmetrie
prompt = f"""
Du bist der Chef-Strategist und OSINT-Analyst des GeoPuls Frühwarn-Dashboards.

DEIN AUFTRAG:
Analysiere die folgenden Feeds aus allen vier Säulen:
1. BRICS & Globaler Süden (China, Indien, Russland, Nahost, Asia Times, Geopolitical Economy Report)
2. Westliche Primärquellen & Diplomatie (White House, EU, WEF, Fed, Schweizer Bundesrat, MSC)
3. Westlicher Mainstream & Finanzmedien
4. Unabhängige/Alternative Analysten

Synthetisiere die Gegensätze und denke UM DIE ECKE.
Identifiziere direkte Absichts-Erklärungen, schleichende Gesetzesinitiativen, BRICS-Dedollarisierung, asymmetrische Risiken und geostrategische Pulverfässer.

STRIKTER NEGATIV-FILTER (STRENG VERBOTENE INHALTE):
Generiere UNTER KEINEN UMSTÄNDEN generische Standard-Floskeln wie "Klimawandel", "allgemeine Cybersicherheit", "allgemeiner Währungskrieg" oder schwammige ESG-Themen.

FOKUS FÜR 'systemic_risks' (SCHAUE AUF OFFIZIELLE INITIATIVEN, BRICS-DYNAMIK & UNTERSCHÄTZTE ZÜNDSCHNÜRE):
Analysiere konkret:
1. Latente Geopolitische Pulverfässer & Diplomatie (z. B. Moldawien/Transnistrien, Suwalki-Lücke, Westbalkan, BRICS-Handelsnetze, Schweizer Neutralität, MSC-Strategiepapiere, Seekabel-Sicherheit).
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
      "topic": "Konkretes Risikofeld aus Regierungs-/BRICS-/Diplomatiequellen oder Geostrategie",
      "category": "Kategorie (z. B. Geostrategie, Digitalrechte, Finanzarchitektur, BRICS-Systeme)",
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
  "daily_executive_summary": "Tagesaktuelle, tiefgründige Synthese aus BRICS-, Primär- und Medienquellen.",
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
        {"role": "system", "content": "Du bist ein hochpräzises OSINT-Geopolitik- und Risikomodell. Du wertest BRICS-, Regierungs- und Medienquellen unvoreingenommen aus."},
        {"role": "user", "content": prompt}
    ],
    model="llama-3.3-70b-versatile",
    response_format={"type": "json_object"}
)

data = json.loads(chat_completion.choices[0].message.content)
data["timestamp"] = datetime.utcnow().strftime("%d.%m.%Y - %H:%M UTC")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("GeoPuls data.json erfolgreich gespeichert!")
