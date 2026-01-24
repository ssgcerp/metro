# -*- coding: utf-8 -*-
{
    'name': "Equdai Productivity & Tracking",
    'summary': "Advanced Task Tracking, Blocker Management, and Gamification",
    'description': """
        Enhances Project Management with:
        - Blocker Management: Flag tasks as blocked (Client, Manager, Tech) with alerts.
        - Workload Analysis: Capacity planning and utilization dashboards.
        - Gamification: Linked goals for task completion and GMB performance.
    """,
    'author': "Equdai",
    'website': "https://equdai.ae",
    'category': 'Project',
    'version': '19.0.1.0.0',
    'depends': ['project', 'hr_timesheet', 'gamification', 'equdai_gmb'],
    'data': [
        'views/project_task_views.xml',
        'views/workload_dashboard_views.xml',
        'data/ir_cron_data.xml',
        'data/gamification_data.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
