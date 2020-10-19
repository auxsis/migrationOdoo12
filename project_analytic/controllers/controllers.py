# -*- coding: utf-8 -*-
from odoo import http

# class ProjectAnalytic(http.Controller):
#     @http.route('/project_analytic/project_analytic/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/project_analytic/project_analytic/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('project_analytic.listing', {
#             'root': '/project_analytic/project_analytic',
#             'objects': http.request.env['project_analytic.project_analytic'].search([]),
#         })

#     @http.route('/project_analytic/project_analytic/objects/<model("project_analytic.project_analytic"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('project_analytic.object', {
#             'object': obj
#         })