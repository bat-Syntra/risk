# 📦 Installation Guide - ArbitrageBot Canada

Guide d'installation complet étape par étape.

## 📋 Prerequisites

Avant de commencer, assure-toi d'avoir:

- ✅ Python 3.11 ou supérieur
- ✅ PostgreSQL 14 ou supérieur  
- ✅ Un compte Telegram
- ✅ Git (optionnel)

## 🔧 Step 1: Python & Virtual Environment

### Mac/Linux

```bash
# Vérifier la version de Python
python3 --version

# Si < 3.11, installer avec Homebrew (Mac) ou package manager (Linux)
# Mac:
brew install python@3.11

# Créer le virtual environment
cd risk0-bot
python3 -m venv .venv

# Activer l'environnement
source .venv/bin/activate
```

### Windows

```powershell
# Vérifier la version
python --version

# Créer le virtual environment
cd risk0-bot
python -m venv .venv

# Activer l'environnement
.venv\Scripts\activate
```

Tu devrais voir `(.venv)` dans ton terminal.

## 📦 Step 2: Install Dependencies

```bash
# Avec l'environnement activé
pip install --upgrade pip
pip install -r requirements.txt
```

**Packages installés:**
- aiogram (Telegram bot)
- fastapi + uvicorn (API)
- sqlalchemy (ORM)
- psycopg2-binary (PostgreSQL driver)
- alembic (Database migrations)
- pydantic, pillow, openai, etc.

## 🗄️ Step 3: PostgreSQL Setup

### Installation PostgreSQL

#### Mac (Homebrew)

```bash
brew install postgresql@14
brew services start postgresql@14
```

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

#### Windows

Télécharge et installe depuis: https://www.postgresql.org/download/windows/

### Créer la Database

```bash
# Se connecter à PostgreSQL
psql -U postgres

# Dans psql:
CREATE DATABASE arbitrage_bot;
CREATE USER arbitrage_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE arbitrage_bot TO arbitrage_user;
\q
```

## 🤖 Step 4: Telegram Bot Setup

### Créer le Bot

