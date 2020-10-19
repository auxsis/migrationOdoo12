# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, exceptions
import datetime
import logging
import requests
from odoo.tools.safe_eval import safe_eval
from odoo.addons.apiux_utils.apiux_utils import call_sbif,call_mindicator

_logger = logging.getLogger(__name__)


MONEY = [
    ('clp', 'CLP'),
    ('uf', 'UF'),
    ('usd', 'USD')
]

BOOL = [
    ('si', 'Si'),
    ('no', 'No')
]

INVOICE_STATUS = [
    ('proyectado', 'Proyectado'),
    ('pendiente', 'Pendiente'),
    ('facturado', 'Facturado')
]

class ProjectPreInvoice(models.Model):
    _name = 'project.pre.invoice'
    _description = 'Project Pre Invoice'
    _order = 'invoice_period asc'
    _rec_name='preinvoice_name'


    #add a couple of fields
    @api.multi
    @api.depends('invoice_type','outsourcing_ids.amount')

    def _compute_amount(self):
        for record in self:
            if record.invoice_type=='t&m':
                record.amount=sum([x.amount for x in record.outsourcing_ids])

    @api.depends("outsourcing_ids")
    @api.multi
    def _compute_num_outsourcing(self):
        for rec in self:
            rec.num_outsourcing=len(rec.outsourcing_ids)>0
            
            
    @api.multi
    def _compute_preinvoice_name(self):
        for rec in self:
            rec.preinvoice_name='-'.join((rec.project_id.project_reference  and rec.project_id.project_reference or "" ,rec.period_id and rec.period_id.name or ""))

    preinvoice_name=fields.Char('Name', compute="_compute_preinvoice_name")
    invoice_type=fields.Selection([('milestone','Hito'),('t&m','Staffing')], default='milestone', string='Tipo')
    period_id=fields.Many2one('account.period', String='Periodo')
    company_id=fields.Many2one(related='project_id.company_id', string='Compañia')
    currency_id=fields.Many2one('res.currency',string='Moneda')
    amount=fields.Monetary(compute='_compute_amount', store=True)
    projected_amount=fields.Monetary(string='Monto Proyectado', digits=(10,2))    
    num_outsourcing=fields.Boolean(compute="_compute_num_outsourcing", string="Cant. Staffing")
    project_id = fields.Many2one('project.project')
    pre_invoice_state = fields.Selection(INVOICE_STATUS, string="Estado", default="proyectado", readonly="True", store=True)
    invoice_period = fields.Date(string="Fecha", required=True)
    money = fields.Selection(MONEY, string="Tipo moneda", default="uf", required=True)
    document_number = fields.Char(string="Número de documento")
    entry_date = fields.Date(string="Fecha Ingreso")
    state=fields.Selection([('draft','Borrador'),('open','Abierto'),('rejected','Rechazado'),('done','Por Facturar'),('preinvoiced','PreFacturado'),('invoiced','Facturado')], string='Estado', default='draft', required=True)
    outsourcing_ids=fields.One2many('project.outsourcing','projection_id', string='Staffing')
    invoice_id=fields.Many2one('account.invoice', 'Factura')
   

    @api.multi
    def send_preinvoice(self):
        sequence=1
        order_lines = []
        for line in self.outsourcing_ids:
            order_lines.append((0, 0, {
                'sequence': sequence,
                'outsourcing_id': line.id,
            }))
            sequence+=1
            
        last_sale_note=None
        sale_notes=self.project_id.nota_ids.sorted(key=lambda r:r.create_date, reverse=True)
        if sales_notes:
            last_sale_note=sales_notes[0]
            

        currency_id=self.env['res.currency'].search([('name','=',self.money.upper())])
        inv_values={}
        inv_values['projection_id']=self.id
        inv_values['company_id']=self.project_id.company_id.id
        inv_values['project_id']=self.project_id.id
        inv_values['client_id']=self.project_id.partner_id.id
        inv_values['currency_id']=currency_id.id
        inv_values['emission_date'] = fields.Date.today()
        inv_values['entry_date'] = self.entry_date
        inv_values['money']=currency_id.name.lower()
        inv_values['amount']=self.amount
        inv_values['OC']=last_sale_note and last_sale_note.purchase_order or None
        inv_values['line_ids']=order_lines


        inv_obj = self.env['project.invoice.wizard']
        inv=inv_obj.create(inv_values)

        cform = self.env.ref('apiux_project.project_invoice_wizard_form', False)
        action = {
            'type': 'ir.actions.act_window',
            'id':'invoice_wizard_view',
            'name': 'Enviar factura',
            'res_model': 'project.invoice.wizard',
            'src_model': 'project.pre.invoice',
            'res_id':inv.id,
            'target':'new',
            'view_id':cform.id,
            'view_mode': 'form',
            'view_type':'form',
            }
        return action





