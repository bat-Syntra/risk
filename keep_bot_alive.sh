#!/bin/bash
# Script pour garder le bot toujours actif

while true; do
    # Vérifie si le bot tourne
    if ! pgrep -f "python3 main_new.py" > /dev/null; then
        echo "[$(date)] ⚠️ Bot DOWN - Redémarrage..."
        cd "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/risk0-bot"
        
        # Nettoie port 8080
        lsof -ti:8080 | xargs kill -9 2>/dev/null
        sleep 2
        
        # Relance le bot
        python3 main_new.py >> /tmp/bot_auto.log 2>&1 &
        echo "[$(date)] ✅ Bot redémarré!"
    fi
    
    # Vérifie toutes les 30 secondes
    sleep 30
done
