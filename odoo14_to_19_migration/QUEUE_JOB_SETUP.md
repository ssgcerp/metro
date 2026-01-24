# Queue Job Setup for Migration

This module now uses `queue_job` for background processing of migrations. This provides:
- ✅ No UI blocking
- ✅ Automatic retry on failure
- ✅ Resume after server restart
- ✅ Better error handling
- ✅ Scalable for large datasets (7,184+ records)

## Installation Steps

### 1. Install queue_job Module

**Option A: From OCA (Recommended)**
```bash
# Add OCA addons path to your Odoo configuration
addons_path = /path/to/odoo/addons,/path/to/oca/addons

# Install via pip
pip install odoo-addon-queue-job
```

**Option B: Manual Installation**
1. Download from: https://github.com/OCA/queue
2. Place in your addons directory
3. Update module list in Odoo

### 2. Install Queue Job Module in Odoo

1. Go to **Apps** menu
2. Remove "Apps" filter
3. Search for "Queue Job"
4. Click **Install**

### 3. Start Queue Worker

The queue worker must be running to process background jobs.

**Option A: Command Line**
```bash
odoo-bin queue_job --workers=2
```

**Option B: Docker**
```yaml
command: ["odoo", "queue_job", "--workers=2"]
```

**Option C: Systemd Service**
Create `/etc/systemd/system/odoo-queue.service`:
```ini
[Unit]
Description=Odoo Queue Job Worker
After=network.target

[Service]
Type=simple
User=odoo
WorkingDirectory=/opt/odoo
ExecStart=/opt/odoo/odoo-bin queue_job --workers=2
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable odoo-queue
sudo systemctl start odoo-queue
```

### 4. Verify Setup

1. Go to **Settings → Technical → Queue → Jobs**
2. You should see jobs being processed
3. Check worker logs to ensure jobs are running

## Usage

### Starting Migration

1. Open **Migration → Customers** menu
2. Select your migration configuration
3. Click **Check** to count records
4. Click **Start Migration** (ONCE)
5. Migration runs in background
6. Click **Refresh Status** to see progress

### Monitoring

- **Settings → Technical → Queue → Jobs**: See all jobs, retry failed ones, view logs
- **Migration Wizard**: Shows real-time progress (refresh to update)

### Troubleshooting

**Jobs not processing?**
- Check queue worker is running: `ps aux | grep queue_job`
- Check worker logs for errors
- Verify queue_job module is installed

**Migration stuck?**
- Go to **Settings → Technical → Queue → Jobs**
- Find the migration job
- Click **Retry** or **Cancel** if needed

**Need to resume?**
- Jobs automatically resume from last checkpoint
- Or manually retry from Queue Jobs interface

## Benefits Over Previous Approach

❌ **Old (Wizard-based):**
- Required JavaScript countdown
- Modal reuse issues
- Only worked for first batch
- UI blocking
- No retry mechanism

✅ **New (Queue Job):**
- One-click start
- Runs in background
- Auto-resume on restart
- Retry failed batches
- No UI blocking
- Enterprise-grade solution
