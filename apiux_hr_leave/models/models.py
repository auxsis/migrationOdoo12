# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning,ValidationError,AccessDenied
from odoo.tools.translate import _
from odoo import tools

from collections import namedtuple
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY
from odoo.tools import float_compare
from odoo.tools.float_utils import float_round
from odoo.tools.safe_eval import safe_eval

import time,math
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from datetime import datetime, time
from pytz import timezone, UTC

import logging
_logger = logging.getLogger(__name__)

HOLIDAY_EXEMPTION_LIST=['Vacaciones']
HOLIDAY_SAMEDAY_LIST=['Administrativo', 'Medio_Dia_Administrativo', 'Trabajo_Remoto', 'Compensatorios', 'Medio_Dia_Compensatorio']
HOLIDAY_HALFDAY_LIST=['Medio_Dia_Administrativo', 'Medio_Dia_Compensatorio']

DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period')

class HrEmployee(models.Model):
    _inherit='hr.employee'
   
    is_outsourcing=fields.Boolean('Es outsourcing?',default=False)
    employee_type=fields.Selection([('staff','Staff'),('outsourcing','Outsourcing')], string='Tipo Empleado') 
    account_ejecutive=fields.Many2one('hr.employee', string='Account Executive')
    current_leave_state=fields.Selection([
                    ('draft', 'New'), 
                    ('cancel', 'Cancelled'),
                    ('signed','Signed'),
                    ('confirm', 'To Approve'), 
                    ('refuse', 'Refused'), 
                    ('validate', 'First Approval'),                   
                    ('validate1', 'Second Approval'),
                    ('validate2', 'Approved')],compute='_compute_leave_status', string="Current Leave Status")   

    @api.multi
    def write(self, values):
        res = super(models.Model, self).write(values)
        if 'parent_id' in values or 'department_id' in values:
            hr_vals = {}
            if values.get('parent_id') is not None:
                hr_vals['manager_id'] = values['parent_id']
            if values.get('department_id') is not None:
                hr_vals['department_id'] = values['department_id']
            holidays = self.env['hr.leave'].sudo().search([('state', 'in', ['draft', 'confirm']), ('employee_id', 'in', self.ids)])
            if holidays:
                holidays.write(hr_vals)
            allocations = self.env['hr.leave.allocation'].sudo().search([('state', 'in', ['draft', 'confirm']), ('employee_id', 'in', self.ids)])
            if allocations:
                allocations.write(hr_vals)
        return res



class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'
    
    
    @api.one
    @api.depends('name', 'description')
    def _compute_display_name(self):
        names = [self.name, self.description]
        self.display_name = ' '.join(filter(None, names)) 

    @api.multi
    def name_get(self):
 
        res = super(HrLeaveType, self).name_get()
        data = []
        for holiday in self:
            names = [holiday.name, holiday.description]
            display_value = ' '.join(filter(None, names))
            data.append((holiday.id, display_value))
        return data            
         
    
    
    @api.multi
    @api.depends('group_ids')
    def _compute_visible(self):
    
        for rec in self:
            visible=False
            for group in rec.group_ids:
                ext_id=group.get_external_id()
                if self.env.user.has_group(ext_id[group.id]):
                    visible=True
            
            rec.user_has_group=visible
            
            
    description=fields.Char('Description')
    name=fields.Char(translate=False)
    display_name = fields.Char(string='Name', compute='_compute_display_name')  
    group_ids=fields.Many2many('res.groups', string='Groups')
    user_has_group=fields.Boolean(compute=_compute_visible, default=False, string='Visible')
    

    
    
class HrHolidaysExemptions(models.Model):
    _name = 'hr.holidays.exemptions'
    
    name=fields.Char('Nombre')
    holiday_id=fields.Many2one('hr.leave', string="Peticion", ondelete='cascade')
    holiday_employee_id=fields.Many2one(related='holiday_id.employee_id', string='Empleado')
    holiday_state=fields.Selection(related='holiday_id.state', string='Peticion Estado')
    public_holiday_id=fields.Many2one('hr.public.holiday', string="Feriados", ondelete='cascade')    
    holiday_date=fields.Date('Fecha', required=True)
    holiday_type=fields.Selection([('weekend','Fin De Semana'),('public','Feriado')], string="Tipo")
    holiday_description=fields.Char('Descripcion', required=True)    
  


