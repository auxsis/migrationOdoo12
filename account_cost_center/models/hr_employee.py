from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class hr_employee(models.Model):
    _inherit='hr.employee'
    
    cost_center_id=fields.Many2one('account.cost.center', string='Cost Center')