# -*- coding: utf-8 -*-
{
    'name': "apiux_purchase",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Apiux",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','purchase','account_sector','l10n_cl_fe'],

    # always loaded
    'data': [

        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',        
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}