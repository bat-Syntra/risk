# 🚨 GUIDE DE DÉMARRAGE CORRECT - SANS DOUBLONS

## ⚠️ PROBLÈMES CORRIGÉS

1. ✅ **Doublons éliminés** - Déduplication dans main_new.py /public/drop
2. ✅ **Format corrigé** - "(+154)" au lieu de "@ +154"
3. ✅ **Time ajouté** - Affichage de la date/heure du match
4. ✅ **Hash robuste** - Ordre-indépendant dans bridge_simple.py

---

## 📋 FICHIERS À UTILISER

**IMPORTANT: Utilise ces 2 fichiers UNIQUEMENT:**

1. **bridge_simple.py** - Écoute Nonoriribot et parse avec GPT Vision
2. **main_new.py** - API qui reçoit les calls et les distribue aux users

❌ **NE PAS UTILISER:**
- ~~main.py~~ (ancien, pas à jour)
- ~~main_simple.py~~ (ancien, pas à jour)
- ~~bridge.py~~ (complexe, remplacé par bridge_simple.py)
- ~~bridge_hybrid.py~~ (ancien système)

---

## 🚀 DÉMARRAGE CORRECT

### Terminal 1: Lance l'API (main_new.py)

```bash
cd "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/test/risk0-bot"
source .venv/bin/activate
python3 main_new.py
```

**Tu DOIS voir:**
```
🚀 Initializing database...
✅ Database initialized
✅ ArbitrageBot Canada - Starting...
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

**Si erreur "port 8080 already in use":**
```bash
# Tue l'ancien process
lsof -ti:8080 | xargs kill -9
# Relance
python3 main_new.py
```

---

### Terminal 2: Lance le bridge (bridge_simple.py)

```bash
cd "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/test/risk0-bot"
source .venv/bin/activate
python3 bridge_simple.py
```

**Tu DOIS voir:**
```
🚀 Starting bridge_simple...
📋 Loaded 18 casinos from JSON
✅ Bot connected and ready
👂 Listening to @Nonoriribot
📤 Sending to risk0_bot API: http://localhost:8080/public/drop
```

**Si "All connection attempts failed":**
- Vérifie que main_new.py tourne dans Terminal 1
- Vérifie http://localhost:8080/docs (doit charger)

---

## 🧪 TEST

### 1. Envoie un screenshot à Nonoriribot

### 2. Vérifie les logs

**Terminal 2 (bridge_simple.py):**
```
📸 Screenshot received from @nonoriribot
🧠 GPT Vision extracted 2 call(s)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 CALL PROCESSING:
Teams: US Sassuolo Calcio vs Pisa Sporting Club
League: Italy - Serie A
Market: Team Total Corners
Time: Tomorrow, 3:00PM
Books: Coolbet vs iBet
Odds: +117 vs +110
Hash: abc123def456789
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Sent to risk0_bot API: abc123def456
✅ Sent: US Sassuolo Calcio vs Pisa Sporting Club
📊 1/2 sent
```

**Terminal 1 (main_new.py):**
```
Received drop: abc123def456
Sending alert to 1 users...
```

**Si doublon détecté:**
```
🚨 DUPLICATE event_id: abc123def456 - Skipping send to users
```

### 3. Vérifie ton message Telegram

**Format CORRECT:**
```
🚨 ARBITRAGE ALERT - 6.3% 🚨

🏟️ US Sassuolo Calcio vs Pisa Sporting Club
⚽ Italy - Serie A - Team Total Corners
🕐 Tomorrow, 3:00PM

💰 CASHH: $699.0
✅ Guaranteed Profit: $46.98

❄️ [Coolbet] Pisa Sporting Club Over 4
💵 Stake: $343.77 (+117) → Return: $745.98

📱 [iBet] Pisa Sporting Club Under 4
💵 Stake: $355.23 (+110) → Return: $745.98
```

**Vérifie:**
- ✅ Pas de "@ +117" (juste "+117" entre parenthèses après Stake)
- ✅ Time affiché "🕐 Tomorrow, 3:00PM"
- ✅ Pas de doublon (même call envoyé 1 seule fois)

---

## 🔧 SI ENCORE DES DOUBLONS

1. **Arrête tout:**
```bash
# Terminal 1: Ctrl+C
# Terminal 2: Ctrl+C
```

2. **Vide la DB de déduplication:**
```bash
rm calls_simple.db
rm arbitrage_bot.db
```

3. **Redémarre:**
```bash
# Terminal 1
python3 main_new.py

# Terminal 2 (attends que Terminal 1 soit prêt)
python3 bridge_simple.py
```

---

## 🐛 DEBUG

### Voir les calls en DB (pour vérifier déduplication)
```bash
sqlite3 arbitrage_bot.db "SELECT event_id, match, received_at FROM drop_events ORDER BY received_at DESC LIMIT 10;"
```

### Voir les logs en temps réel
```bash
# Terminal 1
python3 main_new.py 2>&1 | tee main_new.log

# Terminal 2
python3 bridge_simple.py 2>&1 | tee bridge_simple.log
```

---

## ❓ QUESTIONS FRÉQUENTES

**Q: Je reçois encore "@ +154"**
A: Tu utilises probablement main.py au lieu de main_new.py. Vérifie le nom du fichier lancé.

**Q: Je reçois des doublons**
A: 
1. Vérifie que main_new.py affiche "🚨 DUPLICATE event_id: ..." dans les logs
2. Si non, vide la DB et redémarre
3. Vérifie que tu n'as pas plusieurs instances de main_new.py qui tournent

**Q: Pas de time affiché**
A: GPT n'a pas extrait le time. Vérifie que le screenshot contient bien "Tomorrow, X:XXam" en haut à droite.

**Q: Bridge dit "All connection attempts failed"**
A: main_new.py ne tourne pas. Lance-le d'abord dans Terminal 1.

---

## ✅ CHECKLIST FINALE

Avant de tester:
- [ ] Terminal 1: main_new.py tourne et affiche "Uvicorn running on http://0.0.0.0:8080"
- [ ] Terminal 2: bridge_simple.py tourne et affiche "📤 Sending to risk0_bot API: http://localhost:8080/public/drop"
- [ ] http://localhost:8080/docs charge dans le navigateur
- [ ] Pas d'autres instances de main*.py qui tournent (`ps aux | grep main`)
- [ ] DB vidées si problème de doublons persistants

---

**Maintenant teste et partage les logs des 2 terminaux si ça marche pas!**
