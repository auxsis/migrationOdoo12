from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, AccessError, ValidationError

class sale_order_wizard(models.TransientModel):
    _name = 'sale.order.wizard'
    _description = 'Sale Order Wizard'

    renewel = fields.Integer(string='Renovación', compute='change_project_id', readonly=True, default=0)
    project_id = fields.Many2one('project.project', string='Proyecto')
    sale_note = fields.Many2one('crm.sale.note', string="nota de venta")
    sale_order = fields.Many2one('sale.order', string="orden de venta")

    name = fields.Char(string="nombre")
    partner_id = fields.Many2one('res.partner')
    user_id = fields.Many2one('res.users')
    contact_id = fields.Many2one('res.partner')
    project_currency_id = fields.Many2one('res.currency')
    price = fields.Float(string="precio")
    cost = fields.Float(string="costo")
    margin = fields.Float(string="margen")
    project_id = fields.Many2one('project.project')
    external_lead = fields.Char(string="external lead")
    order_line_quotation = fields.Char(string="order line quotation")
    total_hours = fields.Float(string="total de horas")

    @api.onchange('project_id')
    @api.depends('project_id')
    def change_project_id(self):
        project_obj=self.project_id.renewel
        self.update({
            'renewel': project_obj+1,
        })

    def send_renewel(self):
        order_line_quotation=self.order_line_quotation
        order_line_quotation=self.order_line_quotation.split("[")
        order_line_quotation=order_line_quotation[1].split("]")
        order_line_quotation=order_line_quotation[0].split(",")
        list_order_line_quotation=[]
        for number in order_line_quotation:
            list_order_line_quotation.append(int(number))
        #for line in list_order_line_quotation:
            #raise UserError(_('list_order_line_quotation: '+str(line)))
        sale_note_obj=self.env["crm.sale.note"]
        cvalues={}
        cvalues["name"]=self.name #rec.reference2
        cvalues["partner_id"]=self.partner_id.id
        cvalues["user_id"]=self.user_id.id
        cvalues["contact_id"]=self.contact_id.id#rec.contact_id.id
        cvalues["project_currency_id"]=self.project_currency_id.id
        cvalues["price"]=self.price
        cvalues["cost"]=self.cost
        cvalues["margin"]=self.margin
        cvalues["project_id"]= self.project_id.id
        cvalues["external_lead"]=self.external_lead
        cvalues["order_line_quotation"]=[(6,0,list_order_line_quotation)]
        cvalues["total_hours"]=self.total_hours
        #raise UserError(_('cvalues: '+str(cvalues)))
        if self.sale_note.id:
            sale_note=self.sale_note.id
            try:
                sale_note.write(cvalues)
            except Exception as e:
                raise exceptions.ValidationError(_('No se podia actualizar la Nota de Venta. Por favor contactese con el Admin del sistema!'))
        else:
            try:
                sale_note=sale_note_obj.create(cvalues)
                #raise UserError(_('sale_note: '+str(sale_note)))
            except Exception as e:
                raise exceptions.ValidationError(_('No se puede crear la Nota de Venta. Por favor contactese con el Admin del sistema!\n\n e:'+str(e)))
        sale_order_line_obj=self.env['sale.order.line']
        for sale_order_line in list_order_line_quotation:
            sale_order_line_obj.search([('id', '=', sale_order_line)]).write({'project_id': self.project_id.id})

        sale_order_obj=self.env['sale.order'].search([('id', '=', self.sale_order.id)])
        sale_order_obj.write({'state': 'sale', 'crm_sale_note_id':sale_note.id, 'project_id': self.project_id.id})
        project_obj=self.env['project.project'].search([('id', '=', self.project_id.id)])
        project_obj.write({'renewel': self.renewel})
        #for sale_note in self.project_id:
        #project=self.env['project.project'].search([('project_id', '=', self.project_id.id)])
        #project.write({'nota_ids': [(4, self.sale_order.id, 0)]})
            #raise UserError(_('project: '+str(project)))
            #self.env['crm.sale.note'].write({'project_id': [(4,0,sale_note.id)]})
