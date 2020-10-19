# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 ONESTEiN BV (<http://www.onestein.nl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import _
from odoo import models, fields, api, exceptions
from odoo.exceptions import Warning,ValidationError

from collections import defaultdict
import collections

from lxml import etree
import logging

import logging
_logger = logging.getLogger(__name__)



class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def _default_sector(self):
        return self._context.get('sector_id') \
            or self.env['account.sector']

    sector_id = fields.Many2one('account.sector', string='Sector',default=_default_sector)

    @api.model
    def move_line_get_item(self, line):
        res = super(account_invoice_line, self).move_line_get_item(line)
        if line.cost_center_id:
            res['cost_center_id'] = line.cost_center_id.id
        if line.sector_id:
            res['sector_id'] = line.sector_id.id            
        return res

        
class account_invoice_tax(models.Model):
    _inherit = 'account.invoice.tax'        
        
        
    @api.model
    def _default_sector(self):
        return self._context.get('sector_id') \
            or self.env['account.sector']        
     
    sector_id = fields.Many2one('account.sector', string='Sector', default=_default_sector)

    @api.model
    def move_line_get(self, invoice_id):
        res = super(account_invoice_tax, self).move_line_get(invoice_id)

        
        invoice=self.env['account.invoice'].browse([invoice_id])
        if invoice and invoice.cost_center_id:
            for tax_line in res:
                tax_line['cost_center_id'] = invoice.cost_center_id.id
        if invoice and invoice.sector_id:
            for tax_line in res:
                tax_line['sector_id'] = invoice.sector_id.id                
        return res        
        
        
        
