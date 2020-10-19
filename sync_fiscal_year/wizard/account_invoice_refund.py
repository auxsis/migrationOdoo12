# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, fields, api, _

class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    def _get_period(self):
        ctx = dict(self._context)
        period_ids = []
        check_period_ids = self.env['account.period'].search([])
        if check_period_ids:
            period_ids = self.env['account.period'].with_context(ctx).find()
        return period_ids and period_ids[0] or False

    period_id = fields.Many2one('account.period', 'Period', required=True, default=lambda self: self._get_period())

    @api.multi
    def invoice_refund(self):
        data_refund = self.read(['filter_refund'])[0]['filter_refund']
        ctx = dict(self._context)
        ctx.update({'period_id': self.period_id.id})
        return self.with_context(ctx).compute_refund(data_refund)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
