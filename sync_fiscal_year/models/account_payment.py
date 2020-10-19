# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_period(self):
        ctx = dict(self._context)
        period_ids = []
        check_period_ids = self.env['account.period'].search([])
        if check_period_ids:
            period_ids = self.env['account.period'].with_context(ctx).find()
        return period_ids and period_ids[0] or False

    period_id = fields.Many2one('account.period', 'Period', readonly=True, states={'draft':[('readonly',False)]}, default=lambda self: self._get_period(), copy=False)

    @api.model
    def create(self, vals):
        if vals.get('payment_date') and not vals.get('period_id'):
            period_id = self.env['account.period'].search([('state', '!=', 'done'), ('special', '=', False), ('date_start', '<=' , vals.get('payment_date')), ('date_stop', '>=', vals.get('payment_date')), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                vals.update({'period_id': period_id.id})
        return super(AccountPayment, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('payment_date'):
            period_id = self.env['account.period'].search([('state', '!=', 'done'), ('special', '=', False), ('date_start', '<=' , vals.get('payment_date')), ('date_stop', '>=', vals.get('payment_date')), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                vals.update({'period_id': period_id.id})
        return super(AccountPayment, self).write(vals)

    @api.onchange('payment_date')
    def _onchange_payment_date(self):
        if self.payment_date:
            self.period_id = False
            period_id = self.env['account.period'].search([('state', '!=', 'done'), ('special', '=', False), ('date_start', '<=' , self.payment_date), ('date_stop', '>=', self.payment_date), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                self.period_id = period_id.id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
