@echo off
echo Starting script execution... > "e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Migration\fix_mysore_taxes.log"
echo Python Path: "C:\Program Files\Odoo 19\python\python.exe" >> "e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Migration\fix_mysore_taxes.log"
echo Odoo Bin Path: "C:\Program Files\Odoo 19\server\odoo-bin" >> "e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Migration\fix_mysore_taxes.log"
echo Conf Path: "C:\Program Files\Odoo 19\server\odoo.conf" >> "e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Migration\fix_mysore_taxes.log"
echo DB: metro >> "e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Migration\fix_mysore_taxes.log"

"C:\Program Files\Odoo 19\python\python.exe" "C:\Program Files\Odoo 19\server\odoo-bin" shell -c "C:\Program Files\Odoo 19\server\odoo.conf" -d metrodb < "e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Migration\fix_mysore_invoices_v2.py" >> "e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Migration\fix_mysore_taxes.log" 2>&1

if %errorlevel% neq 0 (
    echo Command failed with error code %errorlevel% >> "e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Migration\fix_mysore_taxes.log"
) else (
    echo Command completed successfully >> "e:\odoo modules\19\metro\odoo14_to_19_migration\tools\Migration\fix_mysore_taxes.log"
)
