# Migration Progress Update Guide

## ✅ Changes Made for Real-Time Progress Display

### 1. Added Progress Fields
- `quotations_progress` - Computed field showing percentage (0-100%)
- `migration_status` - Text field showing current migration status
- `is_migrating` - Boolean flag indicating if migration is in progress

### 2. Updated Migration Method
- **Count updates after EVERY record** - `quotations_migrated` increments after each successful migration
- **Status updates** - Shows current progress like "Migrating quotations... (150/7184) - 2.1%"
- **Progress percentage** - Automatically calculated based on migrated/total count

### 3. Enhanced View
- **Progress bar widget** - Visual progress bar showing percentage
- **Status message** - Shows current migration status
- **Refresh button** - Appears when migration is in progress
- **Visual indicators** - Migrated count highlighted, spinner when migrating

### 4. Auto-Refresh JavaScript
- **Auto-refreshes view every 2 seconds** when `is_migrating = True`
- Automatically stops when migration completes
- Uses Odoo 19's OWL framework

---

## How It Works

### When You Click "Migrate":

1. **Migration starts**:
   - `is_migrating` = True
   - `quotations_migrated` = 0
   - Status: "Starting migration..."

2. **During migration**:
   - After **each record**, the count updates:
     - `quotations_migrated` increments
     - `quotations_progress` recalculates
     - `migration_status` updates with current progress
   - JavaScript **auto-refreshes the view every 2 seconds**
   - You'll see the count increasing in real-time

3. **Migration completes**:
   - `is_migrating` = False
   - Final count displayed
   - Success notification shown

---

## What You'll See

### In the UI:
- **Migrated Count**: Increases from 0 → 1 → 2 → ... → 7184
- **Progress Bar**: Fills from 0% → 100%
- **Status Message**: Updates like "Migrating quotations... (150/7184) - 2.1%"
- **Spinner**: Shows "Migration in progress..." message

### In the Logs:
- Progress logged after each record
- Checkpoint logs every 100 records

---

## Manual Refresh Option

If auto-refresh doesn't work, you can:
1. Click the **"Refresh"** button (appears when migration is in progress)
2. Or manually refresh the browser page
3. The count will show the current progress

---

## Troubleshooting

### If count doesn't update:
1. **Check browser console** for JavaScript errors
2. **Manually refresh** the view using Refresh button
3. **Check logs** to verify migration is running
4. **Restart Odoo** if JavaScript changes don't load

### If migration seems stuck:
1. Check the **status message** - it shows current progress
2. Check **server logs** - they show detailed progress
3. The migration continues even if UI doesn't refresh

---

## Technical Details

### Database Updates:
- `quotations_migrated` field updated after **every record**
- Committed to database immediately
- Visible when view refreshes

### JavaScript Auto-Refresh:
- Checks `is_migrating` field every 2 seconds
- Reloads the form view when migration is active
- Stops automatically when migration completes

### Progress Calculation:
```python
progress_percent = (quotations_migrated / quotations_count) * 100
```

---

## Expected Behavior

✅ **Count increases** after each record  
✅ **Progress bar fills** as migration progresses  
✅ **Status updates** with current progress  
✅ **View auto-refreshes** every 2 seconds  
✅ **Completion notification** when done  

---

## Notes

- Migration runs **synchronously** - the UI may freeze during migration
- **Auto-refresh** helps show progress without manual refresh
- **Count updates** happen in database, visible on refresh
- For **very large migrations** (7000+ records), consider running in batches
