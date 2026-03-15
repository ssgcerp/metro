"""
fix_bill_accounts.py
=====================
Fixes two issues on Odoo 18 → Odoo 19 migrated vendor bills:
  1. Invoice line accounts are wrong (e.g. 400001 Cost of Goods Sold in Trading) instead of
     the correct Odoo 18 account (e.g. 101010 PDC Cheque Paid).
  2. Missing analytic_distribution on invoice lines.

Matching strategy:
  - Match bills by name (e.g. EXP/2025/10/0259) between Odoo 18 and Odoo 19.
  - Only processes bills where name != False (i.e. skips draft bills).

In both Odoo 18 and Odoo 19, invoice product lines have display_type='product'.
Lines are matched by position (index order). Bills with different line counts are skipped.

Usage:
    python fix_bill_accounts.py [--dry-run] [--bill BILL_NUMBER] [--limit N]

Options:
    --dry-run          Preview changes only, do NOT write to Odoo 19
    --bill             Fix only this specific bill number
    --limit N          Stop after N Odoo 19 bills processed (default: all)
    --skip-analytics   Skip fixing analytic_distribution
    --skip-accounts    Skip fixing account_id
"""

import xmlrpc.client
import argparse
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Odoo 18 (Source) ─────────────────────────────────
SRC_URL  = "https://metro-fire-system-llc.odoo.com"
SRC_DB   = "metro-fire-system-llc"
SRC_USER = "sruthi@metrofiresystems.com"
SRC_PASS = "Sruthi@321"

# ── Odoo 19 (Destination) ─────────────────────────────
DST_URL  = "https://metro.equdaierp.com"
DST_DB   = "newdb"
DST_USER = "admin"
DST_PASS = "Amaze@321"


def connect(url, db, user, password):
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
    uid = common.authenticate(db, user, password, {})
    if not uid:
        raise ConnectionError(f"Authentication failed for {url} with user {user}")
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
    return uid, models


def sr(models, db, uid, pw, model, domain, fields, limit=0, order=None):
    """Shorthand search_read."""
    kw = {"fields": fields}
    if limit:
        kw["limit"] = limit
    if order:
        kw["order"] = order
    return models.execute_kw(db, uid, pw, model, "search_read", [domain], kw)


def get_product_lines(models, db, uid, pw, move_id):
    """Return only product invoice lines (display_type='product'), ordered by sequence/id."""
    lines = sr(models, db, uid, pw,
               "account.move.line",
               [("move_id", "=", move_id), ("display_type", "=", "product")],
               ["id", "name", "account_id", "analytic_distribution",
                "product_id", "sequence"],
               order="sequence asc, id asc")
    return lines


