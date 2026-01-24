# -*- coding: utf-8 -*-
# Copyright 2024 Jupetern

import re

from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def load_web_menus(self, debug):
        menus = super(IrUiMenu, self).load_web_menus(debug)

        for menu in menus.values():
            if menu['id'] == menu['appID']:
                webIcon = menu.get('webIcon', '')
                webIconlist = webIcon and webIcon.split(',')
                iconClass = color = backgroundColor = None
                if webIconlist:
                    if len(webIconlist) >= 2:
                        iconClass, color = webIconlist[:2]
                    if len(webIconlist) == 3:
                        backgroundColor = webIconlist[2]

                if menu.get('webIconData'):
                    # Handle both bytes and string data for compatibility
                    web_icon_data = menu['webIconData']
                    if isinstance(web_icon_data, bytes):
                        web_icon_data = web_icon_data.decode('utf-8')
                    
                    menu['webIconData'] = re.sub(
                        r'\s/g',
                        '',
                        (
                            'data:%s;base64,%s'
                            % (menu['webIconDataMimetype'], web_icon_data)
                        ),
                    )
                elif backgroundColor is not None:  # Could split in three parts?
                    menu['webIcon'] = ','.join([iconClass or '', color or '', backgroundColor])
                else:
                    menu['webIconData'] = '/equdai_theme/static/img/default_icon_app.png'

        return menus
