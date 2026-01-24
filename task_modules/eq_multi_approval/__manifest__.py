# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Jumana Haseen (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': "Equdai Multi Level Approval",
    'version': '19.0.1.0.0',
    'category': 'Project',
    'summary': """This module add the multiple approval option for project BOQ,
     and Material requisition.""",
    'description': """This module add the multiple approval option for BOQ and Material requisition.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['project','pragtech_ppc','pragtech_purchase'],
    'data': [
        'security/project_multi_approval_groups.xml',
        'security/ir.model.access.csv',
        'data/project_approval_data.xml',
        'views/project_approval_views.xml',
        'views/stage_view.xml',
        'views/purchase_requisition_form_view.xml',
        'views/res_partner_views.xml',
        'data/stage_master_data.xml',
        'data/project_stage_data.xml',
        'wizard/stage_transaction_wizard.xml',
        'wizard/purchase_requisition_approval_wizard_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': "AGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
}
