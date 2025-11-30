# 🔧 ML CALL LOGGER - TROUBLESHOOTING GUIDE

**Guide de dépannage complet pour le système ML**

---

## 📊 VÉRIFIER L'ÉTAT DU SYSTÈME

### **1. Status dans les logs**

```bash
tail -100 /tmp/bot_auto.log | grep -i "call logger"
```

**Bon signe:**
```
✅ ML Call Logger initialized (background mode - no performance impact)
📊 Call Logger started (background mode)
```

**Mauvais signe:**
```
❌ Failed to initialize call logger
⚠️ Call logger queue full
ERROR:utils.call_logger: ...
```

---

### **2. Vérifier la table SQL**

```bash
cd /Users/z/Library/Mobile\ Documents/com~apple~CloudDocs/risk0-bot
sqlite3 arbitrage_bot.db "SELECT COUNT(*) FROM arbitrage_calls;"
```

**Résultat attendu:** Un nombre (même 0 au début)

**Si erreur "no such table":**
→ La table n'existe pas, relancer la migration

---

### **3. Stats du logger (via bot)**

Commande admin à créer:
```
/ml_stats
```

Affiche:
- Calls loggés avec succès
- Erreurs count
- Taux d'erreur
- Dernière erreur

---

## 🚨 PROBLÈMES COURANTS & SOLUTIONS

### **PROBLÈME 1: Table n'existe pas**

**Symptôme:**
```
ERROR: no such table: arbitrage_calls
```

**Solution:**
```bash
sqlite3 arbitrage_bot.db "
CREATE TABLE IF NOT EXISTS arbitrage_calls (
    call_id TEXT PRIMARY KEY,
    call_type TEXT NOT NULL,
    sport TEXT,
    team_a TEXT,
    team_b TEXT,
    match_date TIMESTAMP,
    book_a TEXT NOT NULL,
    book_b TEXT NOT NULL,
    market TEXT,
    odds_a REAL NOT NULL,
    odds_b REAL NOT NULL,
    roi_percent REAL NOT NULL,
    stake_a REAL,
    stake_b REAL,
    profit_expected REAL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    users_notified INTEGER DEFAULT 0,
    users_clicked INTEGER DEFAULT 0,
    outcome TEXT,
    profit_actual REAL,
    clv_a REAL,
    clv_b REAL
);
"
```

Puis redémarrer le bot.

---

### **PROBLÈME 2: Queue pleine**

**Symptôme:**
```
⚠️ Call logger queue full - skipping call
```

**Cause:** Trop de calls en même temps (>1000)

**Solution:**
1. C'est normal si énormément de calls
2. Le bot continue sans problème
3. Certains calls pas loggés mais bot fonctionne
4. Augmenter la queue si besoin:

```python
# Dans utils/call_logger.py ligne 20
self.queue = asyncio.Queue(maxsize=5000)  # Au lieu de 1000
```

---

### **PROBLÈME 3: Erreurs DB connection**

**Symptôme:**
```
ERROR: database is locked
ERROR: unable to open database file
```

**Causes possibles:**
1. Trop de connexions simultanées
2. Permissions fichier
3. Disk full

**Solutions:**

**A. Vérifier permissions:**
```bash
ls -la arbitrage_bot.db
chmod 644 arbitrage_bot.db
```

**B. Vérifier espace disque:**
```bash
df -h
```

Si <100MB libre → Nettoyer!

**C. Vérifier connexions:**
```bash
lsof | grep arbitrage_bot.db | wc -l
```

Si >50 connexions → Problème de fermeture DB

---

### **PROBLÈME 4: Logger disabled automatiquement**

**Symptôme:**
```
🚨 ML CALL LOGGER - CRITICAL
❌ 100 consecutive errors
🔴 Logger auto-disabled
```

**Cause:** 100 erreurs consécutives

**Solution:**
1. Vérifier ML_TROUBLESHOOTING.md (ce fichier)
2. Fixer le problème root (DB, permissions, etc.)
3. Redémarrer le bot

Le logger se réactivera au redémarrage.

---

