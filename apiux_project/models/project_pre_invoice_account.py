from odoo import _
from odoo import models, fields, api, exceptions
from odoo.exceptions import Warning,ValidationError,UserError
from odoo.tools.safe_eval import safe_eval

from collections import defaultdict
import collections

from lxml import etree
import logging

_logger = logging.getLogger(__name__)


class ProjectPreInvoiceAccount(models.Model):
    _name="project.pre.invoice.account"
    
    
    
    company_id=fields.Many2one('res.company', 'Company')
    sector_id=fields.Many2one('account.sector', 'Sector')
    cost_center_id=fields.Many2one('account.cost.center', 'Cost Center')   
    account_income_id=fields.Many2one('account.account', 'Account Income')
    account_expense_id=fields.Many2one('account.account', 'Account Expense')    
    account_receivable_id=fields.Many2one('account.account', 'Account Receivable')
    account_payable_id=fields.Many2one('account.account', 'Account Payable')
    active=fields.Boolean('Activo?')
    