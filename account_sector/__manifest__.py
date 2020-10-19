# Copyright 2016-2019 Apiux (<http://www.api-ux.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Sector',
    'summary': 'Sector information for invoice lines',
    'author': 'Apiux',
    'license': 'AGPL-3',
    'website': 'https://github.com/OCA/account-financial-tools/',
    'category': 'Accounting',
    'version': '12.0.1.0.0',
    'depends': [
        'account',
        'base_view_inheritance_extension',        
        # 'account_cost_center'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/account_sector_security.xml',
        'views/account_view.xml',
        'views/hr_employee_view.xml',        
        # 'views/account_invoice_view.xml',
        # 'views/account_invoice_report.xml',        
        'views/sector_view.xml',   
    ],
    'installable': True,
}
