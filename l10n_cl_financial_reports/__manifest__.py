# -*- coding: utf-8 -*-
{
    'name': "l10n_cl_financial_reports",

    'summary': """
        Reportes legales solicitados por SII 
        """,

    'description': """
        Reportes Legales SII
    """,

    'author': "Andrew Copley",
    'website': "http://www.opensolve.org",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account_sector'],

    # always loaded
    'data': [
        'views/libro_ventas_view.xml',
        'views/libro_compra_view.xml',
        'views/libro_honorarios_view.xml',
        'views/balance_tabular_view.xml',
        'views/estado_resultado_view.xml',
    ],
}