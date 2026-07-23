ARGUS GRID // Systemic Intelligence Engine (v3.0)

ARGUS GRID ist eine hochgradig automatisierte, unvoreingenommene Systemic Intelligence Engine, die globale Geopolitik, Makroökonomie, Konfliktherde, Fluchtbewegungen und Militäroperationen in Echtzeit analysiert.

Das System kombiniert ein ausbalanciertes Netzwerk aus über 140 weltweiten Primärquellen mit Live-Finanzdaten, OpenSky ADS-B Flugtracking und einem orchestrierten Multi-LLM-Komitee (DeepSeek V4 Pro, Claude Sonnet 5, Gemini 3.6 Flash, Llama 3.3 70B via Groq).


Systemarchitektur & Pipeline

Die Datenverarbeitung verläuft vollautomatisch in einer mehrstufigen High-Performance Pipeline:

1. 140+ RSS Feeds (Politik, OSINT, Makro) + yFinance Live-Märkte + OpenSky ADS-B
   (Parallel Fetching via ThreadPool)

2. STUFE 1: Groq LPU (Llama 3.3 70B)
   Extreme Datenkomprimierung & Entrauschung (~90.000 Zeichen -> ~3.000 Wörter)

3. STUFE 2a: DeepSeek V4 Pro
   Spieltheoretisches Gutachten (Fraktionen, Payoffs, Counter-Model)

4. STUFE 2b: Gemini 3.6 Flash
   Makro-Schocks, Rohstoffe, Vertreibung & Digitale Souveränität

5. STUFE 3: Claude Sonnet 5 (Chef-Synthesizer)
   Validierung, Balancierung aller Narrative (Dem/GOP/Left/Right/BRICS) & JSON-Bau -> data.json -> Frontend (index.html + Leaflet.js)


Kernfunktionen & Features

Taktische Live-Radar-Karte:
- Pulsierende Kriegszonen: Automatische Hervorhebung aktiver Konflikt- und Fluchtherde.
- Animierte Fluchtkorridore: Visuelle Vektoren für weltweite Migration (UNHCR/IOM DTM).
- Live OpenSky ADS-B Tracking: Ausgerichtete Flugspuren aktiver Aufklärungs- und Militärmaschinen (FORTE, NATO AWACS, Strategic Airlift).

Spieltheoretisches Gutachten (DeepSeek Engine):
- Zerlegung von Staaten in interne Fraktionen (Militär, Parteiflügel, Exekutive).
- Trennung von Kurzfrist- (4-8 Wochen) und Langfrist-Horizonten.
- Quantifizierte Payoff-Matrix (Skala -3 bis +3) inkl. Falsifikations-Gegenmodell.

Innenpolitik & Regimestabilität:
- Systematische Erfassung von Wahlzyklen, Parteienkämpfen und Gesetzgebungsdruck in den USA, der EU, Großbritannien, den BRICS-Staaten, Nahost und Afrika.

Vollständig ausbalanciertes Quellenspektrum (No-Bias Policy):
- Gegenüberstellung von Links/Progressiv, Konservativ/Rechts und Liberal/Mitte bei allen Großmächten zur Vermeidung von Confirmation Bias.

Dynamische Aktien-Rotation:
- Lageabhängige Gewichtung von Sektoren (Shipping, Defense, Rohstoffe, Tech, Energie).


Required Environment Variables (GitHub Secrets)

- GROQ_API_KEY: Fast Filtering & Summarization (Llama 3.3 70B)
- ANTHROPIC_API_KEY: Final Synthesis & JSON Generation (Claude Sonnet 5)
- GEMINI_API_KEY: Macro & Migration Intelligence (Gemini 3.6 Flash)
- DEEPSEEK_API_KEY: Game Theory Deep Dive (DeepSeek V4 Pro)
- OPENSKY_USER: (Optional) Account für höhere ADS-B Rate-Limits
- OPENSKY_PASSWORD: (Optional) OpenSky Passwort


GitHub Actions Automation (.github/workflows/update.yml)

name: Update Argus Grid Dashboard

on:
  schedule:
    - cron: '0 */4 * * *'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repo
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: |
          pip install requests feedparser yfinance anthropic groq openai

      - name: Run Dashboard Pipeline
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          OPENSKY_USER: ${{ secrets.OPENSKY_USER }}
          OPENSKY_PASSWORD: ${{ secrets.OPENSKY_PASSWORD }}
        run: python update_dashboard.py

      - name: Commit and Push Data
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add data.json
          git commit -m "auto: Sync Argus Grid Live Intelligence Data [skip ci]" || exit 0
          git push


Lokale Entwicklung & Start

1. Repository klonen:
   git clone https://github.com/coolerfisch/argus-grid.git
   cd argus-grid

2. Pip-Pakete installieren:
   pip install requests feedparser yfinance anthropic groq openai

3. Pipeline manuell ausführen:
   python update_dashboard.py

4. Lokalen Webserver starten:
   python -m http.server 8000
   Dashboard im Browser unter http://localhost:8000 öffnen.


System- & Haftungsausschluss (Disclaimer)

- Keine Finanz- oder Anlageberatung: Sämtliche auf ARGUS GRID dargestellten Inhalte, Aktien-Rotationen, Stress-Test-Szenarien und Kennzahlen dienen ausschließlich akademischen, strategischen und Forschungszwecken im Rahmen automatisierter OSINT-Analysen (Open Source Intelligence).
- Automatisierte Verarbeitung: Die Auswertungen basieren auf Algorithmen und LLM-Synthesen. Es wird keine Haftung für die Richtigkeit, Vollständigkeit oder Aktualität der Primärdaten übernommen.
