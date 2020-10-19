# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
import logging
import string as str
from datetime import datetime
from odoo.tools.safe_eval import safe_eval
from odoo.addons import decimal_precision as dp
from odoo import exceptions
import collections
import requests
from odoo.addons.apiux_utils.apiux_utils import call_sbif,call_mindicator


_logger = logging.getLogger(__name__)

INVOICE_STATUS = [
    ('proyectado', 'Proyectado'),
    ('pendiente', 'Pendiente'),
    ('devengado', 'Devengado'),
    ('facturado', 'Facturado')
]

BOOL = [
    ('si', 'Si'),
    ('no', 'No')
]




class AccountAnalyticLine(models.Model):
    _inherit='account.analytic.line'

    projection_id=fields.Many2one('project.pre.invoice',string='Proyeccion')



class InvoiceAccrued(models.TransientModel):
    _name = 'project.accrued.invoice.wizard'

    @api.onchange('emission_date')
    def _get_uf(self):

        uf_value=0.0
        dolar_value=0.0

        if self.emission_date:           
            uf_value,dolar_value=call_mindicator('UF',self.emission_date)
            if (uf_value==1):
                raise models.ValidationError("No se puede obtener tasa de cambio. Intenta nuevamente")
                
        self.uf_value=uf_value

    def _get_default_uf(self):
    
        uf_value=0.0
        dolar_value=0.0

        if self.emission_date:           
            uf_value,dolar_value=call_mindicator('UF',self.emission_date)
            if (uf_value==1):
                raise models.ValidationError("No se puede obtener tasa de cambio. Intenta nuevamente")

        return uf_value

    @api.multi
    @api.depends('currency_id','emission_date')
    def onchange_currency(self):
        for rec in self:
            if rec.emission_date:   
            
                uf_value=0.0
                dolar_value=0.0
                        
                uf_value,dolar_value=call_mindicator(rec.currency_id.name,rec.emission_date)
                rec.uf_value,rec.dolar_value=uf_value,dolar_value



    company_id = fields.Many2one('res.company', string="Empresa")
    partner_id = fields.Many2one('res.partner',  string="Cliente")
    project_id = fields.Many2one('project.project', string="Proyecto")
    pre_invoice_state = fields.Selection(INVOICE_STATUS, string="Estado", default='pendiente', readonly=True, store=True)
    hes = fields.Char(string="Hes")
    contract = fields.Char(string="Contrato")
    oc = fields.Char(string="OC")
    glosa = fields.Char(string="Glosa", size=100)
    amount = fields.Monetary(string="Monto neto", currency_field='currency_id')
    is_tax_exempt = fields.Selection(BOOL, string="¿Excento de iva?", default="no")
    tax = fields.Float(string="Impuesto (%)")
    uf_value = fields.Float(string="Valor uf a la fecha", digits=(10,2),compute=onchange_currency)
    dolar_value = fields.Integer(string="Valor dolar a la fecha")
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, ondelete='restrict')
    currency_name=fields.Char(related='currency_id.name', string='Moneda')
    clp_id=fields.Many2one('res.currency', string='CLP',readonly=True, default=lambda self: self.env['res.currency'].search([('name','=','CLP')]))
    total_clp = fields.Monetary(string="Monto neto (CLP)", compute="_get_total", readonly=True, currency_field='currency_id')
    emission_date = fields.Date(string="Fecha de emision", store=True)
    send_date = fields.Date(string="Fecha de envio", store=True)
    #document_ids = fields.One2many('ir.attachment', 'invoice_id', string="Documentos")
    documents_count = fields.Integer(string="Documentos")
    document_type = fields.Many2one('sii.document_class', string="Tipo de documento")
    document_number = fields.Char(string="Número de documento")
    invoice_account_id=fields.Many2one('account.account',string='Cuenta de Ingresos')
    invoice_account_receivable_id=fields.Many2one('account.account',string='Cuenta a cobrar')
    invoice_product_id=fields.Many2one('product.product', string='Producto')
    journal_id =fields.Many2one('account.analytic.journal', string='Diario Analitico')
    projection_id=fields.Many2one('project.pre.invoice', string="Pre-Factura")

    @api.multi
    @api.depends('currency_id', 'dolar_value', 'uf_value', 'amount')
    def _get_total(self):
        for invoice in self:
            temp_clp=0
            currency_id=invoice.currency_id
            if currency_id.name == 'USD':
                temp_clp = invoice.dolar_value * float(invoice.amount)
            elif currency_id.name == 'UF':
                temp_clp = invoice.uf_value * float(invoice.amount)
            elif currency_id.name == 'CLP':
                temp_clp = float(invoice.amount)
            invoice.total_clp=temp_clp

    @api.multi
    def action_send(self):
        values={}
        #if projection is already accrued, remove and recreate
        if self.projection_id.is_preaccrued and self.projection_id.preaccrued_id:
            self.projection_id.preaccrued_id.unlink()
        #OK setup values and create new analytic line. Used to represent changes in the pre_accrued record.

        values['name']=self.invoice_product_id.name
        values['product_id']=self.invoice_product_id.id
        values['journal_id']=self.journal_id.id
        values['account_id']=self.project_id.analytic_account_id.id
        values['general_account_id']=self.invoice_account_id.id
        values['ref']=self.glosa
        values['unit_amount']=1.0
        values['amount']=self.total_clp
        values['projection_id']=self.projection_id.id
        values['user_id']=self.env.uid
        values['company_id']=self.company_id.id
        values['date']=self.emission_date
        try:
            analytic_line=self.env['account.analytic.line'].create(values)
            self.projection_id.preaccrued_id=analytic_line

        except Exception as e:
            _logger.info("Error en account.pre_accrued.finish_accrued %s",str(e))
            raise models.ValidationError("No se puede crear el registro analitico Devengado! Por favor. contactése con el Admin del sistema")



