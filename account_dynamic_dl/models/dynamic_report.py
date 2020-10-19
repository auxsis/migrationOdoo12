# -*- coding: utf-8 -*-

import time
import json
import calendar

from odoo import api, fields, models, _
from odoo.tools.misc import format_date
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, pycompat, config, date_utils
from odoo.osv import expression
from babel.dates import get_quarter_names
from odoo.tools.misc import formatLang, format_date, get_user_companies
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ReportDynamicDailyLedger(models.AbstractModel):
    _name = 'report.account.dynamic.report_dailyledger'

    @api.model
    def get_invoice_details(self,lref):
        '''
        Used to find out invoice id from reference number in move line
        :param lref: Char .from account move line
        :return: Integer .invoice id or False
        '''
        if lref:
            invoice_id = self.env['account.invoice'].search([('number','=',lref)]).id
            return invoice_id or False
        return False
        

    @api.multi
    def get_date_from_filter(self,filter):
        '''
        :param filter: dictionary
                {u'disabled': False, u'text': u'This month', u'locked': False, u'id': u'this_month', u'element': [{}]}
        :return: date_from and date_to
        '''
        if filter.get('id'):
            date = datetime.today()
            
            if filter['id'] == 'today':
                date_from = date.strftime("%Y-%m-%d")
                date_to = date.strftime("%Y-%m-%d")
                return date_from, date_to
            if filter['id'] == 'this_week':
                day_today = date - timedelta(days=date.weekday())
                date_from = (day_today - timedelta(days=date.weekday()) ).strftime("%Y-%m-%d")
                date_to = (day_today + timedelta(days=6)).strftime("%Y-%m-%d")
                return date_from, date_to
            if filter['id'] == 'this_month':
                date_from = datetime(date.year, date.month, 1).strftime("%Y-%m-%d")
                date_to = datetime(date.year, date.month, calendar.mdays[date.month]).strftime("%Y-%m-%d")
                return date_from,date_to
            if filter['id'] == 'this_quarter':
                if int((date.month-1) / 3) == 0: # First quarter
                    date_from = datetime(date.year, 1, 1).strftime("%Y-%m-%d")
                    date_to = datetime(date.year, 3, calendar.mdays[3]).strftime("%Y-%m-%d")
                if int((date.month-1) / 3) == 1: # First quarter
                    date_from = datetime(date.year, 4, 1).strftime("%Y-%m-%d")
                    date_to = datetime(date.year, 6, calendar.mdays[6]).strftime("%Y-%m-%d")
                if int((date.month-1) / 3) == 2: # First quarter
                    date_from = datetime(date.year, 7, 1).strftime("%Y-%m-%d")
                    date_to = datetime(date.year, 9, calendar.mdays[9]).strftime("%Y-%m-%d")
                if int((date.month-1) / 3) == 3: # First quarter
                    date_from = datetime(date.year, 10, 1).strftime("%Y-%m-%d")
                    date_to = datetime(date.year, 12, calendar.mdays[12]).strftime("%Y-%m-%d")
                return date_from, date_to
            if filter['id'] == 'this_financial_year':
                date_from = datetime(date.year, 1, 1).strftime("%Y-%m-%d")
                date_to = datetime(date.year, 12, 31).strftime("%Y-%m-%d")
                return date_from, date_to
            date = (datetime.now() - relativedelta(day=1))
            if filter['id'] == 'yesterday':
                date_from = date.strftime("%Y-%m-%d")
                date_to = date.strftime("%Y-%m-%d")
                return date_from, date_to
            date = (datetime.now() - relativedelta(day=7))
            if filter['id'] == 'last_week':
                day_today = date - timedelta(days=date.weekday())
                date_from = (day_today - timedelta(days=date.weekday())).strftime("%Y-%m-%d")
                date_to = (day_today + timedelta(days=6)).strftime("%Y-%m-%d")
                return date_from, date_to
            date = (datetime.now() - relativedelta(months=1))
            if filter['id'] == 'last_month':
                date_from = datetime(date.year, date.month, 1).strftime("%Y-%m-%d")
                date_to = datetime(date.year, date.month, calendar.mdays[date.month]).strftime("%Y-%m-%d")
                return date_from, date_to
            date = (datetime.now() - relativedelta(months=3))
            if filter['id'] == 'last_quarter':
                if int((date.month-1) / 3) == 0:  # First quarter
                    date_from = datetime(date.year, 1, 1).strftime("%Y-%m-%d")
                    date_to = datetime(date.year, 3, calendar.mdays[3]).strftime("%Y-%m-%d")
                if int((date.month-1) / 3) == 1:  # Second quarter
                    date_from = datetime(date.year, 4, 1).strftime("%Y-%m-%d")
                    date_to = datetime(date.year, 6, calendar.mdays[6]).strftime("%Y-%m-%d")
                if int((date.month-1) / 3) == 2:  # Third quarter
                    date_from = datetime(date.year, 7, 1).strftime("%Y-%m-%d")
                    date_to = datetime(date.year, 9, calendar.mdays[9]).strftime("%Y-%m-%d")
                if int((date.month-1) / 3) == 3:  # Fourth quarter
                    date_from = datetime(date.year, 10, 1).strftime("%Y-%m-%d")
                    date_to = datetime(date.year, 12, calendar.mdays[12]).strftime("%Y-%m-%d")
                return date_from, date_to
            date = (datetime.now() - relativedelta(years=1))
            if filter['id'] == 'last_financial_year':
                date_from = datetime(date.year, 1, 1).strftime("%Y-%m-%d")
                date_to = datetime(date.year, 12, 31).strftime("%Y-%m-%d")
                return date_from, date_to

    def _get_account_move_entry(self, accounts, init_balance, sortby, display_account):
        """
        :param:
                accounts: the recordset of accounts
                init_balance: boolean value of initial_balance
                sortby: sorting by date or partner and journal
                display_account: type of account(receivable, payable and both)

        Returns a dictionary of accounts with following key and value {
                'code': account code,
                'name': account name,
                'debit': sum of total debit amount,
                'credit': sum of total credit amount,
                'balance': total balance,
                'amount_currency': sum of amount_currency,
                'move_lines': list of move line
        }
        """
        context = dict(self.env.context or {})
        cr = self.env.cr
        MoveLine = self.env['account.move.line']
        move_lines = dict(map(lambda x: (x, []), accounts.ids))

        sql_sort = 'l.date, m.name'
        if sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'

        # Prepare sql query base on selected parameters from wizard
        context.update({'initial_bal':False})
        tables, where_clause, where_params = MoveLine.with_context(context)._query_get()
        new_where_params=[]
        for param in where_params:
            try:
                new_where_params.append(datetime.strftime(datetime.strptime(param,'%d/%m/%Y'),'%Y-%m-%d'))
            except:
                new_where_params.append(param)
            
        where_params=new_where_params
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        filters = filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')

        # Get move lines base on sql query and Calculate the total balance of move lines
        sql = ('''SELECT l.id AS lid, l.account_id AS account_id, COALESCE(to_char(l.date,'DD-MM-YYYY')) AS ldate, j.code AS lcode,asec.name as lsector,acen.name as lcenter, l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit,\
            m.name AS move_name, l.move_id AS move_id, c.symbol AS currency_code,c.position AS amount_currency_position, p.display_name AS partner_name,afr.name AS reconciled\
            FROM account_move_line l\
            JOIN account_move m ON (l.move_id=m.id)\
            JOIN account_journal j ON (l.journal_id=j.id)\
            JOIN account_account acc ON (l.account_id = acc.id)\
            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
            LEFT JOIN account_sector asec ON (l.sector_id=asec.id)\
            LEFT JOIN account_cost_center acen ON (l.cost_center_id=acen.id)\
            LEFT JOIN account_full_reconcile afr on afr.id=l.full_reconcile_id\
            WHERE l.account_id IN %s ''' + filters  + ''' ORDER BY ''' + sql_sort)
        params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql, params)

        dates=[]
        rows=[]
        for row in cr.dictfetchall():
            balance = 0
            if row.get('currency_id', False):
                row['amount_currency_precision'] = self.env['res.currency'].browse(int(row['currency_id'])).decimal_places
            dates.append(row['ldate'])
            rows.append(row)

          
        dates=list(set(dates))      
        new_move_lines = dict(map(lambda x: (x, []), dates))
        for line in rows:
            new_move_lines[line['ldate']].append(line)

        # Calculate the debit, credit and balance for Accounts
        date_res = []
        digits = str(self.env.user.company_id.currency_id.decimal_places)

        for ldate in dates:
            res = dict((fn, 0.0) for fn in ['credit', 'debit'])
            res['date'] = ldate
            res['move_lines'] = new_move_lines[ldate]
            for line in res.get('move_lines'):
                account=self.env['account.account'].browse(line['account_id'])
                currency = account.currency_id and account.currency_id or account.company_id.currency_id
                line['account_code']=account.code
                line['account_name']=account.name
                res['debit'] += line['debit']
                res['credit'] += line['credit']
                res['precision'] = digits
                res['currency_symbol'] = currency.symbol # base currency symbol
                res['currency_position'] = currency.position # base currency position
            if 'display_account'=='all':
                date_res.append(res)
            elif account.id in accounts.ids:
                date_res.append(res)
                
        return date_res

    @api.model
    def render_html_daily(self, docids, act_type='show'):
        context = dict(self.env.context or {})
        init_balance = docids.get('initial_balance', False)
        target_moves = 'all_posted'
        if docids.get('all_posted'):
            target_moves = 'posted'
        if docids.get('all_entries'):
            target_moves = 'all'


        sort_by = 'sort_date'
        display_account = 'all'


        codes = []
        if docids.get('journal_ids', False):
            codes = [journal.code for journal in self.env['account.journal'].search([('id', 'in', docids['journal_ids'])])]
        accounts = self.env['account.account'].search([])
        local_ctx = {
            'state':target_moves or False,
            'journal_ids':docids.get('journal_ids',[]),
            'company_ids': docids.get('company_ids', []),
            'initial_bal': docids.get('initial_balance', False),
            'strict_range':True, # Always expect date from and date_to
            'all_accounts': True,
            'display_account':display_account,
            'sort_by':sort_by
        }

        # If accounts selected
        if docids.get('account_ids', []):
            accounts = self.env['account.account'].browse(docids.get('account_ids')) or []
            local_ctx['all_accounts'] = False
        local_ctx['account_ids'] = accounts
        local_ctx['account_ids_list'] = accounts.mapped('id')
        if not local_ctx['all_accounts']:
            local_ctx['account_name'] = accounts.mapped('name')

        # If accounts tag selected
        account_tags = []
        if docids.get('account_tag_ids', []):
            account_tags = self.env['account.account.tag'].browse(docids.get('account_tag_ids')) or []
            local_ctx['acc_tags'] = account_tags.mapped('id')
            local_ctx['account_tag_ids'] = account_tags
            local_ctx['acc_tags_name'] = account_tags.mapped('name')

        # If partners selected
        if docids.get('partner_ids', []):
            partners = self.env['res.partner'].browse(docids.get('partner_ids')) or []
            local_ctx['partner_ids_list'] = partners.mapped('id')
            local_ctx['partner_ids'] = partners
            local_ctx['partner_name'] = partners.mapped('name')

        # If analytic account selected
        analytic_account = []
        if docids.get('analytic_account_ids', []):
            analytic_account = self.env['account.analytic.account'].browse(docids.get('analytic_account_ids')) or []
            local_ctx['analytic_acc_ids'] = analytic_account.mapped('id')
            local_ctx['analytic_account_ids'] = analytic_account
            local_ctx['analytic_acc_name'] = analytic_account.mapped('name')

        date_from, date_to = False, False
        if docids.get('date_filter'):
            date_from, date_to = self.get_date_from_filter(docids.get('date_filter')[0])
            local_ctx['date_from'] = date_from
            local_ctx['date_to'] = date_to
        
        else:
            local_ctx['date_from'] = docids.get('date_from', False)
            local_ctx['date_to'] = docids.get('date_to', False)

        if act_type == 'show':
            move_lines = self.with_context(local_ctx)._get_account_move_entry(accounts, init_balance, sort_by, display_account)

            if local_ctx.get('account_ids_list'):
                local_ctx['account_ids'] = local_ctx['account_ids_list']
            if local_ctx.get('acc_tags'):
                local_ctx['account_tag_ids'] = local_ctx['acc_tags']
            if local_ctx.get('analytic_acc_ids'):
                local_ctx['analytic_account_ids'] = local_ctx['analytic_acc_ids']
            if local_ctx.get('partner_ids_list'):
                local_ctx['partner_ids'] = local_ctx['partner_ids_list']


            docs = self.env.context
            docargs = {
                'doc_ids': docids,
                'time': datetime.now().strftime("%Y-%m-%d"),
                'Accounts': move_lines,
                'print_journal': codes,
                'local_ctx':local_ctx
            }

            # Prepare JSON
            return json.dumps(docargs)

        if act_type == 'pdf':
            # Prepare pdf
            local_ctx['account_ids'] = False
            local_ctx['account_tag_ids'] = False
            local_ctx['analytic_account_ids'] = False
            local_ctx['partner_ids'] = False

            result = {'model': 'ir.ui.menu',
                 'ids': [],
                 'form': {
                            'initial_balance': local_ctx['initial_bal'] or False,
                            'display_account': display_account,
                            'date_from': local_ctx['date_from'] or False,
                            'journal_ids': local_ctx.get('journal_ids',[]),
                            'used_context': local_ctx,
                            'sortby': sort_by,
                            'date_to': local_ctx['date_to'] or False,
                            'target_move': target_moves
                          }}
            if local_ctx['initial_bal']:
                result['form']['used_context'].update({'date_to':False})
                result['form']['used_context'].update({'initial_bal': False})
            return result

        if act_type == 'xlsx':
            move_lines = self.with_context(local_ctx)._get_account_move_entry(accounts, init_balance, sort_by,
                                                                              display_account)

            if local_ctx.get('account_ids_list'):
                local_ctx['account_ids'] = local_ctx['account_ids_list']
            if local_ctx.get('acc_tags'):
                local_ctx['account_tag_ids'] = local_ctx['acc_tags']
            if local_ctx.get('analytic_acc_ids'):
                local_ctx['analytic_account_ids'] = local_ctx['analytic_acc_ids']
            if local_ctx.get('partner_ids_list'):
                local_ctx['partner_ids'] = local_ctx['partner_ids_list']


            docargs = {
                'doc_ids': docids,
                'time': datetime.now().strftime("%Y-%m-%d"),
                'Accounts': move_lines,
                'print_journal': codes,
                'form':{'initial_balance': local_ctx['initial_bal'] or False,
                          'display_account': display_account,
                          'date_from': local_ctx['date_from'] or False,
                          'journal_ids': local_ctx.get('journal_ids',[]),
                          'partner_ids': local_ctx.get('partner_ids', []),
                          'sortby': sort_by,
                          'date_to': local_ctx['date_to'] or False,
                          'target_move': target_moves,
                          'all_accounts': local_ctx['all_accounts'],
                          'account_ids': local_ctx.get('account_ids',[]),
                          'account_tag_ids': local_ctx.get('acc_tags',[]),
                          'analytic_account_ids': local_ctx.get('analytic_acc_ids',[])
                          }
            }
            return docargs

class AccountMoveLine(models.AbstractModel):
    _inherit = 'account.move.line'

    @api.model
    def _query_get(self, domain=None):
        if domain is None:
            domain = []
        if self._context.get('account_ids_list', False):
            domain += [('account_id', 'in', self._context['account_ids_list'])]
        if self._context.get('acc_tags', False):
            domain += [('account_id.tag_ids', 'in', self._context['acc_tags'])]
        if self._context.get('analytic_acc_ids', False):
            domain += [('analytic_account_id', 'in', self._context['analytic_acc_ids'])]
        if self._context.get('partner_ids_list', False):
            domain += [('partner_id', 'in', self._context['partner_ids_list'])]
        return super(AccountMoveLine, self)._query_get(domain)