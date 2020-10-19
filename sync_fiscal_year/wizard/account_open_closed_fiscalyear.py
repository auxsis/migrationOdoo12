# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class AccountOpenClosedFiscalYear(models.TransientModel):
    _name = "account.open.closed.fiscalyear"
    _description = "Choose Fiscal Year"

    fyear_id = fields.Many2one('account.fiscalyear', 'Fiscal Year', required=True,\
                        help='Select Fiscal Year which you want to remove entries for its End of year entries journal')

    def remove_entries(self):
        move_obj = self.env['account.move']

        cr = self.env.cr

        period_journal = self.fyear_id.end_journal_period_id or False
        if not period_journal:
            raise UserError(_("Error! \nYou have to set the 'End  of Year Entries Journal' for this Fiscal Year which is set after generating opening entries from 'Generate Opening Entries'."))

        if period_journal.period_id.state == 'done':
            raise UserError(_("Error! \nYou can not cancel closing entries if the 'End of Year Entries Journal' period is closed."))

        ids_move = move_obj.search([('journal_id','=', period_journal.journal_id.id),('period_id','=', period_journal.period_id.id)])
        if ids_move:
            cr.execute('delete from account_move where id IN %s', (tuple(ids_move.ids),))
            self.invalidate_cache()
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
