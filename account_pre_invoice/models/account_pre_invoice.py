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

from odoo.addons.apiux_utils.apiux_utils import call_sbif,call_mindicator


BOOL = [
    ('si', 'Si'),
    ('no', 'No')
]

INVOICE_STATUS = [
    ('projected', 'Proyectado'),
    ('pending', 'Pendiente'),
    ('invoiced', 'Facturado')
]

class AccountPreInvoice(models.Model):
    _name = 'account.pre_invoice'
    _rec_name = 'project_id'

    company_id = fields.Many2one('res.company', string="Empresa")
    client_id = fields.Many2one('res.partner', string="Cliente")
    project_id = fields.Many2one('project.project', string="Proyecto")
    projection_status = fields.Selection(INVOICE_STATUS, string="Estado", default='pending', store=True, readonly=False)      
    
    

    hes = fields.Char(string="Hes")
    contract = fields.Char(string="Contrato")
    oc = fields.Char(string="OC")
    glosa = fields.Char(string="Glosa")
    amount = fields.Float(string="Monto neto")
    tax = fields.Float(string="Impuesto")
    is_tax_exempt = fields.Selection(BOOL, string="¿Excento de iva?")
    uf_value = fields.Float(string="Valor uf a la fecha",digits=(10,2))
    dolar_value = fields.Float(string="Valor dolar a la fecha")
    total_clp = fields.Float(string="Total a facturar", readonly=True)
    emission_date = fields.Date(string="Fecha de emision", store=True)
    document_type = fields.Many2one('sii.document_class', string="Tipo de documento")
    document_number = fields.Char(string="Número de documento")
    document_ids = fields.One2many('ir.attachment', 'id', string="Documentos")
    message_last_post = fields.Datetime()

    #apiux project and note related fields to be implemented later
    
    # note_ids=fields.One2many(related='project_id.nota_ids', string='Nota de Venta')    
    # projection_id = fields.Many2one('project.pre.invoice')  


    invoice_id = fields.Many2one('account.invoice', string="Factura")
    cost_center_id=fields.Many2one('account.cost.center', string='Cost Center')
    sector_id=fields.Many2one('account.sector', string='Sector')

      
    line_ids=fields.One2many('account.pre_invoice.line','preinvoice_id',string='Lineas')
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, ondelete='restrict') 
    currency_name=fields.Char(related='currency_id.name', string='Moneda')
    clp_id=fields.Many2one('res.currency', string='CLP',readonly=True, default=lambda self: self.env['res.currency'].search([('name','=','CLP')]))    
    amount = fields.Monetary(string="Monto neto",currency_field='currency_id',compute="_get_total", store=True,readonly=True) 
    total_clp = fields.Monetary(string="Total a facturar",currency_field='clp_id', compute="_get_total", store=True, readonly=True, digits=(16,2))    
    send_date = fields.Date(string="Fecha de envio", store=True)
    reference = fields.Char(string='SII Reference')


    client_rut=fields.Char(related='client_id.document_number', string='RUT Cliente')
 
    invoice_account_id=fields.Many2one('account.account',string='Cuenta de Ingresos')
    invoice_account_receivable_id=fields.Many2one('account.account',string='Cuenta a cobrar')            
    invoice_product_id=fields.Many2one('product.product', string='Producto')   

      
    
    @api.one
    @api.constrains('invoice_id')
    def _check_unique_constraint(self):
        if self.invoice_id:    
            if len(self.search([('invoice_id', '=', self.invoice_id.id)])) > 1:
                    raise models.ValidationError("Factura ya esta asociada con una PreFactura! Elija otra factura")    
    
    
    @api.onchange('is_tax_exempt')
    def onchange_is_tax_exempt(self):
        if self.is_tax_exempt == 'si':
            self.document_type = self.env['sii.document_class'].search([('id', '=', '55')])
            self.tax = 0.00
        elif self.is_tax_exempt == 'no':
            self.document_type = self.env['sii.document_class'].search([('id', '=', '54')])
            self.tax = 19.00

    @api.onchange('document_number','client_id')
    def onchange_reference(self):
        self.reference = 'FVE_' + (self.document_number or '') + '_' + (self.client_id and self.client_id.name or '')

    @api.onchange('amount','currency_id', 'emission_date')
    def _get_uf(self):

        if self.emission_date:
            uf_value,dolar_value=call_mindicator(self.currency_id.name,self.emission_date)
            if (self.currency_id.name=='USD' and dolar_value==1) or (self.currency_id.name=='UF' and uf_value==1):
                raise models.ValidationError("No se puede obtener tasa de cambio. Intenta nuevamente")

            self.uf_value,self.dolar_value=uf_value,dolar_value   
    
    
    
    @api.onchange('invoice_id')
    def change_invoice(self):
    
        if self.invoice_id:
            self.document_number=self.invoice_id.supplier_invoice_number
            self.document_type=self.invoice_id.journal_document_class_id.sii_document_class_id          
        else:
           self.document_number=None
           self.document_type=None    
    
    
    
    @api.multi
    def finish_invoice(self):
    

        if self.projection_status == 'invoiced':
            raise models.ValidationError("El documento ya se encuentra facturado.")

        if not self.emission_date:
            raise models.ValidationError("Por favor, Ingrese valor Fecha de Emission de Factura.")
            
        if not self.send_date:
            raise models.ValidationError("Por favor, Ingrese Fecha de Envio de Factura para habilitar seguimiento.")            
            
        if not self.document_type:
            raise models.ValidationError("Por favor, Ingrese valor Tipo de Documento (Factura Elec. Exenta/No Exenta).")

        if not self.document_number:
            raise models.ValidationError("Por favor, Ingrese valor Numero Folio Documento SII. Este numero se encuentra en la factura emitida por el SII")

        if not self.reference:
            raise models.ValidationError("Por favor, Ingrese Referencia de la Factura")   
                
        if self.currency_id and self.currency_id.name=='UF':
            if self.uf_value <25000:
                raise models.ValidationError("Por favor, Revisa valor del UF a la fecha. Debiera ser mas de CLP25000")                
                       
        for line in self.line_ids: 
            if not line.product_id:
                raise models.ValidationError("Por favor, Asegurese que todas las lineas de esta Prefactura tienen un Producto.") 


        for line in self.line_ids:
            if not line.account_id:
                raise models.ValidationError("Por favor, Asegurese que todas las lineas tienen Cuenta de Ingresos.")  
                
            
        #checks completed? create invoice   

        invoice=collections.OrderedDict()
        invoice['Header'] = collections.OrderedDict()
        invoice['Lines']= collections.OrderedDict()        
        
        #invoice header
        invoice['Header']['preinvoice_id']=self.id
        invoice['Header']['type']='out_invoice'
        invoice['Header']['state']='draft'             
        invoice['Header']['currency_id']=self.clp_id.id
        invoice['Header']['company_id']=self.company_id.id
        invoice['Header']['user_id']=self.env.user.id                           
        invoice['Header']['partner_id']=self.client_id.id 
        invoice['Header']['payment_term_id']=self.client_id.property_payment_term_id.id
        invoice['Header']['invoice_turn']=self.client_id.acteco_ids and self.client_id.acteco_ids[0].id or None
        invoice['Header']['reference']=' '.join((self.reference or '', self.glosa or ''))
        
        
        #find period...dont want to pick up automatically
        period=self.env['account.period'].search([('company_id','=',self.company_id.id),('date_start','<=',self.emission_date),('date_stop','>=',self.emission_date),('special','=',False)])
        if not period:
            raise exceptions.ValidationError(_('''No hay periodo disponible para este fecha %s y compañia %s! Contactese con el Administrador de sistema!''') % (self.emission_date,self.company_id.name))          

        invoice['Header']['period_id']=period[0].id             
            
            
        if not self.invoice_account_receivable_id:
            raise exceptions.ValidationError(_('''No hay cuenta por cobrar asociada con este Prefactura de cliente %s! Por favor, editar registro y colocar cuenta correcta!''') % (self.client_id.name))   
            
            
        if  self.invoice_account_receivable_id.company_id.id!=self.company_id.id:
            raise exceptions.ValidationError(_('''La cuenta por cobrar de esta Prefactura %s no pertence a la compañia %s! Por favor, editar registro y colocar cuenta correcta!''') % (self.invoice_account_receivable_id.name,self.company_id.name))          
        
            
            
        invoice['Header']['account_id']=self.invoice_account_receivable_id.id
                            
        #document type and number of documents..each file contains 1 document
        

        sii_document_class_id=self.document_type
        responsability_ids=[x.id for x in sii_document_class_id.document_letter_id.receptor_ids]
            
        if self.client_id.responsability_id.id not in responsability_ids:
            raise exceptions.ValidationError(_('''Este cliente no este autorizado a emitir este documento %s! Por favor, revisa el registro de cliente y su responsabilidad SII!''') % (self.document_type.name))
        
        journal_id=self.env['account.journal'].search([('type','=','sale'),('company_id', '=', self.company_id.id),('code','=','VEN')])[0]
        if not journal_id:
            raise exceptions.ValidationError(_('''No hay diario de venta defined para este compañia. Revisa configuracion de diarios en contabilidad!'''))            
        
        account_journal_sii_document_class_id=self.env['account.journal.sii_document_class'].search([('journal_id','=',journal_id.id),('sii_document_class_id','=',sii_document_class_id.id)])
        if not account_journal_sii_document_class_id:   
            raise exceptions.ValidationError(_('''El tipo de documento %s no esta configurado para este diario %s! Revisa configuracion de diarios en contabilidad!''') % (sii_document_class_id.name,journal_id.name))            
                  
                
                
        invoice['Header']['journal_id']=journal_id.id            
        invoice['Header']['journal_document_class_id']=account_journal_sii_document_class_id.id
        
        #project and account
        invoice['Header']['project_id']=self.project_id.id
        invoice['Header']['account_analytic_id']=self.project_id.analytic_account_id.id
        
        #find cost_center from selection


        if not self.project_id.cost_center_id:
            raise exceptions.ValidationError(_('''Proyecto no tiene Centro de Costo asociado!'''))   
        
        invoice['Header']['cost_center_id']=self.cost_center_id.id
        
        
        if not self.project_id.sector_id:
            raise exceptions.ValidationError(_('''Proyecto no tiene Sector asociado!'''))   

        invoice['Header']['sector_id']=self.sector_id.id
        
        
        #Folio number
        try:
            invoice['Header']['sii_document_number']=int(self.document_number)
        except:
            raise exceptions.ValidationError(_('''Numero de documento no es numero entero. Por favor, revisa No. de Documento en Prefactura!'''))            
        
        
        
        #invoice date and due date
            
        invoice['Header']['date_invoice']=self.emission_date            
        invoice['Header']['date_sent']=self.send_date    
 
        #calculate due date from payment term on partner
        
        if not invoice['Header']['payment_term_id']:
            invoice['Header']['due_date']=invoice['Header']['date_invoice']
        else:    
            pterm = self.env['account.payment.term'].browse(invoice['Header']['payment_term_id'])
            pterm_list = pterm.compute(value=1, date_ref=invoice['Header']['date_invoice'])[0]
            if pterm_list:
                invoice['Header']['due_date']=max(tline[0] for tline in pterm_list)
            else:
                raise exceptions.ValidationError(_('''Data insuficiente. Los terminos de pago de este Cliente no tiene lineas!'''))
                                       
        
        invoice_line_ids=[]
        lineNo=1

        #do preinvoice lines
        #we also need to force the period on the invoice 
        #to the latest real_period_id on the prefactura lines
        #with read ahead
        
        forced_period_id=self.line_ids[0].real_period_id
        
        for line in self.line_ids:
            line_id_list=[0,False]

            line_id=collections.OrderedDict()
            line_id['sequence']=lineNo
            line_id['preinvoice_line_id']=line.id            
            line_id['product_id']=line.product_id.id
            line_id['name']=line.product_id.name

            #This field will drive the analitic line when validated
            line_id['analytic_period_id']=line.period_id.id
            
            #Check forced period id against next real_period_id
            if line.real_period_id.date_start>forced_period_id.date_start:
                forced_period_id=line.real_period_id
                    
            line_id['account_id']=line.account_id.id
            line_id['account_analytic_id']=invoice['Header']['account_analytic_id']
            line_id['cost_center_id']=invoice['Header']['cost_center_id']
            line_id['sector_id']=invoice['Header']['sector_id']

            #account_receivables      

            
            #take quantity as 1 so as to calculate taxes correctly
            line_id['quantity']=1
            line_id['price_unit']=line.amount_clp
            line_id['uom_id']=1
            line_id['discount']=0
                
            #add taxes if any to invoice lines.                              
            invoice_line_tax_ids=[tax.id for tax in line.taxes_id]
                                   
            #add all taxes to line object
            line_id['invoice_line_tax_ids']=[(4,id) for id in invoice_line_tax_ids]
                 
            #append individual line to list of lines
            line_id_list.append(line_id)
            invoice_line_ids.append(line_id_list)
       
            lineNo+=1
        #end invoice line processing
        
        invoice['Header']['period_id']=forced_period_id.id
                                
        #create invoice header and lines
        inv_obj=self.env['account.invoice']
        
        #check to see if invoice with folio already exists         
        
        old_invoice=None
        old_invoice=self.env['account.invoice'].search([
            ('sii_document_number','=',invoice['Header']['sii_document_number']),
            ('company_id','=',invoice['Header']['company_id']),
            ('journal_document_class_id','=',invoice['Header']['journal_document_class_id']),
            ('type','=',invoice['Header']['type'])])
        
        if old_invoice:
            raise exceptions.ValidationError(_('''Ya existe Factura con numero de documento %s and tipo %s. Please check original XML !''') % (invoice['Header']['supplier_invoice_number'],invoice['Header']['type']))   

        new_invoice=inv_obj.create({
            'account_id':invoice['Header']['account_id'],       
            'company_id':invoice['Header']['company_id'],
            'partner_id':invoice['Header']['partner_id'],              
            'journal_id':invoice['Header']['journal_id'],
            'invoice_turn':invoice['Header']['invoice_turn'],
            'user_id':invoice['Header']['user_id']})        
              
        

        new_invoice.write({
            'cost_center_id':invoice['Header']['cost_center_id'],
            'sector_id':invoice['Header']['sector_id'],               
            'payment_term_id':invoice['Header']['payment_term_id'],
            'date_invoice':invoice['Header']['date_invoice'],
            'period_id':invoice['Header']['period_id'],            
            'preinvoice_id':invoice['Header']['preinvoice_id'],
            'date_due':invoice['Header']['due_date'],                
            'date_sent':invoice['Header']['date_sent'],                
            'type':invoice['Header']['type'],
            'currency_id':invoice['Header']['currency_id'],
            'project_id':invoice['Header']['project_id'],
            'invoice_line_ids':invoice_line_ids,
            'journal_document_class_id':invoice['Header']['journal_document_class_id'],                                        
            'sii_document_number':invoice['Header']['sii_document_number'],
            'reference':invoice['Header']['reference'],
            'state':invoice['Header']['state']})              
        
        #set document class id
        new_invoice.document_class_id = new_invoice.journal_document_class_id.sii_document_class_id
            
        #compute taxes
        #self.env['account.invoice.tax'].compute(new_invoice)
        new_invoice._onchange_invoice_line_ids()
            
        #confirm invoice if draft invoice and create queue record to send to SII
        if new_invoice.state not in ('draft', 'cancel'):
            raise exceptions.ValidationError(_("Selected invoice(s) cannot be confirmed as they are not in 'Draft' or 'Cancel' state."))
        if new_invoice.state in ('draft'):
            new_invoice.action_invoice_open()
            
        #link invoice with preinvoice    
        self.invoice_id=new_invoice.id
                                                                         
        
        #invoice completed link to projections
        
        self['projection_status'] = 'invoiced'
        for line in self.line_ids:
            if line.outsourcing_id:
                line.outsourcing_id.write({'state': 'invoiced','document_number':new_invoice.sii_document_number,'invoice_id':new_invoice.id})

            elif line.projection_id:
                line.projection_id.write({'state': 'invoiced','document_number':new_invoice.sii_document_number,'invoice_id':new_invoice.id})
            elif line.note_id:
                line.note_id.write({'state': 'invoiced','document_number':new_invoice.sii_document_number,'invoice_id':new_invoice.id}) 
    
    
    @api.multi
    def write(self, values):
        self.ensure_one()
        res = super(AccountPreInvoice, self).write(values)
        # self.projection_id.write({'document_number': self.document_number})
        return res
        

    @api.multi
    @api.depends('dolar_value', 'uf_value', 'line_ids.amount','line_ids.amount_clp','line_ids.currency_id')
    def _get_total(self):
        
        for invoice in self:    
            total_clp=0.0
            temp_clp=0.0            
            total=0.0
            
            
            
            for line in invoice.line_ids:            
                if line.currency_id.name == 'USD':
                    temp_clp = (invoice.dolar_value * line.amount)
                elif line.currency_id.name == 'UF':
                    temp_clp = (invoice.uf_value * line.amount)
                elif line.currency_id.name == 'CLP':
                    temp_clp = float(line.amount)
     
                total_clp+=temp_clp
                total+=line.amount
            
            invoice.amount=total
            invoice.total_clp=total_clp    

            
            
    @api.onchange('company_id')
    def onchange_company(self):
        self.ensure_one()
        for line in self.line_ids:
            line.company_id=self.company_id
            line.product_id=None
            line.account_id=None

        self.invoice_product_id=None
        self.invoice_account_id=None            
             
            
                   
              
            
    @api.onchange('invoice_product_id')
    def onchange_product(self):
        self.ensure_one()
        
        if self.invoice_product_id.property_account_income_id:
            self.invoice_account_id=self.invoice_product_id.property_account_income_id   
        
        for line in self.line_ids:
            line.product_id=self.invoice_product_id
            line.account_id=self.invoice_account_id
            line.company_id=self.company_id 
            if self.is_tax_exempt=='no':
                line.taxes_id=[tax.id for tax in self.invoice_product_id.taxes_id]  
            else:
                self.taxes_id=[(5,_,_)]               
  
    @api.onchange('invoice_account_id')
    def onchange_account(self):
        self.ensure_one()
        for line in self.line_ids:
            line.account_id=self.invoice_account_id
            line.product_id=self.invoice_product_id
            line.company_id=self.company_id
            if self.is_tax_exempt=='no':
                line.taxes_id=[tax.id for tax in self.invoice_product_id.taxes_id]  
            else:
                self.taxes_id=[(5,_,_)]            
      

    @api.onchange('is_tax_exempt')
    def onchange_is_tax_exempt(self):
        self.ensure_one()
        for line in self.line_ids:
            line.account_id=self.invoice_account_id
            line.product_id=self.invoice_product_id
            line.company_id=self.company_id        
            if self.is_tax_exempt=='no':
                line.taxes_id=[tax.id for tax in line.product_id.taxes_id]  
            else:
                line.taxes_id=[(5,_,_)]

        
        
