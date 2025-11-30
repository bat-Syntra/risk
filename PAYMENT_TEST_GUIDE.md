# 💳 GUIDE DE TEST DU SYSTÈME DE PAIEMENT

**Bot redémarré (PID 48578)** ✅

---

## 🎯 CE QUI A ÉTÉ CONFIGURÉ

### **1. Mode TEST pour $3** ✅

**Fichier:** `bot/handlers.py` (ligne 2093)

```python
TEST_ACCOUNT_ID = 0  # <-- CHANGE TO YOUR 2ND ACCOUNT ID
```

**Quand le prix = $3:**
- Affichage: `<s>$200</s> $3 CAD/mois 🎁`
- Rabais affiché: $197
- Prix réel: **$3.00**

---

### **2. Notification Admin Automatique** ✅

**Fichier:** `bot/nowpayments_handler.py` (ligne 102-130)

**Quand paiement confirmé:**
```
🎉 NOUVEAU MEMBRE ALPHA!

👤 User: @username
🆔 ID: telegram_id
📅 Expire: 2025-12-29

💰 Paiement reçu via NOWPayments ✅
🔥 Membre activé automatiquement!
```

---

### **3. Webhook NOWPayments** ✅

**Endpoint:** `http://170.75.162.252:8080/webhook/nowpayments`

**Flow automatique:**
1. User paie via NOWPayments
2. Webhook reçoit confirmation
3. Vérifie signature IPN
4. Active user en ALPHA
5. Notifie admin
6. Envoie welcome message au user

---

## 🧪 COMMENT TESTER

### **Étape 1: Donne-moi l'ID de ton 2ème compte**

**Méthode 1 - Via le bot:**
1. Connecte-toi avec ton 2ème compte
2. Envoie `/start` au bot
3. Ton ID sera affiché quelque part

**Méthode 2 - Via @userinfobot:**
1. Cherche `@userinfobot` sur Telegram
2. Envoie `/start` depuis ton 2ème compte
3. Il t'affichera ton ID

**Donne-moi cet ID et je vais le mettre dans TEST_ACCOUNT_ID!**

---

### **Étape 2: Active le bonus (optionnel)**

**Depuis ton 2ème compte:**
```
/bonus
```

Mais ce n'est pas nécessaire car le mode TEST force le prix à $3!

---

### **Étape 3: Clique sur "Acheter ALPHA"**

**Depuis ton 2ème compte:**

1. Menu → **💎 Tiers Alpha**
2. Ou tape `/subscribe`
3. Clique **🚀 Buy ALPHA**

**Tu verras:**
```
💎 ALPHA - <s>$200</s> $3 CAD/mois 🎁
(Rabais nouveau membre: $197)

💰 Paiement crypto via NOWPayments

[💳 Payer avec Crypto]
```

---

### **Étape 4: Paye via NOWPayments**

1. Clique **💳 Payer avec Crypto**
2. Tu seras redirigé vers NOWPayments
3. Choisis ta crypto (USDT, BTC, ETH, etc.)
4. Paie **$3.00** en crypto
5. Attends confirmation (1-5 minutes)

---

### **Étape 5: Vérifications automatiques**

**Ce qui devrait se passer:**

**1. Sur ton 2ème compte:**
```
✅ Bienvenue en PREMIUM!

Ton accès est actif pendant 30 jours

Important: Lis le guide...
```

**2. Sur ton compte admin (toi):**
```
🎉 NOUVEAU MEMBRE ALPHA!

👤 User: @ton2emecompte
🆔 ID: xxxxxx
📅 Expire: 2025-12-29

💰 Paiement reçu via NOWPayments ✅
🔥 Membre activé automatiquement!
```

**3. Dans ton wallet NOWPayments:**
- Tu devrais voir **$3.00** (en crypto équivalent)
- Statut: Confirmé

---

## 📊 VÉRIFICATIONS À FAIRE

### **1. User est bien ALPHA:**

Depuis ton 2ème compte:
```
/mystats
```

**Devrait afficher:**
```
🏆 Tier: ALPHA
⏰ Expire dans: 30 jours
```

---

### **2. Vérifier dans la DB:**

```bash
sqlite3 arbitrage_bot.db "
SELECT telegram_id, tier, subscription_start, subscription_end 
FROM users 
WHERE telegram_id = XXXXXX;
"
```

**Résultat attendu:**
```
telegram_id|tier|subscription_start|subscription_end
XXXXXX|PREMIUM|2025-11-29 XX:XX:XX|2025-12-29 XX:XX:XX
```

