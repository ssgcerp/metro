# -*- coding: utf-8 -*-
# Copyright 2024 Jupetern

from odoo import models, _


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()

        if result.get('is_internal_user', False):
            result['udoo_presets'] = result.get('udoo_presets', [])
            result['udoo_presets'].extend(
                [
                    self._default_udoo_preset(),
                    {'code': '', 'title': _('Default'), 'color': '#05869C'},
                    {'code': 'magenta', 'title': _('Magenta'), 'color': '#714B67'},
                    {'code': 'rose', 'title': _('Rose'), 'color': '#b25968'},
                    {'code': 'lime', 'title': _('Lime'), 'color': '#66954f'},
                    {'code': 'green', 'title': _('Green'), 'color': '#19876a'},
                    {'code': 'emerald', 'title': _('Emerald'), 'color': '#0E837C'},
                    {'code': 'dodger', 'title': _('Dodger'), 'color': '#2383af'},
                    {'code': 'sky', 'title': _('Sky'), 'color': '#1e93c9'},
                    {'code': 'indigo', 'title': _('Indigo'), 'color': '#665f99'},
                    {'code': 'pink', 'title': _('Pink'), 'color': '#b16080'},
                    {'code': 'orange', 'title': _('Orange'), 'color': '#ae6464'},
                    {'code': 'yellow', 'title': _('Yellow'), 'color': '#a98357'},
                ]
            )
        return result

    def _default_udoo_preset(self):
        return {
            'code': '',
            'title': _('Slate'),
            'subtitle': _('Seriousness and freshness, creating a refined, modern space'),
            'creator': 'Udoo',
            'scheme': {
                '#05869c': _('Primary'),
                '#28979b': _('Action'),
                '#0f172a': _('Gray 900'),
                '#1e293b': _('Gray 800'),
                '#334155': _('Gray 700'),
                '#475569': _('Gray 600'),
                '#64748b': _('Gray 500'),
                '#94a3b8': _('Gray 400'),
                '#cbd5e1': _('Gray 300'),
                '#e2e8f0': _('Gray 200'),
                '#f1f5f9': _('Gray 100'),
            },
        }
