# -*- coding: utf-8 -*-
from odoo import http

# class ApiuxMigration(http.Controller):
#     @http.route('/apiux_migration/apiux_migration/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apiux_migration/apiux_migration/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('apiux_migration.listing', {
#             'root': '/apiux_migration/apiux_migration',
#             'objects': http.request.env['apiux_migration.apiux_migration'].search([]),
#         })

#     @http.route('/apiux_migration/apiux_migration/objects/<model("apiux_migration.apiux_migration"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apiux_migration.object', {
#             'object': obj
#         })