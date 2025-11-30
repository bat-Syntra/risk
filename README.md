<p align="center">
  <img src="assets/risk0_logo.png" alt="Risk0 Logo" width="160"/>
</p>

![Python](https://img.shields.io/badge/python-3.10+-blue.svg) ![Telegram](https://img.shields.io/badge/Telegram-aiogram%203-green.svg)

# Risk0 Bot (autonome)

## Description

Bot Telegram aiogram v3 autonome, sans Syntra. Affiche un drop de bet, calcule les mises pour 3 profils (safe/balanced/aggressive) selon un budget saisi, et mémorise le dernier budget (JSON local). Le bot expose aussi une API FastAPI pour publier automatiquement sur Telegram à partir d'un drop JSON (`/public/drop`) ou d'un e‑mail brut parsé par IA (`/public/email`).

- Test rapide:

```bash
curl -X POST http://localhost:8080/public/drop \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "test_evt_1",
    "league": "MLB",
    "event": "Chicago Cubs vs Milwaukee Brewers",
    "kickoff_iso": "2025-10-08T17:08:00-04:00",
    "market": "Player Hits",
    "player": "Jackson Chourio",
    "edge_percent": 2.2,
    "selection_over":  {"label":"Over 1.5 hits","american":250, "book":"LeoVegas","url":"https://leovegas.com?aff=RISK0"},
    "selection_under": {"label":"Under 1.5 hits","american":-225,"book":"BetVictor","url":"https://betvictor.com?btag=RISK0"}
  }'
```

- Boutons dynamiques:
  - Rangée 1: Books (urls affiliées si fournies; fallback via mapping `AFFILIATES` dans `config.py`)
  - Rangée 2: "Calculer profit / mise" (ouvre la saisie budget)
  - Rangée 3: "Copier"

## Intégration Gmail (survol)

- Créez un filtre Gmail qui applique le label `RISK0/DROP` aux alertes.
- Un script Google Apps Script (déclencheur toutes les minutes) lit ce label, parse l'email, et POST le JSON au webhook `/public/drop`.
- Voir l'exemple de script dans la conversation ou adaptez vos regex à votre format d'alerte. Points clés:
  - Générer `event_id` unique
  - Extraire `player`, `market`, cotes `american`, `book`, `url` affiliées
  - Poster vers `https://votre-domaine/public/drop`

## Tests rapides

- Entrer différents budgets (10, 100, 250, 1000) et vérifier:
  - Safe: profit garanti positif
  - Balanced/Aggressive: formules cohérentes
- Vérifier que le dernier budget réapparaît à la prochaine demande
- Vérifier la stabilité si l’utilisateur envoie du texte non numérique
- Tester `/public/drop` avec `curl` et vérifier la présence des boutons dynamiques

## Webhook `/public/email`

- Endpoint: `POST /public/email`
- Body attendu:

```json
{
  "subject": "Arbitrage Bet Notification: ...",
  "body": "Event: ...\nPlayer: ...\nOverOdds: +250\nUnderOdds: -225\n..."
}
```

- Test rapide:

```bash
curl -X POST http://localhost:8080/public/email \
  -H 'Content-Type: application/json' \
  -d '{
    "subject": "Arbitrage Bet Notification: MLB",
    "body": "Event: Chicago Cubs vs Milwaukee Brewers\nPlayer: Jackson Chourio\nMarket: Player Hits\nLeague: MLB\nOverOdds: +250\nUnderOdds: -225\nEdge: 2.2\nKickoff: 2025-10-08T17:08:00-04:00\nOverBook: LeoVegas\nUnderBook: BetVictor"
  }'
```

- Effet: le bot parse l'e‑mail via OpenAI (fallback regex si besoin), génère une image depuis `assets/base_template.png` + `assets/risk0_logo.png`, et poste l'image + le menu dans `ADMIN_CHAT_ID`.

## Assets

- Placez vos fichiers dans `assets/`:
  - `assets/base_template.png` (ex: 1080x1350)
  - `assets/risk0_logo.png` (PNG, fond transparent)
  - `assets/Inter-Regular.ttf` (police)
- Par défaut, les chemins peuvent être surchargés via env:
  - `RISK0_BASE_TEMPLATE`, `RISK0_LOGO`, `RISK0_FONT`
- Si un asset manque, un fallback sobre est utilisé (fond uni, police par défaut).

## Critères d’acceptation

- Lancement local sans erreur
- Réponse `/start` avec le drop statique et le bouton de calcul
- Dialogue budget → résultats avec 3 profils
- Recalculer et Copier disponibles
- Mémoire du dernier budget opérationnelle (`risk0_memory.json`)
- Réception d'un JSON `/public/drop` → envoi automatique du menu Telegram
- Ajout d’un mode personnalisé de ratio (ex: 60/40)

## Licence

Projet privé © Risk0 Labs — réservé à un usage interne et expérimental. Tous droits réservés.
