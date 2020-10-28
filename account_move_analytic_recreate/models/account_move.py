# Copyright 2019 Eficent Business and IT Consulting Services S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, fields

import logging
_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"


    invl_id=fields.Many2one('account.invoice.line', string='Invoice Line')


    @api.multi
    def write(self, vals):
        res = super(AccountMoveLine, self).write(vals)
        if 'analytic_account_id' in vals or 'analytic_tag_ids' in vals:
            self.mapped('analytic_line_ids').unlink()
            self.create_analytic_lines()
        return res