1. Ouvre Telegram et cherche [@BotFather](https://t.me/botfather)
2. Envoie `/newbot`
3. Suis les instructions:
   - Nom du bot: "ArbitrageBot Canada"
   - Username: "ArbitrageCanadaBot" (doit finir par "bot")
4. **Sauvegarde le TOKEN** reçu (format: `123456789:ABC-DEF...`)

### Obtenir ton Telegram ID

1. Cherche [@userinfobot](https://t.me/userinfobot) sur Telegram
2. Envoie `/start`
3. **Sauvegarde ton ID** (ex: 123456789)

## ⚙️ Step 5: Configuration

### Créer le fichier .env

```bash
# Copier l'exemple
cp .env.example .env

# Éditer avec ton éditeur préféré
nano .env
# ou
code .env  # VS Code
```

### Remplir les variables ESSENTIELLES

```env
# BOT
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF-votre-token-ici
ADMIN_CHAT_ID=123456789  # Ton Telegram ID
ADMIN_IDS=123456789  # Ton Telegram ID (peut être plusieurs, séparés par virgule)

# DATABASE
DATABASE_URL=postgresql://arbitrage_user:your_secure_password@localhost:5432/arbitrage_bot

# OPENAI (optionnel si tu n'utilises pas le email parser)
OPENAI_API_KEY=sk-...
```

### Casino Referral Links (À faire plus tard)

Pour l'instant, laisse les liens par défaut. Tu pourras les mettre à jour quand tu auras tes vrais liens d'affiliation.

## 🗃️ Step 6: Initialize Database

### Méthode Automatique (Recommandée)

Le bot créera automatiquement les tables au premier démarrage:

```bash
# Lance le bot
python main_new.py
```

Le bot va:
1. ✅ Créer toutes les tables automatiquement
2. ✅ Démarrer l'API sur port 8080
3. ✅ Démarrer le bot Telegram

Si tu vois:
```
🚀 Initializing database...
✅ Database initialized
✅ ArbitrageBot Canada - Starting...
```

C'est bon! ✅

### Méthode Alembic (Production)

Pour production, utilise Alembic pour les migrations:

```bash
# Générer la migration initiale
alembic revision --autogenerate -m "Initial schema"

# Appliquer la migration
alembic upgrade head
```

## ✅ Step 7: Test the Bot

### Test Basic Commands

1. Ouvre Telegram
2. Cherche ton bot (ex: @ArbitrageCanadaBot)
3. Envoie `/start`

Tu devrais recevoir le message de bienvenue! 🎉

### Test Admin Panel

1. Envoie `/admin`
2. Tu devrais voir le dashboard admin

Si ça marche, tout est OK! ✅

## 🎰 Step 8: Get Casino Referral Links

**IMPORTANT:** Pour gagner de l'argent avec les referrals, tu DOIS t'inscrire aux programmes d'affiliation.

### Programmes d'Affiliation Majeurs

| Casino | Program URL | Commission |
|--------|-------------|------------|
| BET99 | https://partners.bet99.com | ~30% |
| LeoVegas | https://affiliates.leovegas.com | ~25-40% |
| Betsson | https://betssonaffiliates.com | ~25-35% |
| Coolbet | https://partners.coolbet.com | ~25% |
| Pinnacle | https://affiliates.pinnacle.com | ~25% |
| Sports Interaction | Contacte directement | Variable |

### Processus d'Inscription

1. **Visite le site du programme**
2. **Crée un compte** (infos business requises)
3. **Attends l'approbation** (1-5 jours généralement)
4. **Obtiens ton lien de tracking**

### Ajouter tes Liens

Une fois approuvé:

1. Ouvre `.env`
2. Remplace les liens:
   ```env
   REFERRAL_BETSSON=https://betsson.com?ref=TON_CODE_ICI
   REFERRAL_LEOVEGAS=https://leovegas.com?aff=TON_CODE_ICI
   # etc.
   ```
3. Redémarre le bot:
   ```bash
   # Ctrl+C pour arrêter
   python main_new.py
   ```

## 🚀 Step 9: Deploy to Production (Optionnel)

### Option 1: VPS (Digital Ocean, Linode, etc.)

```bash
# Sur le serveur
git clone ton-repo
cd risk0-bot

# Setup comme ci-dessus
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copier .env avec tes vraies credentials

# Utiliser systemd pour auto-start
sudo nano /etc/systemd/system/arbitragebot.service
```

**arbitragebot.service:**
```ini
[Unit]
Description=ArbitrageBot Canada
After=network.target

[Service]
Type=simple
User=ton_user
WorkingDirectory=/path/to/risk0-bot
Environment="PATH=/path/to/risk0-bot/.venv/bin"
ExecStart=/path/to/risk0-bot/.venv/bin/python main_new.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Activer et démarrer
sudo systemctl enable arbitragebot
sudo systemctl start arbitragebot

# Vérifier status
sudo systemctl status arbitragebot
```

### Option 2: Heroku

```bash
# Installer Heroku CLI
# Créer Procfile
echo "web: python main_new.py" > Procfile

# Deploy
heroku create ton-app-name
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

### Option 3: Docker

```bash
# Créer Dockerfile
docker build -t arbitragebot .
docker run -d --env-file .env arbitragebot
```

## 🔍 Troubleshooting

### Erreur: "Cannot connect to database"

```bash
# Vérifier que PostgreSQL tourne
# Mac:
brew services list

# Ubuntu:
sudo systemctl status postgresql

# Vérifier la connection string dans .env
DATABASE_URL=postgresql://user:password@localhost:5432/arbitrage_bot
```

### Erreur: "Bot token is invalid"

- Vérifie que `TELEGRAM_BOT_TOKEN` dans `.env` est correct
- Pas d'espaces avant/après le token
- Format: `123456789:ABC-DEF...`

### Erreur: "Module not found"

```bash
# Réinstaller les dépendances
pip install -r requirements.txt --force-reinstall
```

### Le bot ne répond pas

1. Vérifie que le bot tourne: `ps aux | grep main_new.py`
2. Vérifie les logs pour erreurs
3. Assure-toi que le bot n'est pas déjà lancé ailleurs

### Database tables not created

```bash
# Forcer la création
python
>>> from database import init_db
>>> init_db()
>>> exit()
```

## 📚 Next Steps

Une fois installé:

1. ✅ **Test toutes les commandes** (/start, /stats, /referral, etc.)
2. ✅ **Ajoute tes referral links** dans `.env`
3. ✅ **Intègre Stripe** pour les paiements (voir README)
4. ✅ **Configure le source bot** pour envoyer les alertes
5. ✅ **Invite des beta testers**
6. ✅ **Lance officiellement!** 🚀

## 💡 Tips

- **Backup ta database** régulièrement
- **Monitor les logs** pour détecter les erreurs
- **Test d'abord en DEV** avant deploy production
- **Garde tes secrets SECRETS** (jamais commit .env)

## 📞 Besoin d'Aide?

Si tu bloques:
1. Check les logs d'erreur
2. Relis ce guide
3. Vérifie le README.md
4. Google l'erreur exacte

Bon courage! 🚀
