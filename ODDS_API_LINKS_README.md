# 🔗 Système de Liens Deep Link - The Odds API

## Vue d'ensemble

Le bot génère maintenant des **boutons qui ouvrent directement le pari exact** sur le site du bookmaker au lieu de juste la homepage.

### Avant vs Après

**AVANT:**
```
[❄️ Coolbet] → https://www.coolbet.com (homepage)
[🔶 Betsson] → https://www.betsson.com (homepage)
```

**APRÈS:**
```
[❄️ Coolbet] → https://www.coolbet.com/en/sports/...
                 ↳ Ouvre DIRECTEMENT "Paris FC Under 4.5"
[🔶 Betsson] → https://www.betsson.com/en/sports/...
                 ↳ Ouvre DIRECTEMENT "Paris FC Over 4.5"
```

---

## Architecture

### 1. Module `utils/odds_api_links.py`

Contient toute la logique de récupération des liens:

- **`fetch_event_links(sport_key, event_id)`** → Appelle The Odds API avec `includeLinks=true`
- **`find_outcome_link(event_data, bookmaker, market, outcome)`** → Trouve le meilleur lien (3 niveaux)
- **`get_links_for_drop(drop, sport_key, event_id)`** → Interface principale

### 2. Niveaux de liens (du meilleur au pire)

```
Priority 1: outcome.link       ← OPTIMAL! Ouvre le pari exact
Priority 2: market.link        ← Page du marché (ex: "Totals")
Priority 3: bookmaker.link     ← Page de l'événement
Priority 4: Fallback URL       ← Homepage du bookmaker
```

### 3. Bookmakers supportés

**16/18 dans The Odds API:**
- 888sport, bet365, BET99, Betsson, BetVictor, Betway, bwin, Casumo, Coolbet, LeoVegas, Mise-o-jeu, Pinnacle, Proline, Sports Interaction, Stake, TonyBet

**2/18 pas dans API (fallback homepage):**
- iBet, Jackpot.bet

---

## Intégration dans `send_alert_to_user()`

### Code modifié (main_new.py lignes 269-305)

```python
# Try to get deep links from The Odds API
sport_key = arb_data.get('sport_key')  # Ex: 'soccer_france_ligue_one'
event_id_api = arb_data.get('event_id_api')  # ID from The Odds API

# Get links (will use API if available, otherwise fallback)
links = get_links_for_drop(
    arb_data,
    sport_key=sport_key,
    event_id=event_id_api
)

for outcome_data in arb_data['outcomes']:
    casino_name = outcome_data['casino']
    
    # Priority: 1) Deep link from API, 2) Referral link, 3) Fallback
    link = links.get(casino_name)
    if not link:
        link = get_casino_referral_link(casino_name)
    if not link:
        link = get_fallback_url(casino_name)
    
    casino_buttons.append(
        InlineKeyboardButton(
            text=f"{logo} {casino_name}",
            url=link
        )
    )
```

---

## Format des données requises

Pour que le système fonctionne optimalement, le `arb_data` doit contenir:

```python
arb_data = {
    'event_id': 'internal_id_123',  # Ton ID interne
    'event_id_api': 'abc123xyz',    # ID de The Odds API ← NOUVEAU!
    'sport_key': 'soccer_france_ligue_one',  # Key API ← NOUVEAU!
    'match': 'Paris FC vs Toulouse',
    'league': 'Ligue 1',
    'market': 'Total Goals',
    'arb_percentage': 2.5,
    'outcomes': [
        {
            'casino': 'Betsson',
            'outcome': 'Over 4.5',
            'odds': +150
        },
        {
            'casino': 'Coolbet',
            'outcome': 'Under 4.5',
            'odds': -120
        }
    ]
}
```

### Sports keys valides (exemples)

```python
SPORT_KEYS = {
    "Soccer": {
        "France Ligue 1": "soccer_france_ligue_one",
        "France Ligue 2": "soccer_france_ligue_two",
        "EPL": "soccer_epl",
        "La Liga": "soccer_spain_la_liga",
        "Serie A": "soccer_italy_serie_a",
        "Bundesliga": "soccer_germany_bundesliga",
        "Champions League": "soccer_uefa_champs_league",
    },
    "Basketball": {
        "NBA": "basketball_nba",
        "NCAA": "basketball_ncaab",
        "Euroleague": "basketball_euroleague",
    },
    "Hockey": {
        "NHL": "icehockey_nhl",
    },
    "Football": {
        "NFL": "americanfootball_nfl",
        "NCAA": "americanfootball_ncaaf",
    }
}
```

Liste complète: https://the-odds-api.com/sports-odds-data/sports-apis.html

---

## Mapping des marchés

Le système mappe automatiquement tes noms de marché vers les keys API:

```python
"Moneyline" → "h2h"
"Total Goals" → "totals"
"Team Total Corners" → "team_totals"
"Spread" → "spreads"
```

---

## Coût API

### Plan gratuit (500 crédits/mois)
- 1 requête = **25 crédits**
- 500 crédits = **20 requêtes max/mois**

### Recommandations
1. **N'appelle l'API que pour les calls PREMIUM** (edge > 3%)
2. **Cache les résultats** pendant 5 minutes minimum
3. **Utilise fallback URLs** si quota dépassé

