from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
import requests
from datetime import datetime
import logging

from odoo.addons.apiux_utils.apiux_utils import call_sbif,call_mindicator

_logger = logging.getLogger(__name__)

class sale_order_quotation(models.Model):
    _inherit = "sale.order"

    sector_id = fields.Many2one('account.sector', string='Sector', required=True)
    cost_center_id = fields.Many2one('account.cost.center', string='Cost Center', required=True)    
    type_service = fields.Many2one('sale.order.service.type', string="Tipo de Servicio", required=False)
    type_sale=fields.Many2one('uom.uom', string='Tipo de Venta')
    oportunity = fields.Char(string="Oportunidad", required=True)
    compute_margin_sim = fields.Float(string="Margen Simulación %")
    final_price = fields.Monetary(string="Precio Final", readonly=True, compute='compute_final_price')
    final_cost = fields.Monetary(string="Costo Final", readonly=True, compute='compute_final_cost')
    margin = fields.Monetary(string="Margen", compute='compute_margin_quotation')
    porc_margin = fields.Float(string="% Margen", compute='compute_margin_quotation')
    sale_cost_line_id = fields.One2many('sale.cost.line', 'sale_order_id', string='Sale Cost Line')
    crm_sale_note_id=fields.Many2one('crm.sale.note',string="Sale Note")
    project_id = fields.Many2one('project.project',string='Project')
    emission_date = fields.Date(string="Fecha Emision", default=fields.Date.today(), required=True)
    currency_quotation = fields.Many2one('res.currency', string='Moneda', required=False)
    currency_quotation_name = fields.Char(related='currency_id.name',string='Nombre Moneda')
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=False, required=True)    
    uf_value = fields.Float(string="Valor UF", readonly=True, compute='_get_values', store=True)
    dolar_value = fields.Float(string="Valor Dolar", readonly=True, compute='_get_values', store=True)

    @api.depends('currency_id','emission_date')
    def _get_values(self):
        for rec in self:
            if rec.emission_date:
            
                currency_name=rec.currency_id.name
                if currency_name=='CLP':
                    currency_name='UF'
                elif currency_name=='UF':
                    currency_name='CLP'                    
            
                uf_value,dolar_value=call_mindicator(currency_name,rec.emission_date)
                if (currency_name=='USD' and dolar_value==1) or (currency_name=='UF' and uf_value==1):
                    raise models.ValidationError("No se puede obtener tasa de cambio. Intenta nuevamente")

                rec.uf_value,rec.dolar_value=uf_value,dolar_value

    @api.multi
    @api.onchange('order_line','type_service')
    def compute_type_margin(self):
        margen=self.type_service.margin
        riesgo=self.type_service.risk

        if self.compute_margin_sim!=0:
            margen=self.compute_margin_sim

        for line in self.order_line:
            line.update({
                'margin': margen,
                'risk': riesgo,
            })

        for line in self.sale_cost_line_id:
            line.update({
                'risk': riesgo,
            })

        for line2 in self.sale_cost_line_id:
            line2.compute_change_product_id()

    @api.multi
    @api.onchange('type_service')
    def compute_set_margin_sim(self):
        self.update({
            'compute_margin_sim': 0,
        })

    @api.depends('order_line.price')
    def compute_final_price(self):
        total=0
        for order in self.order_line:
            total+=order.price
        _logger.info("logsale2=%s", total)            
        self.update({
            'final_price': total,
        })

    @api.depends('order_line.cost','sale_cost_line_id.total_cost')
    def compute_final_cost(self):
        totalcost1=0
        totalcost2=0
        for order in self.order_line:
            totalcost1+=order.cost
        for cost in self.sale_cost_line_id:
            totalcost2+=cost.total_cost
        _logger.info("logsale3=%s,%s", totalcost1,totalcost2)               
        self.update({
            'final_cost': totalcost1+totalcost2,
        })

    @api.depends('final_price', 'final_cost')
    def compute_margin_quotation(self):
        if self.final_price != 0:
            _logger.info("logsale4=%s,%s", self.final_price-self.final_cost,(self.final_price-self.final_cost)/self.final_price*100)   
            self.update({
                'margin': self.final_price-self.final_cost,
                'porc_margin': (self.final_price-self.final_cost)/self.final_price*100,
            })

    @api.multi
    @api.onchange('compute_margin_sim')
    def compute_margin_sim_quotation(self):
        for line in self.order_line:
            line.update({
                'margin': self.compute_margin_sim,
            })

    @api.multi
    def send_quotation(self):
        sale_note_obj=self.env["crm.sale.note"]
        project_obj=self.env["project.project"]

        for rec in self:
            if not rec.order_line:
                raise exceptions.ValidationError(_('No Lineas de Perfiles!'))
            if rec.final_price==0.0:
                raise exceptions.ValidationError(_('Precio 0'))
            if rec.final_cost==0.0:
                raise exceptions.ValidationError(_('Costo 0'))
            if rec.sale_cost_line_id:
                for sale_cost in rec.sale_cost_line_id:
                    if sale_cost.cost_amount==0.0:
                        raise exceptions.ValidationError(_('Costo 0'))
            if not rec.project_id and not rec.cost_center_id:
                raise exceptions.ValidationError(_('For contract type \'New\' you must specify Cost Center!.'))

            cvalues={}
            cvalues["name"]=rec.oportunity+"-"+rec.partner_id.name #rec.reference2
            cvalues["partner_id"]=rec.partner_id.id
            cvalues["user_id"]=rec.user_id.id
            cvalues["contact_id"]=rec.user_id.id#rec.contact_id.id
            cvalues["project_currency_id"]=rec.currency_id.id
            cvalues["price"]=rec.final_price
            cvalues["cost"]=rec.final_cost
            cvalues["margin"]=rec.porc_margin
            cvalues["project_id"]=rec.project_id.id or False
            cvalues["external_lead"]="" #rec.hubspot_link
            cvalues["order_line_quotation"]=[(6,0,rec.order_line.ids)]
            total_hours=0

            for total_hour in rec.order_line:
                total_hours+=total_hour.product_uom_qty
            cvalues["total_hours"]=total_hours
            if rec.crm_sale_note_id:
                sale_note=rec.crm_sale_note_id
                try:
                    sale_note.write(cvalues)
                except Exception as e:
                    raise exceptions.ValidationError(_('No se podia actualizar la Nota de Venta. Por favor contactese con el Admin del sistema!'))
            else:
                try:
                    sale_note=sale_note_obj.create(cvalues)
                except Exception as e:
                    raise exceptions.ValidationError(_('No se podia crear la Nota de Venta. Por favor contactese con el Admin del sistema!\n\n'+str(e)))

            pvalues={}
            pvalues["company_id"]=rec.company_id.id
            pvalues["name"]=rec.oportunity+"-"+rec.partner_id.name
            pvalues["service_type"]=rec.type_service.id
            pvalues["partner_id"]=rec.partner_id.id
            pvalues["manager_user_id"]=rec.user_id.id
            pvalues["sales_value"]=rec.final_price
            pvalues["user_id"]=rec.user_id.id

            if sale_note.project_id and not rec.project_id:
                try:
                    sale_note.project_id.write(pvalues)
                    for order_lines in rec.order_line:
                        order_lines.project_id=sale_note.project_id.id
                except Exception as e:
                    raise exceptions.ValidationError(_('No se puede actualizar el Proyecto. Por favor contactese con el Admin del sistema!'))

            elif sale_note.project_id and rec.project_id:
                pass

            else:
                pvalues["nota_ids"]=[(6,0,[sale_note.id])]
                pvalues["cost_center_id"]=rec.cost_center_id.id
                pvalues["sector_id"]=rec.sector_id.id
                try:
                    project=project_obj.create(pvalues)
                    rec.project_id=project
                    project.user_id=rec.user_id
                    for order_lines in rec.order_line:
                        order_lines.project_id=project.id

                except Exception as e:
                    raise exceptions.ValidationError(_('No se puede crear el Proyecto. Por favor contactese con el Admin del sistema! \n\ne: '+str(e)))

            rec.crm_sale_note_id=sale_note
            rec.state = 'sale'

    def send_prerenewel(self):
        if not self.order_line:
            raise exceptions.ValidationError(_('No Lineas de Perfiles!'))
        if self.final_price==0.0:
            raise exceptions.ValidationError(_('Precio 0'))
        if self.final_cost==0.0:
            raise exceptions.ValidationError(_('Costo 0'))
        if self.sale_cost_line_id:
            for sale_cost in self.sale_cost_line_id:
                if sale_cost.cost_amount==0.0:
                    raise exceptions.ValidationError(_('Costo 0'))
        if not self.project_id and not self.cost_center_id:
            raise exceptions.ValidationError(_('For contract type \'New\' you must specify Cost Center!.'))
        wizard_values={}
        wizard_values["name"]=self.oportunity+"-"+self.partner_id.name #rec.reference2
        wizard_values["partner_id"]=self.partner_id.id
        wizard_values["user_id"]=self.user_id.id
        wizard_values["contact_id"]=self.user_id.id#rec.contact_id.id
        wizard_values["project_currency_id"]=self.currency_id.id
        wizard_values["price"]=self.final_price
        wizard_values["cost"]=self.final_cost
        wizard_values["margin"]=self.porc_margin
        wizard_values["project_id"]= False
        wizard_values["external_lead"]="" #rec.hubspot_link
        wizard_values["order_line_quotation"]=self.order_line.ids
        total_hours=0
        for total_hour in self.order_line:
            total_hours+=total_hour.product_uom_qty
        wizard_values["total_hours"]=total_hours

        renewel=''
        if self.project_id.renewel == 'renewel_zero' or self.project_id.renewel == '':
            renewel = 'renewel_uno'
        if self.project_id.renewel == 'renewel_uno':
            renewel = 'renewel_dos'
        if self.project_id.renewel == 'renewel_dos':
            renewel = 'renewel_tres'

        wizard_values['renewel']=renewel
        wizard_values['sale_note']=self.crm_sale_note_id.id or False
        wizard_values['sale_order']=self.id
        wizard_obj = self.env['sale.order.wizard']
        wizard=wizard_obj.create(wizard_values)
        cform = self.env.ref('apiux_project.sale_order_wizard', False)
        action = {
            'type': 'ir.actions.act_window',
            'id':'invoice_wizard_view',
            'name': 'Renovacion',
            'res_model': 'sale.order.wizard',
            'src_model': 'sale.order',
            'target':'new',
            'view_id':cform.id,
            'res_id':wizard.id,
            'view_mode': 'form',
            'view_type':'form',
            }
        return action

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin = fields.Monetary(string="Margen", store=True)
    risk = fields.Integer(string="Riesgo", store=True)
    cost = fields.Monetary(string="Costo", store=True, compute='compute_cost')
    order_id_quotation = fields.Many2one('crm.sale.note', string='Order Reference', required=False, ondelete='cascade', index=True)
    price = fields.Monetary(compute='compute_price_quotation', string='Precio', readonly=True, store=True)
    state_booking = fields.Boolean(string="Estado", default=False)
    project_id = fields.Many2one('project.project', 'Proyecto Generado', index=True, copy=True)

    @api.depends('cost','product_uom_qty','risk','order_id.type_sale')
    def compute_cost(self):
        for line in self:
        
            qty=line.product_uom_qty/line.order_id.type_sale.factor
            cost=line.product_id.standard_price*qty*line.order_id.uf_value/line.order_id.dolar_value
            cost_risk=cost+(cost*(line.risk/100))
            line.update({
                'cost': cost_risk,
                'product_uom': line.order_id.type_sale.id,
            })

    @api.depends('cost','margin')
    def compute_price_quotation(self):
        for line in self:
            _logger.info("logsaleline2=%s,%s,%s",line.margin,line.cost,line.cost/(1-(line.margin/100)))        
            line.update({
                'price': line.cost/(1-(line.margin/100)),
            })

