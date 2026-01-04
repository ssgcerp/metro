# Equdai Cheque Management Module

## Overview

Enterprise-grade cheque management system for Odoo 19 supporting full cheque lifecycle management with CDC (Current Date Cheque) and PDC (Post Dated Cheque) types, UAE/GCC compliant accounting, queue-based auto-deposit, and AMC/Contract integration.

## Features

### Core Features
- ✅ Incoming & Outgoing Cheque Management
- ✅ CDC (Current Date Cheque) & PDC (Post Dated Cheque) Support
- ✅ Complete Workflow: Draft → Registered → Deposited → Done
- ✅ Bounce & Return Handling with Accounting Reversal
- ✅ UAE/GCC Compliant Chart of Accounts
- ✅ Queue-based Auto-Deposit for PDC Cheques
- ✅ AMC/Contract Integration
- ✅ Multi-company Safe
- ✅ Fully Uninstallable

### Accounting Integration
- ✅ Automatic Journal Entry Creation
- ✅ PDC Receivable/Payable Accounts
- ✅ PDC Clearing Account
- ✅ Bounce Charges Account
- ✅ Complete Audit Trail
- ✅ Journal Entry Reversal Support

### Queue Job System
- ✅ Daily Cron Job for PDC Auto-Deposit
- ✅ Background Processing via queue_job
- ✅ Automatic Deposit on Cheque Date

### AMC/Contract Integration
- ✅ Link Cheques to AMC Contracts
- ✅ Track PDC Amounts per Contract
- ✅ Smart Buttons on Contract Form
- ✅ PDC Amount Calculations

## Installation

1. Copy the `eq_cheque_management` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the module from Apps menu

## Dependencies

- account
- account_accountant
- base
- mail
- queue_job
- amc_contracts

## Configuration

### Initial Setup

1. Go to **Accounting → Configuration → Cheque Management → Cheque Configuration**
2. Configure PDC Accounts:
   - PDC Receivable Account (Other Current Asset)
   - PDC Payable Account (Other Current Liability)
   - PDC Clearing Account (Other Current Asset)
   - Bounce Charges Account (Income/Expense)

3. Set Default Journals:
   - Default Incoming Journal (Bank)
   - Default Outgoing Journal (Bank)

4. Configure Sequences:
   - Incoming Sequence (default: IN-YYYY/0001)
   - Outgoing Sequence (default: OUT-YYYY/0001)

5. Settings:
   - Allow Cancel Journal Entries (for returned cheques)

### Journal Setup

Enable cheque payment methods on bank journals:
1. Go to **Accounting → Configuration → Journals**
2. Open a Bank Journal
3. Enable "Allow Cheque" checkbox

## Usage

### Creating an Incoming Cheque

1. Go to **Accounting → Cheque Management → Incoming Cheques**
2. Click **New**
3. Fill in:
   - Cheque Number (physical cheque number)
   - Cheque Type (CDC or PDC)
   - Payee (Partner)
   - Amount
   - Cheque Date
   - Cheque Received Date
   - Journal (Bank)
   - Debit Account
   - Optional: Link to AMC Contract

4. Click **Register** to create journal entry

### Workflow States

- **Draft**: Initial state, no journal entry
- **Registered**: Journal entry created (PDC Receivable/Clearing ← Partner Receivable/Payable)
- **Deposited**: Moved to bank account (Bank ← PDC Receivable/Clearing)
- **Done**: Cleared and finalized
- **Bounced**: Reversed journal entry
- **Returned**: Cancelled or reversed journal entry
- **Cancelled**: Cancelled before registration

### Auto-Deposit (PDC)

PDC cheques are automatically deposited on their cheque date via queue jobs:
- Cron runs daily
- Finds registered PDC cheques with cheque_date <= today
- Enqueues deposit jobs
- Processes in background

### AMC/Contract Integration

1. Create or open an AMC Contract
2. Link cheques via the contract_id field
3. View PDC statistics via smart buttons:
   - Total Incoming/Outgoing PDC Amount
   - Pending/Cleared/Bounced amounts
   - Cheque counts

## Security

- **Account Manager**: Full access (create, read, write, delete)
- **Account User**: Read + Create access
- **Multi-company**: Automatic company filtering

## Technical Details

### Models

- `eq.cheque.incoming`: Incoming cheque model
- `eq.cheque.outgoing`: Outgoing cheque model
- `eq.cheque.config`: Configuration model (per company)
- `eq.cheque.cron`: Cron job model

### Accounting Flow

**Incoming PDC - Registered:**
- DR: PDC Receivable
- CR: Customer Receivable

**Incoming PDC - Deposited:**
- DR: Bank
- CR: PDC Receivable

**Outgoing PDC - Registered:**
- DR: Vendor Payable
- CR: PDC Payable

**Outgoing PDC - Deposited:**
- DR: PDC Payable
- CR: Bank

### Sequence Format

- Incoming: `IN-YYYY/0001`
- Outgoing: `OUT-YYYY/0001`

## Notes

- Cheque numbers must be unique per company
- Only Bank journals are allowed
- Amount must be greater than zero
- Cannot deposit before registration
- Cannot bounce after done state
- Journal entries can be cancelled only if allowed in configuration

## Support

For issues or questions, contact Equdai support.

