# 🎯 OddsJam Integration Setup

## Vue d'ensemble

Intégration complète des notifications OddsJam (Good Odds + Middle) dans le bot Telegram via Tasker.

### 🎯 Types d'opportunités OddsJam

### 1. **Good Odds (Positive EV)**
Single bet avec cote meilleure que la vraie probabilité.

### 2. **Middle Bets**
Paris sur 2 lignes overlapping avec petite perte fréquente MAIS gros gain rare (EV+ long terme).

---

## 🔧 Installation

### 1. Migration Base de Données

```bash
cd /path/to/risk0-bot
python migrations/add_oddsjam_preferences.py
```

Ceci ajoute les colonnes:
- `enable_good_odds` (Boolean, default False)
- `enable_middle` (Boolean, default False)

### 2. Configuration Tasker (Android)

#### Profil Tasker

**Nom:** OddsJam Notifications  
**Event:** Notification  
- **Owner Application:** OddsJam  
- **Title:** `*Alert*` (capture tous les types)

#### Task: Send Good Odds to Bot

**Actions:**
1. **Variable Set**
   - Name: `%notif_title`
   - To: `%evtprm2`

2. **Variable Set**
   - Name: `%notif_text`
   - To: `%evtprm3`

3. **If** `%notif_title ~ *Positive EV Alert*`

4. **HTTP Request**
   - Method: `POST`
   - URL: `https://ton-serveur.com/api/oddsjam/positive_ev`
   - Headers: `Content-Type: application/json`
   - Body:
   ```json
   {
     "title": "%notif_title",
     "text": "%notif_text",
     "timestamp": "%TIMES"
   }
   ```

#### Task: Send Middle to Bot

**Actions:**
1-2. (même que ci-dessus)

3. **Else If** `%notif_title ~ *Middle Alert*`

4. **HTTP Request**
   - Method: `POST`
   - URL: `https://ton-serveur.com/api/oddsjam/middle`
   - Body: (même structure)

5. **End If**

---

## 📱 Utilisation

### Pour les utilisateurs

1. **Activer les notifications** (PREMIUM uniquement)
   - `/settings`
   - Cliquer sur `✨ Good Odds: OFF` pour activer
   - Cliquer sur `🎯 Middle: OFF` pour activer

2. **Recevoir les alertes**
   - Les Good Odds et Middle arrivent automatiquement
   - Format clair avec stakes calculés
   - Boutons directs vers les bookmakers

### Settings dans le bot

```
⚙️ SETTINGS

🎖️ Tier: PREMIUM
⏰ Expires in: 28 days
🌐 Language: English
💰 Default CASHH: $500.00
🎯 Default risk: 5.0%
🔔 Notifications: ✅ Enabled
✨ Good Odds Alerts: ❌ OFF
🎯 Middle Opportunities: ❌ OFF

[💰 Change CASHH]
[🎯 Change Risk]
[🌐 Langue / Language]
[💎 Premium Tiers]
[🔔 Disable]
[✨ Good Odds: OFF]  ← Cliquer pour activer
[🎯 Middle: OFF]     ← Cliquer pour activer
[◀️ Menu]
```

---

## 🧪 Tests

### Test Parsers

```bash
cd /path/to/risk0-bot
python
```

```python
from utils.oddsjam_parser import parse_positive_ev_notification, parse_middle_notification
import json

# Test Good Odds
test_ev = """🚨 Positive EV Alert 3.92% 🚨
Orlando Magic vs New York Knicks [Player Made Threes : Landry Shamet Under 1.5] +125 @ Betsson (Basketball, NBA)"""

result = parse_positive_ev_notification(test_ev)
print(json.dumps(result, indent=2))

# Test Middle
test_middle = """🚨 Middle Alert 3.1% 🚨
Coastal Carolina vs North Dakota [Point Spread : Coastal Carolina +3.5/North Dakota -2] Coastal Carolina +3.5 -132 @ TonyBet, North Dakota -2 +150 @ LeoVegas (Basketball, NCAAB)"""

result = parse_middle_notification(test_middle)
print(json.dumps(result, indent=2))
```

### Test API Endpoints

```bash
# Test Good Odds endpoint
curl -X POST https://ton-serveur.com/api/oddsjam/positive_ev \
  -H "Content-Type: application/json" \
  -d '{
    "title": "🚨 Positive EV Alert 3.92% 🚨",
    "text": "Orlando Magic vs New York Knicks [Player Made Threes : Landry Shamet Under 1.5] +125 @ Betsson (Basketball, NBA)",
    "timestamp": "1234567890"
  }'

# Test Middle endpoint
curl -X POST https://ton-serveur.com/api/oddsjam/middle \
  -H "Content-Type: application/json" \
  -d '{
    "title": "🚨 Middle Alert 3.1% 🚨",
    "text": "Coastal Carolina vs North Dakota [Point Spread : Coastal Carolina +3.5/North Dakota -2] Coastal Carolina +3.5 -132 @ TonyBet, North Dakota -2 +150 @ LeoVegas (Basketball, NCAAB)",
    "timestamp": "1234567890"
  }'
```

---

## 📊 Format des messages

### Good Odds Alert

```
✨ GOOD ODDS ALERT - 3.92% ✨

🏀 Orlando Magic vs New York Knicks
📊 NBA - Player Made Threes
👤 Landry Shamet Under 1.5

💎 OPPORTUNITÉ:
🔶 [Betsson] Under 1.5
Odds: +125
💵 Suggested stake: $500.00

📈 EV+: 3.92%
⚠️ This is NOT an arbitrage - variance applies!

💡 What is this?
The odds are better than the true probability.
Long term = profit, but short term = variance.

[🔶 Betsson]
[💰 I BET ($500.00)]
[⚙️ Settings]
```

