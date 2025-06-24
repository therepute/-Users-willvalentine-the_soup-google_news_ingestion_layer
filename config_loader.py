# config_loader.py - Load config from .env file
import os
from dotenv import load_dotenv

class ConfigLoader:
    def __init__(self, env_path=None):
        # Load environment variables from .env file
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()  # Loads from .env in current directory
            
        # Verify required variables are loaded
        required_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    def get_gmail_config(self):
        """Extract Gmail configuration"""
        return {
            'max_emails_per_run': int(os.getenv('MAX_EMAILS_PER_RUN', '50')),
            'google_project_id': os.getenv('GOOGLE_PROJECT_ID'),
            'google_client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'google_client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'google_client_email': os.getenv('GOOGLE_CLIENT_EMAIL'),
            'google_private_key': os.getenv('GOOGLE_PRIVATE_KEY'),
            'google_private_key_id': os.getenv('GOOGLE_PRIVATE_KEY_ID')
        }
    
    def get_supabase_config(self):
        """Extract Supabase configuration"""
        return {
            'url': os.getenv('SUPABASE_URL'),
            'key': os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
            'table_name': os.getenv('SUPABASE_TABLE_NAME', 'Soup_Dedupe'),
            'dedupe_table': os.getenv('DEDUPE_TABLE_NAME', 'article_hashes')
        }
    
    def get_parsing_config(self):
        """Get parsing configuration"""
        return {
            'min_headline_length': 10,
            'max_snippet_length': 500
        }
    
    def get_logging_config(self):
        """Get logging configuration"""
        return {
            'level': 'INFO',
            'retention_days': 30
        }