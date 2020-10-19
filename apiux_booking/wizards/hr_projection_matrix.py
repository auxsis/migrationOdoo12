from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class HrProjectionMatrix(models.TransientModel):
    _name = 'hr.proj.matrix'
    _description = 'hr.proj.matrix'

    @api.onchange('project_id','user_id')
    def _onchange_project(self):
        domain_project=[('hr_proj_timesheet_ids','!=',False)]
        domain_user=[]
        if self.project_id:
            domain_project=[('hr_proj_timesheet_ids','!=',False),('project_id','=',self.project_id.id)]
        if self.user_id:
            domain_user=[('user_id','=',self.user_id.id)]
        recs = self.env['project.project'].sudo().search(domain_project)
        # same with users
        users = self.env['hr.projection.timesheet'].sudo().search(domain_user).mapped('user_id')
        list =[
            (0, 0, {
                'name': "{}'s task on {}".format(usr.name, rec.name),
                'account_id': rec.id,
                'user_id': usr.id,
                'from_date':'2018-12-12',
                'to_date':'2018-12-13',
                'amount': 0,
                'percentage':0
            })
            # if the project doesn't have a task for the user, create a new one
            if not rec.hr_proj_timesheet_ids.filtered(lambda x: x.user_id == usr) else
            # otherwise, return the task
            (4, rec.hr_proj_timesheet_ids.filtered(lambda x: x.user_id == usr)[0].id)
            for usr in users
            for rec in recs
        ]

        self.line_ids=list

    name=fields.Char('Name', default='Matriz')
    project_id=fields.Many2one('project.project', string='Proyecto')
    user_id=fields.Many2one('res.users',string='Recurso')
    line_ids = fields.Many2many(
        'hr.projection.timesheet', default=lambda self: self._default_line_ids())

    def _default_line_ids(self):
        recs = self.env['project.project'].sudo().search([('hr_proj_timesheet_ids','!=',False)])
        # same with users
        users = self.env['hr.projection.timesheet'].sudo().search([]).mapped('user_id')
        _logger.info("users=%s,%s",users,[rec.hr_proj_timesheet_ids for rec in recs])
        list =[
            (0, 0, {
                'name': "{}'s task on {}".format(usr.name, rec.name),
                'account_id': rec.id,
                'user_id': usr.id,
                'from_date':'2018-12-12',
                'to_date':'2018-12-13',
                'amount': 0,
                'percentage':0
            })
            # if the project doesn't have a task for the user, create a new one
            if not rec.hr_proj_timesheet_ids.filtered(lambda x: x.user_id == usr) else
            # otherwise, return the task
            (4, rec.hr_proj_timesheet_ids.filtered(lambda x: x.user_id == usr)[0].id)
            for usr in users
            for rec in recs
        ]
        return list

    @api.multi
    def open_x2m_matrix(self):
        wiz = self.create({})
        cform = self.env.ref('hr_projection_timesheet.hr_projection_x2many_2d_matrix', False)
        return {
            'name': 'Try x2many 2D matrix widget',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id':cform.id,
            'res_model': 'hr.proj.matrix',
            'target': 'current',
            'res_id': wiz.id,
            'context': self.env.context,
        }
