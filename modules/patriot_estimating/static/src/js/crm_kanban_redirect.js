/** @odoo-module */
/**
 * Patch the CRM Kanban to redirect to the Estimate form
 * when clicking on a lead that has estimates.
 * 
 * When a pipeline card is clicked:
 *  - If the lead has estimates → opens the estimate form (replaces the screen)
 *  - Otherwise → opens the normal CRM lead form
 */
import { patch } from "@web/core/utils/patch";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

patch(KanbanRecord.prototype, {
    async openRecord() {
        // Only intercept crm.lead kanban records
        if (this.props.record.resModel === "crm.lead") {
            const result = await this.env.services.orm.call(
                "crm.lead",
                "action_open_lead_or_estimate",
                [this.props.record.resId]
            );
            if (result && result.res_model !== "crm.lead") {
                // Redirect to the estimate (or other model) form
                await this.env.services.action.doAction(result);
                return;
            }
        }
        // Default behavior for non-redirect cases
        return super.openRecord(...arguments);
    },
});
