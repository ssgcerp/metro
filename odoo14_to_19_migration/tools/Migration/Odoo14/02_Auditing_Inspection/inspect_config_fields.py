
import xmlrpc.client
import logging

URL_19 = "https://metro.equdaierp.com"
DB_19 = "metrodb"
USER_19 = "admin"
PASS_19 = "Amaze@321"

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def inspect_fields():
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL_19))
    uid = common.authenticate(DB_19, USER_19, PASS_19, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL_19))
    
    fields = models.execute_kw(DB_19, uid, PASS_19, 'odoo14.migration.config', 'fields_get', [], {'attributes': ['string', 'type']})
    for f, v in fields.items():
        logger.info(f"{f}: {v['type']}")

if __name__ == "__main__":
    inspect_fields()
