# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
import logging
from datetime import datetime
from odoo.tools.safe_eval import safe_eval

from odoo import exceptions
import collections

import requests
import pytz
import psycopg2

from datetime import datetime,date
from datetime import timedelta

from collections import defaultdict

ACCESS_TOKEN="access_token=1014170_YmUzZjhhNzY4MzVlZDFiN2Y2ODI5NzZhNGJlYjU2NDk4OTAzMGZjZTRmZmE5MzA1OTlkMTg3ZTQzMjMyYmFlZQ"
BASE_URL="https://webapi.timedoctor.com/v1.1/"
BASE_OAUTH_URL="https://webapi.timedoctor.com/oauth/v2/"
COMPANY_ID="1014170"
OWNER_ID="1842653"


_logger = logging.getLogger(__name__)




def call_timedoctor_oauth(self=None,type=None):

    icp_obj=self.env['ir.config_parameter']


    if type=='get_authorization_code':
    
        #check parameters
        try:
            timedoctor_redirect_url=icp_obj.get_param('timedoctor_redirect_url')
            timedoctor_authorization=icp_obj.get_param('timedoctor_authorization')
            timedoctor_client_id=icp_obj.get_param('timedoctor_client_id')            
        except:
            raise exceptions.Warning('Por favor, revisa timedoctor parametros timedoctor_redirect_url y timedoctor_authorization! Contactése con Admin!')            

        if timedoctor_authorization=='authorized':
            raise exceptions.Warning('Por favor, timedoctor authorization code ya existe! No se puede retirarlo nuevamente!') 

        #ok, every thing is ok
        url=BASE_OAUTH_URL+"auth?client_id=" + timedoctor_client_id + "&response_type=code&redirect_uri="+timedoctor_redirect_url +"&state=authorized"
        
        
        try:
            r=requests.get(url,verify=False)
            if r.status_code==200:
                data=r.json()
                _logger.info("timedoctor call get_authorization_code success with code %s, data %s",r.status_code,data)
                return True
            else:
                data=r.json()
                _logger.info("timedoctor call get_authorization_code failed with code %s, data %s, result %s",r.status_code,param_dict,data)
                return False
        
        except Exception as e:
            _logger.info("Error in timedoctor call  %s",str(e))
            return False  
                        
            
            
    if type=='get_refresh_access_token':
    
        #check parameters
        try:
            timedoctor_redirect_url=icp_obj.get_param('timedoctor_redirect_url')
            timedoctor_refresh_token=icp_obj.get_param('timedoctor_refresh_token')
            timedoctor_client_id=icp_obj.get_param('timedoctor_client_id')
            timedoctor_client_secret=icp_obj.get_param('timedoctor_client_secret') 
            timedoctor_code=icp_obj.get_param('timedoctor_code')            
        except:
            raise exceptions.Warning('Por favor, revisa timedoctor parametros redirect_url, refresh_token, client_id, client_secret! Contactése con Admin!')            

        if timedoctor_refresh_token!='False':
            raise exceptions.Warning('Por favor, timedoctor refresh token ya existe! No se puede retirarlo nuevamente!') 

        #ok, every thing is ok
        url=BASE_OAUTH_URL+"token?client_id=" + timedoctor_client_id + "&client_secret="+timedoctor_client_secret +"&grant_type=authorization_code&redirect_url="+timedoctor_redirect_url +"&code=" + timedoctor_code
        
        
        try:
            r=requests.get(url,verify=False)
            if r.status_code==200:
                data=r.json()
                _logger.info("timedoctor call get_refresh_access_token success with code %s, data %s",r.status_code,data)
                return True
            else:
                data=r.json()
                _logger.info("timedoctor call get_refresh_access_token failed with code %s, data %s, result %s",r.status_code,param_dict,data)
                return False
        
        except Exception as e:
            _logger.info("Error in timedoctor call  %s",str(e))
            return False             
            
                       


    if type=='get_new_access_token':
    
        #check parameters
        try:
            timedoctor_refresh_token=icp_obj.get_param('timedoctor_refresh_token')
            timedoctor_client_id=icp_obj.get_param('timedoctor_client_id')
            timedoctor_client_secret=icp_obj.get_param('timedoctor_client_secret')           
        except:
            raise exceptions.Warning('Por favor, revisa timedoctor parametros refresh_token, client_id, client_secret! Contactése con Admin!')            

        if timedoctor_refresh_token=='False':
            raise exceptions.Warning('Por favor, timedoctor refresh token no existe! No se puede retirarlo nuevamente!') 

        #ok, every thing is ok
        url=BASE_OAUTH_URL+"token?client_id=" + timedoctor_client_id + "&client_secret="+timedoctor_client_secret +"&grant_type=refresh_token&refresh_token=" + timedoctor_refresh_token
        
        
        try:
            r=requests.get(url,verify=False)
            if r.status_code==200:
                data=r.json()
                _logger.info("timedoctor call get_new_access_token success with code %s, data %s",r.status_code,data)
                return data
            else:
                data=r.json()
                _logger.info("timedoctor call get_new_access_token failed with code %s, data %s, result %s",r.status_code,data)
                return False
        
        except Exception as e:
            _logger.info("Error in timedoctor call  %s",str(e))
            return False  





