# 🚀 GUIDE DE TEST - On commence ICI!

## 📋 Checklist rapide

```bash
# 1. Active ton environnement
source .venv/bin/activate

# 2. Installe Playwright (si pas fait)
pip install playwright
playwright install chromium
```

## 🎯 Test 1: Les liens directs (30 secondes)

```bash
python test_direct_links.py
```

**Ce que ça fait:**
- Génère des liens directs pour BET99 et Coolbet
- Te montre les URLs
- **0$ de coût, instantané**

**Vérifie:**
1. Copie un des liens affichés
2. Ouvre-le dans Chrome
3. Est-ce que tu arrives sur la bonne page?
   - ✅ OUI → Continue au Test 2
   - ❌ NON → Les URLs ont besoin d'ajustement

---

## 🔍 Test 2: Extraction sans screenshots (2 minutes)

```bash
python test_verify_odds.py
```

**Ce que ça fait:**
- Ouvre un browser VISIBLE (tu vois tout!)
- Va sur BET99 et Coolbet
- Cherche "Myles Turner"
- Essaie d'extraire les cotes du DOM

**Observe:**
- Est-ce qu'il trouve le joueur?
- Est-ce que la recherche marche?
- Tu vois les cotes sur la page?

---

## 🤖 Test 3: Intégration complète (1 minute)

```bash
python test_full_integration.py
```

**Ce que ça fait:**
- Parse un vrai message d'arbitrage
- Génère les liens et boutons Telegram
- Simule le flow complet

**Résultat attendu:**
```
✅ Parse les messages
✅ Génère les liens directs  
✅ Crée les boutons Telegram
```

---

## ⚡ Test RAPIDE en 1 commande

```bash
# Lance les 3 tests d'un coup
python -c "
import subprocess
tests = ['test_direct_links.py', 'test_verify_odds.py', 'test_full_integration.py']
for test in tests:
    print(f'\n🚀 Running {test}...\n')
    subprocess.run(['python', test])
"
```

---

## 🔧 Si ça marche pas

### Erreur: "No module named utils"
```bash
# Assure-toi d'être dans le bon dossier
cd /Users/z/Library/Mobile\ Documents/com~apple~CloudDocs/risk0-bot
```

### Erreur: "playwright not found"
```bash
pip install playwright
playwright install chromium
```

### Les liens marchent pas
- Les casinos ont peut-être changé leurs URLs
- Ouvre `utils/smart_casino_navigator.py`
- Ajuste les patterns dans `QUEBEC_CASINOS`

---

## ✅ Si tout marche

**Intégration dans ton bot:**

1. Dans ton handler d'arbitrage existant:
```python
from bot.odds_verifier import OddsVerifier

verifier = OddsVerifier()

# Quand tu reçois un arbitrage
message, keyboard = await verifier.create_arbitrage_message(arb_data, user_id)
await bot.send_message(user_id, message, reply_markup=keyboard)
```

2. C'est tout! Les liens sont déjà dans les boutons!

---

## 💰 Économies

| Avant | Maintenant | Économies |
|-------|------------|-----------|
| Screenshots + Claude Vision | Liens directs | 100% gratuit |
| $0.003 par vérification | $0.00 | $450/mois |
| 15-20 secondes | Instantané | 100x plus rapide |

---

## 🎯 Commence par le Test 1!

```bash
python test_direct_links.py
```

**Ça prend 30 secondes et tu verras tout de suite si ça marche!** 🚀
