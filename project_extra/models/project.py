# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import time

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval

class Project(models.Model):
    _inherit = "project.project"
    _inherits = {'account.analytic.account': "analytic_account_id",
                 "mail.alias": "alias_id"}
    _order = "sequence, name, id"
    _period_number = 5

    @api.multi
    def attachment_tree_view(self):
        self.ensure_one(),
        domain = [
            '|',
            '&', ('res_model', '=', 'project.project'), ('res_id', 'in', self.ids),
            '&', ('res_model', '=', 'project.task'), ('res_id', 'in', self.task_ids.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'help': _('''<p class="o_view_nocontent_smiling_face">
                        Documents are attached to the tasks and issues of your project.</p><p>
                        Send messages or log internal notes with attachments to link
                        documents to your project.
                    </p>'''),
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    @api.model
    def activate_sample_project(self):
        """ Unarchives the sample project 'project.project_project_data' and
            reloads the project dashboard """
        # Unarchive sample project
        project = self.env.ref('project.project_project_data', False)
        if project:
            project.write({'active': True})

        cover_image = self.env.ref('project.msg_task_data_14_attach', False)
        cover_task = self.env.ref('project.project_task_data_14', False)
        if cover_image and cover_task:
            cover_task.write({'displayed_image_id': cover_image.id})

        # Change the help message on the action (no more activate project)
        action = self.env.ref('project.open_view_project_all', False)
        action_data = None
        if action:
            action.sudo().write({
                "help": _('''<p class="o_view_nocontent_smiling_face">
                    Create a new project</p>''')
            })
            action_data = action.read()[0]
        # Reload the dashboard
        return action_data

    def _compute_is_favorite(self):
        for project in self:
            project.is_favorite = self.env.user in project.favorite_user_ids

    def _inverse_is_favorite(self):
        favorite_projects = not_fav_projects = self.env['project.project'].sudo()
        for project in self:
            if self.env.user in project.favorite_user_ids:
                favorite_projects |= project
            else:
                not_fav_projects |= project

        # Project User has no write access for project.
        not_fav_projects.write({'favorite_user_ids': [(4, self.env.uid)]})
        favorite_projects.write({'favorite_user_ids': [(3, self.env.uid)]})

    def _get_alias_models(self):
        # Overriden in project_issue to offer more options   cr, uid,
        return [('project.task', "Tasks")]

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    _alias_models = lambda self: self._get_alias_models()

    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Contract/Analytic',
        help="Link this project to an analytic account if you need financial management on projects. "
             "It enables you to connect projects with budgets, planning, cost and revenue analysis, timesheets on projects, etc.",
        ondelete="cascade", required=True, auto_join=True)
    alias_id = fields.Many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
                                help="Internal email associated with this project. Incoming emails are automatically synchronized"
                                     "with Tasks (or optionally Issues if the Issue Tracker module is installed).")
    name = fields.Char("Name", index=True, required=True, track_visibility='onchange')
    members = fields.Many2many('res.users', 'project_user_rel', 'project_id', 'uid', 'Project Members',
        help="Project's members are users who can have an access to the tasks related to this project.", states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]})
    alias_model = fields.Selection( _alias_models, string='Alias Model',index=True, required=True, default='project.task',
                                    help="The kind of document created when an email is received on this project's email alias")
    state = fields.Selection([('template', 'Template'),
                               ('draft','New'),
                               ('open','In Progress'),
                               ('cancelled', 'Cancelled'),
                               ('pending','Pending'),
                               ('close','Closed')],
                              'Status', required=True, copy=False, default='open')
    restrict_automatic_task_follow = fields.Boolean(string="Disable Automatic Task Following", default=True,
        help="It will remove unwanted project followers on task. Only assigned person & created person will follow this task automatically.", defaults=True)

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


    start_date = fields.Date(string='Fecha Inicio')
    end_date = fields.Date(string='Fecha Fin')

    @api.multi
    def _get_project_and_children(self):
        """ retrieve all children projects of project ids;
            return a dictionary mapping each project to its parent project (or None)
        """
        for ids in self:
            res = dict.fromkeys(ids, None)
            while ids:
                self._cr.execute("""
                    SELECT project.id, parent.id
                    FROM project_project project, project_project parent, account_analytic_account account
                    WHERE project.analytic_account_id = account.id
                    AND parent.analytic_account_id = account.parent_id
                    AND parent.id = %s
                    """, (ids.id,))
                dic = dict(self._cr.fetchall())
                #raise UserError(_('dic: '+str(dic)))
                res.update(dic)
                ids = dic.keys()
            #raise UserError(_('res: '+str(res)))
        return res

    def _progress_rate(self):
        child_parent = self._get_project_and_children()
        #raise UserError(_('child_parent: '+str(child_parent)))
        # compute planned_hours, total_hours, effective_hours specific to each project
        self._cr.execute("""
            SELECT project_id, COALESCE(SUM(planned_hours), 0.0),
                COALESCE(SUM(total_hours), 0.0), COALESCE(SUM(effective_hours), 0.0)
            FROM project_task
            LEFT JOIN project_task_type ON project_task.stage_id = project_task_type.id
            WHERE project_task.project_id IN %s AND project_task_type.fold = False
            GROUP BY project_id
            """, (tuple(child_parent.keys()),))

        #raise UserError(_('child_parent: '+str(child_parent)))
        # aggregate results into res
        res = dict([(id, {'planned_hours':0.0, 'total_hours':0.0, 'effective_hours':0.0}) for id in self._ids])
        for id, planned, total, effective in self._cr.fetchall():
            # add the values specific to id to all parent projects of id in the result
            while id:
                if id in self._ids:
                    res[id]['planned_hours'] += planned
                    res[id]['total_hours'] += total
                    res[id]['effective_hours'] += effective
                id = child_parent[id]
        # compute progress rates
        for id in self._ids:
            if res[id]['total_hours']:
                res[id]['progress_rate'] = round(100.0 * res[id]['effective_hours'] / res[id]['total_hours'], 2)
            else:
                res[id]['progress_rate'] = 0.0
        return res

    def set_template(self):
        return self.setActive(False)

    @api.model
    def set_done(self):
        return self.write({'state': 'close'})

    @api.model
    def set_cancel(self):
        return self.write({'state': 'cancelled'})

    @api.model
    def set_pending(self):
        return self.write({'state': 'pending'})

    @api.model
    def set_open(self):
        return self.write({'state': 'open'})

    def reset_project(self):
        return self.setActive(True)

    @api.depends('tasks.rating_ids.rating', 'tasks.rating_ids.parent_res_id')
    def _compute_percentage_satisfaction_project(self):
        res = self.env['project.task']._compute_parent_rating_percentage_satisfaction(self, rating_satisfaction_days=30)
        for project in self:
            project.percentage_satisfaction_project = res[project.id]

    #TODO JEM: Only one field can be kept since project only contains task
    @api.depends('tasks.rating_ids.rating', 'tasks.rating_ids.parent_res_id')
    def _compute_percentage_satisfaction_task(self):
        res = self.env['project.task']._compute_parent_rating_percentage_satisfaction(self)
        for project in self:
            project.percentage_satisfaction_task = res[project.id]

    @api.depends('rating_status', 'rating_status_period')
    def _compute_rating_request_deadline(self):
        periods = {'daily': 1, 'weekly': 7, 'bimonthly': 15, 'monthly': 30, 'quarterly': 90, 'yearly': 365}
        for project in self:
            project.rating_request_deadline = fields.datetime.now() + timedelta(days=periods.get(project.rating_status_period, 0))

    @api.model
    def _map_tasks_default_valeus(self, task):
        """ get the default value for the copied task on project duplication """
        return {
            'stage_id': task.stage_id.id,
            'name': task.name,
        }

    @api.multi
    def map_tasks(self, new_project_id):
        """ copy and map tasks from old to new project """
        tasks = self.env['project.task']
        # We want to copy archived task, but do not propagate an active_test context key
        task_ids = self.env['project.task'].with_context(active_test=False).search([('project_id', '=', self.id)], order='parent_id').ids
        old_to_new_tasks = {}
        for task in self.env['project.task'].browse(task_ids):
            # preserve task name and stage, normally altered during copy
            defaults = self._map_tasks_default_valeus(task)
            if task.parent_id:
                # set the parent to the duplicated task
                defaults['parent_id'] = old_to_new_tasks.get(task.parent_id.id, False)
            new_task = task.copy(defaults)
            old_to_new_tasks[task.id] = new_task.id
            tasks += new_task

        return self.browse(new_project_id).write({'tasks': [(6, 0, tasks.ids)]})

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _("%s (copy)") % (self.name)
        project = super(Project, self).copy(default)
        if self.subtask_project_id == self:
            project.subtask_project_id = project
        for follower in self.message_follower_ids:
            project.message_subscribe(partner_ids=follower.partner_id.ids, subtype_ids=follower.subtype_ids.ids)
        if 'tasks' not in default:
            self.map_tasks(project.id)
        return project

    @api.model
    def setActive(self, value):
        task_obj = self.env['project.task']
        for proj in self.browse(self._ids):
            self.with_context(uid=proj.id)
            self.write({'state': value and 'open' or 'template'})
            self._cr.execute('select id from project_task where project_id=%s', (proj.id,))
            tasks_id = [x[0] for x in self._cr.fetchall()]
            if tasks_id:
                task_obj.write({'active': value})
            child_id = self.search([('parent_id','=', proj.analytic_account_id.id)])
            if child_id:
                self.setActive(value)
        return True

    @api.model
    def create(self, vals):
        # Prevent double project creation
        if vals.get('type', False) not in ('template', 'contract'):
            vals['type'] = 'contract'

        self = self.with_context(dict(vals, mail_create_nosubscribe=True, project_creation_in_progress=True,
                              alias_model_name=vals.get('alias_model', 'project.task'),
                              alias_parent_model_name=self._name))

        #raise UserError(_('create project_project\n\nvals: '+str(vals)+'\n\ncontext: '+str(self._context)))

        project = super(Project, self).create(vals)
        if not vals.get('subtask_project_id'):
            project.subtask_project_id = project.id
        if project.privacy_visibility == 'portal' and project.partner_id:
            project.message_subscribe(project.partner_id.ids)
        return project

    @api.multi
    def write(self, vals):
        #raise UserError(_('vals: '+str(vals)))
        # directly compute is_favorite to dodge allow write access right
        if 'is_favorite' in vals:
            vals.pop('is_favorite')
            self._fields['is_favorite'].determine_inverse(self)
        res = super(Project, self).write(vals) if vals else True
        if 'active' in vals:
            # archiving/unarchiving a project does it on its tasks, too
            self.with_context(active_test=False).mapped('tasks').write({'active': vals['active']})
        if vals.get('partner_id') or vals.get('privacy_visibility'):
            for project in self.filtered(lambda project: project.privacy_visibility == 'portal'):
                project.message_subscribe(project.partner_id.ids)
        return res



