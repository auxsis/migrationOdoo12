# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class AccountPeriodClose(models.TransientModel):
    _name = "account.period.close"
    _description = "period close"

    sure = fields.Boolean('Check this box')

    def data_save(self):

        journal_period_pool = self.env['account.journal.period']
        period_pool = self.env['account.period']
        account_move_obj = self.env['account.move']

        cr = self.env.cr

        mode = 'done'
        for form in self:
            if form.sure:
                for id in self._context.get('active_ids', False):
                    account_move_ids = account_move_obj.search([('period_id', '=', id), ('state', '=', "draft")])
                    if account_move_ids:
                        raise UserError(_('Invalid Action! \nIn order to close a period, you must first post related journal entries.'))

                    cr.execute('update account_journal_period set state=%s where period_id=%s', (mode, id))
                    cr.execute('update account_period set state=%s where id=%s', (mode, id))
                    self.invalidate_cache()

        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
