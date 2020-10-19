# -*- coding: utf-8 -*-
from odoo import http

# class ApiuxHr(http.Controller):
#     @http.route('/apiux_hr/apiux_hr/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apiux_hr/apiux_hr/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('apiux_hr.listing', {
#             'root': '/apiux_hr/apiux_hr',
#             'objects': http.request.env['apiux_hr.apiux_hr'].search([]),
#         })

#     @http.route('/apiux_hr/apiux_hr/objects/<model("apiux_hr.apiux_hr"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apiux_hr.object', {
#             'object': obj
#         })