# 🚀 DÉPLOIEMENT SUR VPS - GUIDE COMPLET

**Pour plus tard quand tu veux déployer le bot sur ton VPS**

---

## 📋 PRÉREQUIS

- VPS avec IP: `170.75.162.252` ✅
- SSH access au VPS
- Python 3.9+ installé
- Port 8080 ouvert

---

## 🎯 ÉTAPES DE DÉPLOIEMENT

### **1. Se connecter au VPS**

```bash
ssh root@170.75.162.252
```

Ou avec ton user:
```bash
ssh user@170.75.162.252
```

---

### **2. Installer les dépendances**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip
sudo apt install python3 python3-pip python3-venv -y

# Install git
sudo apt install git -y
```

---

### **3. Transférer le code sur le VPS**

**Option A: Via Git (recommandé)**

Sur le VPS:
```bash
cd /opt
sudo mkdir risk0-bot
sudo chown $USER:$USER risk0-bot
cd risk0-bot

# Clone ton repo (si tu as un repo git)
git clone https://github.com/ton-username/risk0-bot.git .
```

**Option B: Via SCP (depuis ton Mac)**

```bash
# Depuis ton Mac
cd "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/risk0-bot"

# Compress le projet
tar -czf risk0-bot.tar.gz .

# Transfer au VPS
scp risk0-bot.tar.gz user@170.75.162.252:/opt/

# Sur le VPS
ssh user@170.75.162.252
cd /opt
mkdir risk0-bot
cd risk0-bot
tar -xzf ../risk0-bot.tar.gz
rm ../risk0-bot.tar.gz
```

**Option C: Via rsync (recommandé - synchronise les fichiers)**

```bash
# Depuis ton Mac
rsync -avz --exclude 'arbitrage_bot.db' --exclude '__pycache__' --exclude '*.pyc' \
  "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/risk0-bot/" \
  user@170.75.162.252:/opt/risk0-bot/
```

---

### **4. Créer l'environnement virtuel**

```bash
cd /opt/risk0-bot

# Créer venv
python3 -m venv venv

# Activer venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

---

### **5. Configurer l'environnement (.env)**

**Sur ton VPS:**

```bash
cd /opt/risk0-bot
nano .env
```

Colle tout le contenu de ton `.env` local (déjà configuré avec NOWPayments, etc.)

**Vérifie surtout:**
```bash
NOWPAYMENTS_IPN_URL=http://170.75.162.252:8080/webhook/nowpayments
```

---

### **6. Configurer la base de données**

**Option A: Transférer la DB existante**

Depuis ton Mac:
```bash
scp arbitrage_bot.db user@170.75.162.252:/opt/risk0-bot/
```

**Option B: Créer une nouvelle DB**

```bash
cd /opt/risk0-bot
python3 -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
```

---

### **7. Configurer le firewall (port 8080)**

```bash
# Vérifier le firewall
sudo ufw status

# Ouvrir le port 8080
sudo ufw allow 8080/tcp

# Activer le firewall si pas déjà fait
sudo ufw enable
```

**Tester l'accès:**
```bash
# Depuis le VPS
curl http://localhost:8080/health

# Depuis ton Mac (une fois le bot lancé)
curl http://170.75.162.252:8080/health
```

---

### **8. Lancer le bot en background**

**Option A: Avec screen (simple)**

```bash
# Installer screen
sudo apt install screen -y

# Créer une session
screen -S risk0bot

# Activer venv et lancer
cd /opt/risk0-bot
source venv/bin/activate
python3 main_new.py

# Détacher: Ctrl+A puis D
# Rattacher: screen -r risk0bot
```

**Option B: Avec systemd (professionnel - recommandé)**

Créer le service:
```bash
sudo nano /etc/systemd/system/risk0bot.service
```

Contenu:
```ini
[Unit]
Description=Risk0 Arbitrage Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/risk0-bot
Environment="PATH=/opt/risk0-bot/venv/bin"
ExecStart=/opt/risk0-bot/venv/bin/python3 /opt/risk0-bot/main_new.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activer le service:
```bash
# Recharger systemd
sudo systemctl daemon-reload

# Activer le service (démarrage automatique)
sudo systemctl enable risk0bot

# Démarrer le service
sudo systemctl start risk0bot

# Vérifier le status
sudo systemctl status risk0bot

# Voir les logs
sudo journalctl -u risk0bot -f
```

**Commandes utiles:**
```bash
# Redémarrer
sudo systemctl restart risk0bot

# Arrêter
sudo systemctl stop risk0bot

# Voir les logs
sudo journalctl -u risk0bot -n 100
sudo journalctl -u risk0bot -f  # Follow mode
```

---

### **9. Configurer NOWPayments IPN**

Une fois le bot lancé sur le VPS:

1. Va sur https://nowpayments.io/dashboard
2. Settings → IPN Settings
3. Webhook URL: `http://170.75.162.252:8080/webhook/nowpayments`
4. Save!

---

### **10. Tester le système**

**A) Test de santé:**
```bash
curl http://170.75.162.252:8080/health
```

