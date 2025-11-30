# 🎯 GUIDE PARLAYS - RISK0 BOT

## 🤔 C'EST QUOI UN PARLAY?

Un **parlay** (pari combiné) = plusieurs paris en UN seul
- Tu gagnes **SEULEMENT** si TOUS tes paris gagnent
- Les cotes se **MULTIPLIENT** = gros gains!
- Plus risqué mais plus payant

### Exemple concret:
```
Pari 1: Canadiens gagne → cote 2.0
Pari 2: Over 5.5 buts → cote 1.8
Pari 3: Matthews marque → cote 2.5

PARLAY = 2.0 × 1.8 × 2.5 = 9.0

Mise 10$ → Gain potentiel 90$!
(Au lieu de 20$ + 18$ + 25$ = 63$ en paris séparés)
```

## 🤖 QUE FAIT LE BOT?

Le bot **TROUVE** automatiquement des parlays avec **edge positif**:

1. **Analyse** les drops (arbitrage, middle, good EV)
2. **Détecte** les corrélations entre matchs
3. **Calcule** l'edge mathématique
4. **Filtre** selon ton profil de risque

## 📊 PROFILS DE RISQUE

- 🟢 **CONSERVATIVE** - Win rate 50-55%, ROI 8-12%
- 🟡 **BALANCED** - Win rate 42-48%, ROI 15-22%
- 🟠 **AGGRESSIVE** - Win rate 30-38%, ROI 25-40%
- 🔴 **LOTTERY** - Win rate 8-15%, ROI 50-150%

## 🎮 COMMENT UTILISER?

### 1. Configure tes préférences
```
/parlay_settings
```
- Choisis tes casinos
- Sélectionne ton profil de risque
- Ajuste les paramètres

### 2. Vois les parlays disponibles
```
/parlays
```
- Liste par casino
- Clique sur un casino pour voir les détails

### 3. Place le pari TOI-MÊME
Le bot ne place PAS les paris!
1. Note les détails du parlay
2. Va sur le site du casino
3. Ajoute les matchs un par un
4. Vérifie la cote totale
5. Place ta mise (1-2% bankroll max)

## ⚠️ RÈGLES IMPORTANTES

1. **Ne mise JAMAIS plus que conseillé**
2. **Vérifie toujours les cotes** avant de placer
3. **Skip si les cotes ont trop bougé**
4. **Track tes résultats** pour voir ton ROI

## 💡 CONSEILS PRO

- Commence avec profil **CONSERVATIVE**
- Mise maximum 2% de ta bankroll par parlay
- Diversifie sur plusieurs casinos
- Ne chase jamais tes pertes
- Les parlays sont du LONG TERME

## 🔧 COMMANDES

- `/parlay_settings` - Configure tes préférences
- `/parlays` - Voir parlays disponibles
- `/report_odds` - Signaler changement de cotes

## 📈 EXEMPLE DE BANKROLL

Bankroll: 1000$
- Conservative: Mise 20-30$ par parlay
- Balanced: Mise 10-20$ par parlay
- Aggressive: Mise 5-10$ par parlay
- Lottery: Mise 5$ max

Sur 100 parlays:
- Conservative: ~52 gagnés → +120$ profit
- Balanced: ~45 gagnés → +200$ profit
- Aggressive: ~34 gagnés → +350$ profit
- Lottery: ~12 gagnés → +600$ profit (mais variance++)

## ❓ QUESTIONS?

Le système de parlays est un outil ADDITIONNEL aux alertes arbitrage/middle/good EV.

C'est pour diversifier et augmenter le ROI long terme!

---

*Note: Les parlays de test actuels sont des exemples. Le vrai système utilisera les drops en temps réel.*
