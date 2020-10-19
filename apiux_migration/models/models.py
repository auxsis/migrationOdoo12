# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

# class apiux_migration(models.Model):
#     _name = 'apiux_migration.apiux_migration'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100

class res_company(models.Model):
    _inherit='res.company'

    integration_id = fields.Integer('Integration Id')


class account_cost_center(models.Model):
    _inherit='account.cost.center'

    integration_id = fields.Integer('Integration Id')


class account_sector(models.Model):
    _inherit='account.sector'

    integration_id = fields.Integer('Integration Id')



class res_users(models.Model):
    _inherit='res.users'

    integration_id = fields.Integer('Integration Id')
    
    
    def test_method(self,val):
        _logger.info("testval=%s", val)
    
    
    
class res_partner(models.Model):
    _inherit='res.partner'
    
    integration_id = fields.Integer('Integration Id')
    partner_abbr=fields.Char('Abreviatura')

    @api.model
    def create(self,vals):
          
        return super(res_partner, self).create(vals)
    
    
    
class res_partner_bank(models.Model):
    _inherit='res.partner.bank'
    
    integration_id = fields.Integer('Integration Id')        
    
    
    
    
class hr_employee(models.Model):
    _inherit='hr.employee'
    
    
    cost_center_id=fields.Many2one('account.cost.center')
    sector_id=fields.Many2one('account.sector')
    integration_id = fields.Integer('Integration Id')     
    
    
    
class account_account(models.Model):
    _inherit='account.account'

    integration_id = fields.Integer('Integration Id')
    invisible=fields.Boolean('Invisible?')    
    
    
class account_tax(models.Model):
    _inherit='account.tax'

    integration_id = fields.Integer('Integration Id')    
    
    
    
class product_template(models.Model):
    _inherit='product.template'

    integration_id = fields.Integer('Integration Id') 


class product_product(models.Model):
    _inherit='product.product'

    integration_id = fields.Integer('Integration Id')  


class account_journal(models.Model):
    _inherit='account.journal'

    integration_id = fields.Integer('Integration Id')

class account_invoice(models.Model):
    _inherit='account.invoice'

    integration_id = fields.Integer('Integration Id')
  

    @api.onchange('invoice_line_ids')
    def onchange_invoice_line_ids(self):
        return super(account_invoice, self)._onchange_invoice_line_ids()
  

class account_invoice_line(models.Model):
    _inherit='account.invoice.line'

    integration_id = fields.Integer('Integration Id')

class project_project(models.Model):
    _inherit='project.project'

    integration_id = fields.Integer('Integration Id')

class account_analytic_account(models.Model):
    _inherit='account.analytic.account'

    integration_id = fields.Integer('Integration Id')


class account_move(models.Model):
    _inherit='account.move'

    integration_id = fields.Integer('Integration Id')
    


class account_full_reconcile(models.Model):
    _inherit='account.full.reconcile'

    integration_id = fields.Integer('Integration Id')

 
class account_move_line(models.Model):
    _inherit='account.move.line'

    integration_id = fields.Integer('Integration Id')    


class account_analytic_journal(models.Model):
    _inherit='account.analytic.journal'

    integration_id = fields.Integer('Integration Id')


class account_bank_statement(models.Model):
    _inherit='account.bank.statement'

    integration_id = fields.Integer('Integration Id')
    
class account_bank_statement_line(models.Model):
    _inherit='account.bank.statement.line'

    integration_id = fields.Integer('Integration Id')    
    
    
class account_payment_mode(models.Model):
    _inherit='account.payment.mode'

    integration_id = fields.Integer('Integration Id') 


class account_payment_order(models.Model):
    _inherit='account.payment.order'

    integration_id = fields.Integer('Integration Id')


class account_payment_line(models.Model):
    _inherit='account.payment.line'

    integration_id = fields.Integer('Integration Id') 
  

class hr_public_holiday(models.Model):
    _inherit='hr.public.holiday'
 
    integration_id = fields.Integer('Integration Id')
  
    
class hr_leave(models.Model):
    _inherit='hr.leave'
 
    integration_id = fields.Integer('Integration Id')


class hr_payslip(models.Model):
    _inherit='hr.payslip'
 
    integration_id = fields.Integer('Integration Id')     
    
    
class crm_sale_note(models.Model):
    _inherit='crm.sale.note'
    
    integration_id = fields.Integer('Integration Id')     
    

class project_project(models.Model):
    _inherit='project.project'
    
    integration_id = fields.Integer('Integration Id')     
    
    
class hr_projection_timesheet(models.Model):
    _inherit='hr.projection.timesheet'
    
    integration_id = fields.Integer('Integration Id')     
    

class project_task(models.Model):
    _inherit='project.task'
    
    integration_id = fields.Integer('Integration Id')   


class project_outsourcing(models.Model):
    _inherit='project.outsourcing'
    
    integration_id = fields.Integer('Integration Id')   


class project_pre_invoice(models.Model):
    _inherit='project.pre.invoice'
    
    integration_id = fields.Integer('Integration Id')



class project_worklog(models.Model):
    _inherit='project.worklog'
    
    integration_id = fields.Integer('Integration Id') 


class account_analytic_account(models.Model):
    _inherit='account.analytic.account'
    
    integration_id = fields.Integer('Integration Id')   



class account_analytic_line(models.Model):
    _inherit='account.analytic.line'
    
    integration_id = fields.Integer('Integration Id')   
    