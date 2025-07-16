# Google News Alert Ingestion System - Continuous Operation Guide

## Overview
This document explains how to run, manage, and troubleshoot the Google News Alert ingestion system in continuous operation mode. The system runs as a background service, checking for new alerts every 5 minutes and pushing them to the database.

## System Components
- **Main Service**: Python-based news alert processor
- **Health Check**: Endpoint at http://localhost:5000/health
- **Logging**: Separate files for service and error logs
- **Process Management**: Automated through launchd (macOS service manager)
- **Deployment Location**: ~/soup_deployment

## Quick Start Commands
```bash
# Check service status
./manage_service.sh status

# Start the service
./manage_service.sh start

# Stop the service
./manage_service.sh stop

# Restart the service
./manage_service.sh restart

# View logs
./manage_service.sh logs

# View recently processed articles
./manage_service.sh articles
```

## Directory Structure
```
~/soup_deployment/
├── venv/                  # Python virtual environment
├── logs/                  # Log files directory
│   ├── service.log       # Main service logs
│   ├── error.log        # Error messages and stack traces
│   └── soup_dedupe_processed_articles.log  # Rolling log of processed articles
├── main.py               # Main service script
├── manage_service.sh     # Service management script
└── requirements.txt      # Python dependencies
```

## Monitoring and Logs

### System Logs
Located in `~/soup_deployment/logs/`:
- `service.log`: Regular operation logs
- `error.log`: Error messages and stack traces
- `soup_dedupe_processed_articles.log`: Rolling log of 1000 most recent processed articles (newest at top)
- View all logs with: `./manage_service.sh logs`

### Article Processing Log
The system maintains two ways to view processed articles:

1. **Real-time Database Query**:
   ```bash
   ./manage_service.sh articles
   ```
   - Shows last 24 hours of processed articles
   - Queries directly from Supabase database
   - Displays processing timestamp, title, and URL
   - Most recent articles appear first
   - Updates the rolling log file

2. **Rolling Log File** (`logs/soup_dedupe_processed_articles.log`):
   - Maintains exactly 1000 most recent articles
   - Automatically removes oldest entries when new ones arrive
   - Most recent entries at the top
   - Each entry includes:
     - Processing timestamp (UTC)
     - Article title
     - Permalink URL
   - Updated whenever `articles` command is run
   - View latest entries: `head -n 50 logs/soup_dedupe_processed_articles.log`

The rolling log ensures you always have access to the 1000 most recent articles while preventing the log file from growing indefinitely. When new articles are processed, they are added to the top of the file, and if the total exceeds 1000 entries, the oldest ones are automatically removed.

## Detailed Setup Instructions

### 1. Initial Setup
1. Ensure Python 3.8+ is installed
2. Clone the repository to ~/soup_deployment
3. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Configuration
The system uses several environment variables that must be set:
- `GMAIL_USER`: Your Gmail account email
- `GMAIL_PASSWORD`: Your Gmail app-specific password
- `DB_CONNECTION_STRING`: Database connection URL
- `ENVIRONMENT`: Set to 'production' for live deployment

These can be configured in your ~/.zshrc or through the service configuration.

### 3. Service Management
The system uses launchd for service management. The service configuration is in:
`~/Library/LaunchAgents/com.therepute.googlenews.plist`

Key service features:
- Automatic startup on system boot
- Crash recovery
- 5-minute interval execution
- Resource monitoring

### 4. Logging System
Logs are stored in the ~/soup_deployment/logs directory:
- `service.log`: Regular operation logs
- `error.log`: Error messages and stack traces

Log rotation is automatic, keeping 7 days of history.

### 5. Health Monitoring
The service exposes a health check endpoint:
- URL: http://localhost:5000/health
- Expected response: {"status": "healthy"}
- Monitors: Database connection, Gmail access, processing status

### 6. Troubleshooting Guide

#### Common Issues and Solutions

1. **Service Won't Start**
   - Check logs: `./manage_service.sh logs`
   - Verify environment variables
   - Ensure virtual environment is properly set up
   - Check port 5000 availability

2. **Missing Alerts**
   - Verify Gmail credentials
   - Check Gmail API access
   - Review error.log for processing issues
   - Confirm database connectivity

3. **High Resource Usage**
   - Check for memory leaks in logs
   - Verify database connection pooling
   - Review alert processing patterns

4. **Database Connection Issues**
   - Verify connection string
   - Check database server status
   - Review network connectivity
   - Check error.log for specific errors

### 7. Maintenance Tasks

#### Daily Checks
1. Service status verification
2. Log review for errors
3. Database connection status
4. Health endpoint check

#### Weekly Tasks
1. Log rotation verification
2. Resource usage review
3. Database performance check
4. Backup verification

### 8. For LLMs: System Context and Assistance

This section provides context for AI assistants helping with this system.

#### Key Components for AI Analysis
1. **Service Architecture**
   - Python-based service using schedule package
   - Gmail API integration for alert fetching
   - SQLAlchemy for database operations
   - Flask for health check endpoint

2. **Critical Files**
   - `main.py`: Core service logic
   - `manage_service.sh`: Service management
   - `com.therepute.googlenews.plist`: Launch daemon config

3. **Important Metrics**
   - Expected 5-minute execution interval
   - Sub-second health check response time
   - < 100MB memory usage
   - 100% alert processing success rate

4. **Common Assistance Areas**
   - Log analysis and error diagnosis
   - Service configuration updates
   - Performance optimization
   - Database query troubleshooting

### 9. Version and Update Management

#### Current Version
- Service Version: 1.0.0
- Python Requirements: See requirements.txt
- Last Major Update: [Current Date]

#### Update Procedure
1. Stop service: `./manage_service.sh stop`
2. Backup configuration
3. Pull new code
4. Update dependencies
5. Start service: `./manage_service.sh start`
6. Verify health check

### 10. Security Considerations

1. **Credential Management**
   - Use environment variables for sensitive data
   - Regularly rotate Gmail app password
   - Monitor access logs

2. **Network Security**
   - Health check endpoint on localhost only
   - Database connection through secure channel
   - Regular security updates

### 11. Support and Resources

For issues or questions:
1. Check the logs first
2. Review this documentation
3. Check GitHub issues
4. Contact system administrator

## Conclusion
This system is designed for reliable, continuous operation with minimal maintenance. Regular monitoring and proactive maintenance using the provided tools will ensure smooth operation. 