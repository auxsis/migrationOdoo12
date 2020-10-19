# -*- coding: utf-8 -*-
{
    'name': "apiux_project",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account_sector','sale','project','account_cost_center','apiux_res_partner','account_pre_invoice'],

    # always loaded
    'data': [
        'views/sale_order_view.xml',
        'views/sale_order_service_type.xml', 
        'views/project_task_activity_type.xml', 
        'views/project_pre_invoice_account_view.xml',         
        'views/sale_order_wizard_view.xml', 
        'views/crm_note_view.xml',
        'views/project_view.xml', 
        'views/project_outsourcing.xml', 
        'views/res_config_settings_views.xml',
        'data/uom_uom_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}