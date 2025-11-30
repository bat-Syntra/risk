# 🔍 VÉRIFICATION DES COTES - COMMENT ÇA MARCHE

## ✅ **CE QUI EST VÉRIFIÉ**

Quand tu cliques "🔍 Vérifier Cotes", le système:

### **1. Appelle VRAIMENT The Odds API**
```python
url = "https://api.the-odds-api.com/v4/sports/{sport}/odds"
params = {
    'markets': 'h2h,spreads,totals',  # Marchés standards
    'bookmakers': 'bet365,pinnacle,betsson,...'
}
```

### **2. Cherche ton match**
- Scanne tous les events en cours
- Compare équipes
- Trouve le marché (ML, Spread, Total)

### **3. Compare les cotes**
- Cotes originales vs Cotes actuelles
- Calcule le % de changement
- Détermine si mieux/pire/identique

---

## ⚠️ **LIMITATIONS DE L'API**

### **Player Props = PAS DISPONIBLES** ❌

**The Odds API ne fournit PAS de vérification temps réel pour:**
- ✗ Player Passing Yards
- ✗ Player Rushing Yards  
- ✗ Player Receiving Yards
- ✗ Player Points/Rebounds/Assists
- ✗ Player Made Threes
- ✗ Etc.

**Exemple:**
```
Market: "1st Half Player Passing Yards - Quan Roberson"
Status: ❌ UNAVAILABLE
Raison: Player props pas dans l'API
```

**Solution:** Vérifiez manuellement sur le site du bookmaker

---

### **Bookmakers supportés**

| Bookmaker | Supporté par API | Vérification |
|-----------|------------------|--------------|
| **bet365** | ✅ OUI | Fonctionne |
| **Pinnacle** | ✅ OUI | Fonctionne |
| **Betsson** | ✅ OUI | Fonctionne |
| **LeoVegas** | ✅ OUI | Fonctionne |
| **Coolbet** | ✅ OUI | Fonctionne |
| **Betway** | ✅ OUI | Fonctionne |
| **888sport** | ✅ OUI | Fonctionne |
| **Sports Interaction** | ✅ OUI | Fonctionne |
| **BET99** | ❌ NON | Fallback bet365 |
| **Mise-o-jeu** | ❌ NON | Fallback bet365 |
| **iBet** | ❌ NON | Fallback bet365 |
| **Proline** | ❌ NON | Fallback bet365 |

---

## 📊 **CE QUE TU VERRAS**

### **Cas 1: Cotes trouvées et vérifiées** ✅

```
Outcome 1: bet365
• Lakers ML
• ✅ Unchanged (1.95)

Outcome 2: Pinnacle
• Celtics ML  
• 📈 Better! 2.10 → 2.15 (+2.4%)

📊 RÉSUMÉ:
✅ Vérifiés: 2
📈 Améliorés: 1
📉 Détériorés: 0
❌ Indisponibles: 0

✅ Recommandation: Les cotes sont bonnes!
```

---

### **Cas 2: Player Prop (unavailable)** ⚠️

```
Outcome 1: LeoVegas
• Quan Roberson 99.5
• ⚠️ Player prop - API ne fournit pas de vérification
   Market: 1st Half Player Passing Yards
   Cotes originales: 2.43
   💡 Vérifiez manuellement sur LeoVegas

Outcome 2: Betsson
• Quan Roberson 109.5
• ⚠️ Player prop - API ne fournit pas de vérification
   Market: 1st Half Player Passing Yards
   Cotes originales: 2.30
   💡 Vérifiez manuellement sur Betsson

📊 RÉSUMÉ:
✅ Vérifiés: 0
❌ Indisponibles: 2 (player props)

⚠️ Recommandation: Vérification manuelle nécessaire
```

---

### **Cas 3: Match pas trouvé** ⚠️

```
Outcome 1: bet365
• Lakers ML
• ⚠️ Non trouvé dans The Odds API
   Cherché: Lakers vs Celtics - Moneyline
   Bookmaker: bet365
   Events scannés: 42
   Cotes originales: 1.95
   💡 Vérifiez manuellement sur bet365

Possibles raisons:
- Match déjà commencé
- Cotes retirées par le bookmaker
- Nom d'équipe différent dans l'API
- Marché spécifique non standard
```

---

## 🎯 **TRANSPARENCE**

Le système te dit EXACTEMENT ce qui s'est passé:

| Message | Signification |
|---------|---------------|
| `✅ Unchanged (X.XX)` | Cotes vérifiées et identiques |
| `📈 Better! X → Y (+Z%)` | Cotes AMÉLIORÉES - bon signe! |
| `📉 Worse! X → Y (-Z%)` | Cotes PIRES - recalculez |
| `⚠️ Player prop - API ne fournit pas` | Player prop = vérif manuelle |
| `⚠️ Non trouvé dans The Odds API` | Match/marché pas dans l'API |
| `❌ API error: 429` | Rate limit dépassé |
| `❌ API error: 401` | Clé API invalide |

---

## 💡 **CONSEILS**

### **Pour Player Props:**
1. ⚠️ Vérification automatique impossible
2. ✅ Va sur le site du bookmaker manuellement
3. ✅ Compare avec tes cotes originales
4. ✅ Décide si tu veux placer

### **Pour Marchés Standards (ML, Spread, Total):**
1. ✅ Vérification automatique fonctionne
2. ✅ Fais confiance au système
3. ✅ Suit les recommandations

### **Si "unavailable" répété:**
- ⚠️ Match peut avoir commencé
- ⚠️ Cotes retirées par bookmakers
- ⚠️ Vérification manuelle recommandée

---

## 🔬 **SOUS LE CAPOT**

### **Le système fait:**

```
1. Détecte le type de pari
   ↓
2a. SI player prop → SKIP API (pas dispo)
   ↓ Message transparent
   
2b. SI marché standard → Appelle API
   ↓
3. Scanne events retournés (ex: 42 events)
   ↓
4. Cherche match exact
   ↓
5a. SI trouvé → Compare cotes
   ↓ Message avec nouvelles cotes
   
5b. SI pas trouvé → Message détaillé
   ↓ "Non trouvé, 42 events scannés"
```

---

## 📈 **LOGS DEBUG**

Dans le terminal, tu verras:

```
📊 API returned 42 events for americanfootball_ncaaf
🔍 Searching for: Buffalo vs Ohio - 1st Half Player Passing Yards
⚠️ Player prop detected, skipping API verification
```

Ou:

```
📊 API returned 38 events for basketball_nba
🔍 Searching for: Lakers vs Celtics - Moneyline
✅ Found match! Current odds: 1.95 (unchanged)
```

---

## ✅ **CONCLUSION**

Le système:
- ✅ Vérifie VRAIMENT via l'API (quand possible)
- ✅ Est TRANSPARENT sur les limitations
- ✅ Montre les NOUVELLES cotes quand trouvées
- ✅ Explique POURQUOI quand pas trouvé
- ✅ Te guide sur quoi faire

**Pour player props:** Vérification manuelle nécessaire (limitation de l'API)

**Pour tout le reste:** Le système fonctionne! 🎯
