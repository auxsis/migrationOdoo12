# -*- coding: utf-8 -*-
from odoo import http

# class ApiuxSync(http.Controller):
#     @http.route('/apiux_sync/apiux_sync/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apiux_sync/apiux_sync/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('apiux_sync.listing', {
#             'root': '/apiux_sync/apiux_sync',
#             'objects': http.request.env['apiux_sync.apiux_sync'].search([]),
#         })

#     @http.route('/apiux_sync/apiux_sync/objects/<model("apiux_sync.apiux_sync"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apiux_sync.object', {
#             'object': obj
#         })