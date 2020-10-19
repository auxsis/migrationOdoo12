# -*- coding: utf-8 -*-
from odoo import http

# class ApiuxTimedoctor(http.Controller):
#     @http.route('/apiux_timedoctor/apiux_timedoctor/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apiux_timedoctor/apiux_timedoctor/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('apiux_timedoctor.listing', {
#             'root': '/apiux_timedoctor/apiux_timedoctor',
#             'objects': http.request.env['apiux_timedoctor.apiux_timedoctor'].search([]),
#         })

#     @http.route('/apiux_timedoctor/apiux_timedoctor/objects/<model("apiux_timedoctor.apiux_timedoctor"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apiux_timedoctor.object', {
#             'object': obj
#         })