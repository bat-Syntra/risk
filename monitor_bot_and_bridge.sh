#!/bin/bash
# Monitor main_new.py (bot) + bridge_simple.py and restart if they crash.
# Also notifies admin on Telegram when a restart happens.

ROOT_DIR="/Users/z/Library/Mobile Documents/com~apple~CloudDocs/risk0-bot"
cd "$ROOT_DIR" || exit 1

# Load .env if present (for TELEGRAM_BOT_TOKEN, DEFAULT_OWNER_ID)
if [ -f .env ]; then
  # shellcheck disable=SC2046
  export $(grep -E '^(TELEGRAM_BOT_TOKEN|DEFAULT_OWNER_ID)=' .env | xargs)
fi

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
ADMIN_ID="${DEFAULT_OWNER_ID:-}"

notify_admin() {
  local msg="$1"
  echo "[$(date)] $msg"
  if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$ADMIN_ID" ]; then
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d chat_id="$ADMIN_ID" \
      --data-urlencode text="$msg" >/dev/null 2>&1 || true
  fi
}

start_bot() {
  # Kill anything on 8080 to avoid bind errors
  lsof -ti:8080 | xargs kill -9 2>/dev/null || true
  sleep 2
  python3 main_new.py >> /tmp/bot_auto.log 2>&1 &
  notify_admin "⚠️ Bot RISK0 relancé automatiquement (main_new.py)."
}

start_bridge() {
  # Use venv if exists
  if [ -d .venv ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
  fi
  python3 bridge_simple.py >> /tmp/bridge_auto.log 2>&1 &
  notify_admin "⚠️ Bridge OddsJam (bridge_simple.py) relancé automatiquement."
}

check_bot_health() {
  # Returns 0 if healthy, 1 otherwise
  curl -s --max-time 3 http://localhost:8080/health >/dev/null 2>&1
}

while true; do
  # 1) Check bot health via /health
  if ! check_bot_health; then
    # If process existe encore, kill and restart
    pkill -f "python3 main_new.py" 2>/dev/null || true
    start_bot
  fi

  # 2) Check bridge process
  if ! pgrep -f "bridge_simple.py" >/dev/null 2>&1; then
    start_bridge
  fi

  # 3) Sleep before next check
  sleep 30
done