---

### **3. Wallet NOWPayments:**

1. Va sur https://nowpayments.io/dashboard
2. Login avec tes credentials
3. Check **Payments**
4. Tu devrais voir le paiement de $3.00

**Status:** Finished ✅

---

## 🔧 CONFIGURATION NOWPAYMENTS

### **Variables .env (déjà configurées):**

```bash
NOWPAYMENTS_API_KEY=FR3N5NM-A9J4CVZ-GRFP0EZ-Y26SF5R ✅
NOWPAYMENTS_IPN_SECRET=qNwqHASSdC4DGwWPZCNKFWo3YXCo5elv ✅
NOWPAYMENTS_IPN_URL=http://170.75.162.252:8080/webhook/nowpayments ✅
NOWPAYMENTS_SANDBOX=False ✅
```

**Tout est bon!** ✅

---

## ⚠️ TROUBLESHOOTING

### **Problème 1: Prix n'est pas $3**

**Cause:** TEST_ACCOUNT_ID pas configuré

**Solution:**
1. Donne-moi l'ID de ton 2ème compte
2. Je vais le mettre dans handlers.py
3. Redémarrer le bot

---

### **Problème 2: Paiement pas confirmé**

**Cause:** Webhook pas reçu ou signature invalide

**Check logs:**
```bash
tail -100 /tmp/bot_auto.log | grep -i "nowpayments\|webhook\|payment"
```

**Solution:**
1. Vérifier que l'IP du serveur est whitelistée dans NOWPayments dashboard
2. Vérifier que IPN_URL est correcte
3. Vérifier que IPN_SECRET est correct

---

### **Problème 3: User pas upgradé**

**Cause:** `activate_premium` a échoué

**Check logs:**
```bash
tail -100 /tmp/bot_auto.log | grep -i "activate"
```

**Solution:** Vérifier que l'user existe dans la DB

---

### **Problème 4: Pas de notification admin**

**Cause:** ADMIN_CHAT_ID pas configuré ou erreur d'envoi

**Check:**
```bash
grep ADMIN_CHAT_ID .env
```

**Solution:** S'assurer que ADMIN_CHAT_ID = ton ID

---

## 🎯 APRÈS LE TEST

### **Si tout marche:**

1. ✅ User devient ALPHA automatiquement
2. ✅ Tu reçois notification
3. ✅ Paiement apparaît dans wallet
4. ✅ Le système est prêt pour production!

---

### **Pour activer en PRODUCTION:**

**Option 1: Enlever le mode test**
```python
# Dans handlers.py ligne 2093
TEST_ACCOUNT_ID = 0  # Mettre à 0 pour désactiver test
```

**Option 2: Changer le prix de base**

Si tu veux garder $150 avec bonus:
- Prix de base reste $200
- Bonus reste $50
- Prix final = $150

Si tu veux changer:
```python
# Dans config ou TierManager
PREMIUM_PRICE = 150  # Au lieu de 200
```

---

## 💰 GESTION WALLET

### **Retirer l'argent de NOWPayments:**

1. Dashboard: https://nowpayments.io/dashboard
2. **Withdrawals** → Create withdrawal
3. Choisir crypto
4. Entrer wallet address
5. Confirmer

**Minimum withdrawal:** Varie selon la crypto
- USDT: $10
- BTC: 0.0005 BTC
- ETH: 0.01 ETH

---

## 📋 CHECKLIST FINALE

**Avant de lancer le test:**

- [ ] Tu m'as donné l'ID de ton 2ème compte
- [ ] J'ai mis l'ID dans TEST_ACCOUNT_ID
- [ ] Bot redémarré
- [ ] Tu as accès à ton 2ème compte Telegram
- [ ] Tu as $3-5 en crypto disponible
- [ ] Tu connais ton wallet NOWPayments login

**Pendant le test:**

- [ ] Prix affiché = $3
- [ ] Lien NOWPayments généré
- [ ] Paiement envoyé
- [ ] Confirmation reçue (1-5 min)

**Après le test:**

- [ ] User devient ALPHA
- [ ] Notification admin reçue
- [ ] Paiement visible dans wallet
- [ ] Tout fonctionne!

---

## 🚀 PRÊT À TESTER?

**Donne-moi l'ID de ton 2ème compte et on teste!**

**Format:** Juste le chiffre, ex: `123456789`

---

**Créé le:** 29 Nov 2025  
**Status:** Prêt pour test  
**Mode:** TEST ($3)  
**Production:** Après validation
