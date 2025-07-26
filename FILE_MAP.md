# File Map - Google News Alert Ingestion System
                                        
🎯 **Primary Flow**: main.py → Gmail API → Alert Parser → Database Storage

## 🔄 Process Integration:

```
News_Alert_Ingestion/
├── main.py                         # 🎯 Main orchestrator (5-step process)
│   ├── Step 1: Email Fetching      # 📧 Gmail API client initialization
│   ├── Step 2: Alert Parsing       # 🔍 HTML parsing & article extraction
│   ├── Step 3: Multi-Article Loop  # 🔄 Process ALL articles (not just first)
│   ├── Step 4: Database Storage    # 💾 Supabase insertion with deduplication
│   └── Step 5: Email Management    # 🗂️ Mark processed/delete emails
├── requirements.txt                # 📦 All dependencies
└── test_reorganization.py          # 🧪 Comprehensive functionality tests
```

## 📦 Core Application Structure:

### 🏗️ Source Code Organization:
```
src/
├── clients/                        # 📧 Email Service Clients
│   ├── __init__.py
│   └── gmail_client.py             # 🎯 GmailClient class
│                                   # 📋 fetch_unprocessed_alerts(), mark_as_processed()
│                                   # 🔐 OAuth + Service Account authentication
│                                   # 🧹 Auto-cleanup & trash management
│
├── parsers/                        # 🔍 Alert Processing Engines
│   ├── __init__.py
│   └── google_parser.py            # 🎯 AlertParser class (Google Alert format)
│                                   # 📋 parse_alert() → Returns LIST of articles
│                                   # 🔄 Multi-article processing (fixed from single)
│                                   # 🏆 HTML parsing with BeautifulSoup
│
├── database/                       # 💾 Data Operations
│   ├── __init__.py
│   ├── soup_pusher.py              # 📤 SoupPusher class
│   │                               # 📋 insert_article(), batch operations
│   │                               # 🗄️ Supabase client integration
│   └── dedupe_utils.py             # 🔍 DedupeUtils class
│                                   # 📋 get_existing_articles_count()
│                                   # 🔄 Hash-based deduplication
│
├── config/                         # ⚙️ Configuration Management
│   ├── __init__.py
│   ├── loader.py                   # 🎯 ConfigLoader class
│   │                               # 📋 get_gmail_config(), get_supabase_config()
│   │                               # 🔐 Environment variable loading
│   └── sources.yaml                # 📄 Email source definitions
│                                   # 🥇 Google Alerts: googlealerts-noreply@google.com
│                                   # 🥈 Muck Rack: [Ready for configuration]
│                                   # 🔧 Processing settings & query patterns
│
└── utils/                          # 🔧 Utility Functions
    ├── __init__.py
    └── health_check.py             # 🏥 Health monitoring endpoints
```

## 📊 Data Flow Architecture:

### 🔄 Email Processing Pipeline:
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. Gmail Client → Fetch unprocessed alerts (max 50 per run)                    │
│ 2. Alert Parser → Extract ALL articles per email (multi-article fix)          │
│ 3. Database Layer → Insert with deduplication & error handling                │
│ 4. Email Management → Mark processed/delete (security compliance)             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 📧 Email Source Configuration:
```yaml
email_sources:
  google_alerts:
    from_address: "googlealerts-noreply@google.com"
    parser_type: "google"
    enabled: true
    query: "from:{from_address} -has:userlabels"
  
  # Ready for extension:
  muck_rack:
    from_address: "[TO BE CONFIGURED]"
    parser_type: "muckrack"
    enabled: false
```

## 🎯 Core Classes & Methods:

### 📧 GmailClient (src/clients/gmail_client.py):
```python
class GmailClient:
    # 🔐 Authentication
    ├── _authenticate()                 # OAuth + Service Account fallback
    ├── _oauth_authenticate()           # Local OAuth flow
    
    # 📧 Email Operations  
    ├── fetch_unprocessed_alerts()      # Main email fetching with pagination
    ├── mark_as_processed()             # Label & archive emails
    ├── delete_email()                  # Security: permanent deletion
    
    # 🧹 Maintenance
    ├── daily_purge_trash()             # Auto-cleanup (security)
    ├── weekly_cleanup_non_google_alerts() # Remove non-alert emails
    └── get_email_stats()               # Monitoring & metrics
```

