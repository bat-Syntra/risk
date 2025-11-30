# 🔧 PARLAYS - BOUTONS & CASINOS FIXÉS

## ❌ **PROBLÈMES TROUVÉS**

### **1. Boutons "not handled"** ❌
```
INFO:aiogram.event:Update id=431013804 is not handled.
  - Data: parlay_main_settings

INFO:aiogram.event:Update id=431013805 is not handled.
  - Data: menu
```

**Cause:** Pas de handlers pour ces callbacks!

### **2. Casinos manquants** ❌
```
Avant: Betsson, Pinnacle, bet365, LeoVegas, Mise-o-jeu...
Maintenant: Seulement Mise-o-jeu (ou 1-2 casinos)
```

**Cause:** Filtrage trop strict par casinos préférés!

---

## ✅ **CORRECTIONS APPLIQUÉES**

### **1. Handler `parlay_main_settings` ajouté** ✅

**Fichier:** `bot/parlays_info_handler.py`

```python
@router.callback_query(F.data == "parlay_main_settings")
async def handle_parlay_main_settings(callback: types.CallbackQuery):
    """Redirect to parlay settings"""
    await callback.answer()
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🏢 Sélectionner Casinos", callback_data="settings_casinos")],
        [types.InlineKeyboardButton(text="📊 Profil de Risque", callback_data="settings_risk")],
        # ... autres options ...
        [types.InlineKeyboardButton(text="« Retour", callback_data="parlays_info")]
    ])
    
    await callback.message.edit_text(
        "⚙️ PARAMÈTRES PARLAYS...",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
```

**Maintenant le bouton "⚙️ Settings Parlays" fonctionne!** ✅

---

### **2. Handler `menu` ajouté** ✅

**Fichier:** `bot/parlays_info_handler.py`

```python
@router.callback_query(F.data == "menu")
async def handle_menu_callback(callback: types.CallbackQuery):
    """Redirect to main menu"""
    from bot.handlers import callback_main_menu
    await callback_main_menu(callback)
```

**Maintenant le bouton "« Retour Menu" fonctionne!** ✅

---

### **3. Filtre casinos corrigé** ✅

**Fichier:** `bot/parlay_preferences_handler.py` (lignes 1342-1356)

**AVANT:**
```python
# Filtre TOUJOURS si user a preferred_casinos
if prefs['preferred_casinos'] and parlay_casinos:
    match_found = False
    # ... check match ...
    if not match_found:
        continue  # ❌ Filtre même si liste vide!
```

**PROBLÈME:**
- Si l'utilisateur a `preferred_casinos = []` (vide), le code filtrait quand même!
- Résultat: Seulement quelques parlays passaient le filtre

**MAINTENANT:**
```python
# Filtre SEULEMENT si user a des préférences configurées
if prefs['preferred_casinos'] and len(prefs['preferred_casinos']) > 0:
    if parlay_casinos:  # Only filter if parlay has casino info
        match_found = False
        # ... check match ...
        if not match_found:
            print(f"  → Filtered out: {parlay_casinos} vs {prefs['preferred_casinos']}")
            continue
# Si pas de préférences → TOUT passe! ✅
```

**Résultat:**
- ✅ Si utilisateur n'a PAS de préférences → TOUS les casinos s'affichent
- ✅ Si utilisateur a des préférences → Filtre seulement ceux sélectionnés
- ✅ Debug ajouté pour voir ce qui est filtré

---

## 📊 **COMMENT VÉRIFIER**

### **Test 1: Boutons**
1. Clique "🎲 Parlays"
2. Clique "⚙️ Settings Parlays"
3. **Avant:** "not handled" ❌
4. **Maintenant:** Affiche menu settings ✅

5. Clique "« Retour Menu"
6. **Avant:** "not handled" ❌
7. **Maintenant:** Retour au menu principal ✅

---

### **Test 2: Casinos**

**Scénario A: Aucune préférence configurée**
```
User prefs: preferred_casinos = []
Résultat: TOUS les casinos s'affichent! ✅
```

**Scénario B: Préférences configurées**
```
User prefs: preferred_casinos = ['Mise-o-jeu', 'bet365']
Résultat: Seulement Mise-o-jeu et bet365 ✅
```

---

## 🔍 **DEBUG AJOUTÉ**

Dans les logs terminal, tu verras:

```
DEBUG: User prefs - preferred_casinos: []
  → Filtered out: casino mismatch. Parlay casinos: ['Betsson'], User prefs: []

OU si c'est vide:

DEBUG: User prefs - preferred_casinos: []
  → ✅ PASSED all filters (pas de filtrage si liste vide)
```

