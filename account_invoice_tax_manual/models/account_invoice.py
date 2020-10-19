# -*- coding: utf-8 -*-
# Copyright 2009-2018 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    amount = fields.Monetary(help="Tax amount in invoice currency.")