**B) Test de paiement:**
1. Depuis ton 2ème compte (8004919557)
2. Acheter ALPHA à $10
3. Vérifier que le webhook est reçu:
   ```bash
   sudo journalctl -u risk0bot -f | grep webhook
   ```
4. Vérifier l'activation automatique
5. Vérifier la notification admin

---

## 🔧 MAINTENANCE

### **Mettre à jour le code**

**Option A: Via Git**
```bash
cd /opt/risk0-bot
git pull
sudo systemctl restart risk0bot
```

**Option B: Via rsync (depuis ton Mac)**
```bash
rsync -avz --exclude 'arbitrage_bot.db' --exclude '__pycache__' \
  "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/risk0-bot/" \
  user@170.75.162.252:/opt/risk0-bot/

# Sur le VPS
sudo systemctl restart risk0bot
```

---

### **Backup de la base de données**

**Automatique (recommandé):**

Créer un cron job:
```bash
crontab -e
```

Ajouter:
```bash
# Backup DB tous les jours à 3h du matin
0 3 * * * cp /opt/risk0-bot/arbitrage_bot.db /opt/risk0-bot/backups/arbitrage_bot_$(date +\%Y\%m\%d).db
```

**Manuel:**
```bash
cp arbitrage_bot.db arbitrage_bot_backup_$(date +%Y%m%d).db
```

**Télécharger depuis le VPS:**
```bash
scp user@170.75.162.252:/opt/risk0-bot/arbitrage_bot.db ~/Desktop/
```

---

### **Voir les logs**

```bash
# Logs du service
sudo journalctl -u risk0bot -n 100

# Logs en temps réel
sudo journalctl -u risk0bot -f

# Filtrer par erreur
sudo journalctl -u risk0bot | grep ERROR

# Filtrer par webhook
sudo journalctl -u risk0bot | grep webhook
```

---

## ⚠️ TROUBLESHOOTING

### **Problème 1: Bot ne démarre pas**

```bash
# Vérifier le status
sudo systemctl status risk0bot

# Voir les erreurs
sudo journalctl -u risk0bot -n 50

# Tester manuellement
cd /opt/risk0-bot
source venv/bin/activate
python3 main_new.py
```

---

### **Problème 2: Port 8080 already in use**

```bash
# Trouver le process
sudo lsof -i:8080

# Tuer le process
sudo kill -9 <PID>

# Redémarrer
sudo systemctl restart risk0bot
```

---

### **Problème 3: Webhook pas reçu**

**Vérifier:**
1. Port 8080 ouvert: `sudo ufw status`
2. Bot tourne: `sudo systemctl status risk0bot`
3. Endpoint accessible: `curl http://170.75.162.252:8080/health`
4. IPN URL correcte dans NOWPayments dashboard
5. Logs du webhook: `sudo journalctl -u risk0bot -f | grep webhook`

---

### **Problème 4: Permissions**

```bash
# Donner les bonnes permissions
sudo chown -R $USER:$USER /opt/risk0-bot
chmod +x main_new.py
```

---

## 📊 MONITORING

### **Vérifier que le bot tourne**

```bash
# Status
sudo systemctl status risk0bot

# Uptime
ps aux | grep main_new.py

# CPU/Memory
top -p $(pgrep -f main_new.py)
```

---

### **Créer un script de monitoring**

```bash
nano /opt/risk0-bot/monitor.sh
```

Contenu:
```bash
#!/bin/bash

# Check if bot is running
if ! systemctl is-active --quiet risk0bot; then
    echo "Bot is down! Restarting..."
    sudo systemctl start risk0bot
    
    # Send alert to admin (optional)
    curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
      -d "chat_id=$ADMIN_CHAT_ID" \
      -d "text=⚠️ Bot was down and has been restarted!"
fi
```

Rendre exécutable:
```bash
chmod +x /opt/risk0-bot/monitor.sh
```

Ajouter au cron (check toutes les 5 minutes):
```bash
crontab -e
```

Ajouter:
```bash
*/5 * * * * /opt/risk0-bot/monitor.sh
```

---

## 🎯 CHECKLIST FINALE

**Avant de déployer:**
- [ ] Code testé localement
- [ ] `.env` configuré avec bonnes valeurs
- [ ] Base de données sauvegardée
- [ ] NOWPayments IPN URL mise à jour

**Après déploiement:**
- [ ] Bot démarre sans erreur
- [ ] `/health` endpoint accessible
- [ ] Test paiement $10 réussi
- [ ] Webhook reçu et traité
- [ ] User activé automatiquement
- [ ] Notification admin reçue
- [ ] Logs propres

**Maintenance:**
- [ ] Backup automatique configuré
- [ ] Monitoring script en place
- [ ] Service systemd actif
- [ ] Firewall configuré

---

## 💡 CONSEILS

1. **Toujours tester localement d'abord**
2. **Faire un backup avant chaque déploiement**
3. **Utiliser systemd pour auto-restart**
4. **Surveiller les logs régulièrement**
5. **Garder un backup de `.env` en sécurité**
6. **Documenter chaque modification**

---

**Créé le:** 29 Nov 2025  
**VPS IP:** 170.75.162.252  
**Port:** 8080  
**Service:** risk0bot  
**Status:** Prêt pour déploiement
