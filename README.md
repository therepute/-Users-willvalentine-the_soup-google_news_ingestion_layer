# Google News Alert Ingestion System

This system automatically processes Google News Alert emails and stores the extracted articles in a Supabase database with deduplication.

## Setup Instructions

### 1. Virtual Environment Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the `.env` file and fill in your credentials:

#### Required Supabase Configuration:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key (not anon key)

#### Gmail Authentication (Choose One):

**Option A: OAuth (Recommended for personal Gmail)**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download the credentials as `credentials.json`
6. Place `credentials.json` in the project root
7. Leave Google service account fields empty in `.env`

**Option B: Service Account (For GSuite/Workspace)**
1. Create a service account in Google Cloud Console
2. Download the service account JSON key
3. Fill in the Google credentials in `.env`:
   - `GOOGLE_PROJECT_ID`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_CLIENT_EMAIL`
   - `GOOGLE_PRIVATE_KEY`
   - `GOOGLE_PRIVATE_KEY_ID`
4. Optionally set `DELEGATE_EMAIL` for domain-wide delegation

### 3. Database Setup

Ensure your Supabase database has the required tables:
- `Soup_Dedupe` (or custom table name)
- `article_hashes` (for deduplication)

### 4. Running the System

```bash
# Activate virtual environment
source venv/bin/activate

# Run the ingestion system
python main.py
```

The system will:
- Run immediately on startup
- Schedule runs every 15 minutes
- Process Google News Alert emails
- Extract article data
- Check for duplicates
- Store in Supabase
- Mark emails as processed

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | Required |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Required |
| `SUPABASE_TABLE_NAME` | Main articles table | `Soup_Dedupe` |
| `DEDUPE_TABLE_NAME` | Deduplication table | `article_hashes` |
| `MAX_EMAILS_PER_RUN` | Max emails to process per run | `50` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_RETENTION_DAYS` | Log retention period | `30` |

### Google Authentication Variables

For OAuth (leave empty):
- `GOOGLE_PROJECT_ID`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_CLIENT_EMAIL`
- `GOOGLE_PRIVATE_KEY`
- `GOOGLE_PRIVATE_KEY_ID`

For Service Account (fill in):
- All the above variables
- `DELEGATE_EMAIL` (optional)

## File Structure

```
├── main.py              # Main entry point
├── gmail_client.py      # Gmail API wrapper
├── alert_parser.py      # Email parsing logic
├── soup_pusher.py       # Supabase integration
├── dedupe_utils.py      # Deduplication utilities
├── config_loader.py     # Configuration management
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables
├── credentials.json     # Google OAuth credentials (if using OAuth)
├── logs/                # Log files directory
└── README.md           # This file
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure credentials are properly configured
2. **Missing Dependencies**: Run `pip install -r requirements.txt`
3. **Database Connection**: Verify Supabase URL and service role key
4. **Permission Errors**: Check Gmail API permissions and scopes

### Logs

Check the `logs/ingestion.log` file for detailed error messages and processing statistics.

## Security Notes

- Never commit `.env` or `credentials.json` to version control
- Use service role keys, not anon keys for Supabase
- Keep Google credentials secure
- Consider using environment-specific configurations 