class Task(models.Model):
    _inherit = "project.task"
    #_inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'rating.mixin']

    """_track = {
        'stage_id': {
            # this is only an heuristics; depending on your particular stage configuration it may not match all 'new' stages
            'project.mt_task_new': lambda self, cr, uid, obj, ctx=None: obj.stage_id and obj.stage_id.sequence <= 1,
            'project.mt_task_stage': lambda self, cr, uid, obj, ctx=None: obj.stage_id.sequence > 1,
        },
        'user_id': {
            'project.mt_task_assigned': lambda self, cr, uid, obj, ctx=None: obj.user_id and [user.id for user in obj.user_id],
        },
        'kanban_state': {
            'project.mt_task_blocked': lambda self, cr, uid, obj, ctx=None: obj.kanban_state == 'blocked',
            'project.mt_task_ready': lambda self, cr, uid, obj, ctx=None: obj.kanban_state == 'done',
        },
    }"""

    @api.model
    def _hours_get(self):
        res = {}
        #raise UserError(_('ids: '+str(self.id)))
        self._cr.execute("SELECT task_id, COALESCE(SUM(hours),0) FROM project_task_work WHERE task_id = %s GROUP BY task_id",(self.id,))
        hours = dict(self._cr.fetchall())
        #raise UserError(_('res: '+str(hours)))
        for task in self.browse(self._ids):
            res[task.id] = {'effective_hours': hours.get(task.id, 0.0), 'total_hours': (task.remaining_hours or 0.0) + hours.get(task.id, 0.0)}
            res[task.id]['delay_hours'] = res[task.id]['total_hours'] - task.planned_hours
            res[task.id]['progress'] = 0.0
            if hours:
                if (task.remaining_hours + hours.get(task.id)):
                    res[task.id]['progress'] = round(min(100.0 * hours.get(task.id, 0.0) / res[task.id]['total_hours'], 99.99),2)
            if task.stage_id and task.stage_id.fold:
                res[task.id]['progress'] = 100.0
        return res

    delegated_user_id = fields.Many2one('res.users', string='Delegated To')
    work_ids = fields.One2many('project.task.work', 'task_id', 'Work done')
    id = fields.Integer('ID', readonly=True)
    categ_ids = fields.Many2many('project.category', string='Tags')
    reviewer_id = fields.Many2one('res.users', 'Reviewer', store=True)
    remaining_hours = fields.Float('Remaining Hours', digits=(16,2), help="Total remaining time, can be re-estimated periodically by the assignee of the task.")
    effective_hours = fields.Float('Hours Spent', compute='_hours_get', multi='hours', help="Computed using the sum of the task work done."
        #,store = {
        #    'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
        #    'project.task.work': (_get_task, ['hours'], 10),}
        )
    total_hours = fields.Float('Total', compute='_hours_get', help="Computed as: Time Spent + Remaining Time."
        #,store = {
        #    'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
        #    'project.task.work': (_get_task, ['hours'], 10),}
        )
    progress = fields.Float('Working Time Progress (%)', multi='hours', compute='_hours_get', group_operator="avg", default=0,
    help="If the task has a progress of 99.99% you should close the task if it's finished or reevaluate the time"
        #,store = {
        #    'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours', 'state', 'stage_id'], 10),
        #    'project.task.work': (_get_task, ['hours'], 10),}
        )
    delay_hours = fields.Float('Delay Hours', multi='hours', compute='_hours_get', help="Computed as difference between planned hours by the project manager and the total hours of the task."
        #,store = {
        #    'project.task': (lambda self, cr, uid, ids, c={}: ids, ['work_ids', 'remaining_hours', 'planned_hours'], 10),
        #    'project.task.work': (_get_task, ['hours'], 10),}
        )

    def _compute_access_warning(self):
        super(Task, self)._compute_access_warning()
        for task in self.filtered(lambda x: x.project_id.privacy_visibility != 'portal'):
            task.access_warning = _(
                "The task cannot be shared with the recipient(s) because the privacy of the project is too restricted. Set the privacy of the project to 'Visible by following customers' in order to make it accessible by the recipient(s).")

    @api.model
    def _store_history(self):
        #raise UserError(_('task: '+str(self._context['ids'])))
        for task in self.browse(self._context['ids']):
            #raise UserError(_('_store_history\n\ntask_id: '+str(task.id)))
            self.env['project.task.history'].create({
                'task_id': task.id,
                'remaining_hours': task.remaining_hours,
                'planned_hours': task.planned_hours,
                'kanban_state': task.kanban_state,
                'type_id': task.stage_id.id
            })
        return True

    def flatten(self,l):
        return self.flatten(l[0]) + (len(l) > 1 and self.flatten(l[1:]) or []) if (type(l) is list and len(l)>0) else [l]

    @api.multi
    def message_auto_subscribe(self, updated_fields, values=None):
        """ override 'message_auto_subscribe' function in 'mail.thread' ."""
        new_partners, new_channels = dict(), dict()
        restrict_task_follow = self.project_id.restrict_automatic_task_follow
        user_field_lst = self._message_get_auto_subscribe_fields(updated_fields)
        subtypes = self.env['mail.message.subtype'].search(
            ['|', ('res_model', '=', False), ('parent_id.res_model', '=', self._name)])
        relation_fields = set([subtype.relation_field for subtype in subtypes if subtype.relation_field is not False])
        if not any(relation in updated_fields for relation in relation_fields) and not user_field_lst:
            return True
        if values is None:
            record = self[0]
            for updated_field in updated_fields:
                field_value = getattr(record, updated_field)
                if isinstance(field_value, models.BaseModel):
                    field_value = field_value.id
                values[updated_field] = field_value
        headers = set()
        for subtype in subtypes:
            if subtype.relation_field and values.get(subtype.relation_field):
                headers.add((subtype.res_model, values.get(subtype.relation_field)))
        if headers:
            header_domain = ['|'] * (len(headers) - 1)
            for header in headers:
                header_domain += ['&', ('res_model', '=', header[0]), ('res_id', '=', header[1])]
            if not restrict_task_follow:
                for header_follower in self.env['mail.followers'].sudo().search(header_domain):
                    for subtype in header_follower.subtype_ids:
                        if subtype.parent_id and subtype.parent_id.res_model == self._name:
                            new_subtype = subtype.parent_id
                        elif subtype.res_model is False:
                            new_subtype = subtype
                        else:
                            continue
                        if header_follower.partner_id:
                            new_partners.setdefault(header_follower.partner_id.id, set()).add(new_subtype.id)
                        else:
                            new_channels.setdefault(header_follower.channel_id.id, set()).add(new_subtype.id)
        user_ids = [values[name] for name in user_field_lst if values.get(name)]
        user_ids=self.flatten(user_ids)
        #opensolve fix here to cope with multiple assignees in the task

        #lets get old user_ids and reviewer_ids

        old_user_ids=[]
        if self.user_id:
            old_user_ids=[x.id for x in self.user_id]
        if self.reviewer_id:
            old_user_ids.extend([self.reviewer_id.id])

        if old_user_ids:
            old_user_pids = [user.partner_id.id for user in self.env['res.users'].sudo().browse([x for x in old_user_ids if x])]
        else:
            old_user_pids = []

        #This is a patch for a problem with an empty user_id list ending up as a key in the values dictionary of the write
        user_pids=[]
        try:
            if len(user_ids)==1:
                user_pids = [user.partner_id.id for user in self.env['res.users'].sudo().browse([x for x in user_ids if x])]
            elif len(user_ids)>1:
                user_pids = [user.partner_id.id for user in self.env['res.users'].sudo().browse([x for x in user_ids[1:] if x])]
        except:
            pass

        #union

        total_union_set=set(old_user_pids or [])|set(user_pids or [])
        user_pids=list(total_union_set)

        #remove all old user_ids followers
        self.message_unsubscribe([x.id for x in self.message_follower_ids if x.id not in user_pids])

        for partner_id in user_pids:
            new_partners.setdefault(partner_id, None)
        for pid, subtypes in new_partners.items():
            subtypes = list(subtypes) if subtypes is not None else None
            self.message_subscribe(partner_ids=[pid], subtype_ids=subtypes)
        for cid, subtypes in new_channels.items():
            subtypes = list(subtypes) if subtypes is not None else None
            self.message_subscribe(channel_ids=[cid], subtype_ids=subtypes)
        user_pids = [user_pid for user_pid in user_pids if user_pid != self.env.user.partner_id.id]

        self._message_auto_subscribe_notify(user_pids)
        return True


    @api.multi
    def write(self, values):
        result=super(Task, self).write(values)
        _logger.debug("writevalues=%s",values)
        #self.message_auto_subscribe(['user_id','reviewer_id'], values) error_jose: superno tiene atributo message_auto_subscribe
        return result

    def message_get_suggested_recipients(self):
        """ Returns suggested recipients for ids. Those are a list of
            tuple (partner_id, partner_name, reason), to be managed by Chatter. """
        result = dict((res_id, []) for res_id in self._ids)
        if 'user_id' in self._fields:
            for obj in self.browse(self._ids):  # SUPERUSER because of a read on res.users that would crash otherwise
                if not obj.user_id:
                    continue
                else:
                    for ob in obj.user_id:
                        if not ob.partner_id:
                            continue
                        else:
                            self._message_add_suggested_recipient(result, obj, partner=ob.partner_id, reason=self._fields['user_id'].string)
        return result