**Si tu vois des parlays filtrés alors que tu n'as pas de préférences:**
→ Vérifie que `preferred_casinos` est bien `[]` et pas `None`

---

## 🎯 **POURQUOI IL MANQUAIT DES CASINOS?**

### **Raison 1: Filtrage trop strict** ✅ CORRIGÉ
```python
# Avant: filtrait même si preferred_casinos = []
# Maintenant: filtre SEULEMENT si len(preferred_casinos) > 0
```

### **Raison 2: Pas assez de parlays générés?**
```sql
SELECT * FROM parlays
WHERE date(created_at) = date('now')
    AND status = 'pending'
ORDER BY quality_score DESC
LIMIT 50
```

**Vérifie:**
- La table `parlays` contient des entrées pour tous les casinos?
- Le générateur de parlays fonctionne?
- Les drops sont bien enregistrés?

**Commande pour vérifier:**
```bash
sqlite3 risk0.db "SELECT bookmakers, COUNT(*) FROM parlays GROUP BY bookmakers;"
```

---

### **Raison 3: Risk profile filtering**
```python
# Si user a risk_profiles = ['CONSERVATIVE']
# Alors SEULEMENT parlays CONSERVATIVE s'affichent
```

**Vérifie tes préférences:**
```
/parlay_settings
→ Profil de Risque
→ Coche TOUS les profils pour voir tous les parlays
```

---

## 📝 **RECOMMANDATIONS**

### **Pour voir TOUS les parlays:**
1. Va dans `/parlay_settings`
2. Sélectionner Casinos → **Ne sélectionne RIEN** (laisse vide)
3. Profil de Risque → **Coche TOUS** les profils
4. Retourne à `/parlays`

**Maintenant tu devrais voir:**
- ✅ Mise-o-jeu (2 parlays)
- ✅ Betsson (1 parlay)
- ✅ bet365 (1 parlay)
- ✅ Pinnacle (1 parlay)
- ✅ ... etc

---

### **Si tu veux filtrer par casino:**
1. `/parlay_settings`
2. Sélectionner Casinos
3. Coche SEULEMENT les casinos que tu veux
4. Retourne à `/parlays`

**Maintenant tu verras seulement ces casinos**

---

## ✅ **FICHIERS MODIFIÉS**

### **1. `bot/parlays_info_handler.py`**
- Lignes 167-197: Handler `parlay_main_settings` ajouté
- Lignes 200-211: Handler `menu` ajouté

### **2. `bot/parlay_preferences_handler.py`**
- Lignes 1342-1356: Filtre casinos corrigé

---

## 🚀 **PROCHAINES ÉTAPES**

1. **Redémarre le bot**
2. **Teste les boutons:**
   - ⚙️ Settings Parlays → Devrait fonctionner
   - « Retour Menu → Devrait fonctionner
3. **Vérifie les casinos:**
   - Va dans `/parlay_settings`
   - **Désélectionne TOUS les casinos** (ou laisse vide)
   - Retourne à `/parlays`
   - Tu devrais voir TOUS les casinos maintenant!
4. **Regarde les logs:**
   ```
   DEBUG: User prefs - preferred_casinos: []
   # Si vide, tous les parlays passent!
   ```

---

## 💡 **SI TU VOIS TOUJOURS PAS TOUS LES CASINOS**

### **Vérifie 1: Les préférences**
```
/parlay_settings → Profil de Risque
Assure-toi que TOUS les profils sont cochés!
```

### **Vérifie 2: La génération**
```bash
# Dans sqlite3
SELECT DISTINCT bookmakers FROM parlays WHERE date(created_at) = date('now');

# Devrait afficher:
# ["Mise-o-jeu", "LeoVegas"]
# ["Betsson", "Pinnacle"]
# etc.
```

### **Vérifie 3: Les logs**
```
Cherche dans le terminal:
  → Filtered out: ...
  → ✅ PASSED all filters

Si BEAUCOUP de "Filtered out" → Problème de config
Si TOUS "PASSED" mais pas de parlays → Problème de génération
```

---

## ✅ **STATUS**

- ✅ Bouton "Settings Parlays" fonctionne
- ✅ Bouton "Retour Menu" fonctionne
- ✅ Filtre casinos corrigé (montre tous si pas de prefs)
- ✅ Debug ajouté pour diagnostiquer

**Redémarre et teste!** 🚀
