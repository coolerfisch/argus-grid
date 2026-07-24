import socket
socket.setdefaulttimeout(10)

import os
import json
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import feedparser
import requests
import yfinance as yf
from groq import Groq
from openai import OpenAI
import anthropic

# EXTERNE QUELLEN
from sources import SOURCES

NOW_UTC = datetime.utcnow()
CURRENT_DATE_STR = NOW_UTC.strftime("%d.%m.%Y")
CURRENT_YEAR = NOW_UTC.year

# API CLIENTS
groq_key = os.environ.get("GROQ_API_KEY", "").strip()
anth_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
xai_key = os.environ.get("XAI_API_KEY", "").strip()
perplexity_key = os.environ.get("PERPLEXITY_API_KEY", "").strip()
openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
mistral_key = os.environ.get("MISTRAL_API_KEY", "").strip()
qwen_key = os.environ.get("QWEN_API_KEY", "").strip()

client_groq = Groq(api_key=groq_key) if groq_key else None
client_anthropic = anthropic.Anthropic(api_key=anth_key) if anth_key else None
client_gemini = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=gemini_key) if gemini_key else None
client_deepseek = OpenAI(base_url="https://api.deepseek.com", api_key=deepseek_key) if deepseek_key else None
client_xai = OpenAI(base_url="https://api.x.ai/v1", api_key=xai_key) if xai_key else None
client_perplexity = OpenAI(base_url="https://api.perplexity.ai", api_key=perplexity_key) if perplexity_key else None
client_openrouter = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key) if openrouter_key else None
client_mistral = OpenAI(base_url="https://api.mistral.ai/v1", api_key=mistral_key) if mistral_key else None
client_qwen = OpenAI(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", api_key=qwen_key) if qwen_key else None

def clean_text(raw_text):
    if not raw_text or not isinstance(raw_text, str):
        return ""
    text = re.sub(r'<[^>]+>', '', raw_text)
    text = re.sub(r'\*{1,3}', '', text)  # Entfernt Sternchen
    text = re.sub(r'#{1,6}\s?', '', text) # Entfernt Rauten
    text = re.sub(r'`{1,3}', '', text)
    return text.strip()

def sanitize_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_json(item) for item in obj]
    elif isinstance(obj, str):
        return clean_text(obj)
    return obj

def fetch_feed(src):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"
    }
    try:
        res = requests.get(src["url"], headers=headers, timeout=8)
        if res.status_code == 200:
            feed = feedparser.parse(res.content)
            if feed.entries:
                out = f"\n--- {src['name']} ({src['cat']}) ---\n"
                cnt = 0
                for entry in feed.entries[:3]:
                    title = clean_text(entry.get('title', ''))
                    desc = clean_text(entry.get('summary', '') or entry.get('description', ''))
                    if title:
                        out += f"- {title}: {desc[:120]}...\n"
                        cnt += 1
                if cnt > 0:
                    return True, out
    except Exception:
        pass
    return False, ""

print(f"Starte Feed-Ingestion für {len(SOURCES)} Quellen...")
raw_feed_text = ""
loaded_count = 0

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch_feed, src) for src in SOURCES]
    for future in as_completed(futures):
        success, res_str = future.result()
        if success:
            loaded_count += 1
            raw_feed_text += res_str

print(f"Erfolgreich geladen: {loaded_count}/{len(SOURCES)} Feeds.")

# GROQ FILTER
def filter_context(text):
    if not client_groq or not text:
        return text[:30000]
    prompt = f"Du bist ein OSINT-Filter. Datum: {CURRENT_DATE_STR}. Filtere irrelevante Artikel heraus und liefere prägnante Stichpunkte der wichtigsten Weltgeschehnisse."
    try:
        res = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text[:60000]}],
            temperature=0.1
        )
        return res.choices[0].message.content
    except Exception:
        return text[:30000]

filtered_text = filter_context(raw_feed_text)

# EXPERTEN SPEZIALISTEN
def get_deepseek_analysis(ctx):
    if not client_deepseek: return "Keine Daten."
    try:
        res = client_deepseek.chat.completions.create(
            model="deepseek-reasoner",
            messages=[{"role": "system", "content": "Analysiere die Lage spieltheoretisch."}, {"role": "user", "content": ctx}]
        )
        return res.choices[0].message.content
    except Exception: return "Keine Daten."