def call_timedoctor(self=None,type=None,param_dict={}):



    icp_obj=self.env['ir.config_parameter']
    timedoctor_access_token=icp_obj.get_param('timedoctor_access_token')
    
    ACCESS_TOKEN='='.join(('access_token',timedoctor_access_token))
    COMPANY_ID=icp_obj.get_param('timedoctor_company_id')
    OWNER_ID=icp_obj.get_param('timedoctor_owner_id')    

    if type=='create_project':    #param_dict={'project_name':"",assign_users:[1,2,3,4...]
    
        url=BASE_URL+"companies/"+COMPANY_ID+"/"+"users/"+OWNER_ID+"/projects?"+ACCESS_TOKEN
        data=param_dict
        
        try:
            r=requests.post(url,data,verify=False)
            if r.status_code==201:
                data=r.json()
                _logger.info("timedoctor call create_project success with code %s, data %s",r.status_code,data)
                return data
            else:
                data=r.json()
                _logger.info("timedoctor call create_project failed with code %s, data %s, result %s",r.status_code,param_dict,data)
                return False
        
        except Exception as e:
            _logger.info("Error in timedoctor call create_project %s",str(e))
            return False



    elif type=='get_project_id':

        url=BASE_URL+"companies/"+COMPANY_ID+"/"+"users/"+OWNER_ID+"/projects?"+ACCESS_TOKEN + "&_format=json&limit=500&all=1"
        data=param_dict

        try:
            r=requests.get(url,verify=False)
            if r.status_code==200:
                data=r.json()
                _logger.info("timedoctor call get_project_id success with code %s, data %s",r.status_code,data)
                return data
            else:
                data=r.json()
                _logger.info("timedoctor call get_project_id failed with code %s, data %s, result %s",r.status_code,param_dict,data)
                return False
        
        except Exception as e:
            _logger.info("Error in timedoctor call get_project_id %s",str(e))
            return False
            

    elif type=='get_all_project_id':

        url=BASE_URL+"companies/projects?"+ACCESS_TOKEN + "&_format=json&limit=500&all=1"
        data=param_dict

        try:
            r=requests.get(url,verify=False)
            if r.status_code==200:
                data=r.json()
                _logger.info("timedoctor call get_project_id success with code %s, data %s",r.status_code,data)
                return data
            else:
                data=r.json()
                _logger.info("timedoctor call get_project_id failed with code %s, data %s, result %s",r.status_code,param_dict,data)
                return False
        
        except Exception as e:
            _logger.info("Error in timedoctor call get_project_id %s",str(e))
            return False            
            
    elif type=='get_all_user_id':

        url=BASE_URL+"companies/"+COMPANY_ID+"/"+"users?"+ACCESS_TOKEN + "&_format=json&limit=500"
        data=param_dict

        try:
            r=requests.get(url,verify=False)
            if r.status_code==200:
                data=r.json()
                _logger.info("timedoctor call get_all_user_id success with code %s, data %s",r.status_code,data)
                return data
            else:
                data=r.json()
                _logger.info("timedoctor call get_all_user_id failed with code %s, data %s, result %s",r.status_code,param_dict,data)
                return False
        
        except Exception as e:
            _logger.info("Error in timedoctor call get_all_user_id %s",str(e))
            return False   



    elif type=='assign_project_users':

        PROJECT=param_dict['project']
        url=BASE_URL+"companies/"+COMPANY_ID+"/"+"users/"+OWNER_ID+"/projects"+"/"+str(PROJECT)+"?"+ACCESS_TOKEN
        data={'assign_users':param_dict['assign_users']}
        
        _logger.info("assign_project_users=%s,%s",url,data)
        try:
            r=requests.put(url,data,verify=False)
            _logger.info("assign_project_users_response=%s",r)
            if r.status_code==200:
                data=r.json()
                _logger.info("timedoctor call assign_project_users success with code %s, data %s",r.status_code,data)
                return data
            else:
                data=r.json()
                _logger.info("timedoctor call assign_project_users failed with code %s, data %s, result %s",r.status_code,param_dict,data)
                return False
        
        except Exception as e:
            _logger.info("Error in timedoctor call assign_project_users %s",str(e))
            return False        


    elif type=='get_project_worklog':
    
        PROJECT_IDS=str(param_dict['project_ids'])
        START_DATE=param_dict['start_date']
        END_DATE=param_dict['end_date']
        OFFSET=str(param_dict['offset'])

        _logger.info("params=%s",param_dict)

        url=BASE_URL+"companies/"+COMPANY_ID+"/"+"worklogs?"+ACCESS_TOKEN+"&_format=json&limit=500&offset="+OFFSET+"&start_date="+START_DATE+"&end_date="+END_DATE+"&project_ids="+PROJECT_IDS+"&consolidated=0"

        _logger.info("get_project_workload=%s",url)
        try:
            r=requests.get(url,verify=False)
            if r.status_code==200:
                data=r.json()
                _logger.info("timedoctor call get_project_workload success with code %s, data %s",r.status_code,data)
                return data
            else:
                data=r.json()
                _logger.info("timedoctor call get_project_workload failed with code %s, data %s, result %s",r.status_code,param_dict,data)
                return False
        
        except Exception as e:
            _logger.info("Error in timedoctor call get_project_workload %s",str(e))
            return False



