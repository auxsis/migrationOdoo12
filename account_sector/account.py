# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 ONESTEiN BV (<http://www.onestein.nl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields,api
import logging
_logger = logging.getLogger(__name__)


class account_move_line(models.Model):
    _inherit = 'account.move.line'



    sector_id = fields.Many2one('account.sector', string='Sector')
    
    
class account_account(models.Model):
    _inherit = 'account.account'
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):

        add_arg=True
        for arg in args:
            if 'invisible' in arg:
                add_arg=False
        # if add_arg:
            # args += [('invisible','=',False)]


        return super(account_account, self).search(args, offset, limit,order, count=count)


    
    
    
    invisible = fields.Boolean(default=False,string='Invisible?')
    move_line_ids=fields.One2many('account.move.line','account_id', string='Account move lines')
    