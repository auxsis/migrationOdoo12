from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
import requests
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class SaleOrderServiceType(models.Model):
    _name='sale.order.service.type'
    
    
    name=fields.Char('Name')
    code=fields.Char('Code')
    risk=fields.Float('Risk')
    margin=fields.Float('Margin')
    company_id=fields.Many2one('res.company', 'Company')
    active=fields.Boolean('Active?')
    