### Middle Opportunity

**LA VRAIE DÉFINITION:**
Un middle = overlapping bets avec:
- Petite perte si UN gagne (80-85% du temps)
- GROS gain si LES DEUX gagnent (15-20% du temps)
- EV+ car: (prob_middle × gros_gain) > (prob_no_middle × petite_perte)

**Exemple: LeBron Points**

```
🎯 MIDDLE OPPORTUNITY - 14.0% EV 🎯

🏀 Lakers vs Suns
📊 NBA - Player Points

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 SETUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏀 [DraftKings] LeBron Over 20.5
💵 Miser: $25.50 (-118)
📈 Si gagne → Retour: $47.00

🏀 [FanDuel] LeBron Under 22.5
💵 Miser: $22.00 (+114)
📈 Si gagne → Retour: $47.00

💰 Total misé: $47.50

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 SCÉNARIOS POSSIBLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ Un seul pari gagne (~85% du temps)
   → Profit: -$0.50 ❌

2️⃣ MIDDLE HIT! (~15% du temps)
   → Les DEUX gagnent! 🎯
   → Profit: +$46.50 🚀🚀

💡 Zone middle: Entre 20.5 et 22.5
   → Distance: 2 points
   → Probabilité: ~15%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 EXPECTED VALUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EV moyen: +14.0%
Profit moyen/bet: +$6.65
Sur 100 middles: +$665

Comment?
• 85 fois: perte de $0.50 = -$42.50
• 15 fois: gain de $46.50 = +$697.50
• NET: +$655 ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ C'EST QUOI UN MIDDLE?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ceci N'EST PAS un arbitrage!

Tu peux perdre $0.50 dans 85% des cas.

MAIS si le middle hit (15%):
→ Gain énorme: $46.50

Long terme = EV positif (+14.0%)

C'est comme acheter un billet de loto à EV+!
• Coût: $0.50 (souvent)
• Gain potentiel: $46.50 (rare)
• Mathématiquement profitable!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎲 GESTION RISQUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bankroll minimum: $4,750
Bets minimum: 50-100 pour voir EV

Variance:
• Sur 10 middles: probablement -$5.00
• Sur 100 middles: convergence vers EV (+14.0%)

Tu es comfortable avec:
• Perdre $0.50 souvent?
• Pour chance de gagner $46.50?

Si oui → Fonce!
Si non → Skip ce bet.

[🏀 DraftKings] [🏀 FanDuel]
[💰 I BET]
[⚙️ Settings]
```

---

## 🔐 Sécurité

- ✅ Notifications désactivées par défaut (opt-in)
- ✅ PREMIUM uniquement
- ✅ Filtrage par FREE tier dans les endpoints
- ✅ Parsing sécurisé avec gestion d'erreurs
- ✅ Fallback URLs pour tous les bookmakers

---

## 📝 Notes

### Différences vs Arbitrage

| Feature | Arbitrage | Good Odds | Middle |
|---------|-----------|-----------|--------|
| **Profit garanti?** | ✅ Oui | ❌ Non (variance) | ❌ Non (perte fréquente) |
| **2 paris** | ✅ Oui | ❌ Non (1 seul) | ✅ Oui |
| **EV+** | ✅ Oui | ✅ Oui | ✅ Oui |
| **Risque** | 0% | Variable (100% stake) | Petit (1-5% stake) |
| **Gain rare** | ❌ Non | ❌ Non | ✅ Jackpot si middle hit |
| **Fréquence perte** | Jamais | ~50% | ~80-85% |
| **Taille perte** | N/A | 100% stake | 1-5% total stake |
| **Fun** | 😐 Meh | 😬 Stressant | 🎉 Excitant! |

**Résumé:**
- **Arbitrage** = Profit garanti, pas de risque, boring
- **Good Odds** = Single bet EV+, perte 50% du temps = full stake
- **Middle** = EV+ lottery ticket, petite perte fréquente, gros gain rare

### Pourquoi désactivé par défaut?

1. **Volume**: Good Odds + Middle peuvent générer beaucoup d'alertes
2. **Complexité**: Les users FREE doivent d'abord comprendre l'arbitrage
3. **Éducation**: Besoin de comprendre EV et variance avant d'utiliser

### Évolution future

- [ ] Stats Good Odds / Middle dans `/mystats`
- [ ] Calculateur Middle intégré
- [ ] Historique des opportunities manquées
- [ ] Filtrage par sport/league

---

## 🐛 Troubleshooting

### Les notifications n'arrivent pas

1. Vérifier que l'utilisateur est PREMIUM
2. Vérifier `enable_good_odds` ou `enable_middle` = True
3. Vérifier `notifications_enabled` = True
4. Vérifier que Tasker envoie bien au bon endpoint
5. Regarder les logs du serveur

### Le parsing échoue

1. Vérifier le format exact de la notification OddsJam
2. Tester avec `python test_oddsjam_parser.py`
3. Ajuster les regex si le format a changé

### Les stakes sont incorrects

1. Vérifier `default_bankroll` de l'utilisateur
2. Tester `calculate_middle_stakes()` manuellement
3. Vérifier la conversion American → Decimal odds

---

## ✅ Checklist déploiement

- [x] Migration DB
- [x] Parsers créés
- [x] Formatters créés
- [x] Endpoints API
- [x] Settings UI
- [x] Toggle handlers
- [x] PREMIUM-only filtering
- [ ] Tasker configuré
- [ ] Tests end-to-end
- [ ] Monitoring activé
- [ ] Documentation utilisateur

---

**Made with 🚀 by ZEROR1SK**
