# -*- coding: utf-8 -*-

from odoo import models, fields, api
import uuid
import logging
_logger = logging.getLogger(__name__)

class SyncJobLog(models.Model):
    _name = "sync.job.log"
    _order ="create_date asc"

    type =  fields.Selection((('1',u'Export'),('2',u'Import')),default='1',string='Type',help='Process Type')
    state = fields.Selection((('R',u'Running'),('D',u'Done'),('F',u'Failed')),default='O',string='State',help='Process State')
    error = fields.Text('Message')
    name =  fields.Char('Name')
    job_id =fields.Many2one('sync.job.queue',string='Job Reference') 
    

class SyncJobQueue(models.Model):
    _name = "sync.job.queue"
    _order ="id asc"


    def _default_name(self):
        return str(uuid.uuid4())

    def _default_user(self):
        return self.env.user


    name = fields.Char('Name', default=_default_name)
    user_id=fields.Many2one('res.users','User',default=_default_user)
    active = fields.Boolean('Active', default=True)
    state = fields.Selection((('P',u'Paused'),('Q',u'Queued'),('R',u'Running'),('D',u'Done'),('F',u'Failed')),default='P',string='State',help='Process State')
    type=fields.Selection((('1',u'Export'),('2',u'Import')),default='1',string='State',help='Type')
    source=fields.Reference([('res.users', 'User'), ('res.partner', 'Contact'),('hr.payslip.run','Payslip Run')], string='Source')
    method=fields.Char('Method')
    params=fields.Char('Params dict')
    date_processed=fields.Datetime('Date Processed')

    @api.model
    def sync_job_cron(self):
        _logger.info("Sync Job Cron - Started by cron")

        #how many jobs will I process?
        sync_job_qty=1
        icp_obj = self.env['ir.config_parameter']
        try:
            sync_ob_qty=int(icp_obj.get_param('sync_job_qty'))
        except Exception as e:
            _logger.info("Joberror no se encuentra config param sync_job_qty , %s",str(e))  
        
        
        jobs=self.search([('state','=','Q'),('active','=',True)], order='id asc',limit=sync_job_qty)
        for job in jobs:
            
            source=job.source
            method=job.method
            sync_method=getattr(source, method)
            try:
                job.state='R'
                res=sync_method(job.name,job.id)
                job.state='D'
            except Exception as e:
                _logger.info("Joberror Job name %s failed with message %s",job.name,str(e))
                job.state='F'
            

             
        _logger.info("Sync Job Cron - Ended by cron")         
        
  
        
        
        
        
        
        
        
        
        
        
        
    
    
    

                