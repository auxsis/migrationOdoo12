# -*- coding: utf-8 -*-
{
    'name': "project_extra",
    'summary': """
       extras para project, hr_timesheet y pad_project
    """,
    'description': """
       extras para project, hr_timesheet y pad_project
    """,
    'author': "José contreras",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': [
        'project',
        'hr_timesheet',
        'pad_project',
    ],
    # always loaded
    'data': [
        'views/project_views.xml',
        'views/res_config_settings_views.xml',
        'security/ir.model.access.csv',
        'security/project_security.xml',
    ],
    'installable': True,


}
