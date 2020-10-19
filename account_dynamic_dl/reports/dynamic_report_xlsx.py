from odoo import models, fields, api,_

try:
    from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
    from xlsxwriter.utility import xl_rowcol_to_cell
except ImportError:
    ReportXlsx = object

class DailyLedgerXlsx(models.AbstractModel):
    _name = 'report.account_dynamic_dl.daily_ledger_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _define_formats(self, workbook):
        """ Add cell formats to current workbook.
        Available formats:
         * format_title
         * format_header
        """
        self.format_title = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 14,
            'bg_color': '#FFF58C',
            'border': False
        })
        self.format_header = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFFCC',
            'border': True
        })
        self.content_header = workbook.add_format({
            'bold': False,
            'bg_color': '#FFFFFF',
            'border': True
        })
        self.line_header = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFFCC',
            'border': True
        })

    def prepare_report_filters(self,filter):
        self.row_pos += 3
        if filter:
            # Date from
            self.sheet.write_string(self.row_pos, 0, _('Date from'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 1, _('Date to'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 2, _('Target moves'),
                                    self.format_header)
            self.row_pos += 1

            if filter.get('date_from'):
                self.sheet.write_string(self.row_pos, 0, str(filter.get('date_from','')),
                                    self.content_header)
            else:
                self.sheet.write_string(self.row_pos, 0, _('None'),
                                        self.content_header)
            if filter.get('date_to'):
                self.sheet.write_string(self.row_pos, 1, str(filter.get('date_to','')),
                                    self.content_header)
            else:
                self.sheet.write_string(self.row_pos, 1, _('None'),
                                        self.content_header)

            if filter['target_move'] == 'posted':
                self.sheet.write_string(self.row_pos, 2, _('All posted'),
                                        self.content_header)
            elif filter['target_move'] == 'all':
                self.sheet.write_string(self.row_pos, 2, _('All entries'),
                                        self.content_header)

            # Journals

            self.row_pos += 2
            self.sheet.write_string(self.row_pos, 0, _('Journals'),
                                    self.format_header)
            journal_col = 1
            for journal in self.env['account.journal'].browse(filter['journal_ids']):
                self.sheet.write_string(self.row_pos, journal_col, str(journal.code),
                                        self.content_header)
                journal_col += 1

            # Partners
            self.row_pos += 1
            self.sheet.write_string(self.row_pos, 0, _('Partners'),
                                                 self.format_header)
            partner_col = 1
            for partner in self.env['res.partner'].browse(filter['partner_ids']):
                self.sheet.write_string(self.row_pos, partner_col, str(partner.name),
                                                self.content_header)
                partner_col += 1

            # Account tags

            self.row_pos += 1
            self.sheet.write_string(self.row_pos, 0, _('Acc Tags'),
                                    self.format_header)
            acc_tags_col = 1
            for tag in self.env['account.account.tag'].browse(filter['account_tag_ids']):
                self.sheet.write_string(self.row_pos, acc_tags_col, str(tag.name),
                                        self.content_header)
                acc_tags_col += 1

            # Analytic Account

            self.row_pos += 1
            self.sheet.write_string(self.row_pos, 0, _('Analytic Acc'),
                                    self.format_header)
            acc_analytic_col = 1
            for tag in self.env['account.analytic.account'].browse(filter['analytic_account_ids']):
                self.sheet.write_string(self.row_pos, acc_analytic_col, str(tag.name),
                                        self.content_header)
                acc_analytic_col += 1

            # Accounts

            self.row_pos += 1
            self.sheet.write_string(self.row_pos, 0, _('Accounts'),
                                    self.format_header)
            account_col = 1
            if not filter['all_accounts']:
                for accounts in self.env['account.account'].browse(filter['account_ids']):
                    self.sheet.write_string(self.row_pos, account_col, str(accounts.name),
                                            self.content_header)
                    account_col += 1
            else:
                self.sheet.write_string(self.row_pos, account_col, _('All'),
                                        self.content_header)

    def prepare_report_contents(self, Accounts):
        self.row_pos += 3
        if Accounts:
            self.sheet.write_string(self.row_pos, 0, _('Date'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 1, _('Journal'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 2, _('Code'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 3, _('Nombre'),
                                    self.format_header)                                    
            self.sheet.write_string(self.row_pos, 4, _('Partner'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 5, _('Reference'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 6, _('Move'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 7, _('Label'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 8, _('Sector'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 9, _('Cost Center'),
                                    self.format_header)                                    
            self.sheet.write_string(self.row_pos, 10, _('Reconciled'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 11, _('Debit'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 12, _('Credit'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 13, _('Balance'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 14, _('Currency'),
                                    self.format_header)
            for account in Accounts:
                self.row_pos += 1
                self.sheet.write_string(self.row_pos, 0, str(account.get('date')),
                                        self.line_header)
                self.sheet.write_string(self.row_pos, 11, self._format_currency(account['debit'],account['precision']),
                                        self.line_header)
                self.sheet.write_string(self.row_pos, 12, self._format_currency(account['credit'],account['precision']),
                                        self.line_header)
                for lines in account['move_lines']:
                    self.row_pos += 1
                    self.sheet.write_string(self.row_pos, 0, str(lines.get('ldate')),
                                            self.content_header)
                    self.sheet.write_string(self.row_pos, 1, str(lines.get('lcode')),
                                            self.content_header)
                    self.sheet.write_string(self.row_pos, 2, str(lines.get('account_code')),
                                            self.content_header)
                    self.sheet.write_string(self.row_pos, 3, str(lines.get('account_name')),
                                            self.content_header)                                            
                    if lines.get('partner_name', ''):
                        self.sheet.write_string(self.row_pos, 4, str(lines.get('partner_name')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 4, ' ',
                                                self.content_header)
                    if lines.get('lref', ''):
                        self.sheet.write_string(self.row_pos, 5, str(lines.get('lref')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 5, ' ',
                                                self.content_header)
                    if lines.get('move_name', ''):
                        self.sheet.write_string(self.row_pos, 6, str(lines.get('move_name','')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 6, ' ',
                                                self.content_header)
                    if lines.get('lname',''):
                        self.sheet.write_string(self.row_pos, 7, str(lines.get('lname','')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 7, ' ',
                                                self.content_header)
                    if lines.get('lsector',''):
                        self.sheet.write_string(self.row_pos, 8, str(lines.get('lsector','')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 8, ' ',
                                                self.content_header)
                    if lines.get('lcenter',''):
                        self.sheet.write_string(self.row_pos, 9, str(lines.get('lcenter','')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 9, ' ',
                                                self.content_header)                                                
                    if lines.get('reconciled'):
                        self.sheet.write_string(self.row_pos, 10, str(lines.get('reconciled','')),self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 10, ' ',self.content_header)
                    self.sheet.write_string(self.row_pos, 11, self._format_currency(lines['debit'],account['precision']),
                                            self.content_header)
                    self.sheet.write_string(self.row_pos, 12, self._format_currency(lines['credit'],account['precision']),
                                            self.content_header)
                    if lines.get('amount_currency','0.0'):
                        self.sheet.write_string(self.row_pos, 13, self._format_currency(lines.get('amount_currency','0.0'),lines.get('amount_currency_precision',2)),
                                            self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 13," ",self.content_header)
                    self.sheet.write_string(self.row_pos, 14, str(lines.get('currency_code')),
                                            self.content_header)


    def _format_currency(self, amount, precision):
        format_amount = b = '{:.' + str(precision) + 'f}'
        return format_amount.format(amount)

    def generate_xlsx_report(self, workbook, data, partners):
        self._define_formats(workbook)
        self.row_pos = 0
        self.sheet = workbook.add_worksheet('Libro Diario')
        self.sheet.merge_range(0, 0, 0, 5, _('Daily Ledger'), self.format_title
        )
        if data:
            # Filter section
            self.prepare_report_filters(data['form'])
            # Content section
            self.prepare_report_contents(data['Accounts'])