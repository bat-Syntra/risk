# 🔌 ML CALL LOGGER - GUIDE D'INTÉGRATION

**Comment intégrer le logger dans votre code existant**

---

## 🎯 PRINCIPE

**Règle d'or:** Le logging ne doit JAMAIS bloquer ou crasher l'envoi d'alertes!

```
Envoi d'alerte → Log (async, safe) → Continue
                      ↓
                 (Erreur? Bot continue quand même!)
```

---

## 📍 OÙ INTÉGRER?

### **Chercher les endroits où tu envoies des calls:**

```bash
grep -r "send_message.*arbitrage\|arb\|middle\|good.*ev" bot/
```

**Fichiers probables:**
- `bot/handlers.py` - Envoi général d'alertes
- `bot/alert_sender.py` - Si existe
- `bot/bet_handlers.py` - Gestion des bets
- `bot/bet_handlers_ev_middle.py` - Middle & Good EV

---

## 💻 EXEMPLE D'INTÉGRATION

### **AVANT (Code existant):**

```python
async def send_arbitrage_alert(user_id: int, arb_data: dict):
    """Send arbitrage alert to user"""
    
    # Build message
    message = (
        f"🎯 ARBITRAGE ALERT\n"
        f"{arb_data['team_a']} vs {arb_data['team_b']}\n"
        f"ROI: {arb_data['roi']}%\n"
        # ... reste du message
    )
    
    # Send to user
    await bot.send_message(user_id, message)
```

---

### **APRÈS (Avec ML logging):**

```python
async def send_arbitrage_alert(user_id: int, arb_data: dict):
    """Send arbitrage alert to user"""
    
    # Build message
    message = (
        f"🎯 ARBITRAGE ALERT\n"
        f"{arb_data['team_a']} vs {arb_data['team_b']}\n"
        f"ROI: {arb_data['roi']}%\n"
        # ... reste du message
    )
    
    # Send to user
    await bot.send_message(user_id, message)
    
    # 🆕 LOG FOR ML (safe, non-blocking)
    try:
        from utils.safe_call_logger import get_safe_logger
        safe_logger = get_safe_logger()
        
        await safe_logger.log_call_safe(
            call_type='arbitrage',
            sport=arb_data.get('sport', 'Unknown'),
            team_a=arb_data['team_a'],
            team_b=arb_data['team_b'],
            book_a=arb_data['book_a'],
            book_b=arb_data['book_b'],
            odds_a=arb_data['odds_a'],
            odds_b=arb_data['odds_b'],
            roi_percent=arb_data['roi'],
            stake_a=arb_data.get('stake_a', 0),
            stake_b=arb_data.get('stake_b', 0),
            match_date=arb_data.get('match_date'),
            users_notified=1  # Increment for each user
        )
    except Exception as e:
        # Log error but DON'T crash!
        logging.error(f"ML logging failed: {e}")
        pass  # Bot continues normally
```

---

## 🔄 BROADCAST À PLUSIEURS USERS

### **Si tu envoies à plusieurs users à la fois:**

```python
async def broadcast_arbitrage(arb_data: dict, user_ids: list):
    """Send arbitrage to multiple users"""
    
    # Send to all users
    sent_count = 0
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, message)
            sent_count += 1
        except Exception:
            pass  # Skip errors
    
    # 🆕 LOG ONCE with total count
    try:
        from utils.safe_call_logger import get_safe_logger
        safe_logger = get_safe_logger()
        
        await safe_logger.log_call_safe(
            call_type='arbitrage',
            sport=arb_data['sport'],
            team_a=arb_data['team_a'],
            team_b=arb_data['team_b'],
            book_a=arb_data['book_a'],
            book_b=arb_data['book_b'],
            odds_a=arb_data['odds_a'],
            odds_b=arb_data['odds_b'],
            roi_percent=arb_data['roi'],
            stake_a=arb_data['stake_a'],
            stake_b=arb_data['stake_b'],
            users_notified=sent_count  # 🎯 Total users
        )
    except Exception:
        pass  # Ignore logging errors
```

---

