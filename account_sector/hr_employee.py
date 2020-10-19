from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class hr_employee(models.Model):
    _inherit='hr.employee'
    
    sector_id=fields.Many2one('account.sector', string='Sector')