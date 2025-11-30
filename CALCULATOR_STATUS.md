# ✅ CALCULATEUR CUSTOM - REFONTE TOTALE

## TERMINÉ
- ✅ Menu principal ultra-simple avec contexte du call
- ✅ Mode SAFE avec format OddsJam (clair, arrondis suggérés, noms bookmakers)
- ✅ Explication MODE RISKED conversationnelle
- ✅ FSM States ajoutés

## EN COURS
- 🔄 Handler "Changer CASHH temporairement" avec FSM
- 🔄 Handler "Changer les cotes" avec FSM conversation
- 🔄 Compléter flow RISKED (% → choix côté → calcul détaillé)

## FORMAT ULTRA-CLAIR (FAIT)
Avant:
```
RISKED — risk 5% | favor A
Stakes: A=$287 B=$213
Profits: A=$75 B=$-25 | R/R 3.04
```

Après:
```
✅ CALCUL ARBITRAGE - MODE SAFE

💰 CASHH: $500.00
✅ Profit garanti: $28.30 (5.66%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔶 [Betsson] Over 5
Cote: +100
💵 Miser: $264.15
📈 Si gagne → Retour: $528.30

❄️ [Coolbet] Under 5
Cote: +124
💵 Miser: $235.85
📈 Si gagne → Retour: $528.30
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Résumé:
• Total misé: $500.00
• Retour garanti: $528.30
• Profit: $28.30
• ROI: 5.66%

⚠️ Arrondis tes stakes:
🔶 Betsson: $264 ou $265
❄️ Coolbet: $236 ou $235
```

## PROCHAINES ÉTAPES
1. Tester le menu principal et SAFE mode
2. Implémenter les handlers manquants
3. Compléter RISKED flow
