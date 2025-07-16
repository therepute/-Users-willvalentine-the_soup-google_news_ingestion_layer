#!/bin/bash

# Service monitoring script
SERVICE_NAME="com.therepute.googlenews"
WORKSPACE_DIR="/Users/willvalentine/Soup_Google_News_Ingestion/-Users-willvalentine-the_soup-google_news_ingestion_layer"
LOG_FILE="$WORKSPACE_DIR/logs/monitor.log"
NOTIFICATION_SCRIPT="$WORKSPACE_DIR/notify_crash.sh"

# Create logs directory if it doesn't exist
mkdir -p "$WORKSPACE_DIR/logs"

# Function to send notification
send_notification() {
    local message="$1"
    if [ -x "$NOTIFICATION_SCRIPT" ]; then
        "$NOTIFICATION_SCRIPT" "$message"
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" >> "$LOG_FILE"
}

# Check if service is running
check_service() {
    if ! launchctl list | grep -q "$SERVICE_NAME"; then
        send_notification "Service $SERVICE_NAME is not running!"
        return 1
    fi
    
    # Check if process is actually running
    local pid=$(launchctl list | grep "$SERVICE_NAME" | awk '{print $1}')
    if [ "$pid" = "-" ] || [ -z "$pid" ]; then
        send_notification "Service $SERVICE_NAME process is not active!"
        return 1
    fi
    
    # Check last error log entry
    if [ -f "$WORKSPACE_DIR/error.log" ]; then
        local last_error=$(tail -n 1 "$WORKSPACE_DIR/error.log")
        if [ ! -z "$last_error" ]; then
            local last_error_time=$(stat -f "%m" "$WORKSPACE_DIR/error.log")
            local current_time=$(date +%s)
            local time_diff=$((current_time - last_error_time))
            
            # If error is less than 5 minutes old
            if [ $time_diff -lt 300 ]; then
                send_notification "Recent error detected: $last_error"
                return 1
            fi
        fi
    fi
    
    # Check if service is responsive (health check)
    if ! curl -s http://localhost:5000/health | grep -q "healthy"; then
        send_notification "Service health check failed!"
        return 1
    fi
    
    return 0
}

# Main monitoring loop
while true; do
    check_service
    sleep 300  # Check every 5 minutes
done 