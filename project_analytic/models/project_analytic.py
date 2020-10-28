# -*- coding: utf-8 -*-

from odoo import _
from odoo import models, fields, api, exceptions
from odoo.exceptions import Warning,ValidationError,UserError
from odoo.tools.safe_eval import safe_eval

from collections import defaultdict
import collections

from lxml import etree
import logging

_logger = logging.getLogger(__name__)



class project_task_type(models.Model):
    _inherit = 'project.task.type'

    close_stage=fields.Boolean('Close Stage',default=False)


class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'

    
    @api.multi       
    @api.depends('project_id')        
    def _compute_cost_center(self):        

        for rec in self:
            cost_center=False
            try:
                if rec.project_id and rec.project_id.cost_center_id:            
                    rec.cost_center_id=rec.project_id.cost_center_id   
            except:
                pass
     
    def _default_cost_center(self):        

        cost_center=False
        try:
            cost_center=self.project_id.cost_center_id
        
        except:
            pass
        
        return cost_center      
    
    
    @api.multi       
    @api.depends('project_id')        
    def _compute_sector(self):        

        for rec in self:
            sector=False
            try:
                if rec.project_id and rec.project_id.sector_id:            
                    rec.sector_id=rec.project_id.sector_id   
            except:
                pass
     
    def _default_sector(self):        

        sector=False
        try:
            sector=self.project_id.sector_id
        except:
            pass
        
        return sector      


    @api.depends('move_id.invoice_id.state')
    def _compute_payment_state(self):
    
        for rec in self:
            
            payment_state='n/a' 
            if rec.move_id.invoice_id:
                if rec.move_id.invoice_id.state=='open':
                    payment_state='invoiced'
                elif rec.move_id.invoice_id.state=='paid':
                    payment_state='paid'

            rec.payment_state=payment_state
            

    def _default_payment_state(self):
    
        for rec in self:
            
            payment_state='n/a' 
            if rec.move_id.invoice_id:
                if rec.move_id.invoice_id.state=='open':
                    payment_state='invoiced'
                elif rec.move_id.invoice_id.state=='paid':
                    payment_state='paid'

            return payment_state 
    
    
    cost_center_id=fields.Many2one('account.cost.center', string='Centro de Costo', compute=_compute_cost_center, default=_default_cost_center,store=True)
    sector_id=fields.Many2one('account.sector', string='Sector', compute=_compute_sector, default=_default_sector,store=True)
    task_activity_type=fields.Many2one(related='task_id.activity_type', string='Activity Type', readonly=True)
    task_stage_close=fields.Boolean(related='task_id.stage_id.close_stage', string='Task Closed', readonly=True)    
    payment_state=fields.Selection([('n/a','N/A'),('invoiced','Facturado'),('paid','Pagado')], store=True, default=_default_payment_state, compute=_compute_payment_state, string='Estado Pago')      
    
    
                  
    
    
    @api.model
    def create(self, vals):


        # for rec in vals:
            # date=rec.get('date',False)
            # task_id=rec.get('task_id')

            
            # task=self.env['project.task'].browse([task_id])
            # if task.date_deadline and date > task.date_deadline:
                # raise Warning(_('''The date entered exceeds the date limit on the Task. Please check the date and Task'''))


        return super(account_analytic_line, self).create(vals)

    @api.multi
    def write(self, vals):

        date=vals.get('date',False)
        task_id=vals.get('task_id')

        if date:
            if task_id:
                task=self.env['project.task'].browse([task_id])
            else:
                task=self.task_id
            if task.date_deadline and date > task.date_deadline:
                raise Warning(_('''The date entered exceeds the date limit on the Task. Please check the date and Task'''))

        return super(account_analytic_line, self).write(vals)    
    
    