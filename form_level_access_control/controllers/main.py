# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import Action
import logging
_logger = logging.getLogger(__name__)

class Extension(Action):

    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        '''
             Method overridden for showing the authentication wizard if the menu is configured under Form Level Access Control.
        '''
        try:
            action_id = int(action_id)
        except ValueError:
            try:
                action = request.env.ref(action_id)
                assert action._name.startswith('ir.actions.')
                action_id = action.id
            except Exception:
                action_id = 0   # force failed read        
        orgn_action_id = action_id
        try:
            request.env.cr.execute("SELECT id, default_active FROM auth_window_config ORDER BY write_date DESC LIMIT 1")
            res = request.env.cr.fetchall()
            if res and res[0][1]:
                authaction_id = request.env.ref('form_level_access_control.action_authentication_wizard').id
                currusergrp_ids = [obj.id for obj in request.env.user.groups_id]
                auth_obj = request.env['auth.window.config'].browse(res[0][0])
                group_ids = [obj.id for obj in auth_obj.group_ids]
                user_ids = [obj.id for obj in auth_obj.user_ids]
                action_ids = [obj.action.id for obj in auth_obj.form_ids if obj.action]
    
                if action_id in action_ids:
                    if  auth_obj.security_on == 'users' and request.env.user.id in  user_ids:
                        action_id = authaction_id            
                    elif auth_obj.security_on == 'groups':
                        for group_id in currusergrp_ids:
                            if group_id in group_ids:
                                action_id = authaction_id
                                break;
        except Exception as e:
            raise Exception(repr(e))
            _logger.warning("An Error has occured. Error details: %s"%(repr(e)))
            
        ret = super(Extension, self).load(action_id, additional_context)
        if action_id != orgn_action_id:
            ret.update({'context':{'action_auth_id':orgn_action_id}})
        return ret
