# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import logging


_logger = logging.getLogger(__name__)


class account_analytic_line(models.Model):
    _inherit='account.analytic.line'
    
    journal_id=fields.Many2one('account.analytic.journal', string='Analytic Journal')


    def _timesheet_preprocess(self, vals):

        vals=super(account_analytic_line,self)._timesheet_preprocess(vals)
        # employee implies analytic journal
        if vals.get('employee_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            vals['journal_id'] = employee.journal_id.id                   
        return vals


    @api.model
    def create(self, values):
        # compute employee only for timesheet lines, makes no sense for other lines
        if not values.get('employee_id') and values.get('project_id'):
            if values.get('user_id'):
                ts_user_id = values['user_id']
            else:
                ts_user_id = self._default_user()
            values['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id),'|',('active','=',False),('active','=',True)], limit=1).id
        _logger.info("values1=%s",values)
        values = self._timesheet_preprocess(values)
        _logger.info("values2=%s",values)
        result = super(account_analytic_line, self).create(values)
        if result.project_id:  # applied only for timesheet
            result._timesheet_postprocess(values)
        return result


class account_analytic_journal(models.Model):
    _name = 'account.analytic.journal'
    _description = 'Analytic Journal'

    name=fields.Char('Journal Name', required=True)
    code=fields.Char('Journal Code', size=8)
    active=fields.Boolean('Active', help="If the active field is set to False, it will allow you to hide the analytic journal without removing it.", default=True)
    type=fields.Selection([('sale','Sale'), ('purchase','Purchase'), ('cash','Cash'), ('general','General'), ('situation','Situation')], 'Type', default='general', required=True, help="Gives the type of the analytic journal. When it needs for a document (eg: an invoice) to create analytic entries, Odoo will look for a matching journal of the same type.")
    line_ids=fields.One2many('account.analytic.line', 'journal_id', 'Lines', copy=False)
    company_id=fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id)


class hr_employee(models.Model):
    _inherit='hr.employee'
    
    journal_id=fields.Many2one('account.analytic.journal', string='Analytic Journal')


class account_journal(models.Model):
    _inherit="account.journal"

    analytic_journal_id=fields.Many2one('account.analytic.journal','Analytic Journal', help="Journal for analytic entries")
    


class account_move(models.Model):
    _inherit='account.move'
    
    
    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items',states={'posted': [('readonly', False)]}, copy=True)    

 
    
class account_move_line(models.Model):
    _inherit='account.move.line'
    
  
    analytic_journal_id=fields.Many2one('account.analytic.journal','Analytic Journal', help="Journal for analytic entries")  
  
  
  
    @api.one
    def _prepare_analytic_line(self):
        res=super(account_move_line,self)._prepare_analytic_line()
        
        if not self.analytic_journal_id:
            raise ValidationError(_("Move line does not have an analytic journal specified. Cannot create the analytic line"))

        if type(res) is list:
            res=res[0]    

        res['journal_id']=self.analytic_journal_id.id
                
        return res



    @api.multi
    def write(self, vals):
    
        self.env.context = dict(self.env.context)
        allow_analytic_update=True
        if any(key in vals for key in ('account_id', 'journal_id', 'date', 'move_id', 'debit', 'credit')) and not any(key in vals for key in ('analytic_account_id', 'analytic_journal_id')):
            allow_analytic_update=False
        self.env.context.update({'allow_analytic_update': allow_analytic_update})    
    
        _logger.info("allowup=%s,%s",allow_analytic_update,vals)
    
        res = super(account_move_line, self).write(vals)
        if 'analytic_account_id' in vals or 'analytic_journal_id' in vals and self.move_id.state=='posted':
            self.env.context.update({'allow_analytic_update': allow_analytic_update}) 
            self.mapped('analytic_line_ids').unlink()
            self.create_analytic_lines()
        return res



    @api.multi
    def _update_check(self):
        """ Raise Warning to cause rollback if the move is posted, some entries are reconciled or the move is older than the lock date"""
        move_ids = set()
        for line in self:
             
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            if line.move_id.state != 'draft' and not self._context.get('allow_analytic_update', False):
                raise UserError(_('You cannot do this modification on a posted journal entry, you can just change some non legal fields. You must revert the journal entry to cancel it.\n%s.') % err_msg)
            if line.reconciled and not (line.debit == 0 and line.credit == 0):
                raise UserError(_('You cannot do this modification on a reconciled entry. You can just change some non legal fields or you must unreconcile first.\n%s.') % err_msg)
            if line.move_id.id not in move_ids:
                move_ids.add(line.move_id.id)
        self.env['account.move'].browse(list(move_ids))._check_lock_date()
        return True


class AccountInvoice(models.Model):
    _inherit='account.invoice'
    
    
    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()

        for dict_data in res:
            dict_data['analytic_journal_id'] = self.journal_id.analytic_journal_id.id

        return res    


    @api.model
    def tax_line_move_line_get(self):
        res = super(AccountInvoice, self).tax_line_move_line_get()

        for dict_data in res:
            dict_data['analytic_journal_id'] = self.journal_id.analytic_journal_id.id

        _logger.info("restaxline=%s",res)
        return res   
   
    
#apiux override this method in account/product.py to include invl_id when groupedlines on journal is false
class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _convert_prepared_anglosaxon_line(self, line, partner):
    
        res=super(ProductProduct,self)._convert_prepared_anglosaxon_line(line, partner)
        res['analytic_journal_id']=line.get('analytic_journal_id', False)
        return res
      

    
    
