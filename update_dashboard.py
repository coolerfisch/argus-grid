import os
import json
from datetime import datetime
from groq import Groq
import feedparser

# 1. RSS-Feeds auslesen (NachDenkSeiten, Apolut, Achgut, Apollo News)
rss_urls = {
    "NachDenkSeiten": "https://www.nachdenkseiten.de/?feed=rss2",
    "Apolut": "https://apolut.net/feed/",
    "Achgut": "https://www.achgut.com/rss",
    "Apollo News": "https://apollo-news.net/feed/"
}

feed_context = ""

print("Hole tagesaktuelle News aus RSS-Feeds...")
for source_name, url in rss_urls.items():
    try:
        feed = feedparser.parse(url)
        feed_context += f"\n--- Aktuelle Meldungen von {source_name} ---\n"
        # Die neuesten 5 Artikel pro Quelle abgreifen
        for entry in feed.entries[:5]:
            summary = entry.get('summary', '') or entry.get('description', '')
            feed_context += f"- Titel: {entry.title}\n  Zusammenfassung: {summary[:250]}...\n"
    except Exception as e:
        print(f"Fehler beim Laden von {source_name}: {e}")

# 2. Groq Client initialisieren
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY nicht in den Umgebungsvariablen gefunden!")

client = Groq(api_key=api_key)

# 3. Prompt inklusive Geopolitik & Multiperspektiv-Kontext
prompt = f"""
Du bist der Chef-Analyst des GeoPuls Dashboards.
Erstelle eine tagesaktuelle, institutionelle Synthese der weltweiten Finanz-, Geopolitik- und Sicherheitslage.

Analysiere insbesondere aktuelle Kriegsgefahren, militärische Dynamiken, Geopolitik und wer aktuell wo zündelt/provoziert sowie deren globale Auswirkungen.

Nutze dazu auch die folgenden aktuellen Meldungen aus unabhängigen und alternativen Medien (NachDenkSeiten, Apolut, Achgut, Apollo News):

{feed_context}

Gib das Ergebnis AUSSCHLIESSLICH als korrektes JSON zurück.

Exaktes Schema:
{{
  "timestamp": "",
  "global_risk_score": 75,
  "market_regime": "Geopolitische Stagflation",
  "top_overweight": "Gold, Energie & Rüstung/Rohstoffe",
  "top_risk": "Eskalation der Regionalkonflikte / Lieferketten-Schock",
  "daily_executive_summary": "Prägnante Zusammenfassung der wichtigsten geopolitischen & finanziellen Entwicklungen der letzten 24h unter Berücksichtigung aller Medienquellen.",
  "conflict_hotspots": [
    {{
      "region": "Naher Osten / Hormus",
      "actors": "USA / Israel vs. Iran / Achse",
      "escalation_level": "KRITISCH",
      "catalyst": "Wer zündelt / was ist passiert (Kurzbeschreibung)",
      "impact": "Auswirkung auf Ölpreis, Tanker-Routen und Märkte"
    }},
    {{
      "region": "Osteuropa / NATO-Ostflanke",
      "actors": "NATO / Ukraine vs. Russland",
      "escalation_level": "HOCH",
      "catalyst": "Wer zündelt / was ist passiert",
      "impact": "Auswirkung auf Energie, Getreide, Sanktionen"
    }},
    {{
      "region": "Taiwan-Straße / Indopazifik",
      "actors": "USA / Taiwan vs. China",
      "escalation_level": "MITTEL-HOCH",
      "catalyst": "Wer zündelt / was ist passiert",
      "impact": "Auswirkung auf Halbleiter, Tech-Sektor, Frachtraten"
    }}
  ],
  "assets": [
    {{ "name": "Gold & Silber", "signal": "GREEN", "signal_text": "🟢 Sehr Attraktiv", "trend": "Stark Steigend", "driver": "Kriegs-Unsicherheit & Sichere Häfen" }},
    {{ "name": "KI & Halbleiter", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Steigend", "driver": "Monetarisierung KI-Hardware" }},
    {{ "name": "Uran & Energie", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "Stark Steigend", "driver": "Angebotsdefizit vs. Versorgungsangst" }},
    {{ "name": "S&P 500 / Nasdaq", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Volatil", "driver": "Bewertung vs. Geopolitik" }},
    {{ "name": "Bitcoin & Krypto", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "Volatil", "driver": "Liquidity-Squeeze" }},
    {{ "name": "High-Yield Bonds", "signal": "RED", "signal_text": "🔴 Unattraktiv", "trend": "Fallend", "driver": "Refinanzierungsdruck & Risikoaufschläge" }},
    {{ "name": "Gewerbeimmobilien", "signal": "RED", "signal_text": "🔴 Meiden", "trend": "Stark Fallend", "driver": "Leerstand & Zinsdruck" }}
  ],
  "regions": [
    {{ "name": "USA", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Militär- und Tech-Dominanz, aber hohe Verschuldung." }},
    {{ "name": "Japan & Indien", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Profiteure von Umstrukturierung der Handelsrouten." }},
    {{ "name": "ASEAN", "signal": "GREEN", "signal_text": "🟢 Grün", "summary": "Starker Kapitalzufluss durch Friendshoring." }},
    {{ "name": "Kern-Europa (DE/FR)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Deindustrialisierung, Energiekrise & Standortschwäche." }},
    {{ "name": "China (Binnenmarkt)", "signal": "RED", "signal_text": "🔴 Rot", "summary": "Immobilienkrise, Deflation & Handelskonflikte." }}
  ],
  "scenarios": [
    {{ "title": "Ausweitung Naher Osten (Ölschock >100$)", "prob": 40 }},
    {{ "title": "Zweite Inflationswelle / Stagflation", "prob": 30 }},
    {{ "title": "KI-Produktivitätsboom (Goldilocks)", "prob": 20 }},
    {{ "title": "Direkte NATO-Eskalation", "prob": 10 }}
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

print("GeoPuls data.json mit erweitertem Quellenkontext erfolgreich erstellt!")
