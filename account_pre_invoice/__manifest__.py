# -*- coding: utf-8 -*-
# Copyright 2016-2019 Apiux (<http://www.api-ux.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Account Pre Invoice',
    'summary': 'Account Pre Invoice',
    'author': 'Apiux',
    'license': 'AGPL-3',
    'website': 'https://github.com/OCA/account-financial-tools/',
    'category': 'Accounting',
    'version': '12.0.1.0.0',
    'depends': [
        'account',
        'account_sector',
        'account_cost_center',
        'l10n_cl_fe',
    ],
    'data': [
        'views/account_pre_invoice_view.xml', 
        'views/account_invoice_view.xml',         
    ],
    'installable': True,
}
