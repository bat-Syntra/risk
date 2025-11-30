# 🎁 Système de Bonus Marketing - Guide Complet

## 📋 Vue d'ensemble

Le système de bonus marketing permet de:
- Offrir un rabais de $50 sur le premier mois ALPHA aux nouveaux utilisateurs
- Activer automatiquement l'éligibilité pendant 2 jours après inscription
- Envoyer des campagnes marketing quotidiennes automatiques
- Tracker qui a utilisé le bonus dans l'admin panel

## 🚀 Configuration NOW Payments

### 1. Créer deux plans de paiement sur NOWPayments

Tu dois créer **DEUX plans distincts** sur NOWPayments:

#### Plan 1: Prix régulier
- **Nom**: ALPHA Monthly - Regular
- **Prix**: 200 CAD
- **ID de plan**: [note cet ID]

#### Plan 2: Prix avec bonus
- **Nom**: ALPHA Monthly - New Member Bonus
- **Prix**: 150 CAD
- **ID de plan**: [note cet ID]

### 2. Configuration automatique des prix

Le système détecte automatiquement si un utilisateur a un bonus actif:

**Si bonus actif**: `create_invoice(telegram_id, amount_cad=150)`
**Si pas de bonus**: `create_invoice(telegram_id, amount_cad=200)`

Ceci se fait automatiquement dans:
- `handlers.py` ligne ~2030 (callback_buy_premium)
- `handlers.py` ligne ~1287 (show_tiers)

### 3. Marquer le bonus comme utilisé après paiement

**IMPORTANT**: Quand NOWPayments confirme un paiement, tu dois appeler:

```python
from bot.bonus_handler import BonusManager

# Dans ton IPN handler (webhook de NOWPayments)
if payment_confirmed and amount == 150:  # C'était un paiement avec bonus
    BonusManager.redeem_bonus(telegram_id)
```

Ceci marque le bonus comme "redeemed" dans la base de données.

## 📊 Admin Panel - Tracking des Bonus

### Query SQL pour voir tous les bonus actifs

```sql
SELECT 
    bt.telegram_id,
    u.username,
    bt.bonus_activated_at,
    bt.bonus_expires_at,
    bt.bonus_redeemed,
    bt.campaign_messages_sent,
    CASE 
        WHEN bt.bonus_redeemed = 1 THEN 'UTILISÉ ✅'
        WHEN datetime('now') > bt.bonus_expires_at THEN 'EXPIRÉ ❌'
        ELSE 'ACTIF 🔥'
    END as status
FROM bonus_tracking bt
JOIN users u ON bt.telegram_id = u.telegram_id
WHERE bt.bonus_activated_at IS NOT NULL
ORDER BY bt.bonus_activated_at DESC;
```

### Query SQL pour voir qui a utilisé le bonus

```sql
SELECT 
    bt.telegram_id,
    u.username,
    bt.bonus_redeemed_at,
    bt.bonus_amount,
    u.tier
FROM bonus_tracking bt
JOIN users u ON bt.telegram_id = u.telegram_id
WHERE bt.bonus_redeemed = 1
ORDER BY bt.bonus_redeemed_at DESC;
```

### Query SQL pour voir l'impact marketing

```sql
SELECT 
    COUNT(*) as total_bonus_activated,
    COUNT(CASE WHEN bonus_redeemed = 1 THEN 1 END) as redeemed_count,
    COUNT(CASE WHEN datetime('now') > bonus_expires_at AND bonus_redeemed = 0 THEN 1 END) as expired_count,
    ROUND(COUNT(CASE WHEN bonus_redeemed = 1 THEN 1 END) * 100.0 / COUNT(*), 2) as conversion_rate,
    AVG(campaign_messages_sent) as avg_messages_sent
FROM bonus_tracking
WHERE bonus_activated_at IS NOT NULL;
```

## 🤖 Campagne Marketing Automatique

### Fonctionnement

1. **Activation du bonus**: Quand user clique `/bonus`, le bonus expire dans 7 jours
2. **Messages quotidiens**: Système envoie 1 message/jour pendant 7 jours
3. **Messages progressifs**: Intensité augmente (Day 1 → Day 7)
4. **Stop automatique**: Si user achète ou bonus expire

### Lancer la campagne manuellement

```bash
cd /Users/z/Library/Mobile\ Documents/com~apple~CloudDocs/risk0-bot
python3 -m utils.bonus_marketing_campaign
```

### Automatiser avec cron (recommandé)

Ajoute à ta crontab:

