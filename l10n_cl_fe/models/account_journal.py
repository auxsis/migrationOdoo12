# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    sucursal_id = fields.Many2one(
            'sii.sucursal',
            string="Sucursal",
        )
    sii_code = fields.Char(
            related='sucursal_id.name',
            string="Código SII Sucursal",
            readonly=True,
        )
    journal_document_class_ids = fields.One2many(
            'account.journal.sii_document_class',
            'journal_id',
            'Documents Class',
        )
    document_class_ids = fields.Many2many(
        'sii.document_class',
        string="Document Class IDs"
    )
    use_documents = fields.Boolean(
            string='Use Documents?',
            default='_get_default_doc',
        )
    company_activity_ids = fields.Many2many(
        'partner.activities',
        related='company_id.company_activities_ids'
    )
    journal_activities_ids = fields.Many2many(
            'partner.activities',
            id1='journal_id',
            id2='activities_id',
            string='Journal Turns',
            help="""Select the turns you want to \
            invoice in this Journal""",
        )
    restore_mode = fields.Boolean(
            string="Restore Mode",
            default=False,
        )
        
    #apiux additional fields for chile
    refund_journal_id = fields.Many2one(
            'account.journal',
            string="Credit Note Journal",
            default=False,
        )


    egress_sequence_id = fields.Many2one(
            'ir.sequence', 
            string='Egress Sequence',
            help="This field contains the information related to the numbering of the journal entries of this journal.",
            copy=False
        )
    egress_sequence_number_next = fields.Integer(
            string='Egress Next Number',
            help='The next sequence number will be used for the next invoice.',
            compute='_compute_egr_seq_number_next',
            inverse='_inverse_egr_seq_number_next'
        )        
        

    @api.depends('egress_sequence_id.use_date_range', 'egress_sequence_id.number_next_actual')
    def _compute_egr_seq_number_next(self):
        '''Compute 'sequence_number_next' according to the current sequence in use,
        an ir.sequence or an ir.sequence.date_range.
        '''
        for journal in self:
            if journal.egress_sequence_id:
                sequence = journal.egress_sequence_id._get_current_sequence()
                journal.egress_sequence_number_next = sequence.number_next_actual
            else:
                journal.egress_sequence_number_next = 1

    @api.multi
    def _inverse_egr_seq_number_next(self):
        '''Inverse 'sequence_number_next' to edit the current sequence next number.
        '''
        for journal in self:
            if journal.egress_sequence_id and journal.egress_sequence_number_next:
                sequence = journal.egress_sequence_id._get_current_sequence()
                sequence.sudo().number_next = journal.egress_sequence_number_next



    @api.onchange('journal_document_class_ids')
    def set_documents(self):
        self.document_class_ids = []
        for r in self.journal_document_class_ids:
            self.document_class_ids += r.sii_document_class_id

    @api.onchange('journal_activities_ids')
    def max_actecos(self):
        if len(self.journal_activities_ids) > 4:
            raise UserError("Deben Ser máximo 4 actecos por Diario, seleccione los más significativos para este diario")

    @api.multi
    def _get_default_doc(self):
        self.ensure_one()
        if self.type == 'sale' or self.type == 'purchase':
            self.use_documents = True

    @api.multi
    def name_get(self):
        res = []
        for journal in self:
            currency = journal.currency_id or journal.company_id.currency_id
            name = "%s (%s)" % (journal.name, currency.name)
            if journal.sucursal_id and self.env.context.get('show_full_name', False):
                name = "%s (%s)" % (name, journal.sucursal_id.name)
            res.append((journal.id, name))
        return res
