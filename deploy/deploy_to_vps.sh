#!/bin/bash
#
# DEPLOY TO VPS - Quick deploy script
# Usage: ./deploy_to_vps.sh user@your-vps-ip
#

if [ -z "$1" ]; then
    echo "Usage: $0 user@vps-ip"
    echo "Example: $0 root@123.45.67.89"
    exit 1
fi

VPS="$1"
REMOTE_DIR="/root/risk0-bot"

echo "🚀 Deploying to $VPS..."

# Sync code (excluding sensitive files)
rsync -avz --progress \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude '*.db' \
    --exclude '*.session' \
    --exclude 'node_modules' \
    --exclude 'venv' \
    ./ $VPS:$REMOTE_DIR/

# Restart service on VPS
echo "🔄 Restarting service..."
ssh $VPS "cd $REMOTE_DIR && systemctl restart risk0"

# Show status
echo "📊 Service status:"
ssh $VPS "systemctl status risk0 --no-pager | head -20"

echo ""
echo "✅ Deploy complete!"
echo "📋 View logs: ssh $VPS 'tail -f /var/log/risk0/*.log'"
