# 📊 MARCHÉS - VÉRIFICATION AUTOMATIQUE

## ✅ **MARCHÉS SUPPORTÉS** (Vérification Auto OK)

### **Tous les sports:**
- ✅ **Moneyline** (ML) - Qui gagne le match
- ✅ **Spread** - Handicap
- ✅ **Totals** - Over/Under points totaux du match

### **Exemples:**
```
✅ Montreal Canadiens ML @ -150
✅ Dallas Cowboys +7.5 @ -110
✅ Over 220.5 Total Points @ +140
```

**Ces marchés sont vérifiables automatiquement via The Odds API** ✅

---

## ❌ **MARCHÉS NON SUPPORTÉS** (Vérification Manuelle)

### **Marchés spécifiques:**
- ❌ **Corners** (Team Total Corners, Total Corners, etc.)
- ❌ **Cards** (Yellow Cards, Red Cards, Bookings)
- ❌ **Shots** (Shots on Target, Total Shots)
- ❌ **Fouls** (Total Fouls, etc.)
- ❌ **Player Props** (Player Points, Receiving Yards, etc.)
- ❌ **Team Totals spécifiques** (Team Total Points une équipe)
- ❌ **Other specials** (First Goal, Anytime Goalscorer, etc.)

### **Exemples:**
```
❌ Team Total Corners - Over 5.5
❌ Player Receiving Yards - Over 59.5
❌ Yellow Cards - Over 2.5
❌ Anytime Goalscorer
```

**Ces marchés nécessitent vérification manuelle** ⚠️

---

## 📱 **CE QUE TU VERRAS**

### **Marché Supporté (Moneyline, Spread, Totals):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 VÉRIFICATION (11:45)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 2 cotes vérifiées

💡 Action: Les cotes sont bonnes!
```

---

### **Marché Non Supporté (Corners):**

**AVANT (confus):**
```
⚠️ Vérification automatique non disponible pour ce type de pari.
💡 Action: Vérifiez manuellement sur les sites des bookmakers.
```

**MAINTENANT (clair):**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 VÉRIFICATION (11:45)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Corners non disponibles pour vérification automatique

💡 Action: Vérifiez manuellement sur LeoVegas et Betsson
(Marchés spécifiques non supportés par API)
```

**Le bot détecte et nomme le type de marché!** ✅

---

### **Player Props:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 VÉRIFICATION (11:12)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Player props détectés
La vérification automatique n'est pas disponible 
pour les paris sur joueurs.

💡 Action: Vérifiez manuellement sur les sites 
des bookmakers avant de placer.
```

---

## 🎯 **DÉTECTION AUTOMATIQUE**

Le bot détecte automatiquement:

| Mot-clé dans Market | Type Détecté | Message |
|---------------------|--------------|---------|
| CORNER | Corners | "Corners non disponibles" |
| CARD, YELLOW, RED | Cards | "Cards non disponibles" |
| BOOKING | Bookings | "Bookings non disponibles" |
| SHOT | Shots | "Shots non disponibles" |
| FOUL | Fouls | "Fouls non disponibles" |
| PLAYER, RECEIVING, etc. | Player Props | "Player props détectés" |

**Plus de messages génériques!** ✅

---

## 🔧 **POURQUOI CES LIMITATIONS?**

### **The Odds API Standard:**

L'API fournit seulement les marchés principaux:
- `h2h` (Moneyline)
- `spreads` (Handicap)
- `totals` (Over/Under match totals)

### **Marchés spéciaux:**

Les corners, cards, player props, etc. nécessitent:
- Des endpoints spécifiques (non disponibles)
- Des providers différents ($$$ coûteux)
- Scraping direct des sites (complexe)

**Pour l'instant, vérification manuelle nécessaire** ⚠️

---

## 💡 **RECOMMANDATIONS**

### **Pour les marchés supportés:**
1. Clique "🔍 Vérifier Cotes"
2. Le bot te dira si les cotes ont changé
3. Décide si tu places quand même

### **Pour les marchés non supportés:**
1. Le bot te dira clairement le type (Corners, Cards, etc.)
2. Ouvre les sites des bookmakers manuellement
3. Vérifie les cotes toi-même avant de placer

**Toujours vérifier manuellement pour les marchés spéciaux!** 🎯

---

## 🚀 **FUTUR (Possible Extensions)**

Si besoin d'ajouter support pour marchés spéciaux:
- 💰 Upgrade API plan (plus cher)
- 🔌 Scraping direct des bookmakers
- 🤝 Partenariats avec providers de données

**Pour l'instant, focus sur marchés principaux** ✅

---

## ✅ **RÉSUMÉ**

| Type de Marché | Support | Message |
|----------------|---------|---------|
| Moneyline | ✅ Auto | "X cotes vérifiées" |
| Spread | ✅ Auto | "X cotes vérifiées" |
| Totals (match) | ✅ Auto | "X cotes vérifiées" |
| Corners | ❌ Manuel | "Corners non disponibles" |
| Cards | ❌ Manuel | "Cards non disponibles" |
| Player Props | ❌ Manuel | "Player props détectés" |
| Autres spéciaux | ❌ Manuel | "Vérification manuelle" |

**Le bot est maintenant transparent sur ce qu'il peut et ne peut pas vérifier!** 🎯
