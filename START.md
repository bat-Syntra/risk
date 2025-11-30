# 🚀 START - 3 Étapes Seulement

## ✅ Ce Qu'il Te Faut (1 fois seulement)

### Obtenir API_ID et API_HASH

1. Va sur: **https://my.telegram.org**
2. Login avec ton numéro Telegram
3. Clique: **"API development tools"**
4. Crée une app:
   - App title: `Risk0 Bridge`
   - Short name: `risk0bridge`
   - Platform: `Desktop`
5. Tu vas voir:
   ```
   api_id: 12345678
   api_hash: abc123def456...
   ```

### Remplis .env

Ouvre le fichier `.env` (lignes 13-15) et mets:

```env
TELEGRAM_API_ID=12345678                    ← Ton api_id ici
TELEGRAM_API_HASH=abc123def456...           ← Ton api_hash ici  
TELEGRAM_PHONE=+15141234567                 ← Ton numéro ici
```

**Sauvegarde!**

---

## 🚀 Lancer le Bot (2 commandes)

### Terminal 1 - Risk0_bot

```bash
cd "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/test/risk0-bot"
python3 main_new.py
```

**Laisse ce terminal ouvert!**

### Terminal 2 - Bridge Automatique

```bash
cd "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/test/risk0-bot"
python3 bridge.py
```

**Premier lancement:**
- Il va demander un code
- Check tes messages Telegram (code de "Telegram")
- Entre le code
- Entre ton password 2FA si demandé

**Résultat:**
```
✅ Connecté en tant que: Ton Nom
👂 Écoute les messages de: Nonoriribot
⏳ En attente de messages...
```

**Laisse ce terminal ouvert aussi!**

---

## 🎉 C'est Tout!

Maintenant:
- ✅ Quand **Nonoriribot** t'envoie une alerte
- ✅ Le **bridge** la capte automatiquement (tu ne fais RIEN)
- ✅ **Risk0_bot** parse et distribue à tous les users
- ✅ **100% AUTOMATIQUE**

---

## 🧪 Test Sans Attendre

### Test 1: Bot marche

Telegram → Cherche `@Risk0_bot` → `/start`

Tu devrais recevoir le message de bienvenue!

### Test 2: Alerte automatique

```bash
# Nouveau terminal
cd "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/test/risk0-bot"
python3 test_alert.py
```

Tu reçois l'alerte sur Telegram! ✅

---

## 📊 Statut Normal

**Terminal 1 (Risk0_bot):**
```
✅ ArbitrageBot Canada - Starting...
INFO:     Uvicorn running on http://0.0.0.0:8080
```

**Terminal 2 (Bridge):**
```
✅ Connecté en tant que: Ton Nom
👂 Écoute les messages de: Nonoriribot
⏳ En attente de messages...
```

**Les 2 doivent tourner en même temps!**

---

## 🔍 Si Problème

### "API_ID is invalid"
→ Revérifie sur https://my.telegram.org

### "Phone number is not registered"
→ Utilise le format: `+15141234567` (avec +)

### "ModuleNotFoundError"
→ Install:
```bash
pip3 install aiogram fastapi uvicorn sqlalchemy telethon aiohttp
```

### Port 8080 déjà utilisé
```bash
lsof -i :8080
# Kill le process
kill -9 PID_NUMBER
```

---

## 🎯 C'est Quoi le Flow?

```
Nonoriribot envoie alerte
      ↓
bridge.py écoute (TON compte)
      ↓
Parse automatiquement
      ↓
Envoie à main_new.py (API)
      ↓
Distribution à TOUS les users
```

**Tu ne fais RIEN - c'est 100% automatique!** ⚡

---

## 💡 Important

- **Garde les 2 terminaux ouverts** tant que tu veux que ça marche
- **Pour production:** Utilise `screen` ou `systemd` pour les garder actifs 24/7
- **Backup:** Le fichier `arbitrage_bot.db` contient toutes les données

---

## ✅ Checklist Rapide

- [ ] Obtenu api_id et api_hash de my.telegram.org
- [ ] Rempli .env (lignes 13-15)
- [ ] Lancé `python3 main_new.py` (Terminal 1)
- [ ] Lancé `python3 bridge.py` (Terminal 2)
- [ ] Testé avec `/start` sur @Risk0_bot
- [ ] Testé avec `python3 test_alert.py`

**Dès que les 2 programmes tournent, c'est AUTOMATIQUE!** 🚀
