# -*- coding: utf-8 -*-
from odoo import http

# class ApiuxQueue(http.Controller):
#     @http.route('/apiux_queue/apiux_queue/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apiux_queue/apiux_queue/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('apiux_queue.listing', {
#             'root': '/apiux_queue/apiux_queue',
#             'objects': http.request.env['apiux_queue.apiux_queue'].search([]),
#         })

#     @http.route('/apiux_queue/apiux_queue/objects/<model("apiux_queue.apiux_queue"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apiux_queue.object', {
#             'object': obj
#         })