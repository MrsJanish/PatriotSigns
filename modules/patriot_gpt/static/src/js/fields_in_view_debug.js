/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

// Fields Odoo auto-loads for every view but that aren't real columns.
const TECH = new Set([
    "id", "create_date", "create_uid", "write_date", "write_uid", "display_name", "__last_update",
]);

/**
 * Debug-menu item factory. Opens ir.model.fields for the current model/view.
 *   inverse = false -> fields IN the current view
 *   inverse = true  -> fields NOT in the current view
 */
function makeFieldsItem(ctx, inverse) {
    const { component, env } = ctx;
    const config = component.env.config;
    const resModel = component.props.resModel || (config && config.resModel);
    const viewType = config && config.viewType;
    const viewId = config && config.viewId;
    if (!resModel || !viewType) {
        return null;
    }
    return {
        type: "item",
        description: inverse ? _t("Fields NOT in this view") : _t("Fields in this view"),
        sequence: inverse ? 276 : 275,
        section: "ui",
        callback: async () => {
            const res = await env.services.orm.call(resModel, "get_view", [], {
                view_id: viewId || false,
                view_type: viewType,
            });
            const m = (res.models && res.models[resModel]) || {};
            const names = (Array.isArray(m) ? m : Object.keys(m)).filter((f) => !TECH.has(f));
            let qty = names.length;
            if (inverse) {
                const total = await env.services.orm.searchCount("ir.model.fields", [["model", "=", resModel]]);
                qty = total - names.length;
            }
            env.services.action.doAction({
                type: "ir.actions.act_window",
                name: inverse
                    ? _t("Fields NOT in %(model)s %(type)s view (ID %(v)s, Qty. %(q)s)", { model: resModel, type: viewType, v: res.id, q: qty })
                    : _t("Fields in %(model)s %(type)s view (ID %(v)s, Qty. %(q)s)", { model: resModel, type: viewType, v: res.id, q: qty }),
                res_model: "ir.model.fields",
                views: [[false, "list"], [false, "form"]],
                domain: [["model", "=", resModel], ["name", inverse ? "not in" : "in", names]],
                target: "current",
            });
        },
    };
}

registry.category("debug").category("view").add("fieldsInView", (ctx) => makeFieldsItem(ctx, false));
registry.category("debug").category("view").add("fieldsNotInView", (ctx) => makeFieldsItem(ctx, true));
