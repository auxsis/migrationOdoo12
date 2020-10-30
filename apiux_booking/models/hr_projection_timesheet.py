# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from odoo.tools.translate import _
import logging
from odoo.addons import decimal_precision as dp
from odoo import exceptions
from isoweek import Week
from odoo import tools
from odoo import SUPERUSER_ID
import pytz
import pandas as pd
import operator
import time,math
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from functools import reduce

_logger = logging.getLogger(__name__)

class HrBookingExemptions(models.Model):
    _name = 'hr.booking.exemptions'
    _description = 'hr.booking.exemptions'

    name=fields.Char('Nombre')
    booking_id=fields.Many2one('hr.projection.timesheet', string="Booking", ondelete='cascade')
    booking_user_id=fields.Many2one(related='booking_id.user_id', string='Recurso')
    booking_state=fields.Selection(related='booking_id.state', string='Booking Estado')
    public_holiday_id=fields.Many2one('hr.public.holiday', string="Feriados", ondelete='cascade')
    booking_date=fields.Date('Fecha', required=True)
    booking_type=fields.Selection([('weekend','Fin De Semana'),('public','Feriado')], string="Tipo")
    booking_description=fields.Char('Descripcion', required=True)
    booking_exclude=fields.Boolean(default=False, string='Excluir?')

class HrBookingSchedule(models.Model):
    _name='hr.booking.schedule'
    _description = 'hr.booking.schedule'

    name=fields.Selection([('0','Lunes'),('1','Martes'),('2','Miercoles'),('3','Jueves'),('4','Viernes'),('5','Sabado'),('6','Domingo')], string='Dia')
    booking_id=fields.Many2one('hr.projection.timesheet', string="Booking", ondelete='cascade')
    quantity=fields.Float(string='Ctd. Horas', digits=(4,2))

class ProjectOutsourcing(models.Model):
    _inherit='project.outsourcing'

    @api.one
    @api.depends('task_id.name')
    def _compute_display_name(self):
        self.display_name = self.task_id.name
        
        
    @api.depends('assignment_id.unit_amount','quantity')
    def _compute_quantity_days(self):
        for rec in self:
            rec.quantity_days=round((rec.quantity/rec.assignment_id.unit_amount), 2)
    

    activity_type=fields.Many2one('project.task.activity.type',string='Activity Type',required=True,help='Pleas select an activity type for your tasks')
    assignment_id=fields.Many2one('hr.projection.timesheet', string='Asignacion de Staffing', ondelete='cascade')
    display_name = fields.Char(string='Nombre', compute='_compute_display_name')
    preinvoice_line_id=fields.One2many('account.pre_invoice.line','outsourcing_id','Linea Prefactura')
    quantity_days=fields.Float('Dias Proyectadas', compute=_compute_quantity_days)    

    @api.model
    def create(self, values):
        #Override the original create function for the res.partner model
        record = values
        _logger.info("createhpt=%s",values)        
        #call super to create outsourcing and task
        res=super(ProjectOutsourcing, self).create(record)
        #create project.pre.invoice
        pre_invoice_obj=self.env['project.pre.invoice']
        #is there a prefactura associated with this?
        domain=[('period_id','=', res.period_id.id),('invoice_type','=','t&m'),('project_id','=',res.project_id.id)]
        pre_invoice=pre_invoice_obj.search(domain, limit=1)


        if pre_invoice:
            res.projection_id=pre_invoice

        else:
            values={}
            values={'period_id':res.period_id.id,
                'currency_id':res.currency_id.id,
                'company_id':res.company_id.id,
                'amount':0.0,
                'projected_amount':0.0,
                'invoice_period':res.period_id.date_stop,
                'entry_date':res.period_id.date_stop,
                'invoice_type':'t&m',
                'project_id':res.project_id.id,
                }

            pre_invoice=pre_invoice_obj.create(values)
            res.projection_id=pre_invoice

        #now update amounts on pre_invoice
        pre_invoice.amount=sum([x.amount for x in pre_invoice.outsourcing_ids])
        pre_invoice.projected_amount=sum([x.projected_amount for x in pre_invoice.outsourcing_ids])
        return res

    @api.multi
    def write(self,values):
        record=values
        res=super(ProjectOutsourcing, self).write(record)

        #now we must update amounts for pre_invoice
        for ots in self:
            #and now update state based on state of staffing
            p={}
            p["draft"]=len([x for x in ots.projection_id.outsourcing_ids if x.state=='draft'])
            p["open"]=len([x for x in ots.projection_id.outsourcing_ids if x.state=='open'])
            p["done"]=len([x for x in ots.projection_id.outsourcing_ids if x.state=='done'])
            p["preinvoiced"]=len([x for x in ots.projection_id.outsourcing_ids if x.state=='preinvoiced'])
            p["invoiced"]=len([x for x in ots.projection_id.outsourcing_ids if x.state=='invoiced'])

            if ots.projection_id:
                ots.projection_id.state=max(p.items(), key=operator.itemgetter(1))[0]

    @api.multi
    def unlink(self):
        for record in self:
            prefactura=record.projection_id
            res= super(ProjectOutsourcing, record).unlink()
            if prefactura:
                prefactura.amount=sum([x.amount for x in prefactura.outsourcing_ids])
                prefactura.projected_amount=sum([x.projected_amount for x in prefactura.outsourcing_ids])
        
        return True



