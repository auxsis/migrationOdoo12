# -*- coding: utf-8 -*-
import os
import sys  
import base64
import logging
import xlsxwriter
from odoo import api, fields, models, _, exceptions
from datetime import datetime, timedelta
from dateutil import relativedelta
import collections
from copy import deepcopy,copy


_patch =  os.path.dirname(os.path.realpath(__file__))
_logger = logging.getLogger(__name__)

class Doc(object):
    pass

class Reg(object):
    pass

class Agrupador (object):  
    pass


class estado_resultado(models.TransientModel):

    _name = 'cl.repo.estado_resultado'
    

 
    @api.depends('name')
    def get_file(self):
        result = None
        for record_browse in self:
            record_browse.name = "Estado_Resultado.xlsx"
            with open(_patch + "/reports/Estado_Resultado.xlsx", 'rb') as f:
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

    def xls_footer(self, row, worksheet, format,format1, totales,code):
        worksheet.write(row, 0, _('Totales'), format)
        if code=='4':
            worksheet.write(row, 1, _('Perdidas'), format)
        else:
            worksheet.write(row, 1, _('Ganancias'), format)
            
        column=2
        for p in totales:
            worksheet.write(row,column,totales[p], format1)
            column+=1   
        
        
        return worksheet
        
    def xls_summary(self, row, worksheet, format,format1, totales,code):
        worksheet.write(row, 0, _('Totales'), format)
        worksheet.write(row, 1, _('Resultado'), format)
            
        column=2
        for p in totales:
            worksheet.write(row,column,totales[p], format1)
            column+=1   
        
        
        return worksheet        
        
    def xls_header(self, row, worksheet, format,format1, periods):
        worksheet.write(row, 0, _('Account Code'), format)
        worksheet.write(row, 1, _('Name'), format) 
        
        column=2
        for p in periods:
            if periods[p]['pstart'].id==periods[p]['pend'].id:
                worksheet.write(row,column,periods[p]['pstart'].code, format)            
            else:
                worksheet.write(row,column,periods[p]['pstart'].code +"-" + periods[p]['pend'].code, format1)
            column+=1   
        
        
        return worksheet


    def query_report(self, this):
        account = this.env['account.account'].search([('deprecated', '=', False), ('company_id', '=', this.company_id.id),'|',('code','like','5%'),('code','like','4%')], order="code asc") 
        account.filtered(lambda r: int(r.code[:1]) == 4 or int(r.code[:1]) == 5)

        move_periods=[]
        
        fiscal_start=this.env['account.period'].search([('special','!=',True),('date_start','<=',this.date_start),('date_stop','>=',this.date_start),('company_id', '=', this.company_id.id)])
        fiscal_end=this.env['account.period'].search([('special','!=',True),('date_start','<=',this.date_stop),('date_stop','>=',this.date_stop),('company_id', '=', this.company_id.id)])
        fiscal_middle=this.env['account.period'].search([('special','!=',True),('date_start','>',this.date_start),('date_stop','<',this.date_stop),('company_id', '=', this.company_id.id)])

        move_periods=fiscal_start+fiscal_middle+fiscal_end
        move = this.env['account.move.line'].search([('period_id', 'in', tuple(x.id for x in move_periods)),('account_id','in',tuple(x.id for x in account)),('company_id', '=', this.company_id.id) ])
          
          
        lista = []
        periodos=collections.OrderedDict()
        
        #find timeperiods from date_start and date_stop
        begin=fiscal_start.date_start + relativedelta.relativedelta(years=-1)
        end=fiscal_end.date_stop
        deltayear=relativedelta.relativedelta(end,begin)
        
        period_length=len(move_periods)
        period_end=begin+relativedelta.relativedelta(months=period_length,days=-1)

        
        n=0
        if deltayear.years>=1:
            fiscal_periods=this.env['account.period'].search([('special','!=',True),'|',('date_start','=',begin),('date_stop','=',period_end)])
            _logger.info("fiscalperiods=%s,%s,%s",fiscal_periods,begin,period_end)
            periodos[n]={'start':begin,'end':period_end,'pstart':fiscal_periods[n],'pend':fiscal_periods[-1],'saldo':0}
            n+=1
        
        #count periods until end of time


        nstart=periodos[n-1]['end']+relativedelta.relativedelta(days=1)
        nend=nstart+relativedelta.relativedelta(months=1,days=-1)    
        fiscal_periods=this.env['account.period'].search([('company_id', '=', this.company_id.id),('special','!=',True),'|',('date_start','=',datetime.strftime(nstart,"%Y-%m-%d")),('date_stop','=',datetime.strftime(nend,"%Y-%m-%d"))])          

          
        while nend<=end:
            periodos[n]={'start':nstart,'end':nend,'pstart':fiscal_periods[0],'pend':fiscal_periods[-1],'saldo':0}
            
            #add extra period if months are the same

            if nend.month==end.month:
                n=n+1
                beginyear=nend+relativedelta.relativedelta(months=-(period_length-1),day=1)
                _logger.debug("byear=%s",beginyear)
                fiscal_periods=this.env['account.period'].search([('company_id', '=', this.company_id.id),('special','!=',True),'|',('date_start','=',datetime.strftime(beginyear,"%Y-%m-%d")),('date_stop','=',datetime.strftime(nend,"%Y-%m-%d"))])
                periodos[n]={'start':beginyear,'end':nend,'pstart':fiscal_periods[0],'pend':fiscal_periods[-1],'saldo':0} 
                
            n=n+1    
            nstart=periodos[n-1]['end']+relativedelta.relativedelta(days=1)
            nend=nstart+relativedelta.relativedelta(months=1,days=-1)
            fiscal_periods=this.env['account.period'].search([('company_id', '=', this.company_id.id),('special','!=',True),'|',('date_start','=',datetime.strftime(nstart,"%Y-%m-%d")),('date_stop','=',datetime.strftime(nend,"%Y-%m-%d"))])          
                   
        
        for c in account:
        
            r = Reg()
            r.full_code=c.code
            r.periodos=this.mydeepcopy(periodos)
            r.id = c.id
            r.code =  c.code
            r.name = c.name
            
            debit=0
            credit=0
            saldo=0
                        
            for m in move:
                if m.account_id.id == c.id:
                    debit =  m.debit
                    credit = m.credit
                    if r.code=='5':
                        saldo = -(debit - credit)
                    else:
                        saldo = (debit - credit)
                    
                    for key in r.periodos:
                        period=r.periodos[key]
                        if m.period_id.date_start>=period['start'] and m.period_id.date_stop<=period['end']:
                            r.periodos[key]['saldo']+=saldo
   
        
            if this.display_account=='bal_mix' and (saldo!=0):
                lista.append(r)
            if this.display_account=='bal_all':
                lista.append(r)

        return {'data':lista,'periods':periodos}

    def no_negativo(seft, valor):
        if valor < 0:
            valor = valor * -1
        return valor

    def genera_xls(self, this, user):
        row = 0
        workbook = xlsxwriter.Workbook(_patch + "/reports/Estado_Resultado.xlsx")

        #add some background formats
        #Title
        
        format_title= workbook.add_format({'bold':True,'bg_color':'#CCFFFF','border':7})
        format_header= workbook.add_format({'bold':True,'bg_color':'#FFFFCC','border':7})
        format_special=workbook.add_format({'bold':True,'bg_color':'#FF0000','border':7}) 
        format_section= workbook.add_format({'bold':True})
        format_normal=workbook.add_format({'font_size':12})


        worksheet = workbook.add_worksheet()
        row, worksheet = self.set_partner_info(user, row, worksheet, this.date_start, this.date_stop , format_title)
        row += 2
        
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 40)

        worksheet.merge_range('I'+str(row)+':J'+str(row), _('State of Results'), format_header)
        


        result = self.query_report(this)
        data=result['data']
        periods=result['periods']

        worksheet = self.xls_header(row, worksheet, format_header,format_special,periods)
        
        totales_p=collections.OrderedDict()
        totales_g=collections.OrderedDict()
        totales_f=collections.OrderedDict()

        if data:
            actual_code=data[0].code
            for d in data:
        
                if d.code!=actual_code:
                    row+=1
                    worksheet=self.xls_footer(row,worksheet,format_header,format_special,totales_p,actual_code)
                    actual_code=d.code
                    row+=2
        
                row += 1
                format=format_normal

                worksheet.write(row, 0, d.full_code, format)
                worksheet.write(row, 1, d.name, format)            
                
                column_num=2
                for key in d.periodos:
                    period=d.periodos[key]
                    worksheet.write(row, column_num, period['saldo'], format)
                    if d.code=='5':
                        if key in totales_g:
                            totales_g[key]+=period['saldo']
                        else:
                            totales_g[key]=period['saldo']
                    else:
                        if key in totales_p:
                            totales_p[key]+=period['saldo']
                        else:
                            totales_p[key]=period['saldo']                
                        
                    column_num+=1

            #final totals
            row+=1
            worksheet=self.xls_footer(row,worksheet,format_header,format_special,totales_g,actual_code)
            #calculate result
            for key in totales_g:
                totales_f[key]=totales_g[key]-totales_p[key]
            
            row+=2
            worksheet=self.xls_summary(row,worksheet,format_header,format_special,totales_f,actual_code)        
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
                      
            
            
    def mydeepcopy(self,copy_objs):
        
        copied_object=collections.OrderedDict()
        for key in copy_objs:
            copy_obj=copy_objs[key]
            copied_object[key]={'start':copy_obj['start'],'end':copy_obj['end'],'pstart':copy_obj['pstart'],'pend':copy_obj['pend'],'saldo':deepcopy(copy_obj['saldo'])}
    
        return copied_object
    
            
            