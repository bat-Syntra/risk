#!/usr/bin/env bash

set -euo pipefail

mkdir -p logos
cd logos

# nom|domaine
sites=(
  "888sport|888sport.com"
  "bet105|bet105.com"
  "BET99|bet99.com"
  "Betsson|betsson.com"
  "BetVictor|betvictor.com"
  "Betway|betway.com"
  "bwin|bwin.com"
  "Casumo|casumo.com"
  "Coolbet|coolbet.com"
  "iBet|ibet.com"
  "Jackpot.bet|jackpot.bet"
  "LeoVegas|leovegas.com"
  "Mise-o-jeu|miseojeu.lotoquebec.com"
  "Pinnacle|pinnacle.com"
  "Proline|proline.ca"
  "Sports_Interaction|sportsinteraction.com"
  "Stake|stake.com"
  "TonyBet|tonybet.com"
)

for entry in "${sites[@]}"; do
  IFS="|" read -r name domain <<< "$entry"
  url="https://logo.clearbit.com/$domain"
  echo "Téléchargement de $name depuis $url"
  # -f = échoue si 404, -L = suit les redirections
  if ! curl -fL "$url" -o "${name}.png" 2>/dev/null; then
    echo "  ⚠️  Échec pour $name ($domain)"
  fi
done

echo "Terminé. Tous les fichiers PNG disponibles sont dans le dossier ./logos"