import socket
socket.setdefaulttimeout(8)

import os
import json
import re
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import anthropic
import feedparser
import requests
import yfinance as yf
from groq import Groq
from openai import OpenAI

# EXTERNE QUELLENLISTE IMPORTIEREN
from sources import SOURCES

NOW_UTC = datetime.utcnow()
CURRENT_DATE_STR = NOW_UTC.strftime("%d.%m.%Y")
CURRENT_YEAR = NOW_UTC.year

PIPELINE_HEALTH = {
    "groq_filter": "failed",
    "deepseek_game_theory": "failed",
    "gemini_macro": "failed",
    "xai_grok": "failed",
    "perplexity_factcheck": "failed",
    "qwen_indopacific": "failed",
    "openrouter_nemotron_tech": "failed",
    "mistral_json_builder": "failed",
    "claude_chief_editor": "failed",
    "feeds_loaded": 0,
    "feeds_total": len(SOURCES)
}

# API CLIENTS INITIALISIEREN
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

def clean_markdown_and_html(raw_text):
    """Entfernt HTML-Tags sowie Markdown-Sonderzeichen (** sternchen, # rauten etc.)."""
    if not raw_text or not isinstance(raw_text, str):
        return ""
    text = re.sub(r'<[^>]+>', '', raw_text)
    text = re.sub(r'\*{1,3}', '', text)  # Entfernt Fett/Kursiv Sternchen
    text = re.sub(r'#{1,6}\s?', '', text) # Entfernt Überschriften-Rauten
    text = re.sub(r'`{1,3}', '', text)   # Entfernt Codeblocks
    return text.strip()

def sanitize_json_strings(obj):
    """Iteriert durch das finale JSON und säubert alle Strings von Rest-Markdown."""
    if isinstance(obj, dict):
        return {k: sanitize_json_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_json_strings(item) for item in obj]
    elif isinstance(obj, str):
        return clean_markdown_and_html(obj)
    return obj

def clean_expert_input(val):
    if not val or not isinstance(val, str):
        return "Keine spezifischen Zusatzdaten vorhanden."
    val_strip = val.strip()
    if val_strip.startswith("[") or "API Ausfall" in val_strip or "Fehler:" in val_strip:
        return "Keine auffälligen Sonder-Signale im Berichtszeitraum."
    return clean_markdown_and_html(val_strip)

def repair_and_parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace+1]
    return json.loads(text)

# ------------------------------------------------------------
# RSS FEED INGESTION MIT ZEIT-FILTER (MAX 48H ALT)
# ------------------------------------------------------------
browser_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def fetch_feed(src):
    try:
        res = requests.get(src["url"], headers={"User-Agent": browser_agent}, timeout=8)
        if res.status_code == 200:
            feed = feedparser.parse(res.content)
            if feed.entries:
                out = f"\n--- QUELLE: {src['name']} | Kat: {src['cat']} ---\n"
                valid_entries = 0
                for entry in feed.entries[:3]:
                    # Datums-Check: Verhindert uralte Archiv-Meldungen
                    published_parsed = entry.get('published_parsed') or entry.get('updated_parsed')
                    if published_parsed:
                        entry_dt = datetime(*published_parsed[:6])
                        if NOW_UTC - entry_dt > timedelta(hours=48):
                            continue # Überspringe alte Artikel
                    
                    title = clean_markdown_and_html(entry.get('title', ''))
                    summary = clean_markdown_and_html(entry.get('summary', '') or entry.get('description', ''))
                    out += f"- {title}: {summary[:140]}...\n"
                    valid_entries += 1
                
                if valid_entries > 0:
                    return True, out
    except Exception:
        pass
    return False, ""

print("Starte parallele Ingestion der Feeds...")
raw_feed_text = ""
loaded_count = 0

with ThreadPoolExecutor(max_workers=12) as executor:
    futures = [executor.submit(fetch_feed, src) for src in SOURCES]
    for future in as_completed(futures):
        success, res_str = future.result()
        if success:
            loaded_count += 1
            raw_feed_text += res_str

PIPELINE_HEALTH["feeds_loaded"] = loaded_count
print(f"Ingestion abgeschlossen: {loaded_count}/{len(SOURCES)} Feeds geladen.")

# ------------------------------------------------------------
# STUFE 1: GROQ FILTER
# ------------------------------------------------------------
def filter_feeds(text):
    if not client_groq:
        return text[:30000]
    prompt = f"Du bist ein OSINT-Filter. HEUTIGES DATUM: {CURRENT_DATE_STR}. Filtere uralte Meldungen strikt heraus. Behalte nur hochakute geopolitische, militärische und makroökonomische Fakten."
    try:
        res = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text[:70000]}],
            temperature=0.1
        )
        PIPELINE_HEALTH["groq_filter"] = "ok"
        return res.choices[0].message.content
    except Exception:
        return text[:30000]

filtered_context = filter_feeds(raw_feed_text)

# ------------------------------------------------------------
# STUFE 2: EXPERTEN ANALYSEN (DeepSeek & Gemini)
# ------------------------------------------------------------
def run_deepseek(context):
    if not client_deepseek: return "Keine Daten"
    try:
        res = client_deepseek.chat.completions.create(
            model="deepseek-reasoner",
            messages=[{"role": "system", "content": "Analysiere Krisen streng spieltheoretisch."}, {"role": "user", "content": context}]
        )
        PIPELINE_HEALTH["deepseek_game_theory"] = "ok"
        return res.choices[0].message.content
    except Exception: return "Keine Daten"

