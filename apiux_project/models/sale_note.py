# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
import logging

from odoo.addons import decimal_precision as dp
from odoo import exceptions

_logger = logging.getLogger(__name__)

class crm_sale_note(models.Model):
    _name = 'crm.sale.note'
    _inherit = 'mail.thread'
    _description = 'Sale Note'

    @api.model
    def _default_currency(self):
        current_user_id=self._context.get('uid')
        current_user=self.env['res.users'].browse([current_user_id])
        currency_uf=None
        currency_obj=self.env['res.currency']
        currency_uf=currency_obj.search([('name','=','UF')], limit=1)
        if currency_uf:
            return currency_uf
        else:
            return current_user.company_id.currency_id

    @api.depends('partner_id','sale_note_number','partner_id.partner_abbr')
    def _compute_reference(self):
        abbr=None
        for sale in self:
            if sale.sale_note_number and sale.partner_id:
                abbr=sale.partner_id.partner_abbr
                if abbr and "ABR" in sale.sale_note_number:
                    sale.sale_note_reference=sale.sale_note_number.replace("ABR",abbr)
                else:
                    raise exceptions.Warning(_('Cliente %s no tiene Abreviatura. Ingrese abreviatura en Cliente') %(sale.partner_id.name,))
            else:
                sale.sale_note_reference=_("Ref. No Disponible")


    name=fields.Char('Description', required=True)
    partner_id=fields.Many2one('res.partner',string='Partner',store=True, required=True)
    partner_rut=fields.Char(related='partner_id.vat', string='RUT Cliente')    
    partner_name=fields.Char(related='partner_id.name')
    street = fields.Char(related='partner_id.street', store=True, readonly=True)
    street2 = fields.Char(related='partner_id.street2', store=True,readonly=True)
    city = fields.Char(related='partner_id.city', store=True,readonly=True)
    zip = fields.Char(related='partner_id.zip', store=True,readonly=True)
    address_state = fields.Char(related='partner_id.state_id.name', store=True,readonly=True)
    country = fields.Char(related='partner_id.country_id.name', store=True,readonly=True)

    #contact for the sale note

    contact_id=fields.Many2one('res.partner',string='Contact', domain="[('parent_id','=',partner_id),('is_company','=',False)]",store=True)
    contact_function= fields.Char(related='contact_id.function', store=True,readonly=True)
    contact_name= fields.Char(related='contact_id.name', store=True,readonly=True)
    contact_email= fields.Char(related='contact_id.email', store=True,readonly=True)
    contact_phone= fields.Char(related='contact_id.phone', store=True,readonly=True)
    contact_mobile= fields.Char(related='contact_id.mobile', store=True,readonly=True)
    user_id=fields.Many2one('res.users',string='Vendedor',store=True)
    salesman_id=fields.Many2one('res.users',string='Vendedor',store=True)

    #oppportunity link crm.lead

    project_id=fields.Many2one('project.project',string='Project',store=True, required=False, ondelete='cascade')
    external_lead=fields.Char(string='Oportunidad externa')

    #sales fields
    project_currency_id = fields.Many2one('res.currency', string='Currency',required=False, default=_default_currency, track_visibility='always', ondelete='restrict')
    price=fields.Monetary('Price', currency_field='project_currency_id',required=True, help='Price of Project')
    cost=fields.Monetary('Cost', currency_field='project_currency_id',required=True, help='Cost of Project')
    margin=fields.Float('Margen',digits=(16,2), readonly=True, help='Margen of Project')
    total_hours=fields.Float('Horas Total',digits=(6,1),  help='Total Horas Vendidas')

    #invoice lines
    # invoice_ids=fields.One2many('crm.sale.note.invoice','note_id','Sales Note Invoice Lines')
    # supplier_ids=fields.One2many('crm.sale.note.supplier','note_id','Sales Note Supplier Lines')
    # comission_ids=fields.One2many('crm.sale.note.comm','note_id','Sales Note Commission Lines')
    doc_count=fields.Integer(compute="_get_attached_docs", string="Number of documents attached")
    purchase_order_id=fields.Many2many('purchase.order', string='Orden de Compra')
    purchase_order=fields.Char(string='O/C')


    order_line_quotation = fields.One2many('sale.order.line', 'order_id_quotation', string='Order Lines')
    date_from = fields.Date(string="Fecha Inicio")
    date_to = fields.Date(string="Fecha Fin")

    #sale note reference...basically a copy of project reference
    sale_note_number= fields.Char('Numero Referencia')
    sale_note_reference= fields.Char('Referencia', compute="_compute_reference", store=True)




    """_sql_constraints = [
    ('sale_note_uniq',
    'UNIQUE (name,lead_id)',
    _('Sales Note name must be unique for the Opportunity!'))]"""

    @api.multi
    def _get_attached_docs(self):
        res = {}
        attachment = self.env['ir.attachment']
        for note in self:
            note_attachments = attachment.search([('res_model', '=', 'crm.sale.note'), ('res_id', '=', note.id)])
            self.doc_count= len(note_attachments) or 0

    # @api.multi
    # @api.onchange('invoice_ids')
    # @api.depends('invoice_ids')
    # def compute_max_line_sequence(self):
        # #Allow to know the highest sequence
        # #entered in purchase order lines.
        # #Web add 10 to this value for the next sequence
        # #This value is given to the context of the o2m field
        # #in the view. So when we create new purchase order lines,
        # #the sequence is automatically max_sequence + 10


        # self.max_line_sequence = (
            # max(self.mapped('invoice_ids.sequence') or [0]) + 1)

    # @api.multi
    # @api.onchange('supplier_ids')
    # @api.depends('supplier_ids')
    # def compute_max_supplier_sequence(self):
        # #Allow to know the highest sequence
        # #entered in purchase order lines.
        # #Web add 10 to this value for the next sequence
        # #This value is given to the context of the o2m field
        # #in the view. So when we create new purchase order lines,
        # #the sequence is automatically max_sequence + 10

        # self.max_supplier_sequence = (
            # max(self.mapped('supplier_ids.sequence') or [0]) + 1)

    # max_line_sequence = fields.Integer(string='Max sequence in lines',compute='compute_max_line_sequence')
    # max_supplier_sequence = fields.Integer(string='Max sequence in Supplier',compute='compute_max_supplier_sequence')

    @api.multi
    def attachment_tree_view(self):
        domain = [('res_model', '=', 'crm.sale.note'), ('res_id', 'in', self.ids)]
        res_id = self.ids and self.ids[0] or False

        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'limit': 80,
            'target':'same',
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, res_id)
        }

    @api.model
    def create(self, vals):
        abbr=None
        sequence_dict={}
        partner=self.env['res.partner'].browse(vals['partner_id'])
        abbr=partner.partner_abbr

        if not abbr or abbr=="":
            raise exceptions.Warning(_('Cliente %s no tiene Abreviatura. Ingrese abreviatura en Cliente') %(partner.name,))

        sequence_dict=self.env['res.config.settings'].sudo().get_values()
        sequence_id=sequence_dict['project_sequence']
    
        _logger.info("secuence=%s",sequence_dict)
        if not sequence_id:
            raise exceptions.Warning(_('Sequencia no esta configurada. Por favor, contactese con el Administrador de sistema'))

        sequence_id=sequence_dict['project_sequence']
        vals['sale_note_number'] = self.env['ir.sequence'].sudo().next_by_code('project_sale_order')
        vals['sale_note_reference']=vals.get('sale_note_number').replace("ABR",abbr)

        res=super(crm_sale_note, self).create(vals)
        return res

    @api.multi
    def write(self,vals):
        #create project_reference if project_reference not set
        if (not self.sale_note_reference or self.sale_note_reference=='Ref. No Disponible') and (self.partner_id or 'partner_id' in vals):
            abbr=None
            sequence_dict={}
            if not vals.get('partner_id',False):
                partner=self.env['res.partner'].browse(self.partner_id.id)
                abbr=partner.partner_abbr
            else:
                partner=self.env['res.partner'].browse(vals['partner_id'])
                abbr=partner.partner_abbr

            if not abbr or abbr=="":
                raise exceptions.Warning(_('Cliente %s no tiene Abreviatura. Ingrese abreviatura en Cliente') %(partner.name,))

            sequence_dict=self.env['res.config.settings'].sudo().get_values()
            sequence_id=sequence_dict['project_sequence']

            if not sequence_id:
                raise exceptions.Warning(_('Sequencia no esta configurada. Por favor, contactese con el Administrador de sistema'))

            sequence_id=sequence_dict['project_sequence']
            vals['sale_note_number'] = self.env['ir.sequence'].next_by_code('project_sale_order')
            vals['sale_note_reference']=vals.get('project_number',False).replace("ABR",abbr)

        res=super(crm_sale_note, self).write(vals)
        return res