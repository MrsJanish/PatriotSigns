/** @odoo-module **/

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { jsonrpc } from "@web/core/network/rpc_service";

/**
 * AISearch - AI-powered natural language search for projects/tasks
 * 
 * Single search field that uses GPT to match queries to projects/tasks.
 * Shows 1 result if confident, up to 3 if unsure.
 */
export class AISearch extends Component {
    static template = "patriot_timeclock.AISearch";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.notification = useService("notification");
        this.inputRef = useRef("searchInput");

        this.state = useState({
            query: "",
            results: [],
            selectedIndex: 0,
            loading: false,
            searched: false,
        });

        this.debounceTimer = null;
    }

    onInputChange(ev) {
        this.state.query = ev.target.value;
        this.state.searched = false;

        // Clear previous timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Debounce - wait 600ms after typing stops
        if (this.state.query.length >= 2) {
            this.debounceTimer = setTimeout(() => {
                this.search();
            }, 600);
        }
    }

    onKeyDown(ev) {
        if (ev.key === 'Enter') {
            ev.preventDefault();
            if (this.state.results.length > 0) {
                this.selectResult(this.state.results[this.state.selectedIndex]);
            } else if (this.state.query.length >= 2) {
                this.search();
            }
        } else if (ev.key === 'ArrowDown') {
            ev.preventDefault();
            if (this.state.selectedIndex < this.state.results.length - 1) {
                this.state.selectedIndex++;
            }
        } else if (ev.key === 'ArrowUp') {
            ev.preventDefault();
            if (this.state.selectedIndex > 0) {
                this.state.selectedIndex--;
            }
        }
    }

    async search() {
        if (this.state.query.length < 2) return;

        this.state.loading = true;
        this.state.results = [];

        try {
            const response = await jsonrpc('/timeclock/ai-search', {
                query: this.state.query
            });

            this.state.results = response.results || [];
            this.state.selectedIndex = 0;
            this.state.searched = true;

            // If only 1 high-confidence result, auto-select it
            if (this.state.results.length === 1 &&
                this.state.results[0].confidence >= 0.85) {
                this.selectResult(this.state.results[0]);
            }
        } catch (error) {
            console.error("AI Search error:", error);
            this.notification.add("Search failed. Please try again.", {
                type: "warning"
            });
        } finally {
            this.state.loading = false;
        }
    }

    selectResult(result) {
        // Update the form fields based on result type
        if (result.type === 'task') {
            this.props.record.update({
                task_id: [result.id, result.name],
                project_id: result.project_id ? [result.project_id, result.project_name] : false,
            });
        } else if (result.type === 'project') {
            this.props.record.update({
                project_id: [result.id, result.name],
                task_id: false,
            });
        }

        // Clear search state
        this.state.query = result.display;
        this.state.results = [];
        this.state.searched = true;
    }

    getConfidenceClass(confidence) {
        if (confidence >= 0.85) return "text-success";
        if (confidence >= 0.6) return "text-warning";
        return "text-muted";
    }

    getConfidenceIcon(confidence) {
        if (confidence >= 0.85) return "fa-check-circle";
        if (confidence >= 0.6) return "fa-question-circle";
        return "fa-circle-o";
    }
}

// Register the widget
export const aiSearchField = {
    component: AISearch,
    supportedTypes: ["many2one"],
};

registry.category("fields").add("ai_search", aiSearchField);