### **PROBLÈME 5: Données pas collectées**

**Symptôme:** 
```sql
SELECT COUNT(*) FROM arbitrage_calls; 
-- Retourne 0 même après plusieurs jours
```

**Causes possibles:**

**A. Logger pas intégré dans le code:**
→ Vérifier que `log_call_safe()` est appelé dans l'envoi d'alertes

**B. Logger désactivé:**
```python
# Vérifier dans safe_call_logger
safe_logger.enabled  # Doit être True
```

**C. Aucun call envoyé:**
→ Normal si pas d'arbitrages détectés

---

### **PROBLÈME 6: Performance dégradée**

**Symptôme:** Bot plus lent après activation logger

**Diagnostic:**
```bash
# Vérifier CPU
top -pid $(pgrep -f main_new.py)

# Vérifier mémoire
ps aux | grep main_new.py
```

**Solution:**

**Si CPU >80%:**
1. Augmenter délai dans worker:
```python
# utils/call_logger.py ligne 129
await asyncio.sleep(0.5)  # Au lieu de 0.1
```

**Si Mémoire >500MB:**
1. Réduire taille queue:
```python
self.queue = asyncio.Queue(maxsize=500)  # Au lieu de 1000
```

2. Cleanup plus fréquent:
```python
await logger.cleanup_old_data(days_to_keep=180)  # Au lieu de 365
```

---

### **PROBLÈME 7: Indexes manquants (queries lentes)**

**Symptôme:** Queries ML prennent >5 secondes

**Solution:** Recréer les indexes

```bash
sqlite3 arbitrage_bot.db "
CREATE INDEX IF NOT EXISTS idx_calls_type ON arbitrage_calls(call_type);
CREATE INDEX IF NOT EXISTS idx_calls_sport ON arbitrage_calls(sport);
CREATE INDEX IF NOT EXISTS idx_calls_sent_at ON arbitrage_calls(sent_at);
CREATE INDEX IF NOT EXISTS idx_calls_roi ON arbitrage_calls(roi_percent);
CREATE INDEX IF NOT EXISTS idx_calls_ml ON arbitrage_calls(call_type, sport, sent_at);
"
```

---

## 🔍 DIAGNOSTICS AVANCÉS

### **Test 1: Vérifier que le logger démarre**

```bash
grep "Call Logger started" /tmp/bot_auto.log
```

**Attendu:**
```
INFO:utils.call_logger:📊 Call Logger started (background mode)
```

---

### **Test 2: Test manuel d'insertion**

```bash
sqlite3 arbitrage_bot.db "
INSERT INTO arbitrage_calls (call_id, call_type, sport, team_a, team_b, book_a, book_b, odds_a, odds_b, roi_percent)
VALUES ('test123', 'arbitrage', 'NBA', 'Lakers', 'Celtics', 'bet365', 'Pinnacle', -110, 105, 2.5);

SELECT * FROM arbitrage_calls WHERE call_id = 'test123';
"
```

**Si ça marche:** DB fonctionne, problème dans le code
**Si ça fail:** Problème DB

---

### **Test 3: Vérifier intégration dans le code**

```bash
grep -r "log_call_safe" /Users/z/Library/Mobile\ Documents/com~apple~CloudDocs/risk0-bot/bot/
```

**Attendu:** Au moins 1 résultat

**Si 0 résultats:** Logger pas encore intégré dans l'envoi d'alertes

---

### **Test 4: Monitor en temps réel**

```bash
# Terminal 1: Logs du bot
tail -f /tmp/bot_auto.log | grep -i "call logger"

# Terminal 2: DB en temps réel
watch -n 2 'sqlite3 arbitrage_bot.db "SELECT COUNT(*) FROM arbitrage_calls;"'
```

Envoyer un call et vérifier que le count augmente.

---

## 📋 CHECKLIST DE SANTÉ

### **Avant de lancer en production:**