```bash
# Campagne marketing quotidienne à 10h ET
0 10 * * * cd /Users/z/Library/Mobile\ Documents/com~apple~CloudDocs/risk0-bot && python3 -m utils.bonus_marketing_campaign >> /tmp/bonus_campaign.log 2>&1
```

## 💰 Tracking des Revenus

### Ajuster les revenus dans l'admin

Quand un utilisateur achète avec bonus, tu dois mettre à jour:

1. **Revenue total**: Ajouter $150 (pas $200)
2. **Champ bonus_used**: Marquer dans l'admin qu'un bonus a été utilisé

### Query pour calculer revenus réels

```sql
SELECT 
    SUM(CASE 
        WHEN bt.bonus_redeemed = 1 THEN 150
        ELSE 200
    END) as total_revenue
FROM bonus_tracking bt
JOIN users u ON bt.telegram_id = u.telegram_id
WHERE bt.bonus_redeemed = 1;
```

## 📱 Admin Panel - Modifications suggérées

### Ajouter une colonne "Bonus" dans la liste des users

Dans ton admin panel, ajoute:

```python
def get_user_bonus_status(telegram_id):
    """Retourne le statut du bonus pour un user"""
    db = SessionLocal()
    result = db.execute(text("""
        SELECT 
            bonus_activated_at,
            bonus_expires_at,
            bonus_redeemed,
            ever_had_bonus,
            CASE 
                WHEN bonus_redeemed = 1 THEN '✅ Utilisé'
                WHEN datetime('now') > bonus_expires_at THEN '❌ Expiré'
                WHEN bonus_activated_at IS NOT NULL THEN '🔥 Actif'
                WHEN ever_had_bonus = 1 THEN '📌 Déjà eu'
                ELSE '❌ Aucun'
            END as status
        FROM bonus_tracking
        WHERE telegram_id = :tid
    """), {'tid': telegram_id}).first()
    db.close()
    
    if not result:
        return "❌ Aucun"
    return result.status
```

## 🔔 Notifications Admin

### Message quand un bonus est activé

Tu peux être notifié quand un user active son bonus:

```python
# Dans bonus_handler.py, après BonusManager.activate_bonus()
admin_id = os.getenv("ADMIN_ID")
await bot.send_message(
    admin_id,
    f"🎁 <b>BONUS ACTIVÉ</b>\n\n"
    f"User: {telegram_id}\n"
    f"Bonus: $50\n"
    f"Expire: dans 7 jours",
    parse_mode=ParseMode.HTML
)
```

### Message quand un bonus est utilisé

```python
# Dans ton IPN handler
admin_id = os.getenv("ADMIN_ID")
await bot.send_message(
    admin_id,
    f"💰 <b>BONUS UTILISÉ</b>\n\n"
    f"User: {telegram_id}\n"
    f"Montant: $150\n"
    f"Économie user: $50",
    parse_mode=ParseMode.HTML
)
```

## 📈 KPIs à tracker

1. **Taux de conversion**: % de users qui activent le bonus et achètent
2. **Temps moyen avant achat**: Combien de jours entre activation et achat
3. **Messages envoyés avant conversion**: Moyenne de messages marketing avant achat
4. **Revenus perdus vs gagnés**: $50 perdu par bonus vs nouveau client à $150

## 🛠️ Commandes utiles

### Réinitialiser le bonus d'un user (admin only)

```sql
UPDATE bonus_tracking 
SET bonus_redeemed = 0,
    bonus_activated_at = datetime('now'),
    bonus_expires_at = datetime('now', '+7 days'),
    campaign_messages_sent = 0
WHERE telegram_id = [TELEGRAM_ID];
```

### Désactiver la campagne pour un user

```sql
UPDATE bonus_tracking 
SET bonus_expires_at = datetime('now')
WHERE telegram_id = [TELEGRAM_ID];
```

## ⚙️ Variables d'environnement

Assure-toi d'avoir dans ton `.env`:

```env
TELEGRAM_BOT_TOKEN=ton_token
NOWPAYMENTS_API_KEY=ta_cle_api
NOWPAYMENTS_IPN_SECRET=ton_secret_ipn
NOWPAYMENTS_IPN_URL=https://ton-serveur.com/ipn
ADMIN_ID=ton_telegram_id
```

## 🎯 Prochaines étapes recommandées

1. ✅ Créer les deux plans sur NOWPayments (150 CAD et 200 CAD)
2. ✅ Tester le flow complet avec un compte test
3. ✅ Configurer le cron job pour la campagne quotidienne
4. ✅ Ajouter les notifications admin dans ton panel
5. ✅ Tracker les KPIs dans un dashboard

---

**Contact**: @ZEROR1SK sur Telegram pour questions
