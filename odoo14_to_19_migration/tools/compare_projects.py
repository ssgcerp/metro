import xmlrpc.client
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def main():
    # ── Odoo 14 (Source) ─────────────────────────────────
    src_url  = "https://metro.equdaierp.com"
    src_db   = "metrodb"
    src_user = "admin"
    src_pass = "Amaze@321"

    # ── Odoo 19 (Destination) ─────────────────────────────
    dst_url  = "https://metro.equdaierp.com"
    dst_db   = "newdb"
    dst_user = "admin"
    dst_pass = "Amaze@321"

    # Connect to Odoo 14
    logger.info("Connecting to Odoo 14...")
    s_common = xmlrpc.client.ServerProxy(f"{src_url}/xmlrpc/2/common", allow_none=True)
    s_uid = s_common.authenticate(src_db, src_user, src_pass, {})
    s_models = xmlrpc.client.ServerProxy(f"{src_url}/xmlrpc/2/object", allow_none=True)

    # Connect to Odoo 19
    logger.info("Connecting to Odoo 19...")
    d_common = xmlrpc.client.ServerProxy(f"{dst_url}/xmlrpc/2/common", allow_none=True)
    d_uid = d_common.authenticate(dst_db, dst_user, dst_pass, {})
    d_models = xmlrpc.client.ServerProxy(f"{dst_url}/xmlrpc/2/object", allow_none=True)

    # Fetch Odoo 14 Projects
    logger.info("Fetching projects from Odoo 14...")
    s_projects = s_models.execute_kw(src_db, s_uid, src_pass, 'project.project', 'search_read', [[]], {'fields': ['id', 'name']})
    logger.info(f"Odoo 14 total projects: {len(s_projects)}")

    # Fetch Odoo 19 Projects
    logger.info("Fetching projects from Odoo 19...")
    d_projects = d_models.execute_kw(dst_db, d_uid, dst_pass, 'project.project', 'search_read', [[]], {'fields': ['id', 'name']})
    logger.info(f"Odoo 19 total projects: {len(d_projects)}")

    # Create sets for comparison based on project names
    # Note: strip spaces and make lower case for better matching
    s_project_names = {p['name'].strip() for p in s_projects if p.get('name')}
    d_project_names = {p['name'].strip() for p in d_projects if p.get('name')}

    missing_in_19 = s_project_names - d_project_names
    
    logger.info("-" * 40)
    logger.info(f"Missing Projects in Odoo 19 (Count: {len(missing_in_19)}):")
    logger.info("-" * 40)
    
    for name in sorted(missing_in_19):
        logger.info(f" - {name}")

    logger.info("-" * 40)

if __name__ == "__main__":
    main()
