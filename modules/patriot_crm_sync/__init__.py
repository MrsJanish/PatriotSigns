import logging

from . import models

_logger = logging.getLogger(__name__)


def _disable_studio_automations(env):
    """Disable old Studio-based automations replaced by this module.

    These automations were created via Studio on the production database
    and may not exist on fresh builds.  We search by name instead of
    hard-coded IDs so this never crashes on a clean database.
    """
    Automation = env['base.automation']
    names = [
        'Auto-Create Project When Won',   # replaced by CrmLead.write()
        'Sync Opportunity → Project',     # replaced by CrmLead._sync_to_project()
        'Sync Project → Opportunity',     # replaced by ProjectProject._sync_to_crm()
    ]
    for name in names:
        automations = Automation.search([('name', '=', name)])
        if automations:
            automations.write({'active': False})
            _logger.info(
                "Disabled Studio automation '%s' (ids=%s) — replaced by patriot_crm_sync",
                name, automations.ids,
            )
        else:
            _logger.info(
                "Studio automation '%s' not found — nothing to disable", name,
            )
