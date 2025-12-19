/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class CCOpsDashboard extends Component {
    static template = "patriot_cc_ops.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            projects: [],
            loading: true,
            searchQuery: "",
            expandedId: null,
            theme: localStorage.getItem("cc_ops_theme") || "splash",
        });

        this.animationFrame = null;
        this.auroraT = 0;

        onMounted(() => {
            this.loadProjects();
            if (this.state.theme === "aurora") {
                this.startAurora();
            }
        });

        onWillUnmount(() => {
            this.stopAurora();
        });
    }

    // Theme
    get themeClass() {
        return this.state.theme === "aurora" ? "aurora-theme" : "";
    }

    toggleTheme() {
        const newTheme = this.state.theme === "splash" ? "aurora" : "splash";
        this.state.theme = newTheme;
        localStorage.setItem("cc_ops_theme", newTheme);

        if (newTheme === "aurora") {
            this.startAurora();
        } else {
            this.stopAurora();
        }
    }

    startAurora() {
        const canvas = document.getElementById("ccAuroraCanvas");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const draw = () => {
            const w = canvas.width, h = canvas.height;
            ctx.fillStyle = "#020205";
            ctx.fillRect(0, 0, w, h);

            [[0, 242, 254], [79, 172, 254], [162, 210, 255]].forEach((c, i) => {
                ctx.beginPath();
                const g = ctx.createLinearGradient(0, 0, w, 0);
                g.addColorStop(0, `rgba(${c.join(",")},0)`);
                g.addColorStop(0.5, `rgba(${c.join(",")},${0.2 - i * 0.05})`);
                g.addColorStop(1, `rgba(${c.join(",")},0)`);
                ctx.fillStyle = g;

                for (let x = 0; x <= w; x += 10) {
                    const y = h / 2 + Math.sin(x * 0.005 + this.auroraT + i) * 100 + Math.sin(x * 0.01 - this.auroraT * 0.5) * 50;
                    if (x === 0) ctx.moveTo(x, h);
                    ctx.lineTo(x, y);
                }
                ctx.lineTo(w, h);
                ctx.closePath();
                ctx.fill();
            });

            this.auroraT += 0.01;
            this.animationFrame = requestAnimationFrame(draw);
        };
        draw();
    }

    stopAurora() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    }

    // Data
    async loadProjects() {
        try {
            const projects = await this.orm.searchRead(
                "cc.opportunity", [],
                ["id", "name", "project_number", "city", "state_id", "bid_date", "state", "document_count", "estimated_value", "gc_name", "owner_name"],
                { order: "bid_date asc" }
            );
            this.state.projects = projects;
        } catch (e) {
            console.error("Load error:", e);
        }
        this.state.loading = false;
    }

    // Search
    get filteredProjects() {
        const q = this.state.searchQuery.toLowerCase().trim();
        if (!q) return this.state.projects;
        return this.state.projects.filter(p =>
            (p.name || "").toLowerCase().includes(q) ||
            (p.city || "").toLowerCase().includes(q) ||
            (p.gc_name || "").toLowerCase().includes(q)
        );
    }

    onSearch(ev) {
        this.state.searchQuery = ev.target.value;
    }

    // Expand
    toggleExpand(id) {
        this.state.expandedId = this.state.expandedId === id ? null : id;
    }

    isExpanded(id) {
        return this.state.expandedId === id;
    }

    // Actions
    async openProject(id) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cc.opportunity",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // Formatting
    formatDate(d) {
        if (!d) return "—";
        return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
    }

    formatCurrency(v) {
        if (!v) return "—";
        return "$" + Math.round(v / 1000) + "k";
    }
}

registry.category("actions").add("cc_ops_dashboard", CCOpsDashboard);
