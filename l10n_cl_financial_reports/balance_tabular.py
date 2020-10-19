# -*- coding: utf-8 -*-
import os
import sys  
import base64
import logging
import xlsxwriter
from odoo import api, fields, models, _, exceptions
from datetime import datetime, timedelta


_patch =  os.path.dirname(os.path.realpath(__file__))
_logger = logging.getLogger(__name__)

class Doc(object):
    pass

class Reg(object):
    pass

class Agrupador (object):  
    pass


class balance_tabular(models.TransientModel):

    _name = 'cl.repo.balance_tabular'
    


    @api.depends('name')
    def get_file(self):
        result = None
        for record_browse in self:
            record_browse.name = "Balance_Tabular.xlsx"
            with open(_patch + "/reports/Balance_Tabular.xlsx", 'rb') as f:
                record_browse.file = base64.encodestring(f.read())
            
            f.close()
        return result    


    company_id=fields.Many2one('res.company', 'Company', required=True, select=True)
    display_account=fields.Selection([('bal_all', _('All')),('bal_mix', _('With transactions'))],string='Mostrar cuentas',required=True, default='bal_mix')   
    date_start=fields.Date('Start Date',required=True)
    date_stop=fields.Date('Finish Date',required=True)
    file_path=fields.Char('File Location', size=128)
    name=fields.Char('Name', size=128)
    file=fields.Binary(compute='get_file', string="Download Report")
    file_data=fields.Binary(string='File Data')

    def xls_format(self, worksheet):
        worksheet.set_column('A:A', 50)


    def set_partner_info(self, user, row, worksheet, date_start, date_stop, format):
        worksheet.write(row, 0, _('Company Name'), format)
        worksheet.write(row, 1, user.company_id.name)
        row += 1
        worksheet.write(row, 0, _('Domicilio'), format)
        worksheet.write(row, 1, str(user.company_id.street) or '')
        row += 1
        worksheet.write(row, 0, _('Contributor ID'), format)
        worksheet.write(row, 1, user.company_id.vat[2:-1]+'-'+user.company_id.vat[-1:] or '')
        row += 1
        worksheet.write(row, 0, _('Industry'), format)
        actividades = ""
        for act in user.company_id.partner_activities_ids:
            if actividades == "":
                actividades = act.name
            else:
                actividades = actividades + " , " + act.name
        worksheet.write(row, 1, actividades)
        row += 1
        worksheet.write(row, 0, _('Period'), format)
        worksheet.write(row, 1, datetime.strftime(date_start,'%d/%m/%Y') + " al " + datetime.strftime(date_stop,'%d/%m/%Y'))
        row += 1
        return row, worksheet


    def xls_header(self, row, worksheet, format):
        worksheet.write(row, 0, _('Account Code'), format)
        worksheet.write(row, 1, _('Name'), format)
        worksheet.write(row, 2, _('Debit'), format)
        worksheet.write(row, 3, _('Credit'), format)
        worksheet.write(row, 4, _('Debtor'), format)
        worksheet.write(row, 5, _('Creditor'), format)
        worksheet.write(row, 6, _('Active'), format)
        worksheet.write(row, 7, _('Passive'), format)
        worksheet.write(row, 8, _('Loss'), format)
        worksheet.write(row, 9, _('Profit'), format)
        return worksheet


    def query_report(self, this):
        account = this.env['account.account'].sudo().search([('deprecated', '=', False), ('company_id', '=', this.company_id.id) ], order="code asc")      
        move = this.env['account.move.line'].sudo().search([('period_id.date_start', '>=', this.date_start),('period_id.date_stop', '<=', this.date_stop), ('company_id', '=', this.company_id.id) ])
        _logger.info("account=%s,%s",account,move)
        account=account.sorted(key=lambda r: r.code[:1] or '0')   
        move=move.sorted(key=lambda r: r.account_id.code[:1] or '0')        
        lista = []
        for c in account:
            
            tipo_cuenta = c.code[:1]
            
            debit = 0
            credit = 0
            saldo = 0
            for m in move:
                if m.account_id.id == c.id:
                    _logger.info("ids2=%s,%s",m.account_id.id,c.id)
                    debit = debit + m.debit
                    credit = credit + m.credit
                    saldo = saldo + (debit - credit)
            
            r = Reg()
            r.id = c.id
            r.code = c.code
            r.name = c.name
            #r.level = c.level
            r.level=4

            r.debit = debit
            r.credit = credit

            
            r.deudor = 0
            r.acreedor = 0
            r.activo = 0
            r.pasivo = 0
            r.perdida = 0
            r.ganancia = 0

            saldo = debit - credit
            
            if tipo_cuenta == "1":
                if saldo > 0:
                    r.deudor = abs(saldo)
                    r.activo = abs(saldo)                        
                else:
                    r.acreedor = abs(saldo)            
                    r.pasivo = abs(saldo)
                    
            if tipo_cuenta == "2":
                if saldo >0:
                    r.deudor = abs(saldo)
                    r.activo = abs(saldo)
                else:
                    r.acreedor = abs(saldo)
                    r.pasivo = abs(saldo)                
            
            
            if tipo_cuenta == "3":
                if saldo >0:
                    r.deudor = abs(saldo)
                    r.activo = abs(saldo)
                else:
                    r.acreedor = abs(saldo)
                    r.pasivo = abs(saldo)    

            if tipo_cuenta == "4":
                if saldo >0:
                    r.deudor = abs(saldo)
                    r.perdida = abs(saldo)                 
                else:    
                    r.acreedor = abs(saldo)
                    r.ganancia = abs(saldo)
                    
            if tipo_cuenta == "5":
                if saldo >0:
                    r.deudor = abs(saldo)
                    r.perdida = abs(saldo)
                else:
                    r.acreedor = abs(saldo)
                    r.ganancia = abs(saldo)
 


            #r.parent = c.parent_id.id
            
            if this.display_account=='bal_mix' and (saldo!=0 or debit!=0 or credit!=0):
                lista.append(r)
            if this.display_account=='bal_all':
                lista.append(r)



        return lista

    def no_negativo(seft, valor):
        if valor < 0:
            valor = valor * -1
        return valor

    def genera_xls(self, this, user):
        row = 0
        workbook = xlsxwriter.Workbook(_patch + "/reports/Balance_Tabular.xlsx")

        #add some background formats
        #Title
        
        format_title= workbook.add_format({'bold':True,'bg_color':'#CCFFFF','border':7})
        format_header= workbook.add_format({'bold':True,'bg_color':'#FFFFCC','border':7})
        format_section= workbook.add_format({'bold':True})
        format_normal=workbook.add_format({'font_size':12})


        worksheet = workbook.add_worksheet()
        row, worksheet = self.set_partner_info(user, row, worksheet, this.date_start, this.date_stop , format_title)
        row += 2
        
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 40)

        worksheet.merge_range('E'+str(row)+':F'+str(row), _('Balances'), format_header)
        worksheet.merge_range('G'+str(row)+':H'+str(row), _('General Balance'), format_header)
        worksheet.merge_range('I'+str(row)+':J'+str(row), _('State of Results'), format_header)
        
        worksheet = self.xls_header(row, worksheet, format_header)

        data = self.query_report(this)
        
        t_debit = 0
        t_credit = 0
        t_deudor = 0
        t_acreedor = 0
        t_activo = 0
        t_pasivo = 0
        t_perdida = 0
        t_ganancia = 0
        _logger.info("data=%s",data)
        for d in data:
    
            row += 1
            if d.level == 1 or d.level==2:
                format = format_section
            else:
                format=format_normal

            worksheet.write(row, 0, d.code, format)
            worksheet.write(row, 1, d.name, format)
            worksheet.write(row, 2, d.debit, format)
            worksheet.write(row, 3, d.credit, format)

            worksheet.write(row, 4, d.deudor, format)
            worksheet.write(row, 5, d.acreedor, format)
            worksheet.write(row, 6, d.activo, format)
            worksheet.write(row, 7, d.pasivo, format)
            worksheet.write(row, 8, d.perdida, format)
            worksheet.write(row, 9, d.ganancia, format)



            t_debit += d.debit
            t_credit += d.credit
            t_deudor += d.deudor
            t_acreedor += d.acreedor
            t_activo += d.activo
            t_pasivo += d.pasivo
            t_perdida += d.perdida
            t_ganancia += d.ganancia

        row += 1
        worksheet.write(row, 1, _('Sum'), format_header)
        worksheet.write(row, 2, self.no_negativo(t_debit), format_header)
        worksheet.write(row, 3, self.no_negativo(t_credit), format_header)
        worksheet.write(row, 4, self.no_negativo(t_deudor), format_header)
        worksheet.write(row, 5, self.no_negativo(t_acreedor), format_header)
        worksheet.write(row, 6, self.no_negativo(t_activo), format_header)
        worksheet.write(row, 7, self.no_negativo(t_pasivo), format_header)
        worksheet.write(row, 8, self.no_negativo(t_perdida), format_header)
        worksheet.write(row, 9, self.no_negativo(t_ganancia), format_header)
        
        row += 1

        ut_balace = self.no_negativo(t_activo) - self.no_negativo(t_pasivo)
        ut_resultado = self.no_negativo(t_perdida) - self.no_negativo(t_ganancia)
        
        ut_activo = 0
        ut_pasivo = 0

        ut_perdida = 0
        ut_ganancia = 0

        if ut_balace > 0:
            ut_activo = 0
            ut_pasivo = abs(ut_balace)        
        else:
            ut_activo = abs(ut_balace)
            ut_pasivo = 0

        if ut_resultado > 0:
            ut_perdida = 0
            ut_ganancia = abs(ut_resultado)
        else:
            ut_perdida = abs(ut_resultado)
            ut_ganancia = 0


        worksheet.write(row, 1, _("Sum"), format_section)
        worksheet.write(row, 6, ut_activo, format_section)
        worksheet.write(row, 7, ut_pasivo, format_section)    
        worksheet.write(row, 8, ut_perdida, format_section)
        worksheet.write(row, 9, ut_ganancia, format_section)    

        row += 1
        worksheet.write(row, 1, _("Totals"), format_header)
        worksheet.write(row, 2, self.no_negativo(t_debit), format_header)
        worksheet.write(row, 3, self.no_negativo(t_credit), format_header)
        worksheet.write(row, 4, self.no_negativo(t_deudor), format_header)
        worksheet.write(row, 5, self.no_negativo(t_acreedor), format_header)
        worksheet.write(row, 6, self.no_negativo(t_activo) + self.no_negativo(ut_activo), format_header)
        worksheet.write(row, 7, self.no_negativo(t_pasivo) + self.no_negativo(ut_pasivo), format_header)
        worksheet.write(row, 8, self.no_negativo(t_perdida) + self.no_negativo(ut_perdida), format_header)
        worksheet.write(row, 9, self.no_negativo(t_ganancia) + self.no_negativo(ut_ganancia), format_header)

        workbook.close()



    def generar(self):
    
        user = self.env.user   
        self.genera_xls(self, user)

        
        return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }