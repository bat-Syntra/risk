# 🧪 Guide de Test - Système Feedback & Vouch

## ✅ Checklist de Test

### 1. Test des boutons sur confirmation de bet

#### Test Arbitrage:
1. Place un bet arbitrage
2. Confirme le bet comme gagné
3. Vérifie que tu vois:
   - ✅ Message de confirmation
   - 🗑️ Bouton "Supprimer ce message"
   - 👍 Bouton "Bon feedback"
   - 👎 Bouton "Mauvais feedback"
   - 🎉 Bouton "VOUCH" (seulement si profit > 0)

#### Test Middle:
1. Place un bet middle
2. Confirme le résultat (Jackpot, Arbitrage, ou Perdu)
3. Vérifie les mêmes boutons que ci-dessus

#### Test Good EV:
1. Place un bet Good EV
2. Confirme comme gagné ou perdu
3. Vérifie les boutons

### 2. Test bouton CLEAR (Supprimer)

1. Clique sur 🗑️ "Supprimer ce message"
2. ✅ Le message doit disparaître complètement
3. ✅ Pas d'erreur

### 3. Test bouton FEEDBACK

#### Bon feedback:
1. Clique sur 👍 "Bon feedback"
2. ✅ Tu reçois un popup "Merci pour ton feedback positif!"
3. ✅ L'admin reçoit une notification avec:
   - Username
   - Type: GOOD
   - Bet Type
   - Montant et profit
   - Match info
   - Date/heure

#### Mauvais feedback:
1. Clique sur 👎 "Mauvais feedback"
2. ✅ Tu reçois un popup "Feedback reçu"
3. ✅ L'admin reçoit une notification (⚠️)

### 4. Test bouton VOUCH

1. Sur un bet GAGNANT avec profit > 0
2. Clique sur 🎉 "VOUCH (témoigner)"
3. ✅ Tu reçois un popup "Merci pour ton VOUCH!"
4. ✅ L'admin reçoit une notification avec:
   - Username
   - Profit détaillé
   - ROI
   - Type de bet
   - Match info
   - Sport
   - Emojis selon le montant (🚀🔥 si $500+, etc.)

#### Test différents niveaux de profit:
- [ ] Vouch avec profit < $50 → Emoji ✅
- [ ] Vouch avec profit $50-100 → Emoji ✅💚
- [ ] Vouch avec profit $100-200 → Emoji ✨💰
- [ ] Vouch avec profit $200-500 → Emoji 🔥💰
- [ ] Vouch avec profit $500+ → Emoji 🚀🎰🔥

### 5. Test menu admin `/feedbacks`

1. En tant qu'admin, tape `/feedbacks`
2. ✅ Tu vois le menu avec 5 boutons:
   - 📝 Nouveaux Feedbacks
   - 📜 Tous les Feedbacks
   - 🎉 Nouveaux Vouches
   - 📜 Tous les Vouches
   - 📊 Statistiques

#### Test "Nouveaux Feedbacks":
1. Clique sur "📝 Nouveaux Feedbacks"
2. ✅ Affiche tous les feedbacks non vus
3. ✅ Marque automatiquement comme vus
4. ✅ Détails corrects affichés
5. ✅ Bouton "◀️ Retour" fonctionne

#### Test "Tous les Feedbacks":
1. Clique sur "📜 Tous les Feedbacks"
2. ✅ Affiche l'historique groupé par date
3. ✅ Limite à 50 derniers
4. ✅ Format correct

#### Test "Nouveaux Vouches":
1. Clique sur "🎉 Nouveaux Vouches"
2. ✅ Affiche tous les vouches non vus
3. ✅ Emojis corrects selon profit
4. ✅ Toutes les infos présentes
5. ✅ Marque comme vus

#### Test "Tous les Vouches":
1. Clique sur "📜 Tous les Vouches"
2. ✅ Groupés par date
3. ✅ Total journalier affiché
4. ✅ Format correct

#### Test "Statistiques":
1. Clique sur "📊 Statistiques"
2. ✅ Total feedbacks (positifs/négatifs)
3. ✅ Total vouches
4. ✅ Profit total et moyen
5. ✅ Plus gros vouch affiché
6. ✅ Répartition par type de bet

### 6. Test cas limites

#### Bet perdu (pas de bouton Vouch):
- [ ] Confirme un bet comme perdu
- [ ] ✅ Pas de bouton "VOUCH"
- [ ] ✅ Boutons Clear et Feedback présents

#### Double vouch:
- [ ] Vouch une première fois
- [ ] Essaye de vouch à nouveau
- [ ] ✅ Message "Tu as déjà vouch pour ce bet!"

#### Navigation menu admin:
- [ ] Navigue entre différentes sections
- [ ] ✅ Boutons "Retour" fonctionnent
- [ ] ✅ Pas de duplication de menus

### 7. Test base de données

1. Vérifie que les tables existent:
```bash
# Si SQLite
sqlite3 arbitrage_bot.db
.tables
# Tu dois voir: user_feedbacks, user_vouches
```

2. Vérifie qu'un feedback est sauvegardé:
```sql
SELECT * FROM user_feedbacks ORDER BY created_at DESC LIMIT 1;
```

3. Vérifie qu'un vouch est sauvegardé:
```sql
SELECT * FROM user_vouches ORDER BY created_at DESC LIMIT 1;
```

## 🎯 Scénario de test complet

### Scénario 1: User gagne un gros bet Middle
1. User place un middle bet de $550
2. Middle HIT (Jackpot) → profit $44.83
3. User confirme "🎰 JACKPOT!"
4. Bot envoie confirmation avec 4 boutons
5. User clique "🎉 VOUCH"
6. Admin reçoit notification avec emojis ✨💰
7. User clique "🗑️ Supprimer"
8. Message disparaît
9. Admin ouvre `/feedbacks` → voit le vouch dans "Nouveaux Vouches"
10. Stats affichent +1 vouch, +$44.83 profit

### Scénario 2: User a un problème
1. User place arbitrage bet
2. Confirme comme gagné
3. Clique "👎 Mauvais feedback"
4. Admin reçoit notification ⚠️
5. Admin enquête sur le problème

### Scénario 3: Admin review quotidien
1. Admin tape `/feedbacks`
2. Clique "Nouveaux Vouches" → voit 5 nouveaux vouches
3. Clique "Nouveaux Feedbacks" → voit 2 feedbacks négatifs
4. Clique "Statistiques" → overview de la journée
5. Prend actions correctives si nécessaire

## 📊 Métriques de succès

- ✅ Tous les boutons fonctionnent sans erreur
- ✅ Notifications admin arrivent instantanément
- ✅ Data persistée correctement en DB
- ✅ Menu admin rapide et responsive
- ✅ Pas de crash ou bugs
- ✅ UX fluide et intuitive

## 🐛 Debugging

Si erreurs:
1. Check logs: `tail -f logs/bot.log`
2. Check DB: `sqlite3 arbitrage_bot.db`
3. Check imports dans `main_new.py`
4. Vérifie que ADMIN_TELEGRAM_ID est correct dans `.env`

## 📝 Feedback sur le système

Après les tests, note:
- [ ] Ce qui fonctionne bien
- [ ] Ce qui pourrait être amélioré
- [ ] Bugs rencontrés
- [ ] Features manquantes
