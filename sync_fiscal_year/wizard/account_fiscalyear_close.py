# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, Warning


class AccountFiscalYearClose(models.TransientModel):
    _name = "account.fiscalyear.close"
    _description = "Fiscalyear Close"

    fy_id = fields.Many2one('account.fiscalyear', 'Fiscal Year to close',\
                     required=True, help="Select a Fiscal year to close")
    fy2_id = fields.Many2one('account.fiscalyear', 'New Fiscal Year', required=True)
    journal_id = fields.Many2one('account.journal', 'Opening Entries Journal', \
                     domain="[('type','=','situation')]", required=True,\
                     help='The best practice here is to use a journal dedicated to contain the opening entries of all fiscal years. Note that you should define it with default debit/credit accounts, of type \'situation\' and with a centralized counterpart.')
    period_id = fields.Many2one('account.period', 'Opening Entries Period', required=True)
    report_name = fields.Char('Name of new entries', required=True, default="End of Fiscal Year Entry",\
                     help="Give name of the new entries")

    def create_reconcile(self, ids):
        if ids:
            r_id = self.env['account.full.reconcile'].create({'reconciled_line_ids': [(6, 0, ids.ids)]})
            self.env.cr.execute('update account_move_line set full_reconcile_id = %s where id in %s',(r_id.id, tuple(ids.ids),))
        self.invalidate_cache()

    def data_save(self):
        obj_acc_period = self.env['account.period']
        obj_acc_fiscalyear = self.env['account.fiscalyear']
        obj_acc_journal = self.env['account.journal']
        obj_acc_move = self.env['account.move']
        obj_acc_move_line = self.env['account.move.line']
        obj_acc_account = self.env['account.account']
        obj_acc_journal_period = self.env['account.journal.period']
        currency_obj = self.env['res.currency']

        move_ids = obj_acc_move_line.search([('state', 'not in', ['draft', 'posted'])])
        if move_ids:
            move_ids._compute_state()

        cr = self.env.cr

        data = self

        if self._context is None:
            self._context = {}
        fy_id = self.fy_id.id

        cr.execute("SELECT id FROM account_period WHERE not special AND date_stop < (SELECT date_start FROM account_fiscalyear WHERE id = %s)", (str(self.fy2_id.id),))
        fy_period_set = ','.join(map(lambda id: str(id[0]), cr.fetchall()))
        cr.execute("SELECT id FROM account_period WHERE not special AND date_start > (SELECT date_stop FROM account_fiscalyear WHERE id = %s)", (str(fy_id),))
        fy2_period_set = ','.join(map(lambda id: str(id[0]), cr.fetchall()))

        if not fy_period_set or not fy2_period_set:
            raise UserError(_('The periods to generate opening entries cannot be found.'))

        period = self.period_id
        new_fyear = self.fy2_id
        old_fyear = self.fy_id

        new_journal = self.journal_id
        company_id = new_journal.company_id.id

        if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
            raise UserError(_('The journal must have default credit and debit account.'))
        if (not new_journal.centralisation) or new_journal.entry_posted:
            raise UserError(_('The journal must have centralized counterpart without the Skipping draft state option checked.'))

        #delete existing move and move lines if any
        move_ids = obj_acc_move.search([
            ('journal_id', '=', new_journal.id), ('period_id', '=', period.id)])

        for move_id in move_ids:
            if move_id.state == 'posted':
                raise Warning(_('Opening Entries have already been generated. Please run "Cancel Closing Entries" wizard to cancel those entries and then run this wizard.'))
            else:
                move_id.line_ids.remove_move_reconcile()
                move_id.line_ids.unlink()
                move_id.unlink()

        cr.execute("SELECT id FROM account_fiscalyear WHERE date_stop < %s", (str(new_fyear.date_start),))
        result = cr.dictfetchall()
        fy_ids = [x['id'] for x in result]

        #create the opening move
        vals = {
            'name': '/',
            'ref': '',
            'period_id': period.id,
            'date': period.date_start,
            'journal_id': new_journal.id,
        }
        move_id = obj_acc_move.create(vals)

        # period_ids = self.env['account.period'].search([('fiscalyear_id', 'in', fy_ids), ('special', '=', False)])
        period_ids = self.env['account.period'].search([('fiscalyear_id', 'in', fy_ids)])

        period_ids = tuple(period_ids and period_ids.ids or [])

        #1. report of the accounts with defferal method == 'unreconciled'
        cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type_id = t.id)
            WHERE not a.deprecated
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'unreconciled', ))

        account_ids = map(lambda x: x[0], cr.fetchall())
        account_ids = tuple(account_ids)
        if account_ids and period_ids:
            cr.execute('''
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, company_currency_id, currency_id, date_maturity,
                     partner_id, blocked, credit, state, debit,
                     ref, account_id, period_id, date, move_id, amount_currency,
                     quantity, product_id, company_id)
                  (SELECT name, create_uid, create_date, write_uid, write_date,
                     statement_id, %s,company_currency_id, currency_id, date_maturity, partner_id,
                     blocked, credit, 'draft', debit, ref, account_id,
                     %s, (%s) AS date, %s, amount_currency, quantity, product_id, company_id
                   FROM account_move_line
                   WHERE account_id IN %s
                     AND period_id IN %s
                     AND state = 'posted'
                     AND full_reconcile_id IS NULL)''', (new_journal.id, period.id, period.date_start, move_id.id, account_ids, period_ids))
                    # In above Query "full_reconcile_id IS NULL" is replaced by "not reconciled".

            # We have also to consider all move_lines that were reconciled
            # on another fiscal year, and report them too
            cr.execute('''
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, company_currency_id, currency_id, date_maturity,
                     partner_id, blocked, credit, state, debit,
                     ref, account_id, period_id, date, move_id, amount_currency,
                     quantity, product_id, company_id)
                  (SELECT
                     b.name, b.create_uid, b.create_date, b.write_uid, b.write_date,
                     b.statement_id, %s, b.company_currency_id, b.currency_id, b.date_maturity,
                     b.partner_id, b.blocked, b.credit, 'draft', b.debit,
                     b.ref, b.account_id, %s, (%s) AS date, %s, b.amount_currency,
                     b.quantity, b.product_id, b.company_id
                     FROM account_move_line b
                     WHERE b.account_id IN %s
                       AND b.full_reconcile_id IS NOT NULL
                       AND state = 'posted'
                       AND b.period_id IN ('''+fy_period_set+''')
                       AND b.full_reconcile_id IN (SELECT DISTINCT(full_reconcile_id)
                                          FROM account_move_line a
                                          WHERE a.period_id IN ('''+fy2_period_set+''')))''', (new_journal.id, period.id, period.date_start, move_id.id, account_ids,))
            self.invalidate_cache()

        #2. report of the accounts with defferal method == 'detail'
        cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type_id = t.id)
            WHERE not a.deprecated
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'detail', ))
        account_ids = map(lambda x: x[0], cr.fetchall())
        account_ids = tuple(account_ids)

        if account_ids and period_ids:
            cr.execute('''
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, company_currency_id, currency_id, date_maturity,
                     partner_id, blocked, credit, state, debit,
                     ref, account_id, period_id, date, move_id, amount_currency,
                     quantity, product_id, company_id)
                  (SELECT name, create_uid, create_date, write_uid, write_date,
                     statement_id, %s,company_currency_id, currency_id, date_maturity, partner_id,
                     blocked, credit, 'draft', debit, ref, account_id,
                     %s, (%s) AS date, %s, amount_currency, quantity, product_id, company_id
                   FROM account_move_line
                   WHERE account_id IN %s
                     AND state = 'posted'
                     AND period_id IN %s)
                     ''', (new_journal.id, period.id, period.date_start, move_id.id, tuple(account_ids), period_ids))
            self.invalidate_cache()

        #3. report of the accounts with defferal method == 'balance'
        cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type_id = t.id)
            WHERE not a.deprecated
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'balance', ))
        account_ids = map(lambda x: x[0], cr.fetchall())

        query_1st_part = """
                INSERT INTO account_move_line (
                     debit, credit, name, date, move_id, journal_id, period_id,
                     account_id, company_currency_id, currency_id, amount_currency, company_id, state) VALUES
        """
        query_2nd_part = ""
        query_2nd_part_args = []
        for account in obj_acc_account.browse(account_ids):

            balance = 0.0
            # for aml in self.env['account.move.line'].search([('account_id', '=', account.id),('state', '=', 'posted'), ('period_id.special', '=', False), ('date', '<=', self.fy_id.date_stop)]):
            for aml in self.env['account.move.line'].search([('account_id', '=', account.id),('state', '=', 'posted'), ('date', '<=', self.fy_id.date_stop)]):
                balance += (aml.debit - aml.credit)

            account.compute_values()
            company_currency_id = self.env.user.company_id.currency_id
            if (abs(balance)) > 0:
                if query_2nd_part:
                    query_2nd_part += ','
                query_2nd_part += "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                query_2nd_part_args += (balance > 0 and balance or 0.0,
                       balance < 0 and -balance or 0.0,
                       self.report_name,
                       period.date_start,
                       move_id and move_id.id or None,
                       new_journal.id,
                       period.id,
                       account.id,
                       (account.currency_id and account.currency_id.id) or company_currency_id.id,
                       account.currency_id and account.currency_id.id or None,
                       account.foreign_balance if account.currency_id else 0.0,
                       account.company_id.id,
                       'draft')

        if query_2nd_part:
            cr.execute(query_1st_part + query_2nd_part, tuple(query_2nd_part_args))
            self.invalidate_cache()

        #validate and centralize the opening move
        move_id.validate()
        ids = obj_acc_move_line.search([('journal_id', '=', new_journal.id), ('period_id.fiscalyear_id','=',new_fyear.id)])
        self.create_reconcile(ids)

        #create the journal.period object and link it to the old fiscalyear
        new_period = self.period_id.id
        ids = obj_acc_journal_period.search([('journal_id', '=', new_journal.id), ('period_id', '=', new_period)])
        if not ids:
            ids = [obj_acc_journal_period.create({
                   'name': (new_journal.name or '') + ':' + (period.code or ''),
                   'journal_id': new_journal.id,
                   'period_id': period.id
               })]
        cr.execute('UPDATE account_fiscalyear ' \
                    'SET end_journal_period_id = %s ' \
                    'WHERE id = %s', (ids[0].id, old_fyear.id))
        obj_acc_fiscalyear.invalidate_cache(['end_journal_period_id'], [old_fyear.id])

        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
