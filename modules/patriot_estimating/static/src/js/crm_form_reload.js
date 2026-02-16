/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    async onRecordSaved(record) {
        await super.onRecordSaved(record);
        // Auto-reload CRM leads in estimating stage to refresh all computed related fields
        if (record.resModel === "crm.lead") {
            await record.load();
        }
    },
});
