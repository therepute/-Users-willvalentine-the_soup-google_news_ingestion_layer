#!/bin/bash

echo "Setting up local deployment for Google News Ingestion..."

# Create deployment directory
DEPLOY_DIR=~/soup_deployment
mkdir -p $DEPLOY_DIR

# Create virtual environment if it doesn't exist
if [ ! -d "$DEPLOY_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $DEPLOY_DIR/venv
fi

# Activate virtual environment
source $DEPLOY_DIR/venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    echo "Creating .env file..."
    cat > $DEPLOY_DIR/.env << EOL
# Supabase Configuration
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_TABLE_NAME=Soup_Dedupe

# Google Configuration
GOOGLE_PROJECT_ID=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_CLIENT_EMAIL=
GOOGLE_PRIVATE_KEY=
GOOGLE_PRIVATE_KEY_ID=

# Service Configuration
MAX_EMAILS_PER_RUN=50
SCRAPER_MIN_DELAY=0.5
SCRAPER_MAX_DELAY=2.0
SCRAPER_TIMEOUT=15
SCRAPER_MAX_ARTICLES_PER_SITE=10
SCRAPER_MAX_RETRIES=3
EOL

    echo "Please fill in your environment variables in $DEPLOY_DIR/.env"
    echo "Press Enter when you're done..."
    read
fi

# Copy files to deployment directory
echo "Copying files to deployment directory..."
rsync -avz --delete \
    --exclude '.git*' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    ./ $DEPLOY_DIR/

# Make scripts executable
chmod +x $DEPLOY_DIR/restart_service.sh

# Start the service
echo "Starting the service..."
cd $DEPLOY_DIR
./restart_service.sh

# Wait for service to start
echo "Waiting for service to start..."
sleep 5

# Check health
echo "Checking service health..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
if [ $response -eq 200 ]; then
    echo "✅ Service is running and healthy!"
    echo "Health check endpoint: http://localhost:5000/health"
    echo "Service logs: $DEPLOY_DIR/service.log"
    echo "Process ID file: $DEPLOY_DIR/service.pid"
else
    echo "❌ Service health check failed with status $response"
    echo "Check the logs at $DEPLOY_DIR/service.log for details"
    exit 1
fi 