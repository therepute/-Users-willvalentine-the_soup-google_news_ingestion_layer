#!/bin/bash

# Service management script for Google News Alert ingestion

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create logs directory if it doesn't exist
mkdir -p "$DIR/logs"

# Function to check if service is running
check_running() {
    if [ -f "$DIR/service.pid" ]; then
        pid=$(cat "$DIR/service.pid")
        if ps -p $pid > /dev/null; then
            return 0
        fi
    fi
    return 1
}

# Function to show recent articles
show_articles() {
    echo "Querying recent articles from Supabase..."
    source $DIR/venv/bin/activate
    python3 - << EOF
from config_loader import ConfigLoader
from supabase import create_client
from datetime import datetime, timedelta
import pytz
import os
import collections

# Initialize Supabase client
config = ConfigLoader().get_supabase_config()
supabase = create_client(config['url'], config['key'])

# Get articles from the last 24 hours
now = datetime.now(pytz.UTC)
yesterday = now - timedelta(days=1)

# Query articles
result = supabase.table('Soup_Dedupe')\
    .select('permalink_url,created_at,title')\
    .gte('created_at', yesterday.isoformat())\
    .order('created_at', desc=True)\  # This ensures newest first in the query
    .execute()

# Prepare log file path
log_file = os.path.join('${DIR}', 'logs', 'soup_dedupe_processed_articles.log')
temp_file = os.path.join('${DIR}', 'logs', 'soup_dedupe_processed_articles.log.tmp')

# Function to format article entry
def format_article(article):
    created_at = datetime.fromisoformat(article['created_at'].replace('Z', '+00:00'))
    return f"""
Processed at: {created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Title: {article.get('title', 'No title')}
URL: {article['permalink_url']}
{'-' * 80}"""

def format_header():
    return f"Last updated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n{'=' * 80}\n"

# Function to read existing entries (returns a deque of max 1000 entries)
def read_existing_entries(filename):
    if not os.path.exists(filename):
        return collections.deque(maxlen=1000)
    
    entries = collections.deque(maxlen=1000)
    current_entry = []
    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('Last updated:') or line.startswith('=' * 80):
                continue
            if line.strip() == '-' * 80:
                if current_entry:
                    entries.append(''.join(current_entry) + line)
                    current_entry = []
            else:
                current_entry.append(line)
    if current_entry:
        entries.append(''.join(current_entry))
    return entries

if result.data:
    # Display to console in reverse chronological order
    print("\nRecently processed articles (last 24 hours, newest first):")
    print("=" * 80)
    for article in result.data:  # result.data is already in desc order
        print(format_article(article))
    
    # Update log file with rolling 1000 entries
    existing_entries = read_existing_entries(log_file)
    
    # Add new entries at the beginning
    for article in result.data:
        entry = format_article(article)
        if entry not in existing_entries:  # Avoid duplicates
            existing_entries.appendleft(entry)  # Use appendleft to maintain newest-first order
    
    # Write updated log file
    with open(temp_file, 'w') as f:
        f.write(format_header())
        for entry in existing_entries:
            f.write(entry)
        f.write("\n" + "=" * 80 + "\n")
    
    # Replace old file with new one
    os.replace(temp_file, log_file)
    
    print(f"\nArticles log updated (maintaining most recent {existing_entries.maxlen} entries)")
else:
    print("No articles processed in the last 24 hours.")
    # Add note to log file
    with open(log_file, 'a') as f:
        f.write(f"\nNo articles processed in 24 hours before {now.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
EOF
}

case "$1" in
    start)
        if check_running; then
            echo "Service is already running."
            exit 1
        fi
        
        echo "Starting Google News Alert ingestion service..."
        source $DIR/venv/bin/activate
        nohup python $DIR/main.py > $DIR/service.log 2> $DIR/error.log & echo $! > $DIR/service.pid
        echo "Service started. PID: $(cat $DIR/service.pid)"
        ;;
        
    stop)
        if check_running; then
            echo "Stopping service..."
            kill $(cat $DIR/service.pid)
            rm $DIR/service.pid
            echo "Service stopped."
        else
            echo "Service is not running."
        fi
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        if check_running; then
            echo "Service is running. PID: $(cat $DIR/service.pid)"
            echo "Health check URL: http://localhost:5000/health"
        else
            echo "Service is not running."
        fi
        ;;
        
    logs)
        echo "=== Service Log ==="
        tail -n 50 $DIR/service.log
        echo -e "\n=== Error Log ==="
        tail -n 50 $DIR/error.log
        echo -e "\n=== Processed Articles Log (Most Recent) ==="
        head -n 50 $DIR/logs/soup_dedupe_processed_articles.log
        ;;
        
    articles)
        show_articles
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|articles}"
        exit 1
        ;;
esac

exit 0 