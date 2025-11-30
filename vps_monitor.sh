#!/bin/bash
#
# VPS MONITOR - Complete monitoring script for Risk0 Bot
# Runs: Bot API, Bridge, Parlay cleanup, Health checks
# WebSocket ready for real-time web updates
#

set -e

# Configuration
BOT_DIR="/root/risk0-bot"
LOG_DIR="/var/log/risk0"
PID_DIR="/var/run/risk0"

# Create directories
mkdir -p $LOG_DIR $PID_DIR

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check if process is running
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Start Bot API (with WebSocket for real-time updates)
start_bot() {
    if is_running "$PID_DIR/bot.pid"; then
        log "Bot already running"
        return 0
    fi
    
    log "Starting Bot API (port 8080)..."
    cd $BOT_DIR
    nohup python3 main_new.py >> $LOG_DIR/bot.log 2>&1 &
    echo $! > $PID_DIR/bot.pid
    sleep 3
    
    if is_running "$PID_DIR/bot.pid"; then
        log "✅ Bot started (PID: $(cat $PID_DIR/bot.pid))"
    else
        error "Failed to start Bot"
        return 1
    fi
}

# Start Bridge (Telegram listener)
start_bridge() {
    if is_running "$PID_DIR/bridge.pid"; then
        log "Bridge already running"
        return 0
    fi
    
    log "Starting Bridge..."
    cd $BOT_DIR
    nohup python3 bridge_simple.py >> $LOG_DIR/bridge.log 2>&1 &
    echo $! > $PID_DIR/bridge.pid
    sleep 3
    
    if is_running "$PID_DIR/bridge.pid"; then
        log "✅ Bridge started (PID: $(cat $PID_DIR/bridge.pid))"
    else
        error "Failed to start Bridge"
        return 1
    fi
}

# Stop all services
stop_all() {
    log "Stopping all services..."
    
    for service in bot bridge; do
        if [ -f "$PID_DIR/${service}.pid" ]; then
            local pid=$(cat "$PID_DIR/${service}.pid")
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null
                log "Stopped $service (PID: $pid)"
            fi
            rm -f "$PID_DIR/${service}.pid"
        fi
    done
    
    # Kill any remaining processes
    pkill -9 -f "python3.*main_new.py" 2>/dev/null || true
    pkill -9 -f "python3.*bridge_simple.py" 2>/dev/null || true
    
    log "All services stopped"
}

# Health check
health_check() {
    local healthy=true
    
    # Check Bot API
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        log "✅ Bot API: healthy"
    else
        error "❌ Bot API: not responding"
        healthy=false
    fi
    
    # Check Bridge
    if is_running "$PID_DIR/bridge.pid"; then
        log "✅ Bridge: running"
    else
        warn "❌ Bridge: not running"
        healthy=false
    fi
    
    # Check WebSocket (through health endpoint)
    local ws_check=$(curl -s http://localhost:8080/health 2>/dev/null)
    if [ -n "$ws_check" ]; then
        log "✅ WebSocket: ready"
    fi
    
    if [ "$healthy" = true ]; then
        return 0
    else
        return 1
    fi
}

# Cleanup expired parlays (run periodically)
cleanup_parlays() {
    log "Cleaning up expired parlays..."
    cd $BOT_DIR
    python3 cleanup_expired_parlays.py >> $LOG_DIR/cleanup.log 2>&1
}

# Monitor loop - keeps services running
monitor_loop() {
    log "Starting monitor loop..."
    
    local cleanup_counter=0
    
    while true; do
        # Check and restart services if needed
        if ! is_running "$PID_DIR/bot.pid"; then
            warn "Bot not running, restarting..."
            start_bot
        fi
        
        if ! is_running "$PID_DIR/bridge.pid"; then
            warn "Bridge not running, restarting..."
            start_bridge
        fi
        
        # Cleanup parlays every 5 minutes
        cleanup_counter=$((cleanup_counter + 1))
        if [ $cleanup_counter -ge 30 ]; then
            cleanup_parlays
            cleanup_counter=0
        fi
        
        sleep 10
    done
}

# Main command handler
case "${1:-}" in
    start)
        log "🚀 Starting Risk0 services..."
        start_bot
        sleep 2
        start_bridge
        log "All services started!"
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_bot
        sleep 2
        start_bridge
        log "All services restarted!"
        ;;
    status)
        health_check
        ;;
    monitor)
        # Start services and monitor
        start_bot
        sleep 2
        start_bridge
        monitor_loop
        ;;
    cleanup)
        cleanup_parlays
        ;;
    logs)
        tail -f $LOG_DIR/*.log
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|monitor|cleanup|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all services"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Check health of services"
        echo "  monitor - Start and monitor (auto-restart on crash)"
        echo "  cleanup - Cleanup expired parlays"
        echo "  logs    - Follow all logs"
        exit 1
        ;;
esac
