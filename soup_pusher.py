# soup_pusher.py - Push data to Supabase (Updated for Soup_Dedupe schema)
from supabase import create_client, Client
import logging
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class SoupPusher:
    def __init__(self, config):
        self.url = config['url']
        self.key = config['key']
        self.supabase: Client = create_client(self.url, self.key)
        self.table_name = config.get('table_name', 'Soup_Dedupe')
    
    def test_connection(self):
        """Test database connection for health checks"""
        try:
            # Simple query to test connection
            result = self.supabase.table(self.table_name).select("*", count="exact").limit(1).execute()
            logger.info(f"Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def insert_article(self, article_data):
        """Insert article into Supabase Soup_Dedupe table"""
        try:
            # Map Gmail alert data to your Soup_Dedupe schema
            soup_record = self._map_to_soup_schema(article_data)
            
            result = self.supabase.table(self.table_name).insert(soup_record).execute()
            
            if result.data:
                title = soup_record.get('title', soup_record.get('source_title', 'Unknown'))
                logger.info(f"Successfully inserted article: {title[:50]}...")
                return True
            else:
                logger.error(f"Failed to insert article: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error inserting article into Supabase: {str(e)}")
            return False
    
    def _map_to_soup_schema(self, article_data):
        """
        Map article data to your Soup_Dedupe schema.
        Handles Gmail alert parsing format.
        """
        # Create a hash for the ID (since id is primary key)
        content_for_id = f"{article_data.get('headline', '')}{article_data.get('story_link', '')}"
        article_id = hashlib.sha256(content_for_id.encode()).hexdigest()[:20]  # Shortened hash
        
        # Map to your exact Soup_Dedupe schema
        return {
            'id': article_id,                                    # Primary key (shortened hash)
            'created_at': datetime.now().isoformat(),            # Current timestamp
            'title': article_data.get('headline', ''),           # Article headline
            'permalink_url': article_data.get('story_link', ''), # Article URL
            'published_at': self._parse_date(article_data.get('date')), # Article publish date
            'publication': article_data.get('publication', ''),     # Publication name (HelpNet Security, ETV Bharat, etc.)
            'source_url': None,                                  # Not available from Gmail alerts
            'language': 'en',                                    # Assume English
            'summary': article_data.get('body', ''),             # Article snippet
            'content': article_data.get('body', ''),             # Article content
            'categories': None,                                  # Not available from Gmail alerts
            'raw_payload': article_data,                         # Store original Gmail alert data
            'actor_name': None,                                  # Not available from Gmail alerts
            'actor_profile_url': None,                           # Not available from Gmail alerts
            'object_title': article_data.get('headline', ''),    # Same as title
            'object_type': 'article',                            # Always article
            'subscription_source': f"GN_CL_{article_data.get('search', 'unknown')}", # GN_CL_[Search Term]
            'total_articles_count': None,                        # Will be set by trigger
            'daily_articles_count': None,                        # Will be set by trigger
            'monthly_articles_count': None                       # Will be set by trigger
        }
    
    def _parse_date(self, date_string):
        """Parse date from Gmail alert"""
        if not date_string:
            return None
        
        try:
            # Try to parse common Gmail date formats
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_string).isoformat()
        except:
            # If parsing fails, return None
            return None
    
    def bulk_insert_articles(self, articles_list):
        """Insert multiple articles at once for better performance"""
        try:
            if not articles_list:
                return True
            
            # Map all articles to schema
            mapped_articles = [self._map_to_soup_schema(article) for article in articles_list]
            
            result = self.supabase.table(self.table_name).insert(mapped_articles).execute()
            
            if result.data:
                logger.info(f"Successfully bulk inserted {len(articles_list)} articles")
                return True
            else:
                logger.error(f"Failed to bulk insert articles: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error bulk inserting articles: {str(e)}")
            return False