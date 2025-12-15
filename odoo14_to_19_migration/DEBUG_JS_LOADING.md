# Debug: JavaScript Not Loading

## Steps to Fix:

### 1. **VERIFY MODULE NAME MATCHES**
Check that the module directory name is exactly: `odoo14_to_19_migration`
- The path in manifest must match the directory name exactly
- Current path: `odoo14_to_19_migration/static/src/js/migration_auto_continue.js`

### 2. **UPGRADE MODULE (CRITICAL!)**
```
1. Go to Apps menu
2. Remove "Apps" filter (show all modules)
3. Search: "Odoo 14 to Odoo 19"
4. Click "Upgrade" button
5. Wait for upgrade to complete
```

### 3. **RESTART ODOO SERVER**
- Stop Odoo completely
- Start Odoo again
- This clears asset cache

### 4. **CLEAR BROWSER CACHE**
- Press `Ctrl + Shift + Delete`
- Select "Cached images and files"
- Click "Clear data"
- Or use `Ctrl + F5` for hard refresh

### 5. **CHECK BROWSER CONSOLE**
Open DevTools (F12) → Console tab:
- Look for: `🚀 migration_auto_continue.js LOADED!`
- If you DON'T see this, the file is NOT loading
- Check for any red errors

### 6. **VERIFY FILE EXISTS**
Check that file exists at:
```
e:\odoo modules\19\metro\odoo14_to_19_migration\static\src\js\migration_auto_continue.js
```

### 7. **CHECK ODOO LOGS**
Look in Odoo server logs for:
- Asset compilation errors
- JavaScript syntax errors
- Module loading errors

### 8. **ALTERNATIVE: Check if bundled**
In browser DevTools → Network tab:
- Click on `web.assets_web.min.js`
- Go to "Response" tab
- Press `Ctrl + F` and search for: "migration_auto_continue"
- If found, JavaScript IS bundled (even if not showing separately)

## If Still Not Working:

Try this test - create a simple JavaScript file to verify assets work:

1. Create: `static/src/js/test.js`
```javascript
/** @odoo-module **/
console.log("TEST JS LOADED!");
```

2. Add to manifest:
```python
'assets': {
    'web.assets_backend': [
        'odoo14_to_19_migration/static/src/js/test.js',
    ],
},
```

3. Upgrade module and check console for "TEST JS LOADED!"

If test.js loads but migration_auto_continue.js doesn't, there's a syntax error in migration_auto_continue.js

