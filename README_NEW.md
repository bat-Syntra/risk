# 🎰 ArbitrageBot Canada

Système complet d'arbitrage betting pour le marché Canadien/Québécois avec système de tiers (FREE/BRONZE/SILVER/GOLD), programme referral, et admin panel Telegram.

## 📋 Table des Matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Système de Tiers](#système-de-tiers)
- [Programme Referral](#programme-referral)
- [Admin Panel](#admin-panel)
- [API Endpoints](#api-endpoints)
- [Base de Données](#base-de-données)

## ✨ Fonctionnalités

### 🎯 Core Features

- **Arbitrage automatique** - Parsing des alertes du bot source
- **Calcul SAFE mode** - Profit garanti via arbitrage
- **Calcul RISKED mode** - High risk/reward pour utilisateurs avancés
- **Multi-casino** - Support de 18 casinos canadiens
- **Liens referral** - Intégration automatique des liens d'affiliation

### 🎖️ Système de Tiers

| Tier | Prix | Délai | Min Arb % | Features |
|------|------|-------|-----------|----------|
| ⚪ **FREE** | Gratuit | 30 min | 3% | 5 alertes/jour |
| 🥉 **BRONZE** | $29/mois | 0 min | 2% | Alertes illimitées, calculateur |
| 🥈 **SILVER** | $79/mois | 0 min | 1% | + Mode RISKED, stats avancées |
| 🥇 **GOLD** | $199/mois | 0 min | 0.5% | + Alertes prioritaires, API access |

### 🎁 Programme Referral

- **20% commission récurrente** (Tier 1 - directs)
- **10% commission récurrente** (Tier 2 - indirects)
- **Bonus GOLD** - 2x les commissions pour tier GOLD
- Tracking automatique des commissions

### 🛠️ Admin Panel (100% Telegram)

- Dashboard avec stats temps réel
- Gestion des users (pagination, recherche)
- Broadcast ciblé par tier
- Stats détaillées (revenue, croissance, etc.)

## 🏗️ Architecture

```
risk0-bot/
├── main_new.py              # Point d'entrée principal
├── config.py                # Configuration
├── database.py              # Database setup
│
├── models/                  # SQLAlchemy models
│   ├── user.py             # User + tiers
│   ├── referral.py         # Referral tracking
│   └── bet.py              # Bet history
│
├── core/                    # Business logic
│   ├── calculator.py       # Arbitrage calculations
│   ├── parser.py           # Message parsing
│   ├── tiers.py            # Tier management
│   ├── referrals.py        # Referral system
│   └── casinos.py          # Casino config + referrals
│
├── bot/                     # Telegram bot
│   ├── handlers.py         # User commands
│   └── admin_handlers.py   # Admin panel
│
└── utils/                   # Utilities (existing)
    ├── odds.py
    ├── parser_ai.py
    ├── image_card.py
    └── memory.py
```

## 🚀 Installation

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Telegram Bot Token

### 2. Clone & Setup

```bash
# Clone repository
cd risk0-bot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb arbitrage_bot

# Or with psql:
psql -U postgres
CREATE DATABASE arbitrage_bot;
\q
```

### 4. Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit .env with your values
nano .env
```

**Required variables:**

```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ADMIN_CHAT_ID=your_telegram_id
ADMIN_IDS=your_telegram_id,other_admin_id
DATABASE_URL=postgresql://user:password@localhost:5432/arbitrage_bot
```

### 5. Initialize Database

```bash
# Run the bot once to create tables
python main_new.py

# Tables will be created automatically via init_db()
```

## ⚙️ Configuration

### 📧 Casino Referral Links

**IMPORTANT:** You need to sign up for affiliate programs and get your referral links.

1. Visit each casino's affiliate program:
   - BET99: https://partners.bet99.com
   - LeoVegas: https://affiliates.leovegas.com
   - Betsson: https://betssonaffiliates.com
   - Coolbet: https://partners.coolbet.com
   - Pinnacle: https://affiliates.pinnacle.com
   - etc.

2. Add your links to `.env`:
   ```env
   REFERRAL_BETSSON=https://betsson.com?ref=YOUR_CODE
   REFERRAL_LEOVEGAS=https://leovegas.com?aff=YOUR_CODE
   # ... etc
   ```

3. Or update directly in `core/casinos.py`

### 🤖 Telegram Bot Setup

1. Create bot with [@BotFather](https://t.me/botfather)
2. Get your bot token
3. Get your Telegram ID (use [@userinfobot](https://t.me/userinfobot))
4. Add to `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
   ADMIN_IDS=123456789
   ```

### 💳 Payment Integration (TODO)

The bot has placeholders for Stripe integration. To enable payments:

1. Create Stripe account: https://stripe.com
2. Create products for each tier (Bronze $29, Silver $79, Gold $199)
3. Get payment links or use Stripe API
4. Update `bot/handlers.py` in `callback_buy_tier()` function

## 📱 Utilisation

### Start the Bot

```bash
python main_new.py
```

The bot will:
- ✅ Initialize database
- ✅ Start FastAPI server (port 8080)
- ✅ Start Telegram bot polling

### User Commands

| Command | Description |
|---------|-------------|
| `/start` | Démarrer le bot / S'inscrire |
| `/help` | Afficher l'aide complète |
| `/mystats` | Voir ses statistiques |
| `/subscribe` | Voir les tiers premium |
| `/referral` | Son lien de parrainage |
| `/settings` | Paramètres (bankroll, risk) |

### Admin Commands

| Command | Description |
|---------|-------------|
| `/admin` | Ouvrir le admin panel |

**Admin Panel Features:**
- 📊 Dashboard (users, revenue, stats)
- 👥 Liste users avec pagination
- 📢 Broadcast par tier
- 🔍 Recherche users
- 📈 Stats détaillées

## 🎖️ Système de Tiers

### FREE Tier (Gratuit)

- 5 alertes par jour
- Délai de 30 minutes
- Arbitrages >3% seulement
- Pas de calculateur
- Pas de liens referral

### BRONZE Tier ($29/mois)

- Alertes illimitées
- Temps réel (0 délai)
- Arbitrages >2%
- Calculateur de stakes
- Liens referral intégrés

### SILVER Tier ($79/mois)

- Tout BRONZE +
- Arbitrages >1%
- Mode RISKED (high risk/reward)
- Stats avancées
- Settings de risk custom

### GOLD Tier ($199/mois)

- Tout SILVER +
- Arbitrages >0.5%
- Alertes prioritaires (reçues en premier)
- Accès API
- Support VIP
- Bonus referral x2 (40% commission)

## 🎁 Programme Referral

### Comment ça marche?

1. **Chaque user reçoit un code unique** (ex: `ABC12DEF`)
2. **Lien de parrainage:** `https://t.me/YourBot?start=ABC12DEF`
3. **Partage le lien** à ses amis
4. **Commission automatique** quand l'ami subscribe

### Structure de Commission

```
User A (Original) 
  └─> User B (Tier 1)    → 20% commission pour A
       └─> User C (Tier 2) → 10% commission pour A
                           → 20% commission pour B
```

**Exemple:**
- User B subscribe à BRONZE ($29/mois)
- User A gagne: $5.80/mois (20% de $29)
- Si User C subscribe à SILVER ($79/mois):
  - User B gagne: $15.80/mois (20%)
  - User A gagne: $7.90/mois (10%)

### Commissions Récurrentes

Les commissions sont **récurrentes** - payées chaque mois tant que le user reste subscribed.

## 🛠️ Admin Panel

### Accès

Seuls les admins (définis dans `ADMIN_IDS`) peuvent accéder au panel.

```bash
/admin
```

### Dashboard

Affiche:
- 👥 Total users (par tier)
- 💰 Revenue mensuel/annuel
- 📈 Croissance (nouveaux users)
- 🎁 Total commissions
- 💎 Profit total des users

### Gestion Users

- **Liste paginée** (10 users par page)
- **Recherche** par username ou telegram ID
- **Détails complets** de chaque user
- **Actions:** Change tier, ban, message direct

### Broadcast

Envoie un message à:
- Tous les users
- Un tier spécifique (FREE/BRONZE/SILVER/GOLD)

Le système:
1. Demande la cible
2. Admin envoie le message
3. Distribution automatique avec tracking

## 🔌 API Endpoints

### POST `/public/drop`

Receive arbitrage drop from external source.

**Request:**
```json
{
  "event_id": "abc123",
  "arb_percentage": 5.16,
  "match": "Team A vs Team B",
  "market": "Total Points",
  "outcomes": [
    {"outcome": "Over 200", "odds": -200, "casino": "Betsson"},
    {"outcome": "Under 200", "odds": 255, "casino": "Coolbet"}
  ],
  "sport": "Basketball",
  "league": "NBA"
}
```

**Response:**
```json
{"ok": true}
```

### POST `/public/email`

Receive email notification from source bot.

**Request:**
```json
{
  "subject": "Arbitrage Bet Notification: ...",
  "body": "🚨 Arbitrage Alert 5.16% 🚨\n..."
}
```

**Response:**
```json
{"ok": true, "event_id": "abc123"}
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{"status": "ok", "timestamp": "2025-01-01T12:00:00"}
```

## 💾 Base de Données

### Models

**User**
- Telegram info (ID, username, etc.)
- Tier & subscription
- Referral code
- Stats (bets, profit, loss)
- Settings (bankroll, risk)

**Referral**
- Tier 1 (direct referrals)
- Commission tracking
- Monthly recurring calculation

**ReferralTier2**
- Tier 2 (indirect referrals)
- 10% commission

**Bet**
- Bet history
- Mode (SAFE/RISKED)
- Stakes, outcomes, profit
- Settlement tracking

### Migrations (TODO)

For production, use Alembic for database migrations:

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

## 🔐 Sécurité

### Best Practices

1. **Environment Variables**
   - Jamais commit `.env`
   - Utilise `.env.example` comme template

2. **Admin Access**
   - Whitelist d'admin IDs
   - Pas de bypass possible

3. **Database**
   - Connection pooling
   - Prepared statements (SQLAlchemy)

4. **API**
   - Rate limiting (à implémenter)
   - Validation des inputs

## 📊 Monitoring

### Logs

Le bot log automatiquement:
- Alertes envoyées
- Erreurs de parsing
- Broadcast results
- Database operations

### Metrics à Tracker

- Users actifs par tier
- Conversion rate (FREE → PREMIUM)
- Profit moyen par user
- Taux de retention
- Commission totale générée

## 🚧 TODO / Roadmap

### Court Terme

- [ ] Intégration Stripe pour paiements
- [ ] Webhooks Stripe pour auto-upgrade
- [ ] Email notifications
- [ ] Alembic migrations

### Moyen Terme

- [ ] API publique (pour tier GOLD)
- [ ] Webhook notifications
- [ ] Historical data export
- [ ] Analytics dashboard (web)

### Long Terme

- [ ] Mobile app
- [ ] Auto-betting integration
- [ ] Machine learning pour prediction
- [ ] Multi-currency support

## 📞 Support

Pour toute question:
- Telegram: @YourSupport
- Email: support@yourbot.com

## 📄 License

Proprietary - All rights reserved

---

**Note:** Ce bot est pour le marché Canadien/Québécois uniquement. Assurez-vous de respecter les lois locales sur les paris sportifs.
