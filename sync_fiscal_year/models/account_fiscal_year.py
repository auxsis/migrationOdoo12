# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError, Warning
from odoo.osv import expression
from datetime import datetime
from dateutil.relativedelta import relativedelta


class account_fiscalyear(models.Model):
    _name = "account.fiscalyear"
    _description = "Fiscal Year"
    _order = "date_start, id"

    name = fields.Char('Fiscal Year', required=True)
    code = fields.Char('Code', size=6, required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id.id)
    date_start = fields.Date('Start Date', required=True)
    date_stop = fields.Date('End Date', required=True)
    period_ids = fields.One2many('account.period', 'fiscalyear_id', 'Periods')
    state = fields.Selection([('draft','Open'), ('done','Closed')],
            string ='Status', readonly=True, copy=False, default='draft')
    end_journal_period_id = fields.Many2one(
             'account.journal.period', 'End of Year Entries Journal',
             readonly=True, copy=False)

    def set_period(self):
        for invoice in self.env['account.invoice'].search([('date_invoice', '>=' , self.date_start),('date_invoice', '<=', self.date_stop),('period_id', '=', False)]):
            period_id = self.env['account.period'].search([
                ('special', '=', False),
                ('date_start', '<=' , invoice.date_invoice),
                ('date_stop', '>=', invoice.date_invoice),
                ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                invoice.write({'period_id': period_id.id})

        for payment in self.env['account.payment'].search([('payment_date', '>=' , self.date_start),('payment_date', '<=', self.date_stop),('period_id', '=', False)]):
            period_id = self.env['account.period'].search([
                ('special', '=', False),
                ('date_start', '<=', payment.payment_date),
                ('date_stop', '>=', payment.payment_date),
                ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                payment.write({'period_id': period_id.id})

        for move in self.env['account.move'].search([('date', '>=', self.date_start), ('date', '<=', self.date_stop),
                                                     ('period_id', '=', False)]):
            period_id = self.env['account.period'].search([
                ('special', '=', False),
                ('date_start', '<=', move.date),
                ('date_stop', '>=', move.date),
                ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                move.write({'period_id': period_id.id})

        for line in self.env['account.move.line'].search([('date', '>=', self.date_start),
                                                          ('date', '<=', self.date_stop),
                                                          ('period_id', '=', False)]):
            period_id = self.env['account.period'].search([
                ('special', '=', False),
                ('date_start', '<=', line.date),
                ('date_stop', '>=', line.date),
                ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                line.write({'period_id': period_id.id})

        for voucher in self.env['account.voucher'].search([('date', '>=', self.date_start),
                                                           ('date', '<=', self.date_stop),
                                                           ('period_id', '=', False)]):
            period_id = self.env['account.period'].search([
                ('special', '=', False),
                ('date_start', '<=' , voucher.date),
                ('date_stop', '>=', voucher.date),
                ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                voucher.write({'period_id':period_id.id})

    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        if self.date_stop < self.date_start:
            raise UserError(_('The start date of a fiscal year must precede its end date.'))

    def create_period3(self):
        return self.with_context(interval=3).create_period()

    def create_period(self):
        interval = self._context.get('interval', 1)
        period_obj = self.env['account.period']

        for fy in self:
            ds = datetime.strptime(str(fy.date_start), '%Y-%m-%d')
            period_obj.create({
                    'name':  "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
                    'code': ds.strftime('00/%Y'),
                    'date_start': ds,
                    'date_stop': ds,
                    'special': True,
                    'fiscalyear_id': fy.id,
                })
            while ds.date() < fy.date_stop:
                de = ds + relativedelta(months=interval, days=-1)

                if de.date() > fy.date_stop:
                    de = datetime.strptime(str(fy.date_stop), '%Y-%m-%d')

                period_obj.create({
                    'name': ds.strftime('%m/%Y'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                })
                ds = ds + relativedelta(months=interval)
        return True

    def find(self, dt=None, exception=True, previous=False):
        res = self.finds(dt, exception, previous)
        return res and res[0] or False

    def finds(self, dt=None, exception=True, previous=False):

        context = self._context
        if not dt:
            dt = fields.Date.context_today(self)
        args = [('date_start', '<=', dt), ('date_stop', '>=', dt)]
        if context.get('company_id', False):
            company_id = context['company_id']
        else:
            company_id = self.env.user.company_id.id

        args.append(('company_id', '=', company_id))
        ids = self.search(args)

        if not ids and not previous:
            return []
        return ids

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=80):
        args = args or []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        ids = self.search(expression.AND([domain, args]), limit=limit)
        return ids.name_get()


class account_period(models.Model):
    _name = "account.period"
    _description = "Account period"
    _order = "date_start, special desc"

    name = fields.Char('Period Name', required=True)
    code = fields.Char('Code', size=12)
    special = fields.Boolean('Opening/Closing Period',help="These periods can overlap.")
    date_start = fields.Date('Start of Period', required=True, states={'done':[('readonly',True)]})
    date_stop = fields.Date('End of Period', required=True, states={'done':[('readonly',True)]})
    fiscalyear_id = fields.Many2one('account.fiscalyear', 'Fiscal Year', required=True, states={'done':[('readonly',True)]})
    state = fields.Selection([('draft','Open'), ('done', 'Closed')], 'Status', readonly=True, copy=False, default='draft',
                              help='When monthly periods are created. The status is \'Draft\'. At the end of monthly period it is in \'Done\' status.')
    company_id = fields.Many2one('res.company', related='fiscalyear_id.company_id', string='Company', store=True, readonly=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'The name of the period must be unique per company!'),
    ]

    @api.constrains('date_stop')
    def _check_duration(self):
        if self.date_stop < self.date_start:
            raise UserError(_('The duration of the Period(s) is/are invalid.'))
        for obj_period in self:
            if obj_period.special:
                continue

            if obj_period.fiscalyear_id.date_stop < obj_period.date_stop or \
               obj_period.fiscalyear_id.date_stop < obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_stop:
                raise UserError(_('The period is invalid. Either some periods are overlapping or the period\'s dates are not matching the scope of the fiscal year.'))

            pids = self.search([('date_stop','>=',obj_period.date_start),('date_start','<=',obj_period.date_stop),('special','=',False),('id','<>',obj_period.id)])
            for period in pids:
                if period.fiscalyear_id.company_id.id==obj_period.fiscalyear_id.company_id.id:
                    return UserError(_('The period is invalid. Either some periods are overlapping or the period\'s dates are not matching the scope of the fiscal year.'))

    @api.returns('self')
    def next(self, period, step):
        ids = self.search([('date_start', '>', period.date_start)])
        if len(ids) >= step:
            return ids[step-1]
        return False

    @api.returns('self')
    def find(self, dt=None):
        context = self._context
        if not dt:
            dt = fields.Date.context_today(self)
        args = [('date_start', '<=', dt), ('date_stop', '>=', dt)]
        if context.get('company_id', False):
            args.append(('company_id', '=', context['company_id']))
        else:
            company_id = self.env.user.company_id.id
            args.append(('company_id', '=', company_id))
        result = []
        if context.get('account_period_prefer_normal', True):
            # look for non-special periods first, and fallback to all if no result is found
            result = self.search(args + [('special', '=', False)])
        if not result:
            result = self.search([])
        return result

    def action_draft(self):
        mode = 'draft'
        for period in self:
            if period.fiscalyear_id.state == 'done':
                raise Warning(_('You can not re-open a period which belongs to closed fiscal year'))
        self.env.cr.execute('update account_journal_period set state=%s where period_id in %s', (mode, tuple(self.ids),))
        self.env.cr.execute('update account_period set state=%s where id in %s', (mode, tuple(self.ids),))
        self.invalidate_cache()
        return True

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        ids = self.search(expression.AND([domain, args]), limit=limit)
        return ids.name_get()

    @api.multi
    def write(self, vals):
        if 'company_id' in vals:
            move_lines = self.env['account.move.line'].search([('period_id', 'in', ids)])
            if move_lines:
                raise Warning(_('This journal already contains items for this period, therefore you cannot modify its company field.'))
        return super(account_period, self).write(vals)

    def build_ctx_periods(self, period_from_id, period_to_id):
        if period_from_id == period_to_id:
            return [period_from_id]
        period_from = self.period_from_id
        period_date_start = period_from.date_start
        company1_id = period_from.company_id.id
        period_to = self.period_to_id
        period_date_stop = period_to.date_stop
        company2_id = period_to.company_id.id
        if company1_id != company2_id:
            raise UserError(_('You should choose the periods that belong to the same company.'))
        if period_date_start > period_date_stop:
            raise UserError(_('Start period should precede then end period.'))

        if period_from.special:
            return self.search([('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop)])
        return self.search([('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop), ('special', '=', False)])


class account_journal_period(models.Model):
    _name = "account.journal.period"
    _description = "Journal Period"
    _order = "period_id"

    @api.multi
    def _icon_get(self):
        for rec in self:
            result = {}.fromkeys(self, 'STOCK_NEW')
            for r in self.read(['state']):
                result[r['id']] = {
                    'draft': 'STOCK_NEW',
                    'printed': 'STOCK_PRINT_PREVIEW',
                    'done': 'STOCK_DIALOG_AUTHENTICATION',
                }.get(r['state'], 'STOCK_NEW')
            return result

    name = fields.Char('Journal-Period Name', required=True)
    journal_id = fields.Many2one('account.journal', 'Journal', required=True, ondelete="cascade")
    period_id = fields.Many2one('account.period', 'Period', required=True, ondelete="cascade")
    icon = fields.Char(compute=_icon_get, string='Icon')
    active = fields.Boolean('Active', default=True, help="If the active field is set to False, it will allow you to hide the journal period without removing it.")
    state = fields.Selection([('draft','Draft'), ('printed','Printed'), ('done','Done')], 'Status', required=True, readonly=True, default='draft',
                              help='When journal period is created. The status is \'Draft\'. If a report is printed it comes to \'Printed\' status. When all transactions are done, it comes in \'Done\' status.')
    fiscalyear_id = fields.Many2one('account.fiscalyear',related='period_id.fiscalyear_id', string='Fiscal Year')
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True)

    def _check(self):
        for obj in self:
            self.env.cr.execute('select * from account_move_line where journal_id=%s and period_id=%s limit 1', (obj.journal_id.id, obj.period_id.id))
            res = self.env.cr.fetchall()
            if res:
                raise UserError(_('You cannot modify/delete a journal with entries for this period.'))
        return True

    @api.multi
    def write(self, vals):
        for rec in self:
            rec._check()
        return super(account_journal_period, self).write(vals)

    @api.model
    def create(self, vals):
        if vals.get('period_id',False):
            period = self.env['account.period'].browse(vals.get('period_id',False))
            vals['state'] = period.state
        return super(account_journal_period, self).create(vals)

    @api.multi
    def unlink(self):
        for rec in self:
            rec._check()
        return super(account_journal_period, self).unlink()