#add timedoctor_id fields to models

class res_users(models.Model):
    _inherit='res.users'
       
    timedoctor_id=fields.Integer(string='Timedoctor_id')


class project_project(models.Model):
    _inherit='project.project'
        
    timedoctor_id=fields.Integer(string='Timedoctor_id')
    workload_id=fields.One2many('project.worklog','project_id', string='TD Worklog')
    
    
    @api.multi
    def timedoctor_get_project_worklog(self,start_date='2020-01-01',end_date='2020-12-31'):
    
        worklog_obj=self.env['project.worklog']
        task_obj=self.env['project.task']
        log_obj=self.env['project.refresh.log']
        
        for rec in self:
            project_ids=rec.timedoctor_id
            
            res=call_timedoctor(self,'get_project_worklog',{'project_ids':project_ids,'start_date':start_date,'end_date':end_date,'offset':0})
            if not res:
                raise exceptions.Warning('Bajar Worklog no exitosa! Contactése con Admin!')
            else:
                worklog_items=res['worklogs']['items']
                count=res['worklogs']['count']
                
                #loop over pages result
                counter=int(round(500/float(count)))
                for x in range(counter):
                    offset=500*(x+1)+1
                    res=call_timedoctor(self,'get_project_worklog',{'project_ids':project_ids,'start_date':start_date,'end_date':end_date,'offset':offset})
                    if not res:
                        raise exceptions.Warning('Bajar Worklog no exitosa! Contactése con Admin!')
                    else:
                        if res['worklogs'].get('items', False):
                            worklog_items+=res['worklogs']['items']                
                         
                values={}
                for item in worklog_items:
                    #search for TD_id
                    worklog=rec.env['project.worklog'].search([('td_id','=',int(item['id']))])
                    if worklog:
                        worklog.td_length=int(item['length'])
                        
                        user_id=rec.env['res.users'].search([('timedoctor_id','=',int(item['user_id']))])
                        worklog.user_id=user_id
                        local = pytz.timezone (worklog.user_id.partner_id.tz or self.env.user.partner_id.tz)
                        start_naive = datetime.strptime (item['start_time'], "%Y-%m-%d %H:%M:%S")+timedelta(hours=1)
                        end_naive = datetime.strptime (item['end_time'], "%Y-%m-%d %H:%M:%S")+timedelta(hours=1)
                        
                        start_local_dt = local.localize(start_naive, is_dst=True)
                        end_local_dt=local.localize(end_naive, is_dst=True)
                        
                        start_time = start_local_dt.astimezone(pytz.utc)
                        end_time = end_local_dt.astimezone(pytz.utc)
                        
                        worklog.td_start_time=start_time
                        worklog.td_end_time=end_time
                    else:
                        user_id=rec.env['res.users'].search([('timedoctor_id','=',int(item['user_id']))])
                        local = pytz.timezone (user_id.partner_id.tz or self.env.user.partner_id.tz)
                        start_naive = datetime.strptime (item['start_time'], "%Y-%m-%d %H:%M:%S")+timedelta(hours=1)
                        end_naive = datetime.strptime (item['end_time'], "%Y-%m-%d %H:%M:%S")+timedelta(hours=1)
                        
                        start_local_dt = local.localize(start_naive, is_dst=True)
                        end_local_dt=local.localize(end_naive, is_dst=True)
                        
                        start_time = start_local_dt.astimezone(pytz.utc)
                        end_time = end_local_dt.astimezone(pytz.utc)                        
                        
                        values['name']=item['task_name']
                        values['td_length']=int(item['length'])
                        values['td_start_time']=start_time
                        values['td_end_time']=end_time
                        values['td_id']=int(item['id'])
                        values['td_user_id']=int(item['user_id'])
                        values['td_task_id']=int(item['task_id'])
                        values['td_project_id']=int(item['project_id'])

                        values['user_id']=user_id and user_id.id or False
                        values['project_id']=rec.id or False
                        
                        if values['td_length']>60:
                            worklog=worklog_obj.create(values)
                        else:
                            worklog=None
                        
                    #find WBS for this worklog
                    if worklog:
                        domain=[('user_id','in',worklog.user_id.id),('date_start','<=',worklog.td_start_time),('date_end','>=',worklog.td_end_time),('project_id','=',rec.id)]
                        wbs=task_obj.search(domain)
                        if wbs:
                            worklog.task_id=wbs[0]
                        else:
                            message='Error Timedoctor: No hay WBS para Usuario ' + (worklog.user_id.login or item['user_id']) +', Fecha:'+worklog.td_start_time+', Proyecto:' +str(rec.id)
                            log=log_obj.create({'results':rec.project_reference,'message':message})
                        
    
    
    @api.multi
    def timedoctor_assign_project_users(self):
        for rec in self:
            assign_users=[]
            project=rec.timedoctor_id
            
            if rec.tasks:
                for task in rec.tasks:
                    assign_users+=[u.timedoctor_id for u in task.user_id]
    
            res=call_timedoctor(self,'assign_project_users',{'project':project,'assign_users':assign_users})
            if not res:
                raise exceptions.Warning('Asignacion de Usuarios no exitosa! Contactése con Admin!')
    
    
    @api.multi
    def timedoctor_create_project(self):
        for rec in self:
            assign_users=[]
            project_name=rec.project_reference
            timedoctor_id=None
            
            if rec.tasks:
                for task in rec.tasks:
                    assign_users+=[u.timedoctor_id for u in task.user_id]
                
            res=call_timedoctor(self,'create_project',{'project[project_name]':project_name,'assign_users':assign_users})
            if res:
                timedoctor_id=res['id']
                res.timedoctor_id=timedoctor_id
                
                
    @api.multi        
    def timedoctor_get_project_id(self):
        for rec in self:
            assign_users=[]
            project_name=rec.project_reference
            timedoctor_id=None            
                
            res=call_timedoctor(self,'get_project_id',{})
            project_found=False
            if res:
                projects=res['projects']
                
                for project in projects:
                    if project['project_name']==project_name:
                        rec.timedoctor_id=project['project_id']
                        project_found=True
                        
            if not project_found:
                res=call_timedoctor(self,'get_all_project_id',{}) 
                if res:
                    projects=res['count']
                    
                    for project in projects:
                        if project['name']==project_name:
                            rec.timedoctor_id=project['id']
                            project_found=True                
                        
                        
            if not project_found:
                _logger.info("No hay Proyecto en Timedoctor con nombre %s,%s",project_name)
                raise exceptions.Warning("No hay Projecto en Timedoctor con esta referencia!")
                        
         
    @api.model        
    def timedoctor_get_all_project_id(self):

        proj_obj=self.env['project.project']
        
        res=False
        try:
        
            res=call_timedoctor(self,'get_all_project_id',{})
            
        except Exception as e:    
            _logger.info("InternalError in timedoctor_get_all_projects %s",str(e))
            return False            
           
        if res:
            projects=res['count']
            
            for project in projects:
                proj_inst=proj_obj.search([('project_reference','=',project['name'])])
                if proj_inst:
                    proj_inst.timedoctor_id=project['id']
              
                else:
                    _logger.info("No hay Proyecto en Backoffice  con Timedoctor referencia %s",project['name'])                    
         

    @api.model        
    def timedoctor_get_all_user_id(self):

        user_obj=self.env['res.users']
        
        res=False
        try:        
            res=call_timedoctor(self,'get_all_user_id',{})
            
        except Exception as e:    
            _logger.info("InternalError in timedoctor_get_all_user_id %s",str(e))
            return False            
           
        if res:
            users=res['users']
            
            for user in users:
                user_inst=user_obj.with_context(active_test=False).search([('login','=',user['email'])])
                if user_inst:
                    user_inst.timedoctor_id=user['id']
              
                else:
                    _logger.info("No hay Usuario en Backoffice con Timedoctor email %s",user['email'])          
         

    @api.multi
    def timedoctor_create_timesheet(self):
    
        time_obj=self.env['hr.analytic.timesheet']
        work_obj=self.env['project.worklog']
        user_obj=self.env['res.users']
    
        for rec in self:
            worklogs=rec.workload_id.filtered(lambda r:not r.timesheet_id and r.task_id)
            worklog_hours=defaultdict(lambda:defaultdict(lambda:defaultdict(lambda:defaultdict(dict))))
            
            for work in worklogs:
                if worklog_hours.get(work.user_id.id,{}).get(work.td_start_time[:10],{}).get(work.name,{}).get(work.task_id.id,False):
                    worklog_hours[work.user_id.id][work.td_start_time[:10]][work.name][work.task_id.id]['seconds']+= work.td_length
                    worklog_hours[work.user_id.id][work.td_start_time[:10]][work.name][work.task_id.id]['ids'].append(work.id)                   
                else:
                    worklog_hours[work.user_id.id][work.td_start_time[:10]][work.name][work.task_id.id]['seconds']= work.td_length                
                    worklog_hours[work.user_id.id][work.td_start_time[:10]][work.name][work.task_id.id]['ids']= [work.id]                  
        
        
            _logger.info("worklog=%s,%s",worklog_hours,worklogs)
        
        
            #iterate over dict to get timesheet values
            for key1,value1 in worklog_hours.items():
                for key2,value2 in value1.items():
                    for key3,value3 in value2.items():
                        for key4,value4 in value3.items():

                            values={}
                            values['user_id']=key1
                            values['date']=key2
                            values['name']=key3
                            values['task_id']=key4
                            values['unit_amount']=round(float(value4['seconds'])/3600.0,2)
                            
                            #need to get analytic account id
                            values['account_id']=rec.analytic_account_id.id
                            
                            user=user_obj.browse(values['user_id'])
                            values['journal_id']=user.employee_id.journal_id.id
                            values['product_id']=user.employee_id.product_id.id
                            
                            #first search for record 
                            domain=[('user_id','=',key1),('date','=',key2),('name','=',key3),('task_id','=',key4),('account_id','=',rec.analytic_account_id.id)]
                            timesheet=time_obj.search(domain)
                            if timesheet:
                                timesheet.unit_amount+=values['unit_amount']
                            else:
                                timesheet=time_obj.sudo(values['user_id']).create(values)
                                
                                
                            #finally update worklog with timesheet id
                            work_lines=work_obj.browse(value4['ids'])
                            for line in work_lines:
                                line.timesheet_id=timesheet
   



    @api.multi
    def timedoctor_clean_project(self,start_date=None):


        project_obj=self.env['project.project']
        log_obj=self.env['project.refresh.log']
        icp_obj = self.env['ir.config_parameter']
        override_start_date=False
        override_end_date=False
    
        #if not start_date parameter then calculate first day of previous month

        last_day_of_prev_month = date.today().replace(day=1) - timedelta(days=1)
        start_day_of_prev_month = date.today().replace(day=1) - timedelta(days=last_day_of_prev_month.day)
        start_date=start_day_of_prev_month.strftime('%Y-%m-%d')

        #check for override in system parameters
        try:
            override_start_date=icp_obj.get_param('timedoctor_start_date')
        except Exception as e:
            _logger.info("Timedoctor start date no sobreescrito con parametro del sistema, %s",str(e))                     

        start_date=override_start_date or start_date                

        for project in self:

            #OK get all timesheet ids for worklog greater than or equal to start date

            try:
                worklogs=project.workload_id.filtered(lambda r:r.td_start_time>=start_date)
                if worklogs:
                    for wklog in worklogs:
                        if wklog.timesheet_id:
                            wklog.timesheet_id.unlink()

            except Exception as e:
                _logger.info("Timedoctor: no se podia eliminar partes de hora for proyecto %s, %s",project.id,str(e))      

            _logger.info("worklogdeletelist=%s",worklogs)
            
            try:
                for wklog in worklogs:
                    wklog.unlink()
            except Exception as e:
                _logger.info("Timedoctor: no se podia eliminar worklogs for proyecto %s, %s",project.id,str(e))                   
                            
                
    @api.multi
    def timedoctor_refresh_project(self):


        project_obj=self.env['project.project']
        log_obj=self.env['project.refresh.log']
        icp_obj = self.env['ir.config_parameter']
        override_start_date=False
        override_end_date=False
          
        for project in self:
            #try:
            
            #get startdate and enddate
            last_day_of_prev_month = date.today().replace(day=1) - timedelta(days=1)
            start_day_of_prev_month = date.today().replace(day=1) - timedelta(days=last_day_of_prev_month.day)
            start_date=start_day_of_prev_month.strftime('%Y-%m-%d')
            end_date = fields.Date.today()
            
                      
            #check for override in system parameters

            try:
                override_start_date=icp_obj.get_param('timedoctor_start_date')
            except Exception as e:
                _logger.info("Timedoctor start date no sobreescrito con parametro del sistema, %s",str(e))                     
            
            try:
                override_end_date=icp_obj.get_param('timedoctor_end_date')
            except Exception as e:
                _logger.info("Timedoctor end date no sobreescrito con parametro del sistema, %s",str(e))  
                            
        
        
            start_date=override_start_date or start_date
            end_date=override_end_date or end_date         
        
            project.timedoctor_clean_project(start_date)
            project.timedoctor_get_project_worklog(start_date,end_date)
            project.timedoctor_create_timesheet()
            
            message='Exito Timedoctor:' + 'desde:'+start_date+' hasta:' +end_date
            log=log_obj.create({'results':project.project_reference,'message':message})
                
            # except psycopg2.InternalError,e:
                # _logger.info("InternalError in timedoctor_refresh_project %s",str(e))
                
                
            # except Exception as e:    
                # _logger.info("InternalError in timedoctor_refresh_project %s",str(e))
                # pass

                
                
    #token functions

    
                
                
    @api.model
    def timedoctor_refresh_token(self):
    
        icp_obj = self.env['ir.config_parameter']
        res=call_timedoctor_oauth(self,'get_new_access_token')
        if not res:
            _logger.info("InternalError in timedoctor_refresh_token")
        else:
        
            _logger.info("timedoctor_refresh_token=%s",res)
            access_token=res.get('access_token',False)
            refresh_token=res.get('refresh_token',False)
            
            if access_token and refresh_token:
                icp_obj.set_param('timedoctor_access_token', access_token)
                icp_obj.set_param('timedoctor_refresh_token', refresh_token)
    


    @api.model            
    def timedoctor_refresh_all_projects(self):

        project_obj=self.env['project.project']
        log_obj=self.env['project.refresh.log']
        icp_obj = self.env['ir.config_parameter']
        override_start_date=False
        override_end_date=False
    
        
        project_ids= project_obj.search([('has_hours', '!=', False),('exclude_sql','=',False),('timedoctor_id','!=',0)], order='updated_index asc')
        _logger.info("timedoctor projectrefresh=%s,%s",[p.id for p in project_ids], [p.updated_index for p in project_ids])
        
        for project in project_ids:
            try:
            
                #get startdate and enddate
                #start_datetime = datetime.strptime (fields.Date.today(), "%Y-%m-%d")+timedelta(days=-1)
                #start_date = datetime.strftime (start_datetime, "%Y-%m-%d")
                
                #get startdate and enddate
                last_day_of_prev_month = date.today().replace(day=1) - timedelta(days=1)
                start_day_of_prev_month = date.today().replace(day=1) - timedelta(days=last_day_of_prev_month.day)
                
                start_date=start_day_of_prev_month.strftime('%Y-%m-%d')
                end_date = fields.Date.today()
                
                #check for override in system parameters

                try:
                    override_start_date=icp_obj.get_param('timedoctor_start_date')
                except Exception as e:
                    _logger.info("Timedoctor start date no sobreescrito con parametro del sistema, %s",str(e))                     
                
                try:
                    override_end_date=icp_obj.get_param('timedoctor_end_date')
                except Exception as e:
                    _logger.info("Timedoctor end date no sobreescrito con parametro del sistema, %s",str(e))  
                 

                start_date=override_start_date or start_date
                end_date=override_end_date or end_date                
                               
                project.timedoctor_clean_project(start_date)
                project.timedoctor_get_project_worklog(start_date,end_date)
                project.timedoctor_create_timesheet()
                
                message='Exito Timedoctor:' + 'desde:'+start_date+' hasta:' +end_date
                log=log_obj.create({'results':project.project_reference,'message':message})
                
            except psycopg2.InternalError as e:
                _logger.info("InternalError in timedoctor_refresh_all_projects %s",str(e))
                
                
            except Exception as e:    
                _logger.info("InternalError in timedoctor_refresh_all_projects %s",str(e))
                pass



    

         
                
    
