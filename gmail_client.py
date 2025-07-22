# gmail_client.py - Gmail API wrapper (Updated for Service Account)
import pickle
import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import email
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GmailClient:
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    def __init__(self, config):
        self.config = config
        self.service = self._authenticate()
        self.processed_label_id = self._get_or_create_label('Processed Google Alerts')
        self.archive_label_id = self._get_or_create_label('Archive/Extracted Alerts')
        
    def _authenticate(self):
        """Authenticate with Gmail API - prefer OAuth over Service Account"""
        try:
            # Try OAuth first (simpler and more reliable for personal Gmail)
            logger.info("Attempting OAuth authentication")
            return self._oauth_authenticate()
                
        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            logger.info("Falling back to Service Account authentication")
            
            # Fall back to Service Account if OAuth fails
            if all(key in self.config for key in ['google_project_id', 'google_private_key', 'google_client_email']):
                logger.info("Using Service Account authentication")
                
                # Create service account credentials from config
                service_account_info = {
                    "type": "service_account",
                    "project_id": self.config['google_project_id'],
                    "private_key_id": self.config.get('google_private_key_id', ''),
                    "private_key": self.config['google_private_key'].replace('\\n', '\n'),
                    "client_email": self.config['google_client_email'],
                    "client_id": "",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                }
                
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=self.SCOPES)
                
                # For Gmail API with service account, you need to delegate to a user
                if 'delegate_email' in self.config:
                    credentials = credentials.with_subject(self.config['delegate_email'])
                
                return build('gmail', 'v1', credentials=credentials)
            else:
                raise Exception("Neither OAuth nor Service Account credentials properly configured")
    
    def _oauth_authenticate(self):
        """Authenticate using OAuth flow"""
        creds = None
        
        # Token file stores the user's access and refresh tokens
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
                
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
            else:
                logger.info("Starting OAuth flow")
                if not os.path.exists('credentials.json'):
                    raise Exception("credentials.json file not found. Please download it from Google Cloud Console.")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                # Use fixed port 8501 to match OAuth configuration
                creds = flow.run_local_server(port=8501)
            
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
                
        return build('gmail', 'v1', credentials=creds)
    
    def _get_or_create_label(self, label_name):
        """Get or create a Gmail label"""
        try:
            labels = self.service.users().labels().list(userId='me').execute()
            for label in labels.get('labels', []):
                if label['name'] == label_name:
                    return label['id']
            
            # Create the label if it doesn't exist
            label_body = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            created_label = self.service.users().labels().create(
                userId='me', body=label_body).execute()
            return created_label['id']
            
        except Exception as e:
            logger.error(f"Error managing labels: {str(e)}")
            return None
    
    def fetch_unprocessed_alerts(self, max_emails=50):
        """Fetch unprocessed Google News Alert emails with pagination support"""
        try:
            # Search for Google Alert emails that aren't processed
            # Note: Gmail API has issues with combined from: and -label: queries
            # Using -has:userlabels as a more reliable alternative
            query = f'from:googlealerts-noreply@google.com -has:userlabels'
            
            all_messages = []
            page_token = None
            
            # Fetch emails across multiple pages until we have enough or run out
            while len(all_messages) < max_emails:
                query_params = {
                    'userId': 'me',
                    'q': query,
                    'maxResults': min(100, max_emails - len(all_messages))  # Gmail API max is 500
                }
                
                if page_token:
                    query_params['pageToken'] = page_token
                
                results = self.service.users().messages().list(**query_params).execute()
                messages = results.get('messages', [])
                
                if not messages:
                    break  # No more emails
                    
                all_messages.extend(messages)
                
                # Check if there are more pages
                page_token = results.get('nextPageToken')
                if not page_token:
                    break  # No more pages
            
            # Limit to requested amount
            messages_to_process = all_messages[:max_emails]
            
            # Parse email metadata
            emails = []
            for message in messages_to_process:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id'], format='full').execute()
                emails.append(self._parse_email_metadata(msg))
                
            logger.info(f"Fetched {len(emails)} unprocessed emails from {len(all_messages)} available across multiple pages")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return []
    
    def _parse_email_metadata(self, message):
        """Extract metadata from Gmail message"""
        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
        
        # Get email body
        body = self._get_email_body(message['payload'])
        
        return {
            'id': message['id'],
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'date': headers.get('Date', ''),
            'body': body,
            'thread_id': message.get('threadId', '')
        }
    
    def _get_email_body(self, payload):
        """Extract HTML body from email payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        elif payload['mimeType'] == 'text/html':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')
            
        return body
    
    def mark_as_processed(self, message_id):
        """Mark email as processed and archive it (deprecated - use delete_email instead)"""
        try:
            # Add both processed and archive labels, remove from inbox
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': [self.processed_label_id, self.archive_label_id],
                    'removeLabelIds': ['INBOX']  # Move out of inbox (archives it)
                }
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking email as processed and archived: {str(e)}")
            return False
    
    def delete_email(self, message_id):
        """Permanently delete an email after successful import"""
        try:
            # Use trash() first, then immediately expunge to permanently delete
            # This ensures it bypasses Gmail's normal trash retention
            self.service.users().messages().trash(userId='me', id=message_id).execute()
            # Note: Gmail API doesn't allow immediate permanent deletion in one step
            # The daily purge will clean up the trash
            logger.info(f"Successfully deleted email {message_id} (moved to trash)")
            return True
        except Exception as e:
            logger.error(f"Error deleting email {message_id}: {str(e)}")
            return False
    
    def daily_purge_trash(self):
        """Daily purge of trash - permanently delete emails older than 7 days from trash"""
        try:
            # Calculate date 7 days ago for trash purging
            week_ago = datetime.now() - timedelta(days=7)
            date_str = week_ago.strftime('%Y/%m/%d')
            
            # Search for emails in trash older than 7 days
            query = f'in:trash before:{date_str}'
            
            logger.info(f"Starting daily trash purge for emails before {date_str}")
            
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=1000).execute()
            
            messages = results.get('messages', [])
            purged_count = 0
            
            if not messages:
                logger.info("No old emails found in trash to purge")
                return 0
            
            logger.info(f"Found {len(messages)} emails in trash older than 7 days")
            
            # Process in smaller batches for trash purging
            batch_size = 25  # Smaller batches for permanent deletion
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                
                for message in batch:
                    try:
                        # Permanently delete from trash (this is irreversible)
                        self.service.users().messages().delete(userId='me', id=message['id']).execute()
                        purged_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Error permanently deleting email {message['id']} from trash: {e}")
                        continue
                
                # Longer delay between batches for permanent deletion operations
                import time
                time.sleep(1.0)
            
            logger.info(f"Daily trash purge completed: {purged_count} emails permanently deleted")
            return purged_count
            
        except Exception as e:
            logger.error(f"Error during daily trash purge: {str(e)}")
            return 0
    
    def weekly_cleanup_non_google_alerts(self):
        """Delete emails that are NOT from Google Alerts and older than 7 days"""
        try:
            # Calculate date 7 days ago
            week_ago = datetime.now() - timedelta(days=7)
            date_str = week_ago.strftime('%Y/%m/%d')
            
            # Search for emails NOT from Google Alerts and older than 7 days
            query = f'-from:googlealerts-noreply@google.com before:{date_str}'
            
            logger.info(f"Starting weekly cleanup of non-Google Alert emails before {date_str}")
            
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=500).execute()
            
            messages = results.get('messages', [])
            deleted_count = 0
            
            if not messages:
                logger.info("No old non-Google Alert emails found to delete")
                return 0
            
            # Process in batches to avoid rate limits
            batch_size = 50
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                
                for message in batch:
                    try:
                        # Get email details for logging
                        msg = self.service.users().messages().get(
                            userId='me', id=message['id'], format='metadata').execute()
                        
                        headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
                        subject = headers.get('Subject', 'No Subject')[:50]
                        from_addr = headers.get('From', 'Unknown')
                        
                        # Delete the email
                        if self.delete_email(message['id']):
                            deleted_count += 1
                            logger.debug(f"Deleted: {subject} from {from_addr}")
                        
                    except Exception as e:
                        logger.warning(f"Error processing email {message['id']} for deletion: {e}")
                        continue
                
                # Small delay between batches to respect rate limits
                import time
                time.sleep(0.5)
            
            logger.info(f"Weekly cleanup completed: {deleted_count} non-Google Alert emails deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during weekly cleanup: {str(e)}")
            return 0
    
    def get_email_stats(self):
        """Get statistics about email counts for monitoring"""
        try:
            stats = {}
            
            # Count Google Alert emails
            google_results = self.service.users().messages().list(
                userId='me', q='from:googlealerts-noreply@google.com').execute()
            stats['google_alerts'] = len(google_results.get('messages', []))
            
            # Count processed Google Alerts
            processed_results = self.service.users().messages().list(
                userId='me', q=f'label:{self.processed_label_id}').execute()
            stats['processed_alerts'] = len(processed_results.get('messages', []))
            
            # Count total emails
            total_results = self.service.users().messages().list(
                userId='me', maxResults=1).execute()
            stats['total_emails'] = total_results.get('resultSizeEstimate', 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting email stats: {str(e)}")
            return {}