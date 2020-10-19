# -*- coding: utf-8 -*-
from odoo import http

# class ApiuxHrPayroll(http.Controller):
#     @http.route('/apiux_hr_payroll/apiux_hr_payroll/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apiux_hr_payroll/apiux_hr_payroll/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('apiux_hr_payroll.listing', {
#             'root': '/apiux_hr_payroll/apiux_hr_payroll',
#             'objects': http.request.env['apiux_hr_payroll.apiux_hr_payroll'].search([]),
#         })

#     @http.route('/apiux_hr_payroll/apiux_hr_payroll/objects/<model("apiux_hr_payroll.apiux_hr_payroll"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apiux_hr_payroll.object', {
#             'object': obj
#         })