class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    def _get_full_name(self):
        res = {}
        for elmt in self.browse(self._ids):
            res[elmt.id] = self._get_one_full_name(elmt)
        return res

    def _get_one_full_name(self, elmt, level=6):
        if level<=0:
            return '...'
        if elmt.parent_id and not elmt.type == 'template':
            parent_path = self._get_one_full_name(elmt.parent_id, level-1) + " / "
        else:
            parent_path = ''
        return parent_path + elmt.name

    def _child_compute(self):
        result = {}
        for account in self.browse(self._ids):
            result[account.id] = map(lambda x: x.id, [child for child in account.child_ids if child.state != 'template'])

        return result

    name = fields.Char('Account/Contract Name', required=True, track_visibility='onchange')
    complete_name = fields.Char(string='Full Name', compute='_get_full_name')
    use_tasks = fields.Boolean('Tasks_',help="If checked, this contract will be available in the project menu and you will be able to manage tasks or track issues", default=True)
    company_uom_id = fields.Many2one('uom.uom', 'project_time_mode_id', related='company_id')
    state = fields.Selection([('open','In Progress'),
                              ('close','Closed'),
                              ('pending','To Renew')],'Status', required=True,
                                  track_visibility='onchange', copy=False,default='open')

    code = fields.Char(string='Reference', index=True, track_visibility='onchange', default=lambda self: self.env['ir.sequence'].next_by_code('Analytic_account'))
    parent_id = fields.Many2one('account.analytic.account', 'Parent Analytic Account') #, default=61
    child_ids = fields.One2many('account.analytic.account', 'parent_id', 'Child Accounts')
    child_complete_ids = fields.Many2many(relation='account.analytic.account', compute='_child_compute', string="Account Hierarchy")
    template_id = fields.Many2one('account.analytic.account', 'Template of Contract')
    description = fields.Text('Description')
    user_id = fields.Many2one('res.users', 'Project Manager', track_visibility='onchange',default=lambda self: self.env.uid )
    manager_id = fields.Many2one('res.users', 'Account Manager', track_visibility='onchange', default=lambda self: self.env.context.get('manager_id', False))
    date_start = fields.Date('Start Date', default=lambda *a: time.strftime('%Y-%m-%d'))
    date = fields.Date('Expiration Date', index=True, track_visibility='onchange')
    type = fields.Selection([('view','Analytic View'), ('normal','Analytic Account'),('contract','Contract or Project'),('template','Template of Contract')], 'Type of Account', required=True,
                                 help="If you select the View Type, it means you won\'t allow to create journal entries using that account.\n"\
                                  "The type 'Analytic account' stands for usual accounts that you only want to use in accounting.\n"\
                                  "If you select Contract or Project, it offers you the possibility to manage the validity and the invoicing options for this account.\n"\
                                  "The special type 'Template of Contract' allows you to define a template with default data that you can reuse easily.",default='normal')

    def on_change_template(self, template_id, date_start=False):
        if not template_id:
            return {}
        res = {'value':{}}
        template = self.browse(template_id)
        if template.date_start and template.date:
            from_dt = datetime.strptime(template.date_start, tools.DEFAULT_SERVER_DATE_FORMAT)
            to_dt = datetime.strptime(template.date, tools.DEFAULT_SERVER_DATE_FORMAT)
            timedelta = to_dt - from_dt
            res['value']['date'] = datetime.strftime(datetime.now() + timedelta, tools.DEFAULT_SERVER_DATE_FORMAT)
        if not date_start:
            res['value']['date_start'] = fields.date.today()
        res['value']['quantity_max'] = template.quantity_max
        res['value']['parent_id'] = template.parent_id and template.parent_id.id or False
        res['value']['description'] = template.description

        if template_id and 'value' in res:
            template = self.browse(template_id)
            res['value']['use_tasks'] = template.use_tasks
        return res

    def on_change_partner_id(self, partner_id, name):
        res={}
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            if partner.user_id:
                res['manager_id'] = partner.user_id.id
            if not name:
                res['name'] = _('Contract: ') + partner.name
        return {'value': res}

    def on_change_company(self, company_id):
        if not company_id:
            return {}
        currency = self.env['res.company'].read(['currency_id'])[0]['currency_id']
        return {'value': {'currency_id': currency}}

    @api.model
    def _trigger_project_creation(self, vals):
        context=self._context
        '''
        This function is used to decide if a project needs to be automatically created or not when an analytic account is created. It returns True if it needs to be so, False otherwise.
        '''
        if context is None: context = {}
        return vals.get('use_tasks') and not 'project_creation_in_progress' in context

    @api.model
    def project_create(self, analytic_account_id, vals):
        '''
        This function is called at the time of analytic account creation and is used to create a project automatically
        linked to it if the conditions are meet.
        '''
        project_pool = self.env['project.project']
        project_id = project_pool.search([('analytic_account_id','=', analytic_account_id)])
        #raise UserError(_('project_create\n\nvals: '+str(vals)+'\n\nanalytic_account_id: '+str(analytic_account_id.id)+'\n\nproject_pool: ' +str(project_pool)+'\n\nproject_pool2: ' +str(project_pool2)+'\n\nproject_id: ' +str(project_id)))
        if not project_id and self._trigger_project_creation(vals):
            project_values = {
                'name': vals.get('name'),
                'analytic_account_id': analytic_account_id,
                'type': vals.get('type','contract'),
            }
            return self.env['project.project'].create(project_values)
        return False

    @api.model
    def create(self, vals):
        context=self._context
        if vals.get('child_ids', False) and context.get('analytic_project_copy', False):
            vals['child_ids'] = []
        #self.env.context = self.with_context(context).env.context
        #raise UserError(_('create account_analytic_account\n\nvals: '+str(vals)+'\n\ncontext: '+str(context)))
        analytic_account_id = super(account_analytic_account, self).create(vals)
        #raise UserError(_('create account.analytic.account\n\nvals: '+str(vals)+'\n\ncontext: '+str(context)+'\n\nsumatoria: '+str(sumatoria)+'\n\nanalytic_account_id: '+str(analytic_account_id)))
        self.project_create(analytic_account_id.id, vals)
        return analytic_account_id

    @api.multi
    def write(self, vals):
        #raise UserError(_('write account.analytic.account'))
        ids=self._ids
        if isinstance(ids, (int, int)):
            ids = [ids]
        vals_for_project = vals.copy()
        for account in self.browse(ids):
            #raise UserError('write account: '+str(account.id))
            if not vals.get('name'):
                vals_for_project['name'] = account.name
            """if not vals.get('type'):
                vals_for_project['type'] = account.type"""
            self.project_create(account.id, vals_for_project)
        return super(account_analytic_account, self).write(vals)

    @api.multi
    def unlink(self):
        project_obj = self.env['project.project']
        analytic_ids = project_obj.search([('analytic_account_id','in',self._ids)])
        if analytic_ids:
            raise UserError(_('Warning!'), _('Please delete the project linked with this account first.'))
        return super(account_analytic_account, self).unlink()

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        context=self._context
        if context.get('current_model') == 'project.project':
            project_ids = self.search(args + [('name', operator, name)], limit=limit)
            return self.with_context(id=project_ids).name_get()
        return super(account_analytic_account, self).name_search(name, args=args, operator=operator, limit=limit)

