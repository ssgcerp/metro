# -*- coding: utf-8 -*-
# Copyright 2024 Jupetern

from odoo import fields, models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    ps_data = fields.Json()
    ps_start_xmlid = fields.Char()
    ps_menu_orders = fields.Json()
    ps_fav_menus = fields.Json()
    ps_auto_hmenu = fields.Boolean()

    up_bookmarks = fields.Json(readonly=True)
