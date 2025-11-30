# 🔧 CONFLIT NOM DE VARIABLE `text` CORRIGÉ!

## ❌ **ERREUR**

```
UnboundLocalError: cannot access local variable 'text' where it is not associated with a value
```

**Traceback:**
```python
File "bot/parlay_preferences_handler.py", line 1295, in _build_parlays_list
    result = db.execute(text("""
                        ^^^^
UnboundLocalError: cannot access local variable 'text' where it is not associated with a value
```

---

## 🎯 **CAUSE DU PROBLÈME**

### **Conflit de noms!**

En Python, si tu ASSIGNES une variable dans une fonction, Python considère cette variable comme **LOCALE** dans TOUTE la fonction.

**Exemple du problème:**

```python
from sqlalchemy import text  # Import SQLAlchemy

async def my_function():
    # Ligne 10: Utilise text() de SQLAlchemy
    result = db.execute(text("""SELECT..."""))  # ❌ ERREUR!
    
    # ... 100 lignes plus tard...
    
    # Ligne 110: Crée une variable locale text
    text = "Mon message"  # ← Python voit ça AVANT l'exécution!
    
    return {'text': text}
```

**Ce qui se passe:**
1. Python scanne TOUTE la fonction
2. Voit `text = "..."` à la ligne 110
3. Décide que `text` est une **variable locale**
4. À la ligne 10, quand tu essaies d'utiliser `text(...)`, Python dit:
   - "Tu essaies d'utiliser la variable locale `text`"
   - "Mais elle n'est pas encore assignée!"
   - **UnboundLocalError!** ❌

---

## ✅ **SOLUTIONS APPLIQUÉES**

### **Fix 1: Fonction `_build_parlays_list()`**

**Fichier:** `bot/parlay_preferences_handler.py` (ligne 1387)

**AVANT:**
```python
async def _build_parlays_list(user_id: int):
    # Ligne 1295: Utilise text() de SQLAlchemy
    result = db.execute(text("""SELECT..."""))  # ❌ ERREUR!
    
    # ... code ...
    
    # Ligne 1387: Crée variable locale text
    text = (  # ❌ Conflit!
        f"🎯 PARLAYS D'AUJOURD'HUI..."
    )
    
    return {'text': text}
```

**MAINTENANT:**
```python
async def _build_parlays_list(user_id: int):
    # Ligne 1295: Utilise text() de SQLAlchemy
    result = db.execute(text("""SELECT..."""))  # ✅ Fonctionne!
    
    # ... code ...
    
    # Ligne 1387: Variable renommée
    message_text = (  # ✅ Pas de conflit!
        f"🎯 PARLAYS D'AUJOURD'HUI..."
    )
    
    return {'text': message_text}
```

---

### **Fix 2: Fonction `cmd_report_odds()`**

**Fichier:** `bot/parlay_preferences_handler.py` (ligne 1460)

**AVANT:**
```python
async def cmd_report_odds(message: types.Message):
    # Ligne 1433: Utilise text() de SQLAlchemy
    result = db.execute(text("""SELECT..."""))  # ❌ ERREUR!
    
    # ... code ...
    
    # Ligne 1460: Crée variable locale text
    for bet in bets:
        text = f"{bet.bookmaker}..."  # ❌ Conflit!
        keyboard_buttons.append([
            types.InlineKeyboardButton(text=text[:50])
        ])
```

**MAINTENANT:**
```python
async def cmd_report_odds(message: types.Message):
    # Ligne 1433: Utilise text() de SQLAlchemy
    result = db.execute(text("""SELECT..."""))  # ✅ Fonctionne!
    
    # ... code ...
    
    # Ligne 1460: Variable renommée
    for bet in bets:
        button_text = f"{bet.bookmaker}..."  # ✅ Pas de conflit!
        keyboard_buttons.append([
            types.InlineKeyboardButton(text=button_text[:50])
        ])
```

---

## 📊 **RÉSUMÉ DES CHANGEMENTS**

| Fonction | Ligne | Ancien Nom | Nouveau Nom | Raison |
|----------|-------|------------|-------------|--------|
| `_build_parlays_list()` | 1387 | `text` | `message_text` | Conflit avec `text()` SQLAlchemy |
| `cmd_report_odds()` | 1460 | `text` | `button_text` | Conflit avec `text()` SQLAlchemy |

