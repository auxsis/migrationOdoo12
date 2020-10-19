from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, AccessError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ProjectTaskActivityType(models.Model):
    _name='project.task.activity.type'
    
    
    name=fields.Char('Name')
    code=fields.Char('Code')
    company_id=fields.Many2one('res.company', 'Company')
    active=fields.Boolean('Active?')
    