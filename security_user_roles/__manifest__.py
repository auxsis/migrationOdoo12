# -*- coding: utf-8 -*-
{
    "name": "Security User Roles",
    "version": "12.0.1.0.2",
    "category": "Extra Tools",
    "author": "Odoo Tools",
    "website": "https://odootools.com/apps/12.0/security-user-roles-318",
    "license": "Other proprietary",
    "application": True,
    "installable": True,
    "auto_install": False,
    "depends": [
        "base"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "views/res_users.xml",
        "views/security_role.xml"
    ],
    "qweb": [
        
    ],
    "js": [
        
    ],
    "demo": [
        
    ],
    "external_dependencies": {},
    "summary": "The tool to combine users in roles and to simplify security group assigning",
    "description": """

For the full details look at static/description/index.html

* Features * 

- Easy to maintain to save your time

- Simple to start

- Safe and comfortable in changing environment
 
* Extra Notes *


    """,
    "images": [
        "static/description/main.png"
    ],
    "price": "32.0",
    "currency": "EUR",
    "post_init_hook": "post_init_hook",
    "live_test_url": "https://odootools.com/my/tickets/newticket?&url_app_id=99&ticket_version=12.0&url_type_id=3",
}