class project_work(models.Model):
    _name = "project.task.work"
    _description = "Project Task Work"

    name = fields.Char('Work summary')
    date = fields.Datetime('Date', index="1", default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))  #default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S')
    task_id = fields.Many2one('project.task', 'Task', ondelete='cascade', required=True, index="1")
    hours = fields.Float('Time Spent')
    user_id = fields.Many2one('res.users', 'Done by', required=True, index="1", default=lambda obj: obj)
    company_id = fields.Many2one('res.company', string='Company', related='task_id.company_id', store=True)

    _order = "date desc"

    @api.model
    def create(self, vals):
        #raise UserError(_('project.task.work.\nvals: '+str(vals)+'\ncontext: '+str(context)))
        if 'hours' in vals and (not vals['hours']):
            vals['hours'] = 0.00
        if 'task_id' in vals:
            self._cr.execute('update project_task set remaining_hours=remaining_hours - %s where id=%s', (vals.get('hours',0.0), vals['task_id']))
            self.env['project.task'].invalidate_cache(['remaining_hours'], [vals['task_id']])
        #self.env.context = self.with_context(self._context).env.context
        #raise UserError('project.task.work: \n\nvals: '+str(vals))
        return super(project_work,self).create(vals)

    @api.multi
    def write(self, vals):
        #raise UserError('project_work write')
        if 'hours' in vals and (not vals['hours']):
            vals['hours'] = 0.00
        if 'hours' in vals:
            task_obj = self.env['project.task']
            for work in self.browse(self._ids):
                self._cr.execute('update project_task set remaining_hours=remaining_hours - %s + (%s) where id=%s', (vals.get('hours',0.0), work.hours, work.task_id.id))
                task_obj.invalidate_cache(['remaining_hours'], [work.task_id.id])
        return super(project_work,self).write(vals)

    @api.multi
    def unlink(self):
        task_obj = self.env['project.task']
        for work in self.browse(self._ids):
            self._cr.execute('update project_task set remaining_hours=remaining_hours + %s where id=%s', (work.hours, work.task_id.id))
            task_obj.invalidate_cache(['remaining_hours'], [work.task_id.id])
        return super(project_work,self).unlink()


