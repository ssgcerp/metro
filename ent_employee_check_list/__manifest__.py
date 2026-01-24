# -*- coding: utf-8 -*-
######################################################################################
#
#    A part of EQHRMS Project <https://www.equdai.ae>
#
#    Copyright (C) 2022-TODAY Equdai(<https://www.equdai.ae>).
#    Author: Equdai Software Solutions (odoo@equdai.ae)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
########################################################################################
{
    'name': 'Enterprise EQHRMS Employee Checklist',
    'version': '19.0.1.0.0',
    'summary': """Manages Employee's Entry & Exit Process""",
    'description': """This module is used to remembering the employee's entry and exit progress.""",
    'category': 'Generic Modules/Human Resources',
    'author': 'Equdai Software Solutions, EQHRMS',
    'company': 'Equdai Software Solutions',
    'maintainer': 'Equdai Software Solutions',
    'website': "https://www.equdai.ae",
    'depends': ['ent_employee_documents_expiry', 'mail', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/checklist_views.xml',
        'views/employee_check_list_views.xml',
        'views/hr_employee_views.xml',
        'views/mail_activity_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
}

