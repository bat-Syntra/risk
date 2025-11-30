# ⚡ Quick Start - Risk0_bot

## 🎯 Setup Complet en 10 Minutes

### 1️⃣ Database (2 min)

```bash
# Créer la database PostgreSQL
createdb arbitrage_bot

# Ou si t'as un password:
psql -U postgres
CREATE DATABASE arbitrage_bot;
\q
```

Édite `.env` ligne 9:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/arbitrage_bot
```

### 2️⃣ Dependencies (1 min)

```bash
# Active venv
source .venv/bin/activate  # Mac/Linux
# ou
.venv\Scripts\activate     # Windows

# Install tout
pip install -r requirements.txt
```

### 3️⃣ Bridge Setup (5 min)

**IMPORTANT:** Pour recevoir les alertes de Nonoriribot.

1. Va sur **https://my.telegram.org**
2. Login avec ton # Telegram
3. API development tools → Create app
4. **Copie** `api_id` et `api_hash`

Édite `.env` lignes 12-14:
```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abc123def456...
TELEGRAM_PHONE=+15141234567
```

### 4️⃣ Launch (2 min)

**Terminal 1 - Risk0_bot:**
```bash
python main_new.py
```

Tu devrais voir:
```
🚀 Initializing database...
✅ Database initialized
✅ ArbitrageBot Canada - Starting...
```

**Terminal 2 - Bridge:**
```bash
python bridge.py
```

Premier lancement:
- Entre le code reçu par Telegram
- Entre ton password 2FA (si activé)

Tu devrais voir:
```
✅ Connecté en tant que: Ton Nom
👂 Écoute les messages de: Nonoriribot
⏳ En attente de messages...
```

## ✅ Test

### Test 1: Bot fonctionne

1. Ouvre Telegram
2. Cherche `@Risk0_bot`
3. `/start`
4. Tu devrais recevoir le message de bienvenue!

### Test 2: Admin panel

1. `/admin`
2. Dashboard s'affiche avec stats

### Test 3: Bridge (attends une vraie alerte)

Quand Nonoriribot envoie une alerte:
- Le bridge la capte ✅
- Parse automatiquement ✅
- Envoie à Risk0_bot ✅
- Tu reçois l'alerte! ✅

## 🎛️ Commandes Utiles

### Users
- `/start` - Inscription
- `/help` - Guide
- `/mystats` - Tes stats
- `/subscribe` - Voir les tiers
- `/referral` - Ton lien de parrainage
- `/settings` - Paramètres

### Admin (toi seulement)
- `/admin` - Dashboard complet

## 🔍 Troubleshooting Rapide

### Bot ne répond pas
```bash
# Check si le process tourne
ps aux | grep main_new.py

# Kill et relance
pkill -f main_new.py
python main_new.py
```

### Bridge ne se connecte pas
```bash
# Vérifie tes credentials dans .env
cat .env | grep TELEGRAM_

# Supprime la session et relance
rm bridge_session.session
python bridge.py
```

### Database error
```bash
# Drop et recrée
dropdb arbitrage_bot
createdb arbitrage_bot

# Relance le bot (recrée les tables auto)
python main_new.py
```

## 📊 Architecture Rapide

```
Nonoriribot (source des alertes)
      ↓
bridge.py (ton compte Telegram écoute)
      ↓
main_new.py (Risk0_bot API + Bot Telegram)
      ↓
Users (distribution basée sur tier)
```

## 🎯 Next Steps

### Aujourd'hui
- [x] Setup database ✅
- [x] Lance le bot ✅
- [x] Lance le bridge ✅
- [x] Test avec `/start` ✅

### Cette Semaine
- [ ] Obtiens tes referral links casino
- [ ] Setup Stripe pour paiements
- [ ] Invite des beta testers
- [ ] Monitor les premières alertes

### Plus Tard
- [ ] Deploy sur VPS (DigitalOcean, etc.)
- [ ] Marketing et croissance
- [ ] Optimisations

## 💡 Tips

1. **Garde les 2 terminaux ouverts** (bot + bridge)
2. **Check les logs** pour debug
3. **Teste d'abord en local** avant deploy
4. **Backup ta database** régulièrement

## 🚀 En Production

Pour lancer 24/7:

```bash
# Option 1: Screen
screen -S risk0bot
python main_new.py
# Ctrl+A puis D pour détacher

screen -S bridge
python bridge.py
# Ctrl+A puis D

# Option 2: Systemd (voir BRIDGE_SETUP.md)
```

## 📞 Besoin d'Aide?

1. Check `BRIDGE_SETUP.md` pour détails bridge
2. Check `README_NEW.md` pour documentation complète
3. Check `INSTALLATION.md` pour setup détaillé

Bon lancement! 🎉
