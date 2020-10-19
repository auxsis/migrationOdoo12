# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models, api, _
import odoo.addons.decimal_precision as dp


class AccountAccount(models.Model):
    _inherit = "account.account"

    @api.multi
    @api.depends('move_line_ids','move_line_ids.amount_currency','move_line_ids.debit','move_line_ids.credit')
    def compute_values(self):
        for account in self:
            balance = 0.0
            credit = 0.0
            debit = 0.0
            for aml in self.env['account.move.line'].search([('account_id', '=', account.id)]):
                balance += aml.debit - aml.credit
                credit += aml.credit
                debit += aml.debit
            account.balance = balance
            account.credit = credit
            account.debit = debit

    move_line_ids = fields.One2many('account.move.line','account_id','Journal Entry Lines')
    balance = fields.Float(compute="compute_values", digits=dp.get_precision('Account'), string='Balance')
    credit = fields.Float(compute="compute_values",digits=dp.get_precision('Account'), string='Credit')
    debit = fields.Float(compute="compute_values",digits=dp.get_precision('Account'), string='Debit')


class AccountAccountType(models.Model):
    _inherit = "account.account.type"

    close_method = fields.Selection([('none', 'None'), ('balance', 'Balance'), ('detail', 'Detail'), ('unreconciled', 'Unreconciled')], 'Deferral Method', required=False, help="""Set here the method that will be used to generate the end of year journal entries for all the accounts of this type.
                                     'None' means that nothing will be done.
                                     'Balance' will generally be used for cash accounts.
                                     'Detail' will copy each existing journal item of the previous year, even the reconciled ones.
                                     'Unreconciled' will copy only the journal items that were unreconciled on the first day of the new fiscal year.""")


class account_journal(models.Model):
    _inherit = "account.journal"

    centralisation = fields.Boolean('Centralized Counterpart', help="Check this box to determine that each entry of this journal won't create a new counterpart but will share the same counterpart. This is used in fiscal year closing.")
    entry_posted = fields.Boolean('Autopost Created Moves', help='Check this box to automatically post entries of this journal. Note that legally, some entries may be automatically posted when the source document is validated (Invoices), whatever the status of this field.')
    type = fields.Selection(selection_add=[('situation', 'Opening/Closing Situation')])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
