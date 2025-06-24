# dedupe_utils.py - Simple deduplication using Soup_Dedupe table
import hashlib
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class DedupeUtils:
    def __init__(self, config):
        self.url = config['url']
        self.key = config['key']
        self.supabase: Client = create_client(self.url, self.key)
        self.table_name = config.get('table_name', 'Soup_Dedupe')
    
    def is_duplicate(self, article_data):
        """
        Check if article already exists in Soup_Dedupe table.
        Uses permalink_url as the unique identifier.
        """
        try:
            story_link = article_data.get('story_link', article_data.get('permalink_url', ''))
            
            if not story_link:
                # If no URL, can't check for duplicates
                return False
            
            # Check if this permalink_url already exists
            result = self.supabase.table(self.table_name)\
                .select('id')\
                .eq('permalink_url', story_link)\
                .limit(1)\
                .execute()
            
            if result.data:
                logger.debug(f"Duplicate found for URL: {story_link[:50]}...")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}")
            # If we can't check, assume it's not a duplicate to avoid losing articles
            return False
    
    def get_existing_articles_count(self):
        """Get total count of articles in database"""
        try:
            result = self.supabase.table(self.table_name)\
                .select('*', count='exact')\
                .limit(1)\
                .execute()
            
            return result.count if hasattr(result, 'count') else 0
            
        except Exception as e:
            logger.error(f"Error getting article count: {str(e)}")
            return 0