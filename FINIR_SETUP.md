# ✅ FINIR LE SETUP - 2 Étapes

## 📌 État Actuel

✅ Bot Risk0 tourne (main_new.py)  
⚠️ Bridge pas encore lancé (besoin API credentials)

## 🎯 Ce Qu'il Reste à Faire

### 1️⃣ Bridge Setup (5 min)

**Obtenir API_ID et API_HASH:**

1. Va sur: https://my.telegram.org
2. Login avec ton # Telegram  
3. Clique "API development tools"
4. Crée app (nom: Risk0 Bridge)
5. Copie `api_id` et `api_hash`

**Édite `.env`:**

Ouvre `.env` et remplis lignes 13-15:

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abc123...
TELEGRAM_PHONE=+15141234567
```

**Lance le bridge:**

```bash
# Nouveau terminal (garde l'autre ouvert!)
cd "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/test/risk0-bot"
source .venv/bin/activate
python3 bridge.py
```

Premier lancement:
- Il demande un code → Check Telegram
- Entre le code
- Entre password 2FA si demandé

**Résultat attendu:**
```
✅ Connecté en tant que: Ton Nom
👂 Écoute les messages de: Nonoriribot
⏳ En attente de messages...
```

### 2️⃣ Intégrer Guide `/learn` (Optionnel)

**Étapes:**

1. Les handlers learn sont déjà créés dans `bot/learn_handlers.py`

2. Ajoute l'import dans `main_new.py`:

```python
# Ligne ~21 (après les autres imports)
from bot import handlers, admin_handlers, learn_handlers
```

3. Include le router (ligne ~43):

```python
dp.include_router(handlers.router)
dp.include_router(admin_handlers.router)
dp.include_router(learn_handlers.router)  # ← Ajoute cette ligne
```

4. Redémarre le bot:
   - Ctrl+C dans le terminal du bot
   - Relance: `python3 main_new.py`

**Test:**
- Telegram → `/learn`
- Tu devrais voir le menu du guide!

---

## ✅ Système 100% Automatique

Une fois le bridge lancé:

```
Nonoriribot envoie alerte
      ↓
bridge.py capte (automatique)
      ↓
Parse et envoie à main_new.py
      ↓
Distribution à TOUS les users
```

**Tu ne fais RIEN** - c'est 100% automatique! ⚡

---

## 🧪 Test Maintenant

### Test 1: Bot fonctionne

```
Telegram → Cherche @Risk0_bot → /start
```

Tu devrais recevoir le message de bienvenue ✅

### Test 2: Admin panel

```
/admin
```

Dashboard s'affiche ✅

### Test 3: Guide learn (si intégré)

```
/learn
```

Menu du guide s'affiche ✅

### Test 4: Alerte de test

```bash
# Nouveau terminal
cd "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/test/risk0-bot"
python3 test_alert.py
```

Tu reçois l'alerte! ✅

---

## 📊 Status des Terminaux

Tu devrais avoir **2 terminaux ouverts:**

**Terminal 1 - Risk0_bot:**
```
✅ ArbitrageBot Canada - Starting...
INFO: Uvicorn running on http://0.0.0.0:8080
```

**Terminal 2 - Bridge:**
```
✅ Connecté en tant que: Ton Nom
⏳ En attente de messages...
```

---

## 🎉 Une Fois Terminé

Quand Nonoriribot envoie une alerte:
- ✅ Bridge la capte automatiquement
- ✅ Parse et distribue via Risk0_bot
- ✅ Tous les users reçoivent selon leur tier

**100% AUTOMATIQUE - TU NE FAIS RIEN!** 🚀

---

## 💡 Features Complètes

✅ Bot Telegram opérationnel  
✅ Database SQLite (auto-créée)  
✅ Admin panel `/admin`  
✅ Système de tiers (FREE/BRONZE/SILVER/GOLD)  
✅ Referral system  
✅ Bridge automatique (à lancer)  
✅ Guide `/learn` (à intégrer)  
✅ Calcul SAFE + RISKED modes  
✅ 18 casinos canadiens  

---

## 📞 Besoin d'Aide?

Si le bridge ne se connecte pas:
- Vérifie API_ID et API_HASH dans `.env`
- Format téléphone: `+15141234567` (avec +)
- Supprime `bridge_session.session` et relance

Si le bot ne répond pas:
- Check que `main_new.py` tourne
- Port 8080 libre: `lsof -i :8080`

---

**C'EST PRESQUE FINI!** Il te reste juste à:
1. Remplir les 3 lignes dans `.env`  
2. Lancer `bridge.py`

Et c'est TOUT! 🎉
