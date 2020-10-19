from odoo import fields, models, api
import logging
import pytz
import operator
from odoo.addons import decimal_precision as dp
from odoo import exceptions
from isoweek import Week
from odoo import tools
from odoo import SUPERUSER_ID
import time,math
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%d"

class HrProjectionShorten(models.TransientModel):
    _name = 'hr.proj.shorten'
    _description = 'hr.proj.shorten'

    @api.onchange('to_date')
    def _onchange_todate(self):
        if self.to_date:
            if self.to_date>self.booking_id.to_date:
                raise models.ValidationError(('Nuevo Fecha Fin no puede ser mayor que %s' % (self.booking_id.to_date,)))
            if self.to_date<self.booking_id.from_date:
                raise models.ValidationError(('Nuevo Fecha Fin no puede ser menor que %s' % (self.booking_id.from_date,)))

    booking_id= fields.Many2one('hr.projection.timesheet', string='Booking', default=lambda r: r._context['booking_id'])
    to_date=fields.Date(default=lambda r: r.booking_id.to_date, string='Fecha Fin Nueva')

    @api.multi
    def action_generate(self):
        for line in self:
            #raise models.ValidationError(('state_booking %s' % (self.booking_id.oc_profile.id,)))
            if line.booking_id.confirm_type=='periodws':
                line.booking_id.booking_shorten_periodws(line.to_date)
            if line.booking_id.confirm_type=='periodns':
                line.booking_id.booking_shorten_periodns(line.to_date)
            if line.booking_id.confirm_type=='weekws':
                line.booking_id.booking_shorten_weekws(line.to_date)
            if line.booking_id.confirm_type=='weekns':
                line.booking_id.booking_shorten_weekns(line.to_date)
            values={}
            values["state_booking"]=False
            sale_order_line_obj=self.env["sale.order.line"].search([('id','=',self.booking_id.oc_profile.id)])
            #raise models.ValidationError(('sale_order_line_obj %s' % (sale_order_line_obj,)))
            sale_order_line_obj.write(values)
