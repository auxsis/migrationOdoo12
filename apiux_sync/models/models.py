# -*- coding: utf-8 -*-


from odoo import models, fields, api, exceptions
from odoo.tools.translate import _
import logging
import psycopg2


from odoo import exceptions
from odoo.exceptions import Warning,ValidationError
from odoo.tools.safe_eval import safe_eval


from calendar import monthrange
import time,math
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import re
import uuid

import erppeek
_logger = logging.getLogger(__name__)


database = 'apiuxProduccion'
server = 'http://138.197.108.163/'
admin_password = 'Admin.1234.Apiux'
user = 'admin'

class odoopeek(models.Model):
    _name='odoo.peek'
    _auto=False
        
    
    @api.model
    def odoo_connect(self):
    
        # Connect to the database
        client=None
        client = erppeek.Client(server, database, user, admin_password)    
        if not client:
            raise models.ValidationError("No puedo connectar a otro instancia")
             
        else:
            return client   




class hr_leave(models.Model):
    _inherit='hr.leave'
 


    @api.multi
    def odoo_connect(self):
    
        # Connect to the database
        util= self.env['odoo.peek']
        client = util.odoo_connect()    
        if not client:
            raise models.ValidationError("No puedo connectar a otro instancia")
             
        else:
            return client 


    @api.multi
    def create_hr_leave_job(self):
    
        job_obj=self.env['sync.job.queue']
        
        for rec in self:
            values={}
            
            values['source']='%s,%s' % ('hr.leave', rec.id)
            values['method']='export_hr_leave'
            
            try:
                job_inst=job_obj.create(values)
                job_inst.state='Q'
        
            except Exception as e:
                _logger.info("Joberror:Could not create create_remuneraciones_job for %s due to %s", rec.name,str(e))  


    @api.multi
    def export_hr_leave(self,job_name=False,job_id=False):
    
        #set up objects
        log_obj=self.env['sync.job.log']
        client=self.odoo_connect()
        
        for rec in self:    
    
            #write log record
            log=log_obj.create({'name':job_name,'state':'R','error':'Job started...','job_id':job_id})
            
            try:
                
                #first we need to get the employee using integration id
                employee_id=client.model('hr.employee').search([('id','=',rec.employee_id.integration_id),'|',('active','=',True),('active','=',False)])
                if not employee_id:
                    raise ValueError("Employee not found in Odoo8:ID", rec.employee_id.id)

                #first we need to get the user using integration id
                user_id=client.model('res.users').search([('id','=',rec.user_id.integration_id),'|',('active','=',True),('active','=',False)])
                if not user_id:
                    raise ValueError("User not found in Odoo8:ID", rec.user_id.id)


                manager_id1=False
                manager_id2=False
                manager_id3=False

                if rec.first_approver_id:
                    manager_id1=client.model('hr.employee').search([('id','=',rec.first_approver_id.integration_id),'|',('active','=',True),('active','=',False)])
                    if not manager_id1:
                        raise ValueError("Approver 1 not found in Odoo8:ID", rec.first_approver_id.id)
                    

                if rec.second_approver_id:
                    manager_id2=client.model('hr.employee').search([('id','=',rec.second_approver_id.integration_id),'|',('active','=',True),('active','=',False)])
                    if not manager_id2:
                        raise ValueError("Approver 2 not found in Odoo8:ID", rec.second_approver_id.id)
                    

                if rec.third_approver_id:
                    manager_id3=client.model('hr.employee').search([('id','=',rec.third_approver_id.integration_id),'|',('active','=',True),('active','=',False)])
                    if not manager_id3:
                        raise ValueError("Approver 3 not found in Odoo8:ID", rec.third_approver_id.id)

                #get leave_type (holiday_status)
                holiday_status_id=client.model('hr.holidays.status').search([('name','=',rec.holiday_status_id.name)])
                if not holiday_status_id:
                    raise ValueError("Leave Type not found in Odoo8", rec.holiday_status_id.id)



                #arm value dict
                values={}
                values['holiday_status_id']=holiday_status_id[0]
                values['alt_holiday_status_id']=holiday_status_id[0]
                values['employee_id']=employee_id[0]
                values['user_id']=user_id[0]                

                values['name']='MIGRATED'
                values['number_of_days_temp']=rec.number_of_days_display
                values['number_of_days']=-1*rec.number_of_days_display
                values['holiday_type']=rec.holiday_type

                values['date_from']=datetime.strftime(rec.date_from,'%Y-%m-%d')
                values['date_to']=datetime.strftime(rec.date_to,'%Y-%m-%d')

                #finally create leave in odoo 8
                hr_leave=client.model('hr.holidays').create(values)
                
                values={}
                
                values['manager_id']=manager_id1[0]
                values['manager_id2']=manager_id2[0]
                values['manager_id3']=manager_id3[0]
                values['state']='validate'

                hr_leave.write(values)
                
                          
                        
            except Exception as e:
                #log
                log=log_obj.create({'name':job_name,'state':'F','error':str(e),'job_id':job_id})            
            
                #clean-up
                for mig_move_id in mig_move_ids:
                    mig_move_id.unlink()
                                
                raise

            message='.'.join(('Job Finished- Exported Leave Id:',str(rec.id)))
            log=log_obj.create({'name':job_name ,'state':'D','error':message,'job_id':job_id})   


