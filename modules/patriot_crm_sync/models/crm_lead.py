import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

# Context flag to prevent infinite sync loops
SYNC_FLAG = '_crm_project_syncing'

# ============================================================
# Field mapping: CRM lead field → Project field
# These are synced on create AND on every subsequent write.
# ============================================================
FIELD_MAP_CRM_TO_PROJECT = {
    # Core fields
    'name': 'name',
    'partner_id': 'partner_id',
    'user_id': 'user_id',
    'description': 'x_studio_description',
    # Contract / financial
    'x_studio_contract_amount': 'x_studio_contract_amount',
    'x_studio_contract_no': 'x_studio_contract_no',
    'x_studio_contract_date_issued': 'x_studio_contract_date',
    'x_studio_retainage_percentage': 'x_studio_retainage_percentage',
    'x_studio_warranty_period': 'x_studio_warranty_period',
    'x_studio_billing': 'x_studio_billing',
    'x_studio_project_contract_number': 'x_studio_project_contract_number',
    # Reference / identifier
    'x_studio_gc_project_no': 'x_studio_sequence',
    'x_studio_pa_due_date': 'x_studio_payapp_due_date',
    # Status
    'x_studio_needs_attention': 'x_studio_needs_attention',
    # Relational (many2one / many2many — need special handling)
    'x_studio_project_alias': 'x_studio_project_alias',
    'x_studio_team_contacts': 'x_studio_team_contacts',
    'x_studio_project_stage': 'x_studio_project_stage_sync',
    'x_studio_city_state': 'x_studio_city_state',
    'x_studio_owner': 'x_studio_opportunity_customer',
}

