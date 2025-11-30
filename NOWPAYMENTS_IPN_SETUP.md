# 🔔 CONFIGURATION NOWPAYMENTS IPN (WEBHOOK AUTOMATIQUE)

**Bot redémarré avec logging complet!** ✅

---

## 🎯 PROBLÈME ACTUEL

Le paiement fonctionne ✅ mais l'activation n'est **PAS automatique** ❌

**Cause:** NOWPayments n'envoie pas le webhook IPN à ton serveur

---

## 🔧 SOLUTION: CONFIGURER L'IPN DANS NOWPAYMENTS

### **Étape 1: Accéder au Dashboard NOWPayments**

1. Va sur: https://nowpayments.io/dashboard
2. Login avec tes credentials
3. Clique sur **Settings** (⚙️)

---

### **Étape 2: Configurer IPN Settings**

Dans le menu de gauche, cherche **IPN Settings** ou **Webhooks**

**Configure les paramètres suivants:**

#### **A) IPN Callback URL:**
```
http://170.75.162.252:8080/webhook/nowpayments
```

**⚠️ IMPORTANT:**
- Pas de `/` à la fin
- Doit être exactement comme ci-dessus
- Utilise `http://` (pas https://)

#### **B) IPN Secret Key:**
Copie depuis ton `.env`:
```bash
qNwqHASSdC4DGwWPZCNKFWo3YXCo5elv
```

#### **C) Whitelist IP (si demandé):**
```
170.75.162.252
```

---

### **Étape 3: Choisir les événements à envoyer**

Coche ces événements:
- ✅ **Payment Finished**
- ✅ **Payment Confirmed**
- ✅ **Payment Partially Paid**

---

### **Étape 4: Tester le Webhook**

NOWPayments a souvent un bouton **"Test IPN"** ou **"Send Test Webhook"**

1. Clique dessus
2. Vérifie les logs du bot:

```bash
tail -f /tmp/bot_auto.log | grep "webhook\|NOWPayments"
```

**Tu devrais voir:**
```
INFO: 🔔 NOWPayments webhook received! Signature: xxx
INFO: ✅ Webhook signature validated!
INFO: 📦 Webhook data: {...}
```

---

## 📊 VÉRIFIER SI LE WEBHOOK FONCTIONNE

### **Option 1: Check les logs en temps réel**

```bash
tail -f /tmp/bot_auto.log | grep -i "webhook\|payment"
```

### **Option 2: Test avec un nouveau paiement**

1. Remet ton 2ème compte en FREE:
```bash
sqlite3 arbitrage_bot.db "UPDATE users SET tier='FREE', subscription_start=NULL, subscription_end=NULL WHERE telegram_id=8004919557;"
```

2. Relance un paiement de $10
3. Attends 1-5 minutes
4. Vérifie les logs

**Si ça marche:**
```
🔔 NOWPayments webhook received!
✅ Webhook signature validated!
💰 Payment status: finished
📄 Order ID: premium_8004919557_1234567890
✅ Telegram ID extracted: 8004919557
🚀 Activating PREMIUM for user 8004919557...
✅ User 8004919557 activated to PREMIUM!
```

---

## ⚠️ TROUBLESHOOTING

### **Problème 1: Webhook pas reçu**

**Symptôme:** Aucun log `🔔 NOWPayments webhook received!`

**Solutions:**
1. Vérifie que l'IPN URL est correctement configurée dans NOWPayments
2. Vérifie que ton VPS est accessible:
   ```bash
   curl http://170.75.162.252:8080/health
   ```
   Devrait retourner: `{"status": "healthy"}`

3. Vérifie que le port 8080 est ouvert:
   ```bash
   sudo ufw status
   ```
   Si bloqué:
   ```bash
   sudo ufw allow 8080
   ```

---

### **Problème 2: Webhook reçu mais signature invalide**

**Symptôme:** `❌ Webhook signature validation failed!`

**Solutions:**
1. Vérifie que `NOWPAYMENTS_IPN_SECRET` dans `.env` est correct
2. Copie-le depuis NOWPayments dashboard (Settings → IPN Secret)
3. Redémarre le bot après modification

---

### **Problème 3: Telegram ID non trouvé**

**Symptôme:** `❌ Could not find telegram_id from webhook data!`

**Solutions:**
1. Vérifie le format de l'`order_id` dans les logs
2. Devrait être: `premium_TELEGRAM_ID_TIMESTAMP`
3. Si différent, le code doit être ajusté

---

### **Problème 4: User non trouvé en DB**

**Symptôme:** `❌ Failed to activate PREMIUM for user XXX`

**Solution:**
Vérifie que l'user existe:
```bash
sqlite3 arbitrage_bot.db "SELECT * FROM users WHERE telegram_id=XXX;"
```

---

## 🧪 TESTER MANUELLEMENT LE WEBHOOK

Tu peux tester le webhook sans faire de vrai paiement:

```bash
curl -X POST http://localhost:8080/webhook/nowpayments \
  -H "Content-Type: application/json" \
  -H "x-nowpayments-sig: TEST_SIGNATURE" \
  -d '{
    "payment_status": "finished",
    "order_id": "premium_8004919557_1234567890",
    "price_amount": 10.0
  }'
```

**Vérifie les logs pour voir la réponse**

---

## 📝 CHECKLIST FINALE

**Configuration NOWPayments:**
- [ ] IPN URL configurée: `http://170.75.162.252:8080/webhook/nowpayments`
- [ ] IPN Secret ajouté
- [ ] IP whitelistée (si demandé)
- [ ] Événements sélectionnés (finished, confirmed)
- [ ] Test IPN envoyé et réussi

**Configuration Serveur:**
- [ ] Bot running (PID 51452)
- [ ] Port 8080 ouvert
- [ ] Logs actifs: `tail -f /tmp/bot_auto.log`
- [ ] Endpoint /health accessible

**Test Complet:**
- [ ] Nouveau paiement test
- [ ] Webhook reçu dans les logs
- [ ] User activé automatiquement
- [ ] Message de bienvenue envoyé
- [ ] Notification admin reçue

---

## 🚀 NEXT STEPS

1. **Configure l'IPN dans NOWPayments dashboard** (Étapes ci-dessus)
2. **Teste avec un Test IPN** depuis le dashboard
3. **Si ça marche pas, montre-moi:**
   - Screenshot de ta config IPN dans NOWPayments
   - Les logs du bot après le test

4. **Une fois que ça marche:**
   - Remet ton 2ème compte en FREE
   - Refais un paiement test de $10
   - Vérifie l'activation automatique ✅

---

## 💡 ALTERNATIVE: WEBHOOK MANUEL

Si NOWPayments n'appelle jamais le webhook, on peut créer un **polling system**:
- Le bot check automatiquement les paiements NOWPayments toutes les 2 minutes
- Active automatiquement les users quand un paiement est confirmé

Mais c'est moins propre que le webhook IPN. Essaie d'abord de configurer l'IPN correctement!

---

**Créé le:** 29 Nov 2025  
**Status:** Logging activé, IPN à configurer  
**Bot PID:** 51452