class ProjectPreInvoice(models.Model):
    _inherit='project.pre.invoice'
    _order='invoice_period desc'

    @api.depends('preaccrued_id')
    def _compute_accrued(self):
        for rec in self:
            if rec.preaccrued_id:
                rec.is_preaccrued=True
                rec.link_preaccrued_id=rec.preaccrued_id[0]
                rec.preaccrued_amount=rec.preaccrued_id[0].amount
            else:
                rec.is_preaccrued=False
                rec.link_preaccrued_id=False
                rec.preaccrued_amount=0.0

    preaccrued_id=fields.One2many('account.analytic.line','projection_id',string='Linea Devengado')
    is_preaccrued=fields.Boolean(default=False,compute=_compute_accrued,string='Devengado?', store=True)
    link_preaccrued_id=fields.Many2one('account.analytic.line',compute=_compute_accrued,string='Linea Devengado')
    project_reference=fields.Char(related='project_id.project_reference', string='Ref.')
    preaccrued_amount=fields.Float(compute=_compute_accrued, string='Monto Devengado', digits=(10,2))
    preaccrued_amount_history=fields.Float(string='Hist Preaccrued', digits=(10,2), default=0)
    
    @api.multi
    def refresh_accrued_account_invoiced_milestone(self):
        #with prefacturas of type 'milestone' we only have to unlink the analytic record
        for rec in self:
            if rec.invoice_type=='milestone' and rec.preaccrued_id and rec.invoice_id:
                rec.preaccrued_amount_history=rec.preaccrued_amount
                rec.preaccrued_id.unlink()

    @api.multi
    def remove_preaccrued(self):
        for rec in self:
            rec.preaccrued_amount_history=rec.preaccrued_amount        
            rec.preaccrued_id.unlink()

    @api.multi
    def send_preaccrued(self):
        default_vals={}
        conf_obj=self.env['ir.config_parameter']
        default_vals=safe_eval(conf_obj.get_param('default_prefactura_account_product'))
        if not any(default_vals.values()):
            raise models.ValidationError("No estan configurados los valores por defecto de Cuenta y Producto de inea Analitica. Por favor contactése con el Admin del sistema")
        #We need to check that at least one of the lines has not been invoiced, if type is Staffing
        for rec in self:
            accrued_total=0
            all_invoiced=True

            if rec.invoice_type=='t&m':
                outsourcing_ids=rec.outsourcing_ids
                if outsourcing_ids:
                    for outsourcing in outsourcing_ids:
                        if not outsourcing.invoice_id:
                            all_invoiced=False
                            accrued_total+=outsourcing.projected_amount

                if accrued_total==0:
                    accrued_total=rec.projected_amount

                if all_invoiced:
                    raise models.ValidationError("Todas las lineas de Staffing ya han sido facturado. Solo se puede devengar lineas no facturadas!")

            else:
                if not rec.invoice_id:
                    accrued_total+=rec.projected_amount
                    all_invoiced=False

                if all_invoiced:
                    raise models.ValidationError("Ya ha sido facturado. Solo se puede devengar lineas no facturadas!")

            default_dict=default_vals.get(rec.company_id.id, False)
            if default_dict:
                product_id=default_dict.get('product_id',False)
                account_id=default_dict.get('account_id',False)
                account_receivable_id=default_dict.get('account_receivable_id',False)

            default_journal=rec.env['account.analytic.journal'].sudo().search([('code','=','DEV'),('company_id','=',rec.company_id.id)])
            currency_id=rec.env['res.currency'].search([('name','=',rec.money.upper())])
            inv_values={}
            inv_values['projection_id']=rec.id
            inv_values['company_id']=rec.project_id.company_id.id
            inv_values['project_id']=rec.project_id.id
            inv_values['partner_id']=rec.project_id.partner_id.id
            inv_values['currency_id']=currency_id.id
            inv_values['emission_date'] = rec.invoice_period
            inv_values['money']=currency_id.name.lower()
            inv_values['amount']=accrued_total
            inv_values['journal_id']=default_journal[0].id
            inv_values['invoice_account_receivable_id']=account_receivable_id or False
            inv_values['invoice_account_id']=account_id or False
            inv_values['invoice_product_id']=product_id or False
            inv_obj = rec.env['project.accrued.invoice.wizard']
            inv=inv_obj.create(inv_values)
            cform = rec.env.ref('apiux_booking.project_accrued_invoice_wizard_form', False)
            action = {
                'type': 'ir.actions.act_window',
                'id':'project_accrued_invoice_wizard_view',
                'name': 'Enviar Devengado',
                'res_model': 'project.accrued.invoice.wizard',
                'src_model': 'project.pre.invoice',
                'res_id':inv.id,
                'target':'new',
                'view_id':cform.id,
                'view_mode': 'form',
                'view_type':'form',
                }
            return action
