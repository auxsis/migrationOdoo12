# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError
from .bigint import BigInt
import logging
_logger = logging.getLogger(__name__)


class account_move(models.Model):
    _inherit = "account.move"

    document_class_id = fields.Many2one(
            'sii.document_class',
            string='Document Type',
            copy=False,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    sii_document_number = BigInt(
            string='Document Number',
            copy=False,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    canceled = fields.Boolean(
            string="Canceled?",
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    iva_uso_comun = fields.Boolean(
            string="Iva Uso Común",
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    no_rec_code = fields.Selection(
            [
                ('1','Compras destinadas a IVA a generar operaciones no gravados o exentas.'),
                ('2','Facturas de proveedores registrados fuera de plazo.'),
                ('3','Gastos rechazados.'),
                ('4','Entregas gratuitas (premios, bonificaciones, etc.) recibidos.'),
                ('9','Otros.')
            ],
            string="Código No recuperable",
            readonly=True,
            states={'draft': [('readonly', False)]},
        )# @TODO select 1 automático si es emisor 2Categoría
    sended = fields.Boolean(
            string="Enviado al SII",
            default=False,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    factor_proporcionalidad = fields.Float(
            string="Factor proporcionalidad",
            default=0.00,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )

    def _get_move_imps(self):
        imps = {}
        for l in self.line_ids:
            if l.tax_line_id:
                if l.tax_line_id:
                    if not l.tax_line_id.id in imps:
                        imps[l.tax_line_id.id] = {'tax_id':l.tax_line_id.id, 'credit':0 , 'debit': 0, 'code':l.tax_line_id.sii_code}
                    imps[l.tax_line_id.id]['credit'] += l.credit
                    imps[l.tax_line_id.id]['debit'] += l.debit
                    if l.tax_line_id.activo_fijo:
                        ActivoFijo[1] += l.credit
            elif l.tax_ids and l.tax_ids[0].amount == 0: #caso monto exento
                if not l.tax_ids[0].id in imps:
                    imps[l.tax_ids[0].id] = {'tax_id':l.tax_ids[0].id, 'credit':0 , 'debit': 0, 'code':l.tax_ids[0].sii_code}
                imps[l.tax_ids[0].id]['credit'] += l.credit
                imps[l.tax_ids[0].id]['debit'] += l.debit
        return imps

    def totales_por_movimiento(self):
        move_imps = self._get_move_imps()
        imps = {'iva':0,
                'exento':0,
                'otros_imps':0,
                }
        for key, i in move_imps.items():
            if i['code'] in [14]:
                imps['iva'] += (i['credit'] or i['debit'])
            elif i['code'] == 0:
                imps['exento']  += (i['credit'] or i['debit'])
            else:
                imps['otros_imps'] += (i['credit'] or i['debit'])
        imps['neto'] = self.amount - imps['otros_imps'] - imps['exento'] - imps['iva']
        return imps



    @api.multi
    def post(self, invoice=False):
        _logger.info("movepost2")
        self._post_validate()
        # Create the analytic lines in batch is faster as it leads to less cache invalidation.
        self.mapped('line_ids').create_analytic_lines()
        for move in self:
            _logger.info("movename=%s,%s",move.name,invoice and invoice.move_name or '')
            if move.name == '/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.move_name and invoice.move_name != '/':
                    new_name = invoice.move_name
                else:
                    if journal.sequence_id:
                        # If invoice is actually refund and journal has a refund_sequence then use that one or use the regular one
                        sequence = journal.sequence_id
                        if invoice and invoice.type in ['out_refund', 'in_refund'] and journal.refund_sequence:
                            if not journal.refund_sequence_id:
                                raise UserError(_('Please define a sequence for the credit notes'))
                            sequence = journal.refund_sequence_id

                        new_name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                    else:
                        raise UserError(_('Please define a sequence on the journal.'))

                    #apiux get egress sequence for journal type bank
                    _logger.info("journalline=%s,%s",journal.type,move.line_ids)
                    if journal.type in ['cash','bank']:
                        for ml in move.line_ids:
                            _logger.info("egressline=%s,%s,%s",ml.account_id.user_type_id.type,ml.debit,ml.credit)
                            if ml.account_id.user_type_id.type=='liquidity' and ml.debit==0 and ml.credit>0:
                            
                                if not journal.egress_sequence_id:
                                    raise UserError(_('Please define an egress sequence for the journal'))
                                sequence = journal.egress_sequence_id
                                new_name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                                break

                if new_name:
                    move.name = new_name

            if move == move.company_id.account_opening_move_id and not move.company_id.account_bank_reconciliation_start:
                # For opening moves, we set the reconciliation date threshold
                # to the move's date if it wasn't already set (we don't want
                # to have to reconcile all the older payments -made before
                # installing Accounting- with bank statements)
                move.company_id.account_bank_reconciliation_start = move.date

        return self.write({'state': 'posted'})

class account_move_line(models.Model):
    _inherit = "account.move.line"

    document_class_id = fields.Many2one(
            'sii.document_class',
            string='Document Type',
            related='move_id.document_class_id',
            store=True,
            readonly=True,
        )

    real_period_id = fields.Many2one(
        'account.period', 
        string='Periodo Real',
        )


    #this sets date to real period start date if exists 
    @api.one
    def _prepare_analytic_line(self):
        res=super(account_move_line,self)._prepare_analytic_line()
            
        for line in res:
            real_period_id=line.get('real_period_id',False)
            if real_period_id:
                if line['date']<real_period_id.date_start or line['date']>real_period_id.date_stop:
                    line['date']=real_period_id.date_start
        return res