### Monitoring
```python
# À ajouter dans odds_api_links.py
import os

API_CALLS_TODAY = 0
MAX_CALLS_PER_DAY = 20  # 500/mois ÷ 25 jours

def fetch_event_links(...):
    global API_CALLS_TODAY
    
    if API_CALLS_TODAY >= MAX_CALLS_PER_DAY:
        logger.warning("API quota reached for today, using fallbacks only")
        return {}
    
    response = requests.get(...)
    API_CALLS_TODAY += 1
    
    # Log remaining credits
    remaining = response.headers.get('x-requests-remaining')
    logger.info(f"API calls today: {API_CALLS_TODAY}, Remaining credits: {remaining}")
```

---

## Testing

### 1. Test manuel avec event ID connu
```python
from utils.odds_api_links import fetch_event_links, find_outcome_link

# Remplace par un vrai event_id
event_data = fetch_event_links(
    sport_key="soccer_france_ligue_one",
    event_id="REAL_EVENT_ID_HERE"
)

print(f"Bookmakers trouvés: {len(event_data.get('bookmakers', []))}")

for book in event_data.get('bookmakers', []):
    print(f"\n{book['title']}")
    print(f"  Event link: {book.get('link', 'None')}")
    
    for market in book.get('markets', []):
        print(f"  Market {market['key']}: {market.get('link', 'None')}")
        
        for outcome in market.get('outcomes', []):
            print(f"    {outcome['name']}: {outcome.get('link', 'None')}")
```

### 2. Test via commande bot
Ajoute dans `main_new.py`:

```python
@dp.message(Command("testlinks"))
async def test_links_command(message: types.Message):
    """Test the deep links system"""
    await message.answer("🔍 Testing Odds API links system...")
    
    # Test avec données fictives
    test_drop = {
        'market': 'Total Goals',
        'outcomes': [
            {'casino': 'Betsson', 'outcome': 'Over 4.5'},
            {'casino': 'Coolbet', 'outcome': 'Under 4.5'}
        ]
    }
    
    # Sans API (fallback only)
    links_fallback = get_links_for_drop(test_drop)
    
    msg = "📊 **Links Test Results**\n\n"
    msg += "**Fallback mode (no API):**\n"
    for book, link in links_fallback.items():
        msg += f"• {book}: {link[:50]}...\n"
    
    # Avec API (si event_id fourni)
    # links_api = get_links_for_drop(test_drop, 'soccer_france_ligue_one', 'EVENT_ID')
    # ...
    
    await message.answer(msg)
```

### 3. Logs à surveiller
```
INFO: Fetching links for event abc123 in sport soccer_france_ligue_one
INFO: Successfully fetched links, 12 bookmakers found
INFO: ✅ Found EXACT outcome link for Betsson - Over 4.5
INFO: ⚠️ Using market link for Coolbet - Under 4.5
WARNING: Bookmaker iBet not in Odds API, using fallback
```

---

## Prochaines étapes

### 1. Ajouter event_id_api et sport_key dans ton parser
Quand tu détectes un arbitrage, récupère ces 2 champs:

```python
# Dans ton système de détection
arb_data = {
    ...
    'event_id_api': event['id'],  # De The Odds API
    'sport_key': event['sport_key'],  # De The Odds API
    ...
}
```

### 2. Implémenter le cache
```python
from datetime import datetime, timedelta
import json

LINKS_CACHE = {}  # {event_id: {'links': {...}, 'expires': datetime}}
CACHE_DURATION = timedelta(minutes=5)

def get_links_for_drop(drop, sport_key, event_id):
    # Check cache first
    cache_key = f"{sport_key}:{event_id}"
    if cache_key in LINKS_CACHE:
        cached = LINKS_CACHE[cache_key]
        if datetime.now() < cached['expires']:
            logger.info("Using cached links")
            return cached['links']
    
    # Fetch fresh
    links = ...  # Existing logic
    
    # Cache it
    LINKS_CACHE[cache_key] = {
        'links': links,
        'expires': datetime.now() + CACHE_DURATION
    }
    
    return links
```

### 3. Upgrade API plan si nécessaire
Si tu envoies > 20 calls/jour avec deep links:
- **Starter:** $30/mois → 10,000 crédits (400 requêtes)
- **Pro:** $70/mois → 25,000 crédits (1,000 requêtes)

---

## FAQ

**Q: Pourquoi parfois j'ai juste la homepage?**
A: 3 raisons possibles:
1. Bookmaker pas dans l'API (iBet, Jackpot.bet)
2. Event pas encore disponible dans l'API
3. Quota API dépassé → fallback automatique

**Q: Comment vérifier si un deep link fonctionne?**
A: Les liens API pointent vers les bonnes pages, mais:
- Certains bookmakers peuvent rediriger
- Liens expirés après le match
- Géo-restrictions selon localisation user

**Q: Puis-je forcer les referral links au lieu des deep links?**
A: Oui, passe `event_id=None` à `get_links_for_drop()`:
```python
links = get_links_for_drop(drop, sport_key=None, event_id=None)
# → Utilisera uniquement les fallback URLs
```

---

## Support

Pour toute question sur l'intégration:
1. Vérifier les logs (`logger.info/warning/error`)
2. Tester avec `/testlinks`
3. Checker la doc API: https://the-odds-api.com/liveapi/guides/v4/

Le système est conçu pour **toujours fonctionner** même si l'API échoue (fallback graceful).
