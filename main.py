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
                        # DELETE email after successful import (not just mark as processed)
                        if self.gmail_client.delete_email(email['id']):
                            stats['emails_deleted'] += 1
                            logger.info(f"Article imported and email deleted: {article_data['headline']}")
                        else:
                            logger.warning(f"Article imported but email deletion failed: {email['id']}")
                    
                except Exception as e:
                    logger.error(f"Error processing email {email.get('id', 'unknown')}: {str(e)}")
                    stats['errors'] += 1
            
            # Log execution stats
            logger.info(f"Ingestion complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during ingestion: {str(e)}")
            return None
    
    def run_weekly_cleanup(self):
        """Weekly cleanup of non-Google Alert emails"""
        try:
            logger.info("Starting weekly cleanup of non-Google Alert emails...")
            
            deleted_count = self.gmail_client.weekly_cleanup_non_google_alerts()
            
            logger.info(f"Weekly cleanup completed: {deleted_count} emails deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during weekly cleanup: {str(e)}")
            return 0
    
    def run_daily_trash_purge(self):
        """Daily purge of trash to permanently delete sensitive emails"""
        try:
            logger.info("Starting daily trash purge for security...")
            
            purged_count = self.gmail_client.daily_purge_trash()
            
            logger.info(f"Daily trash purge completed: {purged_count} emails permanently deleted")
            return purged_count
            
        except Exception as e:
            logger.error(f"Error during daily trash purge: {str(e)}")
            return 0
    
    def get_system_stats(self):
        """Get system statistics for monitoring"""
        try:
            email_stats = self.gmail_client.get_email_stats()
            db_count = self.deduper.get_existing_articles_count()
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'gmail': email_stats,
                'database_articles': db_count
            }
            
            logger.info(f"System stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system stats: {str(e)}")
            return None

def main():
    # You can specify the path to your TOML file, or it will auto-detect
    ingestor = GoogleAlertIngestor()
    
    # Schedule the ingestion to run every 15 minutes
    schedule.every(15).minutes.do(ingestor.run_ingestion)
    
    # Schedule weekly cleanup every Sunday at 2 AM
    schedule.every().sunday.at("02:00").do(ingestor.run_weekly_cleanup)
    
    # Schedule daily trash purge at 3 AM for security
    schedule.every().day.at("03:00").do(ingestor.run_daily_trash_purge)
    
    # Optional: Schedule daily stats logging
    schedule.every().day.at("00:01").do(ingestor.get_system_stats)
    
    logger.info("Google News Alert Ingestor started with the following schedule:")
    logger.info("- Ingestion: Every 15 minutes")
    logger.info("- Weekly cleanup: Sundays at 2:00 AM")
    logger.info("- Daily trash purge: Every day at 3:00 AM (SECURITY)")
    logger.info("- System stats: Daily at 12:01 AM")
    
    # Run once immediately
    logger.info("Running initial ingestion...")
    ingestor.run_ingestion()
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()