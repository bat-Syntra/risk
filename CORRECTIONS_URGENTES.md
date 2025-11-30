# 🔧 CORRECTIONS URGENTES

## ✅ **1. TypeError Parlay - CORRIGÉ**

### **Erreur:**
```
TypeError: '>' not supported between instances of 'str' and 'int'
```

### **Cause:**
`american_odds` était stocké comme string (`"-140"`) au lieu d'int.

### **Correction:**
```python
# Convertir en int avant comparaison
american_odds = leg.get('american_odds', 100)

try:
    american_odds = int(american_odds)
except (ValueError, TypeError):
    american_odds = 100

if american_odds > 0:  # ✅ Maintenant ça marche!
    decimal_odds = (american_odds / 100) + 1
```

**Fichier:** `bot/parlay_preferences_handler.py` (lignes 854-858)

---

## 🔗 **2. Liens Directs - DEBUG AJOUTÉ**

### **Problème:**
Les liens directs ne fonctionnent plus, reviennent aux fallbacks.

### **Causes Possibles:**

#### **A) Casse différente**
```python
deep_links = {"Pinnacle": "https://..."}
casino_name = "pinnacle"  # Lowercase!

# ❌ deep_links.get("pinnacle") → None
```

**Solution:** Match case-insensitive ajouté

#### **B) Clé différente**
```python
deep_links = {"Sports Interaction": "https://..."}
casino_name = "SportsInteraction"  # Pas d'espace!

# ❌ Pas de match
```

#### **C) Enrichissement échoué**
```python
deep_links = {}  # Vide!
# Enrichissement n'a pas fonctionné
```

### **Debug Ajouté:**

```python
# Montre ce qu'on a
print(f"📊 DEBUG deep_links keys: {list(deep_links.keys())}")
print(f"📊 DEBUG outcomes casinos: {[o['casino'] for o in arb_data['outcomes']]}")

# Match case-insensitive
if not link and deep_links:
    for key, value in deep_links.items():
        if key.lower() == casino_name.lower():
            link = value
            break
```

**Fichier:** `main_new.py` (lignes 1235-1258)

---

## 📊 **CE QUE TU VERRAS DANS LES LOGS**

### **Si les liens fonctionnent:**
```
📊 DEBUG deep_links keys: ['Pinnacle', 'bet365']
📊 DEBUG outcomes casinos: ['Pinnacle', 'bet365']
✅ Using deep link for Pinnacle: https://pinnacle.com/...
✅ Using deep link for bet365: https://bet365.com/...
```

### **Si problème de casse:**
```
📊 DEBUG deep_links keys: ['Pinnacle', 'bet365']
📊 DEBUG outcomes casinos: ['pinnacle', 'bet365']
✅ Found deep link via case-insensitive match: pinnacle → Pinnacle
✅ Using deep link for pinnacle: https://pinnacle.com/...
```

### **Si pas de deep_links:**
```
📊 DEBUG deep_links keys: None
📊 DEBUG outcomes casinos: ['Pinnacle', 'bet365']
⚠️ No deep link found for 'Pinnacle', using fallback
⚠️ No deep link found for 'bet365', using fallback
```

### **Si enrichissement a échoué:**
```
⚠️ Could not enrich with API: [error message]
📊 DEBUG deep_links keys: None
⚠️ No deep link found for 'Pinnacle', using fallback
```

---

## 🔍 **DIAGNOSTIC**

### **Pour savoir pourquoi les liens ne marchent pas:**

1. **Envoie un drop test**
2. **Regarde les logs terminal**
3. **Cherche:**
   ```
   🔗 Enriched with API: X deep links found
   ```

**Si X = 0:** L'enrichissement échoue
**Si X > 0 mais liens = fallback:** Problème de matching des noms

4. **Regarde les clés:**
   ```
   📊 DEBUG deep_links keys: [...]
   📊 DEBUG outcomes casinos: [...]
   ```

**Compare les noms!** S'ils sont différents, c'est le problème.

---

## 🎯 **PROCHAINES ÉTAPES**

1. **Redémarre le bot**
2. **Envoie un drop arbitrage ≥3%**
3. **Regarde les logs:**
   - L'enrichissement fonctionne?
   - Les deep_links sont là?
   - Les noms matchent?
4. **Partage les logs ici** si ça ne marche toujours pas

---

## ✅ **STATUS**

- ✅ TypeError parlay: CORRIGÉ
- 🔍 Liens directs: DEBUG ajouté pour diagnostic
- ⏳ En attente de tes logs pour comprendre le problème exact
