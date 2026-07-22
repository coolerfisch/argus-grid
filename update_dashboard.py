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

# 1. Quellenspiegel (30 globale Medien: Mainstream + Unabhängig)
rss_urls = {
    # USA & Amerika
    "CNBC (US Finance)": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Foreign Policy": "https://foreignpolicy.com/feed/",
    "ZeroHedge": "http://feeds.feedburner.com/zerohedge/feed",
    "UnHerd": "https://unherd.com/feed/",
    "Antiwar.com": "https://news.antiwar.com/feed/",

    # BRICS, Nahost & Globaler Süden
    "Economic Times (Indien)": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
    "CGTN World (China)": "https://news.cgtn.com/rss/World.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "The Cradle": "https://thecradle.co/feed",
    "Geopolitical Economy Report": "https://geopoliticaleconomy.com/feed/",
    "TASS World": "https://tass.com/rss/v2.xml",

    # Asien & Indopazifik
    "Nikkei Asia": "https://asia.nikkei.com/rss/feed/nar",
    "SCMP": "https://www.scmp.com/rss/91/feed",
    "Asia Times": "https://asiatimes.com/feed/",

    # EU & DACH (Mainstream & Markt)
    "Handelsblatt": "https://www.handelsblatt.com/contentexport/feed/finanzen",
    "Finanzmarktwelt (FMW)": "https://finanzmarktwelt.de/feed/",
    "stock3": "https://stock3.com/news/feed/",
    "Manager Magazin": "https://www.manager-magazin.de/rss",
    "NZZ": "https://www.nzz.ch/international.rss",
    "FAZ": "https://www.faz.net/rss/aktuell/politik/ausland/",
    "Tagesschau": "https://www.tagesschau.de/ausland/index.xml",
    "BBC World News": "http://feeds.bbci.co.uk/news/world/rss.xml",

    # EU & DACH (Unabhängig & Alternativ)
    "NachDenkSeiten": "https://www.nachdenkseiten.de/?feed=rss2",
    "Apolut": "https://apolut.net/feed/",
    "Achgut": "https://www.achgut.com/rss",
    "Apollo News": "https://apollo-news.net/feed/",
    "Anti-Spiegel": "https://anti-spiegel.ru/feed/",
    "Telepolis": "https://www.telepolis.de/index.rss",
    "Tichys Einblick": "https://www.tichyseinblick.de/feed/",
    "Overton Magazin": "https://overton-magazin.de/feed/"
}

browser_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
feed_context = ""

print("Hole tagesaktuelle News aus 30 Quellen...")
for source_name, url in rss_urls.items():
    try:
        feed = feedparser.parse(url, agent=browser_agent)
        feed_context += f"\n--- Aktuelle Meldungen von {source_name} ---\n"
        for entry in feed.entries[:2]:
            title = entry.get('title', '')
            raw_summary = entry.get('summary', '') or entry.get('description', '')
            summary = clean_html(raw_summary)
            feed_context += f"- Titel: {title}\n  Zusammenfassung: {summary[:200]}...\n"
    except Exception as e:
        print(f"Fehler bei {source_name}: {e}")

# 2. Groq Client initialisieren
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY nicht in den Umgebungsvariablen gefunden!")

client = Groq(api_key=api_key)

# 3. Autonomer Prompt für Krisen-Erkennung
prompt = f"""
Du bist das autonome Frühwarn- und Analysesystem des GeoPuls Dashboards.

DEINE AUFGABE:
Analysiere die folgenden 30 weltweiten Medienmeldungen und identifiziere eigenständig, ohne Vorgaben oder Filter:
1. "conflict_hotspots": Akute, kriegerische oder hochbrisante Krisenherde (mindestens 4 Einträge).
2. "systemic_risks": ZUKÜNFTIGE, LATENTE ODER SYSTEMISCHE RISIKEN (mindestens 3 Einträge).
   Scanne die Meldungen gezielt nach aufkeimenden Konflikten, rechtlichen/digitalen Einschränkungen, währungspolitischen Verwerfungen, Rohstoff-Engpässen oder gesellschaftlich-politischen Pulverfässern, die in den nächsten Monaten oder Jahren an Brisanz gewinnen könnten. Bewerte deren Status und potenzielle Auswirkungen vollkommen autonom.

Meldungen der Quellen:
{feed_context}

GIB DAS ERGEBNIS AUSSCHLIESSLICH ALS VALIDES JSON ZURÜCK.

Exaktes Schema:
{{
  "conflict_hotspots": [
    {{
      "region": "Name der Region / Krisenzone",
      "actors": "Beteiligte Akteure / Mächte",
      "escalation_level": "KRITISCH / HOCH / MITTEL",
      "catalyst": "Was ist aktuell passiert oder zeichnet sich ab",
      "impact": "Auswirkungen auf Märkte, Schifffahrt oder Geopolitik"
    }}
  ],
  "systemic_risks": [
    {{
      "topic": "Name des von dir erkannten Zukunfts- oder Systemrisikos",
      "category": "Kategorie (z. B. Geomonetär, Digitalrechte, Ressourcen, Latenter Konflikt)",
      "risk_level": "HOCH / MITTEL-HOCH",
      "status": "Aktueller Stand / Entwicklungstrend",
      "impact": "Deine autonome Einschätzung der langfristigen systemischen Folgen"
    }}
  ],
  "timestamp": "",
  "global_risk_score": 79,
  "market_regime": "Aktuelles Makro-Regime (Kurze Beschreibung)",
  "top_overweight": "Empfohlene defensive Sektoren/Assets",
  "top_risk": "Größtes Einzelrisiko für Märkte und Stabilität",
  "daily_executive_summary": "Deine tagesaktuelle, weltweite Synthese der wichtigsten Entwicklungen.",
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
    {{ "name": "USA", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Kurze Einschätzung" }},
    {{ "name": "BRICS & Globaler Süden", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Kurze Einschätzung" }},
    {{ "name": "Japan & Indien / ASEAN", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Kurze Einschätzung" }},
    {{ "name": "Kern-Europa (DE/FR)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Kurze Einschätzung" }},
    {{ "name": "China (Binnenmarkt)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Kurze Einschätzung" }}
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
        {"role": "system", "content": "Du bist ein präzises Makro-, Finanz- und Geopolitik-Analysesystem, das ausschließlich valides JSON generiert."},
        {"role": "user", "content": prompt}
    ],
    model="llama-3.3-70b-versatile",
    response_format={"type": "json_object"}
)

data = json.loads(chat_completion.choices[0].message.content)

# Zeitstempel setzen
data["timestamp"] = datetime.utcnow().strftime("%d.%m.%Y - %H:%M UTC")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("GeoPuls data.json mit autonomer Krisenerkennung erfolgreich gespeichert!")
