# 🔗 Connexion des Bots - Guide Complet

## 📋 Résumé de la Situation

Tu as **2 bots Telegram:**

### 1. Nonoriribot (Bot Source)
- **Token:** `8337624633:AAEHm2Z0LDEw_LjloEG4hJ80QdiGuHzC2xc`
- **Rôle:** Envoie les alertes d'arbitrage
- **Situation actuelle:** Seul toi (ID: 8213628656) reçois les messages

### 2. Risk0_bot (Bot Public)
- **Token:** `7999609044:AAFS0m1ZzPW8mxmmxtb5iDrUTjMVgyPFxhs`
- **Rôle:** Distribue les alertes à tous tes users avec système de tiers
- **Situation actuelle:** Nouveau bot qu'on vient de coder

## 🎯 Objectif

**Nonoriribot** envoie des alertes → **Risk0_bot** les reçoit et distribue automatiquement à tous les users.

## ⚠️ Problème: Les Bots Ne Peuvent Pas Parler Entre Eux

**Important:** L'API Telegram ne permet PAS aux bots de recevoir des messages d'autres bots.

## ✅ Solution: Bridge Script

On utilise **TON compte Telegram** (pas un bot) comme "pont":

```
Nonoriribot → Ton Compte (bridge.py) → Risk0_bot API → Users
```

## 🚀 Configuration Rapide

### Étape 1: Obtenir API Credentials

1. Va sur **https://my.telegram.org**
2. Login avec ton numéro Telegram
3. Clique "API development tools"
4. Crée une app:
   - App title: "Risk0 Bridge"
   - Short name: "risk0bridge"
5. **Note:** `api_id` et `api_hash`

### Étape 2: Configurer .env

Le fichier `.env` est déjà créé avec tes tokens! Il te manque juste:

```env
# Ajoute ces 3 lignes (obtenues de my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abc123...
TELEGRAM_PHONE=+1514...  # Ton numéro Telegram
```

### Étape 3: Lancer les 2 Programmes

**Terminal 1 - Risk0_bot:**
```bash
cd risk0-bot
source .venv/bin/activate
python main_new.py
```

**Terminal 2 - Bridge:**
```bash
cd risk0-bot
source .venv/bin/activate
python bridge.py
```

## 📊 Comment ça Marche

### 1. Message Reçu de Nonoriribot

Exemple:
```
🚨 Arbitrage Alert 5.16% 🚨
Match: Raptors vs Lakers
League: NBA
Market: Total Points

Outcome 1: Over 200 @ -200 (Betsson)
Outcome 2: Under 200 @ +255 (Coolbet)
```

### 2. Bridge Parse et Envoie

```python
# bridge.py détecte le message
# Parse automatiquement:
{
  "arb_percentage": 5.16,
  "match": "Raptors vs Lakers",
  "outcomes": [...]
}

# Envoie à: http://localhost:8080/public/drop
```

### 3. Risk0_bot Distribue

```python
# main_new.py reçoit via /public/drop
# Calcule les stakes pour chaque user
# Applique les filtres tier:

FREE users:
  - ✅ Arb >= 3% → Reçoit avec 30min délai
  - ❌ Arb < 3% → Ne reçoit pas

BRONZE users:
  - ✅ Arb >= 2% → Reçoit immédiatement
  - ❌ Arb < 2% → Ne reçoit pas

SILVER users:
  - ✅ Arb >= 1% → Reçoit immédiatement
  
GOLD users:
  - ✅ Arb >= 0.5% → Reçoit en premier (prioritaire)
```

### 4. Users Reçoivent l'Alerte

Chaque user reçoit un message formaté avec:
- 📊 Arbitrage percentage
- 🏀 Match details
- 💰 Stakes calculés pour leur bankroll
- 🔗 Liens vers les casinos (si BRONZE+)
- 🧮 Bouton calculateur (si BRONZE+)
- ⚠️ Mode RISKED (si SILVER+)

## 🧪 Test Sans Attendre Nonoriribot

```bash
# Lance le bot
python main_new.py

# Dans un autre terminal, simule une alerte
python test_alert.py
```

Tu devrais recevoir l'alerte de test sur ton Telegram! ✅

## 📁 Fichiers Importants

| Fichier | Rôle |
|---------|------|
| `main_new.py` | Bot Risk0 + API |
| `bridge.py` | Écoute Nonoriribot |
| `test_alert.py` | Simule une alerte |
| `.env` | Configuration (tokens, API keys) |
| `QUICK_START.md` | Guide setup rapide |
| `BRIDGE_SETUP.md` | Détails du bridge |

