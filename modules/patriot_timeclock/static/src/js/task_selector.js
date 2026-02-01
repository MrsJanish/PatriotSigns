/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * TaskSelector - Card-based task/project selector widget
 * 
 * Displays projects and tasks as clickable cards with search filtering.
 */
export class TaskSelector extends Component {
    static template = "patriot_timeclock.TaskSelector";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            searchQuery: "",
            projects: [],
            tasks: [],
            selectedProjectId: false,
            selectedTaskId: false,
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;

        // Load active projects
        const projects = await this.orm.searchRead(
            "project.project",
            [["active", "=", true]],
            ["id", "name", "color"],
            { limit: 50, order: "name asc" }
        );

        // Load tasks assigned to current user
        const tasks = await this.orm.searchRead(
            "project.task",
            [
                ["user_ids", "in", [this.env.uid]],
                ["is_closed", "=", false],
            ],
            ["id", "name", "project_id", "priority_sequence", "work_state", "color"],
            { limit: 50, order: "priority_sequence asc, id desc" }
        );

        this.state.projects = projects;
        this.state.tasks = tasks;
        this.state.loading = false;
    }

    get filteredProjects() {
        const query = this.state.searchQuery.toLowerCase();
        if (!query) return this.state.projects;
        return this.state.projects.filter(p =>
            p.name.toLowerCase().includes(query)
        );
    }

    get filteredTasks() {
        const query = this.state.searchQuery.toLowerCase();
        if (!query) return this.state.tasks;
        return this.state.tasks.filter(t =>
            t.name.toLowerCase().includes(query) ||
            (t.project_id && t.project_id[1].toLowerCase().includes(query))
        );
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    selectProject(project) {
        this.state.selectedProjectId = project.id;
        this.state.selectedTaskId = false;
        // Update the form field
        this.props.record.update({
            project_id: [project.id, project.name],
            task_id: false
        });
    }

    selectTask(task) {
        this.state.selectedTaskId = task.id;
        this.state.selectedProjectId = task.project_id ? task.project_id[0] : false;
        // Update the form fields
        this.props.record.update({
            task_id: [task.id, task.name],
            project_id: task.project_id || false,
        });
    }

    isProjectSelected(project) {
        return this.state.selectedProjectId === project.id && !this.state.selectedTaskId;
    }

    isTaskSelected(task) {
        return this.state.selectedTaskId === task.id;
    }

    getCardColor(item) {
        const colors = [
            "#F06050", "#F4A460", "#F7CD1F", "#6CC1ED",
            "#814968", "#EB7E7F", "#2C8397", "#475577",
            "#D6145F", "#30C381", "#9365B8"
        ];
        const colorIndex = (item.color || 0) % colors.length;
        return colors[colorIndex];
    }
}

// Register the widget
export const taskSelectorField = {
    component: TaskSelector,
    supportedTypes: ["many2one"],
};

registry.category("fields").add("task_selector", taskSelectorField);