class project_project(models.Model):
    _inherit = 'project.project'


    def _default_amount_pending(self):
        for project in self:
            amount=0
            for pr in project.projection_id:
                if pr.pre_invoice_state=='pendiente':
                    amount+=pr.amount
            return amount

    def _default_amount_projected(self):
        for project in self:
            amount=0
            for pr in project.projection_id:
                if pr.pre_invoice_state=='proyectado':
                    amount+=pr.amount
            return amount


    def _default_amount_invoiced(self):
        for project in self:
            amount=0
            for pr in project.projection_id:
                if pr.pre_invoice_state=='facturado':
                    amount+=pr.amount
            return amount

    def _default_amount_total(self):
        for project in self:
            amount=0
            for pr in project.projection_id:
                amount+=pr.amount
            return amount

    def _default_sales_value(self):
        sales_value=0
        for project in self:
            sales_value=project.nota_ids and project.nota_ids[0].price or 0
        return sales_value

    projection_id = fields.One2many('project.pre.invoice', 'project_id')
    sales_value=fields.Monetary('Monto Nota de Venta',currency_field='invoice_money',default=_default_sales_value,compute='_compute_amount_sales',store=True) 
    invoice_money = fields.Many2one('res.currency', string="Fact. Moneda", store=True)    
    invoice_pending=fields.Monetary('Fact. Pendiente', currency_field='invoice_money', default=_default_amount_pending,compute='_compute_amount_pending')
    invoice_projected=fields.Monetary('Fact. Proyectado',currency_field='invoice_money',default=_default_amount_projected, compute='_compute_amount_pending')
    invoice_invoiced=fields.Monetary('Fact. Facturado', currency_field='invoice_money',default=_default_amount_invoiced,compute='_compute_amount_pending')
    invoice_total=fields.Monetary('Fact. Total', currency_field='invoice_money', default=_default_amount_total,compute='_compute_amount_pending', store=True)


    @api.multi
    @api.depends('nota_ids')
    def _compute_amount_sales(self):
        price=0
        for project in self:
            for line in project.nota_ids:
                price+=line.price or 0
            project.sales_value=price


    @api.depends('projection_id.money','projection_id')
    def _compute_money(self):
        for project in self:
            money=None
            for pr in project.projection_id:
                project.invoice_money=pr.currency_id

    @api.depends('projection_id.pre_invoice_state','projection_id.amount','projection_id')
    def _compute_amount_pending(self):
        for project in self:
            amount_pending=0
            amount_projected=0
            amount_invoiced=0
            amount_total=0

            for pr in project.projection_id:
                #raise models.ValidationError("monto: "+str(pr.pre_invoice_state))
                if pr.state=='preinvoiced':
                    amount_pending+=pr.amount
                if pr.state=='draft':
                    amount_projected+=pr.amount
                if pr.state=='invoiced':
                    amount_invoiced+=pr.amount

                amount_total+=pr.amount

            project.invoice_pending=amount_pending
            project.invoice_projected=amount_projected
            project.invoice_invoiced=amount_invoiced
            project.invoice_total=amount_total



    @api.onchange('unit_id')
    def _onchange_unit_id(self):
        acc_obj=self.env["account.cost.center"]
        acc=None
        if self.unit_id:
            acc=acc_obj.search([('code','=', self.unit_id.replace('-','').upper())])
            if acc:
                self.project_activities_ids=[(6,_, [x.cost_center_activity_id.id for x in acc])]


    @api.multi
    @api.depends('nota_ids')
    def compute_hours_sold(self):
        hours_sold=0
        for line in self:
            for nota in line.nota_ids:
                for order_line in nota.order_line_quotation:
                    hours_sold+=order_line.product_uom_qty
                    #raise models.ValidationError('self: '+str(order_line))
        self.total_hours_sold=hours_sold

    @api.multi
    @api.depends('nota_ids','task_ids')
    def compute_hours_projected(self):
        hours_projected=0
        for line in self:
            for task in line.task_ids:
                hours_projected+=task.planned_hours
        self.total_hours_projected=hours_projected

    @api.multi
    @api.depends('nota_ids','task_ids')
    def compute_hours_registered(self):
        hours_registered=0
        for line in self:
            for task in line.task_ids:
                for work in task.work_ids:
                    hours_registered+=work.unit_amount
        self.total_hours_registered=hours_registered