class project_task_history(models.Model):
    """
    Tasks History, used for cumulative flow charts (Lean/Agile)
    """
    _name = 'project.task.history'
    _description = 'History of Tasks'
    #_rec_name = 'task_id'
    #_log_access = False

    def _get_date(self):
        result = {}
        for history in self.browse(self._ids):
            if history.type_id and history.type_id.fold:
                result[history.id] = history.date
                continue
            self._cr.execute('''select
                    date
                from
                    project_task_history
                where
                    task_id=%s and
                    id>%s
                order by id limit 1''', (history.task_id.id, history.id))
            res = self._cr.fetchone()
            result[history.id] = res and res[0] or False
        return result

    def _get_related_date(self):
        result = []
        for history in self.browse(self._ids):
            self._cr.execute('''select
                    id
                from
                    project_task_history
                where
                    task_id=%s and
                    id<%s
                order by id desc limit 1''', (history.task_id.id, history.id))
            res = self._cr.fetchone()
            if res:
                result.append(res[0])
        return result

    task_id = fields.Many2one('project.task', 'Task', required=True, ondelete='cascade', store=True) #
    type_id = fields.Many2one('project.task.type', 'Stage')
    kanban_state = fields.Selection([('normal', 'Normal'),
    ('blocked', 'Blocked'),
    ('done', 'Ready for next stage')], 'Kanban State', required=False)
    date = fields.Date('Date', store=True, default=fields.Date.context_today)
    end_date = fields.Char(compute='_get_date', string='End Date', type="date"
        """,store={
            'project.task.history': (_get_related_date, None, 20)
        }""")
    remaining_hours = fields.Float('Remaining Time', digits=(16, 2))
    planned_hours = fields.Float('Planned Time', digits=(16, 2))
    user_id = fields.Many2one('res.users', 'Responsible')

