# -*- coding: utf-8 -*-
import os
import sys  
import base64
import logging
import xlsxwriter
from datetime import datetime
from odoo import api, fields, models, _, exceptions
from operator import itemgetter


_patch =  os.path.dirname(os.path.realpath(__file__))
_logger = logging.getLogger(__name__)

class Doc(object):
    pass

class libro_venta(models.TransientModel):

    _name = 'tmp.repo.libro_venta'
    
        
    @api.depends('name')
    def get_file(self):
        result = None
        for record_browse in self:
            record_browse.name = "Libro_Ventas.xlsx"
            with open(_patch + "/reports/Libro_Ventas.xlsx", 'rb') as f:
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



    def xls_header(self, row, worksheet,format):
        worksheet.write(row, 0, _("Document Date"),format)
        worksheet.write(row, 1, _("Document Number"),format)
        worksheet.write(row, 2, _("Document Anulled"),format)
        worksheet.write(row, 3, _("Contributor ID"),format)
        worksheet.write(row, 4, _("Supplier Name"),format)
        worksheet.write(row, 5, _("Centro De Costo"),format)
        worksheet.write(row, 6, _("Sector"),format)        
        worksheet.write(row, 7, _("Exent Value"),format)
        worksheet.write(row, 8, _("Afect Value"),format)
        worksheet.write(row, 9, _("VAT"),format)
        worksheet.write(row, 10, _("Other Taxes"),format)
        worksheet.write(row, 11, _("Total"),format)
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



    def set_partner_info(self, user, row, worksheet, format, date_start, date_stop):
        worksheet.write(row, 0, _("Company Name"),format)
        worksheet.write(row, 1, user.company_id.name)
        row += 1
        worksheet.write(row, 0, _("Address"), format)
        worksheet.write(row, 1, str(user.company_id.street) or '')
        row += 1
        worksheet.write(row, 0, _("Contributor ID"),format)
        worksheet.write(row, 1, user.company_id.vat[2:-1]+'-'+user.company_id.vat[-1:] or '')
        row += 1
        worksheet.write(row, 0, _("Industry"),format)
        
        actividades = ""
        for act in user.company_id.partner_activities_ids:
            if actividades == "":
                actividades = act.name
            else:
                actividades = actividades + " , " + act.name

        worksheet.write(row, 1, actividades)
        row += 1
        worksheet.write(row, 0, _("Period"), format)
        worksheet.write(row, 1, datetime.strftime(date_start,'%d/%m/%Y') + " al " + datetime.strftime(date_stop,'%d/%m/%Y'))
        row += 1
        return row, worksheet



    def genera_xls(self, this, user):
        sale_docs_sii=[30,32,33,34,35,38,41,55,56,60,61]
        #restringir factura exenta de venta a documento 32
        #exenta_docs_sii=[32,34]
        exenta_docs_sii=[32]
        
        data = this.env['account.invoice'].search([('period_id.id', '=', False),('date_invoice', '>=', this.date_start),('date_invoice', '<=', this.date_stop), ('state', 'not in', ('draft','cancelled')),('company_id', '=', this.company_id.id), ('journal_id.type', 'in', ('sale','sale_refund')),('journal_document_class_id.sii_document_class_id.sii_code', 'in', sale_docs_sii) ])    
        data += this.env['account.invoice'].search([('period_id.date_start', '>=', this.date_start),('period_id.date_stop', '<=', this.date_stop), ('state', 'not in', ('draft','cancelled')),('company_id', '=', this.company_id.id), ('journal_id.type', 'in', ('sale','sale_refund')),('journal_document_class_id.sii_document_class_id.sii_code', 'in', sale_docs_sii) ])    
        data=list(set(data))
        data = sorted(data, key=itemgetter('date_invoice')) 
        workbook = xlsxwriter.Workbook(_patch + "/reports/Libro_Ventas.xlsx")
        
        
        #add some background formats
        #Title
        
        format_title= workbook.add_format({'bold':True,'bg_color':'#CCFFFF','border':7})
        format_header= workbook.add_format({'bold':True,'bg_color':'#FFFFCC','border':7})
        format_section= workbook.add_format({'bold':True})
        
        worksheet = workbook.add_worksheet()
        row = 0
        row, worksheet = self.set_partner_info(user, row, worksheet,format_title, this.date_start, this.date_stop)
        worksheet.set_column('A:A', 20)
        docs_type = self.group_doc_type(data)    
        resumen = []
        for d in docs_type:
            doc = Doc()
            doc.name = str(d.sii_code) + " " + str(d.name)
            doc.count = 0
            doc.nulas = 0
            doc.valor_exento = 0
            doc.valor_afecto = 0            
            doc.excentos = 0
            doc.sujeto_impuesto = 0
            doc.iva = 0
            doc.otro_impuesto = 0
            doc.total = 0


            row += 1
            worksheet.write(row, 0, _("Document Type : ") + str(d.sii_code) + " " + d.name,format_section)
            row += 1
            worksheet = self.xls_header(row, worksheet,format_header)
            row += 1
            for o in data:
                #initialize
                currency=None
                amount_untaxed=0
                amount_tax=0             
                #set up invoice currency. If company currency does not equal invoice currency then convert and round
                if o.currency_id.id != this.company_id.currency_id.id:
                    currency=this.company_id.currency_id
                    if o.currency_rate>0:
                        amount_untaxed=currency.round(o.amount_untaxed*o.currency_rate)
                        amount_tax=currency.round(o.amount_tax*o.currency_rate)
                else:
                    amount_untaxed=o.amount_untaxed
                    amount_tax=o.amount_tax          
            
            
                if o.journal_document_class_id.sii_document_class_id.id == d.id:
                    doc.count += 1
                    
                    worksheet.write(row, 0, datetime.strftime(o.date_invoice,'%d/%m/%Y'))
                    worksheet.write(row, 1, o.sii_document_number)

                    if o.state == "cancel":
                        doc.nulas += 1
                        worksheet.write(row, 2, "X")
                    else:
                        worksheet.write(row, 2, "")

                    worksheet.write(row, 3, o.commercial_partner_id.vat and (o.commercial_partner_id.vat[2:-1]+'-'+o.commercial_partner_id.vat[-1:]) or '')
                    worksheet.write(row, 4, o.commercial_partner_id.name)

                    
                    worksheet.write(row, 5, o.cost_center_id and o.cost_center_id.name or "")
                    worksheet.write(row, 6, o.sector_id and o.sector_id.name or "")  

                    #format correctly for exenta y no exenta
                    if o.journal_document_class_id.sii_document_class_id.sii_code in exenta_docs_sii:
                        doc.excentos += 1
                        worksheet.write(row, 7, amount_untaxed)
                        worksheet.write(row, 8, "")
                        worksheet.write(row, 9, "")
                        doc.total = doc.total + amount_untaxed;
                        doc.valor_exento=doc.valor_exento+amount_untaxed                        
                        worksheet.write(row, 10, 0)
                        worksheet.write(row, 11, amount_untaxed)   
                    else:
                        amount_exenta=sum([x.price_subtotal for x in o.invoice_line_ids if not x.invoice_line_tax_ids])
                        amount_untaxed=sum([x.price_subtotal for x in o.invoice_line_ids if x.invoice_line_tax_ids])

                    
                        doc.sujeto_impuesto += 1
                        worksheet.write(row, 7, amount_exenta)
                        worksheet.write(row, 8, amount_untaxed)
                        worksheet.write(row, 9, amount_tax)                    
                        doc.iva = doc.iva + amount_tax
                        doc.total = doc.total + (amount_untaxed+amount_tax+amount_exenta)
                        doc.valor_afecto=doc.valor_afecto+amount_untaxed                            
                        doc.valor_exento=doc.valor_exento+amount_exenta                       
                        worksheet.write(row, 10, 0)
                        worksheet.write(row, 11, amount_untaxed+amount_tax+amount_exenta)    

                

                    if o.state == "cancel":
                        worksheet.write(row, 8, 0)
                        worksheet.write(row, 9, 0)
                        worksheet.write(row, 10, 0)
                        worksheet.write(row, 11, 0)    

                    row += 1

            row += 2

            resumen.append(doc)

        worksheet.write(row, 0, _("Document Type"),format_header)
        worksheet.write(row, 1, _("Count"),format_header)
        worksheet.write(row, 2, _("Document Anulled"),format_header)
        worksheet.write(row, 3, _("Exent"),format_header)
        worksheet.write(row, 4, _("Subject to Taxes"),format_header)
        worksheet.write(row, 5, _("Centro de Costo"),format_header)
        worksheet.write(row, 6, _("Sector"),format_header)            
        worksheet.write(row, 7, _("Exent Value"),format_header)
        worksheet.write(row, 8, _("Afect Value"),format_header)        
        worksheet.write(row, 9, _("VAT"),format_header)
        worksheet.write(row, 10, _("Other Taxes"),format_header)
        worksheet.write(row, 11, _("Total"),format_header)

        for rs in resumen:
            row += 1
            worksheet.write(row, 0, rs.name,format_section)
            worksheet.write(row, 1, rs.count,format_section)
            worksheet.write(row, 2, rs.nulas,format_section)
            worksheet.write(row, 3, rs.excentos,format_section)
            worksheet.write(row, 4, rs.sujeto_impuesto,format_section)
            worksheet.write(row, 7, rs.valor_exento,format_section)
            worksheet.write(row, 8, rs.valor_afecto,format_section)            
            worksheet.write(row, 9, rs.iva,format_section)
            worksheet.write(row, 10, rs.otro_impuesto,format_section)
            worksheet.write(row, 11, rs.total,format_section)
            

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
                'res_model': this._name,
                'res_id': this.id,
                'view_mode': 'form',
                'target': 'new',
            }
