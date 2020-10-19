# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models


class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'
    _description = 'Account Reconciliation widget'

    @api.model
    def _domain_move_lines_for_manual_reconciliation(self, account_id, partner_id=False, excluded_ids=None, search_str=False):
        domain = super(AccountReconciliation, self)._domain_move_lines_for_manual_reconciliation(account_id, partner_id, excluded_ids, search_str)
        domain.append(('period_id.special', '=', False))
        return domain
