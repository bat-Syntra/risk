# 🚀 OPTIMISATIONS PERFORMANCE - DÉLAI 5-15s → <2s

## **Problèmes identifiés dans les logs**

### 1. **API enrichment AVANT duplicate detection** ❌
```python
# main_new.py ligne 1355-1361
d = enrich_alert_with_api(d, 'arbitrage')  # 2-3s gaspillés!
...
# ligne 1376: vérifie duplicate APRÈS
if ev:
    is_duplicate = True
```

**Impact:** 2-3s perdues pour chaque duplicate

### 2. **Double API enrichment** ❌
- Ligne 1355: `/public/drop` enrichit
- Ligne 782: `send_arbitrage_alert_to_users` enrichit ENCORE

**Impact:** 2-3s × 2 = 4-6s perdues

### 3. **Pas de cache pour minor leagues** ❌
```
INFO:utils.odds_enricher:⚠️ Event not found in API: EC Vitória vs Mirassol FC (Brazil - Serie A)
INFO:utils.odds_enricher:⚠️ Event not found in API: Paris FC vs Association Jeunesse Auxerroise (France - Ligue 1)
```

Minor leagues **jamais** dans l'API, mais on check à chaque fois.

**Impact:** 2-3s perdues par call de minor league

### 4. **Processing séquentiel des users** ❌
```python
# main_new.py ligne 810-909
for user in users:  # 8 users traités 1 par 1
    await send_alert_to_user(...)  # ~1s par user
```

**Impact:** 8 users × 1s = **8 secondes minimum**

### 5. **"Failed to save pending calls" répété** ❌
```
WARNING:__main__:⚠️ Failed to save pending calls: Can't get local object 'handle_positive_ev.<locals>.GoodEVCall'
```

Répété 5× par call → ralentissement + spam logs

---

## **Solutions proposées**

### **Optimisation #1: Duplicate detection AVANT API**

**Fichier:** `main_new.py` ligne 1334-1470

```python
@app.post("/public/drop")
async def receive_drop(req: Request):
    d = await req.json()
    eid = d.get("event_id")
    
    # ✅ 1. CHECK DUPLICATE FIRST (avant API enrichment)
    db = SessionLocal()
    is_duplicate = False
    try:
        ev = db.query(DropEvent).filter(DropEvent.event_id == eid).first()
        if ev:
            is_duplicate = True
            print(f"🚨 DUPLICATE event_id: {eid} - Skipping API enrichment")
    finally:
        db.close()
    
    # ✅ 2. ENRICH ONLY IF NEW (pas si duplicate)
    if not is_duplicate:
        try:
            from utils.odds_enricher import enrich_alert_with_api
            d = enrich_alert_with_api(d, 'arbitrage')
            print(f"🔗 Enriched with API: {len(d.get('deep_links', {}))} deep links found")
        except Exception as e:
            print(f"⚠️ Could not enrich with API: {e}")
    
    # Continue with rest...
```

**Gain:** 2-3s par duplicate (70% des calls sont duplicates selon tes logs)

---

### **Optimisation #2: Remove double enrichment**

**Fichier:** `main_new.py` ligne 781-798

```python
async def send_arbitrage_alert_to_users(arb_data: dict):
    # ❌ SUPPRIMER CE BLOC (déjà fait dans /public/drop)
    # if ap >= 3.0:
    #     logger.info(f"Arbitrage {ap}% >= 3%, enriching with API")
    #     enriched = enrich_alert_with_api(arb_data, 'arbitrage')
    
    # ✅ Utiliser directement arb_data (déjà enrichi si nouveau)
    db = SessionLocal()
    ...
```

**Gain:** 2-3s par call

---

### **Optimisation #3: Cache négatif pour minor leagues**

**Fichier:** `utils/odds_enricher.py`

