# Migration Cron URL Usage

Simple HTTP endpoint to process quotations one at a time, perfect for cron jobs.

## URL Endpoints

### 1. Process One Quotation
**URL:** `http://your-odoo-url:port/migration/process_one`

**Method:** GET

**Description:** 
- Shows current status
- Processes the first quotation in queue (if nothing is currently migrating)
- Returns simple text response

**Example:**
```bash
curl http://localhost:8079/migration/process_one
```

**Response:**
```
Total Queued: 1000
Migrating Now: S00061
DONE
```

### 2. Get Status Only (No Processing)
**URL:** `http://your-odoo-url:port/migration/status`

**Method:** GET

**Description:** 
- Returns JSON with current migration status
- Does NOT process any quotations

**Example:**
```bash
curl http://localhost:8079/migration/status
```

**Response:**
```json
{
  "total_queued": 1000,
  "migrating_now": "S00061",
  "total_migrated": 50,
  "total_errors": 2
}
```

## Usage as Cron Job

### Linux Cron Example

Add to crontab (`crontab -e`):
```bash
# Process one quotation every minute
* * * * * curl -s http://localhost:8079/migration/process_one

# Or with logging
* * * * * curl -s http://localhost:8079/migration/process_one >> /var/log/migration.log 2>&1
```

### Windows Task Scheduler

1. Create a batch file `migrate_one.bat`:
```batch
@echo off
curl -s http://localhost:8079/migration/process_one
```

2. Schedule it to run every minute in Task Scheduler

### Using wget (if curl not available)

```bash
* * * * * wget -q -O - http://localhost:8079/migration/process_one
```

## How It Works

1. **First Call:** Finds first quotation in queue, processes it
2. **While Migrating:** Shows "Migrating Now: S00061" and does nothing
3. **After Migration:** Next call will process the next quotation
4. **Repeat:** Keep calling the URL to process one at a time

## Response Format

The `/migration/process_one` endpoint returns:
- `Total Queued: <number>` - Total quotations waiting to be migrated
- `Migrating Now: <quotation_number>` - Currently migrating quotation (or "None")
- `DONE` - End marker

## Notes

- **Authentication:** Endpoint uses `auth='public'` - you may want to add authentication
- **Processing:** Uses queue jobs for async processing (non-blocking)
- **Status Updates:** Status updates in real-time as migrations complete
- **Error Handling:** Errors are logged and status is updated to "error"

## Security Note

The endpoint is currently set to `auth='public'` for easy cron access. For production, consider:
1. Adding authentication token
2. Using IP whitelist
3. Adding rate limiting
