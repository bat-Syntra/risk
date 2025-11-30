# 📊 État des Liens Directs par Bookmaker

## Résumé Exécutif

- **Bookmakers avec liens fonctionnels**: 3/18 (17%)
- **Bookmakers avec liens potentiels (patterns manuels)**: 9/18 (50%)
- **Bookmakers fallback homepage uniquement**: 6/18 (33%)

## 🟢 FONCTIONNELS (Level 1 - The Odds API)

Ces bookmakers retournent des liens directs depuis The Odds API avec `includeLinks=true`:

| Bookmaker | API Key | Exemple de lien | Status |
|-----------|---------|-----------------|---------|
| LeoVegas | `leovegas` | `https://www.leovegas.com/en-ca/betting#event/1024877487` | ✅ Confirmé |
| Coolbet | `coolbet` | `https://www.coolbet.ca/en/sports/match/4677959` | ✅ Confirmé |
| Betsson | `betsson` | `https://www.betsson.com/en-ca/sportsbook/.../eventId=...` | ✅ Confirmé |

## 🟡 PATTERNS MANUELS (Level 3)

Ces bookmakers sont dans The Odds API mais ne retournent pas de liens. On utilise des patterns manuels:

| Bookmaker | Pattern | Testé | Notes |
|-----------|---------|-------|-------|
| bet365 | `https://www.bet365.ca/#/HO/{eventId}` | ⏳ | Peut nécessiter SID |
| Betway | `https://betway.ca/en/sports/evt/{eventId}` | ⏳ | Format event ID incertain |
| Pinnacle | `https://www.pinnacle.com/en/{sport}/{match-slug}` | ⏳ | Nécessite slug du match |
| bwin | `https://sports.bwin.ca/en/sports/{sport}/{eventId}` | ⏳ | À tester |
| 888sport | `https://www.888sport.com/ca/sports/{sport}/{eventId}` | ⏳ | À tester |
| BetVictor | `https://www.betvictor.com/en-ca/sports/{sport}/{eventId}` | ⏳ | À tester |

## 🔴 BOOKMAKERS CANADIENS (Level 2/4)

Ces bookmakers ne sont PAS dans The Odds API standard. Options:

| Bookmaker | Solution | Status | Notes |
|-----------|----------|---------|-------|
| BET99 | OpticOdds API | ❌ | Fallback homepage |
| Sports Interaction | OpticOdds API | ❌ | Fallback homepage |
| Proline | OpticOdds API | ❌ | Ontario uniquement |
| Mise-o-jeu | OpticOdds API | ❌ | Québec uniquement |

## ⚫ PETITS BOOKMAKERS (Level 4)

Pas dans l'API, fallback sur homepage:

| Bookmaker | Homepage |
|-----------|----------|
| iBet | `https://www.ibet.ca` |
| Jackpot.bet | `https://jackpot.bet` |
| Stake | `https://stake.com/sports` |
| Casumo | `https://www.casumo.com/en-ca/sports` |
| TonyBet | `https://tonybet.ca` |

## 📈 Roadmap d'Amélioration

### Phase 1 (Immédiat)
- [x] Implémenter BookmakerLinkResolver à 4 niveaux
- [x] Ajouter patterns manuels pour bet365, Betway, Pinnacle
- [ ] Tester les patterns sur de vrais events
- [ ] Ajuster selon résultats

### Phase 2 (Court terme)
- [ ] Investiguer les SIDs pour bet365/Betway
- [ ] Mapper les event IDs entre systèmes
- [ ] Améliorer le matching d'outcomes

### Phase 3 (Moyen terme)
- [ ] Intégrer OpticOdds pour bookmakers canadiens
- [ ] Ajouter cache persistant des event IDs
- [ ] Monitoring des taux de succès

## 🧪 Comment Tester

```bash
# Tester tous les bookmakers
python3 test_link_resolver.py --all

# Tester un bookmaker spécifique
python3 test_link_resolver.py --bookmaker BET99

# Tester la fonction v2
python3 test_link_resolver.py --v2
```

## 📝 Notes Importantes

1. **Event IDs**: Les IDs de The Odds API ne correspondent pas toujours aux IDs internes des bookmakers
2. **Transformation UK→CA**: Critique pour LeoVegas, Coolbet, Betsson
3. **Player Props**: Nécessitent un marché différent (`player_points`, etc.)
4. **Cache**: 5 minutes pour éviter les appels répétés
5. **Fallback**: Toujours retourner au moins la homepage

## 🔧 Debug Tips

Si un lien ne marche pas:
1. Vérifier dans les logs quel niveau a été utilisé
2. Tester manuellement le pattern avec un vrai event ID
3. Vérifier si le bookmaker est dans la région demandée
4. Essayer avec différents marchés (h2h, totals, spreads)
