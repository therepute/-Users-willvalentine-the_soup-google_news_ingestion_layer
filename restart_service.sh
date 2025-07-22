#!/bin/bash

# Load environment variables
set -a
source .env
set +a

# Kill existing process if running
if [ -f "service.pid" ]; then
    pid=$(cat service.pid)
    if ps -p $pid > /dev/null; then
        kill $pid
    fi
    rm service.pid
fi

# Activate virtual environment or create if doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Start the service
nohup python main.py > service.log 2>&1 &
echo $! > service.pid

# Wait a moment and check if process is still running
sleep 5
if ! ps -p $(cat service.pid) > /dev/null; then
    echo "Service failed to start. Check service.log for details."
    exit 1
fi

echo "Service restarted successfully" 