## 👆 TRACKER LES CLICKS "I BET"

### **Dans le handler du bouton "I BET":**

```python
@router.callback_query(F.data.startswith("i_bet_"))
async def handle_i_bet(callback: CallbackQuery):
    """User clicked I BET button"""
    
    # Extract call_id from callback data
    call_id = callback.data.replace("i_bet_", "")
    
    # Existing code: save bet, etc.
    # ...
    
    # 🆕 INCREMENT CLICK COUNTER
    try:
        from utils.safe_call_logger import get_safe_logger
        safe_logger = get_safe_logger()
        await safe_logger.increment_click_safe(call_id)
    except Exception:
        pass  # Ignore errors
    
    await callback.answer("✅ Bet tracked!")
```

---

## 🏁 UPDATE RÉSULTAT DU MATCH

### **Dans le questionnaire intelligent:**

```python
async def update_bet_result(bet_id: int, outcome: str, profit: float):
    """Update bet result after match"""
    
    # Existing code: update bet in DB
    # ...
    
    # 🆕 UPDATE ML DATA
    try:
        from utils.safe_call_logger import get_safe_logger
        safe_logger = get_safe_logger()
        
        # Get call_id from bet (if stored)
        call_id = bet_data.get('call_id')
        
        if call_id:
            await safe_logger.update_result_safe(
                call_id=call_id,
                outcome=outcome,  # 'a_won', 'b_won', 'push'
                profit_actual=profit
            )
    except Exception:
        pass  # Ignore errors
```

---

## 🔑 GÉNÉRER CALL_ID

### **Pour tracker les clicks, tu dois avoir le même call_id:**

**Option 1: Générer dans l'alerte**

```python
import hashlib
from datetime import datetime

def generate_call_id(team_a, team_b, book_a, book_b, odds_a, odds_b):
    """Generate unique call ID"""
    unique_string = f"{team_a}_{team_b}_{book_a}_{book_b}_{odds_a}_{odds_b}_{datetime.now().strftime('%Y%m%d%H')}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:16]

# Dans l'envoi d'alerte
call_id = generate_call_id(team_a, team_b, book_a, book_b, odds_a, odds_b)

# Passer call_id dans le bouton
button = InlineKeyboardButton(
    text="✅ I BET",
    callback_data=f"i_bet_{call_id}"
)
```

**Option 2: Récupérer de la DB après insert**

```python
# Le logger retourne automatiquement le call_id
# Tu peux le stocker dans ta table `user_bets`
```

---

## 🎨 EXEMPLE COMPLET

### **Fichier hypothétique `alert_sender.py`:**

```python
from utils.safe_call_logger import get_safe_logger
import hashlib
from datetime import datetime

async def send_arb_to_users(arb, users):
    """
    Send arbitrage to filtered users
    """
    # Generate unique call_id
    call_id = hashlib.md5(
        f"{arb['team_a']}_{arb['team_b']}_{arb['book_a']}_{arb['book_b']}_{arb['odds_a']}_{arb['odds_b']}_{datetime.now().strftime('%Y%m%d%H')}".encode()
    ).hexdigest()[:16]
    
    # Send to all users
    sent_count = 0
    for user in users:
        try:
            message = build_arb_message(arb, call_id)  # Include call_id in button
            await bot.send_message(user.telegram_id, message)
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {user.telegram_id}: {e}")
    
    # Log for ML (safe, won't crash even if fails)
    try:
        safe_logger = get_safe_logger()
        await safe_logger.log_call_safe(
            call_type='arbitrage',
            sport=arb.get('sport', 'Unknown'),
            team_a=arb['team_a'],
            team_b=arb['team_b'],
            book_a=arb['book_a'],
            book_b=arb['book_b'],
            odds_a=arb['odds_a'],
            odds_b=arb['odds_b'],
            roi_percent=arb['roi'],
            stake_a=arb.get('stake_a', 0),
            stake_b=arb.get('stake_b', 0),
            match_date=arb.get('match_date'),
            users_notified=sent_count
        )
        logger.info(f"✅ ML: Logged call {call_id} (sent to {sent_count} users)")
    except Exception as e:
        logger.error(f"⚠️ ML logging failed: {e}")
        # Bot continues normally!
```

