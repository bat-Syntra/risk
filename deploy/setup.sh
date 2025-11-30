#!/usr/bin/env bash
# ArbitrageBot VPS One-Click Setup (Ubuntu 22.04/24.04)
# - Installs Python, PostgreSQL, optional Nginx + Certbot
# - Creates linux user, clones repo to /opt/arbitrage-bot, sets up venv
# - Creates .env, systemd service, firewall rules
# - Starts the bot as a service (24/7)
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ===== USER VARS (EDIT BEFORE RUN) =====
BOT_TOKEN="${BOT_TOKEN:-REPLACE_ME_BOT_TOKEN}"
ADMIN_CHAT_ID="${ADMIN_CHAT_ID:-0}"      # e.g. 123456789 (single admin chat for admin messages)
ADMIN_IDS="${ADMIN_IDS:-}"               # e.g. 123,456 (comma-separated)
REPO_URL="${REPO_URL:-REPLACE_ME_GIT_REPO_URL}"  # https://github.com/you/risk0-bot.git
DOMAIN="${DOMAIN:-}"              # optional, e.g. bot.example.com (enables nginx + https)
PORT="${PORT:-8080}"            # internal app port

# DB settings (local postgres)
DB_NAME="${DB_NAME:-arbitrage_bot}"
DB_USER="${DB_USER:-arbitrage_user}"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 24 | tr -d '\n' | sed 's/[^a-zA-Z0-9]/A/g')}"

# ===== System prep =====
echo -e "${GREEN}📦 Updating system...${NC}"
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y git curl wget build-essential ca-certificates lsb-release apt-transport-https

# Python 3.11 + venv
echo -e "${GREEN}🐍 Installing Python 3.11...${NC}"
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip || true
if ! command -v python3.11 >/dev/null 2>&1; then
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo apt-get update -y
  sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
fi

# PostgreSQL
echo -e "${GREEN}🐘 Installing PostgreSQL...${NC}"
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql

# Create DB/user
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || sudo -u postgres createdb ${DB_NAME}
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" || true
sudo -u postgres psql -c "ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};" || true

# Linux user + app dir
echo -e "${GREEN}👤 Creating app user & directory...${NC}"
sudo id -u arbitragebot >/dev/null 2>&1 || sudo useradd -m -s /bin/bash arbitragebot
sudo mkdir -p /opt/arbitrage-bot
sudo chown -R arbitragebot:arbitragebot /opt/arbitrage-bot

# Clone repo
echo -e "${GREEN}📥 Cloning repository...${NC}"
if [ -z "$REPO_URL" ] || [ "$REPO_URL" = "REPLACE_ME_GIT_REPO_URL" ]; then
  echo -e "${RED}Set REPO_URL to your git repository URL, then re-run.${NC}"
  exit 1
fi
sudo -u arbitragebot bash -lc "cd /opt/arbitrage-bot && git init && git remote add origin $REPO_URL || true && git fetch origin && git checkout -f origin/main || git checkout -f origin/master"

# Python venv + deps
echo -e "${GREEN}🔧 Creating virtualenv & installing dependencies...${NC}"
sudo -u arbitragebot bash -lc "cd /opt/arbitrage-bot && python3.11 -m venv venv && ./venv/bin/pip install --upgrade pip && ./venv/bin/pip install -r requirements.txt"

# .env
echo -e "${GREEN}⚙️ Writing .env...${NC}"
cat <<EOF | sudo tee /opt/arbitrage-bot/.env >/dev/null
# Telegram
TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
ADMIN_CHAT_ID=${ADMIN_CHAT_ID}
ADMIN_IDS=${ADMIN_IDS}
BOT_USERNAME=

# Database (local)
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}

# HTTP
PORT=${PORT}

# OpenAI (optional)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
EOF
sudo chown arbitragebot:arbitragebot /opt/arbitrage-bot/.env
sudo chmod 600 /opt/arbitrage-bot/.env

# systemd service
echo -e "${GREEN}🧩 Creating systemd service...${NC}"
cat <<'EOF' | sudo tee /etc/systemd/system/arbitrage-bot.service >/dev/null
[Unit]
Description=Arbitrage Bot (Telegram + FastAPI)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=arbitragebot
Group=arbitragebot
WorkingDirectory=/opt/arbitrage-bot
EnvironmentFile=-/opt/arbitrage-bot/.env
ExecStart=/opt/arbitrage-bot/venv/bin/python -u main_new.py
Restart=always
RestartSec=5
# Journald logging
StandardOutput=journal
StandardError=journal
# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/arbitrage-bot

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable arbitrage-bot

# Nginx + TLS (optional when DOMAIN set)
if [ -n "$DOMAIN" ]; then
  echo -e "${GREEN}🌐 Installing Nginx + Certbot...${NC}"
  sudo apt-get install -y nginx certbot python3-certbot-nginx
  sudo bash -lc "cat >/etc/nginx/sites-available/arbitrage-bot <<NGINX\nserver {\n  server_name ${DOMAIN};\n  client_max_body_size 20m;\n  location / {\n    proxy_set_header Host \$host;\n    proxy_set_header X-Real-IP \$remote_addr;\n    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;\n    proxy_set_header X-Forwarded-Proto \$scheme;\n    proxy_read_timeout 300;\n    proxy_pass http://127.0.0.1:${PORT};\n  }\n}\nNGINX"
  sudo ln -sf /etc/nginx/sites-available/arbitrage-bot /etc/nginx/sites-enabled/arbitrage-bot
  sudo nginx -t && sudo systemctl reload nginx
  sudo certbot --nginx -d "$DOMAIN" --agree-tos -m you@example.com --non-interactive || true
fi

# Firewall
echo -e "${GREEN}🔥 Configuring UFW...${NC}"
sudo ufw --force enable
sudo ufw allow OpenSSH
if [ -n "$DOMAIN" ]; then
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
else
  sudo ufw allow ${PORT}/tcp
fi

# Start service
echo -e "${GREEN}🚀 Starting Arbitrage Bot...${NC}"
sudo systemctl restart arbitrage-bot
sleep 2
sudo systemctl --no-pager --full status arbitrage-bot || true

echo -e "${YELLOW}DB Credentials${NC}: user=${DB_USER} pass=${DB_PASSWORD} db=${DB_NAME}"
echo -e "${GREEN}Done. Use: journalctl -u arbitrage-bot -f${NC} to watch logs."
