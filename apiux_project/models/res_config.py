# -*- coding: utf-8 -*-
import logging

from odoo import models,fields,api
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    project_sequence=fields.Many2one('ir.sequence', 'Project Sequence')
    task_sequence=fields.Many2one('ir.sequence', 'Task Sequence')


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            project_sequence = int(self.env['ir.config_parameter'].sudo().get_param('apiux_project.project_sequence')),
            task_sequence = int(self.env['ir.config_parameter'].sudo().get_param('apiux_project.task_sequence')),
         
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()

        field1 = self.project_sequence and self.project_sequence.id or False
        field2 = self.task_sequence and self.task_sequence.id or False


        param.set_param('apiux_project.project_sequence', field1)
        param.set_param('apiux_project.task_sequence', field2) 

