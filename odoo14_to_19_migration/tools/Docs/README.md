# Migration Monitor Tool

Real-time command-line tool to trigger and monitor Odoo 14 to 19 quotation migrations.

## Installation

No additional installation required - uses Python's built-in `xmlrpc` library.

## Usage

### 1. Monitor All Migrations in Real-Time

```bash
python migration_monitor.py --monitor --password your_password
```

### 2. Trigger Migration for Specific Quotations

```bash
python migration_monitor.py --trigger \
  --quotation-numbers S00031,S00032,S00033 \
  --password your_password
```

### 3. Trigger All Pending Migrations

```bash
python migration_monitor.py --trigger-all-pending --password your_password
```

### 4. Monitor Specific Quotations

```bash
python migration_monitor.py --monitor \
  --quotation-numbers S00031,S00032 \
  --password your_password
```

### 5. Show Current Status (One-Time)

```bash
python migration_monitor.py --password your_password
```

## Options

- `--url`: Odoo URL (default: http://localhost:8079)
- `--db`: Database name (default: metrodb)
- `--username`: Username (default: admin)
- `--password`: Password (required)
- `--trigger`: Trigger migration for specified quotations
- `--trigger-all-pending`: Trigger migration for all pending quotations
- `--monitor`: Monitor migration status in real-time
- `--quotation-numbers`: Comma-separated list of quotation numbers
- `--interval`: Monitoring refresh interval in seconds (default: 2)

## Examples

### Full Workflow: Trigger and Monitor

```bash
# Terminal 1: Trigger migrations
python migration_monitor.py --trigger-all-pending --password admin

# Terminal 2: Monitor in real-time
python migration_monitor.py --monitor --password admin --interval 1
```

### Monitor with Custom Refresh Rate

```bash
python migration_monitor.py --monitor --password admin --interval 5
```

### Connect to Remote Odoo

```bash
python migration_monitor.py --monitor \
  --url http://192.168.1.100:8069 \
  --db production_db \
  --username admin \
  --password your_password
```

## Status Colors

- 🟢 **Green**: Migrated, Already Migrated
- 🔵 **Blue**: Already Migrated
- 🟡 **Yellow**: Queued, Pending Migration
- 🔵 **Cyan**: Migrating
- 🔴 **Red**: Error, Not Found

## Output

The tool displays:
- Real-time status updates
- Status change notifications
- Summary statistics
- Detailed table with quotation numbers, status, messages, and dates

Press `Ctrl+C` to stop monitoring.
