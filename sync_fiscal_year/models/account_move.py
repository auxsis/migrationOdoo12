# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, Warning
from odoo.tools.safe_eval import safe_eval


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_period(self):
        ctx = dict(self._context)
        period_ids = []
        check_period_ids = self.env['account.period'].search([])
        if check_period_ids:
            period_ids = self.env['account.period'].with_context(ctx).find()
        return period_ids and period_ids[0] or False

    period_id = fields.Many2one('account.period', 'Period', required=False, states={'posted':[('readonly',True)]}, default=lambda self: self._get_period(), copy=False)

    @api.model
    def create(self, vals):
        if vals.get('date') and not vals.get('period_id'):
            # period_id = self.env['account.period'].search([('state', '!=', 'done'), ('special', '=', False), ('date_start', '<=' , vals.get('date')), ('date_stop', '>=', vals.get('date')), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            period_id = self.env['account.period'].search([('state', '!=', 'done'), ('date_start', '<=' , vals.get('date')), ('date_stop', '>=', vals.get('date')), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                vals.update({'period_id': period_id.id})
        return super(AccountMove, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('date'):
            # period_id = self.env['account.period'].search([('state', '!=', 'done'), ('special', '=', False), ('date_start', '<=' , vals.get('date')), ('date_stop', '>=', vals.get('date')), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            period_id = self.env['account.period'].search([('state', '!=', 'done'), ('date_start', '<=' , vals.get('date')), ('date_stop', '>=', vals.get('date')), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                vals.update({'period_id': period_id.id})
        return super(AccountMove, self).write(vals)

    @api.onchange('date')
    def _onchange_date(self):
        if self.date:
            self.period_id = False
            # period_id = self.env['account.period'].search([('state', '!=', 'done'), ('special', '=', False), ('date_start', '<=' , self.date), ('date_stop', '>=', self.date), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            period_id = self.env['account.period'].search([('state', '!=', 'done'), ('date_start', '<=' , self.date), ('date_stop', '>=', self.date), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                self.period_id = period_id.id

    def _centralise(self, mode):
        cr = self.env.cr
        assert mode in ('debit', 'credit'), 'Invalid Mode' #to prevent sql injection
        currency_obj = self.env['res.currency']
        account_move_line_obj = self.env['account.move.line']
        context = dict(self._context or {})

        if mode == 'credit':
            account_id = self.journal_id.default_debit_account_id.id
            mode2 = 'debit'
            if not account_id:
                raise UserError(_('There is no default debit account defined \n' \
                                'on journal "%s".') % self.journal_id.name)
        else:
            account_id = self.journal_id.default_credit_account_id.id
            mode2 = 'credit'
            if not account_id:
                raise UserError(_('There is no default credit account defined \n' \
                                'on journal "%s".') % self.journal_id.name)

        self.env.cr.execute('select id from account_move_line where move_id=%s and centralisation=%s limit 1', (self.id, mode))
        res = cr.fetchone()
        if res:
            line_id = res[0]
        else:
            context.update({'journal_id': self.journal_id.id, 'period_id': self.period_id.id})
            line_id = account_move_line_obj.create({
                'name': _(mode.capitalize()+' Centralisation'),
                'centralisation': mode,
                'partner_id': False,
                'account_id': account_id,
                'move_id': self.id,
                'journal_id': self.journal_id.id,
                'period_id': self.period_id.id,
                'date': self.period_id.date_stop,
                'debit': 0.0,
                'credit': 0.0,
            })

        cr.execute('select id from account_move_line where move_id=%s and centralisation=%s limit 1', (self.id, mode2))
        res = cr.fetchone()
        if res:
            line_id2 = res[0]
        else:
            line_id2 = 0

        cr.execute('SELECT SUM(%s) FROM account_move_line WHERE move_id=%%s AND id!=%%s' % (mode,), (self.id, line_id2))
        result = cr.fetchone()[0] or 0.0
        cr.execute('update account_move_line set '+mode2+'=%s where id=%s', (result, line_id.id))
        account_move_line_obj.invalidate_cache([mode2], [line_id])

        cr.execute("select currency_id, sum(amount_currency) as amount_currency from account_move_line where move_id = %s and currency_id is not null group by currency_id", (self.id,))
        for row in cr.dictfetchall():
            currency_id = currency_obj.browse(row['currency_id'])
            if not currency_obj.is_zero(currency_id):
                amount_currency = row['amount_currency'] * -1
                account_id = amount_currency > 0 and self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id
                cr.execute('select id from account_move_line where move_id=%s and centralisation=\'currency\' and currency_id = %slimit 1', (self.id, row['currency_id']))
                res = cr.fetchone()
                if res:
                    cr.execute('update account_move_line set amount_currency=%s , account_id=%s where id=%s', (amount_currency, account_id, res[0]))
                    account_move_line_obj.invalidate_cache(['amount_currency', 'account_id'], [res[0]])
                else:
                    context.update({'journal_id': self.journal_id.id, 'period_id': self.period_id.id})
                    line_id = account_move_line_obj.create({
                        'name': _('Currency Adjustment'),
                        'centralisation': 'currency',
                        'partner_id': False,
                        'account_id': account_id,
                        'move_id': self.id,
                        'journal_id': self.journal_id.id,
                        'period_id': self.period_id.id,
                        'date': self.period_id.date_stop,
                        'debit': 0.0,
                        'credit': 0.0,
                        'currency_id': row['currency_id'],
                        'amount_currency': amount_currency,
                    })

        return True

    def validate(self):
        context = self._context
        if context and ('__last_update' in context):
            del context['__last_update']

        valid_moves = []
        obj_analytic_line = self.env['account.analytic.line']
        obj_move_line = self.env['account.move.line']
        obj_precision = self.env['decimal.precision']
        prec = obj_precision.precision_get('Account')
        for move in self:
            journal = move.journal_id
            amount = 0
            line_ids = []
            line_draft_ids = []
            company_id = None

            obj_move_line._update_journal_check(journal.id, move.period_id.id)
            for line in move.line_ids:
                amount += line.debit - line.credit
                line_ids.append(line.id)
                if line.state=='draft':
                    line_draft_ids.append(line.id)

                if not company_id:
                    company_id = line.account_id.company_id.id
                if not company_id == line.account_id.company_id.id:
                    raise UserError(_("Cannot create moves for different companies."))

                if line.account_id.currency_id and line.currency_id:
                    if line.account_id.currency_id.id != line.currency_id.id and (line.account_id.currency_id.id != line.account_id.company_id.currency_id.id):
                        raise UserError(_("""Couldn't create move with currency different from the secondary currency of the account "%s - %s". Clear the secondary currency field of the account definition if you want to accept all currencies.""") % (line.account_id.code, line.account_id.name))

            if round(abs(amount), prec) < 10 ** (-max(5, prec)):
                valid_moves.append(move)
                if not line_draft_ids:
                    continue
                # self.env['account.move.line'].browse(line_draft_ids).write({'state': 'valid'})

                account = {}
                account2 = {}

            elif journal.centralisation:
                valid_moves.append(move)
                move._centralise('debit')
                move._centralise('credit')

                # self.env['account.move.line'].browse(line_draft_ids).write({'state': 'valid'})
            else:
                not_draft_line_ids = list(set(line_ids) - set(line_draft_ids))
                if not_draft_line_ids:
                    self.env['account.move.line'].browse(not_draft_line_ids).write({'state': 'valid'})

        valid_moves = [move.id for move in valid_moves]
        return len(valid_moves) > 0 and valid_moves or False

    @api.multi
    def _check_lock_date(self):
        """
        overwrite method for check closed period.
        """
        for move in self:
            close_periods = self.env['account.period'].search([('state', '=', 'done')])
            for close_period in close_periods:
                if move.date >= close_period.date_start and move.date <= close_period.date_stop:
                    if self.user_has_groups('account.group_account_manager'):
                        message = _("You cannot add/modify entries prior to and inclusive of the lock date %s to %s") % (close_period.date_start, close_period.date_stop)
                    else:
                        message = _("You cannot add/modify entries prior to and inclusive of the lock date %s to %s. Check the company settings or ask someone with the 'Adviser' role") % (close_period.date_start, close_period.date_stop)
                    raise UserError(message)
        return True

    @api.multi
    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        for line in self.line_ids:
            line._compute_state()
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('move_id', 'move_id.state', 'period_id', 'move_id.period_id')
    def _compute_state(self):
        for record in self.filtered('move_id'):
            record.state = record.move_id.state

    period_id = fields.Many2one('account.period', related='move_id.period_id', string='Period', index=True, store=True, copy=False)
    state = fields.Selection([('draft', 'Unposted'), ('posted', 'Posted')], compute="_compute_state", string='Status', store=True, copy=False)
    centralisation = fields.Selection([('normal','Normal'),('credit','Credit Centralisation'),('debit','Debit Centralisation'),('currency','Currency Adjustment')], 'Centralisation', default='normal')
    date_maturity = fields.Date(string='Due date', index=True, required=False,
        help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")

    @api.model
    def _query_get(self, domain=None):
        self.check_access_rights('read')

        context = dict(self._context or {})
        domain = domain or []
        if not isinstance(domain, (list, tuple)):
            domain = safe_eval(domain)

        date_field = 'date'
        if context.get('aged_balance'):
            date_field = 'date_maturity'
        if context.get('date_to'):
            domain += [(date_field, '<=', context['date_to'])]
        if context.get('date_from'):
            if not context.get('strict_range'):
                domain += ['|', (date_field, '>=', context['date_from']), ('account_id.user_type_id.include_initial_balance', '=', True)]
            elif context.get('initial_bal'):
                domain += [(date_field, '<', context['date_from'])]
            else:
                domain += [(date_field, '>=', context['date_from'])]

        if context.get('journal_ids'):
            domain += [('journal_id', 'in', context['journal_ids'])]

        if context.get('fiscalyear'):
            period_ids = self.env['account.period'].search([('fiscalyear_id', 'in', context.get('fiscalyear'))])
            if period_ids:
                domain += [('period_id', 'in', period_ids.ids)]

        state = context.get('state')
        if state and state.lower() != 'all':
            domain += [('move_id.state', '=', state)]

        if context.get('company_id'):
            domain += [('company_id', '=', context['company_id'])]

        if 'company_ids' in context:
            domain += [('company_id', 'in', context['company_ids'])]

        if context.get('reconcile_date'):
            domain += ['|', ('reconciled', '=', False), '|', ('matched_debit_ids.max_date', '>', context['reconcile_date']), ('matched_credit_ids.max_date', '>', context['reconcile_date'])]

        if context.get('account_tag_ids'):
            domain += [('account_id.tag_ids', 'in', context['account_tag_ids'].ids)]

        if context.get('account_ids'):
            domain += [('account_id', 'in', context['account_ids'].ids)]

        if context.get('analytic_tag_ids'):
            domain += [('analytic_tag_ids', 'in', context['analytic_tag_ids'].ids)]

        if context.get('analytic_account_ids'):
            domain += [('analytic_account_id', 'in', context['analytic_account_ids'].ids)]

        if context.get('partner_ids'):
            domain += [('partner_id', 'in', context['partner_ids'].ids)]

        if context.get('partner_categories'):
            domain += [('partner_id.category_id', 'in', context['partner_categories'].ids)]

        where_clause = ""
        where_clause_params = []
        tables = ''
        if domain:
            query = self._where_calc(domain)

            # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
            self._apply_ir_rules(query)

            tables, where_clause, where_clause_params = query.get_sql()
        return tables, where_clause, where_clause_params

    def _update_journal_check(self, journal_id, period_id):
        cr = self.env.cr
        journal_obj = self.env['account.journal']
        period_obj = self.env['account.period']
        jour_period_obj = self.env['account.journal.period']
        cr.execute('SELECT state FROM account_journal_period WHERE journal_id = %s AND period_id = %s', (journal_id, period_id))
        result = cr.fetchall()
        journal = journal_obj.browse(journal_id)
        period = period_obj.browse(period_id)
        for (state,) in result:
            if state == 'done':
                raise UserError(_('You can not add/modify entries in a closed period %s of journal %s.') % (period.name, journal.name))
        if not result:
            jour_period_obj.create({
                'name': (journal.code or journal.name)+':'+(period.name or ''),
                'journal_id': journal.id,
                'period_id': period.id
            })
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
