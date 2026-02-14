from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class PortalPartnerStatement(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'statement_count' in counters:
            values['statement_count'] = 1 # Just a static entry point
        return values

    @http.route(['/my/statement'], type='http', auth="user", website=True)
    def portal_my_statement(self, date_from=None, date_to=None, **kw):
        partner = request.env.user.partner_id
        
        # Default dates
        if not date_to:
            date_to = fields.Date.today()
        else:
            date_to = fields.Date.from_string(date_to)
            
        if not date_from:
            date_from = date_to.replace(day=1)
        else:
            date_from = fields.Date.from_string(date_from)

        values = {
            'date_from': date_from,
            'date_to': date_to,
            'partner': partner,
        }
        return request.render("partner_statement_soa.portal_my_statement", values)

    @http.route(['/my/statement/download'], type='http', auth="user", website=True)
    def portal_download_statement(self, date_from, date_to, **kw):
        partner = request.env.user.partner_id
        
        # Create wizard in context of the user (who is a portal user, might have restriction?)
        # Portal users usually cannot create transient models or read account.move.line directly if record rules block it.
        # We need to sudo() or ensure rights.
        # But report generation needs to be done.
        
        wizard = request.env['partner.statement.wizard'].sudo().create({
            'partner_ids': [(6, 0, [partner.id])],
            'company_id': request.env.company.id,
            'date_from': date_from,
            'date_to': date_to,
            'target_move': 'posted',
            'account_type': 'both', # Portal view usually shows everything
            'show_aging': True,
            'show_running_balance': True,
        })
        
        # Determine format
        return self._show_report(model=wizard, report_type='pdf', report_ref='partner_statement_soa.action_report_partner_statement', download=True)

