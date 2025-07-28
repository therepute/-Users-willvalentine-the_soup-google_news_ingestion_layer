# mesh_scraper.py - Automated News Mesh Ingestion System
"""
Automated news scraping component that integrates with existing alert_parser system.
Uses Link Creator logic to generate Google News URLs and scrape articles automatically.
"""

import urllib.parse
import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import hashlib
import random
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import existing components
from src.config.loader import ConfigLoader
from src.database.soup_pusher import SoupPusher
from src.database.dedupe_utils import DedupeUtils

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MeshScraper:
    """
    Automated news mesh scraper that generates and scrapes Google News URLs
    for all active clients and their search terms.
    """
    
    def __init__(self, config_path: str = None):
        """Initialize with existing config system"""
        self.config_loader = ConfigLoader(config_path)
        self.soup_pusher = SoupPusher(self.config_loader.get_supabase_config())
        self.deduper = DedupeUtils(self.config_loader.get_supabase_config())
        
        # Initialize Supabase client for querying clients
        supabase_config = self.config_loader.get_supabase_config()
        from supabase import create_client, Client
        self.supabase: Client = create_client(supabase_config['url'], supabase_config['key'])
        
        # Outlet configurations (from your Link Creator)
        self.outlet_categories = self._load_outlet_categories()
        
        # Load configuration from environment variables
        self.min_delay = float(os.getenv('SCRAPER_MIN_DELAY', '0.5'))
        self.max_delay = float(os.getenv('SCRAPER_MAX_DELAY', '2.0'))
        self.timeout = int(os.getenv('SCRAPER_TIMEOUT', '15'))
        self.max_articles_per_site = int(os.getenv('SCRAPER_MAX_ARTICLES_PER_SITE', '10'))
        self.max_retries = int(os.getenv('SCRAPER_MAX_RETRIES', '3'))
        
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # Rate limiting
        self.delay_range = (self.min_delay, self.max_delay)
        
    def _load_outlet_categories(self) -> Dict[str, List[Tuple[str, str]]]:
        """Load outlet categories (same as your Link Creator)"""
        return {
            "Influence 10": [
                ("New York Times", "nytimes.com"),
                ("Wall Street Journal", "wsj.com"), 
                ("Washington Post", "washingtonpost.com"),
                ("CNN", "cnn.com"),
                ("CNBC", "cnbc.com"),
                ("Fortune", "fortune.com"),
                ("Fox News", "foxnews.com"),
                ("Politico", "politico.com"),
                ("Axios", "axios.com"),
                ("Bloomberg", "bloomberg.com")
            ],
            "Policy 12": [
                ("New York Times", "nytimes.com"),
                ("Wall Street Journal", "wsj.com"),
                ("Washington Post", "washingtonpost.com"),
                ("CNN", "cnn.com"),
                ("Politico", "politico.com"),
                ("Axios", "axios.com"),
                ("Bloomberg", "bloomberg.com"),
                ("The Hill", "thehill.com"),
                ("The Atlantic", "theatlantic.com"),
                ("Fox News", "foxnews.com"),
                ("NPR", "npr.org"),
                ("MSNBC", "msnbc.com")
            ],
            "Tech 10": [
                ("The Verge", "theverge.com"),
                ("Wired", "wired.com"),
                ("Fast Co", "fastcompany.com"),
                ("CNET", "cnet.com"),
                ("Engadget", "engadget.com"),
                ("Axios", "axios.com"),
                ("TechCrunch", "techcrunch.com"),
                ("The Information", "theinformation.com"),
                ("Mashable", "mashable.com"),
                ("ZDNet", "zdnet.com")
            ]
        }
    
    def get_client_search_terms(self) -> Dict[str, List[str]]:
        """
        Get all active clients and their search terms from Supabase.
        """
        try:
            logger.info("Fetching client data from Supabase...")
            
            # Query your clients table in Supabase
            # Adjust table name and field names to match your actual Supabase schema
            response = self.supabase.table('clients').select('*').eq('status', 'active').execute()
            
            if not response.data:
                logger.warning("No active clients found in Supabase clients table")
                return self._get_fallback_clients()
            
            client_terms = {}
            logger.info(f"Retrieved {len(response.data)} records from Supabase")
            
            for record in response.data:
                # Debug: Print available fields for the first record
                if not client_terms:  # Only for first record
                    logger.info(f"Available Supabase client fields: {list(record.keys())}")
                
                # Adjust these field names to match your actual Supabase client table schema
                client_name = (record.get('client_name') or 
                             record.get('name') or 
                             record.get('company_name'))
                
                search_terms = (record.get('search_terms') or 
                              record.get('keywords') or 
                              record.get('monitoring_terms'))
                
                status = record.get('status', 'active')
                
                if status.lower() == 'active' and client_name and search_terms:
                    # Handle different search term formats
                    if isinstance(search_terms, str):
                        # Split comma-separated terms
                        terms = [t.strip() for t in search_terms.split(',') if t.strip()]
                    elif isinstance(search_terms, list):
                        terms = search_terms
                    else:
                        continue
                    
                    if terms:  # Only add if we have actual search terms
                        client_terms[client_name] = terms
                        logger.info(f"Added client: {client_name} with {len(terms)} search terms")
            
            logger.info(f"Successfully loaded {len(client_terms)} active clients from Supabase")
            return client_terms
                
        except Exception as e:
            logger.error(f"Error fetching client search terms from Supabase: {e}")
            logger.warning("Using fallback test data")
            return self._get_fallback_clients()
    
    def _get_fallback_clients(self):
        """Fallback client data for testing"""
        return {
            "TestClient1": ["artificial intelligence", "machine learning", "AI regulation"],
            "TestClient2": ["online dating", "dating apps", "relationship technology"], 
            "TestClient3": ["renewable energy", "solar power", "wind energy"]
        }
    
    def generate_google_news_url(self, search_term: str, domain: str) -> str:
        """Generate Google News site-filtered URL (same as Link Creator logic)"""
        encoded_term = urllib.parse.quote_plus(f'"{search_term}"')
        url = f"https://www.google.com/search?tbm=nws&q={encoded_term}+site:{domain}&gl=us"
        return url
    
    def scrape_google_news_results(self, url: str, outlet_name: str, domain: str, search_term: str, client_name: str) -> List[Dict]:
        """
        Scrape articles from a Google News URL.
        Returns list of article dictionaries ready for database insertion.
        """
        try:
            # Random delay for rate limiting
            time.sleep(random.uniform(*self.delay_range))
            
            # Rotate user agents
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []
            
            # Multiple selectors for Google News results (they change frequently)
            selectors = [
                'div[data-hveid] h3',
                'div.SoaBEf h3', 
                'div.xrnccd h3',
                'h3[role="heading"]',
                'div.g h3'
            ]
            
            news_results = []
            for selector in selectors:
                results = soup.select(selector)
                if results:
                    news_results = results
                    break
            
            # Parse each result
            for i, result in enumerate(news_results[:self.max_articles_per_site]):
                try:
                    # Extract headline
                    headline = result.get_text(strip=True)
                    if not headline:
                        continue
                    
                    # Extract link (traverse up to find parent with link)
                    link_elem = result.find_parent('a') or result.find('a')
                    if not link_elem:
                        # Try finding sibling or nearby link
                        parent = result.find_parent()
                        link_elem = parent.find('a') if parent else None
                    
                    if not link_elem:
                        continue
                        
                    link = link_elem.get('href', '')
                    
                    # Clean Google redirect URLs
                    if link.startswith('/url?q='):
                        link = urllib.parse.unquote(link.split('/url?q=')[1].split('&')[0])
                    elif link.startswith('/'):
                        continue  # Skip relative links
                    
                    # Extract snippet (look for nearby text)
                    snippet = ""
                    snippet_elem = result.find_parent().find('span', class_='st')
                    if not snippet_elem:
                        # Try other common snippet selectors
                        snippet_selectors = ['.st', '.s', '.Y2IQFc', '[data-content-feature="1"]']
                        for sel in snippet_selectors:
                            snippet_elem = result.find_parent().find(sel)
                            if snippet_elem:
                                break
                    
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                    
                    # Create article record (matching your Supabase column structure)
                    article = {
                        'permalink_url': link,                    # Where the story link goes
                        'source_title': headline,                 # Where the headline goes  
                        'created_at': datetime.now().isoformat(), # Time/date of scraping
                        'id': link,                              # Story link as ID
                        'subscription_source': f'GN_{client_name}_{search_term}',  # GN_[Client]_[Search Term]
                        'body': snippet,                         # Article snippet
                        'search_term': search_term,              # For filtering/debugging
                        'outlet_domain': domain,                 # For debugging (now defined)
                        'scraper_url': url                       # Store the search URL for debugging
                    }
                    
                    # Only add if we have minimum required fields
                    if headline and link:
                        articles.append(article)
                
                except Exception as e:
                    logger.warning(f"Error parsing result {i}: {e}")
                    continue
            
            logger.info(f"Scraped {len(articles)} articles from {domain} for '{search_term}'")
            return articles
            
        except requests.RequestException as e:
            logger.error(f"Request error scraping {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
            return []
    
    def run_mesh_ingestion(self) -> Dict[str, int]:
        """
        Main ingestion process - scrape all clients and search terms.
        Returns statistics about the ingestion run.
        """
        start_time = datetime.now()
        logger.info("🚀 Starting mesh ingestion process...")
        
        stats = {
            'clients_processed': 0,
            'search_terms_processed': 0,
            'urls_scraped': 0,
            'articles_found': 0,
            'articles_inserted': 0,
            'duplicates_skipped': 0,
            'errors': 0
        }
        
        try:
            # Get all client search terms
            client_terms = self.get_client_search_terms()
            
            if not client_terms:
                logger.warning("No client search terms found")
                return stats
            
            # Get all unique outlets (combine categories, remove duplicates)
            all_outlets = []
            for category in self.outlet_categories.values():
                all_outlets.extend(category)
            
            # Remove duplicates while preserving order
            seen_domains = set()
            unique_outlets = []
            for outlet_name, domain in all_outlets:
                if domain not in seen_domains:
                    unique_outlets.append((outlet_name, domain))
                    seen_domains.add(domain)
            
            logger.info(f"Processing {len(client_terms)} clients across {len(unique_outlets)} outlets")
            
            # Process each client
            for client_name, search_terms in client_terms.items():
                logger.info(f"📊 Processing client: {client_name}")
                stats['clients_processed'] += 1
                
                # Process each search term for this client
                for search_term in search_terms:
                    logger.info(f"🔍 Processing search term: '{search_term}'")
                    stats['search_terms_processed'] += 1
                    
                    # Generate URLs for each outlet
                    for outlet_name, domain in unique_outlets:
                        try:
                            stats['urls_scraped'] += 1
                            
                            # Generate Google News URL
                            url = self.generate_google_news_url(search_term, domain)
                            
                            # Scrape articles
                            articles = self.scrape_google_news_results(
                                url, outlet_name, domain, search_term, client_name
                            )
                            
                            stats['articles_found'] += len(articles)
                            
                            # Insert articles into database
                            for article in articles:
                                try:
                                    # Check for duplicates
                                    if self.deduper.is_duplicate(article):
                                        stats['duplicates_skipped'] += 1
                                        continue
                                    
                                    # Insert into database
                                    success = self.soup_pusher.insert_article(article)
                                    if success:
                                        stats['articles_inserted'] += 1
                                        logger.debug(f"✅ Inserted: {article['source_title'][:50]}...")
                                    else:
                                        stats['errors'] += 1
                                        
                                except Exception as e:
                                    logger.error(f"Error inserting article: {e}")
                                    stats['errors'] += 1
                        
                        except Exception as e:
                            logger.error(f"Error processing {outlet_name}: {e}")
                            stats['errors'] += 1
                
                # Brief pause between clients
                time.sleep(1)
        
        except Exception as e:
            logger.error(f"Critical error in mesh ingestion: {e}")
            stats['errors'] += 1
        
        # Log execution summary
        duration = datetime.now() - start_time
        logger.info(f"🏁 Mesh ingestion completed in {duration}")
        logger.info(f"📈 Stats: {stats}")
        
        # Send alert if success rate is low
        if stats['urls_scraped'] > 0:
            success_rate = (stats['articles_found'] / stats['urls_scraped']) * 100
            if success_rate < 30:  # Less than 30% of URLs returned articles
                logger.warning(f"⚠️ Low success rate: {success_rate:.1f}% - possible scraper issues")
        
        return stats
    
    def health_check(self) -> Dict[str, bool]:
        """
        Perform health check on key components.
        Returns status of database, config, etc.
        """
        health = {
            'database_connection': False,
            'config_loaded': False,
            'outlets_loaded': False
        }
        
        try:
            # Test database connection
            health['database_connection'] = self.soup_pusher.test_connection()
        except:
            pass
        
        try:
            # Test config
            config = self.config_loader.get_supabase_config()
            health['config_loaded'] = bool(config)
        except:
            pass
        
        try:
            # Test outlets
            health['outlets_loaded'] = len(self.outlet_categories) > 0
        except:
            pass
        
        return health

def main():
    """Main execution function for testing"""
    mesh_scraper = MeshScraper()
    
    # Run health check
    health = mesh_scraper.health_check()
    logger.info(f"Health check: {health}")
    
    if not all(health.values()):
        logger.error("Health check failed - aborting")
        return
    
    # Run mesh ingestion
    stats = mesh_scraper.run_mesh_ingestion()
    logger.info(f"Final stats: {stats}")

if __name__ == "__main__":
    main()