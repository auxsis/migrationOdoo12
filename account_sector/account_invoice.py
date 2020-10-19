# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 ONESTEiN BV (<http://www.onestein.nl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import _
from odoo import models, fields, api, exceptions
from odoo.exceptions import Warning,ValidationError,UserError
from odoo.tools.safe_eval import safe_eval

from collections import defaultdict
import collections

from lxml import etree
import logging

_logger = logging.getLogger(__name__)


class AccountAccount(models.Model):
    _inherit='account.account'
    
    
    move_line_ids=fields.One2many('account.move.line','account_id', string='Account move lines')
    
   

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    sector_id = fields.Many2one('account.sector', string='Sector', help="Default Sector")
    
    
     
        
    @api.model
    def line_get_convert(self, line, part):
        res = super(AccountInvoice, self).line_get_convert(line, part)
        if line.get('sector_id'):
            res['sector_id'] = line['sector_id']            
        return res



    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()

        for dict_data in res:
            invl_id = dict_data.get('invl_id')
            line = self.env['account.invoice.line'].browse(invl_id)
            if line.sector_id:
                dict_data['sector_id'] = line.sector_id.id

        return res
        
        
        
    @api.model
    def tax_line_move_line_get_old(self):
        res = super(AccountInvoice, self).tax_line_move_line_get()

        for dict_data in res:
            invl_id = dict_data.get('invl_id')
            line = self.env['account.invoice.line'].browse(invl_id)
            if line.cost_center_id:
                dict_data['cost_center_id'] = line.cost_center_id.id            
            if line.sector_id:
                dict_data['sector_id'] = line.sector_id.id

        return res        
        
        
        
    @api.model
    def tax_line_move_line_get(self):
        res = []
        # keep track of taxes already processed
        done_taxes = []
        # loop the invoice.tax.line in reversal sequence
        for tax_line in sorted(self.tax_line_ids, key=lambda x: -x.sequence):
            amount = tax_line.amount_total + tax_line.amount_retencion
            if amount:
                tax = tax_line.tax_id
                if tax.amount_type == "group":
                    for child_tax in tax.children_tax_ids:
                        done_taxes.append(child_tax.id)
                analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in tax_line.analytic_tag_ids]
                done_taxes.append(tax.id)
                if tax_line.amount_total > 0:
                    res.append({
                        'invoice_tax_line_id': tax_line.id,
                        'tax_line_id': tax_line.tax_id.id,
                        'type': 'tax',
                        'name': tax_line.name,
                        'price_unit': tax_line.amount_total,
                        'quantity': 1,
                        'price': tax_line.amount_total,
                        'account_id': tax_line.account_id.id,
                        'cost_center_id':tax_line.cost_center_id.id,
                        'sector_id':tax_line.sector_id.id,
                        'account_analytic_id': tax_line.account_analytic_id.id,
                        'analytic_tag_ids': analytic_tag_ids,
                        'invoice_id': self.id,
                        'tax_ids': [(6, 0, done_taxes)] if tax_line.tax_id.include_base_amount else []
                    })
                if tax_line.amount_retencion > 0:
                    res.append({
                        'invoice_tax_line_id': tax_line.id,
                        'tax_line_id': tax_line.tax_id.id,
                        'type': 'tax',
                        'name': 'RET - ' + tax_line.name,
                        'price_unit': -tax_line.amount_retencion,
                        'quantity': 1,
                        'price': -tax_line.amount_retencion,
                        'account_id': tax_line.retencion_account_id.id,
                        'cost_center_id':tax_line.cost_center_id.id,
                        'sector_id':tax_line.sector_id.id,                        
                        'account_analytic_id': tax_line.account_analytic_id.id,
                        'analytic_tag_ids': analytic_tag_ids,
                        'invoice_id': self.id,
                        'tax_ids': [(6, 0, done_taxes)] if tax_line.tax_id.include_base_amount else []
                    })
        return res        
        

    #apiux modify this to direct 
    def _prepare_tax_line_vals(self, line, tax):
        vals = super(AccountInvoice, self)._prepare_tax_line_vals(line, tax)
        vals['cost_center_id']=line.cost_center_id.id
        vals['sector_id']=line.sector_id.id
        return vals




    @api.model
    def _prepare_refund(self, invoice, date_invoice=None,
                        date=None, description=None, journal_id=None,
                        tipo_nota=61, mode='1',sector_id=None,cost_center_id=None):
        values = super(AccountInvoice, self)._prepare_refund(invoice,
                                                             date_invoice,
                                                             date, description,
                                                             journal_id)
        jdc = self.env['account.journal.sii_document_class']
        if invoice.type in ['in_invoice', 'in_refund']:
            dc = self.env['sii.document_class'].search(
                [
                    ('sii_code', '=', tipo_nota),
                ],
                limit=1,
            )
        else:
            jdc = self.env['account.journal.sii_document_class'].search(
                [
                    ('sii_document_class_id.sii_code', '=', tipo_nota),
                    ('journal_id', '=', journal_id),
                ],
                limit=1,
            )
            dc = jdc.sii_document_class_id
        if invoice.type == 'out_invoice' and dc.document_type == 'credit_note':
            type = 'out_refund'
        elif invoice.type in ['out_refund', 'out_invoice']:
            type = 'out_invoice'
        elif invoice.type == 'in_invoice' and dc.document_type == 'credit_note':
            type = 'in_refund'
        elif invoice.type in ['in_refund', 'in_invoice']:
            type = 'in_invoice'
        values.update({
                'document_class_id': dc.id,
                'sector_id':sector_id,
                'cost_center_id':cost_center_id,
                'type': type,
                'journal_document_class_id': jdc.id,
                'referencias':[[0, 0, {
                        'origen': invoice.sii_document_number,
                        'sii_referencia_TpoDocRef': invoice.document_class_id.id,
                        'sii_referencia_CodRef': mode,
                        'motivo': description,
                        'fecha_documento': invoice.date_invoice.strftime("%Y-%m-%d")
                    }]],
            })
        return values

    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None,
               journal_id=None, tipo_nota=61, mode='1'):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(invoice, date_invoice=date_invoice,
                                          date=date, description=description,
                                          journal_id=journal_id,
                                          tipo_nota=tipo_nota, mode=mode,sector_id=invoice.sector_id.id,cost_center_id=invoice.cost_center_id.id)
            refund_invoice = self.create(values)
            invoice_type = {'out_invoice': ('customer invoices credit note'),
                            'out_refund': ('customer invoices debit note'),
                            'in_invoice': ('vendor bill credit note'),
                            'in_refund': ('vendor bill debit note')}
            message = _("This %s has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a><br>Reason: %s") % (invoice_type[invoice.type], invoice.id, invoice.number, description)
            refund_invoice.message_post(body=message)
            new_invoices += refund_invoice
        return new_invoices





