# Copyright 2015-2019 Onestein (<http://www.onestein.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def _default_cost_center(self):
        return self.env['account.cost.center'].browse(
            self.env.context.get('cost_center_id'))

    cost_center_id = fields.Many2one(
        'account.cost.center',
        string='Cost Center',
        index=True,
        default=lambda self: self._default_cost_center(),
    )


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'        
        
        
    @api.model
    def _default_cost_center(self):
        return self._context.get('cost_center_id') \
            or self.env['account.cost.center']        
     
    cost_center_id = fields.Many2one(
        'account.cost.center', string='Cost Center',
        default=_default_cost_center)

    @api.model
    def move_line_get(self, invoice_id):
        res = super(AccountInvoiceTax, self).move_line_get(invoice_id)
        
        invoice=self.env['account.invoice'].browse([invoice_id])
        if invoice and invoice.cost_center_id:
            for tax_line in res:
                tax_line['cost_center_id'] = invoice.cost_center_id.id
        return res