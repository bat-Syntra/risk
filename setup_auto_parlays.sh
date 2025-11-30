#!/bin/bash
#
# Installation automatique du système de parlays
#

echo "🚀 Installation du système intelligent de parlays..."
echo ""

# Vérifier que le script existe
SCRIPT_PATH="/Users/z/Library/Mobile Documents/com~apple~CloudDocs/risk0-bot/auto_generate_parlays.sh"
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Erreur: Script auto_generate_parlays.sh introuvable"
    exit 1
fi

# Rendre le script exécutable
chmod +x "$SCRIPT_PATH"
echo "✅ Script rendu exécutable"

# Créer la ligne cron
CRON_LINE="0 */6 * * * $SCRIPT_PATH >> /tmp/parlay_gen.log 2>&1"

# Vérifier si déjà installé
if crontab -l 2>/dev/null | grep -q "auto_generate_parlays.sh"; then
    echo "⚠️  Cron job déjà installé!"
    echo ""
    read -p "Voulez-vous le réinstaller? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation annulée."
        exit 0
    fi
    
    # Supprimer l'ancienne entrée
    crontab -l 2>/dev/null | grep -v "auto_generate_parlays.sh" | crontab -
    echo "✅ Ancienne entrée supprimée"
fi

# Ajouter la nouvelle entrée
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
echo "✅ Cron job installé!"

echo ""
echo "📅 Horaire de génération automatique:"
echo "   • 00:00 (minuit)"
echo "   • 06:00 (matin)"
echo "   • 12:00 (midi)"
echo "   • 18:00 (soir)"
echo ""
echo "📊 Logs disponibles dans: /tmp/parlay_gen.log"
echo ""
echo "🔍 Pour vérifier l'installation:"
echo "   crontab -l"
echo ""
echo "🚀 Pour tester manuellement:"
echo "   cd '/Users/z/Library/Mobile Documents/com~apple~CloudDocs/risk0-bot'"
echo "   ./auto_generate_parlays.sh"
echo ""
echo "✅ Installation terminée!"
