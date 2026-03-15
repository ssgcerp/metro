
import xmlrpc.client
import argparse
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_odoo14_credentials(url, db, username, password):
    """Fetch Odoo 14 credentials from Odoo 19 odoo14.migration.config model"""
    try:
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            logger.error("Authentication failed for Odoo 19")
            return None

        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        # Search for migration config
        config_ids = models.execute_kw(db, uid, password,
            'odoo14.migration.config', 'search', [[]], {'limit': 1})
            
        if not config_ids:
            logger.error("No Odoo 14 migration configuration found in Odoo 19")
            return None
            
        config = models.execute_kw(db, uid, password,
            'odoo14.migration.config', 'read', [config_ids], 
            {'fields': ['odoo14_url', 'odoo14_database', 'odoo14_username', 'odoo14_password']})
            
        if config:
            return config[0]
        return None

    except Exception as e:
        logger.error(f"Error fetching credentials: {str(e)}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get Odoo 14 Credentials from Odoo 19')
    parser.add_argument('--url', default='https://metro.equdaierp.com', help='Odoo 19 URL')
    parser.add_argument('--db', default='metrodb', help='Odoo 19 DB')
    parser.add_argument('--user', default='admin', help='Odoo 19 User')
    parser.add_argument('--password', default='Amaze@321', help='Odoo 19 Password')
    
    args = parser.parse_args()
    
    creds = get_odoo14_credentials(args.url, args.db, args.user, args.password)
    
    if creds:
        print("\n--- Odoo 14 Credentials Found ---")
        print(f"URL: {creds.get('odoo14_url')}")
        print(f"DB: {creds.get('odoo14_database')}")
        print(f"User: {creds.get('odoo14_username')}")
        print(f"Password: {creds.get('odoo14_password')}")
        print("---------------------------------")
    else:
        print("Failed to retrieve credentials.")
