# main.py - Entry point for Google News Alert ingestion
import schedule
import time
import logging
import os
from src.config.loader import ConfigLoader
from src.parsers.google_parser import AlertParser
from src.clients.gmail_client import GmailClient
from src.database.soup_pusher import SoupPusher
from src.database.dedupe_utils import DedupeUtils
from flask import Flask
import threading

# Get the absolute path to the logs directory
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(WORKSPACE_DIR, 'logs')

# Create logs directory if it doesn't exist
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'ingestion.log')),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app for health checks
app = Flask(__name__)

class NewsAlertIngestor:
    def __init__(self):
        # Load configuration
        self.config = ConfigLoader()
        self.gmail_config = self.config.get_gmail_config()
        self.supabase_config = self.config.get_supabase_config()
        
        # Initialize components
        self.gmail_client = GmailClient(self.gmail_config)
        self.alert_parser = AlertParser()
        self.soup_pusher = SoupPusher(self.supabase_config)
        self.dedupe_utils = DedupeUtils(self.supabase_config)
        
        # Track stats
        self.stats = {
            'emails_checked': 0,
            'valid_alerts_parsed': 0,
            'articles_inserted': 0,
            'duplicates_skipped': 0,
            'emails_deleted': 0
        }
        
    def process_alerts(self, max_alerts=10):
        """Process Google News Alerts from Gmail"""
        try:
            logger.info("Starting Google News Alert ingestion...")
            
            # Get unread alerts with pagination support
            alerts = self.gmail_client.fetch_unprocessed_alerts(max_emails=max_alerts)
            if not alerts:
                logger.info("No new alerts found")
                return
            logger.info(f"Found {len(alerts)} unprocessed alerts, processing {max_alerts} alerts")
            
            # Process each alert
            for email in alerts:
                self.stats['emails_checked'] += 1
                
                # Parse alert
                articles = self.alert_parser.parse_alert(email)
                if not articles:
                    continue
                
                self.stats['valid_alerts_parsed'] += len(articles)
                
                # Process each article found in the email
                for article_data in articles:
                    logger.info(f"Processing article: {article_data.get('headline', 'Unknown')} - URL: {article_data.get('story_link', 'No URL')}")
                    success = self.soup_pusher.insert_article(article_data)
                
                    if success:
                        self.stats['articles_inserted'] += 1
                        logger.info(f"Article sent to database successfully: {article_data['headline']}")
                    else:
                        logger.warning(f"Failed to send article to database: {article_data['headline']}")
                
                # MARK email as processed (more reliable than deletion)
                if self.gmail_client.mark_as_processed(email['id']):
                    self.stats['emails_deleted'] += 1
                    logger.info(f"Email marked as processed for {len(articles)} articles.")
                else:
                    logger.warning(f"Failed to mark email as processed: {email['id']}")
            
            # Log final stats
            logger.info(f"Ingestion complete. Stats: {self.stats}")
            
        except Exception as e:
            logger.error(f"Error processing alerts: {str(e)}")

    def run_scheduled_tasks(self):
        """Run initial ingestion and schedule recurring tasks"""
        logger.info("Google News Alert Ingestor started with the following schedule:")
        logger.info("- Ingestion: Every 15 minutes")
        logger.info("- Weekly cleanup: Sundays at 2:00 AM")
        logger.info("- Daily trash purge: Every day at 3:00 AM (SECURITY)")
        logger.info("- System stats: Daily at 12:01 AM")
    
        logger.info("Running initial ingestion...")
        self.process_alerts(max_alerts=10)
        
        # Schedule recurring tasks
        schedule.every(15).minutes.do(self.process_alerts, max_alerts=10)
        schedule.every().sunday.at("02:00").do(self.gmail_client.weekly_cleanup_non_google_alerts)
        schedule.every().day.at("03:00").do(self.gmail_client.daily_purge_trash)
        schedule.every().day.at("00:01").do(self.log_system_stats)
        
    while True:
        schedule.run_pending()
        time.sleep(1)
    
    def log_system_stats(self):
        """Log system statistics"""
        try:
            total_articles = self.dedupe_utils.get_existing_articles_count()
            logger.info(f"System Stats - Total articles in database: {total_articles}")
        except Exception as e:
            logger.error(f"Error logging system stats: {str(e)}")

# Health check endpoint
@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

if __name__ == "__main__":
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000))
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start the ingestor
    ingestor = NewsAlertIngestor()
    ingestor.run_scheduled_tasks()