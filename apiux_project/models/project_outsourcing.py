# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
import logging
from datetime import datetime
from odoo.tools.safe_eval import safe_eval
from functools import reduce
import requests

from odoo.addons import decimal_precision as dp
import collections

_logger = logging.getLogger(__name__)

INVOICE_STATUS = [
    ('proyectado', 'Proyectado'),
    ('pendiente', 'Pendiente'),
    ('facturado', 'Facturado')
]

BOOL = [
    ('si', 'Si'),
    ('no', 'No')
]


MONEY = [
    ('clp', 'CLP'),
    ('uf', 'UF'),
    ('usd', 'USD')
]




class project_outsourcing(models.Model):
    _name='project.outsourcing'
    _description='Project Outsourcing'
    _order = 'sequence asc'

    @api.model
    def _default_currency(self):
        current_user_id=self._context.get('uid')
        current_user=self.env['res.users'].browse([current_user_id])

        #set default currency to UF
        currency_id=self.env['res.currency'].search([('name','=','UF')])
        #raise UserError(_("_default_currency: %s") % (currency_id))
        return currency_id

    @api.depends('unit_price','quantity')
    def _get_amount(self):
        for line in self:
            amount=line.unit_price*line.quantity
            if line.currency_id:
                line.amount=line.currency_id.round(amount or 0.0)

    @api.model
    def _default_company(self):
        current_user_id=self._context.get('uid')
        current_user=self.env['res.users'].browse(current_user_id)
        return current_user.company_id


    @api.onchange('amount')
    def _onchange_amount(self):
        for rec in self:
            rec.amount=round(rec.amount,2)

    @api.depends('task_id.work_ids','user_id') #apiux_sale_note
    def _get_task_hours(self):
        for line in self:
            quantity_real=0
            if line.task_id:
                if line.task_id.work_ids:
                    if line.task_id.work_ids.filtered(lambda r: r.user_id == line.user_id):
                        quantity_real=reduce((lambda x, y: x+y),[i.unit_amount for i in line.task_id.work_ids.filtered(lambda r: r.user_id == line.user_id)])
                    else:
                        quantity_real=0

                    line.quantity_real=quantity_real

    sequence = fields.Integer(help="Gives the sequence of this line when displaying the purchase order.",readonly=True, default=1)
    name=fields.Char('Perfil', required=True)
    project_id=fields.Many2one('project.project', string='Proyecto')
    project_reference=fields.Char(related='project_id.project_reference', string='Referencia Proyecto')
    task_id=fields.Many2one('project.task', string='WBS de Proyecto')
    user_id=fields.Many2one('res.users',string='Nombre')
    currency_id = fields.Many2one('res.currency', string='Moneda',required=True, default=_default_currency, ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Compañia',required=True, default=_default_company, ondelete='restrict')
    period_id =fields.Many2one('account.period', 'Periodo', required=False)
    unit_price=fields.Float('Precio/Hora', digits=dp.get_precision('Product Price'), help='The rate of the currency to the currency of rate 1')
    quantity=fields.Integer('Horas Proyectadas',required=True)
    quantity_real=fields.Float('Horas Acumuladas', compute=_get_task_hours, readonly=True)
    quantity_invoiced=fields.Float('Horas Reales', required=True)
    amount=fields.Monetary('Monto Real', required=True, help='Monto Real in UF')
    state=fields.Selection([('draft','Borrador'),
    ('open','Abierto'),
    ('rejected','Rechazado'),
    ('done','Por Facturar'),
    ('preinvoiced','PreFacturado'),
    ('invoiced','Facturado')], string='Estado', default='draft', required=True)
    invoice_period = fields.Date(string="Fecha Emission")
    document_number = fields.Char(string="Número de documento")
    description=fields.Char('Description WBS', required=True)
    activity_type=fields.Many2one('project.task.activity.type',string='Activity Type',required=True,help='Pleas select an activity type for your tasks')
    projected_amount=fields.Monetary('Monto Proyectado', required=True, help='Monto Proyecctado in UF')
    real_period_id =fields.Many2one('account.period', 'Periodo Real')
    projection_id=fields.Many2one('project.pre.invoice', ondelete='set null',required=False,string='Linea Proyeccion')
    invoice_id=fields.Many2one('account.invoice', 'Factura')
    projected_days = fields.Integer(string="Días Proyectados")

    @api.multi
    def write(self,values):
        for staff in self:
            task=staff.task_id
            task_values={}
            _logger.info("values=%s",values)
            new_name=None
            new_period=None
            new_description=None
            old_name=staff.name
            old_period=staff.period_id
            old_description=staff.description
            new_name=values.get('name',old_name)
            new_period=values.get('period_id',old_period.id)
            new_description=values.get('description',old_description)

            if new_name!=old_name or new_period!=old_period.id or new_description!=old_description:
                new_period_name=self.env['account.period'].browse([new_period]).name
                task_values={'name':('/'.join((new_description or "",new_name or "",new_period_name or "")))}
                task.write(task_values)

            if values.get('activity_type',False):
                task_values['activity_type']=values['activity_type']

            if values.get('user_id',False):
                task.user_id=[6,0,(values['user_id'])]
                if staff.assignment_id:
                    staff.assignment_id.user_id=self.env['res.users'].browse(values['user_id'])

            if values.get('quantity',False):
                task.planned_hours=values['quantity']

        return super(project_outsourcing, self).write(values)

    @api.model
    def create(self, values):
        #Override the original create function for the res.partner model
        record = values

        _logger.info("createps=%s",values)

        #retrieve reviewer id from project responsable
        project=self.env['project.project'].browse([record['project_id']])
        period=self.env['account.period'].browse([record['period_id']])

        if not project.user_id:
            raise exceptions.ValidationError('El Proyecto no tiene responsable. Por favor coloca responsable al Proyecto y intenta nuevamente')

        reviewer_id=project.user_id

        #lets build WBP and add it to record values
        create_task=self.env.context.get('create_task',True)

        if create_task:
            task_obj=self.env['project.task']
            task_values={}


            #create task
            task_values={'name':'/'.join((record['description'],record['name'],period.name)),
                'reviewer_id':reviewer_id.id,
                'planned_hours':record['quantity'],
                'project_id':record['project_id'],
                'activity_type':record['activity_type'],
                'period_id':record['period_id'],
                'outsourcing_state':'draft',
                 }

            try:
                task=task_obj.create(task_values)
            except Exception as e:
                _logger.error("Error in project_outsourcing_create_task, %s,%s",repr(e),task_values)
                raise exceptions.Warning(_('No se puede crear el WBS. Por favor contactese con el Administrador del sistema'))

            if record.get('user_id',False):
                task.user_id=record['user_id']

            record['task_id']=task.id

        
        return super(project_outsourcing, self).create(record)



    @api.multi
    def action_open(self):
        for comm in self:
            comm.write({'state':'open'})

    @api.multi
    def action_done(self):
        for comm in self:
            comm.write({'state':'done'})

    @api.multi
    def action_reject(self):
        for comm in self:
            comm.write({'state':'rejected'})

    @api.multi
    def action_draft(self):
        for comm in self:
            comm.write({'state':'draft'})

    @api.multi
    def action_resend(self):
        for comm in self:
            comm.write({'state':'done','invoice_id':False})

    @api.multi
    def action_multi_send_button(self):
        self.env.ref('__export__.ir_act_server_967').run()

    @api.multi
    def action_multi_send(self):

        _logger.info("outids=%s",self.env.context)
        if self.env.context['active_ids'] and len(self.env.context['active_ids'])>0:
            outsourcing_ids=self.env.context['active_ids']

        #set up defaults using first outsourcing line
        first_line=self.env['project.outsourcing'].browse([outsourcing_ids[0]])

        inv_values={}
        inv_values['company_id']=first_line.company_id.id
        inv_values['project_id']=first_line.project_id.id
        inv_values['partner_id']=first_line.project_id.partner_id.id
        inv_values['currency_id']=first_line.project_id.currency_id.id
        inv_values['emission_date'] = datetime.today()
        inv_values['send_date'] = datetime.today()

        #add outsourcing ids
        line_ids=[]
        sequence=1
        values={}
        for id in outsourcing_ids:
            outsourcing=self.env['project.outsourcing'].browse([id])
            if outsourcing.state!='done':
                    raise exceptions.ValidationError('No se puede agregar lineas que no tiene estado "Por Facturar". Todas las lineas debieren tener este estado')

            values={}
            values['sequence']=sequence
            values['outsourcing_id']=id
            line_ids.append((0,0,values))
            sequence+=1

        inv_values['line_ids']=line_ids

        inv_obj = self.env['project.outsourcing.invoice.wizard']
        inv=inv_obj.create(inv_values)
        cform = self.env.ref('apiux_extra.project_outsourcing_invoice_wizard_form', False)
        action = {
            'type': 'ir.actions.act_window',
            'id':'outsourcing_invoice_wizard_view',
            'name': 'Enviar factura',
            'res_model': 'project.outsourcing.invoice.wizard',
            'src_model': 'project.outsourcing',
            'res_id':inv.id,
            'target':'new',
            'view_id':cform.id,
            'view_mode': 'form',
            'view_type':'form',
            }
        return action

    @api.multi
    def action_send(self): #project.outsourcing
        line_values={}
        line_values['outsourcing_id']=self.id
        #raise models.ValidationError(('line_values: %s' % (line_values)))
        inv_values={}
        inv_values['company_id']=self.company_id.id
        inv_values['project_id']=self.project_id.id
        inv_values['partner_id']=self.project_id.partner_id.id
        inv_values['currency_id']=self.project_id.currency_id.id
        inv_values['emission_date'] = datetime.today()
        inv_values['send_date'] = datetime.today()
        inv_values['money']=self.project_id.currency_id.name.lower()
        inv_values['line_ids']=[(0,0,line_values)]

        #raise models.ValidationError(('inv_values: %s' % (inv_values)))
        inv_obj = self.env['project.outsourcing.invoice.wizard']
        inv=inv_obj.create(inv_values)
        cform = self.env.ref('apiux_extra.project_outsourcing_invoice_wizard_form', False)
        action = {
            'type': 'ir.actions.act_window',
            'id':'outsourcing_invoice_wizard_view',
            'name': 'Enviar factura',
            'res_model': 'project.outsourcing.invoice.wizard',
            'src_model': 'project.outsourcing',
            'res_id':inv.id,
            'target':'new',
            'view_id':cform.id,
            'view_mode': 'form',
            'view_type': 'form',
            }
        return action

class Invoice(models.TransientModel):
    _name = 'project.outsourcing.invoice.wizard'
    _description='Project Outsourcing Invoice Wizard'

    company_id = fields.Many2one('res.company', string="Empresa")
    partner_id = fields.Many2one('res.partner', compute="_get_total", store=True, string="Cliente")
    project_id = fields.Many2one('project.project', compute="_get_total", store=True,string="Proyecto")
    pre_invoice_state = fields.Selection(INVOICE_STATUS, string="Estado", default='pendiente', readonly=True, store=True)
    hes = fields.Char(string="Hes")
    contract = fields.Char(string="Contrato")
    oc = fields.Char(string="OC")
    glosa = fields.Char(string="Glosa", size=100)
    amount = fields.Float(string="Monto neto",compute="_get_total", readonly=True)
    is_tax_exempt = fields.Selection(BOOL, string="¿Excento de iva?", default="no")
    tax = fields.Float(string="Impuesto (%)")
    uf_value = fields.Float(string="Valor uf a la fecha", digits=(10,2))
    dolar_value = fields.Integer(string="Valor dolar a la fecha")
    money = fields.Selection(MONEY, string="Moneda", default="clp", required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda',compute="_get_total", required=True, ondelete='restrict')
    currency_name=fields.Char(related='currency_id.name', string='Moneda')
    clp_id=fields.Many2one('res.currency', string='CLP',readonly=True, default=lambda self: self.env['res.currency'].search([('name','=','CLP')]))
    total_clp = fields.Monetary(string="Monto neto (CLP)", currency_field='clp_id', compute="_get_total", readonly=True)
    emission_date = fields.Date(string="Fecha de emision", store=True)
    send_date = fields.Date(string="Fecha de envio", store=True)
    documents_count = fields.Integer(string="Documentos")
    document_type = fields.Many2one('sii.document_class', string="Tipo de documento")
    document_number = fields.Char(string="Número de documento")
    line_ids=fields.One2many('project.outsourcing.invoice.lines','invoice_id',string='Lineas')
    invoice_id=fields.Many2one('account.invoice', 'Factura')

    @api.multi
    @api.depends('dolar_value', 'uf_value', 'line_ids.line_amount','line_ids.currency_id') #'currency_id',
    def _get_total(self):
        for invoice in self:
            total_clp=0
            temp_clp=0
            total=0
            currency_id=None
            temp_currency_id=None
            project_id=None
            temp_project_id=None
            company_id=None
            temp_company_id=None

            for line in invoice.line_ids:
                temp_currency_id=line.currency_id
                #raise UserError(_("currency_id: %s") % (currency_id))
                if currency_id and currency_id.id!=temp_currency_id.id:
                    raise exceptions.ValidationError('Se incluyieron lineas de Factura con Monedas diferentes. Todas las lineas debieren tener la misma Moneda')

                temp_project_id=line.project_id
                if project_id and project_id.id!=temp_project_id.id:
                    raise exceptions.ValidationError('Se incluyieron lineas de Factura de Proyectos diferentes. Todas las lineas debieren tener el mismo Proyecto')

                temp_company_id=line.company_id
                if company_id and company_id.id!=temp_company_id.id:
                    raise exceptions.ValidationError('Se incluyieron lineas de Factura de Compañias diferentes. Todas las lineas debieren tener la misma Compañias')

                if line.currency_id.name == 'USD':
                    temp_clp = invoice.dolar_value * float(line.line_amount)
                elif line.currency_id.name == 'UF':
                    temp_clp = invoice.uf_value * float(line.line_amount)
                elif line.currency_id.name == 'CLP':
                    temp_clp = float(line.line_amount)

                total_clp+=temp_clp
                total+=line.line_amount
                currency_id=temp_currency_id
                project_id=temp_project_id
                company_id=temp_company_id

            invoice.currency_id=currency_id
            #invoice.company_id=company_id Don't set company due to error in setting default company in lines TBD.
            invoice.project_id=project_id
            invoice.partner_id=project_id.partner_id
            invoice.amount=total
            invoice.total_clp=total_clp

    @api.multi
    def action_send(self):
        self.ensure_one()

        if self.is_tax_exempt=='no' and self.tax==0:
            raise models.ValidationError("Por favor ingresa el valor de impuesto >0")

        default_vals={}
        conf_obj=self.env['ir.config_parameter']
        #default_vals=safe_eval(conf_obj.get_param('default_prefactura_account_product'))
        #if not any(default_vals.values()):
            #raise models.ValidationError("No estan configurados los valores de Cuenta y Producto. Por favor contactése con el Admin del sistema")

        #default_dict=default_vals.get(self.company_id.id, False)
        #if default_dict:
        product_id=False #default_dict.get('product_id',False)
        account_id=False #default_dict.get('account_id',False)
        account_receivable_id=False #default_dict.get('account_receivable_id',False)

        values = {
            'company_id': self.company_id.id,
            'client_id': self.partner_id.id,
            'project_id': self.project_id.id,
            'invoice_account_receivable_id': account_receivable_id or False,
            'invoice_account_id': account_id or False,
            'invoice_product_id': product_id or False,
            'hes': self.hes,
            'contract': self.contract,
            'oc': self.oc,
            'glosa': self.glosa,
            'money':self.money,
            'is_tax_exempt': self.is_tax_exempt,
            'tax': self.tax,
            'currency_id':self.currency_id.id,
            'clp_id':self.clp_id.id,
            'uf_value': self.uf_value,
            'dolar_value': self.dolar_value,
            'total_clp': self.total_clp,
            'emission_date': self.emission_date,
            'send_date': self.send_date,
            'projection_status':'pending',
        }

        #create lines for Prefactura
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
            lvalues['product_id']=product_id
            lvalues['account_id']=account_id

            lines_list.append((0,0,lvalues))
            sequence+=1

        values['line_ids']=lines_list
        res = self.env['account.pre_invoice'].create(values)

        if not res:
            raise AssertionError("No se pudo ingresar la factura.")
        else:
            for line in self.line_ids:
                line.outsourcing_id.write({'state': 'preinvoiced'})

class InvoiceLines(models.TransientModel):
    _name = 'project.outsourcing.invoice.lines'
    _description = 'Project Outsourcing Invoice Lines'

    sequence = fields.Integer(help="Gives the sequence of this line when displaying the purchase order.",readonly=True, default=1)
    invoice_id=fields.Many2one('project.outsourcing.invoice.wizard', string='Pre Factura')
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

class Project(models.Model):
    _inherit='project.project'

    outsourcing_id=fields.One2many('project.outsourcing','project_id', string='Facturacion Outsourcing')


class ProjectTask(models.Model):
    _inherit='project.task'

    @api.multi
    @api.depends('outsourcing_ids.state')
    def _compute_outsourcing_state(self):
        outsourcing_state=False
        for task in self:
            #raise exceptions.ValidationError(_("outsourcing_state: %s\n\noutsourcing_ids: %s") % (task.outsourcing_state, task.outsourcing_state.state))
            outsourcing_state=task.outsourcing_state or 'open'
            _logger.info("posstate=%s",outsourcing_state)
            for lines in task.outsourcing_ids:
                outsourcing_state=lines.state

            _logger.info("osstate=%s",outsourcing_state)
            task.outsourcing_state=outsourcing_state

    outsourcing_ids=fields.One2many('project.outsourcing','task_id', string='Staffing')
    outsourcing_state=fields.Selection([('draft','Borrador'),
    ('open','Abierto'),
    ('rejected','Rechazado'),
    ('done','Por Facturar'),
    ('preinvoiced','PreFacturado'),
    ('invoiced','Facturado')], string='Estado Staffing', default='open', store=True, compute='_compute_outsourcing_state')

    @api.multi
    def unlink(self):
        for record in self:
            if record.work_ids:
                raise exceptions.ValidationError(_("No se puede eliminar un WBS con horas ingresados contra ello!"))
            res= super(ProjectTask, record).unlink()
            
        return res

class ResPartner(models.Model):
    _inherit='res.partner'

    @api.model
    def get_default_resonsibility(self):
        res = self.env['sii.responsability'].search([('code','=','IVARI')])
        return res.id or False

    is_company=fields.Boolean(default=True)
    responsability_id=fields.Many2one(default=get_default_resonsibility)

class CrmSaleNote(models.Model):
    _inherit = 'crm.sale.note'
    
    #some related fields for populating a tab on the sale note

    project_invoice_ids=fields.One2many(related='project_id.projection_id', string="Facturacion")
    projection_currency_id=fields.Many2one(related='project_invoice_ids.currency_id', string='Moneda')
    pre_invoice_state = fields.Selection(related='project_invoice_ids.pre_invoice_state', string="Estado")
    invoice_period = fields.Date(related='project_invoice_ids.invoice_period',string="Fecha")
    amount = fields.Monetary(related='project_invoice_ids.amount',currency_field='projection_currency_id',string="Monto neto")
    document_number = fields.Char(related='project_invoice_ids.document_number',string="Número de documento")
    invoice_id=fields.Many2one(related='project_invoice_ids.invoice_id', string='Factura')
