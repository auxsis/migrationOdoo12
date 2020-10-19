# -*- coding: utf-8 -*-
from odoo import http

# class ApiuxAnalyticJournal(http.Controller):
#     @http.route('/apiux_analytic_journal/apiux_analytic_journal/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apiux_analytic_journal/apiux_analytic_journal/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('apiux_analytic_journal.listing', {
#             'root': '/apiux_analytic_journal/apiux_analytic_journal',
#             'objects': http.request.env['apiux_analytic_journal.apiux_analytic_journal'].search([]),
#         })

#     @http.route('/apiux_analytic_journal/apiux_analytic_journal/objects/<model("apiux_analytic_journal.apiux_analytic_journal"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apiux_analytic_journal.object', {
#             'object': obj
#         })