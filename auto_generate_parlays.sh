#!/bin/bash
#
# Script d'automatisation de génération de parlays
# À lancer toutes les 6 heures via cron
#

# Couleurs pour logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Répertoire du projet
PROJECT_DIR="/Users/z/Library/Mobile Documents/com~apple~CloudDocs/risk0-bot"
cd "$PROJECT_DIR"

# Activer l'environnement virtuel
source "$PROJECT_DIR/.venv/bin/activate"

echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} Début de génération automatique des parlays"

# Générer les parlays à partir des drops existants
echo -e "${YELLOW}→${NC} Génération des parlays..."
python3 "$PROJECT_DIR/smart_parlay_generator.py"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Parlays générés avec succès!"
else
    echo -e "${RED}✗${NC} Erreur lors de la génération (exit code: $EXIT_CODE)"
fi

echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} Fin de génération"
echo ""