class project_worklog(models.Model):
    _name='project.worklog'
    
    name=fields.Char('Nombre Tarea')
    project_id=fields.Many2one('project.project', string='Proyecto')
    user_id=fields.Many2one('res.users', string='Usuario')
    task_id=fields.Many2one('project.task', string='WBS')
    timesheet_id=fields.Many2one('account.analytic.line', string='Parte de hora')
    
    td_id=fields.Integer('TD_id')
    td_length=fields.Integer('TD_segundos')
    td_user_id=fields.Integer('TD_user_id')
    td_task_id=fields.Integer('TD_task_id')
    td_project_id=fields.Integer('TD_project_id')
    td_start_time=fields.Datetime('Hora inicio')
    td_end_time=fields.Datetime('Hora termino')
    
    
    
    


class hr_analytic_timesheet(models.Model):
    _inherit='account.analytic.line'
        
    timedoctor_id=fields.Integer(string='Timedoctor_id')
    
    
    
    
class ProjectTask(models.Model):
    _inherit = "project.task"


    def _progress_rate(self, cr, uid, ids, names, arg, context=None):
        """TODO improve code taken for OpenERP"""
        res = {}
        cr.execute("""SELECT task_id, COALESCE(SUM(unit_amount),0)
                        FROM account_analytic_line
                      WHERE task_id IN %s
                      GROUP BY task_id""", (tuple(ids),))
        hours = dict(cr.fetchall())
        for task in self.browse(cr, uid, ids, context=context):
            res[task.id] = {}
            res[task.id]['effective_hours'] = hours.get(task.id, 0.0)
            
            #opensolve the order of calculation means this is erroneous             
            #res[task.id]['total_hours'] = (
            #    task.remaining_hours or 0.0) + hours.get(task.id, 0.0)
            res[task.id]['total_hours']=task.planned_hours
           
            res[task.id]['delay_hours'] = res[task.id][
                'total_hours'] - task.planned_hours
            res[task.id]['progress'] = 0.0
            if (task.remaining_hours + hours.get(task.id, 0.0)):
                res[task.id]['progress'] = round(
                    100.0 * hours.get(task.id, 0.0) /
                    res[task.id]['total_hours'], 2)


                    
            #opensolve Prevent add more hours than planned
            #opensolve Remove limit for Timedoctor
            
            #if res[task.id]['effective_hours']>task.planned_hours:
            #    raise osv.except_osv(_('Warning!'), _('You are trying to enter more hours than planned for this activity ID \'%s\'. Max hours are \'%s\',\'%s\'')%(task.id,task.planned_hours,res[task.id]['effective_hours']))
                
                
    
    
    