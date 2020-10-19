from odoo import models, fields, api,_
import logging

_logger = logging.getLogger(__name__)


try:
    from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx
    from xlsxwriter.utility import xl_rowcol_to_cell
except ImportError:
    ReportXlsx = object

class GeneralLedgerXlsx(models.AbstractModel):
    _name = 'report.account_dynamic_gl.general_ledger_xlsx'
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
        self.content_header_currency = workbook.add_format({
            'bold': False,
            'bg_color': '#FFFFFF',
            'border': True,
            'num_format': '#.###',            
        })        
        self.line_header = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFFCC',
            'border': True
        })


        self.line_header_currency = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFFCC',
            'border': True,
            'num_format': '[$-340A]#.###;[RED][$-340A] -#.###'
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
            self.sheet.write_string(self.row_pos, 3, _('Display accounts'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 4, _('Sort by'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 5, _('Inital balance'),
                                    self.format_header)
            self.row_pos += 1

            if filter.get('date_from'):
                self.sheet.write_string(self.row_pos, 0, str(filter.get('date_from','')),
                                    self.content_header)
            else:
                self.sheet.write_string(self.row_pos, 0, _('Ninguno'),
                                        self.content_header)
            if filter.get('date_to'):
                self.sheet.write_string(self.row_pos, 1, str(filter.get('date_to','')),
                                    self.content_header)
            else:
                self.sheet.write_string(self.row_pos, 1, _('Ninguno'),
                                        self.content_header)

            if filter['target_move'] == 'posted':
                self.sheet.write_string(self.row_pos, 2, _('All posted entries'),
                                        self.content_header)
            elif filter['target_move'] == 'all':
                self.sheet.write_string(self.row_pos, 2, _('All entries'),
                                        self.content_header)

            if filter['display_account'] == 'all':
                self.sheet.write_string(self.row_pos, 3, _('All data'),
                                        self.content_header)
            elif filter['display_account'] == 'movement':
                self.sheet.write_string(self.row_pos, 3, _('All movements'),
                                        self.content_header)
            else:
                self.sheet.write_string(self.row_pos, 3, _('All with balance not zero'),
                                        self.content_header)

            if filter['sortby'] == 'sort_date':
                self.sheet.write_string(self.row_pos, 4, _('By date'),
                                        self.content_header)
            else:
                self.sheet.write_string(self.row_pos, 4, _('By Journal and partner'),
                                        self.content_header)

            if filter['initial_balance']:
                self.sheet.write_string(self.row_pos, 5, _('Yes'),
                                        self.content_header)
            else:
                self.sheet.write_string(self.row_pos, 5, _('No'),
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
                self.sheet.write_string(self.row_pos, partner_col, str(partner.display_name),
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
            self.sheet.write_string(self.row_pos, 2, _('Partner'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 3, _('Reference'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 4, _('Move'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 5, _('Label'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 6, _('Sector'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 7, _('Cost Center'),
                                    self.format_header)                                    
            self.sheet.write_string(self.row_pos, 8, _('Reconciled'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 9, _('Debit'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 10, _('Credit'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 11, _('Balance'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 12, _('Transaction'),
                                    self.format_header)
            self.sheet.write_string(self.row_pos, 13, _('Currency'),
                                    self.format_header)
            for account in Accounts:
                self.row_pos += 1
                self.sheet.write_string(self.row_pos, 0, str(account.get('code')) or '',
                                        self.line_header)
                self.sheet.write_string(self.row_pos, 1, str(account.get('name')),
                                        self.line_header)
                self.sheet.write_number(self.row_pos, 9, account['debit'],self.line_header_currency)
                self.sheet.write_number(self.row_pos, 10, account['credit'],self.line_header_currency)

                for lines in account['move_lines']:
                    self.row_pos += 1
                    self.sheet.write_string(self.row_pos, 0, str(lines.get('ldate')),
                                            self.content_header)
                    self.sheet.write_string(self.row_pos, 1, str(lines.get('lcode')),
                                            self.content_header)
                    if lines.get('partner_name', ''):
                        self.sheet.write_string(self.row_pos, 2, str(lines.get('partner_name')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 2, ' ',
                                                self.content_header)
                    if lines.get('lref', ''):
                        self.sheet.write_string(self.row_pos, 3, str(lines.get('lref')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 3, ' ',
                                                self.content_header)
                    if lines.get('move_name', ''):
                        self.sheet.write_string(self.row_pos, 4, str(lines.get('move_name','')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 4, ' ',
                                                self.content_header)
                    if lines.get('lname',''):
                        self.sheet.write_string(self.row_pos, 5, str(lines.get('lname','')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 5, ' ',
                                                self.content_header)
                    if lines.get('lsector',''):
                        self.sheet.write_string(self.row_pos, 6, str(lines.get('lsector','')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 6, ' ',
                                                self.content_header)
                    if lines.get('lcenter',''):
                        self.sheet.write_string(self.row_pos, 7, str(lines.get('lcenter','')),
                                                self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 7, ' ',
                                                self.content_header)                                                
                    if lines.get('reconciled'):
                        self.sheet.write_string(self.row_pos, 8, str(lines.get('reconciled','')),self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 8, ' ',self.content_header)
                        
                    self.sheet.write_number(self.row_pos, 9, lines['debit'],self.content_header_currency)
                    self.sheet.write_number(self.row_pos, 10, lines['credit'],self.content_header_currency)
                    self.sheet.write_number(self.row_pos, 11, lines['balance'],self.content_header_currency)
                    if lines.get('amount_currency','0.0'):
                        self.sheet.write_string(self.row_pos, 12, self._format_currency(lines.get('amount_currency','0.0'),lines.get('amount_currency_precision',2)),
                                            self.content_header)
                    else:
                        self.sheet.write_string(self.row_pos, 12," ",self.content_header)
                    _logger.info("cc=%s",lines.get('currency_code'))
                    self.sheet.write_string(self.row_pos, 13, str(lines.get('currency_code'))=='None' and 'Ninguna' or lines.get('currency_code'),self.content_header)

                #add footer totals for each account
                self.row_pos += 1
                self.sheet.write_number(self.row_pos, 11, int(account['balance']),self.line_header_currency)

    def _format_currency(self, amount, precision):
        format_amount = b = '{:.' + str(precision) + 'f}'
        return format_amount.format(amount)

    def generate_xlsx_report(self, workbook, data, partners):
        self._define_formats(workbook)
        self.row_pos = 0
        self.sheet = workbook.add_worksheet(_('General Ledger'))
        self.sheet.merge_range(0, 0, 0, 5, _('General Ledger'), self.format_title
        )
        if data:
            # Filter section
            self.prepare_report_filters(data['form'])
            # Content section
            self.prepare_report_contents(data['Accounts'])