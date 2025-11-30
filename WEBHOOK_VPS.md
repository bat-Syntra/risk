# Configuration Webhook NOWPayments sur VPS

## 🎯 Objectif

Configurer l'URL webhook pour que NOWPayments puisse notifier ton bot quand un paiement est confirmé.

## Option 1: Sans Domaine (Utiliser l'IP du VPS) ✅ Recommandé

### Avantages
- ✅ **Gratuit** - Pas besoin d'acheter un domaine
- ✅ **Simple** - Juste besoin de l'IP publique de ton VPS
- ✅ **Fonctionne parfaitement** pour les webhooks

### Configuration

1. **Obtenir l'IP publique de ton VPS**
   ```bash
   # Sur ton VPS, exécute:
   curl ifconfig.me
   # Exemple de résultat: 123.45.67.89
   ```

2. **Mettre à jour .env**
   ```bash
   NOWPAYMENTS_IPN_URL=http://123.45.67.89:8080/webhook/nowpayments
   ```
   ⚠️ Remplace `123.45.67.89` par ton IP réelle

3. **Dans NOWPayments Dashboard**
   - Va dans **Settings → IPN Settings**
   - IPN Callback URL: `http://123.45.67.89:8080/webhook/nowpayments`
   - Active IPN

4. **Ouvrir le port 8080 sur ton VPS**
   ```bash
   # Si tu utilises UFW (Ubuntu/Debian):
   sudo ufw allow 8080
   sudo ufw status
   
   # Si tu utilises firewalld (CentOS/RHEL):
   sudo firewall-cmd --permanent --add-port=8080/tcp
   sudo firewall-cmd --reload
   ```

### ✅ C'est tout! Ça marche parfaitement sans domaine.

---

## Option 2: Avec Domaine (Optionnel)

### Avantages
- ✅ URL plus professionnelle
- ✅ HTTPS possible (plus sécurisé)
- ✅ Plus facile à retenir

### Inconvénients
- ❌ Coûte de l'argent (~10-15$/an)
- ❌ Configuration plus complexe

### Domaines pas chers
- **Namecheap**: ~8$/an pour .xyz, .site
- **Porkbun**: ~3$/an pour .xyz
- **Cloudflare**: ~10$/an pour .com

### Configuration si tu achètes un domaine

1. **Achète un domaine** (ex: `risk0casino.xyz`)

2. **Configure DNS A Record**
   ```
   Type: A
   Name: @
   Value: 123.45.67.89 (ton IP VPS)
   TTL: Auto
   ```

3. **Installe Nginx + Certbot (pour HTTPS)**
   ```bash
   # Sur ton VPS
   sudo apt update
   sudo apt install nginx certbot python3-certbot-nginx
   
   # Configure Nginx
   sudo nano /etc/nginx/sites-available/risk0casino
   ```
   
   Contenu:
   ```nginx
   server {
       listen 80;
       server_name risk0casino.xyz;
       
       location /webhook/nowpayments {
           proxy_pass http://localhost:8080/webhook/nowpayments;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
   
   ```bash
   sudo ln -s /etc/nginx/sites-available/risk0casino /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   
   # Obtenir certificat SSL gratuit
   sudo certbot --nginx -d risk0casino.xyz
   ```

4. **Mettre à jour .env**
   ```bash
   NOWPAYMENTS_IPN_URL=https://risk0casino.xyz/webhook/nowpayments
   ```

5. **Dans NOWPayments Dashboard**
   - IPN Callback URL: `https://risk0casino.xyz/webhook/nowpayments`

---

## 🎯 Ma Recommandation

**Pour commencer: Utilise Option 1 (IP directe)**

Pourquoi?
- C'est gratuit
- Ça marche parfaitement
- Configuration en 2 minutes
- Tu peux toujours ajouter un domaine plus tard

**Plus tard, si tu veux être pro:**
- Achète un domaine pas cher ($3-10/an)
- Configure HTTPS
- Mais ce n'est pas nécessaire pour que ça fonctionne!

---

## 🧪 Test du Webhook

Une fois configuré, teste-le:

```bash
# Sur ton ordinateur ou VPS
curl -X POST http://TON_IP_VPS:8080/webhook/nowpayments \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

Tu devrais voir une réponse du serveur.

---

## ⚠️ Important: Sécurité

**Avec IP (Option 1):**
- Le webhook est en HTTP (pas crypté)
- Mais c'est OK car NOWPayments envoie une signature HMAC pour vérifier l'authenticité
- Notre code vérifie cette signature

**Avec Domaine + HTTPS (Option 2):**
- Plus sécurisé (crypté)
- Mais pas obligatoire grâce à la signature HMAC

---

## 📝 Résumé des étapes

### Pour Option 1 (IP - RECOMMANDÉ):

1. ✅ API keys ajoutées dans `.env` (déjà fait)
2. 🔄 Obtenir IP du VPS: `curl ifconfig.me`
3. 🔄 Mettre l'IP dans `.env` → `NOWPAYMENTS_IPN_URL`
4. 🔄 Ouvrir port 8080: `sudo ufw allow 8080`
5. 🔄 Configurer l'URL dans NOWPayments Dashboard
6. 🔄 Tester un paiement

**Temps total: ~5 minutes**

### Pour Option 2 (Domaine):

1. ✅ API keys ajoutées (déjà fait)
2. 🔄 Acheter domaine (~$10/an)
3. 🔄 Configurer DNS
4. 🔄 Installer Nginx + SSL
5. 🔄 Configurer l'URL dans NOWPayments Dashboard
6. 🔄 Tester

**Temps total: ~30-60 minutes**

---

## 🚀 Prochaines Étapes

1. Décide: IP directe ou domaine?
2. Configure l'URL webhook
3. Je t'aide à créer le code pour gérer les paiements automatiquement!

Dis-moi quelle option tu choisis et je continue l'implémentation! 🎯
