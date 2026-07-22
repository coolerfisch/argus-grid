import os
import json
import re
from datetime import datetime
from groq import Groq
import feedparser

# HTML-Tags aus RSS-Texten entfernen für sauberen Prompt
def clean_html(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return clean_text.strip()

# 1. Erweiterte RSS-Feeds (inkl. Anti-Spiegel)
rss_urls = {
    "NachDenkSeiten": "https://www.nachdenkseiten.de/?feed=rss2",
    "Apolut": "https://apolut.net/feed/",
    "Achgut": "https://www.achgut.com/rss",
    "Apollo News": "https://apollo-news.net/feed/",
    "Anti-Spiegel": "https://anti-spiegel.ru/feed/",
    "Telepolis": "https://www.telepolis.de/index.rss",
    "Tichys Einblick": "https://www.tichyseinblick.de/feed/",
    "Overton Magazin": "https://overton-magazin.de/feed/",
    "ZeroHedge (Int. Geopolitik)": "http://feeds.feedburner.com/zerohedge/feed"
}

# Browser-Header vortäuschen, damit Server die Anfrage nicht blockieren
browser_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

feed_context = ""

print("Hole tagesaktuelle News aus erweiterten RSS-Feeds...")
for source_name, url in rss_urls.items():
    try:
        feed = feedparser.parse(url, agent=browser_agent)
        count = len(feed.entries)
        print(f"-> {source_name}: {count} Artikel gefunden.")
        
        feed_context += f"\n--- Aktuelle Meldungen von {source_name} ---\n"
        for entry in feed.entries[:6]:
            title = entry.get('title', '')
            raw_summary = entry.get('summary', '') or entry.get('description', '')
            summary = clean_html(raw_summary)
            feed_context += f"- Titel: {title}\n  Zusammenfassung: {summary[:300]}...\n"
    except Exception as e:
        print(f"Fehler beim Laden von {source_name}: {e}")

# 2. Groq Client initialisieren
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY nicht in den Umgebungsvariablen gefunden!")

client = Groq(api_key=api_key)

# 3. Prompt mit striktem Hotspot-Mandat und Multi-Quellen-Fokus
prompt = f"""
Du bist der Chef-Analyst des GeoPuls Dashboards.
Erstelle eine tagesaktuelle, institutionelle Synthese der weltweiten Finanz-, Geopolitik- und Sicherheitslage.

Analysiere tagesaktuell alle zentralen kriegerischen und geopolitischen Brandherde, Eskalationsrisiken, militärische Dynamiken und Machtverschiebungen.

Nutze dazu die folgenden aktuellen Meldungen aus unabhängigen, alternativen und internationalen Medien (u. a. Anti-Spiegel, NachDenkSeiten, Apolut, ZeroHedge) sowie dein umfassendes weltweites Lagebild:

{feed_context}

WICHTIGSTE REGEL FÜR 'conflict_hotspots':
Das Feld "conflict_hotspots" DARF UNTER KEINEN UMSTÄNDEN LEER SEIN.
Erstelle IMMER mindestens 4 bis 5 konkrete, detaillierte Einträge für die wichtigsten globalen Krisenherde (z. B. Ukraine/NATO/Russland, Naher Osten/Iran/Israel, Taiwan-Straße/China/USA, Rotes Meer/Bab al-Mandab/Houthi, Sahel/Afrika).

Gib das Ergebnis AUSSCHLIESSLICH als korrektes JSON zurück.

Exaktes Schema:
{{
  "timestamp": "",
  "global_risk_score": 78,
  "market_regime": "Geopolitische Stagflation & Multipolarer Konflikt",
  "top_overweight": "Gold, Rohstoffe, Energie & Verteidigung",
  "top_risk": "Eskalation der Regionalkonflikte / Versorgungsschock",
  "daily_executive_summary": "Ausführliche Synthese der wichtigsten weltweiten Finanz- und Geopolitik-Entwicklungen der letzten 24h.",
  "conflict_hotspots": [
    {{
      "region": "Naher Osten / Iran & Israel",
      "actors": "USA / Israel vs. Iran / Achse des Widerstands",
      "escalation_level": "KRITISCH",
      "catalyst": "Beschreibung der aktuellen Vorfälle, Provokationen und militärischen Aktionen",
      "impact": "Auswirkungen auf Ölpreis (Brent), Straße von Hormus, Schifffahrt und globale Märkte"
    }},
    {{
      "region": "Ukraine / NATO-Ostflanke",
      "actors": "Russland vs. Ukraine / NATO-Unterstützer",
      "escalation_level": "HOCH",
      "catalyst": "Frontverlauf, Waffenlieferungen, Eskalationsschritte und strategische Zündeleien",
      "impact": "Auswirkungen auf europäische Energiepreise, Rüstungssektor und Agrarrohstoffe"
    }},
    {{
      "region": "Rotes Meer / Bab al-Mandab",
      "actors": "Houthi-Ansarallah vs. Westliche Marine-Allianz",
      "escalation_level": "HOCH",
      "catalyst": "Angriffe auf Handelsschiffe, Umleitung um das Kap der Guten Hoffnung",
      "impact": "Lieferketten-Verzögerungen, Frachtraten-Anstieg (SCFI), Containerschifffahrt"
    }},
    {{
      "region": "Taiwan-Straße / Indopazifik",
      "actors": "China vs. Taiwan / USA & Japan",
      "escalation_level": "MITTEL-HOCH",
      "catalyst": "Militärmanöver, Handelsrestriktionen und diplomatisches Zündeln",
      "impact": "Risiken für globale Halbleiter-Supply-Chains (TSMC) und Tech-Werte"
    }}
  ],
  "assets": [
    {{ "name": "Gold & Silber", "signal": "GREEN", "signal_text": "🟢 Sehr Attraktiv", "trend": "Stark Steigend", "driver": "Geopolitische Krise & Sichere Häfen" }},
    {{ "name": "KI & Halbleiter", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Steigend", "driver": "Technologie-Rüstung & Hardware-Boom" }},
    {{ "name": "Uran & Energie", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Stark Steigend", "driver": "Versorgungsängste & Infrastruktur-Schutz" }},
    {{ "name": "S&P 500 / Nasdaq", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Volatil", "driver": "Hohe Bewertung vs. Kriegs-Risikoaufschlag" }},
    {{ "name": "Bitcoin & Krypto", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Volatil", "driver": "Globales Liquiditätsumfeld" }},
    {{ "name": "High-Yield Bonds", "signal": "RED", "signal_text": "🔴 Unattraktiv", "trend": "Fallend", "driver": "Ausfallrisiken & Refinanzierungsdruck" }},
    {{ "name": "Gewerbeimmobilien", "signal": "RED", "signal_text": "🔴 Meiden", "trend": "Stark Fallend", "driver": "Hohes Zinsniveau & Kreditklemme" }}
  ],
  "regions": [
    {{ "name": "USA", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Militärische Machtprojektion, aber Rekordverschuldung." }},
    {{ "name": "Japan & Indien", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Gewinner der globalen Lieferketten-Neuordnung." }},
    {{ "name": "ASEAN", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Kapitalzuflüsse durch verlagerte Produktion." }},
    {{ "name": "Kern-Europa (DE/FR)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Hohe Energiekosten, Deindustrialisierung & Standortschwäche." }},
    {{ "name": "China (Binnenmarkt)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Immobilienkrise, Kapitalabflüsse & Sanktionen." }}
  ],
  "scenarios": [
    {{ "title": "Ausweitung Nahost-Konflikt (Ölschock >100$)", "prob": 40 }},
    {{ "title": "Zweite Inflationswelle / Geopolitische Stagflation", "prob": 30 }},
    {{ "title": "Direkte NATO-Eskalation / Militärischer Zwischenfall", "prob": 15 }},
    {{ "title": "KI-Produktivitätsboom (Goldilocks)", "prob": 15 }}
  ]
}}
"""

print("Rufe Groq API mit Llama 3.3 70B auf...")
chat_completion = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "Du bist ein präzises Makro- und Geopolitik-Analysesystem, das ausschließlich valides JSON generiert."},
        {"role": "user", "content": prompt}
    ],
    model="llama-3.3-70b-versatile",
    response_format={"type": "json_object"}
)

data = json.loads(chat_completion.choices[0].message.content)
data["timestamp"] = datetime.utcnow().strftime("%d.%m.%Y - %H:%M UTC")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("GeoPuls data.json erfolgreich erstellt!")
