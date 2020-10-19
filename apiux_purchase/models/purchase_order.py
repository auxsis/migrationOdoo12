# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning,ValidationError,AccessDenied
from odoo.tools.translate import _
from odoo import tools

import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit='purchase.order'
    
    employee_id= fields.Many2one('hr.employee', 'Requestor')
    boss_id=fields.Many2one(related='employee_id.parent_id', string='Manager of Requestor')
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Approved by Finance Assistant'),
        ('approve1', 'Approved by Head of Finance'),
        ('approve2', 'Approved by Requestor'),
        ('approve3', 'Approved by Manager of Requestor'),
        ('approve4', 'Approved by General Manager'),
        ('invoiced', 'Invoiced'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')    
    


    @api.multi
    def button_confirm(self):
    
        #we need to get approver params fro m res.config
        
        res_obj=self.env['res.config.settings'].get_values()
        
        if not res_obj['finance_assistant']:
            raise models.ValidationError(_('There is no value set for Finance Assistant in configuration settings. Please contact the system administrator'))
        #get employee
        confirm_emp=self.env['hr.employee'].sudo().search([('id','=',res_obj['finance_assistant'])])
        if not confirm_emp:
            raise models.ValidationError(_('There is no employee for value of Finance Assistant in configuration settings. Please contact the system administrator'))        
        
        #validate login user against confirm_emp
        if confirm_emp.user_id.id!=self.env.uid and confirm_emp.parent_id.user_id.id!=self.env.uid:
            raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden aprobar esta solicitud de presupuesto''')  % (confirm_emp.name,confirm_emp.parent_id.name))         
        
        return super(PurchaseOrder,self).button_confirm()
        

    @api.multi
    def button_approve1(self):
    
        #we need to get approver params fro m res.config
        
        res_obj=self.env['res.config.settings'].get_values()
        
        if not res_obj['finance_manager']:
            raise models.ValidationError(_('There is no value set for Finance Manager in configuration settings. Please contact the system administrator'))
        #get employee
        confirm_emp=self.env['hr.employee'].sudo().search([('id','=',res_obj['finance_manager'])])
        if not confirm_emp:
            raise models.ValidationError(_('There is no employee for value of Finance Manager in configuration settings. Please contact the system administrator'))        
        
        #validate login user against confirm_emp
        if confirm_emp.user_id.id!=self.env.uid and confirm_emp.parent_id.user_id.id!=self.env.uid:
            raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden aprobar esta Orden de Compra''')  % (confirm_emp.name,confirm_emp.parent_id.name))         
        
        for order in self:
            order.write({'state': 'approve1'})
        
        
        return True



    @api.multi
    def button_approve2(self):
    
        #we need to get approver params fro m res.config  
        
        for order in self:              
            confirm_emp=order.employee_id
            if not confirm_emp:
                raise models.ValidationError(_('There is no Requestor for this Purchase Order. Please contact the system administrator'))        
            
            #validate login user against confirm_emp
            if confirm_emp.user_id.id!=self.env.uid and confirm_emp.parent_id.user_id.id!=self.env.uid:
                raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden aprobar esta Orden de Compra''')  % (confirm_emp.name,confirm_emp.parent_id.name))          
        
            order.write({'state': 'approve2'})      
        
        return True


    @api.multi
    def button_approve3(self):
    
        #we need to get general manager approval limit from res.config 
        res_obj=self.env['res.config.settings'].get_values()
        gm_approval_limit=res_obj.get('general_manager_approval_limit',0)
              
        for order in self:              
            confirm_emp=order.employee_id.parent_id
            if not confirm_emp:
                raise models.ValidationError(_('There is no Requestor Manager for this Purchase Order. Please contact the system administrator'))        
            
            #validate login user against confirm_emp
            if confirm_emp.user_id.id!=self.env.uid and confirm_emp.parent_id.user_id.id!=self.env.uid:
                raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden aprobar esta Orden de Compra''')  % (confirm_emp.name,confirm_emp.parent_id.name))          
        
            if gm_approval_limit:
                if gm_approval_limit>0 and gm_approval_limit<=order.amount_total:
                    order.write({'state': 'approve3'})
                else:
                    order.write({'state': 'approve4'})         
            else:
                order.write({'state': 'approve3'})  
        
        return True


    @api.multi
    def button_approve4(self):
    
        #we need to get approver params fro m res.config
        
        res_obj=self.env['res.config.settings'].get_values()
        
        if not res_obj.get('general_manager',False):
            raise models.ValidationError(_('There is no value set for General Manager in configuration settings. Please contact the system administrator'))
        #get employee
        confirm_emp=self.env['hr.employee'].sudo().search([('id','=',res_obj['general_manager'])])
        if not confirm_emp:
            raise models.ValidationError(_('There is no employee for value of General Manager in configuration settings. Please contact the system administrator'))        
        
        #validate login user against confirm_emp
        if confirm_emp.user_id.id!=self.env.uid and (confirm_emp.parent_id and  confirm_emp.parent_id.user_id.id!=self.env.uid):
            raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden aprobar esta Orden de Compra''')  % (confirm_emp.name,confirm_emp.parent_id and confirm_emp.parent_id.name or "" ))         
        
        for order in self:
            order.write({'state': 'approve4'})
               
        return True


    @api.multi
    def button_cancel(self):
    
    
        res_obj=self.env['res.config.settings'].get_values()
        
        if not res_obj['finance_assistant']:
            raise models.ValidationError(_('There is no value set for Finance Assistant in configuration settings. Please contact the system administrator'))
        #get employee
        confirm_emp=self.env['hr.employee'].sudo().search([('id','=',res_obj['finance_assistant'])])
        if not confirm_emp:
            raise models.ValidationError(_('There is no employee for value of Finance Assistant in configuration settings. Please contact the system administrator'))         
        
        #validate login user against confirm_emp
        if confirm_emp.user_id.id!=self.env.uid and confirm_emp.parent_id.user_id.id!=self.env.uid:
            raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden mandar esta O/C a Facturar''')  % (confirm_emp.name,confirm_emp.parent_id.name))            
    
        for order in self:
        
        
        #we need to get approver params fro m res.config
         
        
            for inv in order.invoice_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise UserError(_("Unable to cancel this purchase order. You must first cancel the related vendor bills."))

        self.write({'state': 'cancel'})


    @api.multi
    def action_view_invoice(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        
        
        #we need to get approver params fro m res.config
        
        res_obj=self.env['res.config.settings'].get_values()
        
        if not res_obj['finance_assistant']:
            raise models.ValidationError(_('There is no value set for Finance Assistant in configuration settings. Please contact the system administrator'))
        #get employee
        confirm_emp=self.env['hr.employee'].sudo().search([('id','=',res_obj['finance_assistant'])])
        if not confirm_emp:
            raise models.ValidationError(_('There is no employee for value of Finance Assistant in configuration settings. Please contact the system administrator'))         
        
        #validate login user against confirm_emp
        if confirm_emp.user_id.id!=self.env.uid and confirm_emp.parent_id.user_id.id!=self.env.uid:
            raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden mandar esta O/C a Facturar''')  % (confirm_emp.name,confirm_emp.parent_id.name))         
        
       
        
        action = self.env.ref('account.action_vendor_bill_template')
        result = action.read()[0]
        create_bill = self.env.context.get('create_bill', False)
        # override the context to get rid of the default filtering
        result['context'] = {
            'type': 'in_invoice',
            'default_purchase_id': self.id,
            'default_currency_id': self.currency_id.id,
            'default_company_id': self.company_id.id,
            'company_id': self.company_id.id
        }
        # choose the view_mode accordingly
        if len(self.invoice_ids) > 1 and not create_bill:
            result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
        else:
            res = self.env.ref('account.invoice_supplier_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                result['views'] = form_view
            # Do not set an invoice_id if we want to create a new bill.
            if not create_bill:
                result['res_id'] = self.invoice_ids.id or False
        result['context']['default_origin'] = self.name
        result['context']['default_reference'] = self.partner_ref
        _logger.info("result=%s",result)
        return result

   
class PurchaseOrderLine(models.Model):
    _inherit='purchase.order.line'    
      
    sector_id=fields.Many2one('account.sector', string='Sector')
    cost_center_id=fields.Many2one('account.cost.center', string='Cost Center')