### 🔍 AlertParser (src/parsers/google_parser.py):
```python
class AlertParser:
    # 🎯 Main Processing
    ├── parse_alert(email_data)         # Returns LIST of articles (multi-fix)
    ├── _extract_articles(soup)         # Find ALL article links in HTML
    ├── _extract_actual_url()           # Decode Google tracking URLs
    
    # ✅ Validation
    ├── _is_google_alert()              # Verify email source authenticity
    └── _parse_date()                   # Standardize date formats
```

### 💾 Database Layer:
```python
class SoupPusher:                       # Supabase integration
    ├── insert_article()                # Single article insertion
    └── [batch operations]              # Future: bulk processing

class DedupeUtils:                      # Deduplication engine
    ├── get_existing_articles_count()   # Statistics
    └── [hash-based dedup]              # Prevent duplicate articles
```

## 📋 Article Data Structure:
```python
{
    'headline': str,                    # Article title
    'story_link': str,                  # Clean article URL
    'body': str,                        # Article snippet/description
    'source': 'Google Alert',           # Alert source identifier
    'search': str,                      # Search term from alert
    'date': str,                        # ISO format timestamp
    'raw_email_id': str                 # Gmail message ID for tracking
}
```

## ⚙️ Configuration & Environment:

### 🔐 Required Environment Variables:
```bash
# Supabase Configuration
SUPABASE_URL=                          # Project URL
SUPABASE_SERVICE_ROLE_KEY=             # Service role key (not anon)
SUPABASE_TABLE_NAME=Soup_Dedupe        # Main articles table
DEDUPE_TABLE_NAME=article_hashes       # Deduplication table

# Gmail Authentication (OAuth OR Service Account)
GOOGLE_PROJECT_ID=                     # Google Cloud project
GOOGLE_CLIENT_EMAIL=                   # Service account email
GOOGLE_PRIVATE_KEY=                    # Service account private key
# ... (additional Google auth variables)
```

## 🚀 Deployment & Operations:

### 📅 Scheduling (Automated):
```python
# main.py scheduling configuration
├── process_alerts()                   # Every 15 minutes
├── weekly_cleanup_non_google_alerts() # Sundays at 2:00 AM  
├── daily_purge_trash()                # Daily at 3:00 AM (security)
└── log_system_stats()                 # Daily at 12:01 AM
```

### 🏥 Health Monitoring:
```python
# Flask health endpoint (main.py)
GET /health → {'status': 'healthy'}    # Port 5000
```

### 📊 Statistics Tracking:
```python
{
    'emails_checked': int,              # Emails processed this run
    'valid_alerts_parsed': int,         # Articles extracted (ALL, not just first)
    'articles_inserted': int,           # Successfully stored
    'duplicates_skipped': int,          # Deduplication hits
    'emails_deleted': int               # Cleaned up emails
}
```

## 🔧 Service Management Scripts:
```
├── manage_service.sh                  # 🎯 Main service control
├── monitor_service.sh                 # 📊 Process monitoring  
├── restart_service.sh                 # 🔄 Automatic restart
├── setup_local.sh                     # 🏗️ Local development setup
└── notification_config.sh             # 📢 Alert notifications
```

## ✅ **ARCHITECTURE STATUS: 100% REORGANIZED & ENHANCED**

### 🎉 Key Improvements Made:
• **Multi-Article Processing**: Fixed critical bug (was only processing first article)
• **Clean Architecture**: Organized into logical packages (clients/parsers/database/config)
• **Extensible Design**: Ready for Muck Rack & additional sources via configuration
• **Enhanced Security**: Automated email cleanup & trash purging
• **Better Monitoring**: Comprehensive health checks & statistics
• **Professional Structure**: Follows Python best practices with proper imports

### 🚀 **DEPLOYMENT MODEL:**
• **Single Application**: `python main.py` starts entire system
• **Dependency Management**: `pip install -r requirements.txt`  
• **Configuration-Driven**: Add new sources via `sources.yaml`
• **Self-Contained**: No external services required (just Gmail + Supabase)
• **Production Ready**: Automated scheduling, monitoring, and cleanup

### 🔮 **EXTENSION READY:**
• **Muck Rack Integration**: Just add from_address to `sources.yaml` + create `muckrack_parser.py`
• **Additional Sources**: Framework supports unlimited email alert sources
• **Advanced Processing**: Parser factory pattern ready for source-specific logic
• **Scalability**: Database layer ready for batch processing & optimization 