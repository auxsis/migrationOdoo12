# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.http import request
from odoo.addons.web.controllers import main
from odoo.exceptions import ValidationError,AccessDenied
import logging
_logger = logging.getLogger(__name__)

class wizard_password(models.TransientModel):
    _name='wizard.password'
    _description='Authentication wizard'
    
    password = fields.Char('Enter Password', required=True)
    
    @api.multi
    def validate(self):
        '''Method called from the button action 'Validate' on the authentication wizard. '''
        value = False
        userVerify = False
        
        
        try:
        
            userVerify=self.validate_credentials(self.password)
            if userVerify and self.env.context.get('action_auth_id'):
                action_id = self.env.context['action_auth_id']
                Actions = request.env['ir.actions.actions']
                base_action = Actions.browse([action_id]).read(['type'])
                if base_action:
                    ctx = dict(request.context)
                    action_type = base_action[0]['type']
                    if action_type == 'ir.actions.report.xml':
                        ctx.update({'bin_size': True})
                    action = request.env[action_type].browse([action_id]).read()
                    if action:
                        value = main.clean_action(action[0])   
                    return value
            else:
                raise ValidationError("Incorrect Password")
        except ValidationError:
            raise ValidationError("Incorrect Password. Please contact your administrator to enable the access.")
        except Exception as e:
            _logger.warning("An error has occured while validating. Error %s"%(repr(e)))
            raise ValidationError("There might be an error in re-directing the form or validating the Password. \nPlease remove the security on this Menu.")
                         

    def validate_credentials(self,password):
    
        user_obj=self.env['res.users'].sudo().browse(self.env.uid)
        try:
            user_obj._check_credentials(password)
            return True
        except AccessDenied:
            return False