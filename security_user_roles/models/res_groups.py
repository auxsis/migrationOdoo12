# -*- coding: utf-8 -*-

from lxml import etree
from lxml.builder import E

from odoo import _, api, models

def name_boolean_group(id):
    return 'in_group_' + str(id)

def name_selection_groups(ids):
    return 'sel_groups_' + '_'.join(str(it) for it in ids)


class res_groups(models.Model):
    """
    Re write to update xml view of security roles
    """
    _inherit = "res.groups"

    @api.model
    def create(self, values):
        """
        Re-write to update view of security role

        Methods:
         * _update_security_role_view
        """
        user = super(res_groups, self).create(values)
        self._update_security_role_view()
        self.env['ir.actions.actions'].clear_caches()
        return user

    @api.multi
    def write(self, values):
        """
        Re-write to update view of security role

        Methods:
         * _update_security_role_view
        """
        res = super(res_groups, self).write(values)
        self._update_security_role_view()
        self.env['ir.actions.actions'].clear_caches()
        return res

    @api.multi
    def unlink(self):
        """
        Re-write to update view of security role

        Methods:
         * _update_security_role_view
        """
        res = super(res_groups, self).unlink()
        self._update_security_role_view()
        self.env['ir.actions.actions'].clear_caches()
        return res

    @api.model
    def _update_security_role_view(self):
        """
        The method to prepare the view of rights the same as a user form view (mostly copied as for users view in base)
        """
        if self._context.get('install_mode'):
            user_context = self.env['res.users'].context_get()
            self = self.with_context(**user_context)

        view = self.env.ref('security_user_roles.security_groups_view', raise_if_not_found=False)
        if view and view.exists() and view._name == 'ir.ui.view':
            group_no_one = view.env.ref('base.group_no_one')
            group_employee = view.env.ref('base.group_user')
            xml1, xml2, xml3 = [], [], []
            xml1.append(E.separator(string=_('User Type'), colspan="2", groups='base.group_no_one'))
            xml2.append(E.separator(string=_('Application Accesses'), colspan="2"))

            user_type_field_name = ''
            for app, kind, gs in self.get_groups_by_application():
                attrs = {}
                if app.xml_id in ('base.module_category_hidden', 'base.module_category_extra',
                                  'base.module_category_usability'):
                    attrs['groups'] = 'base.group_no_one'
                if app.xml_id == 'base.module_category_user_type':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    user_type_field_name = field_name
                    attrs['widget'] = 'radio'
                    attrs['groups'] = 'base.group_no_one'
                    xml1.append(E.field(name=field_name, **attrs))
                    xml1.append(E.newline())

                elif kind == 'selection':
                    field_name = name_selection_groups(gs.ids)
                    xml2.append(E.field(name=field_name, **attrs))
                    xml2.append(E.newline())
                else:
                    app_name = app.name or _('Other')
                    xml3.append(E.separator(string=app_name, colspan="4", **attrs))
                    for g in gs:
                        field_name = name_boolean_group(g.id)
                        if g == group_no_one:
                            xml3.append(E.field(name=field_name, invisible="1", **attrs))
                        else:
                            xml3.append(E.field(name=field_name, **attrs))

            xml3.append({'class': "o_label_nowrap"})
            if user_type_field_name:
                user_type_attrs = {'invisible': [(user_type_field_name, '!=', group_employee.id)]}
            else:
                user_type_attrs = {}

            xml = E.field(
                E.group(*(xml1), col="2"),
                E.group(*(xml2), col="2", attrs=str(user_type_attrs)),
                E.group(*(xml3), col="4", attrs=str(user_type_attrs)), name="group_ids", position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))
            xml_content = etree.tostring(xml, pretty_print=True, encoding="unicode")

            new_context = dict(view._context)
            new_context.pop('install_mode_data', None)  # don't set arch_fs for this computed view
            new_context['lang'] = None
            view.with_context(new_context).write({'arch': xml_content})
