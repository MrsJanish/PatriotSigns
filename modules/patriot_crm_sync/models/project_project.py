import logging
from odoo import fields, models, api

_logger = logging.getLogger(__name__)

SYNC_FLAG = '_crm_project_syncing'

# ============================================================
# Reverse field mapping: Project field → CRM lead field
# Only bidirectional fields are included here.
# One-way CRM→Project fields (like warranty_period, city_state)
# are intentionally excluded from reverse sync.
# ============================================================
FIELD_MAP_PROJECT_TO_CRM = {
    # Core
    'name': 'name',
    'partner_id': 'partner_id',
    'user_id': 'user_id',
    # Contract / financial
    'x_studio_contract_amount': 'x_studio_contract_amount',
    'x_studio_contract_no': 'x_studio_contract_no',
    'x_studio_contract_date': 'x_studio_contract_date_issued',
    'x_studio_retainage_percentage': 'x_studio_retainage_percentage',
    'x_studio_billing': 'x_studio_billing',
    'x_studio_project_contract_number': 'x_studio_project_contract_number',
    # Reference
    'x_studio_payapp_due_date': 'x_studio_pa_due_date',
    # Status
    'x_studio_needs_attention': 'x_studio_needs_attention',
    # Relational
    'x_studio_project_alias': 'x_studio_project_alias',
    'x_studio_team_contacts': 'x_studio_team_contacts',
    'x_studio_project_stage_sync': 'x_studio_project_stage',
    'x_studio_opportunity_customer': 'x_studio_owner',
}

# Fields that trigger Project → CRM sync
SYNC_TRIGGER_FIELDS = set(FIELD_MAP_PROJECT_TO_CRM.keys())


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # ----------------------------------------------------------
    # Studio-originated fields — declared here so the module is
    # self-contained and installable on fresh databases.
    # ----------------------------------------------------------
    x_studio_project_bid = fields.Many2one(
        'crm.lead', string='Linked CRM Lead', ondelete='set null',
    )
    x_studio_opportunity_name = fields.Many2one(
        'crm.lead', string='Opportunity (fallback)', ondelete='set null',
    )
    x_studio_contract_amount = fields.Float('Contract Amount')
    x_studio_contract_no = fields.Char('Contract No.')
    x_studio_project_contract_number = fields.Char('Project/Contract No.')
    x_studio_contract_date = fields.Date('Contract Date')
    x_studio_retainage_percentage = fields.Float('Retainage %')
    x_studio_warranty_period = fields.Char('Warranty Period')
    x_studio_billing = fields.Char('Billing')
    x_studio_payapp_due_date = fields.Date('Pay App Due Date')
    x_studio_sequence = fields.Char('GC Project No.')
    x_studio_project_stage_sync = fields.Char('Project Stage')
    x_studio_city_state = fields.Char('City / State')
    x_studio_opportunity_customer = fields.Many2one(
        'res.partner', string='Owner', ondelete='set null',
    )
    x_studio_project_alias = fields.Char('Project Alias')
    x_studio_needs_attention = fields.Boolean('Needs Attention')
    x_studio_team_contacts = fields.Many2many(
        'res.partner', 'x_project_team_contacts_rel',
        'project_id', 'partner_id', string='Team Contacts',
    )
    x_studio_description = fields.Text('CRM Description')
    x_studio_project_name_text = fields.Char('Project Name (text)')
    x_studio_related_field_ke_1ibpjr5k8 = fields.One2many(
        'x_sign_types', 'x_studio_generated_project', string='Sign Types',
    )
    x_studio_locations = fields.One2many(
        'x_defined_locations', 'x_studio_project_won', string='Locations',
    )

    # ----------------------------------------------------------
    # Write override — sync project changes back to CRM
    # ----------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)

        if self.env.context.get(SYNC_FLAG):
            return res

        if SYNC_TRIGGER_FIELDS & set(vals.keys()):
            for project in self:
                self._sync_to_crm(project, vals)

        return res

    # ----------------------------------------------------------
    # Sync Project → CRM on field changes
    # ----------------------------------------------------------
    def _sync_to_crm(self, project, changed_vals):
        """Push changed fields from project back to linked CRM lead."""
        lead = self._find_linked_lead(project)
        if not lead:
            return

        update_vals = {}
        for proj_field, crm_field in FIELD_MAP_PROJECT_TO_CRM.items():
            if proj_field not in changed_vals:
                continue
            try:
                update_vals.update(
                    self._compute_reverse_sync_val(
                        project, lead, proj_field, crm_field
                    )
                )
            except Exception:
                _logger.warning(
                    "Skipping reverse sync for %s → %s on project %s",
                    proj_field, crm_field, project.name, exc_info=True,
                )

        if update_vals:
            lead.sudo().with_context(**{SYNC_FLAG: True}).write(update_vals)
            _logger.info(
                "Synced project %s → CRM %s: %s",
                project.name, lead.name, list(update_vals.keys()),
            )

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------
    def _find_linked_lead(self, project):
        """Find the CRM lead linked to this project."""
        # x_studio_project_bid is the stored many2one field
        if project.x_studio_project_bid:
            return project.x_studio_project_bid

        # Fallback: check the related field chain
        if project.x_studio_opportunity_name:
            return project.x_studio_opportunity_name

        return False

    @staticmethod
    def _compute_reverse_sync_val(project, lead, proj_field, crm_field):
        """
        Compute the value to write on the CRM lead for a single field pair.
        Returns a dict {crm_field: value} or empty dict if no change needed.
        """
        proj_val = getattr(project, proj_field, False)

        # Many2many fields
        if hasattr(proj_val, 'ids') and project._fields[proj_field].type == 'many2many':
            lead_val = getattr(lead, crm_field, False)
            proj_ids = set(proj_val.ids)
            lead_ids = set(lead_val.ids) if lead_val else set()
            if proj_ids != lead_ids:
                return {crm_field: [(6, 0, list(proj_ids))]}
            return {}

        # Many2one fields
        if hasattr(proj_val, 'id'):
            proj_id = proj_val.id if proj_val else False
            lead_val = getattr(lead, crm_field, False)
            lead_id = lead_val.id if lead_val else False
            if proj_id != lead_id:
                return {crm_field: proj_id}
            return {}

        # Scalar fields
        lead_val = getattr(lead, crm_field, False)
        if (proj_val or False) != (lead_val or False):
            return {crm_field: proj_val}
        return {}