```python
# Cache global des leagues NOT in API (expire après 24h)
from datetime import datetime, timedelta
from typing import Set

_MINOR_LEAGUES_CACHE: Set[str] = set()
_CACHE_EXPIRY = None

def is_minor_league_cached(league: str) -> bool:
    """Check if league is known to NOT be in API"""
    global _CACHE_EXPIRY
    
    # Reset cache daily
    if _CACHE_EXPIRY and datetime.now() > _CACHE_EXPIRY:
        _MINOR_LEAGUES_CACHE.clear()
        _CACHE_EXPIRY = None
    
    if not _CACHE_EXPIRY:
        _CACHE_EXPIRY = datetime.now() + timedelta(hours=24)
    
    # Known minor leagues
    KNOWN_MINORS = {
        'brazil - serie a', 'brazil - serie b',
        'france - ligue 2', 'france - national',
        'argentina - primera b', 'spain - segunda',
        'italy - serie b', 'germany - 2. bundesliga',
        'england - championship', 'england - league one'
    }
    
    league_lower = league.lower().strip()
    
    # Check cache
    if league_lower in _MINOR_LEAGUES_CACHE:
        return True
    
    # Check known list
    if league_lower in KNOWN_MINORS:
        _MINOR_LEAGUES_CACHE.add(league_lower)
        return True
    
    return False


def enrich_alert_with_api(data: Dict, bet_type: str) -> Optional[Dict]:
    """Enrich alert with Odds API data"""
    
    league = data.get('league', '')
    
    # ✅ Skip API call if minor league
    if is_minor_league_cached(league):
        logger.info(f"⚡ CACHE HIT: {league} is minor league, skipping API")
        return data
    
    # Continue with normal API enrichment...
    try:
        result = find_event_in_api(...)
        if not result:
            # Add to cache for next time
            _MINOR_LEAGUES_CACHE.add(league.lower().strip())
            logger.info(f"⚠️ Event not found, added {league} to cache")
    except Exception as e:
        ...
```

**Gain:** 2-3s par call de minor league (~50% des calls)

---

### **Optimisation #4: Parallel user processing**

**Fichier:** `main_new.py` ligne 809-909

```python
async def send_arbitrage_alert_to_users(arb_data: dict):
    ...
    # ✅ Process users IN PARALLEL with asyncio.gather
    
    async def send_to_user_safe(user):
        """Wrapper to send to one user with error handling"""
        try:
            # All the user filtering logic...
            if not user.notifications_enabled:
                return None
            
            if not TierManager.can_view_alert(tier_core, arb_data['arb_percentage']):
                return None
            
            # ... other checks ...
            
            # Send
            await send_alert_to_user(user.telegram_id, tier_core, arb_data)
            return user.telegram_id
        except Exception as e:
            print(f"❌ ERROR: send_to_user_safe failed for {user.telegram_id}: {e}")
            return None
    
    # ✅ PARALLEL: Send to all users at once
    tasks = [send_to_user_safe(user) for user in users]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    sent_count = sum(1 for r in results if r is not None and not isinstance(r, Exception))
    print(f"📊 DEBUG: Sent to {sent_count}/{len(users)} users")
```

**Gain:** 8s → 1-2s (8 users en parallèle au lieu de séquentiel)

---

### **Optimisation #5: Fix "Failed to save pending calls"**

**Fichier:** `main_new.py` → définir GoodEVCall au niveau module

```python
# ❌ AVANT (ligne ~984 - classe locale)
@router.message(F.text.startswith("🎰 Odds Alert"))
async def handle_positive_ev(message: types.Message):
    @dataclass
    class GoodEVCall:  # ❌ Classe LOCALE - pickle fail!
        ...

# ✅ APRÈS: définir au niveau module (ligne ~50)
from dataclasses import dataclass

@dataclass
class GoodEVCall:
    """Good EV call data for pending calls tracking"""
    call_id: str
    data: dict
    user_cash: float

# Dans handle_positive_ev:
async def handle_positive_ev(message: types.Message):
    # Utiliser la classe globale
    good_ev_call = GoodEVCall(...)
```

**Gain:** Élimine le warning répété + fix pickle persistence

---

## **Impact total estimé**

| Optimisation | Gain | Fréquence |
|-------------|------|-----------|
| #1: Duplicate before API | 2-3s | 70% calls |
| #2: Remove double enrichment | 2-3s | 100% calls |
| #3: Minor league cache | 2-3s | 50% calls |
| #4: Parallel users | 6-7s | 100% calls |
| #5: Fix pickle warning | 0.5s | 100% calls |

**TOTAL: 15s → <2s** 🚀

---

## **Priorité d'implémentation**

1. ✅ **#1 & #2** (duplicate + double enrichment) → **Gain immédiat 4-6s**
2. ✅ **#4** (parallel users) → **Gain immédiat 6-7s**
3. ✅ **#3** (cache minor leagues) → **Gain 2-3s sur 50% calls**
4. ✅ **#5** (fix pickle) → **Clean logs + stabilité**