class PreInvoiceLine(models.Model):
    _name='account.pre_invoice.line'

    
    
    @api.onchange('product_id','preinvoice_id.is_tax_exempt','taxes_id')
    def onchange_product(self):
        self.ensure_one()
        
        if self.preinvoice_id.is_tax_exempt=='no':
            self.taxes_id=[tax.id for tax in self.product_id.taxes_id]
            self.account_id=self.product_id.property_account_income_id              
        else:
            self.taxes_id=[(5,_,_)]
            self.account_id=self.product_id.property_account_income_id  
    
    
    
    @api.multi
    @api.depends('preinvoice_id.dolar_value', 'preinvoice_id.uf_value', 'amount')
    def _get_total(self):
        
        for line in self:    

            temp_clp=0            
                      
            if line.currency_id.name == 'USD':
                temp_clp = (line.preinvoice_id.dolar_value * float(line.amount))
            elif line.currency_id.name == 'UF':
                temp_clp = (line.preinvoice_id.uf_value * float(line.amount))
            elif line.currency_id.name == 'CLP':
                temp_clp = float(line.amount)
   
            line.amount_clp=temp_clp      
    

    name=fields.Char('Perfil')
    note_id=fields.Many2one('crm.sale.note', ondelete='restrict',required=False,string='Linea Nota de Venta')
    
    
    preinvoice_id=fields.Many2one('account.pre_invoice', string='PreFactura', ondelete="cascade")
    sequence = fields.Integer(help="Gives the sequence of this line when displaying the purchase order.",readonly=True, default=1)    
    currency_id = fields.Many2one('res.currency', string='Moneda',required=True)
    company_id = fields.Many2one('res.company', string='Compañia',required=True)
    period_id =fields.Many2one('account.period', 'Periodo')
    product_id=fields.Many2one('product.product', string='Producto')
    quantity=fields.Float('Reales./Horas',required=True)
    amount=fields.Monetary('Monto Neto',currency_field='currency_id', required=True, help='Monto en la moneda de la Prefectura')
    clp_id=fields.Many2one(related='preinvoice_id.clp_id',depends=['preinvoice_id.clp_id'], store=True,readonly=True)
    amount_clp=fields.Monetary('Monto Neto (CLP)', currency_field='clp_id', compute="_get_total", store=True, help='Monto Neto en CLP de la Prefectura')

    
    account_id=fields.Many2one('account.account',string='Cuenta de Ingresos')
    taxes_id=fields.Many2many('account.tax', string='Impuestos')


