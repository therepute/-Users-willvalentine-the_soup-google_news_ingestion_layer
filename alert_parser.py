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
        """Parse a Google News Alert email and extract a list of articles"""
        try:
            subject = email_data['subject']
            body = email_data['body']
            email_date = email_data['date']
            
            if not self._is_google_alert(subject, email_data['from']):
                return []
            
            # Extract search term from subject
            search_term = self._extract_search_term(subject)
            
            # Parse HTML body
            soup = BeautifulSoup(body, 'html.parser')
            extracted_articles = self._extract_articles(soup)
            
            if not extracted_articles:
                logger.warning(f"No articles found in alert: {subject}")
                return []
            
            # Process all articles found in the email
            processed_articles = []
            for article in extracted_articles:
                article_data = {
                    'headline': article['headline'],
                    'story_link': article['link'],
                    'body': article['snippet'],
                    'source': 'Google Alert',
                    'search': search_term,
                    'date': self._parse_date(email_date),
                    'raw_email_id': email_data['id']
                }
                processed_articles.append(article_data)
            
            return processed_articles
            
        except Exception as e:
            logger.error(f"Error parsing alert: {str(e)}")
            return []
    
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
        """Extract snippet from surrounding elements"""
        snippet = ''
        
        # Get the headline text
        headline = link_element.get_text(strip=True)
        
        # Early filtering: Skip non-legitimate content
        link_url = link_element.get('href', '')
        if any(domain in link_url.lower() for domain in ['youtube.com', 'facebook.com', 'm.facebook.com']):
            return '', snippet
        
        # Look for snippet in the description div
        container = link_element
        for _ in range(10):  # Look up to 10 levels up
            container = container.parent
            if not container:
                break
            
            desc_div = container.find('div', {'itemprop': 'description'})
            if desc_div:
                snippet = desc_div.get_text(strip=True)
                break
        
            # Fallback: look for snippet in the remaining text
            text_content = container.get_text(separator=' ', strip=True)
            lines = text_content.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if headline[:30] in line:  # Find line with headline
                    # Snippet is often a few lines after
                    for j in range(i + 1, min(i + 4, len(lines))):
                        potential_snippet = lines[j].strip()
                        if potential_snippet and len(potential_snippet) > 20 and 'Flag as irrelevant' not in potential_snippet:
                            snippet = potential_snippet
                            break
                    break
        
        return '', snippet
    
    def _parse_date(self, date_string):
        """Parse email date to ISO format"""
        try:
            # Gmail date format parsing
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_string)
            return dt.isoformat()
        except:
            return datetime.now().isoformat()