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
                raise Exception("No valid authentication method available")
    
    def _oauth_authenticate(self):
        """Original OAuth authentication method"""
        creds = None
        token_file = 'token.pickle'
        
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
                
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Check if credentials.json exists
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError(
                        "credentials.json not found. Please download OAuth credentials from Google Cloud Console "
                        "or ensure Service Account credentials are properly configured in secrets.toml"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                # Debug info
                import json
                with open('credentials.json', 'r') as f:
                    creds_json = json.load(f)
                    print("Configured redirect URIs:", creds_json['installed'].get('redirect_uris', []))
                print(f"OAuth flow redirect URI: {getattr(flow, 'redirect_uri', 'Not set')}")
                print(f"About to start local server...")
                print(f"OAuth Client ID: {self.config.get('google_client_id', 'Not set')}")
                print(f"Using service account? {any(str(key).startswith('google_') for key in self.config.keys())}")
                creds = flow.run_local_server(port=8501)
            
            with open(token_file, 'wb') as token:
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
    
    def fetch_unprocessed_alerts(self):
        """Fetch unprocessed Google News Alert emails"""
        try:
            # Search for Google Alert emails that aren't processed
            query = f'from:googlealerts-noreply@google.com -label:{self.processed_label_id}'
            
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=50).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id'], format='full').execute()
                emails.append(self._parse_email_metadata(msg))
                
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
        """Mark email as processed and archive it"""
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