# -*- coding: utf-8 -*-
from odoo import http

# class ApiuxHrLeave(http.Controller):
#     @http.route('/apiux_hr_leave/apiux_hr_leave/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apiux_hr_leave/apiux_hr_leave/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('apiux_hr_leave.listing', {
#             'root': '/apiux_hr_leave/apiux_hr_leave',
#             'objects': http.request.env['apiux_hr_leave.apiux_hr_leave'].search([]),
#         })

#     @http.route('/apiux_hr_leave/apiux_hr_leave/objects/<model("apiux_hr_leave.apiux_hr_leave"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apiux_hr_leave.object', {
#             'object': obj
#         })