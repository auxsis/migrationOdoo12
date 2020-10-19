# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'res.config.settings'

    module_project_forecast = fields.Boolean(string="Forecasts")
    module_hr_timesheet = fields.Boolean(string="Task Logs")
    group_subtask_project = fields.Boolean("Sub-tasks", implied_group="project.group_subtask_project")
    group_project_rating = fields.Boolean("Use Rating on Project", implied_group='project.group_project_rating')

    module_sale_service = fields.Boolean('Generate tasks from sale orders',
        help='This feature automatically creates project tasks from service products in sale orders. '
             'More precisely, tasks are created for procurement lines with product of type \'Service\', '
             'procurement method \'Make to Order\', and supply method \'Manufacture\'.\n'
             '-This installs the module sale_service.')
    module_pad = fields.Boolean("Use integrated collaborative note pads on task",
        help='Lets the company customize which Pad installation should be used to link to new pads '
             '(for example: http://ietherpad.com/).\n'
             '-This installs the module pad.')
    module_project_timesheet = fields.Boolean("Record timesheet lines per tasks",
        help='This allows you to transfer the entries under tasks defined for Project Management to '
             'the timesheet line entries for particular date and user, with the effect of creating, '
             'editing and deleting either ways.\n'
             '-This installs the module project_timesheet.')
    module_project_issue = fields.Boolean("Track issues and bugs",
        help='Provides management of issues/bugs in projects.\n'
             '-This installs the module project_issue.')
    time_unit = fields.Many2one('uom.uom', 'Working time unit',
        help='This will set the unit of measure used in projects and tasks.\n'
             'Changing the unit will only impact new entries.')
    module_project_issue_sheet = fields.Boolean("Invoice working time on issues",
        help='Provides timesheet support for the issues/bugs management in project.\n'
             '-This installs the module project_issue_sheet.')
    group_tasks_work_on_tasks = fields.Boolean("Log work activities on tasks",
        implied_group='project_extra.group_tasks_work_on_tasks',
        help="Allows you to compute work on tasks.")
    group_time_work_estimation_tasks = fields.Boolean("Manage time estimation on tasks",
        implied_group='project_extra.group_time_work_estimation_tasks',
        help="Allows you to compute Time Estimation on tasks.")
    group_manage_delegation_task = fields.Boolean("Allow task delegation",
        implied_group='project_extra.group_delegate_task',
        help="Allows you to delegate tasks to other users.")

    @api.model
    def get_default_time_unit(self, fields):
        user = self.env['res.users'].browse(self._uid)
        return {'time_unit': user.id.company_id.project_time_mode_id.id}

    @api.model
    def set_time_unit(self, fields):
        config = self.browse(self._ids)
        user = self.env['res.users'].browse(self._uid)
        user.company_id.write({'project_time_mode_id': config.time_unit.id})

    def onchange_time_estimation_project_timesheet(self, group_time_work_estimation_tasks, module_project_timesheet):
        if group_time_work_estimation_tasks or module_project_timesheet:
            return {'value': {'group_tasks_work_on_tasks': True}}
        return {}
