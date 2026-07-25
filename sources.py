#!/usr/bin/env python3
"""
ARGUS GRID v3.0 - Global Intelligence Sources Directory (Reparierte Version)
Vollständiges weltweites Quellverzeichnis mit aktiven Primärquellen-Feeds.
"""

# HINWEIS FÜR DEN CRAWLER / FETCH-SKRIPT:
# Nutze beim Abrufen zwingend folgende Headers, um 403-Blockaden zu vermeiden:
# HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}

SOURCES = [
    # ==========================================
    # 🇺🇸🇨🇦 1. NORDAMERIKA (USA & KANADA)
    # ==========================================
    {"name": "CNN World", "url": "https://rss.cnn.com/rss/edition.rss", "cat": "US/Politik", "weight": 0.95, "bias": "US-LEFT-LIBERAL"},
    {"name": "MSNBC / NBC News", "url": "https://feeds.nbcnews.com/nbcnews/public/news", "cat": "US/Politik", "weight": 0.90, "bias": "US-LEFT-LIBERAL"},
    {"name": "New York Times World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "cat": "US/Presse", "weight": 0.95, "bias": "US-LEFT-LIBERAL"},
    {"name": "Fox News Latest", "url": "https://moxie.foxnews.com/google-publisher/latest.xml", "cat": "US/Politik", "weight": 0.95, "bias": "US-CONSERVATIVE"},
    {"name": "National Review", "url": "https://www.nationalreview.com/feed/", "cat": "US/Politik", "weight": 0.85, "bias": "US-CONSERVATIVE"},
    {"name": "The Washington Times", "url": "https://www.washingtontimes.com/rss/headlines/news/", "cat": "US/Politik", "weight": 0.85, "bias": "US-CONSERVATIVE"},
    {"name": "Wall Street Journal (MarketWatch Alt)", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories", "cat": "US/Finanzen", "weight": 0.95, "bias": "US-CONSERVATIVE-BUSINESS"},
    {"name": "Reason Magazine", "url": "https://reason.com/feed/", "cat": "US/Debatte", "weight": 0.80, "bias": "US-LIBERTARIAN"},
    {"name": "Bloomberg Markets (CNBC Alt)", "url": "https://search.cnbc.com/rs/search/combinedAsset/rss.xml?partnerId=wrss01&id=10000664", "cat": "US/Finanzen", "weight": 0.95, "bias": "CENTER-LIBERAL"},
    {"name": "CBC News World (Kanada)", "url": "https://www.cbc.ca/webfeed/rss/rss-world", "cat": "CA/Presse", "weight": 0.90, "bias": "CA-CENTER-LIBERAL"},
    {"name": "The Globe and Mail (Kanada)", "url": "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/world/", "cat": "CA/Presse", "weight": 0.90, "bias": "CA-CENTER-RIGHT"},
    {"name": "National Post (Kanada)", "url": "https://nationalpost.com/feed/", "cat": "CA/Presse", "weight": 0.85, "bias": "CA-CONSERVATIVE"},

    # ==========================================
    # 🇩🇪🇦🇹🇨🇭 2. DEUTSCHLAND & DACH-RAUM
    # ==========================================
    {"name": "taz die tageszeitung", "url": "https://taz.de/rss.xml", "cat": "DE/Politik", "weight": 0.85, "bias": "DE-LEFT-PROGRESSIVE"},
    {"name": "Der Spiegel", "url": "https://www.spiegel.de/schlagzeilen/tops/index.rss", "cat": "DE/Medien", "weight": 0.90, "bias": "DE-LEFT-LIBERAL"},
    {"name": "Süddeutsche Zeitung", "url": "https://rss.sueddeutsche.de/rss/Topthemen", "cat": "DE/Presse", "weight": 0.90, "bias": "DE-LEFT-LIBERAL"},
    {"name": "FAZ Politik", "url": "https://www.faz.net/rss/aktuell/", "cat": "DE/Presse", "weight": 0.90, "bias": "DE-CONSERVATIVE"},
    {"name": "Die Welt", "url": "https://www.welt.de/feeds/latest.rss", "cat": "DE/Presse", "weight": 0.85, "bias": "DE-CONSERVATIVE"},
    {"name": "NZZ International", "url": "https://www.nzz.ch/international.rss", "cat": "CH/Presse", "weight": 0.95, "bias": "DE-CONSERVATIVE-LIBERAL"},
    {"name": "Die Zeit Online", "url": "https://newsfeed.zeit.de/index", "cat": "DE/Presse", "weight": 0.90, "bias": "DE-CENTER-LIBERAL"},
    {"name": "Handelsblatt", "url": "https://www.handelsblatt.com/contentexport/feed/top-themen", "cat": "DE/Finanzen", "weight": 0.90, "bias": "DE-LIBERAL-BUSINESS"},

    # ==========================================
    # 🇬🇧 3. GROSSBRITANNIEN (UK)
    # ==========================================
    {"name": "The Guardian World", "url": "https://www.theguardian.com/world/rss", "cat": "UK/Presse", "weight": 0.90, "bias": "UK-LEFT-LIBERAL"},
    {"name": "The Telegraph", "url": "https://www.telegraph.co.uk/world-news/rss.xml", "cat": "UK/Presse", "weight": 0.85, "bias": "UK-CONSERVATIVE"},
    {"name": "The Spectator", "url": "https://www.spectator.co.uk/feed/", "cat": "UK/Debatte", "weight": 0.80, "bias": "UK-CONSERVATIVE"},
    {"name": "BBC World News", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "cat": "UK/Medien", "weight": 0.95, "bias": "MAINSTREAM-CENTER"},
    {"name": "Financial Times", "url": "https://www.ft.com/news-feed?format=rss", "cat": "UK/Finanzen", "weight": 0.95, "bias": "CENTER-LIBERAL"},

    # ==========================================
    # 🇫🇷🇮🇹🇪🇸🇳🇱🇧🇪 4. WEST- & SÜDEUROPA
    # ==========================================
    {"name": "Le Monde (Frankreich)", "url": "https://www.lemonde.fr/rss/une.xml", "cat": "FR/Presse", "weight": 0.90, "bias": "FR-CENTER-LEFT"},
    {"name": "Le Figaro (Frankreich)", "url": "https://www.lefigaro.fr/rss/figaro_actualites.xml", "cat": "FR/Presse", "weight": 0.90, "bias": "FR-CONSERVATIVE"},
    {"name": "France 24 English", "url": "https://www.france24.com/en/rss", "cat": "FR/Medien", "weight": 0.90, "bias": "EU-CENTER"},
    {"name": "ANSA English (Italien)", "url": "https://www.ansa.it/sito/ansait_rss.xml", "cat": "IT/Agentur", "weight": 0.90, "bias": "IT-CENTER"},
    {"name": "Corriere della Sera (Italien)", "url": "https://xml2.corriere.it/rss/esteri.xml", "cat": "IT/Presse", "weight": 0.85, "bias": "IT-CENTER-RIGHT"},
    {"name": "El País (Spanien)", "url": "https://ep00.epimg.net/rss/elpais/portada.xml", "cat": "ES/Presse", "weight": 0.90, "bias": "ES-CENTER-LEFT"},
    {"name": "El Mundo (Spanien)", "url": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml", "cat": "ES/Presse", "weight": 0.85, "bias": "ES-CENTER-RIGHT"},
    {"name": "NOS Nieuws (Niederlande)", "url": "https://feeds.nos.nl/nosnieuws-buitenland", "cat": "NL/Medien", "weight": 0.85, "bias": "NL-CENTER"},
    {"name": "NRC Handelsblad (Niederlande)", "url": "https://www.nrc.nl/rss/", "cat": "NL/Presse", "weight": 0.85, "bias": "NL-LIBERAL"},
    {"name": "VRT NWS (Belgien)", "url": "https://rss.vrt.be/vrtnws_buitenland.xml", "cat": "BE/Medien", "weight": 0.85, "bias": "BE-CENTER"},

    # ==========================================
    # 🇸🇪🇳🇴🇩🇰🇫🇮 5. SKANDINAVIEN & NORDEUROPA
    # ==========================================
    {"name": "SVT Nyheter (Schweden)", "url": "https://www.svt.se/nyheter/rss.xml", "cat": "SE/Medien", "weight": 0.85, "bias": "NORDIC-CENTER"},
    {"name": "NRK Nyheter (Norwegen)", "url": "https://www.nrk.no/nyheter/siste.rss", "cat": "NO/Medien", "weight": 0.85, "bias": "NORDIC-CENTER"},
    {"name": "DR Nyheder (Dänemark)", "url": "https://www.dr.dk/nyheder/service/feeds/allenyheder", "cat": "DK/Medien", "weight": 0.85, "bias": "NORDIC-CENTER"},
    {"name": "Yle News English (Finnland)", "url": "https://feeds.yle.fi/news/v1/recent.rss?publisher=yle-news", "cat": "FI/Medien", "weight": 0.85, "bias": "NORDIC-CENTER"},

    # ==========================================
    # 🇵🇱🇪🇪🇱🇹 6. OSTEUROPA, BALTIKUM & NATO-OSTFLANKE
    # ==========================================
    {"name": "Notes from Poland", "url": "https://notesfrompoland.com/feed/", "cat": "PL/Presse", "weight": 0.85, "bias": "PL-ANALYTICAL"},
    {"name": "ERR News (Estland / Baltikum)", "url": "https://news.err.ee/rss", "cat": "EE/Medien", "weight": 0.85, "bias": "BALTIC-CENTER"},
    {"name": "LRT English (Litauen)", "url": "https://www.lrt.lt/en/news-in-english?rss", "cat": "LT/Medien", "weight": 0.85, "bias": "BALTIC-CENTER"},

    # ==========================================
    # 🏛️🇷🇸🇬🇷🇹🇷 7. BALKAN, SÜDOSTEUROPA & TÜRKEI
    # ==========================================
    {"name": "Balkan Insight (BIRN)", "url": "https://balkaninsight.com/feed/", "cat": "Balkan/OSINT", "weight": 0.90, "bias": "INDEPENDENT-REGIONAL"},
    {"name": "eKathimerini (Griechenland)", "url": "https://www.ekathimerini.com/rss/", "cat": "GR/Presse", "weight": 0.85, "bias": "GR-CENTER-RIGHT"},
    {"name": "B92 Vesti (Serbien)", "url": "https://www.b92.net/info/rss/vesti.xml", "cat": "RS/Presse", "weight": 0.80, "bias": "BALKAN-REGIONAL"},
    {"name": "TRT World (Türkei)", "url": "https://www.trtworld.com/rss/world", "cat": "TR/Medien", "weight": 0.85, "bias": "TR-GOVERNMENT-ALIGNED"},

    # ==========================================
    # 🇯🇵🇰🇷🇹🇼🇦🇺🇳🇿 8. OSTASIEN, TAIWAN & OZEANIEN
    # ==========================================
    {"name": "Focus Taiwan (CNA)", "url": "https://focustaiwan.tw/rss/news.xml", "cat": "TW/Presse", "weight": 0.90, "bias": "TW-CENTER"},
    {"name": "Yonhap News (Südkorea)", "url": "https://en.yna.co.kr/RSS/news.xml", "cat": "KR/Agentur", "weight": 0.90, "bias": "KR-OFFICIAL"},
    {"name": "The Japan Times (Japan)", "url": "https://www.japantimes.co.jp/feed/", "cat": "JP/Presse", "weight": 0.90, "bias": "JP-CENTER-LIBERAL"},
    {"name": "Asahi Shimbun AJW (Japan)", "url": "https://www.asahi.com/ajw/rss/", "cat": "JP/Presse", "weight": 0.85, "bias": "JP-CENTER-LEFT"},
    {"name": "NHK World News (Japan)", "url": "https://www3.nhk.or.jp/rss/news/cat0.xml", "cat": "JP/Medien", "weight": 0.90, "bias": "OFFIZIELL"},
    {"name": "ABC News Australia", "url": "https://www.abc.net.au/news/feed/51120/rss.xml", "cat": "AU/Medien", "weight": 0.90, "bias": "AU-CENTER-LEFT"},
    {"name": "Australian Financial Review", "url": "https://www.afr.com/rss/feed.xml", "cat": "AU/Finanzen", "weight": 0.85, "bias": "AU-BUSINESS-RIGHT"},
    {"name": "RNZ News (Neuseeland)", "url": "https://www.rnz.co.nz/rss/news.xml", "cat": "NZ/Medien", "weight": 0.85, "bias": "NZ-CENTER"},

    # ==========================================
    # 🇮🇩🇸🇬🇻🇳 9. SÜDOSTASIEN & ASEAN
    # ==========================================
    {"name": "Channel NewsAsia (CNA ASEAN)", "url": "https://www.channelnewsasia.com/api/v1/rss-outbound/rssnews/cna-asia.xml", "cat": "ASEAN/Medien", "weight": 0.85, "bias": "ASIA-CENTER"},
    {"name": "The Jakarta Post (Indonesien)", "url": "https://www.thejakartapost.com/rss/paper", "cat": "ID/Presse", "weight": 0.80, "bias": "ID-CENTER"},

    # ==========================================
    # 🇮🇱🇸🇦🇦🇪🇮🇷 10. NAHER OSTEN & GOLFSTAATEN
    # ==========================================
    {"name": "Times of Israel", "url": "https://www.timesofisrael.com/feed/", "cat": "IL/Presse", "weight": 0.85, "bias": "IL-CENTER"},
    {"name": "Jerusalem Post", "url": "https://www.jpost.com/rss/rssfeedsfrontpage.aspx", "cat": "IL/Presse", "weight": 0.85, "bias": "IL-RIGHT"},
    {"name": "The National UAE", "url": "https://www.thenationalnews.com/rss/world.xml", "cat": "UAE/Presse", "weight": 0.80, "bias": "GULF-OFFICIAL"},

    # ==========================================
    # 🇰🇿🇦🇲🇬🇪 11. ZENTRALASIEN & KAUKASUS
    # ==========================================
    {"name": "Eurasianet (Zentralasien/Kaukasus)", "url": "https://eurasianet.org/feed", "cat": "Zentralasien", "weight": 0.85, "bias": "INDEPENDENT-ANALYTICAL"},

    # ==========================================
    # 🌍🇿🇦🇳🇬🇰🇪🇪🇬 12. AFRIKA (KEY PLAYERS)
    # ==========================================
    {"name": "AllAfrica (Google News Aggregator)", "url": "https://news.google.com/rss/search?q=when:24h+site:allafrica.com&hl=en-US&gl=US&ceid=US:en", "cat": "AF/Aggregator", "weight": 0.90, "bias": "AFRICA-PAN-REGIONAL"},
    {"name": "News24 (Südafrika)", "url": "https://feeds.24.com/articles/news24/SouthAfrica/rss", "cat": "ZA/Presse", "weight": 0.85, "bias": "ZA-CENTER-LIBERAL"},
    {"name": "The Guardian Nigeria", "url": "https://guardian.ng/feed/", "cat": "NG/Presse", "weight": 0.85, "bias": "NG-INDEPENDENT"},
    {"name": "Daily Nation (Kenia)", "url": "https://nation.africa/kenya/rss", "cat": "KE/Presse", "weight": 0.85, "bias": "KE-CENTER"},
    {"name": "Ahram Online (Ägypten)", "url": "https://english.ahram.org.eg/rss/World.xml", "cat": "EG/Presse", "weight": 0.80, "bias": "EG-SEMI-OFFICIAL"},
    {"name": "Addis Standard (Äthiopien)", "url": "https://addisstandard.com/feed/", "cat": "ET/Presse", "weight": 0.85, "bias": "ET-INDEPENDENT"},
    {"name": "ISS Africa (Security Studies)", "url": "https://issafrica.org/rss/all", "cat": "AF/ThinkTank", "weight": 0.90, "bias": "VERIFIED-ANALYSIS"},

    # ==========================================
    # 🌎🇲🇽🇦🇷🇧🇷 13. LATEINAMERIKA & MEXIKO
    # ==========================================
    {"name": "MercoPress (Südamerika)", "url": "https://en.mercopress.com/rss/", "cat": "LATAM/Agentur", "weight": 0.85, "bias": "INDEPENDENT-REGIONAL"},
    {"name": "Folha de S.Paulo (Brasilien)", "url": "https://feeds.folha.uol.com.br/mundo/rss091.xml", "cat": "BR/Presse", "weight": 0.85, "bias": "BR-CENTER-LEFT"},
    {"name": "Buenos Aires Times (Argentinien)", "url": "https://www.batimes.com.ar/feed", "cat": "AR/Presse", "weight": 0.80, "bias": "AR-CENTER"},
    {"name": "El Universal (Mexiko)", "url": "https://www.eluniversal.com.mx/rss/mundo.xml", "cat": "MX/Presse", "weight": 0.80, "bias": "MX-CENTER"},
    {"name": "InSight Crime (LATAM OSINT)", "url": "https://insightcrime.org/feed/", "cat": "LATAM/OSINT", "weight": 0.90, "bias": "VERIFIED-ANALYSIS"},

    # ==========================================
    # 🌾 14. LANDWIRTSCHAFT & ERNÄHRUNGSSICHERHEIT
    # ==========================================
    {"name": "Agrarheute (DACH)", "url": "https://www.agrarheute.com/rss.xml", "cat": "Agrar", "weight": 0.90, "bias": "AGRAR-INDUSTRY"},
    {"name": "AgWeb (US & Global Ag)", "url": "https://www.agweb.com/rss/all", "cat": "Agrar", "weight": 0.90, "bias": "AGRAR-MARKETS"},
    {"name": "FAO News & Press Releases", "url": "https://www.fao.org/news/rss-feed/en/", "cat": "Agrar", "weight": 0.95, "bias": "OFFIZIELL"},

    # ==========================================
    # 🌪️ 15. WETTER, KLIMA & EXTREMEREIGNISSE
    # ==========================================
    {"name": "Severe Weather Europe", "url": "https://www.severeweather.eu/feed/", "cat": "Wetter/OSINT", "weight": 0.90, "bias": "METEO-ANALYSIS"},
    {"name": "NOAA News", "url": "https://www.noaa.gov/rss/news.xml", "cat": "Wetter/Klima", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "NOAA National Hurricane Center", "url": "https://www.nhc.noaa.gov/index-at.xml", "cat": "Wetter/Extreme", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "DWD Pressemitteilungen", "url": "https://www.dwd.de/DE/service/rss/pressemitteilungen_rss.xml", "cat": "Wetter/DE", "weight": 0.90, "bias": "OFFIZIELL"},

    # ==========================================
    # ⚕️ 16. MEDIZIN, EPIDEMIOLOGIE & BIO-SECURITY
    # ==========================================
    {"name": "CIDRAP (Biosecurity & Pandemic)", "url": "https://www.cidrap.umn.edu/feed", "cat": "Medizin/OSINT", "weight": 0.95, "bias": "VERIFIED-EPIDEMIOLOGY"},
    {"name": "ProMED-mail", "url": "https://promedmail.org/feed/", "cat": "Medizin/OSINT", "weight": 0.95, "bias": "INDEPENDENT-EPIDEMIOLOGY"},
    {"name": "WHO Newsroom", "url": "https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml", "cat": "Medizin", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "CDC Health Updates", "url": "https://tools.cdc.gov/api/v2/resources/media/132608.rss", "cat": "Medizin", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "ECDC Disease Threats", "url": "https://www.ecdc.europa.eu/en/rss.xml", "cat": "Medizin", "weight": 0.90, "bias": "OFFIZIELL"},

    # ==========================================
    # 🕵️‍♂️ 17. INVESTIGATIV-NETZWERKE & RECHERCHEN
    # ==========================================
    {"name": "OCCRP (Organized Crime & Corruption)", "url": "https://www.occrp.org/en/feed", "cat": "Investigativ Net", "weight": 0.95, "bias": "VERIFIED-INVESTIGATIVE"},
    {"name": "ICIJ (Panama/Pandora Papers)", "url": "https://www.icij.org/feed/", "cat": "Investigativ Net", "weight": 0.95, "bias": "VERIFIED-INVESTIGATIVE"},
    {"name": "ProPublica", "url": "https://www.propublica.org/feeds/propublica/main", "cat": "Investigativ US", "weight": 0.90, "bias": "US-INVESTIGATIVE"},
    {"name": "Disclose (Frankreich)", "url": "https://disclose.ngo/feed/", "cat": "Investigativ FR", "weight": 0.85, "bias": "FR-INVESTIGATIVE"},
    {"name": "Follow the Money (EU)", "url": "https://www.ftm.eu/feed", "cat": "Investigativ EU", "weight": 0.85, "bias": "EU-FINANCIAL-INVESTIGATIVE"},
    {"name": "Meduza English (Russland Exil)", "url": "https://meduza.io/rss/en/all", "cat": "RU/Exil-Investigativ", "weight": 0.90, "bias": "RU-CRITICAL"},

    # ==========================================
    # ⚓ 18. SCHATTENFLOTTEN, SANKTIONEN & ILLIZITE STRÖME
    # ==========================================
    {"name": "C4ADS (Data-Driven Security Analysis)", "url": "https://c4ads.org/feed/", "cat": "Schattennetzwerke", "weight": 0.95, "bias": "VERIFIED-OSINT"},
    {"name": "TankerTrackers Blog", "url": "https://tankertrackers.com/news/feed", "cat": "Schattenflotte", "weight": 0.90, "bias": "MARITIME-OSINT"},
    {"name": "Kharon Risk & Sanctions", "url": "https://www.kharon.com/rss", "cat": "Sanktionen", "weight": 0.90, "bias": "FINANCIAL-INTEL"},

    # ==========================================
    # ⚔️ 19. KONFLIKT-DATEN, MILIZEN & GREY-ZONE (PMCs / NGOs)
    # ==========================================
    {"name": "ACLED (Armed Conflict Location Data)", "url": "https://acleddata.com/feed/", "cat": "Konfliktdaten", "weight": 1.00, "bias": "RAW-DATA-VERIFIED"},
    {"name": "International Crisis Group (ICG)", "url": "https://www.crisisgroup.org/rss.xml", "cat": "NGO/Frühwarnung", "weight": 0.95, "bias": "ANALYTICAL-NEUTRAL"},
    {"name": "Grey Dynamics (Private Intelligence)", "url": "https://greydynamics.com/feed/", "cat": "Private Intel", "weight": 0.85, "bias": "TACTICAL-INTEL"},
    {"name": "Small Arms Survey", "url": "https://www.smallarmssurvey.org/rss.xml", "cat": "Waffenströme", "weight": 0.85, "bias": "VERIFIED-ANALYSIS"},

    # ==========================================
    # ☢️ 20. NUKLEARE PROLIFERATION & RÜSTUNGSKONTROLLE
    # ==========================================
    {"name": "IAEA Press Releases (IAEO)", "url": "https://www.iaea.org/rss/press.xml", "cat": "Nuklear", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "Arms Control Association", "url": "https://www.armscontrol.org/rss.xml", "cat": "Rüstungskontrolle", "weight": 0.90, "bias": "ANALYTICAL"},
    {"name": "CTBTO (Atomtest-Überwachung)", "url": "https://www.ctbto.org/rss.xml", "cat": "Nuklear", "weight": 0.95, "bias": "OFFIZIELL"},

    # ==========================================
    # 💻 21. CYBER-ESPIONAGE & ZERO-DAY WATCHDOGS
    # ==========================================
    {"name": "Citizen Lab (Spyware & Surveillance)", "url": "https://citizenlab.ca/feed/", "cat": "Cyber-Espionage", "weight": 0.95, "bias": "VERIFIED-TECHNICAL"},
    {"name": "Mandiant / Google Threat Intel", "url": "https://cloud.google.com/feeds/blog-threat-intelligence.xml", "cat": "Cyber-Threats", "weight": 0.95, "bias": "CYBER-INTEL"},

    # ==========================================
    # 💰 22. SCHATTENFINANZEN & GELDWÄSCHE
    # ==========================================
    {"name": "FATF-GAFI (Geldwäsche-Monitoring)", "url": "https://www.fatf-gafi.org/en/news.xml", "cat": "Schattenfinanzen", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "Transparency International", "url": "https://www.transparency.org/en/press/rss", "cat": "Korruption", "weight": 0.85, "bias": "NGO-GLOBAL"},

    # ==========================================
    # 💬 23. REDDIT COMMUNITY OSINT FEEDS
    # ==========================================
    {"name": "r/geopolitics", "url": "https://www.reddit.com/r/geopolitics/.rss", "cat": "Community", "weight": 0.80, "bias": "COMMUNITY-ANALYTICAL"},
    {"name": "r/OSINT", "url": "https://www.reddit.com/r/OSINT/.rss", "cat": "Community", "weight": 0.85, "bias": "COMMUNITY-TECHNICAL"},
    {"name": "r/CredibleDefense", "url": "https://www.reddit.com/r/CredibleDefense/.rss", "cat": "Community", "weight": 0.85, "bias": "COMMUNITY-DEFENSE"},
    {"name": "r/LessCredibleDefence", "url": "https://www.reddit.com/r/LessCredibleDefence/.rss", "cat": "Community", "weight": 0.70, "bias": "COMMUNITY-DEFENSE"},
    {"name": "r/Economics", "url": "https://www.reddit.com/r/Economics/.rss", "cat": "Community", "weight": 0.75, "bias": "COMMUNITY-MACRO"},
    {"name": "r/Macroeconomics", "url": "https://www.reddit.com/r/Macroeconomics/.rss", "cat": "Community", "weight": 0.75, "bias": "COMMUNITY-MACRO"},
    {"name": "r/Commodities", "url": "https://www.reddit.com/r/Commodities/.rss", "cat": "Community", "weight": 0.75, "bias": "COMMUNITY-COMMODITIES"},

    # ==========================================
    # 🔍 24. FREIE, ALTERNATIVE & KONTRÄRE MEDIEN
    # ==========================================
    {"name": "Reitschuster", "url": "https://reitschuster.de/feed/", "cat": "Alternativ DE", "weight": 0.80, "bias": "DE-CRITICAL-JOURNALISM"},
    {"name": "Apollo News", "url": "https://apollo-news.net/feed/", "cat": "Debatte DE", "weight": 0.80, "bias": "DE-CONSERVATIVE-LIBERAL"},
    {"name": "Transition News (Schweiz)", "url": "https://transition-news.org/feed", "cat": "Alternativ CH", "weight": 0.80, "bias": "CH-CRITICAL"},
    {"name": "Global Research (Kanada)", "url": "https://www.globalresearch.ca/feed", "cat": "Alternativ Global", "weight": 0.75, "bias": "COUNTER-HEGEMONIC"},
    {"name": "OffGuardian (UK)", "url": "https://off-guardian.org/feed/", "cat": "Alternativ UK", "weight": 0.75, "bias": "CRITICAL-SKEPTIC"},
    {"name": "SouthFront (Militär OSINT)", "url": "https://southfront.press/feed/", "cat": "Militär Alternativ", "weight": 0.75, "bias": "MULTIPOLAR-MILITARY"},
    {"name": "Auf1", "url": "https://auf1.tv/rss", "cat": "Alternativ AT/DE", "weight": 0.70, "bias": "AT-ALTERNATIVE"},
    {"name": "Ansage.org", "url": "https://ansage.org/feed/", "cat": "Debatte DE", "weight": 0.75, "bias": "DE-CRITICAL"},
    {"name": "Scheerpost", "url": "https://scheerpost.com/feed/", "cat": "Investigativ", "weight": 0.80, "bias": "US-LEFT-CRITICAL"},
    {"name": "Naked Capitalism", "url": "https://www.nakedcapitalism.com/feed", "cat": "Makro", "weight": 0.85, "bias": "FINANCIAL-CRITIQUE"},
    {"name": "Consortium News", "url": "https://consortiumnews.com/feed/", "cat": "Investigativ", "weight": 0.80, "bias": "COUNTER-NARRATIVE"},
    {"name": "Glenn Greenwald", "url": "https://greenwald.substack.com/feed", "cat": "Journalismus", "weight": 0.85, "bias": "MEDIA-CRITIQUE"},
    {"name": "Aaron Maté Substack", "url": "https://mate.substack.com/feed", "cat": "Journalismus", "weight": 0.80, "bias": "FOREIGN-POLICY-CRITIQUE"},
    {"name": "The Duran", "url": "https://theduran.com/feed/", "cat": "Geopolitik", "weight": 0.75, "bias": "BRICS-MULTIPOLAR"},
    {"name": "ZeroHedge", "url": "http://feeds.feedburner.com/zerohedge/feed", "cat": "Alternativ", "weight": 0.75, "bias": "CONTRARIAN-FINANCE"},
    {"name": "The Intercept", "url": "https://theintercept.com/feed/?rss", "cat": "Investigativ", "weight": 0.85, "bias": "INVESTIGATIVE-LEFT"},
    {"name": "The Grayzone", "url": "https://thegrayzone.com/feed/", "cat": "Investigativ", "weight": 0.70, "bias": "ANTI-HEGEMONIC"},
    {"name": "Republik (Schweiz)", "url": "https://www.republik.ch/feed", "cat": "Investigativ", "weight": 0.85, "bias": "INDEPENDENT-SWISS"},
    {"name": "MintPress News", "url": "https://www.mintpressnews.com/feed/", "cat": "Alternativ", "weight": 0.70, "bias": "ANTI-IMPERIALIST"},
    {"name": "UnHerd", "url": "https://unherd.com/feed/", "cat": "Debatte", "weight": 0.85, "bias": "UK-CONTRARIAN"},
    {"name": "Antiwar.com", "url": "https://www.antiwar.com/blog/feed/", "cat": "Friedenspolitik", "weight": 0.80, "bias": "NON-INTERVENTIONIST"},
    {"name": "NachDenkSeiten", "url": "https://www.nachdenkseiten.de/?feed=rss2", "cat": "Medienkritik", "weight": 0.80, "bias": "DE-ALTERNATIVE-LEFT"},
    {"name": "Apolut", "url": "https://apolut.net/feed/", "cat": "Alternativ DE", "weight": 0.70, "bias": "DE-ALTERNATIVE"},
    {"name": "Anti-Spiegel", "url": "https://www.anti-spiegel.ru/feed/", "cat": "Alternativ RU/DE", "weight": 0.65, "bias": "PRO-RUSSIA-DE"},
    {"name": "Telepolis", "url": "https://www.telepolis.de/news-atom.xml", "cat": "Magazin DE", "weight": 0.80, "bias": "DE-CRITICAL-TECH"},
    {"name": "Tichys Einblick", "url": "https://www.tichyseinblick.de/feed/", "cat": "Debatte DE", "weight": 0.75, "bias": "DE-CONSERVATIVE"},
    {"name": "Overton Magazin", "url": "https://overton-magazin.de/feed/", "cat": "Geopolitik DE", "weight": 0.80, "bias": "DE-ANALYTICAL"},
    {"name": "Multipolar Magazin", "url": "https://multipolar-magazin.de/feed", "cat": "Geopolitik DE", "weight": 0.75, "bias": "DE-MULTIPOLAR"},
    {"name": "Manova / Rubikon", "url": "https://www.manova.news/artikel.rss", "cat": "Alternativ DE", "weight": 0.70, "bias": "DE-CRITICAL"},
    {"name": "Berliner Tageszeitung", "url": "https://www.berlinertageszeitung.de/feed", "cat": "Medien DE", "weight": 0.70, "bias": "DE-INDEPENDENT"},
    {"name": "Hintergrund Magazin", "url": "https://www.hintergrund.de/feed/", "cat": "Geopolitik DE", "weight": 0.80, "bias": "DE-CRITICAL"},
    {"name": "Moon of Alabama", "url": "https://www.moonofalabama.org/index.rdf", "cat": "Militär-Blog", "weight": 0.80, "bias": "TACTICAL-MILITARY-CRITIQUE"},
    {"name": "Caitlin Johnstone", "url": "https://caitlinjohnstone.com.au/feed/", "cat": "Kolumne", "weight": 0.75, "bias": "INDEPENDENT-OPINION"},

    # ==========================================
    # 🎯 25. PREDICTION MARKETS & REAL-TIME SIGNALS
    # ==========================================
    {"name": "Polymarket Geopolitics & War", "url": "https://news.google.com/rss/search?q=when:24h+%22Polymarket%22+(geopolitics+OR+war+OR+election)&hl=en-US&gl=US&ceid=US:en", "cat": "Prediction Markets", "weight": 0.95, "bias": "CROWD-WISDOM"},
    {"name": "Kalshi Macro Odds", "url": "https://news.google.com/rss/search?q=when:24h+%22Kalshi%22+(odds+OR+fed)&hl=en-US&gl=US&ceid=US:en", "cat": "Prediction Markets", "weight": 0.90, "bias": "CROWD-WISDOM"},
    {"name": "X / Twitter OSINT Live", "url": "https://news.google.com/rss/search?q=when:24h+(site:x.com+OR+site:twitter.com)+%22OSINT%22&hl=en-US&gl=US&ceid=US:en", "cat": "OSINT / X", "weight": 0.85, "bias": "ALTERNATIVE"},

    # ==========================================
    # 🏛️ 26. ZENTRALBANKEN, REGIERUNGEN & STAATLICHE STELLEN
    # ==========================================
    {"name": "Federal Reserve Press", "url": "https://www.federalreserve.gov/feeds/press_all.xml", "cat": "Zentralbank", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "Fed Speeches & Minutes", "url": "https://www.federalreserve.gov/feeds/speeches.xml", "cat": "Zentralbank", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "Atlanta Fed / NY Fed", "url": "https://www.atlantafed.org/rss/gdpnow", "cat": "Makro/Fed", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "EZB (Europ. Zentralbank)", "url": "https://www.ecb.europa.eu/rss/press.html", "cat": "Zentralbank", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "Bank of England (BoE)", "url": "https://www.bankofengland.co.uk/rss/news", "cat": "Zentralbank", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "Schweizerische Nationalbank (SNB)", "url": "https://www.snb.ch/de/service/rss/media_releases.xml", "cat": "Zentralbank", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "Bank of Canada (BoC)", "url": "https://www.bankofcanada.ca/content_type/press-releases/feed/", "cat": "Zentralbank", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "Bank of Japan (BoJ)", "url": "https://www.boj.or.jp/en/rss/release.xml", "cat": "Zentralbank", "weight": 1.00, "bias": "OFFIZIELL"},

    # --- BRICS & Emerging Market Central Banks ---
    {"name": "People's Bank of China (Caixin Alt)", "url": "https://news.google.com/rss/search?q=when:24h+site:caixinglobals.com+PBoC", "cat": "Zentralbank", "weight": 1.00, "bias": "BRICS"},
    {"name": "Reserve Bank of India (RBI)", "url": "https://rbi.org.in/rss/pressreleases.xml", "cat": "Zentralbank", "weight": 0.95, "bias": "BRICS-INDIA"},
    {"name": "Central Bank of Russia (CBR)", "url": "https://www.cbr.ru/eng/rss/RssNews", "cat": "Zentralbank", "weight": 0.95, "bias": "BRICS-RUSSIA"},
    {"name": "Banco Central do Brasil (BCB)", "url": "https://www.bcb.gov.br/api/feed/pt-br/noticias", "cat": "Zentralbank", "weight": 0.90, "bias": "BRICS-LATAM"},
    {"name": "South African Reserve Bank (SARB)", "url": "https://www.resbank.co.za/en/home/newsroom/rss.xml", "cat": "Zentralbank", "weight": 0.85, "bias": "AFRICA-MACRO"},

    # --- Commodity & Regional Key Monetary Authorities ---
    {"name": "Reserve Bank of Australia (RBA)", "url": "https://www.rba.gov.au/rss/rss-cb-media-releases.xml", "cat": "Zentralbank", "weight": 0.90, "bias": "OFFIZIELL"},
    {"name": "Norges Bank (Norwegen / Staatsfonds)", "url": "https://www.norges-bank.no/en/rss/press-releases/", "cat": "Zentralbank", "weight": 0.90, "bias": "OFFIZIELL"},
    {"name": "Sveriges Riksbank (Schweden)", "url": "https://www.riksbank.se/en-gb/rss/press-releases/", "cat": "Zentralbank", "weight": 0.85, "bias": "OFFIZIELL"},
    {"name": "Bank of Korea (BoK)", "url": "https://www.bok.or.kr/eng/bbs/B0000008/rss.do?menuNo=400030", "cat": "Zentralbank", "weight": 0.90, "bias": "OFFIZIELL"},

    # --- Supranationale Finanzorganisationen & Regierungen ---
    {"name": "BIS (Bank f. Intl. Zahlungsverkehr)", "url": "https://www.bis.org/doclist/all.rss", "cat": "Zentralbank", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "IWF (IMF News)", "url": "https://www.imf.org/en/News/rss", "cat": "Intl. Org", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "Weltbank News", "url": "https://www.worldbank.org/en/news/rss", "cat": "Intl. Org", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "OECD Newsroom", "url": "https://www.oecd.org/newsroom/index.xml", "cat": "Intl. Org", "weight": 0.90, "bias": "OFFIZIELL"},
    {"name": "EU-Kommission Press", "url": "https://ec.europa.eu/commission/presscorner/api/rss", "cat": "Regierung/EU", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "Europäischer Rat", "url": "https://www.consilium.europa.eu/en/rss/", "cat": "Regierung/EU", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "White House Briefing", "url": "https://www.whitehouse.gov/briefing-room/feed/", "cat": "Regierung", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "US Dept of State", "url": "https://www.state.gov/rss-feed/press-releases/feed/", "cat": "Diplomatie", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "Schweizer Bundesrat", "url": "https://www.admin.ch/gov/de/start/dokumentation/medienmitteilungen.rss.html", "cat": "Regierung", "weight": 0.90, "bias": "OFFIZIELL"},

    # ==========================================
    # 🚶 27. MIGRATION, VERTREIBUNG & HUMANITÄRE DATEN
    # ==========================================
    {"name": "UNHCR Press Releases", "url": "https://www.unhcr.org/rss/news.xml", "cat": "UNHCR", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "IOM News", "url": "https://www.iom.int/rss.xml", "cat": "IOM", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "ReliefWeb UN OCHA", "url": "https://reliefweb.int/updates/rss.xml", "cat": "Humanitär", "weight": 0.90, "bias": "OFFIZIELL"},
    {"name": "Frontex Alerts", "url": "https://www.frontex.europa.eu/news/rss/", "cat": "Grenzen", "weight": 0.90, "bias": "OFFIZIELL"},

    # ==========================================
    # 📊 28. ENERGIE, ROHSTOFFE, LOGISTIK & ANLEIHESTRESS
    # ==========================================
    {"name": "EIA Petroleum Report", "url": "https://www.eia.gov/rss/petroleum.xml", "cat": "Energie", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "IEA Oil Reports", "url": "https://www.iea.org/rss/news", "cat": "Energie", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "OPEC Monthly Report", "url": "https://www.opec.org/opec_web/en/rss.xml", "cat": "Energie", "weight": 0.90, "bias": "OFFIZIELL"},
    {"name": "Baker Hughes Rig Count", "url": "https://rigcount.bakerhughes.com/rss/rig-count", "cat": "Energie", "weight": 0.85, "bias": "OFFIZIELL"},
    {"name": "AGSI+ Gas Storage", "url": "https://www.gie.eu/feed/", "cat": "Energie", "weight": 0.90, "bias": "OFFIZIELL"},
    {"name": "Freightos Shipping", "url": "https://www.freightos.com/feed/", "cat": "Container", "weight": 0.85, "bias": "LOGISTICS"},
    {"name": "Baltic Dry Index", "url": "https://hellenicshippingnews.com/category/shipping-news/dry-bulk-market/feed/", "cat": "Logistik", "weight": 0.90, "bias": "LOGISTICS"},
    {"name": "MOVE Index / Bonds (MarketWatch)", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories", "cat": "Bond Stress", "weight": 0.90, "bias": "MARKETS"},

    # ==========================================
    # 🛡️ 29. OSINT, MILITÄR, SATELLITEN, CYBER & SEE
    # ==========================================
    {"name": "Oryx OSINT (Google Search)", "url": "https://news.google.com/rss/search?q=when:24h+site:oryxspioenkop.com", "cat": "OSINT / Militär", "weight": 0.90, "bias": "ALTERNATIVE"},
    {"name": "Perun / Covert Cabal", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC36myo2OAn4L0E4Lq94T6tA", "cat": "OSINT / Analyse", "weight": 0.85, "bias": "ANALYTICAL"},
    {"name": "Lloyd's List", "url": "https://lloydslist.maritimeintelligence.informa.com/rss", "cat": "Schifffahrt", "weight": 0.90, "bias": "MARITIME"},
    {"name": "MarineTraffic Blog", "url": "https://www.marinetraffic.com/blog/feed/", "cat": "Marine OSINT", "weight": 0.85, "bias": "MARITIME"},
    {"name": "NASA Natural Hazards", "url": "https://earthobservatory.nasa.gov/feeder/natural_hazards.rss", "cat": "Satellit", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "USGS Earthquakes", "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/5.5_day.atom", "cat": "Seismik", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "GDACS Disaster Alerts", "url": "https://www.gdacs.org/xml/rss.xml", "cat": "Warnsystem", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "ISW (Institute for the Study of War)", "url": "https://www.understandingwar.org/rss.xml", "cat": "Militäranalyse", "weight": 0.85, "bias": "WESTERN"},
    {"name": "US Naval Institute", "url": "https://news.usni.org/feed", "cat": "Marine OSINT", "weight": 0.90, "bias": "WESTERN-DEFENSE"},
    {"name": "Naval News", "url": "https://www.navalnews.com/feed/", "cat": "Schifffahrt", "weight": 0.90, "bias": "WESTERN-DEFENSE"},
    {"name": "War on the Rocks", "url": "https://warontherocks.com/feed/", "cat": "Militäranalyse", "weight": 0.90, "bias": "WESTERN-DEFENSE"},
    {"name": "Bellingcat", "url": "https://www.bellingcat.com/feed/", "cat": "OSINT / Satellit", "weight": 0.90, "bias": "VERIFIED-OSINT"},
    {"name": "Critical Threats", "url": "https://www.criticalthreats.org/rss", "cat": "Militäranalyse", "weight": 0.85, "bias": "WESTERN"},
    {"name": "CISA Cyber Alerts", "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml", "cat": "Cyber / Infrastruktur", "weight": 1.00, "bias": "OFFIZIELL"},
    {"name": "CERT-EU", "url": "https://cert.europa.eu/publications/warnings/feed.xml", "cat": "Cyber / Infrastruktur", "weight": 0.95, "bias": "OFFIZIELL"},
    {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml", "cat": "Cyber", "weight": 0.85, "bias": "CYBER-INDUSTRY"},
    {"name": "Submarine Telecoms", "url": "https://subtelforum.com/feed/", "cat": "Infrastruktur", "weight": 0.85, "bias": "INFRASTRUCTURE"},
    {"name": "Offshore Energy", "url": "https://www.offshore-energy.biz/feed/", "cat": "Infrastruktur", "weight": 0.85, "bias": "ENERGY-INDUSTRY"},
    {"name": "gCaptain Maritime", "url": "https://gcaptain.com/feed/", "cat": "Schifffahrt", "weight": 0.85, "bias": "MARITIME"},
    {"name": "Splash247 Shipping", "url": "https://splash247.com/feed/", "cat": "Schifffahrt", "weight": 0.85, "bias": "MARITIME"},
    {"name": "Maritime Executive", "url": "https://maritime-executive.com/rss", "cat": "Schifffahrt", "weight": 0.85, "bias": "MARITIME"},
    {"name": "Flightradar24 Blog", "url": "https://www.flightradar24.com/blog/feed/", "cat": "Luftfahrt OSINT", "weight": 0.85, "bias": "AVIATION"},

    # ==========================================
    # 🌍 30. WELT-NACHRICHTENAGENTUREN, DIPLOMATIE & BRICS
    # ==========================================
    {"name": "Associated Press (Google Search Feed)", "url": "https://news.google.com/rss/search?q=when:24h+site:apnews.com", "cat": "Agentur", "weight": 0.95, "bias": "CENTER-NEUTRAL"},
    {"name": "Reuters World (Google Search Feed)", "url": "https://news.google.com/rss/search?q=when:24h+site:reuters.com", "cat": "Agentur", "weight": 0.95, "bias": "CENTER-NEUTRAL"},
    {"name": "Agence France-Presse (EN)", "url": "https://www.afp.com/en/news-hub/rss", "cat": "Agentur", "weight": 0.90, "bias": "EU-CENTER"},
    {"name": "Xinhua (Google Search Feed)", "url": "https://news.google.com/rss/search?q=when:24h+site:xinhuanet.com", "cat": "BRICS", "weight": 0.85, "bias": "BRICS-CHINA"},
    {"name": "IRNA / Anadolu Agency", "url": "https://en.irna.ir/rss", "cat": "BRICS", "weight": 0.80, "bias": "BRICS-MIDDLEEAST"},
    {"name": "Kyodo News", "url": "https://english.kyodonews.net/rss/news.xml", "cat": "Agentur", "weight": 0.85, "bias": "ASIA-WESTERN"},
    {"name": "Kremlin News", "url": "http://en.kremlin.ru/rss/news", "cat": "BRICS / RU", "weight": 0.85, "bias": "BRICS-RUSSIA"},
    {"name": "Russ. Aussenministerium", "url": "https://mid.ru/en/rss.php", "cat": "Diplomatie", "weight": 0.85, "bias": "BRICS-RUSSIA"},
    {"name": "CGTN World", "url": "https://www.cgtn.com/xml/rss/news.xml", "cat": "BRICS", "weight": 0.80, "bias": "BRICS-CHINA"},
    {"name": "TASS World", "url": "https://tass.com/rss/v2.xml", "cat": "BRICS", "weight": 0.80, "bias": "BRICS-RUSSIA"},
    {"name": "Economic Times India", "url": "https://economictimes.indiatimes.com/rssfeeds/12216583.cms", "cat": "BRICS / IN", "weight": 0.85, "bias": "BRICS-INDIA"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "cat": "BRICS / Arabisch", "weight": 0.85, "bias": "MIDDLEEAST-GLOBAL"},
    {"name": "South China Morning Post", "url": "https://www.scmp.com/rss/91/feed", "cat": "BRICS / HK", "weight": 0.85, "bias": "BRICS-ASIA"},
    {"name": "The Cradle", "url": "https://thecradle.co/feed", "cat": "Alternative", "weight": 0.80, "bias": "MIDDLEEAST-ALTERNATIVE"},
    {"name": "Asia Times", "url": "https://asiatimes.com/feed/", "cat": "Geopolitik", "weight": 0.85, "bias": "ASIA-ANALYTICAL"},

    # ==========================================
    # 💡 31. THINK TANKS & QUALITÄTSPRESSE
    # ==========================================
    {"name": "Quincy Institute", "url": "https://quincyinst.org/feed/", "cat": "Think Tank", "weight": 0.90, "bias": "REALIST-DIPLOMACY"},
    {"name": "Carnegie Endowment", "url": "https://carnegieendowment.org/rss/solr.xml", "cat": "Think Tank", "weight": 0.90, "bias": "ANALYTICAL"}
]
