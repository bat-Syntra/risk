# 🌉 Bridge Setup - Nonoriribot → Risk0_bot

## 🎯 Objectif

Recevoir les alertes de **Nonoriribot** et les distribuer automatiquement via **Risk0_bot** à tous tes users.

## ⚡ Setup Rapide (5 minutes)

### 1️⃣ Obtenir API Credentials

Tu dois créer une "application" Telegram pour utiliser ton compte comme bridge.

1. Va sur: **https://my.telegram.org**
2. Login avec ton numéro (+1...)
3. Clique "API development tools"
4. Crée une nouvelle app:
   - App title: "Risk0 Bridge"
   - Short name: "risk0bridge"
   - Platform: Desktop
5. **Sauvegarde:**
   - `api_id` (nombre, ex: 12345678)
   - `api_hash` (string, ex: "abc123def456...")

### 2️⃣ Configurer .env

Ajoute ces lignes dans ton `.env`:

```env
# Bridge Configuration
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abc123def456...
TELEGRAM_PHONE=+15141234567
```

**Note:** Utilise TON numéro de téléphone (celui lié à ton compte Telegram).

### 3️⃣ Installer les dépendances

```bash
# Active ton venv si pas déjà fait
source .venv/bin/activate

# Install telethon
pip install telethon aiohttp
```

### 4️⃣ Test du Bridge

```bash
# Lance le bridge
python bridge.py
```

**Premier lancement:**
1. Il va te demander un code de vérification
2. Check tes messages Telegram (Telegram te l'envoie)
3. Entre le code
4. Si tu as 2FA, entre ton password

Une fois connecté, tu verras:
```
✅ Connecté en tant que: Ton Nom
👂 Écoute les messages de: Nonoriribot
🔗 API Risk0_bot: http://localhost:8080/public/drop
⏳ En attente de messages...
```

### 5️⃣ Test avec un vrai message

Maintenant, quand **Nonoriribot** t'envoie une alerte:
1. ✅ Le bridge la reçoit
2. ✅ Parse automatiquement
3. ✅ Envoie à l'API Risk0_bot
4. ✅ Risk0_bot distribue à tous les users (basé sur leur tier)

## 🔧 Architecture

```
Nonoriribot (8337624633...)
      ↓
  Ton compte Telegram (bridge.py)
      ↓
  API Risk0_bot (/public/drop)
      ↓
  Distribution aux users
      ├─> FREE users (délai 30min, arb >3%)
      ├─> BRONZE users (instant, arb >2%)
      ├─> SILVER users (instant, arb >1%)
      └─> GOLD users (instant, arb >0.5%)
```

## 📊 Fonctionnement du Bridge

### Message reçu de Nonoriribot

```
🚨 Arbitrage Alert 5.16% 🚨
Match: Raptors vs Lakers
League: NBA
Market: Total Points

Outcome 1: Over 200 @ -200 (Betsson)
Outcome 2: Under 200 @ +255 (Coolbet)
```

### Le bridge va:

1. **Parser:**
   - Arb %: 5.16%
   - Match: Raptors vs Lakers
   - Sport: Basketball (détecté depuis "NBA")
   - 2 outcomes avec odds et casinos

2. **Envoyer à l'API:**
   ```json
   {
     "event_id": "arb_1699999999_5.16",
     "arb_percentage": 5.16,
     "match": "Raptors vs Lakers",
     "league": "NBA",
     "sport": "Basketball",
     "outcomes": [...]
   }
   ```

3. **Risk0_bot distribue:**
   - Calcule les stakes pour chaque user
   - Applique les filtres tier (min arb %, délai)
   - Envoie les alertes formatées

## 🚀 Lancer en Production

### Option 1: Screen (Simple)

```bash
# Lance dans un screen
screen -S bridge
python bridge.py

# Détach: Ctrl+A puis D
# Reattach: screen -r bridge
```

### Option 2: Systemd (Recommandé)

Crée `/etc/systemd/system/risk0-bridge.service`:

```ini
[Unit]
Description=Risk0 Bridge - Nonoriribot to Risk0_bot
After=network.target

[Service]
Type=simple
User=ton_user
WorkingDirectory=/path/to/risk0-bot
Environment="PATH=/path/to/risk0-bot/.venv/bin"
ExecStart=/path/to/risk0-bot/.venv/bin/python bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Puis:

```bash
sudo systemctl enable risk0-bridge
sudo systemctl start risk0-bridge
sudo systemctl status risk0-bridge
```

### Option 3: Avec main_new.py

Tu peux aussi lancer le bridge dans le même process que le bot principal. Pour ça, modifie `main_new.py` pour inclure le bridge.

## 📝 Logs

Le bridge affiche:

```
📨 Nouveau message reçu de Nonoriribot
============================================================
🚨 Arbitrage Alert 5.16% 🚨
Match: Raptors vs Lakers
...
============================================================
✅ Message parsé:
   Arbitrage: 5.16%
   Match: Raptors vs Lakers
   Outcomes: 2
✅ Envoyé à Risk0_bot: arb_1699999999_5.16
✅ Alert distribuée aux users!
```

Si erreur:
```
⚠️ Message non parsé (pas une alerte d'arbitrage?)
```

## 🔍 Troubleshooting

### "Phone number is not registered"

Assure-toi que le numéro dans `.env` est celui de TON compte Telegram.

### "API_ID or API_HASH is invalid"

Revérifie sur https://my.telegram.org que tu as bien copié les bonnes valeurs.

### "Cannot connect to Risk0_bot API"

1. Vérifie que `main_new.py` est lancé (port 8080)
2. Check l'URL dans `bridge.py` (ligne 15)

### Le bridge ne reçoit rien

1. Vérifie que tu reçois bien les messages de Nonoriribot dans Telegram
2. Check que le username est correct: "Nonoriribot" (ligne 13 de bridge.py)
3. Regarde les logs du bridge

### Message parsé mais pas distribué

Check les logs de `main_new.py` pour voir si l'API a bien reçu la requête.

## 🎛️ Personnalisation

### Changer le format de parsing

Si Nonoriribot change son format de message, édite la fonction `parse_arbitrage_message()` dans `bridge.py` (ligne 24).

### Changer l'URL de l'API

Si tu deploy sur un serveur distant, change `RISK0_API_URL` dans `bridge.py` (ligne 15):

```python
RISK0_API_URL = "https://ton-serveur.com/public/drop"
```

## ✅ Checklist Finale

- [x] Obtenu API_ID et API_HASH de my.telegram.org
- [x] Ajouté dans `.env`
- [x] Installé telethon
- [x] Lancé `bridge.py` et authentifié
- [x] Reçu au moins 1 message de test
- [x] Message parsé et envoyé à l'API
- [x] Risk0_bot distribue aux users

Une fois tout ça fait, c'est **100% automatique**! 🚀

Le bridge tourne 24/7 et forward automatiquement chaque alerte de Nonoriribot vers tous tes users Risk0_bot.