- [ ] Table `arbitrage_calls` existe
- [ ] Indexes créés (5 indexes)
- [ ] Logger démarre au boot (check logs)
- [ ] Test d'insertion manuelle fonctionne
- [ ] Espace disque >1GB libre
- [ ] Permissions DB correctes (644)
- [ ] Safe logger intégré dans code d'envoi
- [ ] Alertes admin configurées
- [ ] Backup inclut arbitrage_calls

---

## 🚀 OPTIMISATIONS

### **Si beaucoup de calls (>500/jour):**

**1. Batch inserts au lieu de inserts individuels:**

```python
# Dans call_logger.py, modifier _save_to_db pour batch
batch = []
for call in calls:
    batch.append(call_data)
    if len(batch) >= 50:
        db.executemany(INSERT_QUERY, batch)
        batch = []
```

**2. Index partiel pour queries courantes:**

```sql
CREATE INDEX idx_calls_recent 
ON arbitrage_calls(sent_at) 
WHERE sent_at > date('now', '-7 days');
```

**3. Vacuum DB mensuel:**

```bash
sqlite3 arbitrage_bot.db "VACUUM;"
```

---

## 📊 QUERIES UTILES POUR DEBUGGING

### **Vérifier derniers calls:**

```sql
SELECT call_id, call_type, sport, roi_percent, sent_at 
FROM arbitrage_calls 
ORDER BY sent_at DESC 
LIMIT 10;
```

### **Vérifier distribution par sport:**

```sql
SELECT sport, COUNT(*) as count 
FROM arbitrage_calls 
GROUP BY sport 
ORDER BY count DESC;
```

### **Vérifier calls sans résultat:**

```sql
SELECT COUNT(*) 
FROM arbitrage_calls 
WHERE outcome IS NULL 
AND sent_at < datetime('now', '-24 hours');
```

### **Taille de la table:**

```sql
SELECT 
    COUNT(*) as total_calls,
    pg_size_pretty(pg_total_relation_size('arbitrage_calls')) as table_size;
```

---

## 🔧 COMMANDES DE MAINTENANCE

### **Cleanup manuel:**

```bash
sqlite3 arbitrage_bot.db "
DELETE FROM arbitrage_calls 
WHERE sent_at < date('now', '-365 days');
"
```

### **Rebuild indexes:**

```bash
sqlite3 arbitrage_bot.db "
REINDEX arbitrage_calls;
"
```

### **Check DB integrity:**

```bash
sqlite3 arbitrage_bot.db "PRAGMA integrity_check;"
```

**Résultat attendu:** `ok`

---

## 📞 CONTACT SI PROBLÈME

### **Si rien ne marche:**

1. Envoyer à l'admin:
   - Logs: `/tmp/bot_auto.log` (dernières 100 lignes)
   - Output de: `sqlite3 arbitrage_bot.db ".tables"`
   - Output de: `sqlite3 arbitrage_bot.db "SELECT COUNT(*) FROM arbitrage_calls;"`
   - Stats du logger

2. Désactiver temporairement:
```python
# Dans safe_call_logger.py
self.enabled = False
```

3. Bot continue normalement sans ML logging

---

## ✅ SANTÉ DU SYSTÈME

### **Indicateurs verts:**

- ✅ Logger démarre au boot
- ✅ 0 erreurs dans les logs
- ✅ Calls s'accumulent dans DB
- ✅ Queries rapides (<1s)
- ✅ CPU <20%
- ✅ Mémoire <200MB

### **Indicateurs rouges:**

- 🔴 Erreurs répétées dans logs
- 🔴 Table vide après 24h
- 🔴 Queries >5s
- 🔴 CPU >80%
- 🔴 Mémoire >500MB
- 🔴 Disk <100MB

---

## 💡 TIPS

1. **Toujours check les logs en premier**
2. **Test manual insert avant de debugger le code**
3. **Backup DB avant modifications**
4. **Désactiver logger si problèmes critiques**
5. **Bot doit TOUJOURS continuer même si logger fail**

---

**Ce guide couvre 99% des problèmes possibles!**

**Si nouveau problème:** Documenter ici pour la prochaine fois! 📝

---

**Dernière mise à jour:** 29 Nov 2025  
**Version:** 1.0
**Status:** Production Ready
