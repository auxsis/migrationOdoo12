from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    
    finance_assistant=fields.Many2one('hr.employee', 'Finance Assistant')
    finance_manager=fields.Many2one('hr.employee', 'Finance Manager')
    general_manager=fields.Many2one('hr.employee', 'General Manager')
    general_manager_approval_limit=fields.Integer('GM Approval Limit')
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            finance_assistant = int(self.env['ir.config_parameter'].sudo().get_param('apiux_purchase.finance_assistant')),
            finance_manager = int(self.env['ir.config_parameter'].sudo().get_param('apiux_purchase.finance_manager')),
            general_manager = int(self.env['ir.config_parameter'].sudo().get_param('apiux_purchase.general_manager')),
            general_manager_approval_limit = int(self.env['ir.config_parameter'].sudo().get_param('apiux_purchase.general_manager_approval_limit')),               
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()

        field1 = self.finance_assistant and self.finance_assistant.id or False
        field2 = self.finance_manager and self.finance_manager.id or False
        field3 = self.general_manager and self.general_manager.id or False        
        field4 = self.general_manager_approval_limit or -1 

        param.set_param('apiux_purchase.finance_assistant', field1)
        param.set_param('apiux_purchase.finance_manager', field2) 
        param.set_param('apiux_purchase.general_manager', field3)
        param.set_param('apiux_purchase.general_manager_approval_limit', field4)             