ds_analysis = clean_text(get_deepseek_analysis(filtered_text))

# SYNTHESE VIA MISTRAL
orchestrator_prompt = f"""Du bist die 'Argus Grid Intelligence Engine'.
Erstelle ein vollständiges, valides JSON für das Weltlagebild am {CURRENT_DATE_STR}.

WICHTIG:
- VERWENDE KEINE MARKDOWN-FORMATIERUNG (KEINE **, KEINE #)!
- Erzeuge ein Feld 'graph_network' mit Knoten (nodes) und Verbindungen (links).
- Erzeuge ein Feld 'conflict_hotspots' mit Koordinaten (lat, lng) und Status.

JSON STRUKTUR:
{{
  "ampel_status": "GELB",
  "ampel_reason_simple": "Kurzer Satz zur Ampel.",
  "daily_executive_summary_simple": "Kurze Zusammenfassung.",
  "simple_key_takeaways": ["Punkt 1", "Punkt 2", "Punkt 3"],
  "daily_executive_summary": "Ausführlicher Lagebericht.",
  "market_regime": "Stagflationär / Geopolitische Fragmentierung",
  "top_risk": "Lieferketten-Unterbrechung",
  "geoscore": {{"current_score": 76, "previous_48h": 72}},
  "defcon_status": {{"level": 3, "label": "DEFCON 3", "nuclear_risk_percent": 15}},
  "predictive_horizon": {{
    "base_case_summary": "Prognose 30-90 Tage...",
    "base_case_probability_pct": 65,
    "time_horizons": {{"30_days_tactic": "Taktik...", "90_days_macro": "Makro...", "360_days_structural": "Struktur..."}},
    "black_swan_tail_risk": {{"risk_event": "Extremereignis...", "probability_pct": 8, "market_impact": "Marktschock..."}},
    "leading_indicators_to_watch": [{{"indicator": "Frühwarnsignal...", "current_status": "Normal", "critical_threshold": "Schwelle..."}}]
  }},
  "historical_precedents": [{{"current_event": "Aktuelles Ereignis", "historical_analog": "Historischer Vergleich", "similarity_degree": "HOCH", "historical_outcome": "Damaliges Ergebnis", "key_divergence": "Unterschied zu heute"}}],
  "graph_network": {{
    "nodes": [
      {{"id": "n1", "label": "Strasse von Hormus", "group": "hotspot", "val": 10}},
      {{"id": "n2", "label": "Iran / IRGC", "group": "actor", "val": 8}},
      {{"id": "n3", "label": "Brent Rohöl", "group": "commodity", "val": 9}},
      {{"id": "n4", "label": "Rüstungssektor", "group": "market", "val": 7}}
    ],
    "links": [
      {{"source": "n2", "target": "n1", "label": "Drohung"}},
      {{"source": "n1", "target": "n3", "label": "Preisschock"}},
      {{"source": "n3", "target": "n4", "label": "Rotation"}}
    ]
  }},
  "conflict_hotspots": [
    {{"region": "Strasse von Hormus", "status_type": "AKTIV", "escalation_level": "HOCH", "impact": "Öltransport & Frachtraten", "lat": 26.56, "lng": 56.25}},
    {{"region": "Bab al-Mandab", "status_type": "AKTIV", "escalation_level": "HOCH", "impact": "Container-Umleitungen", "lat": 12.58, "lng": 43.33}}
  ],
  "domestic_politics_analysis": [
    {{"region_actor": "USA", "key_event_trend": "Wahlkampf & Zinspolitik", "regime_stability": "STABIL", "geopolitical_impact": "Marktvolatilität"}}
  ],
  "stress_testing_scenarios": [
    {{"scenario_name": "Eskalation Nahost", "probability_pct": 35, "timeframe": "1-3M", "cascade_chain": ["Blockade", "Ölschock", "Inflation"], "winners_long": [{{"asset": "Gold"}}, {{"asset": "Defense"}}], "losers_short": [{{"asset": "Tech"}}]}}
  ],
  "stock_picks": {{
    "top_5_buys": [{{"ticker": "RHM", "name": "Rheinmetall", "reason": "Verteidigungsnachfrage"}}],
    "flop_5_sells": [{{"ticker": "XYZ", "name": "Beispiel", "reason": "Rohstoffkosten"}}]
  }},
  "digital_and_monetary_sovereignty": [
    {{"topic": "CBDC / Digitale Währung", "actor": "EZB / Fed", "trend": "Regulierung", "systemic_impact": "Überwachung", "market_implication": "Flucht in Gold"}}
  ]
}}
"""