class hr_projection_timesheet(models.Model):
    _name = "hr.projection.timesheet"
    _description = 'Timesheet Projection Line'

    def _get_utc_date_from_utc_datetime(self, local, date):
        naive_date = datetime.strptime (date, "%Y-%m-%d %H:%M:%S")
        local_ds = local.localize(naive_date, is_dst=None)
        utc_ds = local_ds.astimezone(pytz.utc)
        utc_date=utc_ds.strftime ("%Y-%m-%d")
        return utc_date

    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the timedelta between two dates given as string."""
        DATETIME_FORMAT = "%Y-%m-%d"
        from_dt = datetime.strptime(str(date_from), DATETIME_FORMAT)
        to_dt = datetime.strptime(str(date_to), DATETIME_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        return diff_day

    def _calculate_quantity(self,start_date_str,end_date_str):
        
        """Returns  number_of_days: number of days between dates taking into account exemptions
                    total_hours: number of hours = number_of_days*unit_amount (number of hours in day)
                    percentage_hours:total_hours*percentage (percentage allocation of resource"""
        
        schedule={}
        number_of_hours=0
        number_of_hours_total=0
        number_of_days=0

        for rec in self.schedule_ids:
            schedule[rec.name]=rec.quantity

        exclude_list=[x.id for x in self.exemption_ids.filtered(lambda r:r.booking_exclude==True)]
        excluded_dates=[x.booking_date for x in self.env['hr.booking.exemptions'].browse(exclude_list)]

        #get exemption days
        DATETIME_FORMAT = "%Y-%m-%d"
        from_dt = datetime.strptime(str(start_date_str), DATETIME_FORMAT)
        to_dt = datetime.strptime(str(end_date_str), DATETIME_FORMAT)
        exemptions_cnt,exemptions_list=self._get_exemption_list(from_dt,to_dt,self.company_id)
        exemption_dates=[x["booking_date"] for x in exemptions_list]

        dt=pd.date_range(start_date_str,end_date_str).astype('str')

        for day_s in dt:
            if day_s not in exemption_dates:
                number_of_days+=1
                number_of_hours+=schedule.get(str(datetime.strptime(day_s, DATETIME_FORMAT).weekday()),self.unit_amount)
                number_of_hours_total+=self.unit_amount
            else:
                if day_s in excluded_dates:
                    number_of_days+=1
                    number_of_hours+=schedule.get(str(datetime.strptime(day_s, DATETIME_FORMAT).weekday()), self.unit_amount)
                    number_of_hours_total+=self.unit_amount

        percentage_hours=number_of_hours*self.percentage/100
        total_hours=number_of_hours_total
        return number_of_days,total_hours,percentage_hours

    @api.multi
    @api.onchange('week')
    @api.depends('week')
    def _onchange_week(self):
        for obs in self:
                obs.from_date=Week(int(obs.year),obs.week).monday()
                obs.to_date=Week(int(obs.year),obs.week).sunday()

    @api.multi
    @api.onchange('period')
    @api.depends('period')
    def _onchange_period(self):
        for obs in self:
                obs.from_date=obs.period.date_start
                obs.to_date=obs.period.date_stop

    @api.multi
    @api.depends('percentage','unit_amount','from_date','to_date','exemption_ids','schedule_ids')
    def _onchange_percentage(self):
        for obs in self:
            if obs.from_date and obs.to_date:
                #lets get schedule as dictionary
                obs.number_of_days_temp,_,obs.amount=obs._calculate_quantity(obs.from_date,obs.to_date)

    @api.multi
    @api.constrains('percentage')
    def _check_percentage(self):
        for obs in self:
            if obs.percentage<0:
                raise exceptions.ValidationError(_('Percentage must be greater than or equal to 0'))
            elif obs.percentage>100:
                raise exceptions.ValidationError(_('Percentage must be less than or equal to 100'))

    def _default_year(self):
        return str(datetime.now().year)

    def _default_week(self):
        return Week.thisweek().week

    @api.depends('user_id')
    def _compute_assignments(self):
        for obj in self:
            related_recordset = self.env["hr.projection.timesheet"].search([('user_id','=',obj.user_id.id)])
            obj.user_assignment_ids = related_recordset

    @api.multi
    @api.depends('user_assignment_ids','from_date','to_date')
    def _compute_assignment_hours(self):
        for obj in self:
            total=0
            assigned=0

            if obj.from_date and obj.to_date:
                assignments=obj.user_assignment_ids.filtered(lambda r: r.state=='confirm' and r.id!=obj.id and r.from_date<=obj.to_date and r.to_date>=obj.from_date)

                for assign in assignments:
                    if assign.from_date>=obj.from_date and assign.to_date<=obj.to_date:
                        assigned+=assign._calculate_quantity(assign.from_date,assign.to_date)[2]

                    if assign.from_date>=obj.from_date and assign.to_date>obj.to_date:
                        assigned+=assign._calculate_quantity(assign.from_date,obj.to_date)[2]

                    if assign.from_date<obj.from_date and assign.to_date>=obj.to_date:
                        assigned+=assign._calculate_quantity(obj.from_date,obj.to_date)[2]

                    if assign.from_date<obj.from_date and assign.to_date<obj.to_date:
                        assigned+=assign._calculate_quantity(obj.from_date,assign.to_date)[2]


                total=obj._calculate_quantity(obj.from_date,obj.to_date)[1]
            obj.user_assigment_hours=assigned
            obj.user_assigment_available=total-assigned
            obj.user_assigment_possible=total

    @api.onchange('to_date','from_date','company_id')
    def onchange_date_from(self):
        """
        If there are no date set for date_to, automatically set one 8 hours later than
        the date_from.
        Also update the number_of_days.
        """
        #check status
        _logger.info("state=%s",self.state)
        if self.state=='confirm':
            raise exceptions.ValidationError(_('A Booking in state Confirm cannot be changed. Please change state to Draft and try again.'))

        # date_to has to be greater than date_from
        if (self.from_date and self.to_date) and (self.from_date > self.to_date):
            raise exceptions.ValidationError(_('The start date must be anterior to the end date.'))

        # No date_to set so far: automatically compute one 8 hours later
        if self.from_date and not self.to_date:
            date_to_with_delta = datetime.strptime(str(self.from_date), tools.DEFAULT_SERVER_DATE_FORMAT) + timedelta(hours=8)
            self.to_date = str(date_to_with_delta)

        # Compute and update the number of days
        if (self.to_date and self.from_date) and (self.from_date <= self.to_date):
            diff_day = self._get_number_of_days(self.from_date, self.to_date)
            self.number_of_days_temp = round(math.floor(diff_day))+1
        else:
            self.number_of_days_temp = 0

        exemptions_list=[]
        exemptions_cnt=0
        if self.from_date and self.to_date:

            DATETIME_FORMAT = "%Y-%m-%d"
            from_dt = datetime.strptime(str(self.from_date), DATETIME_FORMAT)
            to_dt = datetime.strptime(str(self.to_date), DATETIME_FORMAT)

            exemptions_cnt,exemptions_list=self._get_exemption_list(from_dt,to_dt,self.company_id)

        self.number_of_days_temp = self.number_of_days_temp -exemptions_cnt


    def _get_exemption_list(self,from_dt,to_dt,company_id):
        """Returns holidays and weekends between two dates"""
    
   
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
                values={'booking_date':day_date,'booking_type':'weekend','booking_description':'Fin de Semana'}
                exemptions_list.append(values)
            else: # is feriado?
                domain=[('state','=','validate'),('date_from','<=',day_date),('date_to','>=',day_date),('company_id','=',company_id.id)]
                ids=pub_hol_obj.search(domain)
                if len(ids)==1: #feriado found
                    values={'public_holiday_id':ids[0].id,'booking_date':day_date,'booking_type':'public','booking_description':ids[0].name}
                    exemptions_list.append(values)
                elif len(ids)>1: #should be unique
                    raise models.ValidationError(('Para Fecha de Ausencia %s, hay dos Feriados que se coinciden! Por favor, revisar configuracion de Feriados' % (day_date,)))
                else:
                    pass

        exemptions_cnt=len(exemptions_list)
        return exemptions_cnt,exemptions_list

    @api.depends('task_id.planned_hours')
    def _get_task_planned_hours(self):
        for line in self:
            task_planned_hours=0
            if line.task_id:
                task_planned_hours=reduce((lambda x, y: x+y),[i.planned_hours for i in line.task_id])
                line.task_planned_hours=task_planned_hours

    @api.multi
    @api.depends('to_date')
    def _gantt_to_date(self):

        DATETIME_FORMAT = "%Y-%m-%d"
        for rec in self:
            if rec.to_date:
                to_date = datetime.strptime(rec.to_date, DATETIME_FORMAT)
                rec.gantt_to_date=datetime.strftime((to_date + timedelta(days=1)),DATETIME_FORMAT)

    @api.multi
    @api.depends('gantt_to_date')
    def _form_to_date(self):

        DATETIME_FORMAT = "%Y-%m-%d"
        for rec in self:
            if rec.gantt_to_date:
                to_date = datetime.strptime(rec.gantt_to_date, DATETIME_FORMAT)
                rec.to_date=datetime.strftime((to_date + timedelta(days=-1)),DATETIME_FORMAT)

    @api.multi
    @api.depends('amount','user_assigment_available')
    def _compute_overbooked(self):
        for rec in self:
            if rec.amount!=0 and rec.user_assigment_available!=0:
                if rec.amount>rec.user_assigment_available:
                    rec.overbooked_flag=True

    @api.multi
    @api.depends('amount','task_planned_hours')
    def _duplicate_amount(self):
        for rec in self:
            rec.amount_2=rec.amount
            rec.task_planned_hours_2=rec.task_planned_hours

    @api.multi
    @api.depends('user_id','user_id.employee_ids','user_id.employee_ids.employee_unlinked')
    def _compute_employee_unlinked(self):
        for booking in self:
            if booking.user_id.employee_ids and booking.user_id.employee_ids[0]:
                booking.employee_unlinked=booking.user_id.employee_ids[0] and booking.user_id.employee_ids[0].employee_unlinked
            else:
                booking.employee_unlinked=True

    name=fields.Char('Description', default='WBS', store=True) #, compute=_compute_name
    user_name=fields.Char('Description', default='WBS') #, compute=_compute_name
    from_date= fields.Date('From Date', select=True,store=True)
    to_date= fields.Date('To Date', select=True, store=True)
    gantt_to_date=fields.Date('To Date', compute=_gantt_to_date, inverse=_form_to_date)

    percentage= fields.Integer('Percentage', default=100, required=True)
    unit_amount= fields.Float('Horas/dia', default=8.5 ,help='Specifies the amount of quantity to count.')
    amount= fields.Float('Horas Total', compute="_onchange_percentage",help='Calculated by multiplying the quantity and the price given in the Product\'s cost price. Always expressed in the company main currency.', digits=(6,2), store=True)
    account_id= fields.Many2one('project.project', string='Project', required=True, ondelete='restrict', select=True) #domain=[('type','!=','view')]
    task_id=fields.One2many(comodel_name='project.task', inverse_name='hr_proj_timesheet_id',string='Tasks',store=True)
    user_id= fields.Many2one('res.users', 'User')
    employee_id= fields.One2many(related='user_id.employee_ids', string='Employee')
    employee_unlinked=fields.Boolean('Desvinculado', compute=_compute_employee_unlinked, store=True)
    company_id= fields.Many2one(related='account_id.company_id', string='Company', store=True, readonly=True)
    activity_type=fields.Many2one('project.task.activity.type',string='Activity Type',required=True,help='Pleas select an activity type for your tasks')
    year=fields.Selection((('2015','2015'),('2016','2016'),('2017','2017'),('2018','2018'),('2019','2019'),('2020','2020'),('2021','2021'),('2022','2022'),('2023','2023'),('2024','2024')),'Year', default=_default_year, required=False)
    week=fields.Integer('Week', size=2, required=False)
    period=fields.Many2one('account.period', string='Periodo')

    user_assignment_ids=fields.One2many('hr.projection.timesheet',compute='_compute_assignments', string='Bookings')

    user_assigment_possible=fields.Float('Horas Posibles dentro Fechas', compute='_compute_assignment_hours')
    user_assigment_hours=fields.Float('Horas Ya Asignados dentro Fechas', compute='_compute_assignment_hours')
    user_assigment_available=fields.Float('Horas Disponibles dentro Fechas', compute='_compute_assignment_hours')

    exemption_ids = fields.One2many('hr.booking.exemptions','booking_id',string="Feriados/Weekend")
    schedule_ids=fields.One2many('hr.booking.schedule','booking_id', string='Horario')

    number_of_days_temp=fields.Integer(string='Ctd. Dias')
    state=fields.Selection([('draft','Borrador'),('confirm','Confirmado')], default='draft', string='Estado')
    outsourcing_id=fields.One2many('project.outsourcing','assignment_id', 'Staffing')

    active=fields.Boolean('Activo', default=True)
    project_reference=fields.Char(related='account_id.project_reference', string='Ref. Proyecto', store=True)
    project_responsable=fields.Many2one(related='account_id.user_id', string='Resp. Proyecto', store=True)
    project_jp=fields.Many2one(related='account_id.manager_user_id', string='JP. Proyecto', store=True)

    project_sector=fields.Char( string="Sector", store=True) #default=_default_sector,compute=_compute_sector,
    project_client=fields.Many2one(related='account_id.partner_id', string='Cliente', store=True)

    reviewer_id= fields.Many2one('res.users', string='Solicitante', default=lambda self: self.env.user)
    task_planned_hours=fields.Float(compute="_get_task_planned_hours", string='WBS Total Horas')
    confirm_type=fields.Selection([('draft','Borrador'),('periodns','Periodo No Staffing'),('periodws','Periodo Con Staffing'),('weekns','Semana No Staffing'),('weekws','Semana Con Staffing')], default='draft', string='Tipo Booking')
    source_type=fields.Selection([('manual','Manual'),('generated','Generado')], string='Origen', default='manual')
    overbooked_flag=fields.Boolean(string='Flag', default=False, compute='_compute_overbooked',store=True)
    overbooked=fields.Html(string='', default="<b style='color:Tomato;'>OVERBOOKED</b>", readonly=1,store=True)

    amount_2=fields.Float(compute='_duplicate_amount', string='Booking Total Horas')
    task_planned_hours_2=fields.Float(compute='_duplicate_amount',string='WBS Total Horas')

    #invoicing_type = fields.Selection([('mes','Mes'),('horas','Horas')], string="Tipo de Proyección",required=True)
    invoicing_type=fields.Many2one('uom.uom', string='Tipo de Proyección')
    
    oc_profile = fields.Many2one('sale.order.line', string="Perfil OC", required=False)
    hours_profile = fields.Integer(string="Horas Perfil")
    
    origin=fields.Selection([('odoo8','odoo8'),('odoo12','odoo12')], string='Origen', default='odoo12')
    profile_ids = fields.Many2many('sale.order.line',compute='change_invoicing_type',string='Available Profiles')


    @api.depends('invoicing_type','account_id','oc_profile','state')
    def change_invoicing_type(self):

        if self.oc_profile:
            self.invoicing_type=self.oc_profile.order_id.type_sale
            self.hours_profile=self.oc_profile.product_uom_qty/self.oc_profile.order_id.type_sale.factor


        #ok what are my available profiles without filtro
        available_profile_ids=[]
        all_profile_ids=self.env['sale.order.line'].search([('project_id','=',self.account_id.id)])
        
        for profile_id in all_profile_ids:
            #find all bookings for confirmado
            all_bookings=self.env['hr.projection.timesheet'].search([('oc_profile','=',profile_id.id),('state','=','confirm')])

            if all_bookings:
                if self.invoicing_type.name=='Hora(s)':
                    hours_total=sum([x.amount for x in all_bookings])
                    if hours_total<=profile_id.product_uom_qty*1.05:
                        available_profile_ids.append(profile_id.id)
                        
                if self.invoicing_type.name=='Mes(es)':
                    days_total=sum([x.number_of_days_temp for x in all_bookings])
                    if days_total<=profile_id.product_uom_qty:
                        available_profile_ids.append(profile_id.id)
                        
        if available_profile_ids:
            self.profile_ids=available_profile_ids
            if self.oc_profile.id not in available_profile_ids:
                self.oc_profile=False
        else:
            self.profile_ids=all_profile_ids


    # @api.onchange('oc_profile')
    # def change_hours(self):
        # if self.oc_profile:
            # self.invoicing_type=self.oc_profile.order_id.type_sale
            # self.hours_profile=self.oc_profile.product_uom_qty/self.oc_profile.order_id.type_sale.factor


    #On confirm onboard search for employee onboard and update with first project
    @api.multi
    def _update_onboard(self):
        ob_obj=self.env['hr.onboard']
        for rec in self:
            employee= rec.user_id.employee_id
            onboard=ob_obj.sudo().search([('employee_id','=',employee.id)])
            if onboard and not onboard.project_id:
                onboard.project_id=rec.account_id

    @api.multi
    def to_draft(self):
        for book in self:
            #remove Staffing and Preinvoices
            if book.outsourcing_id:
                for line in book.outsourcing_id:
                    preinvoice=line.projection_id
                    line.unlink()
                    preinvoice._compute_amount()
                    if not preinvoice.outsourcing_ids:
                    #if no outsourcing linked to preinvoice..then delete preinvoice
                        preinvoice.unlink()

            #remove WBS
            #book.task_id.unlink()
            for task in book.task_id:
                task.unlink()

            #reset state
            book.state='draft'
            book.confirm_type='draft'

    @api.multi
    def unlink_staffing(self):
        for book in self:
            if book.source_type=='generated':
                book.state='draft'
                book.outsourcing_id=None
                book.task_id=None
            else:
                raise models.ValidationError(('No se puede desvincular WBS y Staffing de un Booking manual!'))

    def _generate_week(self,start_date,end_date):
        task_list=[]
        task_values={}
        staff_list=[]
        staff_values=[]
        start=start_date
        end=end_date
        end_date = datetime.strptime(str(end),"%Y-%m-%d").date()
        week_cnt=0

        while True:
            break_loop=False
            staff_values={}
            week_cnt+=1
            start_date = datetime.strptime(str(start),"%Y-%m-%d").date()
            start_week = start_date - timedelta(days=start_date.weekday())
            end_week = start_week + timedelta(days=6)
            next_week= start_week + timedelta(days=7)

            if start_date>start_week:
                start_week=start_date

            if end_date<end_week:
                end_week=end_date
                break_loop=True

            if next_week>end_date:
                break_loop=True

            start_week_str=datetime.strftime(start_week,"%Y-%m-%d")
            end_week_str=datetime.strftime(end_week,"%Y-%m-%d")

            _,_,quantity=self._calculate_quantity(start_week_str,end_week_str)

            p_obj=self.env['account.period']
            domain=[('date_start','<=',start_week_str ),('date_stop','>=',start_week_str),('company_id','=',self.company_id.id),('special','=',False)]

            p_inst=p_obj.sudo().search(domain)
            if not p_inst:
                raise models.ValidationError(('No se encuentra periodo para las fechas %s hasta %s! Por favor, revisar configuracion de Feriados' % (start_week,end_week)))

            name='_'.join((self.account_id.project_reference,self.name,'SEMANA',str(week_cnt),' '))
            task_name='_'.join((self.account_id.project_reference,p_inst.name,'SEMANA',str(week_cnt)))

            staff_values={'name':name,
                'reviewer_id':self.env.user.id,
                'description':'[{}]'.format(self.user_id.name),
                'company_id':self.company_id.id,
                'quantity':quantity,
                'project_id':self.account_id.id,
                'activity_type':self.activity_type.id,
                'user_id':self.user_id.id,
                'date_start':datetime.strftime(start_week,"%Y-%m-%d"),
                'date_end':datetime.strftime(end_week,"%Y-%m-%d"),
                'period_id':p_inst.id,
                'real_period_id':p_inst.id,
                'state':'draft',
                'amount':0.0,
                'projected_amount':0.0,
                'quantity_invoiced':0.0,
                'assignment_id':self.id
                 }

            staff_list.append(staff_values)

            task_values={'name':task_name,
                'reviewer_id':self.reviewer_id.id,
                'planned_hours':quantity,
                'project_id':self.account_id.id,
                'activity_type':self.activity_type.id,
                'period_id':p_inst.id,
                'outsourcing_state':'draft',
                'hr_proj_timesheet_id':self.id,
                'date_start':datetime.strftime(start_week,"%Y-%m-%d")+' 00:00:00',
                'date_end':datetime.strftime(end_week,"%Y-%m-%d")+' 23:59:00',
                }

            task_list.append(task_values)

            if break_loop:
                break
            else:
                start=datetime.strftime(next_week,"%Y-%m-%d")
        return task_list,staff_list

    def _generate_period(self,start_date,end_date):
        task_list=[]
        task_values={}
        staff_list=[]
        staff_values={}
        start=start_date
        end=end_date
        projected_days=0
        end_date = datetime.strptime(str(end),"%Y-%m-%d").date()

        #unit price could be price per month or price per hour depending on profile sale type
        unit_price=self.oc_profile.price/self.oc_profile.product_uom_qty


        while True:
            projected_amount=0
            amount=0       
            break_loop=False
            staff_values={}
            start_date = datetime.strptime(str(start),"%Y-%m-%d").date()
            start_period = start_date
            
            #initialize end_period and end_month
            end_period=end_month = start_period + relativedelta(day=31)
            
            #initialize next period as first day of next month            
            next_period= start_period + relativedelta(day=1, months=1)

            #check to see if start_period is before start_date and change accordingly.
            #This shouldnt happen.
            if start_date>start_period:
                start_period=start_date

            #check to see if end_period is after end_date and change accordingly
            if end_date<end_period:
                end_period=end_date
                break_loop=True
                
            #check to see if we need more periods
            if next_period>end_date:
                break_loop=True

            start_period_str=datetime.strftime(start_period,"%Y-%m-%d")
            end_period_str=datetime.strftime(end_period,"%Y-%m-%d")

            #Difficult to abstract this completely, but if invoice_type factor<> 1
            #Use pre.invoice projection based on 30 days

            _,_,quantity=self._calculate_quantity(start_period_str,end_period_str)

            if self.invoicing_type.factor !=1: #invoicing_type of Mes(es)
                if start_period.day==1 and (end_period.day==end_month.day):
                    projected_days=30                  
                else:
                    projected_days=(end_period.day-start_period.day)+1             
                
                projected_amount=amount=((unit_price) * projected_days)/30
                    
            else: #invoicing_type of Hora(s)
                projected_amount=amount=unit_price*quantity
          
            #find active period in account.period that matches dates

            p_obj=self.env['account.period']
            domain=[('date_start','<=',start_period_str ),('date_stop','>=',end_period_str),('company_id','=',self.company_id.id),('special','=',False)]

            p_inst=p_obj.sudo().search(domain)
            if not p_inst:
                raise models.ValidationError(('No se encuentra periodo para las fechas %s hasta %s! Por favor, revisar configuracion de Feriados' % (start_period,end_period)))

            name='_'.join((self.account_id.project_reference,self.name))
            task_name='_'.join((self.account_id.project_reference,self.name,'PERIODO',p_inst.name))


            staff_values={'name':name,
                'description':'[{}]'.format(self.user_id.name),
                'company_id':self.company_id.id,
                'quantity':quantity,
                'project_id':self.account_id.id,
                'activity_type':self.activity_type.id,
                'user_id':self.user_id.id,
                'date_start':datetime.strftime(start_period,"%Y-%m-%d"),
                'date_end':datetime.strftime(end_period,"%Y-%m-%d"),
                'period_id':p_inst.id,
                'real_period_id':p_inst.id,                
                'state':'draft',
                'amount': amount,
                'projected_amount': projected_amount,
                'quantity_invoiced':0.0,
                'assignment_id':self.id,
                'projected_days':projected_days
                 }

            staff_list.append(staff_values)

            task_values={'name':task_name,
                'reviewer_id':self.reviewer_id.id,
                'planned_hours':quantity,
                'project_id':self.account_id.id,
                'activity_type':self.activity_type,
                'period_id':p_inst.id,
                'outsourcing_state':'draft',
                'hr_proj_timesheet_id':self.id,
                'date_start':datetime.strftime(start_period,"%Y-%m-%d")+' 00:00:00',
                'date_end':datetime.strftime(end_period,"%Y-%m-%d")+' 23:59:00',
                }

            task_list.append(task_values)

            if break_loop:
                break
            else:
                start=datetime.strftime(next_period,"%Y-%m-%d")

        return task_list,staff_list

    @api.multi
    def booking_reconfirm_shorten(self):
        cform = self.env.ref('apiux_extra_2.hr_proj_shorten_wizard_form', False)
        action = {
            'type': 'ir.actions.act_window',
            'id':'hr_proj_shorten_wizard_view',
            'name': 'Acortar Booking',
            'res_model': 'hr.proj.shorten',
            'src_model': 'hr.projection.timesheet',
            'src_id':self.id,
            'target':'new',
            'view_id':cform.id,
            'view_mode': 'form',
            'view_type':'form',
            'context': {'booking_id': self.id}
            }
        return action



    @api.multi
    def booking_confirm_period(self):
        task_obj=self.env['project.task']
        staff_obj=self.env['project.outsourcing']
        
        #Esta chequeo no aplica para booking de tipo Meses
        if self.invoicing_type.name in ['Hora(s)']:
            hours_5=int(self.hours_profile*0.05)
            if self.hours_profile+hours_5<self.amount_2:
                raise models.ValidationError(('No es posible asignar más de '+str(self.hours_profile+hours_5)+' horas ('+str(self.hours_profile)+' horas + '+str(hours_5)+' horas).\n Para más ayuda contacta al administrador'))
            if self.hours_profile-hours_5>self.amount_2:
                raise models.ValidationError(('No es posible asignar menos de '+str(self.hours_profile-hours_5)+' horas ('+str(self.hours_profile)+' horas - '+str(hours_5)+' horas).\n Para más ayuda contacta al administrador'))

            #End Jose
        
        
        task_list,staff_list=self._generate_period(self.from_date,self.to_date)
        #create staffing
        for staff_val in staff_list:
            date_start=staff_val.get('date_start',False)
            date_end=staff_val.get('date_end',False)
            _logger.info("staff=%s",staff_val)
            del staff_val['date_start']
            del staff_val['date_end']
            staff=staff_obj.create(staff_val)
            staff.task_id.date_start=date_start+' 00:00:00'
            staff.task_id.date_end=date_end+' 23:59:00'
            staff.task_id.hr_proj_timesheet_id=self
        #confirm type
        self.confirm_type='periodws'
        self.state='confirm'

    @api.multi
    def booking_confirm_period_nostaff(self):
        task_obj=self.env['project.task']
        staff_obj=self.env['project.outsourcing']
        task_list,staff_list=self._generate_period(self.from_date,self.to_date)
        #create task
        for task_val in task_list:
            task=task_obj.create(task_val)
            task.user_id=[(self.user_id.id)]#6,0,
            task.outsourcing_state='draft'
        #confirm type
        self.confirm_type='periodns'
        self.state='confirm'

    @api.multi
    def booking_reconfirm_percentage_periodws(self):
        hours=float(self.oc_profile.price/self.oc_profile.product_uom_qty)
        task_list,staff_list=self._generate_period(self.from_date,self.to_date,hours)
        #update staffing
        for staff in staff_list:
            update_staff=self.outsourcing_id.filtered(lambda r:r.period_id.id==int(staff['period_id']))
            if update_staff:
                if update_staff.task_id.task_history_ids:
                    update_staff.quantity=update_staff.task_id.task_history_ids[-1].planned_hours
                else:
                    update_staff.quantity=staff['quantity']

    @api.multi
    def booking_reconfirm_percentage_periodns(self):
        task_list,staff_list=self._generate_period(self.from_date,self.to_date)

        #update staffing
        for task in task_list:
            update_task=self.task_id.filtered(lambda r:(r.period_id.id==int(task['period_id']) and r.date_start==task['date_start'] and r.date_end==task['date_end']))
            if update_task:
                update_task.planned_hours=task['planned_hours']



    def booking_shorten_periodws(self,to_date):
        DATETIME_FORMAT = "%Y-%m-%d"
        hours=float(self.oc_profile.price/self.oc_profile.product_uom_qty)
        task_list,staff_list=self._generate_period(self.from_date,to_date,hours)
        #get existing staffing and sort in reverse order
        staffing=self.outsourcing_id.sorted(key=lambda r: datetime.strptime(str(r.period_id.date_start), DATETIME_FORMAT), reverse=True)
        delete_staffing=[]
        self.state='draft'

        for staff in staffing:
            if staff.period_id.date_start>to_date:
                if staff.quantity_real>0:
                    raise models.ValidationError(('El Staffing del periodo %s tiene %s horas accumuladas! Por favor, elija nueva Fecha Fin despues del %s' % (staff.period_id.name,staff.quantity_real,staff.period_id.date_start)))
                else:
                    delete_staffing.append(staff)

            if to_date>staff.period_id.date_start and to_date<=staff.period_id.date_stop:
                if staff.quantity_real>0:
                    work_ids=staff.task_id.work_ids.filtered(lambda r: r.user_id == staff.user_id and r.date>to_date)
                    sorted_work_ids=work_ids.sorted(key=lambda r: r.date, reverse=True)

                    #has hours allocated after
                    if sorted_work_ids:
                        raise models.ValidationError(('El Staffing del periodo %s tiene %s horas accumuladas! Por favor, elija nueva Fecha Fin despues del %s' % (staff.period_id.name,staff.quantity_real,sorted_work_ids[0].date)))

                    else:
                    #here we can just set booking date to to_date and recalculate
                        self.to_date=to_date

                        #need to remove unnecessary exemption dates
                        for exempt in self.exemption_ids:
                            if exempt.booking_date>to_date:
                                exempt.unlink()

                        self.booking_reconfirm_percentage_periodws()

                else:
                    self.to_date=to_date
                    for exempt in self.exemption_ids:
                        if exempt.booking_date>to_date:
                            exempt.unlink()
                    self.booking_reconfirm_percentage_periodws()

        #finally delete staffing no horas
        for staff in delete_staffing:
            preinvoice=staff.projection_id
            #delete staffing y wbs
            staff.task_id.unlink()
            staff.unlink()
            #recalculate preinvoice if necessary
            if preinvoice:
                preinvoice._compute_amount()
                if not preinvoice.outsourcing_ids:
                #if no outsourcing linked to preinvoice..then delete preinvoice
                    preinvoice.unlink()

        #finally clean up any wbs without staffing
        for wbs in self.task_id:
            if not wbs.outsourcing_ids:
                try:
                    wbs.unlink()
                except:
                    pass

        self.to_date=to_date
        self.state='confirm'

        for task in task_list:
            update_task=self.task_id.filtered(lambda r:(r.period_id.id==int(task['period_id']) and r.date_start==task['date_start'] and r.date_end==task['date_end']))
            if update_task:
                if update_task.task_history_ids:
                    update_task.planned_hours=update_task.task_history_ids[-1].planned_hours
                else:
                    update_task.planned_hours=task['planned_hours']

    def booking_shorten_periodns(self,to_date):
        DATETIME_FORMAT = "%Y-%m-%d"
        local =pytz.timezone("America/Santiago")
        task_list,staff_list=self._generate_period(self.from_date,to_date)

        #get existing staffing and sort in reverse order
        tasking=self.task_id.sorted(key=lambda r: datetime.strptime(r.period_id.date_start, DATETIME_FORMAT), reverse=True)

        delete_tasking=[]
        self.state='draft'

        for task in tasking:

            if task.period_id.date_start>to_date:
                if task.effective_hours>0:
                    raise models.ValidationError(('El Wbs del periodo %s tiene %s horas accumuladas! Por favor, elija nueva Fecha Fin despues del %s' % (task.period_id.name,task.effective_hours,task.period_id.date_start)))
                else:
                    delete_tasking.append(task)

            if to_date>task.period_id.date_start and to_date<=task.period_id.date_stop:
                if task.effective_hours>0:
                    work_ids=task.work_ids.filtered(lambda r: r.user_id.id in [u.id for u in task.user_id] and r.date>to_date)
                    sorted_work_ids=work_ids.sorted(key=lambda r: r.date, reverse=True)

                    #has hours allocated after
                    if sorted_work_ids:
                        raise models.ValidationError(('El WBS del periodo %s tiene %s horas accumuladas! Por favor, elija nueva Fecha Fin despues del %s' % (task.period_id.name,task.effective_hours,sorted_work_ids[0].date)))

                    else:
                    #here we can just set booking date to to_date and recalculate
                        self.to_date=to_date

                        #need to remove unnecessary exemption dates
                        for exempt in self.exemption_ids:
                            if exempt.booking_date>to_date:
                                exempt.unlink()

                        self.booking_reconfirm_percentage_periodns()

                else:
                    self.to_date=to_date
                    for exempt in self.exemption_ids:
                        if exempt.booking_date>to_date:
                            exempt.unlink()
                    self.booking_reconfirm_percentage_periodns()

        for task in delete_tasking:
            task.unlink()

        self.to_date=to_date
        self.state='confirm'


    @api.model
    def create(self, vals):
        #get company from employee..obligatory field
        comp_id=vals.get("company_id",1)
        comp=self.env["res.company"].browse([comp_id])
        company_id=comp.id or 1
        #get dates from vals..they are both obligatory
        date_from=vals["from_date"]
        date_to=vals["to_date"]
        vals["number_of_days_temp"]=self._get_number_of_days(date_from, date_to)+1
        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise exceptions.ValidationError(_('The start date must be anterior to the end date.'))
        DATETIME_FORMAT = "%Y-%m-%d"
        from_dt = datetime.strptime(date_from, DATETIME_FORMAT)
        to_dt = datetime.strptime(date_to, DATETIME_FORMAT)
        exemptions_cnt,exemptions_list=self._get_exemption_list(from_dt,to_dt,comp)
        #add child records to vals
        if exemptions_cnt>0:
            vals["number_of_days_temp"]=vals.get("number_of_days_temp",0)-exemptions_cnt
            vals["exemption_ids"]=[(0,0, exempt) for exempt in exemptions_list]

        #create schedule
        vals["schedule_ids"]=[(0,0,{'name':str(x),'quantity':vals.get("unit_amount",0)}) for x in range(0,7)]
        res=super(hr_projection_timesheet, self).create(vals)
        return res

    @api.multi
    def write(self,vals):
        comp_id=vals.get("company_id",self.company_id.id)
        comp=self.env["res.company"].browse([comp_id])
        company_id=comp.id or 1
        holiday=u'Vacaciones'
        _logger.info("bvals=%s",vals)
        #get exclude dates from vals
        exclude_list=[]
        excluded_dates=[]
        exemption_ids=vals.get('exemption_ids',False)
        if exemption_ids:
            exclude_list=[x[1] for x in exemption_ids if x[2] and x[2].get('booking_exclude',False)]
        #get exclude dates from
        exclude_list+=[x.id for x in self.exemption_ids.filtered(lambda r:r.booking_exclude==True)]
        excluded_dates=[x.booking_date for x in self.env['hr.booking.exemptions'].browse(exclude_list)]
        #allow editing of staffing
        outsourcing_id=vals.get("outsourcing_id", False)
        len_vals=len(vals)
        if (self.state=='confirm' and ((vals.get('state',self.state)!='draft') and (vals.get('percentage',False)==False or vals.get('to_date',False)==False) and (vals.get('schedule_ids',False)==False) and (vals.get('task_id',False)==False)))  and not(outsourcing_id and len_vals==1):
            raise exceptions.ValidationError(_('A Booking in state Confirm cannot be changed. Please change state to Draft and try again.'))

        #remove exemptions by default, readd if necessary
        if self.exemption_ids:
            for exemption in self.exemption_ids:
                exemption.unlink()

        date_from=self.from_date
        date_to=self.to_date
        #raise models.ValidationError(('date_from: '+str(date_from)+str(type(date_from))+'\ndate_to: '+str(date_to)+str(type(date_to))))
        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise exceptions.ValidationError(_('The start date must be anterior to the end date.'))
            

        #recalculate num days adding 1
        vals["number_of_days_temp"]=self._get_number_of_days(date_from, date_to)+1

        DATETIME_FORMAT = "%Y-%m-%d"
        from_dt = datetime.strptime(str(date_from), DATETIME_FORMAT)
        to_dt = datetime.strptime(str(date_to), DATETIME_FORMAT)

        exemptions_cnt,exemptions_list=self._get_exemption_list(from_dt,to_dt,comp)

        for exempt in exemptions_list:
            if exempt['booking_date'] in excluded_dates:
                exempt['booking_exclude']=True
            else:
                exempt['booking_exclude']=False

        #add child records to vals
        if exemptions_cnt>0:
            vals["number_of_days_temp"]=vals.get("number_of_days_temp",self.number_of_days_temp)-exemptions_cnt+len(excluded_dates)
            vals["exemption_ids"]=[(0,0, exempt) for exempt in exemptions_list]

        res=super(hr_projection_timesheet, self).write(vals)
        return res

    @api.multi
    def unlink(self):
        for record in self:
            if record.state!='draft':
                raise models.ValidationError(('No se puede eliminar Booking en estado Confirmado! Por favor, cambiar estado a Borrador y intentar nuevamente'))
        return super(hr_projection_timesheet, self).unlink()

class ProjectTask(models.Model):
    _inherit='project.task'

    hr_proj_timesheet_id=fields.Many2one('hr.projection.timesheet', string='Booking', ondelete='cascade')

    @api.multi
    def action_open(self):
        for comm in self:
            comm.write({'outsourcing_state':'open'})

    @api.multi
    def action_done(self):
        for comm in self:
            comm.write({'outsourcing_state':'done'})

    @api.multi
    def action_reject(self):
        for comm in self:
            comm.write({'outsourcing_state':'rejected'})

    @api.multi
    def action_draft(self):
        for comm in self:
            comm.write({'outsourcing_state':'draft'})

class ProjectProject(models.Model):
    _inherit='project.project'

    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the timedelta between two dates given as string."""

        DATETIME_FORMAT = "%Y-%m-%d"
        from_dt = datetime.strptime((date_from or self.from_date)[:10], DATETIME_FORMAT)
        to_dt = datetime.strptime((date_to or self.to_date)[:10], DATETIME_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        return diff_day

    hr_proj_timesheet_ids=fields.One2many('hr.projection.timesheet','account_id', string='Bookings')

    def set_all_projects_prefactura_cron(self,cr,uid,context=None):
        project_obj=self.pool['project.project']
        project_ids= project_obj.search(cr, uid, [('state', '=','open'),('active','=',True)], context=context)
        for project_id in project_ids:
            project=project_obj.browse(cr,uid,project_id,context=context)
            project.generate_prefactura_staffing_button()

    def close_wbs_cron(self,cr,uid,context=None):
        project_obj=self.pool['project.project']
        project_ids= project_obj.search(cr, uid, [('state', '=','open'),('active','=',True)], context=context)
        for project_id in project_ids:
            project=project_obj.browse(cr,uid,project_id,context=context)
            project.close_wbs()

    @api.multi
    def close_wbs(self):
        today=fields.Date.today()
        task_obj=self.env['project.task']
        for project in self:
            #first close staffing
            staffing=project.outsourcing_id.filtered(lambda r: r.state=='open')
            for staff in staffing:
                if staff.period_id:
                    diffdays=project._get_number_of_days(staff.period_id.date_stop, today)
                    if diffdays>7:
                        staff.action_done()

            #close tasks
            domain=[('project_id','=',self.project_id.id),('outsourcing_state','=', 'open'),('date_start','!=',False),('date_end','!=',False)]
            tasks=task_obj.search(domain)
            tasks=tasks.filtered(lambda r: len(r.outsourcing_ids)==0)

            for task in tasks:
                diffdays=project._get_number_of_days(task.date_end, today)
                task_diffdays=project._get_number_of_days(task.date_start, task.date_end)+1

                if diffdays>max(task_diffdays,7):
                    task.outsourcing_state='done'

            #open staffing
            staffing=project.outsourcing_id.filtered(lambda r: r.state=='draft')
            for staff in staffing:
                if staff.period_id:
                    diffdays=project._get_number_of_days(today, staff.period_id.date_start)
                    if diffdays<=2:
                        staff.action_open()

            #open tasks

            domain=[('project_id','=',self.project_id.id),('outsourcing_state','=', 'draft'),('date_start','!=',False),('date_end','!=',False)]
            tasks=task_obj.search(domain)
            tasks=tasks.filtered(lambda r: len(r.outsourcing_ids)==0)

            for task in tasks:
                diffdays=project._get_number_of_days(today, task.date_start)
                if diffdays<=4:
                    task.outsourcing_state='open'

    @api.multi
    def generate_prefactura_staffing_button(self):
        pre_invoice_obj=self.env['project.pre.invoice']
        for project in self:
            #remove prefactuas not linked with preaccrued (devengados)
            domain=[('invoice_type','=','t&m'),('project_id','=',project.id),('state','in',['draft','open']),('link_preaccrued_id','=',False)]
            pre_invoice_ns=pre_invoice_obj.search(domain)

            for rec in pre_invoice_ns:
                rec.unlink()
            try:
                outsourcing_ids=project.outsourcing_id
                for outsourcing in outsourcing_ids:
                    #is there a prefactura associated with this?

                    domain=[('period_id','=', outsourcing.period_id.id),('invoice_type','=','t&m'),('project_id','=',outsourcing.project_id.id)]
                    pre_invoice=pre_invoice_obj.search(domain, limit=1)
                    if pre_invoice:
                        outsourcing.projection_id=pre_invoice

                    else:
                        values={}
                        values={'period_id':outsourcing.period_id.id,
                            'currency_id':outsourcing.currency_id.id,
                            'company_id':outsourcing.company_id.id,
                            'amount':0.0,
                            'projected_amount':0.0,
                            'invoice_period':outsourcing.period_id.date_stop,
                            'invoice_type':'t&m',
                            'project_id':outsourcing.project_id.id,
                            }

                        pre_invoice=pre_invoice_obj.create(values)
                        outsourcing.projection_id=pre_invoice

                    #now update amounts on pre_invoice
                    pre_invoice.amount=sum([x.amount for x in pre_invoice.outsourcing_ids])
                    pre_invoice.projected_amount=sum([x.projected_amount for x in pre_invoice.outsourcing_ids])

            except Exception as e:
                _logger.error("Error in hr_projection_timesheet.generate_prefactura_staffing, %s",str(e))

    @api.multi
    def generate_bookings(self):

        cform = self.env.ref('hr_projection_timesheet.hr_proj_generate_wizard_form', False)
        action = {
            'type': 'ir.actions.act_window',
            'id':'projection_generate_wizard_view',
            'name': 'Generar Bookings',
            'res_model': 'hr.proj.generate',
            'src_model': 'project.project',
            'context':{'default_project_id':self.id},
            'target':'new',
            'view_id':cform.id,
            'view_mode': 'form',
            'view_type':'form',
            }
        return action

class ResUsers(models.Model):
    _inherit='res.users'

    assignment_ids=fields.One2many('hr.projection.timesheet', 'user_id', string='Bookings')

class hr_projection_dates(models.Model):
    _name = "hr.projection.dates"
    _description = 'Timesheet Projection Dates'

    date= fields.Date('Date', required=True, select=True)
    weekend=fields.Boolean('Weekend?')
    holiday=fields.Boolean('Holiday?')
    unit_amount= fields.Float('Duracion',default=8.5, required=True, help='Calculated by multiplying the quantity and the price given in the Product\'s cost price. Always expressed in the company main currency.', digits=(2,1))

class HrHolidays(models.Model):
    _inherit = 'hr.leave'

    @api.multi
    @api.depends('date_to')
    def _gantt_date_to(self):

        DATETIME_FORMAT = "%Y-%m-%d"
        for rec in self:
            if rec.date_to:
                date_to = datetime.strptime(rec.date_to, DATETIME_FORMAT)
                rec.gantt_date_to=datetime.strftime((date_to + timedelta(days=1)),DATETIME_FORMAT)

    employee_active=fields.Boolean(related='employee_id.active', string='Activo')
    gantt_date_to=fields.Date('To Date', compute=_gantt_date_to)


class AccountPreInvoiceLine(models.Model):
    _inherit='account.pre_invoice.line'
  
    outsourcing_id=fields.Many2one('project.outsourcing', ondelete='restrict',required=False,string='Linea Outsourcing')
    
class ProjectPreInvoice(models.Model):
    _inherit = 'project.pre.invoice'
    
    preinvoice_line_id=fields.One2many('account.pre_invoice.line','outsourcing_id','Linea Prefactura') 


#add oc_profile product to wizar line
class ProjectInvoiceWizardLines(models.TransientModel):
    _inherit = 'project.invoice.wizard.lines'

    product_id =fields.Many2one(related='outsourcing_id.assignment_id.oc_profile.product_id', string='Producto')  
        