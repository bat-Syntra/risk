# 🆓 FREE USERS - CHANGEMENTS FINAUX

## ✅ CHANGEMENTS APPLIQUÉS

### **1. Referral System pour FREE** ✅
- **Ancien:** 20% base
- **Nouveau:** 
  - 8% taux de base
  - 20% après 1 direct refer (PERMANENT, garde à vie!)
  
**Affichage FREE:**
```
🎁 YOUR REFERRAL PROGRAM

💰 Current rate: 8% (recurring)
👥 Active directs: 0
➡️ Get 1 direct → 20% forever!
🎟️ FREE Premium at 10 active directs
```

**Après 1 direct:**
```
💰 Current rate: 20% (recurring)
👥 Active directs: 1
✅ 20% rate unlocked! (permanent)
🎟️ FREE Premium at 10 active directs
```

### **2. Good Odds bloqués pour FREE** ✅
- ✅ `enable_good_odds = False` par défaut
- ✅ Désactivé lors du revoke
- ✅ Check tier dans `send_arbitrage_alert_to_users`
- ✅ FREE users ne reçoivent JAMAIS de Good Odds

### **3. Limites FREE activées** ✅
- ✅ 5 calls arbitrage/jour max
- ✅ 2.5% arbitrage max
- ✅ 2h espacement minimum
- ❌ Pas de Good Odds
- ❌ Pas de Middle Bets

---

## 📝 CHANGEMENTS À FAIRE (PROCHAINS)

### **4. Stats complètes bloquées pour FREE** 🔄
**Situation actuelle:** FREE users peuvent voir "📊 Full Stats & Charts"

**À faire:**
```python
# Dans bot/bet_handlers.py ou handlers.py
# Quand FREE click sur Full Stats:
if user.tier == TierLevel.FREE:
    text = (
        "📊 <b>FULL STATS & CHARTS</b>\n\n"
        "🔒 <b>PREMIUM FEATURE</b>\n\n"
        "Accès aux:\n"
        "• Graphiques de profit\n"
        "• Stats détaillées par type\n"
        "• Analyse de performance\n"
        "• ROI par bookmaker\n\n"
        "🚀 Upgrade PREMIUM pour débloquer!"
    )
    # Afficher message + bouton Upgrade
```

### **5. Manual Add Bet autorisé pour FREE** ✅
**Garder accessible** - C'est OK que FREE users puissent tracker manuellement

### **6. Stats globales dans Menu Principal** 🔄
**À afficher pour FREE users dans `/start`:**

```
📣 Calls today: 32  •  📈 Potential: 68.8%
(Stats de TOUS les membres combinés)
```

**Implémentation:**
```python
# Dans handlers.py - start_command et callback_main_menu
# Calculer les stats globales aujourd'hui
from utils.drops_stats import get_today_stats_for_tier

# Total calls sent today (all tiers)
stats_premium = get_today_stats_for_tier(TierLevel.PREMIUM)
stats_free = get_today_stats_for_tier(TierLevel.FREE)

total_calls = stats_premium['calls'] + stats_free['calls']
total_potential = stats_premium['potential_pct'] + stats_free['potential_pct']

# Show in menu
if lang == 'fr':
    stats_line = f"📣 Calls aujourd'hui: {total_calls}  •  📈 Potentiel: {total_potential:.1f}%\n\n"
else:
    stats_line = f"📣 Calls today: {total_calls}  •  📈 Potential: {total_potential:.1f}%\n\n"

# Ajouter avant le help_line dans le message
```

---

## 🧪 TESTS À FAIRE

### **Test Referral FREE:**
1. ✅ FREE user commence à 8%
2. ✅ Réfère 1 personne → passe à 20%
3. ✅ Garde 20% même si la personne devient inactive
4. ✅ Message "✅ 20% rate unlocked! (permanent)"

### **Test Good Odds:**
1. ✅ FREE user NE reçoit JAMAIS de Good Odds
2. ✅ Check logs: `SKIPPED - enable_good_odds = False`
3. ✅ Même si envoyé par API, bloqué par tier check

### **Test Limites:**
1. ✅ 5 calls/jour max
2. ✅ Arb > 2.5% bloqué
3. ✅ 2ème call < 2h bloqué
4. ✅ Logs montrent les raisons de skip

### **Test Stats (à implémenter):**
1. 🔄 FREE click "Full Stats" → message locked + Upgrade button
2. 🔄 Menu principal affiche stats globales pour FREE
3. 🔄 Stats globales update en temps réel

---

## 📊 RÉSUMÉ DES TIERS

| Feature | FREE | PREMIUM |
|---------|------|---------|
| **Referral rate** | 8% → 20% (1 direct) | 20% → 40% (12 directs) |
| **Calls/jour** | 5 max | Illimité |
| **Arb % max** | 2.5% | Illimité |
| **Espacement** | 2h | Temps réel |
| **Good Odds** | ❌ NON | ✅ OUI |
| **Middle Bets** | ❌ NON | ✅ OUI |
| **Full Stats** | ❌ NON (à bloquer) | ✅ OUI |
| **Manual Add Bet** | ✅ OUI | ✅ OUI |
| **Stats globales** | ✅ OUI (à ajouter) | ✅ OUI |

---

## 📂 FICHIERS MODIFIÉS

### **Aujourd'hui:**
1. ✅ `core/referrals.py` - Taux 8% FREE, 20% après 1 direct
2. ✅ `bot/handlers.py` - Affichage referral différent FREE/PREMIUM
3. ✅ `core/tiers.py` - Limites FREE activées
4. ✅ `models/user.py` - `last_alert_at` pour espacement
5. ✅ `main_new.py` - Check espacement + limites
6. ✅ `bot/admin_handlers.py` - Revoke désactive Good Odds/Middle

### **À modifier prochainement:**
1. 🔄 `bot/bet_handlers.py` - Bloquer Full Stats pour FREE
2. 🔄 `bot/handlers.py` - Ajouter stats globales dans menu principal

---

## 💡 NOTES IMPORTANTES

### **Referral 8% → 20%:**
- C'est PERMANENT une fois débloqué
- Même si le referral devient inactif, le referrer garde 20%
- Simple et clair pour FREE users

### **Good Odds check:**
Le système vérifie 3 niveaux:
1. `enable_good_odds` flag dans User (désactivé pour FREE)
2. Tier check dans `send_arbitrage_alert_to_users`
3. API handlers qui persistent Good Odds avec `bet_type='good_ev'`

Tous les 3 niveaux bloquent les FREE users ✅

### **Stats globales:**
Montre à FREE users combien de calls sont envoyés quotidiennement
→ FOMO: "Wow 32 calls aujourd'hui et moi j'en ai que 5!"
→ Incite à upgrade

---

**Status:** ✅ Referral + Limites DONE, 🔄 Stats à implémenter  
**Date:** Nov 26, 2024
