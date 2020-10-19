# -*- coding: utf-8 -*-
{
    'name': "project_analytic",

    'summary': """Project Analytic additions""",

    'description': """
        Project Analytic Addons
    """,

    'author': "Apiux",
    'website': "http://www.api-ux.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Project',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr_timesheet','apiux_project'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/project_analytic_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}