from config_loader import ConfigLoader
from alert_parser import AlertParser
from gmail_client import GmailClient
from soup_pusher import SoupPusher
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_publication_removal():
    """Test that publication names are no longer being sent to the database"""
    
    # Initialize components
    config = ConfigLoader()
    gmail_client = GmailClient(config.get_gmail_config())
    parser = AlertParser()
    soup_pusher = SoupPusher(config.get_supabase_config())
    
    # Get 10 unprocessed emails
    emails = gmail_client.fetch_unprocessed_alerts()[:10]
    logger.info(f"Testing with {len(emails)} emails")
    
    processed_ids = []
    
    for email in emails:
        # Parse alert
        article_data = parser.parse_alert(email)
        if not article_data:
            continue
            
        # Push to database
        success = soup_pusher.insert_article(article_data)
        if success:
            # Get the actual ID that was used by querying with permalink_url
            permalink_url = article_data.get('story_link', '')
            
            # Query database to get the actual ID that was generated
            result = soup_pusher.supabase.table(soup_pusher.table_name)\
                .select('id, publication')\
                .eq('permalink_url', permalink_url)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                article = result.data[0]
                article_id = article['id']
                processed_ids.append(article_id)
                
                logger.info(f"Article ID: {article_id}")
                logger.info(f"Publication value: {article['publication']}")
                
                # Verify the new ID format
                if article_id.startswith('GA_') and len(article_id.split('_')) == 4:
                    logger.info(f"✅ ID follows new standardized format: {article_id}")
                else:
                    logger.error(f"❌ ID does NOT follow new format: {article_id}")
                
                # Check publication field
                if article['publication'] is not None:
                    logger.error(f"❌ Publication is not None for article {article_id}")
                else:
                    logger.info(f"✅ Publication is correctly None for article {article_id}")
            else:
                logger.warning(f"Could not find inserted article with URL: {permalink_url}")
    
    logger.info("\nProcessed Article IDs for verification:")
    for article_id in processed_ids:
        logger.info(article_id)
    
    return processed_ids

if __name__ == "__main__":
    test_publication_removal() 