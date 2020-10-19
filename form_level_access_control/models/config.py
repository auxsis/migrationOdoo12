#-*- coding:utf-8 -*-
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class auth_window_config(models.Model):
    _name = 'auth.window.config'
    _description = 'Form Level Security Config'

    default_active = fields.Boolean('Active')
    password = fields.Char('Password')
    security_on = fields.Selection([('users','Users'),('groups','Groups')], 'Option to Select')
    form_ids = fields.Many2many('ir.ui.menu', string='Menus')
    group_ids = fields.Many2many('res.groups', string='User Groups')
    user_ids = fields.Many2many('res.users', string='Users')

    @api.model
    def default_get(self, fields):
        ''' Method inherited to set all the fields from the last updated record.'''
        ret = super(auth_window_config, self).default_get(fields)
        try:
            self.env.cr.execute("SELECT id,default_active,password,security_on FROM auth_window_config ORDER BY write_date DESC LIMIT 1")
            res = self.env.cr.fetchall()
            if res:
                form_ids = [obj. id for obj in self.browse(res[0][0]).form_ids]
                group_ids = [obj. id for obj in self.browse(res[0][0]).group_ids]
                user_ids = [obj. id for obj in self.browse(res[0][0]).user_ids]
                ret.update({'default_active':res[0][1], 'password':res[0][2], 'security_on':res[0][3], 'form_ids':[(6,0,form_ids)], 'group_ids':[(6,0,group_ids)], 'user_ids':[(6,0,user_ids)]})
            else:
                ret.update({'security_on':'groups'})
        except Exception as e:
            _logger.warning("An error has occured. Details: %s"%(repr(e)))
        return ret

    @api.multi
    def apply(self):
        ''' Method called from the Apply button action to update the changes of the form.'''
        self.env.cr.execute("DELETE FROM auth_window_config where id != %s"%(self.id))
        return{
            'type':'ir.actions.act_window',
            'name':'Changes Applied ',
            'res_model':'show.message',
            'view_id':self.env.ref('form_level_access_control.show_final_message_wizard').id,
            'view_mode':'form',
            'target':'new'}