# Fields that trigger CRM → Project sync
SYNC_TRIGGER_FIELDS = set(FIELD_MAP_CRM_TO_PROJECT.keys())


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ----------------------------------------------------------
    # Write override — handles both auto-create and sync
    # ----------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)

        if self.env.context.get(SYNC_FLAG):
            return res

        for lead in self:
            # --- Auto-create project on Won ---
            if 'stage_id' in vals:
                stage = self.env['crm.stage'].browse(vals['stage_id'])
                if stage.is_won:
                    self._create_project_for_won(lead)

            # --- Sync changed fields to linked project ---
            if SYNC_TRIGGER_FIELDS & set(vals.keys()):
                self._sync_to_project(lead, vals)

        return res

    # ----------------------------------------------------------
    # Auto-create project when lead is Won
    # ----------------------------------------------------------
    def _create_project_for_won(self, lead):
        """Create a project.project for a newly-won lead."""
        Project = self.env['project.project'].sudo()

        # Guard: don't create duplicates
        existing = Project.search([
            ('x_studio_project_bid', '=', lead.id)
        ], limit=1)
        if not existing and lead.x_studio_project_temp:
            existing = lead.x_studio_project_temp
        if existing:
            _logger.info("Project already exists for lead %s → %s", lead.name, existing.name)
            return

        # Build vals from field map
        project_vals = self._build_project_vals(lead)
        project_vals['allow_timesheets'] = True

        # Create the project
        project = Project.with_context(**{SYNC_FLAG: True}).create(project_vals)

        # Set bidirectional links (x_studio_project_bid is the STORED field)
        project.with_context(**{SYNC_FLAG: True}).write({
            'x_studio_project_bid': lead.id,
        })
        lead.with_context(**{SYNC_FLAG: True}).write({
            'x_studio_project_temp': project.id,
        })

        # Link sign types
        st_count = self._link_sign_types(lead, project)

        # Link locations
        loc_count = self._link_locations(lead, project)

        # Create standard tasks
        self.env['project.task'].sudo().create({
            'name': 'Installation',
            'project_id': project.id,
            'description': 'Clock in to this task while on the install site.',
        })

        # Migrate bidding timesheets
        self._migrate_bidding_timesheets(lead, project)

        # Log
        lead.message_post(
            body=(
                f'Project <b>{project.name}</b> auto-created with full data sync '
                f'({st_count} sign types, {loc_count} locations linked).'
            ),
            subtype_xmlid='mail.mt_note',
        )
        _logger.info(
            "Created project %s (id=%d) for lead %s (id=%d)",
            project.name, project.id, lead.name, lead.id,
        )

    # ----------------------------------------------------------
    # Sync CRM → Project on field changes
    # ----------------------------------------------------------
    def _sync_to_project(self, lead, changed_vals):
        """Push changed fields from CRM lead to linked project."""
        project = self._find_linked_project(lead)
        if not project:
            return

        update_vals = {}
        for crm_field, proj_field in FIELD_MAP_CRM_TO_PROJECT.items():
            if crm_field not in changed_vals:
                continue
            try:
                update_vals.update(
                    self._compute_sync_val(lead, project, crm_field, proj_field)
                )
            except Exception:
                _logger.warning(
                    "Skipping sync for %s → %s on lead %s",
                    crm_field, proj_field, lead.name, exc_info=True,
                )

        # Also sync name to the project_name_text helper field
        if 'name' in changed_vals:
            update_vals['x_studio_project_name_text'] = lead.name

        if update_vals:
            project.sudo().with_context(**{SYNC_FLAG: True}).write(update_vals)
            _logger.info(
                "Synced CRM %s → project %s: %s",
                lead.name, project.name, list(update_vals.keys()),
            )

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------
    def _find_linked_project(self, lead):
        """Find the project linked to this lead via stored fields."""
        project = self.env['project.project'].sudo().search([
            ('x_studio_project_bid', '=', lead.id)
        ], limit=1)
        if not project and lead.x_studio_project_temp:
            project = lead.x_studio_project_temp
        return project

    def _build_project_vals(self, lead):
        """Build a dict of project field values from a lead."""
        vals = {}
        for crm_field, proj_field in FIELD_MAP_CRM_TO_PROJECT.items():
            try:
                pair = self._compute_sync_val(lead, None, crm_field, proj_field)
                vals.update(pair)
            except Exception:
                pass  # Skip fields that don't exist yet
        return vals

    @staticmethod
    def _compute_sync_val(lead, project, crm_field, proj_field):
        """
        Compute the value to write on the project for a single field pair.
        Returns a dict {proj_field: value} or empty dict if no change needed.
        """
        lead_val = getattr(lead, crm_field, False)

        # Many2many fields — use command tuple
        if hasattr(lead_val, 'ids') and lead._fields[crm_field].type == 'many2many':
            proj_val = getattr(project, proj_field, False) if project else False
            lead_ids = set(lead_val.ids)
            proj_ids = set(proj_val.ids) if proj_val else set()
            if lead_ids != proj_ids:
                return {proj_field: [(6, 0, list(lead_ids))]}
            return {}

        # Many2one fields — compare IDs
        if hasattr(lead_val, 'id'):
            lead_id = lead_val.id if lead_val else False
            if project:
                proj_val = getattr(project, proj_field, False)
                proj_id = proj_val.id if proj_val else False
                if lead_id != proj_id:
                    return {proj_field: lead_id}
                return {}
            return {proj_field: lead_id}

        # Scalar fields
        if project:
            proj_val = getattr(project, proj_field, False)
            # Normalize falsy values for comparison
            if (lead_val or False) != (proj_val or False):
                return {proj_field: lead_val}
            return {}
        return {proj_field: lead_val}

    def _link_sign_types(self, lead, project):
        """Link sign type records from the CRM lead to the new project."""
        try:
            sign_types = self.env['x_sign_types'].sudo().search([
                ('x_studio_project', '=', lead.id)
            ])
            if sign_types:
                sign_types.write({'x_studio_generated_project': project.id})
                return len(sign_types)
        except Exception as e:
            _logger.warning("Error linking sign types for lead %s: %s", lead.name, e)
        return 0

    def _link_locations(self, lead, project):
        """Link location records from the CRM lead to the new project."""
        try:
            locations = self.env['x_defined_locations'].sudo().search([
                ('x_studio_project', '=', lead.id)
            ])
            if locations:
                locations.write({'x_studio_project_won': project.id})
                return len(locations)
        except Exception as e:
            _logger.warning("Error linking locations for lead %s: %s", lead.name, e)
        return 0

    def _migrate_bidding_timesheets(self, lead, project):
        """Move timesheet entries from the Bidding project to the new project."""
        try:
            bidding_project = self.env['project.project'].sudo().search(
                [('name', '=', 'Bidding')], limit=1
            )
            if not bidding_project:
                return

            bidding_task = self.env['project.task'].sudo().search([
                ('project_id', '=', bidding_project.id),
                ('x_studio_project_bid', '=', lead.id),
            ], limit=1)
            if not bidding_task:
                return

            new_bid_task = self.env['project.task'].sudo().create({
                'name': 'Bidding Phase',
                'project_id': project.id,
                'user_ids': [(6, 0, bidding_task.user_ids.ids)],
            })

            timesheets = self.env['account.analytic.line'].sudo().search([
                ('task_id', '=', bidding_task.id)
            ])
            if timesheets:
                timesheets.write({
                    'project_id': project.id,
                    'task_id': new_bid_task.id,
                })
                _logger.info(
                    "Moved %d timesheet entries from Bidding to %s",
                    len(timesheets), project.name,
                )

            bidding_task.write({'active': False})
        except Exception:
            _logger.warning(
                "Error migrating bidding timesheets for lead %s",
                lead.name, exc_info=True,
            )