def run_gemini(context):
    if not client_gemini: return "Keine Daten"
    try:
        res = client_gemini.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[{"role": "system", "content": "Analysiere Makro-Schocks & Rohstoffe."}, {"role": "user", "content": context[:20000]}]
        )
        PIPELINE_HEALTH["gemini_macro"] = "ok"
        return res.choices[0].message.content
    except Exception: return "Keine Daten"

ds_out = clean_expert_input(run_deepseek(filtered_context))
gem_out = clean_expert_input(run_gemini(filtered_context))

# ------------------------------------------------------------
# STUFE 3: MISTRAL SYNTHESE & JSON BUILDER
# ------------------------------------------------------------
orchestrator_prompt = f"""Du bist die 'Argus Grid Intelligence Engine'.
Erstelle das finale JSON-Lagebild für den heutigen Tag: {CURRENT_DATE_STR}.

WICHTIGE REGELN:
1. Nutze REINEN TEXT ohne Markdown-Formatierungen (KEINE **, KEINE #, KEINE Sternchen!).
2. Beziehe dich NIEMALS auf vergangene Jahre, sondern rein auf die aktuellen Feed-Meldungen.
3. Erzeuge im Feld `graph_network` 6 bis 10 vernetzte Knoten für das Beziehungsnetzwerk.

ANTWORTE AUSSCHLIESSLICH IM VALIDEN JSON FORMAT:
{{
  "ampel_status": "GELB",
  "ampel_reason_simple": "Einfacher Satz ohne Sternchen.",
  "daily_executive_summary_simple": "Einfacher Text zur Weltlage.",
  "simple_key_takeaways": ["Punkt 1", "Punkt 2", "Punkt 3"],
  "daily_executive_summary": "Ausführlicher Lagebericht.",
  "predictive_horizon": {{
    "base_case_summary": "Prognose...",
    "base_case_probability_pct": 65,
    "time_horizons": {{"30_days_tactic": "...", "90_days_macro": "...", "360_days_structural": "..."}},
    "black_swan_tail_risk": {{"risk_event": "...", "probability_pct": 8, "market_impact": "..."}},
    "leading_indicators_to_watch": [{{"indicator": "...", "current_status": "...", "critical_threshold": "..."}}]
  }},
  "historical_precedents": [{{"current_event": "...", "historical_analog": "...", "similarity_degree": "HOCH", "historical_outcome": "...", "key_divergence": "..."}}],
  "graph_network": {{
    "nodes": [
      {{"id": "n1", "label": "Strasse von Hormus", "group": "hotspot", "val": 10}},
      {{"id": "n2", "label": "Iran IRGC", "group": "actor", "val": 8}},
      {{"id": "n3", "label": "Brent Rohöl", "group": "commodity", "val": 9}}
    ],
    "links": [
      {{"source": "n2", "target": "n1", "label": "Drohung"}},
      {{"source": "n1", "target": "n3", "label": "Preisschock"}}
    ]
  }},
  "geoscore": {{"current_score": 75, "previous_48h": 72}},
  "defcon_status": {{"level": 3, "label": "DEFCON 3", "nuclear_risk_percent": 15}},
  "market_regime": "Fragile Balance",
  "top_risk": "Lieferketten",
  "conflict_hotspots": [{{"region": "Nahost", "status_type": "AKTIV", "escalation_level": "HOCH", "impact": "Öltransport", "lat": 26.5, "lng": 56.2}}]
}}
"""

payload = f"SPIELTHEORIE:\n{ds_out}\n\nMAKRO:\n{gem_out}"

try:
    res = client_mistral.chat.completions.create(
        model="mistral-large-latest",
        messages=[{"role": "system", "content": orchestrator_prompt}, {"role": "user", "content": payload}],
        temperature=0.1
    )
    parsed_data = repair_and_parse_json(res.choices[0].message.content)
    PIPELINE_HEALTH["mistral_json_builder"] = "ok"
except Exception as e:
    # Fallback-JSON
    parsed_data = {
        "ampel_status": "GELB",
        "ampel_reason_simple": "Erhöhte regionale Spannungen ohne akute globale Eskalation.",
        "daily_executive_summary_simple": "Die Lage bleibt angespannt.",
        "simple_key_takeaways": ["Märkte volatil", "Lieferketten überwacht", "Diplomatie läuft"],
        "daily_executive_summary": "Ausführliche Lageanalyse zurzeit stabil.",
        "graph_network": {"nodes": [{"id": "n1", "label": "Globale Märkte", "group": "market", "val": 8}], "links": []}
    }

# FINALE SÄUBERUNG ALLER STRINGS VON MARKDOWN
parsed_data = sanitize_json_strings(parsed_data)

parsed_data["timestamp"] = NOW_UTC.strftime("%d.%m.%Y - %H:%M UTC")
parsed_data["pipeline_health"] = PIPELINE_HEALTH

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(parsed_data, f, ensure_ascii=False, indent=2)

print("✅ data.json erfolgreich generiert & von Müll befreit!")
