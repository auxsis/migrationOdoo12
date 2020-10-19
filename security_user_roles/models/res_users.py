# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.tools import partition


class res_users(models.Model):
    """
    Re write to change user role
    """
    _inherit = "res.users"

    @api.multi
    def _inverse_security_role_ids(self):
        """
        Inverse method for security_role_ids
        """
        for user in self:
            if user.security_role_ids:
                all_groups = user.security_role_ids.mapped("group_ids")
                user.groups_id = [(6, 0, all_groups.ids)]

    security_role_ids = fields.Many2many(
        "security.role",
        "security_role_res_users_rel_table",
        "security_role_id",
        "res_users_id",
        string="Roles",
        inverse=_inverse_security_role_ids,
    )

    @api.multi
    def action_create_role(self):
        """
        The method to open a role form view with pre-filled groups

        Returns:
         * ir.actions.window

        Extra info:
         * Expected singletom
        """
        self.ensure_one()
        action = self.env.ref("security_user_roles.security_role_action_form_only").read()[0]
        action["context"] = {"default_group_ids": [(6, 0, self.groups_id.ids)]}
        return action
