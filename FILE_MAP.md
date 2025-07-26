File Map - Google News Alert Ingestion System                                        
🎯 Primary Flow: main.py → Gmail Client → Alert Parser → Database Storage

🔄 Process Integration:
News_Alert_Ingestion/
├── main.py                         # 🎯 Main orchestrator (5-step process)
│   ├── Step 1: Email Fetching      # 📧 Gmail API client initialization  
│   ├── Step 2: Alert Parsing       # 🔍 HTML parsing & article extraction
│   ├── Step 3: Multi-Article Loop  # 🔄 Process ALL articles (not just first)
│   ├── Step 4: Database Storage    # 💾 Supabase insertion with deduplication
│   └── Step 5: Email Management    # 🗂️ Mark processed/delete emails
└── requirements.txt                # 📦 All dependencies

📦 Core Application Structure:

🏗️ Source Code Organization:
src/
├── clients/
│   └── gmail_client.py             # 🎯 GmailClient class
│                                   # 📋 fetch_unprocessed_alerts(), mark_as_processed()
│                                   # 🔐 OAuth + Service Account authentication
├── parsers/
│   └── google_parser.py            # 🎯 AlertParser class (Google Alert format)
│                                   # 📋 parse_alert() → Returns LIST of articles
│                                   # 🔄 Multi-article processing (fixed from single)
├── database/
│   ├── soup_pusher.py              # 📤 SoupPusher class (Supabase integration)
│   └── dedupe_utils.py             # 🔍 DedupeUtils class (hash-based deduplication)
├── config/
│   ├── loader.py                   # 🎯 ConfigLoader class (environment variables)
│   └── sources.yaml                # 📄 Email source definitions
│                                   # 🥇 Google Alerts: googlealerts-noreply@google.com
│                                   # 🥈 Muck Rack: [Ready for configuration]
└── utils/
    └── health_check.py             # 🏥 Health monitoring endpoints

📊 Article Data Structure:
{
    'headline': str,                    # Article title
    'story_link': str,                  # Clean article URL  
    'body': str,                        # Article snippet/description
    'source': 'Google Alert',           # Alert source identifier
    'search': str,                      # Search term from alert
    'date': str,                        # ISO format timestamp
    'raw_email_id': str                 # Gmail message ID for tracking
}

🎯 Processing Flow:
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Gmail Client → Parser → Database → Email Cleanup (Every 15 minutes)           │
│ Multi-article processing ensures ALL articles extracted per email              │
└─────────────────────────────────────────────────────────────────────────────────┘

✅ **ARCHITECTURE STATUS: 100% REORGANIZED & ENHANCED**
• Multi-Article Processing: Fixed critical bug (was only processing first article)
• Clean Architecture: Organized into logical packages (clients/parsers/database/config)
• Extensible Design: Ready for Muck Rack & additional sources via configuration
• Enhanced Security: Automated email cleanup & trash purging
• Production Ready: Automated scheduling, monitoring, and cleanup

🚀 **DEPLOYMENT MODEL:**
• Single application deployment (`python main.py`)
• Self-contained (Gmail + Supabase only)
• Configuration-driven source management
• Ready for Muck Rack integration 