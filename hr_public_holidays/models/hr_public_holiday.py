# -*- coding: utf-8 -*-
# © 2016 ONESTEiN BV (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,AccessDenied,Warning

_logger = logging.getLogger(__name__)


class HrPublicHoliday(models.Model):
    _name = 'hr.public.holiday'

    name = fields.Char('Description', size=64)
    state = fields.Selection([('draft', 'To Approve'),('validate', 'Approved')],'Status', readonly=True,track_visibility='onchange', copy=False,default='draft')
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    company_id = fields.Many2one('res.company',string='Company')
          

    @api.model
    def _employees_for_public_holiday(self, company):
        company_id = company and company.id or None
        employees = self.env['hr.employee'].search(
            ['|',
             ('company_id', '=', company_id),
             ('company_id', '=', False)])
        return employees


    @api.one
    def validate(self):
        self.state = 'validate'

    @api.one
    def reset(self):
        self.state = 'draft'
        
        
    # @api.onchange('date_from','date_to','company_id','exemptions_ids')
    # def onchange_dates(self):
        # if self.exemptions_ids:
            # raise ValidationError("No se puede modificar el Feriado si hay Vacaciones asociadas. Por favor, contactarse con RRHH") 

