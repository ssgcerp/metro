# -*- coding: utf-8 -*-

from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # valid instructions: Adding these fields to satisfy a broken view or legacy module requirement
    google_client_id = fields.Char(string='Google Client ID', config_parameter='equdai_gmb.google_client_id')
    google_client_secret = fields.Char(string='Google Client Secret', config_parameter='equdai_gmb.google_client_secret')
    google_redirect_uri = fields.Char(string='Google Redirect URI', config_parameter='equdai_gmb.google_redirect_uri')
    google_app_id = fields.Char(string='Google App ID', config_parameter='equdai_gmb.google_app_id')
