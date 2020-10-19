# -*- coding: utf-8 -*-
from odoo import http

# class ApiuxProject(http.Controller):
#     @http.route('/apiux_project/apiux_project/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apiux_project/apiux_project/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('apiux_project.listing', {
#             'root': '/apiux_project/apiux_project',
#             'objects': http.request.env['apiux_project.apiux_project'].search([]),
#         })

#     @http.route('/apiux_project/apiux_project/objects/<model("apiux_project.apiux_project"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apiux_project.object', {
#             'object': obj
#         })