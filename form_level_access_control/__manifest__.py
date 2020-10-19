# -*- coding: utf-8 -*-
{
        'name':'Form Level Access Control',
        'category':'Security',
        'version':'1.1',
        'website': 'http://ktree.com/',
        'author':'KTree Computer Solutions India (P) Ltd',
        'summary': 'Configuration, Authentication Wizard',
        'description':"""
1. Main objective of the module is that every Form in the Odoo can be made more secured.
2. A configuration is provided under the Settings -> Technical ->Security, where the Users/User Groups, Password, Menus are configured.
3. The Users defined under the configured group are authenticated(A wizard popped out to enter the Password) before they can able to access the form.
4. Access is granted only on the successful authentication.
Navigation: Settings -> Technical -> Security -> Form Level Access Control. """,
        'depends':[
               'base',
               'web',
         ],
        'data':[
                'views/config_view.xml',
                'wizard/show_message_view.xml',
                'wizard/wizard_password_view.xml',
                'security/ir.model.access.csv'
         ],
        'images':['images/main-screenshot.png'],
        'demo':[],
        'installable':True,
        'auto_install':False,
        'application':True,
        'price':35.00,
        'currency':'EUR',
        'license':'AGPL-3'        
}
