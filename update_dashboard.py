import os
import json
import re
from datetime import datetime
import anthropic
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

# B. QUELLENSPIEGEL
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

    # 🏛️ 2. PRIMÄRQUELLEN & DIPLOMATIE
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

    # 🔓 4. UNABHÄNGIGE & ALTERNATIVE ANALYSTEN
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
            feed_context += f"- {title}: {summary[:150]}...\n"
    except Exception as e:
        print(f"Fehler bei {source_name}: {e}")

if len(feed_context) > 12000:
    feed_context = feed_context[:12000] + "\n... [Feeds gekürzt]"

# SCHEMA-VORLAGE FÜR BEIDE KIS
json_template_desc = """
{
  "daily_executive_summary": "Synthese...",
  "global_risk_score": 75,
  "market_regime": "Marktregime",
  "top_overweight": "Gewinner",
  "top_risk": "Risiko",
  "defcon_status": {"level": 3, "label": "Label", "nuclear_risk_percent": 15, "primary_driver": "Treiber"},
  "narrative_divergence": [
    {"topic": "Thema 1", "mainstream_view": "Westen", "brics_view": "BRICS", "alternative_view": "Alternativ"},
    {"topic": "Thema 2", "mainstream_view": "Westen", "brics_view": "BRICS", "alternative_view": "Alternativ"},
    {"topic": "Thema 3", "mainstream_view": "Westen", "brics_view": "BRICS", "alternative_view": "Alternativ"}
  ],
  "domestic_politics": [
    {"country_region": "Region 1", "topic": "Thema", "status": "Status", "impact": "Impact"},
    {"country_region": "Region 2", "topic": "Thema", "status": "Status", "impact": "Impact"},
    {"country_region": "Region 3", "topic": "Thema", "status": "Status", "impact": "Impact"}
  ],
  "stock_picks": {
    "top_5_buys": [{"ticker": "T1", "name": "N1", "sector": "S1", "reason": "R1"}, {"ticker": "T2", "name": "N2", "sector": "S2", "reason": "R2"}, {"ticker": "T3", "name": "N3", "sector": "S3", "reason": "R3"}, {"ticker": "T4", "name": "N4", "sector": "S4", "reason": "R4"}, {"ticker": "T5", "name": "N5", "sector": "S5", "reason": "R5"}],
    "flop_5_sells": [{"ticker": "S1", "name": "N1", "sector": "S1", "reason": "R1"}, {"ticker": "S2", "name": "N2", "sector": "S2", "reason": "R2"}, {"ticker": "S3", "name": "N3", "sector": "S3", "reason": "R3"}, {"ticker": "S4", "name": "N4", "sector": "S4", "reason": "R4"}, {"ticker": "S5", "name": "N5", "sector": "S5", "reason": "R5"}]
  },
  "conflict_hotspots": [
    {"region": "R1", "actors": "A1", "escalation_level": "KRITISCH", "catalyst": "C1", "impact": "I1", "lat": 31.5, "lng": 34.75},
    {"region": "R2", "actors": "A2", "escalation_level": "HOCH", "catalyst": "C2", "impact": "I2", "lat": 48.37, "lng": 31.16},
    {"region": "R3", "actors": "A3", "escalation_level": "HOCH", "catalyst": "C3", "impact": "I3", "lat": 23.69, "lng": 120.96},
    {"region": "R4", "actors": "A4", "escalation_level": "MITTEL", "catalyst": "C4", "impact": "I4", "lat": 12.58, "lng": 43.33}
  ],
  "systemic_risks": [
    {"topic": "T1", "category": "C1", "risk_level": "HOCH", "status": "S1", "impact": "I1"},
    {"topic": "T2", "category": "C2", "risk_level": "HOCH", "status": "S2", "impact": "I2"},
    {"topic": "T3", "category": "C3", "risk_level": "MITTEL", "status": "S3", "impact": "I3"}
  ],
  "assets": [
    {"name": "Gold & Silber", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "T", "driver": "D"},
    {"name": "KI & Halbleiter", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "T", "driver": "D"},
    {"name": "Uran & Energie", "signal": "GREEN", "signal_text": "🟢 Attraktiv", "trend": "T", "driver": "D"},
    {"name": "S&P 500 / Nasdaq", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "T", "driver": "D"},
    {"name": "Bitcoin & Krypto", "signal": "AMBER", "signal_text": "🟡 Neutral", "trend": "T", "driver": "D"},
    {"name": "High-Yield Bonds", "signal": "RED", "signal_text": "🔴 Unattraktiv", "trend": "T", "driver": "D"},
    {"name": "Gewerbeimmobilien", "signal": "RED", "signal_text": "🔴 Meiden", "trend": "T", "driver": "D"}
  ],
  "scenarios": [
    {"title": "S1", "prob": 40},
    {"title": "S2", "prob": 30},
    {"title": "S3", "prob": 15},
    {"title": "S4", "prob": 15}
  ]
}
"""

