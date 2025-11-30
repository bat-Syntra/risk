#!/bin/bash
#
# VPS SETUP SCRIPT for Risk0 Bot
# Run this on a fresh Ubuntu VPS
#

set -e

echo "🚀 Risk0 VPS Setup Script"
echo "========================="

# Update system
echo "📦 Updating system..."
apt update && apt upgrade -y

# Install dependencies
echo "📦 Installing dependencies..."
apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Create directories
mkdir -p /var/log/risk0 /var/run/risk0

# Clone or update repo
if [ -d "/root/risk0-bot" ]; then
    echo "📥 Updating existing repo..."
    cd /root/risk0-bot
    git pull
else
    echo "📥 Cloning repo..."
    cd /root
    git clone https://github.com/bat-Syntra/risk.git risk0-bot
    cd /root/risk0-bot
fi

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# Copy .env if not exists
if [ ! -f "/root/risk0-bot/.env" ]; then
    echo "⚠️ Please create /root/risk0-bot/.env with your configuration"
    cp /root/risk0-bot/.env.example /root/risk0-bot/.env
fi

# Make scripts executable
chmod +x /root/risk0-bot/vps_monitor.sh
chmod +x /root/risk0-bot/deploy/*.sh

# Setup systemd service
echo "🔧 Setting up systemd service..."
cp /root/risk0-bot/deploy/risk0.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable risk0

# Initialize database
echo "💾 Initializing database..."
cd /root/risk0-bot
python3 -c "from database import Base, engine; Base.metadata.create_all(engine)"

# Run migrations
echo "🔄 Running migrations..."
for migration in migrations/*.py; do
    if [ -f "$migration" ]; then
        echo "Running $migration..."
        python3 "$migration" || true
    fi
done

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit /root/risk0-bot/.env with your configuration"
echo "2. Start service: systemctl start risk0"
echo "3. Check status: systemctl status risk0"
echo "4. View logs: tail -f /var/log/risk0/*.log"
echo ""
echo "🌐 API will be available at: http://YOUR_VPS_IP:8080"
echo "🔌 WebSocket: ws://YOUR_VPS_IP:8080/api/web/ws"