class HrHolidaysValidation(models.Model):
    _name='hr.holidays.validation'
    
    hr_holiday_id=fields.Many2one('hr.leave', string='Ausencia')
    validation_date=fields.Date('Fecha')
    state=fields.Selection([('signed','Signed'),('validate', 'First Approval'),('validate1', 'Second Approval'), ('validate2', 'Third Approval')],'Estatus', readonly=True, copy=False) 
    user_id=fields.Many2one('res.users', 'Aprobador')
    active=fields.Boolean('Activo?', default=False)  

  

class HrLeave(models.Model):
    _inherit = 'hr.leave'


    @api.depends('hr_holidays_validation_ids.state','hr_holidays_validation_ids.active')
    def _signed_employee(self):
    
        for rec in self:
            signed=False
            if rec.hr_holidays_validation_ids:
                signed_emp=rec.hr_holidays_validation_ids.filtered(lambda r: r.user_id==rec.employee_id.user_id and r.active==True)
                if len(signed_emp)>0:
                    signed=True

            rec.signed_employee=signed


    @api.depends('hr_holidays_validation_ids.validation_date','hr_holidays_validation_ids.user_id')
    def _signed_string(self):
    
        for rec in self:
            signed_string=''
            first_approval_string=''
            second_approval_string=''
            third_approval_string=''
            
            for line in rec.hr_holidays_validation_ids:
                if line.state=='signed':
                    signed_string='Firma Simple por {} el {}'.format(line.user_id.name,datetime.strftime(datetime.strptime(line.validation_date, "%Y-%m-%d"),"%d/%m/%Y"))
                if line.state=='validate1':
                    first_approval_string='Firma Simple por {} el {}'.format(line.user_id.name,datetime.strftime(datetime.strptime(line.validation_date, "%Y-%m-%d"),"%d/%m/%Y"))    
                if line.state=='validate2':
                    second_approval_string='Firma Simple por {} el {}'.format(line.user_id.name,datetime.strftime(datetime.strptime(line.validation_date, "%Y-%m-%d"),"%d/%m/%Y"))     
                if line.state=='third_validate':
                    third_approval_string='Firma Simple por {} el {}'.format(line.user_id.name,datetime.strftime(datetime.strptime(line.validation_date, "%Y-%m-%d"),"%d/%m/%Y")) 

            rec.signed_string=signed_string
            rec.first_approval_string=first_approval_string
            rec.second_approval_string=second_approval_string
            rec.third_approval_string=third_approval_string


    @api.depends('employee_id')
    def _get_available_holiday_status_id(self):
    
        visible=[]
        all_holidays=self.env['hr.leave.type'].sudo().search([])
        user = self.env['res.users'].browse(self.env.uid)
        for rec in all_holidays:
            for group in rec.group_ids:
                ext_id=group.get_external_id()
                if user.has_group(ext_id[group.id]):
                    visible.append(rec.id)
        all_holidays=self.env['hr.leave.type'].sudo().browse(visible)
        self.available_holiday_status_id=all_holidays.ids
  

    @api.multi
    @api.depends('holiday_status_id.name')
    def _get_holiday_type(self):
        for rec in self:
            if rec.holiday_status_id.name in ['Vacaciones','Administrativo','Medio_Dia_Administrativo','Compensatorios','Medio_Dia_Compensatorio']:
                rec.vacation_or_admin=True
                rec.licence_or_absence=False

                
            if rec.holiday_status_id.name in ['Licencia','Licencia_Accidente','Ausencias']:
                rec.licence_or_absence=True
                rec.vacation_or_admin=False
            

            if rec.holiday_status_id.name in ['Permiso','Trabajo_Remoto']:
                rec.licence_or_absence=False
                rec.vacation_or_admin=False     


  
    
    @api.depends('holiday_status_id')
    def _get_holiday_status_id(self):
    
        for rec in self:
            rec.alt_holiday_status_id=rec.holiday_status_id



    exemption_ids = fields.One2many('hr.holidays.exemptions','holiday_id',string="Feriados")
    holiday_status_name=fields.Char(related='holiday_status_id.name', string='Tipo')
    available_holiday_status_id=fields.Many2many('hr.leave.type',compute=_get_available_holiday_status_id)
    alt_holiday_status_id=fields.Many2one('hr.leave.type',compute=_get_holiday_status_id)
    state=fields.Selection([
                    ('draft', 'To Submit'), 
                    ('cancel', 'Cancelled'),
                    ('signed','Signed'),
                    ('confirm', 'For Approval'), 
                    ('refuse', 'Refused'), 
                    ('validate', 'First Approval'),                   
                    ('validate1', 'Second Approval'),
                    ('validate2', 'Final Approval')],
            'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
            help='The status is set to \'To Submit\', when a holiday request is created.\
            \nThe status is \'To Approve\', when holiday request is confirmed by user.\
            \nThe status is \'Refused\', when holiday request is refused by manager.\
            \nThe status is \'Approved\', when holiday request is approved by manager.')    
    first_approver_id = fields.Many2one(
        'hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the leave', oldname='manager_id')
    second_approver_id = fields.Many2one(
        'hr.employee', string='Second Approval', readonly=True, copy=False, oldname='manager_id2',
        help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)')    
    third_approver_id = fields.Many2one(
        'hr.employee', string='Third Approval', readonly=True, copy=False, oldname='manager_id3',
        help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)')   


    hr_holidays_validation_ids=fields.One2many('hr.holidays.validation','hr_holiday_id', string='Firmas Simples')
    signed_employee=fields.Boolean(compute=_signed_employee, default=False, store=True, string='Firma Empleado')
    
    signed_string=fields.Char(compute=_signed_string, string='Firmado Empleado')
    first_approval_string=fields.Char(compute=_signed_string, string='Firmado Primera Aprobador')
    second_approval_string=fields.Char(compute=_signed_string, string='Firmado Segunda Aprobador')
    third_approval_string=fields.Char(compute=_signed_string, string='Firmado Tercera Aprobador')   


    vacation_or_admin=fields.Boolean(compute='_get_holiday_type', default=False, string='Vacaciones/Admin', store=True)
    licence_or_absence=fields.Boolean(compute='_get_holiday_type', default=False, string='Licencia/Ausencia', store=True)      

    employee_outsourcing=fields.Boolean(related='employee_id.is_outsourcing', string='Empleado Outsourcing')
  
    second_validation=fields.Boolean(default=False, string='Apply Double Validation') 



    def _get_number_of_days(self, date_from, date_to,employee_id):
        """Returns a float equals to the timedelta between two dates given as string."""

        timedelta = date_to - date_from
        diff_day = timedelta.days + 1.0
        return diff_day 



    @api.onchange('request_date_from_period', 'request_hour_from', 'request_hour_to',
                  'request_date_from', 'request_date_to',
                  'employee_id','holiday_status_id')
    def _onchange_request_parameters(self):
        if not self.request_date_from:
            self.date_from = False
            return

        if self.holiday_status_id and self.holiday_status_id.name in HOLIDAY_SAMEDAY_LIST:
            self.request_date_to = self.request_date_from
            
        if self.holiday_status_id and self.holiday_status_id.name in HOLIDAY_HALFDAY_LIST:
            self.request_unit_half=True
        else:
            self.request_unit_half=False

        if self.request_unit_half or self.request_unit_hours:
            self.request_date_to = self.request_date_from

        if not self.request_date_to:
            self.date_to = False
            return

        domain = [('calendar_id', '=', self.employee_id.resource_calendar_id.id or self.env.user.company_id.resource_calendar_id.id)]
        attendances = self.env['resource.calendar.attendance'].read_group(domain, ['ids:array_agg(id)', 'hour_from:min(hour_from)', 'hour_to:max(hour_to)', 'dayofweek', 'day_period'], ['dayofweek', 'day_period'], lazy=False)

        # Must be sorted by dayofweek ASC and day_period DESC
        attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'], group['day_period']) for group in attendances], key=lambda att: (att.dayofweek, att.day_period != 'morning'))

        default_value = DummyAttendance(0, 0, 0, 'morning')

        # find first attendance coming after first_day
        attendance_from = next((att for att in attendances if int(att.dayofweek) >= self.request_date_from.weekday()), attendances[0] if attendances else default_value)
        # find last attendance coming before last_day
        attendance_to = next((att for att in reversed(attendances) if int(att.dayofweek) <= self.request_date_to.weekday()), attendances[-1] if attendances else default_value)

        if self.request_unit_half:
            if self.request_date_from_period == 'am':
                hour_from = float_to_time(attendance_from.hour_from)
                hour_to = float_to_time(attendance_from.hour_to)
            else:
                hour_from = float_to_time(attendance_to.hour_from)
                hour_to = float_to_time(attendance_to.hour_to)
        elif self.request_unit_hours:
            # This hack is related to the definition of the field, basically we convert
            # the negative integer into .5 floats
            hour_from = float_to_time(abs(self.request_hour_from) - 0.5 if self.request_hour_from < 0 else self.request_hour_from)
            hour_to = float_to_time(abs(self.request_hour_to) - 0.5 if self.request_hour_to < 0 else self.request_hour_to)
        elif self.request_unit_custom:
            hour_from = self.date_from.time()
            hour_to = self.date_to.time()
        else:
            hour_from = float_to_time(attendance_from.hour_from)
            hour_to = float_to_time(attendance_to.hour_to)

        tz = self.env.user.tz if self.env.user.tz and not self.request_unit_custom else 'UTC'  # custom -> already in UTC
        self.date_from = timezone(tz).localize(datetime.combine(self.request_date_from, hour_from)).astimezone(UTC).replace(tzinfo=None)
        self.date_to = timezone(tz).localize(datetime.combine(self.request_date_to, hour_to)).astimezone(UTC).replace(tzinfo=None)
        self._onchange_leave_dates()


    
    @api.onchange('date_from', 'date_to', 'employee_id')
    def _onchange_leave_dates(self):
    
        if self.date_from and self.date_to:          
            exemptions_cnt=0
            if self.holiday_status_id.name in HOLIDAY_EXEMPTION_LIST:                                
                exemptions_cnt,exemptions_list=self._get_exemption_list(self.date_from,self.date_to,self.employee_id.company_id.id)           
                
            self.number_of_days = max(0,self._get_number_of_days(self.date_from, self.date_to, self.employee_id.id)-exemptions_cnt)
        else:
            self.number_of_days = 0  

        if self.request_unit_half:
            self.number_of_days = 0.5        

    #get exemptions from list of public holidays
    def _get_exemption_list(self,from_dt,to_dt,company_id):
    
        pub_hol_obj=self.env["hr.public.holiday"]
        exemptions_list=[]
        exemptions_cnt=0
        delta = to_dt - from_dt
        
        #only do exemptions if holiday type vacations      
        for day in range(0, int(delta.days+1)):
        
            values={}
            day_datetime=from_dt + timedelta(days=day)
            day_date = datetime.strftime(day_datetime,"%Y-%m-%d")
            
            #is weekend?  
            weekdayno = day_datetime.weekday()                
            if weekdayno>=5:
                values={'holiday_date':day_date,'holiday_type':'weekend','holiday_description':'Fin de Semana'}
                exemptions_list.append(values)
            else: # is feriado?
                domain=[('state','=','validate'),('date_from','<=',day_date),('date_to','>=',day_date),('company_id','=',company_id)]      
                ids=pub_hol_obj.search(domain)
                if len(ids)==1: #feriado found
                    values={'public_holiday_id':ids[0].id,'holiday_date':day_date,'holiday_type':'public','holiday_description':ids[0].name}
                    exemptions_list.append(values)
                elif len(ids)>1: #should be unique
                    raise models.ValidationError(('Para Fecha de Ausencia %s, hay dos Feriados que se coinciden! Por favor, revisar configuracion de Feriados' % (day_date,)))
                else:
                    pass
        exemptions_cnt=len(exemptions_list)    
        return exemptions_cnt,exemptions_list    
         
            


    @api.model
    def create(self, vals):

        #get company from employee..obligatory field
        emp_id=vals.get("employee_id",1)
        emp=self.env["hr.employee"].browse([emp_id])
        company_id=emp.company_id.id or 1
    
        holiday_status_id=vals.get("holiday_status_id",None)
        if holiday_status_id:
            holiday_type=self.env["hr.leave.type"].browse([holiday_status_id])
            
        if holiday_type and holiday_type.name in HOLIDAY_EXEMPTION_LIST:   
    
            #get dates from vals..they are both obligatory
            date_from=vals["request_date_from"]
            date_to=vals["request_date_to"]
            
            DATETIME_FORMAT = "%Y-%m-%d"
            from_dt = datetime.strptime(date_from[:10], DATETIME_FORMAT)
            to_dt = datetime.strptime(date_to[:10], DATETIME_FORMAT)            
            
            exemptions_cnt,exemptions_list=self._get_exemption_list(from_dt,to_dt,company_id)
                        
            #add child records to vals
            if exemptions_cnt>0:
                vals["exemption_ids"]=[(0,0, exempt) for exempt in exemptions_list]
                
        
        res=super(HrLeave, self).create(vals)
        return res        
        
    @api.multi
    def write(self,vals): 

        emp_id=vals.get("employee_id",self.employee_id.id)
        emp=self.env["hr.employee"].browse([emp_id])
        company_id=emp.company_id.id or 1

    
        holiday_status_id=vals.get("holiday_status_id",self.holiday_status_id.id)
        if holiday_status_id:
            holiday_type=self.env["hr.leave.type"].browse([holiday_status_id])

        #remove exemptions by default, readd if necessary
        if self.exemption_ids:
            for exemption in self.exemption_ids:
                exemption.unlink()


        _logger.info("hrvals=%s",vals)

        DATETIME_FORMAT = "%Y-%m-%d"


        date_from=vals.get("date_from",datetime.strftime(self.date_from,DATETIME_FORMAT))[:10]
        date_to=vals.get("date_to",datetime.strftime(self.date_to,DATETIME_FORMAT))[:10]    


        from_dt = datetime.strptime(date_from, DATETIME_FORMAT)
        to_dt = datetime.strptime(date_to, DATETIME_FORMAT)
             
        if holiday_type and holiday_type.name in HOLIDAY_EXEMPTION_LIST:   
            #get dates from vals..they are both obligatory
                    
            exemptions_cnt,exemptions_list=self._get_exemption_list(from_dt,to_dt,company_id)
            #add child records to vals
            if exemptions_cnt>0:
                vals["exemption_ids"]=[(0,0, exempt) for exempt in exemptions_list]

        res=super(HrLeave, self).write(vals)
        return res     
    
    
    def signed(self):
    
        #create wizard record and launch wizard
        approve_obj=self.env['hr.holidays.approve.wizard']
        values={'hr_holiday_id':self.id,'approve_stage':'signed'}
        values['approve_message']='<p style="text-align: center;"><span style="color: #ff0000;">Usted esta a punto de firmar mediante la Firma Electronica Simple,</span></p><p style="text-align: center;"><span style="color: #ff0000;">que autentica la validez del esta petici&oacute;n. Quiere seguir?</span></p>'
        
        approve_rec=approve_obj.create(values)
        
        cform = self.env.ref('apiux_hr_leave.hr_holidays_approve_wizard_form', False)
        action = {
            'type': 'ir.actions.act_window',
            'id':'hr_holidays_approve_wizard_form',
            'name': 'Firma Electronica Simple',
            'res_model': 'hr.holidays.approve.wizard',
            'src_model': 'hr.leave',
            'res_id':approve_rec.id,
            'target':'new',
            'view_id':cform.id,
            'view_mode': 'form',
            'view_type':'form',
            'views': [(cform.id, 'form')],
            }
        return action      
    
    
    def confirm(self):
        obj_emp = self.env['hr.employee']
        conf_obj=self.env['ir.config_parameter']
    

    
        for record in self:
        
            approve1=False
            approve2=False
            approve3=False        
        
        
            #find first approver from  rr_hh configuration option
            rrhh_manager_id=conf_obj.get_param('rrhh_leave_employee_approve_id')
            ids2 = obj_emp.search([('id', '=', rrhh_manager_id)])
            approve1 = ids2 and ids2[0] or False
            
            #if staff then second approver is jefe directo
            if record.employee_id.employee_type=='staff':
                ids2 = obj_emp.search([('id', '=', self.employee_id.account_ejecutive.id)])
                approve2 = ids2 and ids2[0] or False
                if not approve2:
                    raise ValidationError(('''Este petición se requiere otra aprobacion, pero el empleado no cuenta con Ejectutiva de Cuenta '''))   
             
            else:
                ids2 = obj_emp.search([('id', '=', self.employee_id.parent_id.id)])
                approve2 = ids2 and ids2[0] or False
                if not approve2:
                    raise ValidationError(('''Este petición se requiere otra aprobacion, pero el empleado no cuenta con Jefe directo''')) 
                
                controller_approve_id=conf_obj.get_param('rrhh_leave_controller_employee_approve_id')
                
                #now lets find third approver. In this case will be the controller de operations
                ids3 = obj_emp.search([('id', '=', controller_approve_id)])
                approve3 = ids3 and ids3[0] or False
                    
                if not approve3:
                    raise ValidationError(('''No hay Controlador de Outsourcing especificado! Por favor, contactése con el Admin del sistema'''))    



        return self.write({'state': 'confirm','first_approver_id':approve1 and approve1.id or False,'second_approver_id':approve2 and approve2.id or False,'third_approver_id':approve3 and approve3.id or False}) 
    



    def validate(self):
       
        obj_emp = self.env['hr.employee']
        conf_obj=self.env['ir.config_parameter']
        override_approve_uids=safe_eval(conf_obj.get_param('rrhh_leave_override_approve_id'))
    
        #introduce check to make sure only manager can approve    
        if self.first_approver_id.user_id.id!=self.env.uid and self.first_approver_id.parent_id.user_id.id!=self.env.uid and self.env.uid not in override_approve_uids:
            raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden aprobar esta peticion de ausencia''')  % (self.first_approver_id.name,self.first_approver_id.parent_id.name))         

        #create wizard record and launch wizard
        approve_obj=self.env['hr.holidays.approve.wizard']
        values={'hr_holiday_id':self.id,'approve_stage':'validate'}
        values['approve_message']='<p style="text-align: center;"><span style="color: #ff0000;">Usted esta a punto de Aprobar mediante la Firma Electronica Simple,</span></p><p style="text-align: center;"><span style="color: #ff0000;">que autentica la validez del esta petici&oacute;n. Quiere seguir?</span></p>'
        
        approve_rec=approve_obj.create(values)
        
        cform = self.env.ref('apiux_hr_leave.hr_holidays_approve_wizard_form', False)
        action = {
            'type': 'ir.actions.act_window',
            'id':'hr_holidays_approve_wizard_form',
            'name': 'Firma Electronica Simple',
            'res_model': 'hr.holidays.approve.wizard',
            'src_model': 'hr.leave',
            'res_id':approve_rec.id,
            'target':'new',
            'view_id':cform.id,
            'view_mode': 'form',
            'view_type':'form',
            'views': [(cform.id, 'form')],
            }
        return action  



    def validate1(self):
       
        obj_emp = self.env['hr.employee']
    
        #introduce check to make sure only manager can approve    
        conf_obj=self.env['ir.config_parameter']
        override_approve_uids=safe_eval(conf_obj.get_param('rrhh_leave_override_approve_id'))
    
        #introduce check to make sure only manager can approve    
        if self.second_approver_id.user_id.id!=self.env.uid and self.second_approver_id.parent_id.user_id.id!=self.env.uid and self.env.uid not in override_approve_uids: 
            raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden aprobar esta peticion de ausencia''')  % (self.second_approver_id.name,self.second_approver_id.parent_id.name))              

        #create wizard record and launch wizard
        approve_obj=self.env['hr.holidays.approve.wizard']
        values={'hr_holiday_id':self.id,'approve_stage':'validate1'}
        values['approve_message']='<p style="text-align: center;"><span style="color: #ff0000;">Usted esta a punto de Aprobar mediante la Firma Electronica Simple,</span></p><p style="text-align: center;"><span style="color: #ff0000;">que autentica la validez del esta petici&oacute;n. Quiere seguir?</span></p>'
        
        approve_rec=approve_obj.create(values)
        
        cform = self.env.ref('apiux_hr_leave.hr_holidays_approve_wizard_form', False)
        action = {
            'type': 'ir.actions.act_window',
            'id':'hr_holidays_approve_wizard_form',
            'name': 'Firma Electronica Simple',
            'res_model': 'hr.holidays.approve.wizard',
            'src_model': 'hr.holidays',
            'res_id':approve_rec.id,
            'target':'new',
            'view_id':cform.id,
            'view_mode': 'form',
            'view_type':'form',
            'views': [(cform.id, 'form')],
            }
        return action        
    
    
    
    
    def validate2(self):
       
        obj_emp = self.env['hr.employee']
        conf_obj=self.env['ir.config_parameter']
        override_approve_uids=safe_eval(conf_obj.get_param('rrhh_leave_override_approve_id'))        
    
        
        for record in self:

            if record.third_approver_id.user_id.id!=self.env.uid and record.third_approver_id.parent_id.user_id.id!=self.env.uid and record.employee_id.parent_id.user_id.id!=self.env.uid and self.env.uid not in override_approve_uids:
                raise ValidationError(('''Solo %s,su Jefe Directo, %s, o el Jefe Directo del Empleado, %s pueden aprobar esta peticion de ausencia''')  % (record.third_approver_id.name,record.third_approver_id.parent_id.name,record.employee_id.parent_id.name))
                            
                            
        #create wizard record and launch wizard
        approve_obj=self.env['hr.holidays.approve.wizard']
        values={'hr_holiday_id':self.id,'approve_stage':'validate2'}
        values['approve_message']='<p style="text-align: center;"><span style="color: #ff0000;">Usted esta a punto de Final Aprobacion mediante la Firma Electronica Simple,</span></p><p style="text-align: center;"><span style="color: #ff0000;">que autentica la validez del esta petici&oacute;n. Quiere seguir?</span></p>'
        
        approve_rec=approve_obj.create(values)
        
        cform = self.env.ref('apiux_hr_leave.hr_holidays_approve_wizard_form', False)
        action = {
            'type': 'ir.actions.act_window',
            'id':'hr_holidays_approve_wizard_form',
            'name': 'Firma Electronica Simple',
            'res_model': 'hr.holidays.approve.wizard',
            'src_model': 'hr.leave',
            'res_id':approve_rec.id,
            'target':'new',
            'view_id':cform.id,
            'view_mode': 'form',
            'view_type':'form',
            'views': [(cform.id, 'form')],
            }
        return action 



    def reset(self):
        self.write({
            'state': 'draft',
            'first_approver_id': False,
            'second_approver_id': False,
            'third_approver_id': False,            
        })

        #remove electronic signatures from record
        for record in self:
            for rec in record.hr_holidays_validation_ids:
                rec.unlink()
  
        
        return True 



    def refuse(self):
        obj_emp = self.env['hr.employee']
        conf_obj=self.env['ir.config_parameter']
        ids2 = obj_emp.search([('user_id', '=', self.env.uid)])
        manager = ids2 and ids2[0] or False
        
        for record in self:

            rrhh_licence_reject_ids=conf_obj.get_param('rrhh_licence_reject_ids')
            if not self.env.uid in safe_eval(rrhh_licence_reject_ids):
                        
            
                if record.state=='confirm':
                    if record.first_approver_id:
                        if record.first_approver_id.user_id.id!=uid and record.first_approver_id.parent_id.user_id.id!=uid:
                            raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden rechazar esta peticion de ausencia''')  % (record.first_approver_id.name,record.first_approver_id.parent_id.name))            
                
                
                if record.state=='validate':
                    if record.second_approver_id:
                        if record.second_approver_id.user_id.id!=uid and record.second_approver_id.parent_id.user_id.id!=uid:
                            raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden rechazar esta peticion de ausencia''')  % (record.second_approver_id.name,record.second_approver_id.parent_id.name))

                if record.state=='validate1' or record.state=='validate2':
                    if record.second_approver_id:
                        if record.third_approver_id.user_id.id!=uid and record.third_approver_id.parent_id.user_id.id!=uid:
                            raise ValidationError(('''Solo %s o su Jefe Directo, %s pueden rechazar esta peticion de ausencia''')  % (record.third_approver_id.name,record.third_approver_id.parent_id.name))
            
            
            record.write({'state':'refuse'})
            record._remove_resource_leave()



