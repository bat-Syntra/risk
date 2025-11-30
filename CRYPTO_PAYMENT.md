# Configuration des Paiements Crypto

## Vue d'ensemble

Le bot Risk0 Casino utilise **NOWPayments** pour les paiements crypto automatisés.  
Plan PREMIUM: **200 CAD/mois**

## Méthode Recommandée: NOWPayments

**Pourquoi NOWPayments?**
- ✅ **150+ cryptos** acceptées (BTC, ETH, USDT, SOL, TON, DOGE, etc.)
- ✅ **Automatisation complète** via API et webhooks
- ✅ **Frais bas** - 0.5% par transaction
- ✅ **Activation instantanée** après paiement
- ✅ **Pas de KYC** requis

**Guide complet:** Voir `NOWPAYMENTS_SETUP.md`

## Option Simple (Pour Commencer)

### 1. Liens de Paiement Manuels NOWPayments

Sans coder, tu peux créer des liens de paiement:
1. Crée un compte sur https://nowpayments.io
2. Dashboard → **Payment Links**
3. Crée un lien pour 200 CAD
4. Partage le lien aux utilisateurs
5. Check les paiements et upgrade manuellement via `/admin`

### 2. Contact Direct avec Admin

L'utilisateur peut aussi contacter l'admin directement.

**Configuration :**
- Dans `bot/handlers.py`, ligne 669
- Change `admin_username = "Risk0Support"` par ton vrai username Telegram

## Activation Manuelle des Comptes PREMIUM

Quand un utilisateur paie :

1. **Vérifier le paiement** - Confirmez la transaction crypto

2. **Obtenir l'ID Telegram** - L'utilisateur verra son ID dans le message de paiement

3. **Activer via Admin Panel** :
   ```
   /admin → Chercher user par ID → Upgrade Tier → PREMIUM
   ```

4. **OU via Base de Données** :
   ```python
   # Ouvrir la DB SQLite
   import sqlite3
   from datetime import datetime, timedelta
   
   conn = sqlite3.connect('arbitrage_bot.db')
   cursor = conn.cursor()
   
   # Trouver l'utilisateur
   telegram_id = 123456789  # ID de l'utilisateur
   
   # Mettre à jour vers PREMIUM pour 1 mois
   end_date = datetime.now() + timedelta(days=30)
   cursor.execute("""
       UPDATE users 
       SET tier = 'premium',
           subscription_start = ?,
           subscription_end = ?
       WHERE telegram_id = ?
   """, (datetime.now(), end_date, telegram_id))
   
   conn.commit()
   conn.close()
   ```

## Automatisation Future (Optionnel)

Pour automatiser les paiements, vous pouvez :

### Option 1: CryptoBot API
- Utiliser l'API de CryptoBot pour générer des factures
- Webhook pour notification automatique de paiement
- Documentation: https://help.crypt.bot/crypto-pay-api

### Option 2: Coinbase Commerce
- Créer des factures crypto
- Webhook pour confirmation
- Documentation: https://commerce.coinbase.com/docs/

### Option 3: BTCPay Server
- Auto-hébergé, open source
- Accepte Bitcoin et Lightning
- Documentation: https://docs.btcpayserver.org/

## Plan Actuel (Simplifié)

### 🆓 FREE
- 2 alertes par jour
- Arbitrages < 2.5%
- Temps réel

### 🔥 PREMIUM - 200 CAD/mois
- Alertes illimitées
- Tous les arbitrages (≥0.5%)
- Mode RISKED
- Calculateur personnalisé
- Stats avancées
- Support VIP
- Bonus referral x2

## Notes Importantes

1. **Taux de Change** : 200 CAD ≈ 145 USD ≈ 0.0022 BTC (variable)
2. **Vérification** : Toujours demander la preuve de transaction
3. **ID Telegram** : Crucial pour identifier l'utilisateur
4. **Durée** : 1 mois = 30 jours à partir de la date d'activation

## Support

Pour toute question sur les paiements crypto :
- Contact : @Risk0Support (changez dans le code)
- Email : support@risk0casino.com (à configurer)
