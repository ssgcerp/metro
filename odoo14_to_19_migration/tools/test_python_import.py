#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify Python imports work correctly
Run this to check if there are any import errors before restarting Odoo
"""

import sys
import os

# Add the module path (parent of odoo14_to_19_migration)
tools_path = os.path.dirname(os.path.abspath(__file__))
module_path = os.path.dirname(tools_path)  # odoo14_to_19_migration
parent_path = os.path.dirname(module_path)  # metro (parent directory)
if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

print("=" * 60)
print("Testing Python Imports for odoo14_to_19_migration")
print("=" * 60)
print()

errors = []

# Test 1: Import controller
print("1. Testing migration_cron_controller import...")
try:
    from odoo14_to_19_migration.controllers import migration_cron_controller
    print("   [OK] migration_cron_controller imported successfully")
except Exception as e:
    print(f"   [ERROR] ERROR importing migration_cron_controller: {e}")
    errors.append(f"migration_cron_controller: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 2: Check for syntax errors
print("2. Testing syntax compilation...")
try:
    import py_compile
    controller_file = os.path.join(module_path, 'controllers', 'migration_cron_controller.py')
    
    py_compile.compile(controller_file, doraise=True)
    print("   [OK] migration_cron_controller.py compiles successfully")
except py_compile.PyCompileError as e:
    print(f"   [ERROR] Syntax error found: {e}")
    errors.append(f"Syntax error: {e}")
except Exception as e:
    print(f"   [ERROR] ERROR during compilation: {e}")
    errors.append(f"Compilation error: {e}")

print()

# Summary
print("=" * 60)
if errors:
    print("[ERROR] ERRORS FOUND:")
    for error in errors:
        print(f"   - {error}")
    print()
    print("Fix these errors before restarting Odoo!")
    sys.exit(1)
else:
    print("[OK] All imports and syntax checks passed!")
    print()
    print("If controllers still return 404, try:")
    print("  1. FULLY restart Odoo server")
    print("  2. Upgrade the module: Apps > odoo14_to_19_migration > Upgrade")
    print("  3. Check Odoo server logs for runtime errors")
print("=" * 60)

