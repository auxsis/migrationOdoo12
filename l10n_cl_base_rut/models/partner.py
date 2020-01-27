# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from odoo.osv.expression import get_unaccent_wrapper
from itertools import cycle
import re


class res_partner(models.Model):
    _inherit = 'res.partner'

    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            self.check_access_rights('read')
            where_query = self._where_calc(args)
            self._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            from_str = from_clause if from_clause else 'res_partner'
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            unaccent = get_unaccent_wrapper(self.env.cr)

            query = """SELECT res_partner.id
                         FROM {from_str}
                      {where} ({email} {operator} {percent}
                           OR {display_name} {operator} {percent}
                           OR {reference} {operator} {percent}
                           OR {vat} {operator} {percent})
                           -- don't panic, trust postgres bitmap
                     ORDER BY {display_name} {operator} {percent} desc,
                              {display_name}
                    """.format(from_str=from_str,
                               where=where_str,
                               operator=operator,
                               email=unaccent('res_partner.email'),
                               display_name=unaccent('res_partner.display_name'),
                               reference=unaccent('res_partner.ref'),
                               percent=unaccent('%s'),
                               vat=unaccent('res_partner.vat'),)

            where_clause_params += [search_name]*5
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            self.env.cr.execute(query, where_clause_params)
            partner_ids = [row[0] for row in self.env.cr.fetchall()]

            if partner_ids:
                return self.browse(partner_ids).name_get()
            else:
                return []
        return super(res_partner, self).name_search(name, args, operator=operator, limit=limit)    
    
    
    
        
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.parent_id and not record.is_company:
                name = "%s, %s" % (record.parent_name, name)
            if self.env.context.get('show_address_only'):
                name = self._display_address(without_company=True)
            if self.env.context.get('show_address'):
                name = name + "\n" + self._display_address(without_company=True)
                
            name= "["+(record.vat or "")+"] " +name +"\n"
            
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if self.env.context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res    
    
    
    @api.one
    @api.depends('name', 'vat','parent_id')
    def _compute_display_name(self):
        names = [self.parent_id.name, self.name]
        self.display_name = "["+(self.vat or "")+"] " + ' / '.join(filter(None, names))  
      
    
     
    document_number = fields.Char(
        translate=True, 
        help='Show VAT in custom formatted way',
        string='Document Number')
    formated_vat = fields.Char(
        translate=True, string='Printable VAT',
        help='Show formatted vat')
    vat = fields.Char(
        string='VAT',
        compute='_compute_vat', inverse='_inverse_vat',
        store=True, compute_sudo=False)

    display_name = fields.Char(compute='_compute_display_name', store=True)      
        

     
        
    def digito_verificador(self, rut): 

        if rut:
            rut, vdig = rut[:-1], rut[-1]

            reversed_digits = map(int, reversed(str(rut)))
            factors = cycle(range(2, 8))
            s = sum(d * f for d, f in zip(reversed_digits, factors))
            dv = (-s) % 11
            if dv == 10:
                dv = 'K'
            if str(dv) == str(vdig):
                return True
            else:
                return False
        else:
            return True


    def check_vat_cl (self, vat):
   
        for rec in self:
            format_check=False
            
            #clean id using regex
            regex = re.compile('[^a-zA-Z0-9]')
            format_rut=regex.sub('',rec.vat[2:] or '').upper()
            format_check=rec.digito_verificador(format_rut)        
                
            if not format_check:    
                raise exceptions.Warning(('''Por favor, revisa RUT. Digito verificador no es correcto!''')) 

        return True
     
        
        
    # def check_vat_cl_OLD(self, vat):
        # body, vdig = '', ''
        # if len(vat) > 9:
            # vat = vat.replace('-', '', 1).replace('.', '', 2)
        # if len(vat) != 9:
            # return False
        # else:
            # body, vdig = vat[:-1], vat[-1].upper()
        # try:
            # vali = range(2, 8) + [2, 3]
            # operar = '0123456789K0'[11 - (
                # sum([int(digit)*factor for digit, factor in zip(
                    # body[::-1], vali)]) % 11)]
            # if operar == vdig:
                # return True
            # else:
                # return False
        # except IndexError:
            # return False

    @staticmethod
    def format_document_number(vat):
        clean_vat = (
            re.sub('[^1234567890Kk]', '',
                   str(vat))).zfill(9).upper()
        return '%s.%s.%s-%s' % (
            clean_vat[0:2], clean_vat[2:5], clean_vat[5:8], clean_vat[-1])

    @api.onchange('document_number')
    def onchange_document(self):
        self.document_number = self.format_document_number(
            self.document_number)

    @api.depends('document_number')
    def _compute_vat(self):
        for x in self:
            clean_vat = (
                re.sub('[^1234567890Kk]', '',
                       str(x.document_number))).zfill(9).upper()
            x.vat = 'CL%s' % clean_vat
            x.name_get()

    def _inverse_vat(self):
        self.document_number = self.format_document_number(self.vat)
