# 🆓 FREE TIER - LIMITATIONS ACTIVES

## ✅ LIMITES APPLIQUÉES

### **1. CALLS ARBITRAGE**
- ✅ **Maximum 5 calls par jour**
- ✅ **Maximum 2.5% d'arbitrage** (pas de calls "fous" à 3%+)
- ✅ **Espacement minimum: 2 heures entre chaque call**
- ✅ En temps réel (pas de délai)

### **2. GOOD ODDS (+EV)**
- ❌ **PAS D'ACCÈS** pour FREE
- ✅ `enable_good_odds = False` par défaut
- ✅ Désactivé automatiquement lors du revoke vers FREE

### **3. MIDDLE BETS**
- ❌ **PAS D'ACCÈS** pour FREE
- ✅ `enable_middle = False` par défaut
- ✅ Désactivé automatiquement lors du revoke vers FREE

---

## 📊 COMPARAISON FREE vs PREMIUM

| Feature | FREE | PREMIUM |
|---------|------|---------|
| **Calls Arbitrage/jour** | 5 max | Illimité |
| **Arb % maximum** | 2.5% | Illimité |
| **Espacement** | 2h minimum | Temps réel |
| **Good Odds (+EV)** | ❌ NON | ✅ OUI |
| **Middle Bets** | ❌ NON | ✅ OUI |
| **Mode RISKED** | ❌ NON | ✅ OUI |
| **Calculateur** | ❌ Basique | ✅ Avancé |
| **Statistiques** | ❌ NON | ✅ OUI |

---

## 🔧 IMPLÉMENTATION TECHNIQUE

### **Fichiers modifiés:**

1. **`core/tiers.py`**
   ```python
   TierLevel.FREE: {
       "max_alerts_per_day": 5,          # 5 calls max
       "max_arb_percentage": 2.5,        # 2.5% max
       "min_spacing_minutes": 120,       # 2h entre calls
   }
   ```

2. **`models/user.py`**
   - ✅ Ajouté `last_alert_at` timestamp
   - ✅ Mis à jour `increment_alert_count()` pour tracker le timestamp

3. **`main_new.py`**
   - ✅ Check espacement de 2h pour FREE avant envoi
   - ✅ Check limite quotidienne de 5 calls
   - ✅ Check arb% ≤ 2.5%

4. **`bot/admin_handlers.py`**
   - ✅ Revoke vers FREE désactive `enable_good_odds` et `enable_middle`

---

## 🧪 TESTS

### **Scénario 1: Utilisateur FREE reçoit des calls**

**Call 1 - 10:00 AM - 1.5% arb:**
- ✅ PASSÉ (< 2.5%, 0/5 calls aujourd'hui)
- Envoyé!

**Call 2 - 10:30 AM - 2.0% arb:**
- ❌ BLOQUÉ (< 2h depuis dernier call)
- Message: `SKIPPED - spacing limit (wait 90min more)`

**Call 3 - 12:05 PM - 2.2% arb:**
- ✅ PASSÉ (> 2h depuis 10:00, < 2.5%, 1/5 calls)
- Envoyé!

**Call 4 - 2:10 PM - 3.5% arb:**
- ❌ BLOQUÉ (> 2.5% arbitrage)
- Message: `SKIPPED - arb 3.5% not allowed for tier FREE`

**Appels 5-8:** ✅ Envoyés si respectent critères

**Call 9 - 8:00 PM - 1.8% arb:**
- ❌ BLOQUÉ (5/5 calls atteints)
- Message: `SKIPPED - daily limit reached (5/5)`

---

### **Scénario 2: Good Odds envoyé**

**Utilisateur FREE:**
- ❌ JAMAIS reçu (enable_good_odds = False)

**Utilisateur PREMIUM révoqué vers FREE:**
- ✅ `enable_good_odds` mis à False automatiquement
- ❌ Ne recevra plus de Good Odds

---

## 📝 MIGRATION DB

```bash
python3 migrations/add_last_alert_at.py
```

Ajoute la colonne `last_alert_at` pour tracker le dernier envoi.

---

## ⚠️ POUR LES UTILISATEURS EXISTANTS

**Problème:** Utilisateurs révoqués AVANT le fix continuent à recevoir Good Odds/Middle.

**Solution:** Re-revoke tous les FREE users:

```sql
UPDATE users 
SET enable_good_odds = 0, enable_middle = 0 
WHERE tier = 'free';
```

**OU** dans admin panel:
1. Chercher chaque FREE user
2. Cliquer "⬇️ Revoke FREE" encore
3. Cela désactivera Good Odds + Middle

---

## 🚀 RÉSULTAT ATTENDU

### **Utilisateur FREE:**
- Reçoit **maximum 5 calls arbitrage par jour**
- **Seulement arbs ≤ 2.5%**
- **Espacés d'au moins 2 heures**
- **JAMAIS de Good Odds ni Middle**

### **Utilisateur PREMIUM:**
- Calls illimités
- Tous les arb%
- Temps réel
- Accès Good Odds + Middle

---

## 🔍 DEBUG LOGS

Quand un FREE user est skip, tu verras dans les logs:

```
🔍 DEBUG: User 8004919557 SKIPPED - arb 3.57% not allowed for tier FREE
```

Ou:

```
🔍 DEBUG: User 8004919557 SKIPPED - spacing limit (wait 85min more)
```

Ou:

```
🔍 DEBUG: User 8004919557 SKIPPED - daily limit reached (5/5)
```

---

**Date:** Nov 26, 2024  
**Status:** ✅ ACTIF  
**Version:** 1.0