---

## 💡 **POURQUOI C'EST IMPORTANT**

### **Règle Python: Variables locales**

```python
from sqlalchemy import text  # text est dans le scope global

def my_func():
    # Si tu fais ça ANYWHERE dans la fonction:
    text = "something"
    
    # Alors Python considère 'text' comme LOCAL dans TOUTE la fonction
    # Même AVANT cette ligne!
```

### **Comment éviter:**

1. **Ne jamais réutiliser les noms d'imports comme variables locales**
   ```python
   # ❌ MAUVAIS
   from sqlalchemy import text
   text = "mon message"  # Conflit!
   
   # ✅ BON
   from sqlalchemy import text
   message_text = "mon message"  # Pas de conflit!
   ```

2. **Ou utiliser des alias d'import**
   ```python
   # Alternative
   from sqlalchemy import text as sql_text
   
   # Maintenant tu peux utiliser:
   result = db.execute(sql_text("""SELECT..."""))
   text = "mon message"  # Pas de conflit!
   ```

---

## 🧪 **TESTS**

### **Test 1: Build parlays list**
```bash
# Clique sur "Parlays" depuis le menu
# Devrait afficher la liste sans erreur ✅
```

### **Test 2: Report odds**
```bash
# Tape /report_odds
# Devrait afficher les paris actifs sans erreur ✅
```

---

## 📝 **LEÇON APPRISE**

### **Évite ces noms de variables:**

Quand tu utilises ces imports:
```python
from sqlalchemy import text
from aiogram import types
from datetime import datetime
```

**Ne crée JAMAIS de variables locales avec ces noms:**
- ❌ `text = "..."`
- ❌ `types = [...]`
- ❌ `datetime = "..."`

**Utilise plutôt:**
- ✅ `message_text = "..."`
- ✅ `button_text = "..."`
- ✅ `response_text = "..."`
- ✅ `user_types = [...]`
- ✅ `current_datetime = "..."`

---

## 🎯 **AUTRES ENDROITS OÙ ÇA POURRAIT ARRIVER**

### **Patterns à surveiller:**

```python
# DANGER: Importe text de SQLAlchemy
from sqlalchemy import text

# Plus tard dans la fonction...
text = f"Mon message {var}"  # ❌ CONFLIT!

# Solution:
message_text = f"Mon message {var}"  # ✅
```

```python
# DANGER: Importe types d'aiogram
from aiogram import types

# Plus tard...
types = ['admin', 'user']  # ❌ CONFLIT!

# Solution:
user_types = ['admin', 'user']  # ✅
```

---

## ✅ **STATUS FINAL**

- ✅ `_build_parlays_list()` corrigé
- ✅ `cmd_report_odds()` corrigé
- ✅ Tous les fichiers compilent
- ✅ Aucun autre conflit détecté

---

## 🚀 **PROCHAINES ÉTAPES**

1. **Redémarre le bot**
2. **Teste "Parlays"** - Devrait afficher la liste ✅
3. **Teste tous les boutons** - Tout devrait fonctionner ✅
4. **Surveille les logs** - Plus d'erreur UnboundLocalError ✅

---

## 🔍 **DEBUG SI PROBLÈME PERSISTE**

Si tu vois encore cette erreur:
```
UnboundLocalError: cannot access local variable 'X' where it is not associated with a value
```

**Checklist:**
1. ✅ Trouve l'import: `from module import X`
2. ✅ Trouve la variable locale: `X = ...`
3. ✅ Renomme la variable locale: `my_X = ...`
4. ✅ Mets à jour toutes les références à cette variable

**Commande pour trouver:**
```bash
grep -n "text = " bot/parlay_preferences_handler.py
# Cherche toutes les assignations de 'text'
```

---

## 📚 **RESSOURCES**

### **Python Variable Scoping:**
- Variables locales vs globales
- Règle LGB (Local, Global, Built-in)
- `UnboundLocalError` expliquée

### **Best Practices:**
- Éviter les noms de variables qui masquent les imports
- Utiliser des noms descriptifs (`message_text` au lieu de `text`)
- Activer les warnings du linter

---

**Tout devrait fonctionner maintenant!** 🎉

Redémarre le bot et teste les parlays! ✅