class SaleCostLine(models.Model):
    _name = "sale.cost.line"

    name = fields.Text(string='Descripción', required=True)
    currency_id = fields.Many2one(related='sale_order_id.currency_id', depends=['sale_order_id.currency_id'], store=True, string='Currency', readonly=True)
    product_id = fields.Many2one('product.product', domain=['|', ('type_product', '=', 'Equipo'),('type_product', '=', 'Otros')], string='Elemento', ondelete='restrict')
    product_uom = fields.Many2one('uom.uom', string='Unidad', readonly=True)
    product_uom_qty = fields.Integer(string='Cantidad', required=True, default=1.0) #digits=dp.get_precision('Product Unit of Measure'),
    cost_amount = fields.Monetary(string="Monto")
    total_cost = fields.Monetary(string="Total",compute='compute_change_product_id')
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    type_product_cost = fields.Char(string="tipo")
    risk = fields.Integer(string="Riesgo")

    @api.depends('product_id','product_uom_qty','cost_amount','risk','sale_order_id.type_sale')
    def compute_change_product_id(self):
        for line in self:

            qty=0
            type_sale=1
            riesgo=line.sale_order_id.type_service.risk

            if line.sale_order_id.type_sale == "Hours":
                type_sale=6
                qty=line.product_uom_qty
            if line.sale_order_id.type_sale == "Months":
                qty=line.product_uom_qty*160
                type_sale=20
            line.update({
                'product_uom': line.product_id.uom_id,
                'name': str(line.product_id.name),
                'type_product_cost': line.product_id.type_product,
                'product_uom': type_sale,
            })

            if line.type_product_cost=="Equipo":
                cost=(line.product_id.standard_price*line.sale_order_id.uf_value)/line.sale_order_id.dolar_value
                cost_risk=cost+(cost*(riesgo/100))
                line.update({
                    'cost_amount': cost_risk,
                })
                line.update({
                    'total_cost': line.product_uom_qty*line.cost_amount,
                })
            else:
                total_cost=line.product_uom_qty*line.cost_amount
                line.update({
                    'total_cost': total_cost+(total_cost*(riesgo/100)),
                })



class ProductTemplateQuotation(models.Model):
    _inherit="product.template"

    type_product=fields.Selection([('Perfil','Perfil'),('Equipo','Equipo'),('Otros','Otros')], string="Tipo")