---

## ✅ CHECKLIST D'INTÉGRATION

### **Pour chaque type d'alerte:**

- [ ] Identifier la fonction qui envoie l'alerte
- [ ] Ajouter `log_call_safe()` APRÈS l'envoi (pas avant!)
- [ ] Wrapper dans try/except (never crash!)
- [ ] Passer `users_notified` count
- [ ] Générer et stocker `call_id` pour tracking
- [ ] Ajouter `increment_click_safe()` dans bouton "I BET"
- [ ] Ajouter `update_result_safe()` dans questionnaire
- [ ] Tester avec `/ml_test`
- [ ] Vérifier avec `/ml_stats`

---

## 🧪 TESTER L'INTÉGRATION

### **1. Envoyer un call test:**

```python
# Dans ton code, envoyer 1 alerte test
# Vérifier qu'elle arrive normalement
```

### **2. Check DB:**

```bash
sqlite3 arbitrage_bot.db "SELECT * FROM arbitrage_calls ORDER BY sent_at DESC LIMIT 1;"
```

**Résultat attendu:** 1 ligne avec tes données

### **3. Check stats:**

```
/ml_stats
```

**Résultat attendu:**
- Total calls: 1
- Success: 1
- Errors: 0

### **4. Cliquer "I BET":**

Puis check:
```bash
sqlite3 arbitrage_bot.db "SELECT users_clicked FROM arbitrage_calls WHERE call_id='xxx';"
```

**Résultat attendu:** 1 (ou +1 après chaque click)

---

## ⚠️ ERREURS COURANTES

### **Erreur 1: Logger pas initialisé**

```python
# ❌ MAUVAIS
safe_logger = get_safe_logger()  # Crash si pas initialisé

# ✅ BON
try:
    safe_logger = get_safe_logger()
    await safe_logger.log_call_safe(...)
except Exception:
    pass  # Ignore si pas init
```

### **Erreur 2: Bloquer l'envoi**

```python
# ❌ MAUVAIS - Log AVANT envoi
await log_call_safe(...)
await bot.send_message(...)  # Si log crash, message pas envoyé!

# ✅ BON - Log APRÈS envoi
await bot.send_message(...)
try:
    await log_call_safe(...)  # Si crash, message déjà envoyé!
except:
    pass
```

### **Erreur 3: Crash sur erreur**

```python
# ❌ MAUVAIS
safe_logger = get_safe_logger()
await safe_logger.log_call_safe(...)
# Pas de try/except → Crash si erreur!

# ✅ BON
try:
    safe_logger = get_safe_logger()
    await safe_logger.log_call_safe(...)
except Exception as e:
    logger.error(f"ML failed: {e}")
    pass  # Continue!
```

---

## 📊 VÉRIFIER QUE ÇA MARCHE

### **Après 24h d'intégration:**

```sql
-- Nombre de calls
SELECT COUNT(*) FROM arbitrage_calls;
-- Devrait être > 0

-- Distribution par type
SELECT call_type, COUNT(*) 
FROM arbitrage_calls 
GROUP BY call_type;

-- Calls avec clicks
SELECT COUNT(*) 
FROM arbitrage_calls 
WHERE users_clicked > 0;
-- Devrait augmenter avec le temps
```

---

## 💡 TIPS

1. **Toujours logger APRÈS l'envoi**
2. **Toujours wrapper dans try/except**
3. **Ne JAMAIS bloquer sur erreur de logging**
4. **Utiliser `/ml_stats` pour monitorer**
5. **Check ML_TROUBLESHOOTING.md si problèmes**

---

**Une fois intégré, tu collecteras 100+ calls/jour automatiquement!** 📊🤖

---

**Besoin d'aide?**  
1. Check `/ml_stats`  
2. Check ML_TROUBLESHOOTING.md  
3. Vérifier les logs: `tail -f /tmp/bot_auto.log | grep -i "ml"`
