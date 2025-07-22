# dedupe_utils.py - Simple deduplication using Soup_Dedupe table
import hashlib
import logging
from supabase import create_client, Client
from urllib.parse import unquote, urlparse

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
            # Get the URL from either story_link or permalink_url
            story_link = article_data.get('story_link', '')
            permalink_url = article_data.get('permalink_url', '')
            url_to_check = story_link or permalink_url
            
            if not url_to_check:
                logger.warning("No URL found in article data")
                return False
            
            # Log the raw URL without normalization first
            logger.info(f"Raw URL from article data: {url_to_check}")
            
            # Try checking without normalization first
            result = self.supabase.table(self.table_name)\
                .select('id,permalink_url')\
                .eq('permalink_url', url_to_check)\
                .limit(1)\
                .execute()
            
            if result.data:
                logger.info(f"Found exact match - Existing URL: {result.data[0].get('permalink_url', 'Unknown')}")
                return True
            
            # If no exact match, try with normalization
            normalized_url = self._normalize_url(url_to_check)
            logger.info(f"Trying normalized URL: {normalized_url}")
            
            result = self.supabase.table(self.table_name)\
                .select('id,permalink_url')\
                .eq('permalink_url', normalized_url)\
                .limit(1)\
                .execute()
            
            if result.data:
                logger.info(f"Found normalized match - Existing URL: {result.data[0].get('permalink_url', 'Unknown')}")
                return True
            
            logger.info(f"No duplicate found for either raw or normalized URL")
            return False
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}")
            # If we can't check, assume it's not a duplicate to avoid losing articles
            return False
    
    def _normalize_url(self, url):
        """Normalize URL by removing tracking parameters and decoding"""
        try:
            # Parse the URL
            parsed = urlparse(url)
            
            # Basic normalization
            clean_url = parsed.scheme + '://' + parsed.netloc + parsed.path
            
            # Remove trailing slashes and common prefixes
            clean_url = clean_url.rstrip('/')
            clean_url = clean_url.replace('www.', '')
            
            # Convert to lowercase
            clean_url = clean_url.lower()
            
            return clean_url
            
        except Exception as e:
            logger.warning(f"Error normalizing URL {url}: {e}")
            return url
    
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