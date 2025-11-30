import os

# Charge le token depuis variable d'environnement TELEGRAM_BOT_TOKEN
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "7999609044:AAFS0m1ZzPW9mxmmxtb5iDrUTjMVgyPFxhs"

# Chat cible par défaut pour recevoir les drops envoyés via l'endpoint
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID") or "0")

# OpenAI (pour extraction IA depuis email)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "SET_ME"
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

# The Odds API (pour deep links casinos)
ODDS_API_KEY = os.getenv("ODDS_API_KEY") or "SET_ME"

# Affiliations (fallback si l'URL n'est pas fournie dans le drop)
AFFILIATES = {
    "leovegas": "https://leovegas.com?aff=RISK0",
    "betvictor": "https://betvictor.com?btag=RISK0",
}

# Données du drop par défaut (MVP autonome)
DEFAULT_EDGE = 2.2  # marge affichée (indicative)
DEFAULT_BET = {
    "player": "Jackson Chourio",
    "over":  {"book": "LeoVegas",  "label": "Over 1.5 hits",  "odds": +250},
    "under": {"book": "BetVictor", "label": "Under 1.5 hits", "odds": -225},
    "event": "Chicago Cubs vs Milwaukee Brewers",
    "kickoff": "2025-10-08T17:08:00-04:00",
}

# Assets (templates/ressources locales)
ASSETS = {
    "base": os.getenv("RISK0_BASE_TEMPLATE", "assets/base_template.png"),
    "logo": os.getenv("RISK0_LOGO", "assets/risk0_logo.png"),
    "font": os.getenv("RISK0_FONT", "assets/Inter-Regular.ttf"),
}