payload_str = f"FEEDS:\n{filtered_text[:20000]}\n\nSPIELTHEORIE:\n{ds_analysis}"

raw_json = None
if client_mistral:
    try:
        res = client_mistral.chat.completions.create(
            model="mistral-large-latest",
            messages=[{"role": "system", "content": orchestrator_prompt}, {"role": "user", "content": payload_str}],
            temperature=0.1
        )
        raw_json = res.choices[0].message.content
    except Exception as e:
        print(f"Mistral Fehler: {e}")

if not raw_json and client_qwen:
    try:
        res = client_qwen.chat.completions.create(
            model="qwen2.5-72b-instruct",
            messages=[{"role": "system", "content": orchestrator_prompt}, {"role": "user", "content": payload_str}],
            temperature=0.1
        )
        raw_json = res.choices[0].message.content
    except Exception: pass

# PARSEN & REPARIEREN
if raw_json:
    text = raw_json.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    first_b = text.find('{')
    last_b = text.rfind('}')
    if first_b != -1 and last_b != -1:
        text = text[first_b:last_b+1]
    parsed_data = json.loads(text)
else:
    # Notfall-Fallback
    parsed_data = {
        "ampel_status": "GELB",
        "ampel_reason_simple": "Spannungen an maritimen Nadelöhren.",
        "daily_executive_summary_simple": "Die Lage bleibt volatil.",
        "daily_executive_summary": "Lagebericht wird aktualisiert."
    }

# AUTOMATISCHER GRAPH- & HOTSPOT-FALLBACK (Damit NIEMALS leere Felder entstehen!)
if "graph_network" not in parsed_data or not parsed_data["graph_network"].get("nodes"):
    parsed_data["graph_network"] = {
        "nodes": [
            {"id": "n1", "label": "Strasse von Hormus", "group": "hotspot", "val": 10},
            {"id": "n2", "label": "Iran & IRGC", "group": "actor", "val": 8},
            {"id": "n3", "label": "Brent Rohöl", "group": "commodity", "val": 9},
            {"id": "n4", "label": "Rüstungssektor", "group": "market", "val": 7},
            {"id": "n5", "label": "Lieferketten-Schock", "group": "risk", "val": 8}
        ],
        "links": [
            {"source": "n2", "target": "n1", "label": "Drohung"},
            {"source": "n1", "target": "n5", "label": "Blockaderisiko"},
            {"source": "n5", "target": "n3", "label": "Preisschock"},
            {"source": "n3", "target": "n4", "label": "Marge"}
        ]
    }

if "conflict_hotspots" not in parsed_data or not parsed_data["conflict_hotspots"]:
    parsed_data["conflict_hotspots"] = [
        {"region": "Strasse von Hormus", "status_type": "AKTIV", "escalation_level": "HOCH", "impact": "Öltransport-Risiko", "lat": 26.56, "lng": 56.25},
        {"region": "Bab al-Mandab", "status_type": "AKTIV", "escalation_level": "HOCH", "impact": "Container-Umleitungen", "lat": 12.58, "lng": 43.33}
    ]

# ALLE STRINGS SÄUBERN (KEINE STERNCHEN / RAUTEN)
parsed_data = sanitize_json(parsed_data)
parsed_data["timestamp"] = NOW_UTC.strftime("%d.%m.%Y - %H:%M UTC")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(parsed_data, f, ensure_ascii=False, indent=2)

print("✅ Pipeline erfolgreich beendet. data.json gespeichert.")