class ProjectOutsourcing(models.Model):
    _inherit='project.outsourcing'
    
    @api.onchange('real_period_id')
    def onchange_real_period_id(self):

        #get projection_ids of project and filter
        
        available_projections=self.project_id.projection_id.filtered(lambda r: r.state not in ['preinvoiced','invoiced'] and r.period_id==self.real_period_id)
        _logger.info("availproj=%s",available_projections)
        if not available_projections:
            raise models.ValidationError("There are no Projections available for this Period. Please select another period")
        
        else:
            self.projection_id=available_projections[0]
            




class InvoiceAttachment(models.Model):
    _inherit = 'ir.attachment'
    invoice_id = fields.Many2one('project.pre.invoice')

class ProjectInvoiceWizard(models.TransientModel):
    _name = 'project.invoice.wizard'
    _description = 'Project Invoice Wizard'

    @api.multi
    @api.depends('money','currency_id', 'dolar_value', 'uf_value', 'amount')
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


    company_id = fields.Many2one('res.company', string="Empresa")
    client_id = fields.Many2one('res.partner', string="Cliente")
    project_id = fields.Many2one('project.project', string="Proyecto", readonly=True)
    projection_id = fields.Many2one('project.pre.invoice', store=True)
    pre_invoice_state = fields.Selection(INVOICE_STATUS, string="Estado", default='pendiente', readonly=True, store=True)
    hes = fields.Char(string="Hes")
    contract = fields.Char(string="Contrato")
    oc = fields.Char(string="OC")
    glosa = fields.Char(string="Glosa")
    is_tax_exempt = fields.Selection(BOOL, string="¿Excento de iva?", default="si")
    tax = fields.Float(string="Impuesto (%)")
    emission_date = fields.Date(string="Fecha de ingreso", store=True)

    documents_count = fields.Integer(string="Documentos")
    document_type = fields.Many2one('sii.document_class', string="Tipo de documento")
    document_number = fields.Char(string="Número de documento")

    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, ondelete='restrict')
    currency_name=fields.Char(related='currency_id.name', string='Moneda')
    clp_id=fields.Many2one('res.currency', string='CLP',readonly=True, default=lambda self: self.env['res.currency'].search([('name','=','CLP')]))
    amount = fields.Float(string="Monto neto (Moneda)")
    uf_value = fields.Float(string="Valor uf a la fecha",compute='onchange_currency')
    dolar_value = fields.Integer(string="Valor dolar a la fecha",compute='onchange_currency')
    money = fields.Selection(MONEY, string="Moneda", default="uf", required=True)
    total_clp = fields.Integer(string="Total a facturar", compute="_get_total", readonly=True) 
    
    entry_date = fields.Date(string="Fecha Ingreso")
    line_ids=fields.One2many('project.invoice.wizard.lines','invoice_id',string='Lineas')

    @api.multi
    @api.depends('currency_id','emission_date')
    def onchange_currency(self):
        for rec in self:
            if rec.emission_date:   
            
                uf_value,dolar_value=call_mindicator(rec.currency_id.name,rec.emission_date)

                if (rec.currency_id.name=='USD' and dolar_value==1) or (rec.currency_id.name=='UF' and uf_value==1):
                    raise models.ValidationError("No se puede obtener tasa de cambio. Intenta nuevamente")

                rec.uf_value,rec.dolar_value=uf_value,dolar_value
    
    
    #Create account.pre.invoice from project projections
    #This function calls a pop-up form from which details can be checked prior 
    #to sending preinvoice to finance
    @api.multi
    def send_invoice(self):
        self.ensure_one()
        if self.is_tax_exempt=='no' and self.tax==0:
            raise models.ValidationError("Por favor ingresa el valor de impuesto >0")

        #default_currency=self.env['res.currency'].search([('name','=',self.money.upper())])
        default_clp=self.env['res.currency'].search([('name','=','CLP')])


        #we need to find default values for account and account receivable
        pre_acc_obj=self.env['project.pre.invoice.account']
        pre_acc_inst=pre_acc_obj.sudo().search([('company_id','=',self.company_id.id),
                                                ('sector_id','=',self.project_id.sector_id.id),
                                                ('cost_center_id','=',self.project_id.cost_center_id.id)])

        if not pre_acc_inst:
            raise models.ValidationError(_("Default values for Account and Account Receivable cannot be found! Please contact the System Adminstrator."))

        #arm values for pre invoice and lines

        values = {
            'company_id': self.company_id.id,
            'client_id': self.client_id.id,
            'project_id': self.project_id.id,
            'sector_id': self.project_id.sector_id.id,
            'cost_center_id': self.project_id.cost_center_id.id,            
            'invoice_account_receivable_id':pre_acc_inst.account_receivable_id.id,
            'invoice_account_id':pre_acc_inst.account_income_id.id,
            'hes': self.hes,
            'contract': self.contract,
            'oc': self.oc,
            'glosa': self.glosa,
            'money':self.money,
            'is_tax_exempt': self.is_tax_exempt,
            'tax': self.tax,
            'currency_id':self.currency_id.id,
            'clp_id':default_clp.id,
            'uf_value': self.uf_value,
            'dolar_value': self.dolar_value,
            'total_clp': self.total_clp,
            'emission_date': self.emission_date,
            'send_date': self.emission_date,
            'projection_status':'pending',
        }

        lines_list=[]
        lvalues={}
        sequence=1
        for line in self.line_ids:
            lvalues={}

            temp_clp=0
            #here we need to calculate the amounts
            if self.currency_id.name == 'USD':
                temp_clp = round(self.dolar_value * float(line.line_amount))
            elif self.currency_id.name == 'UF':
                temp_clp = round(self.uf_value * float(line.line_amount))
            elif self.currency_id.name == 'CLP':
                temp_clp = float(line.line_amount)

            lvalues['sequence']=sequence
            lvalues['name']=line.outsourcing_id.name
            lvalues['outsourcing_id']=line.outsourcing_id.id
            lvalues['currency_id']=line.currency_id.id
            lvalues['company_id']=line.company_id.id
            lvalues['period_id']=line.period_id.id
            lvalues['quantity']=line.quantity
            lvalues['amount']=line.line_amount
            lvalues['amount_clp']=temp_clp
            lvalues['product_id']=line.product_id.id
            lvalues['account_id']=pre_acc_inst.account_income_id.id

            lines_list.append((0,0,lvalues))
            sequence+=1
        values['line_ids']=lines_list
        res = self.env['account.pre_invoice'].create(values)

        if not res:
            raise AssertionError("No se pudo ingresar la factura.")
        else:
            self.projection_id.write({'state': 'preinvoiced'})

