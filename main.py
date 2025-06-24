# main.py - Entry point for Google News Alert ingestion
import schedule
import time
import logging
from datetime import datetime
from gmail_client import GmailClient
from alert_parser import AlertParser
from soup_pusher import SoupPusher
from dedupe_utils import DedupeUtils
from config_loader import ConfigLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GoogleAlertIngestor:
    def __init__(self, toml_path=None):
        # Load config from your existing TOML file
        self.config_loader = ConfigLoader(toml_path)
        
        self.gmail_client = GmailClient(self.config_loader.get_gmail_config())
        self.parser = AlertParser()
        self.soup_pusher = SoupPusher(self.config_loader.get_supabase_config())
        self.deduper = DedupeUtils(self.config_loader.get_supabase_config())
        
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
                        # Mark email as processed
                        self.gmail_client.mark_as_processed(email['id'])
                        logger.info(f"Article inserted: {article_data['headline']}")
                    
                except Exception as e:
                    logger.error(f"Error processing email {email.get('id', 'unknown')}: {str(e)}")
                    stats['errors'] += 1
            
            # Log execution stats
            logger.info(f"Ingestion complete: {stats}")
            
        except Exception as e:
            logger.error(f"Critical error in ingestion process: {str(e)}")

def main():
    # You can specify the path to your TOML file, or it will auto-detect
    ingestor = GoogleAlertIngestor()
    
    # Schedule the ingestion to run every 15 minutes
    schedule.every(15).minutes.do(ingestor.run_ingestion)
    
    logger.info("Google News Alert Ingestor started. Running every 15 minutes...")
    
    # Run once immediately
    ingestor.run_ingestion()
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()