def main():
    parser = argparse.ArgumentParser(description="Fix Odoo 18→19 migrated vendor bill accounts")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bill", type=str, help="Only fix this bill number")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip-analytics", action="store_true")
    parser.add_argument("--skip-accounts", action="store_true")
    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        logger.info("=== DRY RUN mode - no changes will be written ===")

    # ── Connect ───────────────────────────────────────────────────────────────
    logger.info("Connecting to Odoo 18 (source)...")
    src_uid, src_models = connect(SRC_URL, SRC_DB, SRC_USER, SRC_PASS)
    logger.info("Connected to Odoo 18 (uid=%s)", src_uid)

    logger.info("Connecting to Odoo 19 (destination)...")
    dst_uid, dst_models = connect(DST_URL, DST_DB, DST_USER, DST_PASS)
    logger.info("Connected to Odoo 19 (uid=%s)", dst_uid)

    # ── Cache: Odoo 19 accounts per (code, company_id) ───────────────────────
    logger.info("Caching Odoo 19 accounts...")
    dst_acc_raw = sr(dst_models, DST_DB, dst_uid, DST_PASS,
                     "account.account", [], ["id", "code", "name", "company_ids"])
    dst_acc_by_code_co = {}   # (code, company_id) -> account_id
    dst_acc_by_code    = {}   # code -> first account_id  (fallback)
    for a in dst_acc_raw:
        code = a["code"]
        for cid in a.get("company_ids", []):
            dst_acc_by_code_co[(code, cid)] = a["id"]
        if code not in dst_acc_by_code:
            dst_acc_by_code[code] = a["id"]
    logger.info("Cached %d Odoo 19 accounts", len(dst_acc_raw))

    # ── Cache: Odoo 18 accounts id → (code, name) ────────────────────────────
    logger.info("Caching Odoo 18 accounts...")
    src_acc_raw = sr(src_models, SRC_DB, src_uid, SRC_PASS,
                     "account.account", [], ["id", "code", "name"])
    src_acc = {a["id"]: (a["code"], a["name"]) for a in src_acc_raw}
    logger.info("Cached %d Odoo 18 accounts", len(src_acc_raw))

    # ── Cache: Odoo 18 analytic accounts id → name ───────────────────────────
    logger.info("Caching Odoo 18 analytic accounts...")
    src_aa_raw = sr(src_models, SRC_DB, src_uid, SRC_PASS,
                    "account.analytic.account", [], ["id", "name"])
    src_aa = {str(a["id"]): a["name"] for a in src_aa_raw}
    logger.info("Cached %d Odoo 18 analytic accounts", len(src_aa_raw))

    # ── Cache: Odoo 19 analytic accounts name → id ───────────────────────────
    logger.info("Caching Odoo 19 analytic accounts...")
    dst_aa_raw = sr(dst_models, DST_DB, dst_uid, DST_PASS,
                    "account.analytic.account", [], ["id", "name", "plan_id"])
    dst_aa_by_name = {a["name"]: a["id"] for a in dst_aa_raw}
    logger.info("Cached %d Odoo 19 analytic accounts", len(dst_aa_raw))

    # Default analytic plan for creating missing accounts
    dst_plans = sr(dst_models, DST_DB, dst_uid, DST_PASS,
                   "account.analytic.plan", [], ["id", "name"], limit=1)
    default_plan_id = dst_plans[0]["id"] if dst_plans else None

    # ── Fetch Odoo 19 customer invoices (with name, i.e. not draft) ───────────────
    logger.info("Fetching Odoo 19 customer invoices...")
    dst_domain = [("move_type", "=", "out_invoice"), ("name", "!=", False)]
    if args.bill:
        dst_domain.append(("name", "=", args.bill))

    dst_bills = sr(dst_models, DST_DB, dst_uid, DST_PASS,
                   "account.move", dst_domain,
                   ["id", "name", "company_id", "invoice_line_ids", "state"],
                   limit=args.limit,
                   order="id asc")
    logger.info("Found %d Odoo 19 vendor bills to process", len(dst_bills))

    # ── Stats ─────────────────────────────────────────────────────────────────
    stats = dict(total=len(dst_bills), no_src=0, no_lines=0,
                 line_mismatch=0, account_fixed=0, analytic_fixed=0,
                 bills_updated=0, errors=0)

    for idx, dst_bill in enumerate(dst_bills, 1):
        bill_name  = dst_bill["name"]
        company_id = dst_bill["company_id"][0] if isinstance(dst_bill["company_id"], list) else dst_bill["company_id"]

        if idx % 100 == 0:
            logger.info("Progress %d/%d | acc_fixes=%d analytic_fixes=%d bills=%d",
                        idx, stats["total"],
                        stats["account_fixed"], stats["analytic_fixed"], stats["bills_updated"])

        try:
            # ── Find matching invoice in Odoo 18 ─────────────────────────────────
            src_bills = sr(src_models, SRC_DB, src_uid, SRC_PASS,
                           "account.move",
                           [("name", "=", bill_name), ("move_type", "=", "out_invoice")],
                           ["id"], limit=1)
            if not src_bills:
                stats["no_src"] += 1
                logger.debug("No Odoo 18 match for %s", bill_name)
                continue

            src_move_id = src_bills[0]["id"]

            # ── Get product lines from both sides (display_type='product') ────
            src_lines = get_product_lines(src_models, SRC_DB, src_uid, SRC_PASS, src_move_id)
            dst_lines = get_product_lines(dst_models, DST_DB, dst_uid, DST_PASS, dst_bill["id"])

            if not src_lines and not dst_lines:
                stats["no_lines"] += 1
                continue

            if len(src_lines) != len(dst_lines):
                stats["line_mismatch"] += 1
                logger.debug("Line mismatch %s: src=%d dst=%d",
                             bill_name, len(src_lines), len(dst_lines))
                continue

            # ── Build per-line updates ────────────────────────────────────────
            lines_to_update = []

            for src_line, dst_line in zip(src_lines, dst_lines):
                line_update = {}

                # ── Fix account_id ────────────────────────────────────────────
                if not args.skip_accounts:
                    src_acc_raw_val = src_line.get("account_id")
                    if src_acc_raw_val:
                        src_acc_id = src_acc_raw_val[0] if isinstance(src_acc_raw_val, list) else src_acc_raw_val
                        acc_info = src_acc.get(src_acc_id)
                        if acc_info:
                            code, acc_name = acc_info
                            dst_acc_raw_val = dst_line.get("account_id")
                            dst_acc_id = dst_acc_raw_val[0] if isinstance(dst_acc_raw_val, list) else dst_acc_raw_val

                            # Prefer company-specific match, fallback to any company
                            new_acc_id = dst_acc_by_code_co.get((code, company_id),
                                         dst_acc_by_code.get(code))

                            if new_acc_id and new_acc_id != dst_acc_id:
                                line_update["account_id"] = new_acc_id
                                stats["account_fixed"] += 1
                                logger.info("  ACC %s L%s: %s→%s (%s - %s)",
                                            bill_name, dst_line["id"],
                                            dst_acc_id, new_acc_id, code, acc_name)
                            elif not new_acc_id:
                                logger.debug("  %s: code %s not found in Odoo 19", bill_name, code)

                # ── Fix analytic_distribution ─────────────────────────────────
                if not args.skip_analytics:
                    src_dist = src_line.get("analytic_distribution") or {}
                    if src_dist:
                        new_dist = {}
                        for s_id_str, pct in src_dist.items():
                            s_name = src_aa.get(str(s_id_str))
                            if not s_name:
                                continue
                            d_id = dst_aa_by_name.get(s_name)
                            if not d_id:
                                if not dry_run and default_plan_id:
                                    try:
                                        d_id = dst_models.execute_kw(
                                            DST_DB, dst_uid, DST_PASS,
                                            "account.analytic.account", "create",
                                            [{"name": s_name, "plan_id": default_plan_id}],
                                        )
                                        dst_aa_by_name[s_name] = d_id
                                        logger.info("  Created analytic: %s (ID %s)", s_name, d_id)
                                    except Exception as e:
                                        logger.warning("  Failed to create analytic %s: %s", s_name, e)
                                else:
                                    logger.debug("  [dry] Would create analytic: %s", s_name)
                            if d_id:
                                new_dist[str(d_id)] = pct

                        if new_dist:
                            cur_dist = dst_line.get("analytic_distribution") or {}
                            if new_dist != cur_dist:
                                line_update["analytic_distribution"] = new_dist
                                stats["analytic_fixed"] += 1
                                logger.info("  ANA %s L%s: %s→%s",
                                            bill_name, dst_line["id"], cur_dist, new_dist)

                if line_update:
                    lines_to_update.append((1, dst_line["id"], line_update))

            # ── Write back ────────────────────────────────────────────────────
            if lines_to_update:
                n_acc = sum(1 for _, _, u in lines_to_update if "account_id" in u)
                n_ana = sum(1 for _, _, u in lines_to_update if "analytic_distribution" in u)
                logger.info("Bill %s (ID %s): updating %d line(s) [acc=%d, analytic=%d]",
                            bill_name, dst_bill["id"], len(lines_to_update), n_acc, n_ana)

                if not dry_run:
                    was_posted = (dst_bill["state"] == "posted")
                    try:
                        if was_posted:
                            dst_models.execute_kw(DST_DB, dst_uid, DST_PASS, "account.move", "button_draft", [[dst_bill["id"]]])
                        
                        # Update each line individually
                        for _, line_id, line_vals in lines_to_update:
                            dst_models.execute_kw(DST_DB, dst_uid, DST_PASS, "account.move.line", "write", [[line_id], line_vals])
                        
                        if was_posted:
                            dst_models.execute_kw(DST_DB, dst_uid, DST_PASS, "account.move", "action_post", [[dst_bill["id"]]])
                        
                        stats["bills_updated"] += 1
                        
                    except Exception as write_err:
                        logger.error("Failed to update bill %s: %s", bill_name, write_err)
                        # Try to restore posted state if it failed
                        if was_posted:
                            try:
                                dst_models.execute_kw(DST_DB, dst_uid, DST_PASS, "account.move", "action_post", [[dst_bill["id"]]])
                            except: pass
                        stats["errors"] += 1

        except Exception as e:
            stats["errors"] += 1
            logger.error("Error on %s: %s", bill_name, e)

    # ── Summary ───────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("SUMMARY%s", " (DRY RUN)" if dry_run else "")
    logger.info("  Total Odoo 19 bills:  %d", stats["total"])
    logger.info("  No Odoo 18 match:     %d", stats["no_src"])
    logger.info("  No lines:             %d", stats["no_lines"])
    logger.info("  Line count mismatch:  %d", stats["line_mismatch"])
    logger.info("  Account fixes:        %d lines", stats["account_fixed"])
    logger.info("  Analytic fixes:       %d lines", stats["analytic_fixed"])
    logger.info("  Bills updated:        %d", stats["bills_updated"])
    logger.info("  Errors:               %d", stats["errors"])
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
