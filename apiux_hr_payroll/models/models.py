# -*- coding: utf-8 -*-

from odoo import models, fields, api
from openerp.tools.safe_eval import safe_eval
import requests
import logging
import json

_logger = logging.getLogger(__name__)


BASE_URL="http://138.197.108.163/payslip/fetch"


class HrPayslip(models.Model):
    _inherit='hr.payslip'
    
    file_data = fields.Binary(string='File Data')
    file_name = fields.Char(string="File path")
    employee_name=fields.Char(related='employee_id.name', string='Employee Name')
    user_id=fields.Many2one(related='employee_id.user_id', store=True, string='Usuario')
    payslip_dias_trabajados=fields.Integer('Days worked')
    visible=fields.Boolean('Visible?', default=False)
    state=fields.Selection(readonly=False)
    
    
    
    def call_odoo8(self=None,type=None,param_dict={}):
  

        if type=='payslip_fetch': 
        
            url=BASE_URL
            data={"params":param_dict}
            
            #try:
            r=requests.post(url,json=data,verify=False)
            if r.status_code==200:
                data=r.json()
                _logger.info("Odoo8 call payslip_fetch success with code %s, data %s",r.status_code,data)
                return data
            else:
                data=r.json()
                _logger.info("Odoo8 call payslip_fetch failed with code %s, data %s, result %s",r.status_code,param_dict,data)
                return False
            
            # except Exception as e:
                # _logger.info("Error in Odoo8 call payslip_fetch %s",str(e))
                # return False    
                
                
        return False
            
            
            
    @api.multi
    def payslip_fetch(self):
    
        for rec in self:
        
            param_dict={}
            param_dict['rec_id']=rec.integration_id
            param_dict['rec_model']='hr.payslip'
            param_dict['rec_user_id']=rec.employee_id.user_id.integration_id
            param_dict['rec_report_name']='hr_payroll.report_payslip_password'
            
            res=rec.call_odoo8('payslip_fetch',param_dict)
            
            _logger.info("resdict=%s",res)
            
            if res:
                rec.file_data=res['result'].get('file_data',False)
                rec.file_name=res['result'].get('file_name',False)
                
            else:
                _logger.info("Error in method payslip_fetch %s",rec.id)
                
            
    #allow delete even if status is 'done'. This is temporary
    @api.multi
    def unlink(self):
        return super(models.Model, self).unlink()    
    