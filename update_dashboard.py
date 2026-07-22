import os
import json
import re
from datetime import datetime
from groq import Groq
import feedparser

# HTML-Tags entfernen für sauberen KI-Prompt
def clean_html(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return clean_text.strip()

# 1. Quellenspiegel: Alternative + Mainstream + Finanz- & Marktmedien
rss_urls = {
    # --- Finanz-, Makro- & Börsenmedien ---
    "Handelsblatt (Finanzen)": "https://www.handelsblatt.com/contentexport/feed/finanzen",
    "Finanzmarktwelt (FMW)": "https://finanzmarktwelt.de/feed/",
    "stock3 (Godmode)": "https://stock3.com/news/feed/",
    "Manager Magazin": "https://www.manager-magazin.de/rss",
    "Wallstreet-Online": "https://www.wallstreet-online.de/rss/nachrichten.xml",
    "ZeroHedge (Int. Finance & Macro)": "http://feeds.feedburner.com/zerohedge/feed",

    # --- Geopolitik & Mainstream ---
    "NZZ (International)": "https://www.nzz.ch/international.rss",
    "FAZ (Ausland)": "https://www.faz.net/rss/aktuell/politik/ausland/",
    "Tagesschau (Ausland)": "https://www.tagesschau.de/ausland/index.xml",
    "BBC World News": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Foreign Affairs": "https://www.foreignaffairs.com/rss.xml",

    # --- Unabhängige & Alternative Medien ---
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

print("Hole tagesaktuelle News aus 18 Quellen (Finanzen, Geopolitik, Alternative)...")
for source_name, url in rss_urls.items():
    try:
        feed = feedparser.parse(url, agent=browser_agent)
        feed_context += f"\n--- Aktuelle Meldungen von {source_name} ---\n"
        for entry in feed.entries[:3]:  # Top 3 Fokus-Artikel pro Quelle
            title = entry.get('title', '')
            raw_summary = entry.get('summary', '') or entry.get('description', '')
            summary = clean_html(raw_summary)
            feed_context += f"- Titel: {title}\n  Zusammenfassung: {summary[:250]}...\n"
    except Exception as e:
        print(f"Fehler bei {source_name}: {e}")

# 2. Groq Client initialisieren
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY nicht in den Umgebungsvariablen gefunden!")

client = Groq(api_key=api_key)

# 3. Synthese-Prompt für Makro, Märkte & Geopolitik
prompt = f"""
Du bist der Chef-Analyst des GeoPuls Dashboards.
Erstelle eine tagesaktuelle, objektive Synthese aus Finanzmärkten, Makroökonomie (Zinsen, Inflation, Rohstoffe) und globaler Geopolitik.

Verarbeite dazu die Live-Meldungen aus Markt- und Finanzmedien (Handelsblatt, Finanzmarktwelt, stock3, ZeroHedge), etablierten Geopolitik-Analysen (NZZ, FAZ, Foreign Affairs) und alternativen Medien (NachDenkSeiten, Apolut, Anti-Spiegel, etc.):

{feed_context}

WICHTIG FÜR 'conflict_hotspots':
Das Feld "conflict_hotspots" MUSS mindestens 4 konkrete, detaillierte Einträge zu den wichtigsten weltweiten Krisenherden enthalten (Ukraine/NATO/Russland, Naher Osten/Iran/Israel, Taiwan-Straße/China/USA, Rotes Meer/Bab al-Mandab).

Gib das Ergebnis AUSSCHLIESSLICH als korrektes JSON zurück.

Exaktes Schema:
{{
  "conflict_hotspots": [
    {{
      "region": "Naher Osten / Iran & Israel",
      "actors": "USA / Israel vs. Iran / Achse des Widerstands",
      "escalation_level": "KRITISCH",
      "catalyst": "Aktuelle militärische Ereignisse oder Eskalationsschritte",
      "impact": "Konkrete Folgen für Brent-Öl, Seewege und geopolitische Risikoaufschläge"
    }},
    {{
      "region": "Ukraine / NATO-Ostflanke",
      "actors": "Russland vs. Ukraine / NATO-Unterstützer",
      "escalation_level": "HOCH",
      "catalyst": "Militärische Lage, Rüstungsfragen und strategische Zündeleien",
      "impact": "Folgen für europäische Strom-/Gaspreise, Rüstungssektor und Agrarrohstoffe"
    }},
    {{
      "region": "Rotes Meer / Bab al-Mandab",
      "actors": "Houthi-Milizen vs. Westliche Marine-Allianz",
      "escalation_level": "HOCH",
      "catalyst": "Schiffsangriffe und Sicherung der Handelsrouten",
      "impact": "Lieferketten, Frachtraten und Container-Transport"
    }},
    {{
      "region": "Taiwan-Straße / Indopazifik",
      "actors": "China vs. Taiwan / USA & Japan",
      "escalation_level": "MITTEL-HOCH",
      "catalyst": "Militärmanöver und technologische Sanktionen",
      "impact": "Risiken für Halbleiter-Lieferketten (TSMC) und Tech-Sektor"
    }}
  ],
  "timestamp": "",
  "global_risk_score": 78,
  "market_regime": "Geopolitische Stagflation & Zins-Unsicherheit",
  "top_overweight": "Gold, Energie, Rohstoffe & Verteidigung",
  "top_risk": "Versorgungsschock / Zins- und Refinanzierungsdruck",
  "daily_executive_summary": "Ausführliche Synthese aus Makro-Finanzmärkten und Geopolitik der letzten 24h.",
  "assets": [
    {{ "name": "Gold & Silber", "signal": "GREEN", "signal_text": "🟢 Sehr Attraktiv", "trend": "Stark Steigend", "driver": "Geopolitik, Zentralbankkäufe & Sichere Häfen" }},
    {{ "name": "KI & Halbleiter", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Steigend", "driver": "Technologie-Rüstung & Monetarisierung" }},
    {{ "name": "Uran & Energie", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Stark Steigend", "driver": "Angebotsdefizit & Versorgungsängste" }},
    {{ "name": "S&P 500 / Nasdaq", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Volatil", "driver": "Hohe KGV-Bewertung vs. Zinsaussichten" }},
    {{ "name": "Bitcoin & Krypto", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Volatil", "driver": "M2-Geldmenge & Liquiditätsumfeld" }},
    {{ "name": "High-Yield Bonds", "signal": "RED", "signal_text": "🔴 Unattraktiv", "trend": "Fallend", "driver": "Ausfallrisiken & Refinanzierungsdruck" }},
    {{ "name": "Gewerbeimmobilien", "signal": "RED", "signal_text": "🔴 Meiden", "trend": "Stark Fallend", "driver": "Hohes Zinsniveau & Leerstände" }}
  ],
  "regions": [
    {{ "name": "USA", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Tech- & Kapitalmarkt-Dominanz, aber Rekordverschuldung." }},
    {{ "name": "Japan & Indien", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Gewinner der globalen Lieferketten-Neuordnung." }},
    {{ "name": "ASEAN", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Starker Kapitalzufluss durch Friendshoring." }},
    {{ "name": "Kern-Europa (DE/FR)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Deindustrialisierung, hohe Energiekosten & Standortschwäche." }},
    {{ "name": "China (Binnenmarkt)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Immobilienkrise, Kapitalabflüsse & Deflationsdruck." }}
  ],
  "scenarios": [
    {{ "title": "Ausweitung Nahost-Konflikt (Ölschock >100$)", "prob": 40 }},
    {{ "title": "Zweite Inflationswelle / Geopolitische Stagflation", "prob": 30 }},
    {{ "title": "Direkte NATO-Eskalation / Militärischer Zwischenfall", "prob": 15 }},
    {{ "title": "KI-Produktivitätsboom (Goldilocks)", "prob": 15 }}
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

# Fallback-Sicherung
if "conflict_hotspots" not in data or not data["conflict_hotspots"]:
    print("Warnung: KI hat keine Hotspots geliefert. Nutze Fallback.")
    data["conflict_hotspots"] = [
        {
            "region": "Naher Osten / Iran & Israel",
            "actors": "USA / Israel vs. Iran / Achse des Widerstands",
            "escalation_level": "KRITISCH",
            "catalyst": "Aktivitäten im Persischen Golf und Drohungen an wichtigen Seewegen.",
            "impact": "Risikoaufschläge bei Rohöl und erhöhte Marktvolatilität."
        },
        {
            "region": "Ukraine / NATO-Ostflanke",
            "actors": "Russland vs. Ukraine / NATO-Unterstützer",
            "escalation_level": "HOCH",
            "catalyst": "Frontverlauf, strategische Schläge und Waffenlieferungen.",
            "impact": "Volatilität bei europäischen Agrar- und Energiepreisen."
        },
        {
            "region": "Rotes Meer / Bab al-Mandab",
            "actors": "Houthi-Milizen vs. Westliche Marine-Allianz",
            "escalation_level": "HOCH",
            "catalyst": "Angriffe auf Frachtschiffe und Ausweichrouten um Afrika.",
            "impact": "Steigende Transportkosten und Lieferzeitverzögerungen."
        },
        {
            "region": "Taiwan-Straße / Indopazifik",
            "actors": "China vs. Taiwan / USA",
            "escalation_level": "MITTEL-HOCH",
            "catalyst": "Militärmanöver und technologische Handelsbarrieren.",
            "impact": "Potenzielle Risiken für die globale Chip-Infrastruktur."
        }
    ]

data["timestamp"] = datetime.utcnow().strftime("%d.%m.%Y - %H:%M UTC")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("GeoPuls data.json mit 18 Quellen (inkl. Finanz-Medien) erfolgreich aktualisiert!")