raw_text = None
generator_used = "Claude 3.5 Sonnet"

# 1. SCHRITT: CLAUDE GENERIERT DEN ENTWURF
anth_key = os.environ.get("ANTHROPIC_API_KEY")
if anth_key:
    try:
        print("Schritt 1: Claude 3.5 Sonnet generiert den Analyse-Entwurf...")
        client_anthropic = anthropic.Anthropic(api_key=anth_key)
        response = client_anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.2,
            system="Du bist ein präzises OSINT-Geopolitikmodell. Antworte AUSSCHLIESSLICH im validen JSON-Format basierend auf diesem Schema:\n" + json_template_desc,
            messages=[{"role": "user", "content": f"Live-Finanzdaten:\n{live_market_context}\n\nFeeds:\n{feed_context}"}]
        )
        raw_text = response.content[0].text.strip()
    except Exception as e:
        print(f"Claude Fehler: {e}. Wechsle zu Llama als primärer Generator...")

# Fallback auf Llama wenn Claude fehlgeschlagen ist
if not raw_text:
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        print("Claude nicht erreichbar. Llama 3.3 übernimmt als Generator...")
        client_groq = Groq(api_key=groq_key)
        chat_completion = client_groq.chat.completions.create(
            messages=[
                {"role": "system", "content": "Du bist ein präzises OSINT-Modell. Antworte rein in JSON."},
                {"role": "user", "content": f"Live-Finanzdaten:\n{live_market_context}\n\nFeeds:\n{feed_context}\n\nSchema:\n{json_template_desc}"}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        raw_text = chat_completion.choices[0].message.content
        generator_used = "Llama 3.3 (Fallback-Generator)"

# Säubern von Markdown Wrappern
if raw_text and raw_text.startswith("```"):
    raw_text = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text)
    raw_text = re.sub(r"\n?```$", "", raw_text)

data = json.loads(raw_text)


# 2. SCHRITT: LLAMA KLOPFT AUF DIE FINGER (AUDIT & QUALITÄTSKONTROLLE)
groq_key = os.environ.get("GROQ_API_KEY")
if groq_key:
    try:
        print("Schritt 2: Llama 3.3 (Groq) prüft Claude's Entwurf ('Fingerklopfen'-Audit)...")
        client_groq = Groq(api_key=groq_key)
        audit_prompt = f"""
Du bist der leitende Chefredakteur und OSINT-Qualitätskontrolleur. 
Prüfe den folgenden JSON-Entwurf eines Analysten auf Plausibilität, logische Fehler, korrekte Ticker und ob alle geforderten JSON-Keys vorhanden sind. Korrigiere Fehler, falls Claude geschlampt oder halluziniert hat.
Gib AUSSCHLIESSLICH das korrigierte, valide JSON zurück.

JSON-Entwurf zum Prüfen:
{json.dumps(data, ensure_ascii=False)}
"""
        audit_completion = client_groq.chat.completions.create(
            messages=[
                {"role": "system", "content": "Du bist ein strenger OSINT-Auditor. Korrigiere das JSON falls nötig und gib es im exakten Format zurück."},
                {"role": "user", "content": audit_prompt}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        audited_text = audit_completion.choices[0].message.content.strip()
        if audited_text.startswith("```"):
            audited_text = re.sub(r"^```[a-zA-Z]*\n?", "", audited_text)
            audited_text = re.sub(r"\n?```$", "", audited_text)
        
        data = json.loads(audited_text)
        print("Audit durch Llama erfolgreich abgeschlossen. Daten wurden verifiziert.")
    except Exception as e:
        print(f"Hinweis: Llama-Audit übersprungen wegen Fehler: {e}")


# --- NORMALISIERUNG ALLER FELDER ---
if not data.get("daily_executive_summary"):
    data["daily_executive_summary"] = data.get("executive_summary") or data.get("summary") or "Die geopolitische Lage bleibt angespannt."

raw_nd = data.get("narrative_divergence", [])
if isinstance(raw_nd, dict):
    raw_nd = [raw_nd]

normalized_nd = []
for item in raw_nd:
    if isinstance(item, dict):
        normalized_nd.append({
            "topic": item.get("topic") or "Geopolitischer Schauplatz",
            "mainstream_view": item.get("mainstream_view") or item.get("mainstream") or "Fokus auf westliche Ordnung.",
            "brics_view": item.get("brics_view") or item.get("brics") or "Fokus auf multipolare Perspektive.",
            "alternative_view": item.get("alternative_view") or item.get("alternative") or "Fokus auf Kaskadeneffekte."
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

print(f"GeoPuls Dashboard erfolgreich aktualisiert! (Generator: {generator_used} + Llama Auditor)")