## ✅ Checklist de Vérification

### Configuration
- [x] Token Risk0_bot dans `.env` ✅ (déjà fait)
- [x] Admin ID dans `.env` ✅ (déjà fait)
- [ ] API_ID de my.telegram.org
- [ ] API_HASH de my.telegram.org
- [ ] TELEGRAM_PHONE ton numéro
- [ ] Database PostgreSQL créée

### Installation
- [ ] `pip install -r requirements.txt`
- [ ] Database: `createdb arbitrage_bot`

### Test
- [ ] `python main_new.py` lance sans erreur
- [ ] `python bridge.py` se connecte
- [ ] `/start` sur @Risk0_bot répond
- [ ] `/admin` affiche le dashboard
- [ ] `python test_alert.py` envoie une alerte

### Production
- [ ] Bridge tourne 24/7 (screen ou systemd)
- [ ] Bot tourne 24/7
- [ ] Monitoring actif

## 🔍 Diagnostics

### Bridge ne reçoit rien de Nonoriribot

**Vérifie:**
1. Le bridge est bien connecté (`✅ Connecté en tant que...`)
2. Username correct dans `bridge.py` ligne 13: `"Nonoriribot"`
3. Tu reçois toujours les messages de Nonoriribot dans Telegram

### Alerte parsée mais pas distribuée

**Vérifie:**
1. `main_new.py` tourne bien (check terminal 1)
2. Port 8080 est libre: `lsof -i :8080`
3. Logs de `main_new.py` pour erreurs

### Alerte distribuée mais tu ne la reçois pas

**Vérifie:**
1. Tu as bien fait `/start` sur @Risk0_bot
2. Tes notifications sont activées (`/settings`)
3. Ton tier permet de voir cet arbitrage
4. Tu n'as pas dépassé la limite d'alertes/jour

## 💡 Pro Tips

1. **Lance d'abord `test_alert.py`** pour vérifier que tout marche AVANT d'attendre une vraie alerte

2. **Monitor les logs:**
   ```bash
   # Terminal Risk0_bot
   python main_new.py | tee logs/bot.log
   
   # Terminal Bridge
   python bridge.py | tee logs/bridge.log
   ```

3. **Test avec un 2e compte:**
   - Crée un compte Telegram de test
   - `/start` sur @Risk0_bot
   - Lance `test_alert.py`
   - Vérifie que les 2 comptes reçoivent

4. **Production:**
   ```bash
   # Screen pour garder actif
   screen -S risk0
   python main_new.py
   # Ctrl+A puis D
   
   screen -S bridge
   python bridge.py
   # Ctrl+A puis D
   ```

## 🎯 Ce Qui Va Se Passer Maintenant

1. **Nonoriribot** continue de t'envoyer des alertes (comme avant)
2. **bridge.py** écoute et capte chaque alerte automatiquement
3. **bridge.py** parse et envoie à l'API Risk0_bot
4. **main_new.py** calcule et distribue à TOUS les users (toi + tes futurs users)
5. **Chaque user** reçoit l'alerte selon son tier

## 📞 Questions Fréquentes

### Q: Est-ce que je vais recevoir 2x les alertes?
**A:** Oui, une fois de Nonoriribot (directement) et une fois de Risk0_bot (via le bridge). Tu peux mute Nonoriribot si tu veux.

### Q: Combien de temps avant que ça marche?
**A:** Dès que les 2 programmes sont lancés (main_new.py + bridge.py), c'est actif!

### Q: Si je ferme mon terminal?
**A:** Les programmes s'arrêtent. Utilise `screen` ou `systemd` pour les garder actifs.

### Q: Ça coûte cher en ressources?
**A:** Non, les 2 scripts sont très légers (~50MB RAM total).

### Q: Je peux tester sans casser quelque chose?
**A:** Oui! Utilise `test_alert.py` autant que tu veux.

## 🚀 Ready to Go!

Une fois les 3 variables ajoutées dans `.env` (API_ID, API_HASH, PHONE), tu lances:

```bash
# Terminal 1
python main_new.py

# Terminal 2
python bridge.py

# Terminal 3 (optionnel - pour tester)
python test_alert.py
```

Et c'est PARTI! 🎉

Chaque alerte de Nonoriribot sera automatiquement distribuée à tous tes users Risk0_bot!
