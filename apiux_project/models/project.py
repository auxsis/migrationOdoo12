# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 ONESTEiN BV (<http://www.onestein.nl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, AccessError, ValidationError
import logging

_logger = logging.getLogger(__name__)

SERVICE_TYPE=[
    ('Project','Proyecto'),
    ('Outsourcing','Outsourcing'),
    ('Others','Otros')
]


class project_project(models.Model):
    _inherit = 'project.project'


    @api.one
    @api.depends('partner_id','project_number','partner_id.partner_abbr')
    def check_user_id(self):
        abbr=None
        if self.project_number and self.partner_id:
            abbr=self.partner_id.partner_abbr
            if abbr and "ABR" in self.project_number:
                self.project_reference=self.project_number.replace("ABR",abbr)
            else:
                raise exceptions.Warning(_('User has no abbreviation. Please enter abbreviation in Partner/User'))
        else:
            self.project_reference=_("Ref. No Disponible")




    @api.multi
    @api.depends('analytic_account_id.line_ids')
    def _get_has_horas(self):
            #set backup default
            auxiliary_startdate='2019-01-01'
            icp_obj = self.env['ir.config_parameter']
            line_obj= self.env['account.analytic.line']
            #get list of auxiliary analytic account ids from system configuration parameters
            try:
                auxiliary_startdate=icp_obj.get_param('auxiliary_startdate')
            except Exception as e:
                _logger.info("Error en project.project _get_last_horas, %s",str(e))

            for rec in self:
                domain=[('date','>=',auxiliary_startdate),('account_id','=',rec.analytic_account_id.id)] #('journal_id.type','=','general'),
                line_inst=line_obj.sudo().search(domain,limit=1)
                if line_inst:
                    rec.has_hours=True

    approve_state=fields.Selection([
        ('draft','Open'),
        ('confirm','Waiting Approval'),
        ('done','Approved')], 'Approval Status', index=True, required=True, readonly=True,
        help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed timesheet. \
            \n* The \'Confirmed\' status is used for to confirm the timesheet by user. \
            \n* The \'Done\' status is used when users timesheet is accepted by his/her senior.', default='draft')
    state = fields.Selection([('template', 'Template'),
                               ('draft','New'),
                               ('open','In Progress'),
                               ('cancelled', 'Cancelled'),
                               ('pending','Pending'),
                               ('close','Closed')],
                              'Status', required=True, copy=False, default='open')
    project_number= fields.Char('Project Number')
    #project_reference= fields.Char('Project Reference', compute='check_user_id', store=True) #apiuxmigration dont calculate field being copied
    project_reference= fields.Char('Project Reference', store=True)     
    nota_ids=fields.One2many('crm.sale.note','project_id','CRM Sale Note')
    updated_index= fields.Integer(string='Update count',default=0)
    manager_user_id=fields.Many2one('res.users', string='Jefe de Proyecto')
    project_activities_ids=fields.Many2many('partner.activities', string='Sector')
    exclude_sql=fields.Boolean(default=False, string='Excluir de SQL Consultas')
    has_hours=fields.Boolean(default=False, string='Tiene horas despues 2019-01-01', compute=_get_has_horas, store=True)

    cost_center_id=fields.Many2one('account.cost.center', string='Cost Center')
    sector_id=fields.Many2one('account.sector', string='Sector')
    service_type=fields.Many2one('sale.order.service.type', string="Tipo Servicio")    

    renewel = fields.Integer(string='Renovación', readonly=True, default=0)
    total_hours_projected = fields.Float(string="Horas Proyectadas",compute="compute_hours_projected")
    total_hours_sold = fields.Float(string="Horas Vendidas",compute="compute_hours_sold")
    total_hours_registered = fields.Float(string="Horas Registradas",compute="compute_hours_registered")
    total_hours_analytic = fields.Float(string="Horas Analiticas",compute="compute_hours_analytic")
    
    
    nota_ids=fields.One2many('crm.sale.note','project_id','CRM Sale Note')
    invoice_id=fields.One2many('account.invoice','project_id', string='Invoices')

    planned_hours = fields.Char('Planned Time', help="Sum of planned hours of all tasks related to this project and its child projects."
        #,store = {
        #    'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
        #    'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'work_ids', 'stage_id'], 20),}
        )
    effective_hours = fields.Char('Time Spent',help="Sum of spent hours of all tasks related to this project and its child projects."
        #,store = {
        #    'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
        #    'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'work_ids', 'stage_id'], 20),}
        )
    total_hours = fields.Char('Total Time', help="Sum of total hours of all tasks related to this project and its child projects."
        #,store = {
        #    'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
        #    'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'work_ids', 'stage_id'], 20),}
        )
    progress_rate = fields.Float('Progress',  group_operator="avg", help="Percent of tasks closed according to the total of tasks todo."
        #,store = {
        #    'project.project': (_get_project_and_parents, ['tasks', 'parent_id', 'child_ids'], 10),
        #    'project.task': (_get_projects_from_tasks, ['planned_hours', 'remaining_hours', 'work_ids', 'stage_id'], 20),}
        )


    @api.multi
    @api.depends('nota_ids')
    def compute_hours_sold(self):
        hours_sold=0
        for line in self:
            for nota in line.nota_ids:
                for order_line in nota.order_line_quotation:
                    hours_sold+=order_line.product_uom_qty
                    #raise models.ValidationError('self: '+str(order_line))
        self.total_hours_sold=hours_sold

    @api.multi
    @api.depends('nota_ids','task_ids')
    def compute_hours_projected(self):
        hours_projected=0
        for line in self:
            for task in line.task_ids:
                hours_projected+=task.planned_hours
        self.total_hours_projected=hours_projected

    @api.multi
    @api.depends('nota_ids','task_ids')
    def compute_hours_registered(self):
        hours_registered=0
        for line in self:
            for task in line.task_ids:
                for work in task.work_ids:
                    hours_registered+=work.unit_amount
        self.total_hours_registered=hours_registered


    @api.multi
    @api.depends('analytic_account_id.line_ids')
    def compute_hours_analytic(self):
        hours_analytic=0
        for rec in self:
            for line in rec.analytic_account_id.line_ids.filtered(lambda x:x.journal_id.code=='TS'):
                hours_analytic+=line.unit_amount
        self.total_hours_analytic=hours_analytic


    @api.multi
    def name_get(self):
        result = []
        for project in self:
            result.append((project.id, (project.project_reference or "")+"/"+project.name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100,name_get_uid=None):
        if not args:
            args=[]
        if name:
            project_ids = self.search([('name', '=', name)] + args, limit=limit)
            if not project_ids:
                dom = []
                for name2 in name.split('/'):
                    name = name2.strip()
                    project_ids = self.search(dom + ['|',('name', operator, name),('project_reference',operator,name)] + args, limit=limit)
                    if not project_ids: break
                    dom = [('analytic_account_id','in',project_ids)]
        else:
            project_ids = self.search([]+args, limit=limit)
        return self.browse(project_ids.ids).name_get()


    @api.model
    def create(self, vals):
        abbr=None
        sequence_dict={}
        partner=self.env['res.partner'].browse(vals.get('partner_id',False))
        if partner:
            abbr=partner.partner_abbr

        if not abbr or abbr=="":
            raise exceptions.Warning(('%s no tiene abreviatura. Ingrese abreviatura in Cliente (create project_project)') % partner.name)

        sequence_dict=self.env['res.config.settings'].sudo().get_values()
        sequence_id=sequence_dict.get('project_sequence',False)

        if not sequence_id:
            raise exceptions.Warning(_('Project sequence not set in Project Configuration. Please set sequence in Project Configuration'))

        #vals['project_number'] = self.env['ir.sequence'].sudo().next_by_code('project_sale_order') #apiuxmigration
        #vals['project_reference']=vals.get('project_number').replace("ABR",abbr)

        res=super(project_project, self).create(vals)

        return res

    @api.multi
    def write(self,vals):
        for rec in self:
            #create project_reference if project_reference not set
            if (not rec.project_reference or rec.project_reference=='Ref. No Disponible') and (rec.partner_id or vals.get('partner_id',False)):
                abbr=None
                sequence_dict={}
                if not vals.get('partner_id',False):
                    partner=rec.env['res.partner'].browse(rec.partner_id.id)
                else:
                    partner=rec.env['res.partner'].browse(vals['partner_id'])
                if partner:
                    abbr=partner.partner_abbr

                if not abbr or abbr=="":
                    raise exceptions.Warning(('%s no tiene abreviatura. Ingrese abreviatura in Cliente') % partner.name)

                sequence_dict=rec.env['res.config.settings'].sudo().get_values()
                sequence_id=sequence_dict.get('project_sequence',False)

                if not sequence_id:
                    raise exceptions.Warning(_('Project sequence not set in Project Configuration. Please set sequence in Project Configuration'))

                vals['project_number'] = rec.env['ir.sequence'].next_by_code('project_sale_order')
                vals['project_reference']=vals.get('project_number',False).replace("ABR",abbr)

            res=super(project_project, rec).write(vals)
            return res

    @api.multi
    def update_task_reference(self):
        sequence_dict={}
        sequence_dict=self.env['res.config.settings'].sudo().get_values()
        sequence_id=sequence_dict.get('task_sequence',False)
        if not sequence_id:
            raise exceptions.Warning(_('Task sequence not set in Project Configuration. Please set sequence in Project Configuration'))

        for project in self:
            if project.project_reference:
                for task in project.task_ids:
                    task.task_number=self.env['ir.sequence'].next_by_id(sequence_id)
                    task.task_reference=project.project_reference+"-"+task.task_number


class task(models.Model):
    _inherit = "project.task"
    _name = "project.task"

    @api.depends('project_id.project_reference','task_number')
    def check_user_id(self):

        abbr=None
        for task in self:
            if task.task_number and task.project_id.project_reference:
                if abbr and "Ref" not in task.project_id.project_reference:
                    task.task_reference=task.task_number
                else:
                    task.task_reference=task.project_id.project_reference+"-"+task.task_number
            else:
                task.task_reference=_("Ref. No Disponible")

    @api.depends('effective_hours')
    def check_remaining(self):
        for task in self:
            task.remaining_hours=task.planned_hours-task.effective_hours

    @api.multi
    @api.depends('planned_hours')
    @api.onchange('planned_hours')
    def check_planned(self):
        for obj in self:
            obj.remaining_hours=obj.planned_hours-obj.effective_hours

    def _default_period(self):
        period=None
        period_obj=self.env['account.period']
        date_td=fields.Date.today()
        period=period_obj.search([('date_start','<=',date_td),('date_stop','>=',date_td),('company_id','=',self.env.user.company_id.id)])
        return period


    def _get_resource_emails(self):
        for rec in self:
            email_list=[]
            for user in rec.user_id:
                email_list.append(user.login)

            rec.email_to=",".join(tuple(email_list))

    project_approve_state = fields.Selection(related='project_id.approve_state', store=True, readonly=True)
    task_number= fields.Char('Task Number')
    #task_reference= fields.Char( 'Task Reference', compute='check_user_id', store=True) # apiuxmigration
    task_reference= fields.Char( 'Task Reference', store=True) #    
    remaining_hours= fields.Float(compute='check_remaining', store=True)
    activity_type=fields.Many2one('project.task.activity.type',string='Activity Type',required=True,help='Pleas select an activity type for your tasks')
    stage_close=fields.Boolean(related='stage_id.close_stage', string='Task Closed', readonly=True)
    project_company_id=fields.Many2one(related='project_id.company_id', string='Compañia Proyecto')
    period_id=fields.Many2one('account.period', string='Periodo',  domain="[('company_id','=',project_company_id)]") #default=_default_period, error_jose:
    email_to=fields.Char(compute='_get_resource_emails', string='Correos Recursos')
    work_ids=fields.One2many('account.analytic.line', 'task_id')
    reviewer_id = fields.Many2one('res.users', 'Reviewer', store=True)

    @api.model
    def create(self, vals):
        sequence_dict={}
        sequence_dict=self.env['res.config.settings'].sudo().get_values()
        sequence_id=sequence_dict.get('task_sequence',False)

        if not sequence_id:
            raise exceptions.Warning(_('Task sequence not set in Project Configuration. Please set sequence in Project Configuration'))

        #vals['task_number'] = self.env['ir.sequence'].next_by_code('task_sales_order')

        #get project   apiuxmigration
        # if vals['project_id']:
            # project_id=self.env['project.project'].search([('id','=',vals['project_id'])])
            # vals['task_reference']=(project_id.project_reference or "")+"-"+(vals['task_number'] or "")
        # else:
            # vals['task_reference']="-"+vals.get('task_number',"")

        _logger.info("taskvals=%s",vals)
        return super(task, self).create(vals)


    @api.multi
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
        # Overridden to reset the kanban_state to normal whenever
        # the stage (stage_id) of the task changes.
        if vals and not 'kanban_state' in vals and 'stage_id' in vals:
            new_stage = vals.get('stage_id')
            vals_reset_kstate = dict(vals, kanban_state='normal')
            for t in self:
                write_vals = vals_reset_kstate if t.stage_id.id != new_stage else vals
                models.Model.write(t,write_vals)
            result = True
        else:
            result = models.Model.write(self,vals)
        if any(item in vals for item in ['planned_hours']):
            self.with_context(ids=self._ids)._store_history()
        return result

class project_task_type(models.Model):
    _inherit = 'project.task.type'

    close_stage=fields.Boolean('Close Stage',default=False)

