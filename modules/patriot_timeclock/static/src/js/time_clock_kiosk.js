/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Time Clock Kiosk Component
 * 
 * A simple clock-in/clock-out interface for employees.
 */
class TimeClockKiosk extends Component {
    static template = "patriot_timeclock.TimeClockKiosk";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            isClockedIn: false,
            currentProject: null,
            currentDuration: "0h 0m",
            activePunchId: null,
            projects: [],
            selectedProjectId: null,
            notes: "",
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });

        // Update duration every second
        this.intervalId = setInterval(() => {
            if (this.state.isClockedIn) {
                this.updateDuration();
            }
        }, 1000);
    }

    async loadData() {
        this.state.loading = true;

        // Get current employee's active punch
        const activePunches = await this.orm.searchRead(
            "ps.time.punch",
            [["state", "=", "active"], ["employee_id.user_id", "=", this.env.user.userId]],
            ["id", "project_id", "punch_in", "duration_display"]
        );

        if (activePunches.length > 0) {
            const punch = activePunches[0];
            this.state.isClockedIn = true;
            this.state.activePunchId = punch.id;
            this.state.currentProject = punch.project_id[1];
            this.state.currentDuration = punch.duration_display;
            this.state.punchInTime = new Date(punch.punch_in);
        } else {
            this.state.isClockedIn = false;
        }

        // Get available projects
        const projects = await this.orm.searchRead(
            "project.project",
            [["active", "=", true]],
            ["id", "name"]
        );
        this.state.projects = projects;

        this.state.loading = false;
    }

    updateDuration() {
        if (this.state.punchInTime) {
            const now = new Date();
            const diff = now - this.state.punchInTime;
            const hours = Math.floor(diff / 3600000);
            const minutes = Math.floor((diff % 3600000) / 60000);
            const seconds = Math.floor((diff % 60000) / 1000);
            this.state.currentDuration = `${hours}h ${minutes}m ${seconds}s`;
        }
    }

    async clockIn() {
        if (!this.state.selectedProjectId) {
            this.notification.add("Please select a project", { type: "warning" });
            return;
        }

        await this.orm.create("ps.time.punch", [{
            project_id: this.state.selectedProjectId,
            notes: this.state.notes,
            state: "active",
        }]);

        this.notification.add("Clocked in!", { type: "success" });
        await this.loadData();
    }

    async clockOut() {
        if (!this.state.activePunchId) {
            this.notification.add("Not clocked in", { type: "warning" });
            return;
        }

        await this.orm.call("ps.time.punch", "action_clock_out", [this.state.activePunchId]);

        this.notification.add(`Clocked out! Logged ${this.state.currentDuration}`, { type: "success" });
        await this.loadData();
    }

    async switchProject() {
        if (!this.state.selectedProjectId) {
            this.notification.add("Please select a project to switch to", { type: "warning" });
            return;
        }

        // Clock out current
        if (this.state.activePunchId) {
            await this.orm.call("ps.time.punch", "action_clock_out", [this.state.activePunchId]);
        }

        // Clock into new
        await this.orm.create("ps.time.punch", [{
            project_id: this.state.selectedProjectId,
            notes: this.state.notes,
            state: "active",
        }]);

        this.notification.add("Switched project!", { type: "success" });
        await this.loadData();
    }

    onProjectChange(ev) {
        this.state.selectedProjectId = parseInt(ev.target.value) || null;
    }

    onNotesChange(ev) {
        this.state.notes = ev.target.value;
    }

    willUnmount() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }
}

TimeClockKiosk.template = "patriot_timeclock.TimeClockKiosk";

registry.category("actions").add("ps_time_clock_kiosk", TimeClockKiosk);

export default TimeClockKiosk;
