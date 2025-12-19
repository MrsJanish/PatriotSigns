/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class CCOpsDashboard extends Component {
    static template = "patriot_cc_ops.Dashboard";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            projects: [],
            loading: true,
            expandedId: null,
        });

        onMounted(() => {
            this.loadProjects();
        });
    }

    async loadProjects() {
        try {
            const projects = await this.orm.searchRead(
                "cc.opportunity",
                [],
                ["id", "name", "city", "state_id", "bid_date", "state", "document_count"],
                { order: "bid_date asc" }
            );
            this.state.projects = projects;
        } catch (error) {
            console.error("Failed to load projects:", error);
            this.state.projects = [];
        }
        this.state.loading = false;
    }

    toggleProject(projectId) {
        this.state.expandedId = this.state.expandedId === projectId ? null : projectId;
    }

    async openProject(projectId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cc.opportunity",
            res_id: projectId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("cc_ops_dashboard", CCOpsDashboard);
