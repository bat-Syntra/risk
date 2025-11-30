#!/bin/bash
# Script pour démarrer le bot de façon stable

# Tuer tous les processus Python existants
killall -9 python3 2>/dev/null
sleep 2

# Tuer tout ce qui occupe le port 8080
lsof -ti:8080 | xargs kill -9 2>/dev/null
sleep 2

# Démarrer le bot
cd "/Users/z/Library/Mobile Documents/com~apple~CloudDocs/risk0-bot"
python3 main_new.py &

echo "Bot démarré! PID: $!"
echo "Logs: tail -f /tmp/live_bot.log"
