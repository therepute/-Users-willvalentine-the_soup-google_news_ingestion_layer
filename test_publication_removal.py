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
            # Get the ID that was used
            content_for_id = f"{article_data.get('headline', '')}{article_data.get('story_link', '')}"
            article_id = hashlib.sha256(content_for_id.encode()).hexdigest()[:20]
            processed_ids.append(article_id)
            
            # Verify directly in database
            result = soup_pusher.supabase.table(soup_pusher.table_name)\
                .select('id, publication')\
                .eq('id', article_id)\
                .execute()
            
            if result.data:
                article = result.data[0]
                logger.info(f"Article ID: {article['id']}")
                logger.info(f"Publication value: {article['publication']}")
                if article['publication'] is not None:
                    logger.error(f"❌ Publication is not None for article {article['id']}")
                else:
                    logger.info(f"✅ Publication is correctly None for article {article['id']}")
    
    logger.info("\nProcessed Article IDs for verification:")
    for article_id in processed_ids:
        logger.info(article_id)
    
    return processed_ids

if __name__ == "__main__":
    test_publication_removal() 