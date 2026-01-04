#!/bin/bash

# Vendor Bill Migration Script for Odoo 14 to Odoo 19
# This script helps with vendor bill migration tasks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ODOO_BIN="${ODOO_BIN:-odoo-bin}"
ODOO_CONFIG="${ODOO_CONFIG:-/etc/odoo/odoo.conf}"
DATABASE="${DATABASE:-odoo19}"
MODULE_NAME="odoo14_to_19_migration"

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if Odoo is installed
check_odoo() {
    print_header "Checking Odoo Installation"
    
    if command -v $ODOO_BIN &> /dev/null; then
        print_success "Odoo binary found: $(which $ODOO_BIN)"
    else
        print_error "Odoo binary not found. Please set ODOO_BIN environment variable."
        exit 1
    fi
}

# Check required modules
check_modules() {
    print_header "Checking Required Modules"
    
    local modules=("odoo14_to_19_migration" "eq_fc_purchase_custom" "eq_fc_invoice_custom" "queue_job")
    
    for module in "${modules[@]}"; do
        if odoo shell -d $DATABASE -c $ODOO_CONFIG --no-http <<EOF 2>/dev/null | grep -q "$module"; then
            print_success "Module $module is installed"
        else
            print_warning "Module $module may not be installed"
        fi
    done <<EOF
import odoo
odoo.tools.config.parse_config(['-d', '$DATABASE'])
env = odoo.api.Environment(odoo.registry($DATABASE).cursor(), 1, {})
modules = env['ir.module.module'].search([('name', 'in', ['$module']), ('state', '=', 'installed')])
for m in modules:
    print(m.name)
EOF
}

# Upgrade migration module
upgrade_module() {
    print_header "Upgrading Migration Module"
    
    print_info "Upgrading $MODULE_NAME module..."
    
    if $ODOO_BIN -d $DATABASE -c $ODOO_CONFIG -u $MODULE_NAME --stop-after-init; then
        print_success "Module upgraded successfully"
    else
        print_error "Failed to upgrade module"
        exit 1
    fi
}

# Check migration configuration
check_config() {
    print_header "Checking Migration Configuration"
    
    print_info "Checking for migration configurations in database..."
    
    # This would require a Python script to check the database
    print_warning "Please check migration configuration manually in Odoo UI"
    print_info "Go to: Odoo 14 Migration → Migration Configuration"
}

# View migration status
view_status() {
    print_header "Vendor Bill Migration Status"
    
    print_info "Checking migration status..."
    
    # Count by status
    echo ""
    echo "Migration Status Summary:"
    echo "========================"
    
    # This would require a Python script to query the database
    print_warning "Please check migration status in Odoo UI"
    print_info "Go to: Odoo 14 Migration → Vendors → Vendor Bills"
}

# Process queue jobs
process_queue() {
    print_header "Processing Queue Jobs"
    
    print_info "Starting queue job processor..."
    
    # Start queue job processor in background
    print_info "Queue jobs will be processed automatically by Odoo cron"
    print_info "Or use: odoo shell -d $DATABASE -c $ODOO_CONFIG"
    print_info "Then run: env['queue.job'].process_jobs()"
}

# View logs
view_logs() {
    print_header "Viewing Migration Logs"
    
    local log_file="logs/failed_vendor_bill_migrations.log"
    
    if [ -f "$log_file" ]; then
        print_info "Failed migrations log:"
        echo ""
        tail -n 50 "$log_file"
    else
        print_warning "No failed migrations log found"
    fi
}

# Test connection to Odoo 14
test_connection() {
    print_header "Testing Odoo 14 Connection"
    
    print_info "This requires a Python script to test XML-RPC connection"
    print_warning "Please test connection in Odoo UI:"
    print_info "Go to: Odoo 14 Migration → Migration Configuration → Test Connection"
}

# Main menu
show_menu() {
    echo ""
    print_header "Vendor Bill Migration Tool"
    echo ""
    echo "1. Check Odoo Installation"
    echo "2. Check Required Modules"
    echo "3. Upgrade Migration Module"
    echo "4. Check Migration Configuration"
    echo "5. View Migration Status"
    echo "6. Process Queue Jobs"
    echo "7. View Migration Logs"
    echo "8. Test Odoo 14 Connection"
    echo "9. Run All Checks"
    echo "0. Exit"
    echo ""
    read -p "Select an option: " choice
    
    case $choice in
        1) check_odoo ;;
        2) check_modules ;;
        3) upgrade_module ;;
        4) check_config ;;
        5) view_status ;;
        6) process_queue ;;
        7) view_logs ;;
        8) test_connection ;;
        9) 
            check_odoo
            check_modules
            check_config
            view_status
            ;;
        0) 
            print_info "Exiting..."
            exit 0
            ;;
        *) 
            print_error "Invalid option"
            show_menu
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    show_menu
}

# Help function
show_help() {
    echo "Vendor Bill Migration Script"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -u, --upgrade       Upgrade migration module"
    echo "  -c, --check         Check installation and modules"
    echo "  -s, --status        View migration status"
    echo "  -l, --logs          View migration logs"
    echo "  -m, --menu          Show interactive menu (default)"
    echo ""
    echo "Environment Variables:"
    echo "  ODOO_BIN            Path to odoo-bin (default: odoo-bin)"
    echo "  ODOO_CONFIG         Path to Odoo config file (default: /etc/odoo/odoo.conf)"
    echo "  DATABASE            Database name (default: odoo19)"
    echo ""
    echo "Examples:"
    echo "  $0 --upgrade        # Upgrade migration module"
    echo "  $0 --check          # Check installation"
    echo "  $0 --status         # View migration status"
    echo ""
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    show_menu
else
    case $1 in
        -h|--help)
            show_help
            ;;
        -u|--upgrade)
            upgrade_module
            ;;
        -c|--check)
            check_odoo
            check_modules
            ;;
        -s|--status)
            view_status
            ;;
        -l|--logs)
            view_logs
            ;;
        -m|--menu)
            show_menu
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
fi

