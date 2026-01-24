# -*- coding: utf-8 -*-
#############################################################################
#
#    Equdai
#
#    Copyright (C) 2024-TODAY Equdai(<https://equdai.ae>).
#    Author: Equdai (<https://equdai.ae>)
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
    'name': "Equdai Custom Task Template",
    'version': '19.0.1.0.0',
    'category': 'Project',
    'summary': """This module helps to apply task template on project""",
    'description': """This module helps to apply task template on project.""",
    'author': 'Equdai',
    'company': 'Equdai',
    'maintainer': 'Equdai',
    'website': "https://equdai.ae",
    'depends': ['project', 'social'],
    'data': [
        'data/holiday_day_data.xml',
        'security/roles_groups.xml',
        'security/ir.model.access.csv',
        'wizard/project_subtask_wizard.xml',
        'views/task_roles_view.xml',
        'views/task_template_group_view.xml',
        'views/task_template_subgroup_view.xml',
        'views/platform_view.xml',
        'views/holiday_view.xml',
        'views/task_template_view.xml',
        'wizard/apply_task_template_wizard_view.xml',
        'views/project_custom_view.xml',
        'views/project_task_view.xml',
        'views/social_post_view.xml',
        'views/project_type_view.xml',
        'views/content_type_view.xml',
        'views/content_pillar_view.xml',
        'views/project_view.xml',
    ],
    'license': "AGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
}