class project_task_history_cumulative(models.Model):
    _name = 'project.task.history.cumulative'
    _table = 'project_task_history_cumulative'
    _inherit = 'project.task.history'
    _auto = False

    end_date = fields.Date('End Date')
    nbr_tasks = fields.Integer('# of Tasks', readonly=True)
    project_id = fields.Many2one('project.project', 'Project')

    def init(self):
        cr=self._cr
        tools.drop_view_if_exists(cr, 'project_task_history_cumulative')

        cr.execute(""" CREATE VIEW project_task_history_cumulative AS (
            SELECT
                history.date::varchar||'-'||history.history_id::varchar AS id,
                history.date AS end_date,
                *
            FROM (
                SELECT
                    h.id AS history_id,
                    h.date AS date,
                    h.task_id, h.type_id, h.user_id, h.kanban_state,
                    count(h.task_id) as nbr_tasks,
                    greatest(h.remaining_hours, 1) AS remaining_hours, greatest(h.planned_hours, 1) AS planned_hours,
                    t.project_id

                FROM
                    project_task_history AS h
                    JOIN project_task AS t ON (h.task_id = t.id)
                GROUP BY
                  h.id,
                  h.task_id,
                  t.project_id
            ) AS history
        )
        """)#h.date+generate_series(0, CAST((coalesce(h.end_date, DATE 'tomorrow')::date - h.date) AS integer)-1) AS date,


class project_category(models.Model):
    """ Category of project's task (or issue) """
    _name = "project.category"
    _description = "Category of project's task, issue, ..."

    name = fields.Char('Name', required=True, translate=True)
