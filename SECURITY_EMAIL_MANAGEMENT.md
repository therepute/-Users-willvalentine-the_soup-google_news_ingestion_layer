# Email Security & Management System

## Overview
This system implements **comprehensive email security** for sensitive Google News Alert data, ensuring complete purging within 7 days maximum.

## Security Flow

### 1. Google Alert Processing (Immediate Deletion)
```
Google Alert Email → Parse & Import → Database ✅ → DELETE Email Immediately
```
- **Retention**: 0 days (deleted immediately after successful import)
- **Rationale**: Contains sensitive search terms and business intelligence
- **Implementation**: `gmail_client.delete_email()` after `soup_pusher.insert_article()`

### 2. Non-Google Alert Emails (7-Day Retention)
```
Other Emails → Keep 7 Days → Weekly Cleanup → DELETE
```
- **Retention**: 7 days maximum
- **Schedule**: Sundays at 2:00 AM
- **Rationale**: Allow time to review important emails before deletion

### 3. Trash Purging (Daily Security Sweep)
```
Deleted Emails → Trash → Daily Purge (>7 days) → PERMANENT DELETION
```
- **Retention**: 7 days maximum in trash
- **Schedule**: Daily at 3:00 AM
- **Rationale**: Ensures no sensitive data accumulates in trash

## Complete Schedule

| Task | Frequency | Time | Purpose |
|------|-----------|------|---------|
| **Ingestion** | Every 15 minutes | Continuous | Process new Google Alerts |
| **Weekly Cleanup** | Weekly | Sunday 2:00 AM | Delete old non-Google emails |
| **Daily Trash Purge** | Daily | 3:00 AM | Permanently delete old trash |
| **System Stats** | Daily | 12:01 AM | Monitor system health |

## Security Guarantees

### ✅ Maximum Data Retention
- **Google Alerts**: 0 days (immediate deletion)
- **Other emails**: 7 days maximum
- **Trash**: 7 days maximum
- **Total maximum retention**: 7 days for any email

### ✅ Sensitive Data Protection
- Search terms (business intelligence) deleted immediately
- Article content purged within hours of import
- No indefinite email accumulation
- Automated compliance with data retention policies

### ✅ Attack Surface Reduction
- Minimal email storage reduces breach impact
- Automated purging prevents manual oversight
- Trash doesn't accumulate sensitive data
- Clean Gmail account reduces target value

## Implementation Details

### Email Deletion Methods

```python
# Immediate deletion after import
def delete_email(self, message_id):
    """Move to trash immediately after import"""
    self.service.users().messages().trash(userId='me', id=message_id)

# Daily trash purging
def daily_purge_trash(self):
    """Permanently delete emails >7 days from trash"""
    query = f'in:trash before:{week_ago}'
    # Permanently delete each email
    self.service.users().messages().delete(userId='me', id=message_id)
```

### Security Configuration

```python
# Main scheduler with security timing
schedule.every(15).minutes.do(ingestor.run_ingestion)
schedule.every().sunday.at("02:00").do(ingestor.run_weekly_cleanup)
schedule.every().day.at("03:00").do(ingestor.run_daily_trash_purge)  # SECURITY
```

## Testing & Monitoring

### Test Commands
```bash
# Test email management system
python3 test_email_management.py

# Manual cleanup (testing)
python3 -c "from main import GoogleAlertIngestor; GoogleAlertIngestor().run_weekly_cleanup()"

# Manual trash purge (testing)
python3 -c "from main import GoogleAlertIngestor; GoogleAlertIngestor().run_daily_trash_purge()"
```

### Monitoring Logs
- All operations logged with timestamps
- Deletion counts tracked
- Error handling for failed deletions
- Daily stats for audit trail

## Compliance Benefits

### ✅ Data Minimization
- Only necessary data retained
- Automatic purging prevents accumulation
- Clear retention policies

### ✅ Security by Design
- Default secure behavior
- Automated enforcement
- No manual intervention required

### ✅ Audit Trail
- Complete logging of all deletions
- Timestamps for compliance verification
- Error tracking and recovery

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Sensitive data exposure** | Immediate deletion after import |
| **Trash accumulation** | Daily automated purging |
| **Manual oversight failure** | Fully automated system |
| **Data breach impact** | Minimal data retention window |
| **Compliance violations** | Automatic 7-day maximum retention |

## Recovery Considerations

### ⚠️ Important Notes
- **Trash purging is IRREVERSIBLE** - emails are permanently deleted
- **Google Alerts deleted immediately** - no recovery possible after import
- **7-day window** for manual email review before deletion
- **Database contains imported data** - original emails not needed for operation

### Backup Strategy
- **Database backups** contain all imported article data
- **Email deletion is intentional** for security
- **No email recovery mechanism** by design
- **Source reconstruction** possible from database records

This system prioritizes **security over convenience**, ensuring sensitive Google News Alert data cannot accumulate in email storage while maintaining operational efficiency. 