class HrHolidaysApproveWizard(models.TransientModel):
    _name='hr.holidays.approve.wizard'


    hr_holiday_id=fields.Many2one('hr.leave', string='Ausencia')
    approve_stage=fields.Selection([('signed','Signed'),('validate', 'First Approval'),('validate1', 'Second Approval'), ('validate2', 'Third Approval')],'Estatus', readonly=True, copy=False) 
    
    approve_message=fields.Html('Aviso!')
    approve_username=fields.Char('Usuario', size=50, default=lambda self: self.env.user.login)
    approve_password=fields.Char('Contrasena', size=50)


    @api.multi
    def action_transfer(self):
    
        holiday_obj=self.env['hr.leave']
        user_obj=self.env['res.users']
        validation_obj=self.env['hr.holidays.validation']

        
        for rec in self:
        
            user_id = None
            #look for login 
            res = user_obj.search([('login','=',rec.approve_username)])
            _logger.info("userres=%s,%s,%s",res,rec.approve_username,rec.approve_password)
            if res:
                user_id=res[0]
                try:
                    user_id._check_credentials(rec.approve_password)
                
                except AccessDenied as a:
                    _logger.info("accesserrror=%s",str(a))
                    raise ValidationError(('Contrasena no correcta! Intenta nuevamente'))
        
            else:
                raise ValidationError('Usuario no correcto! Intenta nuevamente')        
        
            #create validation record
            try:
                values={}
                values['hr_holiday_id']=rec.hr_holiday_id.id
                values['validation_date']=fields.Date.today()
                values['state']=rec.approve_stage
                values['user_id']=user_id.id
                values['active']=True
                
                validation=validation_obj.create(values)
        
            except Exception as e:
                _logger.info("No se puede crear registro de validacion de ausencia por %s",str(e))
                raise Warning('No se puede crear registro de validacion! Por favor, contactése con el Admin del sistema') 
        
            holiday=rec.hr_holiday_id
            
            #update holiday status
            if rec.approve_stage=='signed':
                holiday.state='signed'
                
            if rec.approve_stage=='validate':
                holiday.state='validate'
                
            if rec.approve_stage=='validate1':
                if not holiday.third_approver_id:
                    holiday.state='validate2'
                    holiday._validate_leave_request()
                else:
                    holiday.state='validate1'
                

            if rec.approve_stage=='validate2':
                holiday.state='validate2'
                holiday._validate_leave_request()


class HrPublicHoliday(models.Model):
    _inherit = 'hr.public.holiday'    
    
    exemptions_ids = fields.One2many('hr.holidays.exemptions','public_holiday_id', string='Exenciones')      
    
    