class AccountInvoice(models.Model):
    _inherit='account.invoice'


    def _compute_default_glosa(self):
    
        glosa=""
        if self.id:
            if self.preinvoice_id:
                glosa = 'Hes:'+ (self.preinvoice_id.hes or "N/A") + ', Glosa:'+ (self.preinvoice_id.glosa or "N/A") +', OC:'+ (self.preinvoice_id.oc or "N/A")
            else:
                glosa=self.reference
                
        else:        
            glosa=self.reference
            
        _logger.info("glosa=%s",glosa)
        return glosa  


    @api.one
    @api.depends('reference', 'preinvoice_id')        
    def _compute_glosa(self):
    
        glosa=""
        if self.preinvoice_id:
            glosa = 'Hes:'+ (self.preinvoice_id.hes or "N/A") 
            glosa += ', Glosa:'+ (self.preinvoice_id.glosa or "N/A")
            glosa += ', OC:'+ (self.preinvoice_id.oc or "N/A")
        else:
            glosa=self.reference
     
        
        self.invoice_glossary =glosa  

    project_id=fields.Many2one('project.project', string='Project')
    preinvoice_id=fields.Many2one('account.pre_invoice', string='PreFactura', ondelete='restrict')
    company_rut=fields.Char(related='company_id.vat', string='RUT Proveedor')
    partner_rut=fields.Char(related='partner_id.document_number', string='RUT Cliente')
    invoice_glossary=fields.Char(default=_compute_default_glosa, compute="_compute_glosa", string="Glosa", store=True)
    document_type=fields.Integer(related='journal_document_class_id.sii_document_class_id.sii_code', string='Tipo')
    dso=fields.Integer(string="DSO")
    
    
    @api.onchange('project_id')
    def onchange_project_id(self):   
        self.sector_id=self.project_id.sector_id
        self.cost_center_id=self.project_id.cost_center_id
    
    
class AccountInvoiceLine(models.Model):
    _inherit='account.invoice.line'

    analytic_period_id=fields.Many2one('account.period', string='Periodo Analitico')
    
    
class AccountMoveLine(models.Model):
    _inherit='account.move.line'

    analytic_period_id=fields.Many2one('account.period', string='Periodo Analitico')    
    