class InvoiceLines(models.TransientModel):
    _name = 'project.invoice.wizard.lines'
    _description = 'Project Invoice Wizard Lines'

    sequence = fields.Integer(help="Gives the sequence of this line when displaying the purchase order.",readonly=True, default=1)
    invoice_id=fields.Many2one('project.invoice.wizard', string='Pre Factura')
    id_out=fields.Integer(string="ID")
    outsourcing_id=fields.Many2one('project.outsourcing','Outsourcing')
    note_id=fields.Many2one('crm.sale.note', 'Nota de Venta')
    task_id=fields.Many2one(related='outsourcing_id.task_id', string='WBS de Proyecto')
    project_id=fields.Many2one(related='outsourcing_id.project_id', string='Proyecto')
    user_id=fields.Many2one(related='outsourcing_id.user_id',string='Nombre')
    currency_id = fields.Many2one(related='outsourcing_id.currency_id', string='Moneda')
    company_id = fields.Many2one(related='outsourcing_id.company_id', string='Compañia')
    period_id =fields.Many2one(related='outsourcing_id.period_id', string='Periodo')
    quantity=fields.Float(related='outsourcing_id.quantity_invoiced', string='Reales./Horas')
    line_amount=fields.Monetary(related='outsourcing_id.amount',string='Monto Real')
  
    
    
class InvoiceAttachment(models.Model):
    _inherit = 'ir.attachment'
    invoice_id = fields.Many2one('project.pre_invoice')    
