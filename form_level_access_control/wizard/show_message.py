# -*- coding: utf-8 -*-
from odoo import api, fields, models

class show_message(models.TransientModel):
    _name='show.message'
    _description='Final Message for Configurations'

    name = fields.Char('Name', default='Changes applied successfully.')

    @api.one
    def ok(self):
        ''' Method called from the button action 'OK' in the wizard.'''
        return True
