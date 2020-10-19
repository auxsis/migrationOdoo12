# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.tools import float_is_zero
import json

import logging
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _get_period(self):
        ctx = dict(self._context)
        period_ids = []
        check_period_ids = self.env['account.period'].search([])
        if check_period_ids:
            period_ids = self.env['account.period'].with_context(ctx).find()
        return period_ids and period_ids[0] or False

    period_id = fields.Many2one('account.period', string='Force Period',
        domain=[('state', '!=', 'done')],
        help="Keep empty to use the period of the validation(invoice) date.",
        readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self._get_period(), copy=False)

    @api.model
    def create(self, vals):
        _logger.info("invvals=%s",vals)
        if vals.get('date_invoice') and not vals.get('period_id'):
            period_id = self.env['account.period'].search([('state', '!=', 'done'), ('special', '=', False),
                                                           ('date_start', '<=', vals.get('date_invoice')),
                                                           ('date_stop', '>=', vals.get('date_invoice')),
                                                           ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                vals.update({'period_id': period_id.id})
        return super(AccountInvoice, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('date_invoice'):
            period_id = self.env['account.period'].search([('state', '!=', 'done'), ('special', '=', False),
                                                           ('date_start', '<=', vals.get('date_invoice')),
                                                           ('date_stop', '>=', vals.get('date_invoice')),
                                                           ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                vals.update({'period_id': period_id.id})
        return super(AccountInvoice, self).write(vals)

    @api.onchange('date_invoice')
    def _onchange_date_invoice(self):
        if self.date_invoice:
            self.period_id = False
            period_id = self.env['account.period'].search([('state', '!=', 'done'), ('special', '=', False),
                                                           ('date_start', '<=', self.date_invoice),
                                                           ('date_stop', '>=', self.date_invoice),
                                                           ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if period_id:
                self.period_id = period_id.id

    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('period_id.special', '=', False),
                      ('account_id', '=', self.account_id.id),
                      ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                      ('reconciled', '=', False),
                      '|',
                        '&', ('amount_residual_currency', '!=', 0.0), ('currency_id','!=', None),
                        '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id','=', None), ('amount_residual', '!=', 0.0)]
            if self.type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = self.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == self.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        currency = line.company_id.currency_id
                        amount_to_show = currency._convert(abs(line.amount_residual), self.currency_id, self.company_id, line.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue
                    if line.ref :
                        title = '%s : %s' % (line.move_id.name, line.ref)
                    else:
                        title = line.move_id.name
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'title': title,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True
