# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountCommonReport(models.TransientModel):
    _inherit = "account.common.report"

    filter_by = fields.Selection([('date', 'Date'), ('period', 'Period')],
                                 string="Filter By")
    period_from = fields.Many2one('account.period', string="Start Period")
    period_to = fields.Many2one('account.period', string="End Period")

    @api.onchange('filter_by')
    def onchange_filter_by(self):
        self.date_from = False
        self.date_to = False
        self.period_from = False
        self.period_to = False

    @api.onchange('period_from', 'period_to')
    def onchange_period_from(self):
        self.date_from = self.period_from.date_start
        self.date_to = self.period_to.date_stop

    @api.multi
    def check_report(self):
        res = super(AccountCommonReport, self).check_report()
        if self.filter_by == 'period':
                res['data']['form']['date_from'] = self.period_from.date_start
                res['data']['form']['date_to'] = self.period_to.date_stop
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
