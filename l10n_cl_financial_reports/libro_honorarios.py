# -*- coding: utf-8 -*-
import os
import sys  
import base64
import logging
import xlsxwriter
from datetime import datetime
from odoo import api, fields, models, _, exceptions
from operator import itemgetter
from importlib import reload


_patch =  os.path.dirname(os.path.realpath(__file__))
_logger = logging.getLogger(__name__)

class Doc(object):
    pass

class libro_honorarios(models.TransientModel):

    _name = 'cl.repo.libro_honorario'
    
        
    @api.depends('name')
    def get_file(self):
        result = None
        for record_browse in self:
            record_browse.name = "Libro_Honorarios.xlsx"
            f = open(_patch + "/reports/Libro_Honorarios.xlsx")
            record_browse.file = base64.encodestring(f.read())
            f.close()
        return result        
        

    @api.depends('name')
    def get_file(self):
        result = None
        for record_browse in self:
            record_browse.name = "Libro_Honorarios.xlsx"
            with open(_patch + "/reports/Libro_Honorarios.xlsx", 'rb') as f:
                record_browse.file = base64.encodestring(f.read())
            
            f.close()
        return result 



    company_id=fields.Many2one('res.company', 'Company', required=True, select=True)
    date_start=fields.Date('Start Date',required=True)
    date_stop=fields.Date('Finish Date',required=True)
    file_path=fields.Char('File Location', size=128)
    name=fields.Char('Name', size=128)
    file=fields.Binary(compute='get_file', string="Download Report")
    file_data=fields.Binary(string='File Data')


    def xls_format(self, worksheet):
        worksheet.set_column('A:A', 50)


    def xls_header(self, row, workbook, worksheet,format_head):

        worksheet.write(row, 0, _("Date"), format_head)
        worksheet.write(row, 1, _("ID"),format_head)
        worksheet.write(row, 2, _("Name"),format_head)
        worksheet.write(row, 3, _("Voucher Type"),format_head)
        worksheet.write(row, 4, _("Voucher Number"),format_head)
        worksheet.write(row, 5, _("Centro De Costo"),format_head)
        worksheet.write(row, 6, _("Sector"),format_head)             
        worksheet.write(row, 7, _("Gross Amount"),format_head)
        worksheet.write(row, 8, _("Retention"),format_head)
        worksheet.write(row, 9, _("Net"),format_head)
        worksheet.write(row, 10, _("Commentary"),format_head)
        return worksheet


    def group_doc_type(self, data):
        docs = []
        count = 0
        for d in data:
            existe = False
            if count == 0:
                docs.append(d.journal_document_class_id.sii_document_class_id)
            else:
                for i in docs:
                    if d.journal_document_class_id.sii_document_class_id.id == i.id:
                        existe = True
                if existe == False:
                    docs.append(d.journal_document_class_id.sii_document_class_id)
            count += 1

            docs = sorted(docs, key=lambda item: getattr(item, 'sii_code'))

        return docs



    def set_partner_info(self, user, row, workbook, worksheet, format_head, date_start, date_stop):
        

        worksheet.write(row, 0, _("Company Name"), format_head)
        worksheet.write(row, 1, user.company_id.name)
        row += 1
        worksheet.write(row, 0, _("Address"), format_head)
        worksheet.write(row, 1, user.company_id.street or '')
        row += 1
        worksheet.write(row, 0, _("Contributor ID"), format_head)
        worksheet.write(row, 1, user.company_id.vat[2:-1]+'-'+user.company_id.vat[-1:] or '')
        row += 1
        worksheet.write(row, 0, _("Industry"), format_head)
    
        actividades = ""
        for act in user.company_id.partner_activities_ids:
            if actividades == "":
                actividades = act.name
            else:
                actividades = actividades + " , " + act.name
        
        worksheet.write(row, 1, actividades)
        row += 1
        worksheet.write(row, 0, _("Period"), format_head)
        worksheet.write(row, 1, datetime.strftime(date_start,'%d/%m/%Y') + " al " + datetime.strftime(date_stop,'%d/%m/%Y'))
        row += 1
        return row, worksheet



    def genera_xls(self, this, user):

        row = 0
        workbook = xlsxwriter.Workbook(_patch + "/reports/Libro_Honorarios.xlsx")
        worksheet = workbook.add_worksheet()
        
        format_title= workbook.add_format({'bold':True,'bg_color':'#CCFFFF','border':7})
        format_header= workbook.add_format({'bold':True,'bg_color':'#FFFFCC','border':7})
        format_footer= workbook.add_format({'bold':True,'bg_color':'#FF0000','border':7})        
        format_section= workbook.add_format({'bold':True})        
        
        
        row, worksheet = self.set_partner_info(user, row, workbook, worksheet,format_title, this.date_start, this.date_stop)
        row += 2

        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:I', 15)
            

        boleta_docs_sii=[70,71,72]
        data = this.env['account.invoice'].search([('date_invoice', '>=', this.date_start),('date_invoice', '<=', this.date_stop), ('state', 'not in', ('draft','cancelled')),('company_id', '=', this.company_id.id), ('state', '<>','draft'), ('journal_id.type', '=', 'purchase'), ('journal_document_class_id.sii_document_class_id.sii_code', 'in', boleta_docs_sii),('tax_line_ids','!=',False)])    
        

        num_docs = 0
        monto_bruto = 0
        retencion = 0
        liquido = 0
        
        
        docs_type = self.group_doc_type(data)
        for d in docs_type:
        
            #initialise individual doc totals
            doc = Doc()
            doc.name = str(d.sii_code) + " " + str(d.name)
            doc.num_docs = 0
            doc.monto_bruto = 0
            doc.retencion = 0
            doc.liquido = 0            
     

            row += 2
            worksheet.write(row, 0, _("Document Type : ") + str(d.sii_code) + " " + str(d.name),format_section)
            row += 1
            worksheet = self.xls_header(row, workbook,worksheet,format_header)
            row += 1

            #filter and order complete dataset by doc type (d.sii_code) and document date (date invoice)
            filtered_data=data.filtered(lambda r:r.journal_document_class_id.sii_document_class_id.sii_code==d.sii_code)
            sorted_data=filtered_data.sorted(key=lambda r:r.date_invoice)
        
            for d in sorted_data:

                row += 1
                worksheet.write(row, 0, datetime.strftime(d.date_invoice,'%d/%m/%Y'))
                worksheet.write(row, 1, d.partner_id.document_number or (d.partner_id.vat and d.partner_id.vat[2:]) or "" )
                worksheet.write(row, 2, d.partner_id.name)
                worksheet.write(row, 3, d.origin or '')
                worksheet.write(row, 4, str(d.sii_document_number))
                worksheet.write(row, 5, d.cost_center_id.name or '')
                worksheet.write(row, 6, d.sector_id.name or '')                  
                worksheet.write(row, 8, d.comment or '')
                
                invoice_monto_bruto=0
                invoice_retencion=0
                invoice_liquido=0
                
                for l in d.invoice_line_ids:
                    invoice_monto_bruto+=l.price_subtotal
     
                for t in d.tax_line_ids:
                    invoice_retencion+=abs(t.amount_retencion)
                
                
                invoice_liquido=invoice_monto_bruto-invoice_retencion
     
                worksheet.write(row, 7, invoice_monto_bruto)
                worksheet.write(row, 8, invoice_retencion)
                worksheet.write(row, 9, invoice_liquido) 
                
                
                doc.num_docs += 1
                doc.monto_bruto += invoice_monto_bruto
                doc.retencion +=  invoice_retencion
                doc.liquido += invoice_liquido

            row += 1
            worksheet.write(row, 0, "", format_header)            
            worksheet.write(row, 1, "", format_header)            
            worksheet.write(row, 2, "", format_header)
            worksheet.write(row, 3, "", format_header)
            worksheet.write(row, 4, "", format_header)              
            worksheet.write(row, 5, _("Total"), format_header)
            worksheet.write(row, 6, doc.num_docs, format_header)
            worksheet.write(row, 7, doc.monto_bruto, format_header)
            worksheet.write(row, 8, doc.retencion, format_header)
            worksheet.write(row, 9, doc.liquido, format_header)

            #Totales finales
            num_docs +=doc.num_docs
            monto_bruto += doc.monto_bruto
            retencion = doc.retencion
            liquido = doc.liquido

        row += 2
        worksheet.write(row, 0, "", format_footer)            
        worksheet.write(row, 1, "", format_footer)            
        worksheet.write(row, 2, "", format_footer) 
        worksheet.write(row, 3, "", format_header)
        worksheet.write(row, 4, "", format_header)           
        worksheet.write(row, 5, _("Totales"), format_footer)
        worksheet.write(row, 6, num_docs, format_footer)
        worksheet.write(row, 7, monto_bruto, format_footer)
        worksheet.write(row, 8, retencion, format_footer)
        worksheet.write(row, 9, liquido, format_footer)



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


    def generar_old(self, cr, uid, ids, context=None):
        user = self.pool.get('res.users').browse(cr,uid,uid)
        this = self.browse(cr, uid, ids[0], context=context)    
        self.genera_xls(this, user)
        return {
                'type': 'ir.actions.act_window',
                'name' : 'Libro Honorarios',
                'res_model': this._name,
                'res_id': this.id,
                'view_mode': 'form',
                'target': 'new',
            }