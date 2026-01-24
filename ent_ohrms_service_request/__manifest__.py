
{
    'name': "Enterprise Open HRMS Service Request",
    'version': '19.0.1.0.0',
    'category': 'Human Resource',
    'summary': """Allow Employees To Raise A Service Request""",
    'description': """Module provides employee service requests, approvers, 
    service reports""",
    'author': "Cybrosys Techno Solutions,Open HRMS",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.openhrms.com",
    'depends': ['stock', 'ent_oh_employee_creation_from_user',
                'project', 'hr_attendance', 'hr','base'],
    'data': [
            'security/ent_ohrms_service_request_security.xml',
            'security/ir.model.access.csv',
            'data/ir_sequence_data.xml',
            'views/service_request_views.xml',
            'views/service_execution_views.xml',
            ],
    'images': ['static/description/banner.jpg'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': True,
    'application': True,
}

