# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportDailyLedger(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_dailyledger'

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
            m.name AS move_name, l.move_id AS move_id, c.symbol AS currency_code,c.position AS amount_currency_position, p.display_name AS partner_name,l.reconciled AS reconciled\
            FROM account_move_line l\
            JOIN account_move m ON (l.move_id=m.id)\
            JOIN account_journal j ON (l.journal_id=j.id)\
            JOIN account_account acc ON (l.account_id = acc.id)\
            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
            LEFT JOIN account_sector asec ON (l.sector_id=asec.id)\
            LEFT JOIN account_cost_center acen ON (l.cost_center_id=acen.id)\
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
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids', []))

        init_balance = data['form'].get('initial_balance', True)
        sortby = data['form'].get('sortby', 'sort_date')
        display_account = 'all'
        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in self.env['account.journal'].search([('id', 'in', data['form']['journal_ids'])])]

        accounts = docs if self.model == 'account.account' else self.env['account.account'].search([])
        accounts_res = self.with_context(data['form'].get('used_context',{}))._get_account_move_entry(accounts, init_balance, sortby, display_account)
        return {
            'doc_ids': docids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': accounts_res,
            'print_journal': codes,
        }
