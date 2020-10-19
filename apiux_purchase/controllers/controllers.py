# -*- coding: utf-8 -*-
from odoo import http

# class ApiuxPurchase(http.Controller):
#     @http.route('/apiux_purchase/apiux_purchase/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apiux_purchase/apiux_purchase/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('apiux_purchase.listing', {
#             'root': '/apiux_purchase/apiux_purchase',
#             'objects': http.request.env['apiux_purchase.apiux_purchase'].search([]),
#         })

#     @http.route('/apiux_purchase/apiux_purchase/objects/<model("apiux_purchase.apiux_purchase"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apiux_purchase.object', {
#             'object': obj
#         })