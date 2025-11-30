# ⚡ ACTION IMMÉDIATE - Checklist 10 Minutes

## 🎯 À Faire MAINTENANT (dans l'ordre)

### 1️⃣ Obtenir API Credentials (3 min)

**Action:**
1. Ouvre: https://my.telegram.org
2. Login avec ton numéro Telegram
3. Clique "API development tools"
4. Crée une app (nom: "Risk0 Bridge")
5. **COPIE:**
   - `api_id` (ex: 12345678)
   - `api_hash` (ex: "abc123def...")

### 2️⃣ Éditer .env (1 min)

**Action:**
Ouvre le fichier `.env` et remplis les lignes 9-11:

```env
TELEGRAM_API_ID=12345678           ← Mets ton api_id ici
TELEGRAM_API_HASH=abc123def...     ← Mets ton api_hash ici
TELEGRAM_PHONE=+15141234567        ← Mets ton numéro ici
```

**Sauvegarde le fichier!**

### 3️⃣ Database Setup (2 min)

**Action:**
```bash
# Dans le terminal:
createdb arbitrage_bot
```

Ou si ça marche pas:
```bash
psql -U postgres
CREATE DATABASE arbitrage_bot;
\q
```

Puis édite `.env` ligne 6 si besoin:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/arbitrage_bot
```

### 4️⃣ Install Dependencies (2 min)

**Action:**
```bash
cd risk0-bot
source .venv/bin/activate
pip install -r requirements.txt
```

Attends que tout s'installe...

### 5️⃣ Lancer Risk0_bot (1 min)

**Action:**
```bash
# Dans le même terminal:
python main_new.py
```

**Résultat attendu:**
```
🚀 Initializing database...
✅ Database initialized
✅ ArbitrageBot Canada - Starting...
INFO:     Started server process
```

**Laisse ce terminal ouvert!**

### 6️⃣ Lancer Bridge (1 min)

**Action:**
```bash
# NOUVEAU terminal (Cmd+T / Ctrl+Shift+T):
cd risk0-bot
source .venv/bin/activate
python bridge.py
```

**Premier lancement:**
- Il va demander un code
- Check tes messages Telegram (code reçu de "Telegram")
- Entre le code
- Entre ton password 2FA si demandé

**Résultat attendu:**
```
✅ Connecté en tant que: Ton Nom
👂 Écoute les messages de: Nonoriribot
⏳ En attente de messages...
```

**Laisse ce terminal ouvert aussi!**

## ✅ Vérification

### Test 1: Bot fonctionne

1. Ouvre Telegram
2. Cherche `@Risk0_bot`
3. Tape: `/start`

**Résultat:** Tu reçois le message de bienvenue ✅

### Test 2: Admin panel

1. Tape: `/admin`

**Résultat:** Dashboard s'affiche ✅

### Test 3: Alerte de test

```bash
# NOUVEAU terminal:
cd risk0-bot
source .venv/bin/activate
python test_alert.py
```

**Résultat:** Tu reçois une alerte de test sur Telegram! ✅

## 🎉 C'est Prêt!

Si les 3 tests passent, **TOUT MARCHE!**

Maintenant:
- ✅ Quand **Nonoriribot** t'envoie une alerte
- ✅ Le **bridge** la capte automatiquement
- ✅ **Risk0_bot** la distribue à tous les users

## 📊 Status des Terminaux

Tu devrais avoir **2 terminaux ouverts:**

**Terminal 1 - Risk0_bot:**
```
✅ ArbitrageBot Canada - Starting...
INFO:     Uvicorn running on http://0.0.0.0:8080
```

**Terminal 2 - Bridge:**
```
✅ Connecté en tant que: Ton Nom
⏳ En attente de messages...
```

## 🔍 Si Problème

### "Cannot connect to database"

```bash
# Vérifie que PostgreSQL tourne
brew services list   # Mac
# ou
sudo systemctl status postgresql  # Linux

# Vérifie le DATABASE_URL dans .env
```

### "Invalid phone number"

```bash
# Format du numéro: +1234567890
# Pas d'espaces, pas de tirets
TELEGRAM_PHONE=+15141234567
```

### "Module not found"

```bash
# Réinstalle
pip install -r requirements.txt --force-reinstall
```

### Port 8080 déjà utilisé

```bash
# Trouve qui l'utilise
lsof -i :8080

# Kill le process
kill -9 PID_NUMBER

# Relance
python main_new.py
```

## 🚀 Prochaine Étape

Une fois que **TOUT MARCHE**, tu peux:

1. **Invite des amis** à tester le bot
2. **Attends une vraie alerte** de Nonoriribot
3. **Setup Stripe** pour les paiements (voir README)
4. **Obtiens tes referral links** casino (voir README)

## 💰 Commencer à Gagner

Pour que les users puissent subscribe:

1. Crée compte Stripe
2. Crée 3 produits:
   - Bronze: $29/mois
   - Silver: $79/mois
   - Gold: $199/mois
3. Obtiens les payment links
4. Update `bot/handlers.py` ligne ~380

## 📝 Notes

- **Garde les 2 terminaux ouverts** tant que tu veux que ça marche
- **Pour arrêter:** Ctrl+C dans chaque terminal
- **En production:** Utilise `screen` ou `systemd` (voir QUICK_START.md)

## 📞 Recap

**Fichiers importants:**
- `.env` → Configuration (ÉDITE CELUI-CI!)
- `main_new.py` → Lance le bot
- `bridge.py` → Écoute Nonoriribot
- `test_alert.py` → Test sans attendre

**Commandes:**
```bash
# Terminal 1
python main_new.py

# Terminal 2
python bridge.py

# Terminal 3 (test)
python test_alert.py
```

**Temps total:** ~10 minutes
**Résultat:** Système 100% fonctionnel! 🎉

---

**GO GO GO!** ⚡
