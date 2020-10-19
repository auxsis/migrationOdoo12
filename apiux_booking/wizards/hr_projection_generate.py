from odoo import fields, models, api
import logging
import pytz
import operator
from odoo.addons import decimal_precision as dp
from odoo import exceptions
from isoweek import Week
from odoo import tools
from odoo import SUPERUSER_ID
import time,math
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%d"

class HrProjectionGenerate(models.TransientModel):
    _name = 'hr.proj.generate'
    _description = 'hr.proj.generate'

    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the timedelta between two dates given as string."""

        DATETIME_FORMAT = "%Y-%m-%d"
        from_dt = datetime.strptime((date_from or self.from_date)[:10], DATETIME_FORMAT)
        to_dt = datetime.strptime((date_to or self.to_date)[:10], DATETIME_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        return diff_day


    def _get_booking_values_staff(self, user_id,tuple_list):
        _logger.info("tuple_list=%s",tuple_list)
        booking_dict={}
        booking_dict['reviewer_id']=self.env.user.id
        booking_dict['user_id']=user_id
        booking_dict['from_date']=tuple_list[0][1]
        booking_dict['to_date']=tuple_list[-1][2]
        booking_dict['account_id']=tuple_list[0][0].project_id.id
        booking_dict['unit_amount']=8.5
        booking_dict['outsourcing_id']=[([x[0].id for x in tuple_list])]
        booking_dict['state']='draft'
        booking_dict['amount']=sum([x[0].quantity for x in tuple_list])
        booking_dict['confirm_type']='periodws'

        return booking_dict

    def _get_booking_values_task(self, user_id,tuple_list):
        _logger.info("tuple_list=%s",tuple_list)
        booking_dict={}
        booking_dict['reviewer_id']=self.env.user.id
        booking_dict['user_id']=user_id
        booking_dict['from_date']=tuple_list[0][1]
        booking_dict['to_date']=tuple_list[-1][2]
        booking_dict['account_id']=tuple_list[0][0].project_id.id
        booking_dict['unit_amount']=8.5
        booking_dict['task_id']=[([x[0].id for x in tuple_list])]
        booking_dict['state']='draft'
        booking_dict['amount']=sum([x[0].planned_hours for x in tuple_list])
        booking_dict['confirm_type']='periodns'

        return booking_dict

    @api.onchange('from_date','to_date','type','project_id')
    def onchange_date(self):
        task_obj=self.env['project.task']
        staff_obj=self.env['project.outsourcing']
        booking_list=[]

        if self.from_date and self.to_date:
            #do staffing first
            staff_dict={}
            domain=[('project_id','=',self.project_id.id),('period_id.date_start','>=',self.from_date),('period_id.date_stop','<=',self.to_date),('assignment_id','=', False)]
            staffs=staff_obj.search(domain)

            #sort staffs
            staffs=staffs.sorted(key=lambda r: datetime.strptime(r.period_id.date_start, DATETIME_FORMAT))

            #get task list by resource

            for staff in staffs:
                for user in staff.user_id:
                    if staff_dict.get(user.id,False):
                        staff_dict[user.id].append((staff,staff.period_id.date_start,staff.period_id.date_stop))

                    else:
                        staff_dict[user.id]=[]
                        staff_dict[user.id].append((staff,staff.period_id.date_start,staff.period_id.date_stop))

            #loop over dictionary to create bookings
            for user_id, staff_tuple_list in staff_dict.iteritems():
                tuple_list=[]
                for staff_tuple in staff_tuple_list:
                    if len(tuple_list)>0:
                        #get dates and check diff days
                        (_,_,date_stop_1)=tuple_list[-1]
                        (_,date_start,_)=staff_tuple

                        #if day diff > 1, create a new booking
                        if self._get_number_of_days(date_stop_1,date_start)>1:
                            booking_list.append(self._get_booking_values_staff(user_id,tuple_list))
                            tuple_list=[]
                        else:
                            tuple_list.append(staff_tuple)
                    else:

                        tuple_list.append(staff_tuple)

                #at end of list send last tuple
                if len(tuple_list)>0:
                    booking_list.append(self._get_booking_values_staff(user_id,tuple_list))

            #self.line_ids=[(0,0,line) for line in booking_list]

            #now do WBS

            task_dict={}
            domain1=[('project_id','=',self.project_id.id),('period_id.date_start','>=',self.from_date),('period_id.date_stop','<=',self.to_date),('hr_proj_timesheet_id','=', False)]
            #domain2=[('project_id','=',self.project_id.id),('period_id','=',False),('date_start','>=', self.date_start),('date_end','<=',self.date_end),('hr_proj_timesheet_id','=', False)]
            tasks=task_obj.search(domain1)
            #tasks2=task_obj.search(domain2)
            #take union
            #tasks=tasks1|tasks2
            task_dict={}
            _logger.info("tasks=%s",tasks)
            #sort and filter staffs
            tasks=tasks.filtered(lambda r: len(r.outsourcing_ids)==0)
            tasks=tasks.sorted(key=lambda r: datetime.strptime(r.period_id.date_start, DATETIME_FORMAT))
            _logger.info("tasks2=%s",tasks)
            #get task list by resource
            for task in tasks:
                for user in task.user_id:
                    if task_dict.get(user.id,False):
                        task_dict[user.id].append((task,task.period_id.date_start,task.period_id.date_stop))

                    else:
                        task_dict[user.id]=[]
                        task_dict[user.id].append((task,task.period_id.date_start,task.period_id.date_stop))

            #loop over dictionary to create bookings

            for user_id, task_tuple_list in task_dict.iteritems():


                tuple_list=[]

                for task_tuple in task_tuple_list:
                    if len(tuple_list)>0:

                        #get dates and check diff days
                        (_,_,date_stop_1)=tuple_list[-1]
                        (_,date_start,_)=task_tuple

                        #if day diff > 1, create a new booking
                        if self._get_number_of_days(date_stop_1,date_start)>1:
                            booking_list.append(self._get_booking_values_task(user_id,tuple_list))
                            tuple_list=[]
                        else:
                            tuple_list.append(task_tuple)

                    else:

                        tuple_list.append(task_tuple)

                #at end of list send last tuple
                if len(tuple_list)>0:
                    booking_list.append(self._get_booking_values_task(user_id,tuple_list))

            self.line_ids=[(0,0,line) for line in booking_list]

    @api.multi
    def action_generate(self):
        if not self.line_ids:
            raise exceptions.ValidationError(_('No hay Bookings por crearse! Elige otras Fechas y/o Proyecto!'))
        book_obj=self.env['hr.projection.timesheet']
        for line in self.line_ids:
            booking_dict={}
            temp_amount=line.amount
            booking_dict['reviewer_id']=line.reviewer_id.id
            booking_dict['user_id']=line.user_id.id
            booking_dict['from_date']=line.from_date
            booking_dict['to_date']=line.to_date
            booking_dict['account_id']=line.account_id.id
            booking_dict['unit_amount']=line.unit_amount
            booking_dict['state']='draft'
            booking_dict['confirm_type']=line.confirm_type
            booking_dict['source_type']='generated'
            _logger.info("booking_dict=%s",booking_dict)
            booking=book_obj.create(booking_dict)
            #calculate percentage
            booking.percentage=round((temp_amount/booking.amount)*100)
            if line.confirm_type=='periodws':
                for outsourcing in line.outsourcing_id:
                    outsourcing.assignment_id=booking.id
                    outsourcing.task_id.hr_proj_timesheet_id=booking.id
            else:
                for wbs in line.task_id:
                    wbs.hr_proj_timesheet_id=booking.id
            booking.state='confirm'

    from_date= fields.Date('From Date', select=True)
    to_date= fields.Date('To Date', select=True)
    type=fields.Selection((('week','Semanal'),('month','Mes')), string='Tipo')
    project_id= fields.Many2one('project.project', string='Proyecto')
    line_ids=fields.One2many('hr.proj.generate.line','hr_proj_generate_id', string='Lineas de Booking')

class HrProjectionGenerateLine(models.TransientModel):
    _name = 'hr.proj.generate.line'
    _description = 'hr.proj.generate.line'

    hr_proj_generate_id=fields.Many2one('hr.proj.generate', string='Padre')
    from_date= fields.Date('From Date', select=True,store=True)
    to_date= fields.Date('To Date', select=True, store=True)
    percentage= fields.Integer('Percentage', default=100, required=True)
    unit_amount= fields.Float('Horas/dia', help='Specifies the amount of quantity to count.')
    amount= fields.Float('Horas Total',help='Calculated by multiplying the quantity and the price given in the Product\'s cost price. Alway expressed in the company main currency.', digits=(6,2), store=True)
    account_id= fields.Many2one('project.project', string='Project', required=True, ondelete='restrict', select=True, domain=[('type','!=','view')])
    user_id= fields.Many2one('res.users', 'User')
    state=fields.Selection([('draft','Borrador'),('confirm','Confirmado')], default='draft', string='Estado')
    outsourcing_id=fields.Many2many('project.outsourcing', string='Staffing')
    task_id=fields.Many2many('project.task', string='WBS')
    active=fields.Boolean('Activo', default=True)
    reviewer_id= fields.Many2one('res.users', string='Solicitante', default=lambda self: self.env.user)
    confirm_type=fields.Selection([('draft','Borrador'),('periodns','Periodo No Staffing'),('periodws','Periodo Con Staffing'),('weekns','Semana No Staffing'),('weekws','Semana Con Staffing')], default='draft', string='Tipo Booking')

    _defaults = {
        'unit_amount':8.5,
    }
