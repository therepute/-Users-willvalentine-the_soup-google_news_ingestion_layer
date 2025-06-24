# alert_parser.py - Parse Google Alert emails
from bs4 import BeautifulSoup
import re
import logging
from datetime import datetime
from urllib.parse import unquote
import hashlib

logger = logging.getLogger(__name__)

class AlertParser:
    def __init__(self):
        self.google_alert_patterns = {
            'subject_search_term': r'Google Alert - ["\']?([^"\']+)["\']?',
            'article_link': r'url=([^&]+)',
            'source_pattern': r'<td[^>]*><font[^>]*>([^<]+)</font></td>'
        }
    
    def parse_alert(self, email_data):
        """Parse a Google News Alert email and extract article data"""
        try:
            subject = email_data['subject']
            body = email_data['body']
            email_date = email_data['date']
            
            if not self._is_google_alert(subject, email_data['from']):
                return None
            
            # Extract search term from subject
            search_term = self._extract_search_term(subject)
            
            # Parse HTML body
            soup = BeautifulSoup(body, 'html.parser')
            articles = self._extract_articles(soup)
            
            if not articles:
                logger.warning(f"No articles found in alert: {subject}")
                return None
            
            # Process the first article (Google Alerts typically have multiple)
            # You might want to process all articles - modify as needed
            article = articles[0]
            
            # Create standardized record
            article_data = {
                'headline': article['headline'],
                'story_link': article['link'],
                'publication': article['source'],
                'body': article['snippet'],
                'source': 'Google Alert',
                'search': search_term,
                'date': self._parse_date(email_date),
                'raw_email_id': email_data['id']
            }
            
            return article_data
            
        except Exception as e:
            logger.error(f"Error parsing alert: {str(e)}")
            return None
    
    def _is_google_alert(self, subject, from_address):
        """Verify this is a Google Alert email"""
        return (
            'googlealerts-noreply@google.com' in from_address.lower() and
            'google alert' in subject.lower()
        )
    
    def _extract_search_term(self, subject):
        """Extract search term from email subject"""
        match = re.search(self.google_alert_patterns['subject_search_term'], subject)
        return match.group(1) if match else 'Unknown'
    
    def _extract_articles(self, soup):
        """Extract article data from HTML soup"""
        articles = []
        
        # Google Alerts have a specific structure - find all article links
        links = soup.find_all('a', href=True)
        
        current_article = None
        
        for link in links:
            href = link.get('href', '')
            
            # Skip Google's tracking URLs and footer links
            if self._is_article_link(href):
                # Extract the actual URL from Google's redirect
                actual_url = self._extract_actual_url(href)
                headline = link.get_text(strip=True)
                
                if headline and actual_url:
                    # Look for source and snippet in surrounding content
                    source, snippet = self._extract_context(link)
                    
                    articles.append({
                        'headline': headline,
                        'link': actual_url,
                        'source': source,
                        'snippet': snippet
                    })
        
        return articles
    
    def _is_article_link(self, href):
        """Check if this is an article link (not Google's internal links)"""
        if not href:
            return False
        
        # Google Alert article links typically contain 'url=' parameter
        return 'url=' in href and 'google.com' in href
    
    def _extract_actual_url(self, google_url):
        """Extract the actual article URL from Google's tracking URL"""
        match = re.search(r'url=([^&]+)', google_url)
        if match:
            return unquote(match.group(1))
        return google_url
    
    def _extract_context(self, link_element):
        """Extract source publication and snippet from surrounding elements"""
        source = 'Unknown'
        snippet = ''
        
        # Navigate up to find the table cell or div containing this article
        parent = link_element.parent
        article_container = None
        
        # Find the containing article block
        for _ in range(5):  # Look up to 5 levels up
            if parent and parent.name in ['td', 'div', 'table']:
                article_container = parent
                break
            parent = parent.parent if parent else None
        
        if article_container:
            # Look for source (usually in a font tag or immediately after the link)
            text_content = article_container.get_text(separator=' ', strip=True)
            lines = text_content.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                if link_element.get_text(strip=True) in line:
                    # Source is often the next line
                    if i + 1 < len(lines):
                        potential_source = lines[i + 1].strip()
                        if potential_source and len(potential_source) < 100:
                            source = potential_source
                    
                    # Snippet is often after the source
                    if i + 2 < len(lines):
                        snippet = lines[i + 2].strip()
                    break
        
        return source, snippet
    
    def _parse_date(self, date_string):
        """Parse email date to ISO format"""
        try:
            # Gmail date format parsing
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_string)
            return dt.isoformat()
        except:
            return datetime.now().isoformat()