/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

// Fields that Odoo auto-loads for every view but that aren't real columns.
const TECH = new Set([
    "id", "create_date", "create_uid", "write_date", "write_uid", "display_name", "__last_update",
]);

/**
 * Debug-menu item: "Fields in this view".
 * Appears on any model/view (developer mode). Resolves the current view via
 * get_view, then opens ir.model.fields filtered to exactly that view's fields.
 */
function fieldsInView({ component, env }) {
    const config = component.env.config;
    const resModel = component.props.resModel || (config && config.resModel);
    const viewType = config && config.viewType;
    const viewId = config && config.viewId;
    if (!resModel || !viewType) {
        return null;
    }
    return {
        type: "item",
        description: _t("Fields in this view"),
        sequence: 275,
        section: "ui",
        callback: async () => {
            const res = await env.services.orm.call(resModel, "get_view", [], {
                view_id: viewId || false,
                view_type: viewType,
            });
            const m = (res.models && res.models[resModel]) || {};
            const names = (Array.isArray(m) ? m : Object.keys(m)).filter((f) => !TECH.has(f));
            env.services.action.doAction({
                type: "ir.actions.act_window",
                name: _t("Fields in %(model)s %(type)s view (%(n)s)", {
                    model: resModel,
                    type: viewType,
                    n: names.length,
                }),
                res_model: "ir.model.fields",
                views: [[false, "list"], [false, "form"]],
                domain: [["model", "=", resModel], ["name", "in", names]],
                target: "current",
            });
        },
    };
}

registry.category("debug").category("view").add("fieldsInView", fieldsInView);
