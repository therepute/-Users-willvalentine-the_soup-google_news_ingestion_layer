# main.py - Entry point for Google News Alert ingestion
import schedule
import time
import logging
from config_loader import ConfigLoader
from alert_parser import AlertParser
from gmail_client import GmailClient
from soup_pusher import SoupPusher
from dedupe_utils import DedupeUtils
from flask import Flask
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app for health checks
app = Flask(__name__)

class GoogleAlertIngestor:
    def __init__(self):
        self.config = ConfigLoader()
        self.gmail_client = GmailClient(self.config.get_gmail_config())
        self.parser = AlertParser()
        self.soup_pusher = SoupPusher(self.config.get_supabase_config())
        self.deduper = DedupeUtils(self.config.get_supabase_config())
        
    def run_ingestion(self):
        """Main ingestion process"""
        try:
            logger.info("Starting Google News Alert ingestion...")
            
            # Get unprocessed emails
            emails = self.gmail_client.fetch_unprocessed_alerts()
            logger.info(f"Found {len(emails)} unprocessed alerts")
            
            stats = {
                'emails_checked': len(emails),
                'valid_alerts_parsed': 0,
                'articles_inserted': 0,
                'duplicates_skipped': 0,
                'emails_deleted': 0,
                'errors': 0
            }
            
            for email in emails:
                try:
                    # Parse the alert email
                    article_data = self.parser.parse_alert(email)
                    if not article_data:
                        continue
                        
                    stats['valid_alerts_parsed'] += 1
                    
                    # Check for duplicates
                    if self.deduper.is_duplicate(article_data):
                        logger.info(f"Duplicate article skipped: {article_data['headline']}")
                        stats['duplicates_skipped'] += 1
                        continue
                    
                    # Push to Soup database
                    success = self.soup_pusher.insert_article(article_data)
                    if success:
                        stats['articles_inserted'] += 1
                        # DELETE email after successful import
                        if self.gmail_client.delete_email(email['id']):
                            stats['emails_deleted'] += 1
                            logger.info(f"Article imported and email deleted: {article_data['headline']}")
                        else:
                            logger.warning(f"Article imported but email deletion failed: {email['id']}")
                    
                except Exception as e:
                    logger.error(f"Error processing email: {str(e)}")
                    stats['errors'] += 1
            
            logger.info("Ingestion completed with stats:", extra=stats)
            return stats
            
        except Exception as e:
            logger.error(f"Error in ingestion process: {str(e)}")
            return None

# Create global ingestor instance
ingestor = GoogleAlertIngestor()

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        if not ingestor.soup_pusher.test_connection():
            return 'Database connection failed', 500
            
        return 'Healthy', 200
        
    except Exception as e:
        return str(e), 500

def run_flask():
    """Run Flask app in a separate thread"""
    app.run(host='0.0.0.0', port=5000)

def main():
    """Main function that sets up scheduling and runs the service"""
    logger.info("Starting Google News Alert Service...")
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Schedule ingestion to run every 5 minutes
    schedule.every(5).minutes.do(ingestor.run_ingestion)
    
    # Run initial ingestion
    ingestor.run_ingestion()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()