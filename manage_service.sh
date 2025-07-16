#!/bin/bash

SERVICE_NAME="com.therepute.googlenews"
PLIST_PATH="$HOME/Library/LaunchAgents/$SERVICE_NAME.plist"
LOG_PATH="$HOME/soup_deployment/service.log"
ERROR_LOG_PATH="$HOME/soup_deployment/error.log"

function status() {
    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo "✅ Service is running"
        echo "Recent logs:"
        echo "------------"
        tail -n 10 "$LOG_PATH"
        echo
        echo "Recent errors:"
        echo "-------------"
        tail -n 5 "$ERROR_LOG_PATH"
    else
        echo "❌ Service is not running"
    fi
}

function start() {
    echo "Starting service..."
    launchctl load "$PLIST_PATH"
    sleep 2
    status
}

function stop() {
    echo "Stopping service..."
    launchctl unload "$PLIST_PATH"
    sleep 2
    status
}

function restart() {
    echo "Restarting service..."
    stop
    sleep 2
    start
}

function logs() {
    echo "Showing live logs (Ctrl+C to exit)..."
    tail -f "$LOG_PATH"
}

function errors() {
    echo "Showing error logs (Ctrl+C to exit)..."
    tail -f "$ERROR_LOG_PATH"
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    errors)
        errors
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|errors}"
        exit 1
        ;;
esac 