class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def _default_sector(self):
        return self._context.get('sector_id') \
            or self.env['account.sector']

    sector_id = fields.Many2one('account.sector', string='Sector',default=_default_sector)

    @api.model
    def move_line_get_item(self, line):
        res = super(account_invoice_line, self).move_line_get_item(line)
        if line.cost_center_id:
            res['cost_center_id'] = line.cost_center_id.id
        if line.sector_id:
            res['sector_id'] = line.sector_id.id            
        return res

        
class account_invoice_tax(models.Model):
    _inherit = 'account.invoice.tax'        
        
        
    @api.model
    def _default_sector(self):
        return self._context.get('sector_id') \
            or self.env['account.sector']        
     
    sector_id = fields.Many2one('account.sector', string='Sector', default=_default_sector)

    @api.model
    def move_line_get(self, invoice_id):
        res = super(account_invoice_tax, self).move_line_get(invoice_id)
        _logger.info("movelineget=%s",res)
        
        invoice=self.env['account.invoice'].browse([invoice_id])
        if invoice and invoice.cost_center_id:
            for tax_line in res:
                tax_line['cost_center_id'] = invoice.cost_center_id.id
        if invoice and invoice.sector_id:
            for tax_line in res:
                tax_line['sector_id'] = invoice.sector_id.id                
        return res        
        

class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""

    _inherit = "account.invoice.refund"




    
    @api.multi
    def compute_refund(self, mode='1'):
        result,refund,inv=super(AccountInvoiceRefund,self).compute_refund(mode)
        refund.sector_id=inv.sector_id
        refund.cost_center_id=inv.cost_center_id
        
        return result,refund,inv
               
   