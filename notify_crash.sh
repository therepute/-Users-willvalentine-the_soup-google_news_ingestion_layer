#!/bin/bash

# Script to send notifications for service crashes
TITLE="Alert: Workflow Failure / Google Alert Ingestion"
MESSAGE="The Google News Alert service has crashed. Check logs for details."

# Load configuration
CONFIG_FILE="$(dirname "$0")/notification_config.sh"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Send macOS notification
osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\" sound name \"Basso\""

# Log the crash
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Service crash detected" >> "$(dirname "$0")/logs/crash.log"

# Send email notification
if [ ! -z "$EMAIL" ] && [ "$EMAIL" != "your-email@example.com" ]; then
    echo "$MESSAGE" | mail -s "$TITLE" "$EMAIL"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Email notification sent to $EMAIL" >> "$(dirname "$0")/logs/notification.log"
fi

# Send SMS via Twilio
if [ "$TWILIO_ACCOUNT_SID" != "your_account_sid" ] && [ "$TWILIO_AUTH_TOKEN" != "your_auth_token" ]; then
    RESPONSE=$(curl -s -X POST "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Messages.json" \
        --data-urlencode "To=$TO_NUMBER" \
        --data-urlencode "From=$TWILIO_FROM_NUMBER" \
        --data-urlencode "Body=$TITLE - $MESSAGE" \
        -u "$TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN")
    
    if echo "$RESPONSE" | grep -q "\"status\": \"queued\""; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] SMS notification sent to $TO_NUMBER" >> "$(dirname "$0")/logs/notification.log"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Failed to send SMS: $RESPONSE" >> "$(dirname "$0")/logs/notification.log"
    fi
fi 