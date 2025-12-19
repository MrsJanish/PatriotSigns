/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * CC Ops Dashboard - Custom Client Action
 * Glassmorphism themed project viewer with expandable cards
 * Supports two themes: Splash (light) and Aurora Borealis (dark)
 */
class CCOpsDashboard extends Component {
    static template = "patriot_cc_ops.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        // State management
        this.state = useState({
            projects: [],
            loading: true,
            searchQuery: "",
            expandedId: null,
            theme: this._loadThemePreference(),
        });

        // Aurora animation
        this.animationFrame = null;
        this.auroraT = 0;

        onMounted(() => {
            this._loadProjects();
            if (this.state.theme === 'aurora') {
                this._startAuroraAnimation();
            }
        });

        onWillUnmount(() => {
            this._stopAuroraAnimation();
        });
    }

    // === THEME MANAGEMENT ===

    _loadThemePreference() {
        // Per-user preference stored in localStorage
        const saved = localStorage.getItem('cc_ops_theme');
        return saved || 'splash'; // Default to splash theme
    }

    _saveThemePreference(theme) {
        localStorage.setItem('cc_ops_theme', theme);
    }

    toggleTheme() {
        const newTheme = this.state.theme === 'splash' ? 'aurora' : 'splash';
        this.state.theme = newTheme;
        this._saveThemePreference(newTheme);

        if (newTheme === 'aurora') {
            this._startAuroraAnimation();
        } else {
            this._stopAuroraAnimation();
        }
    }

    get themeClass() {
        return this.state.theme === 'aurora' ? 'aurora-theme' : '';
    }

    get themeButtonText() {
        return this.state.theme === 'aurora' ? '☀️ Light Mode' : '🌌 Aurora Mode';
    }

    // === AURORA ANIMATION ===

    _startAuroraAnimation() {
        const canvas = document.getElementById('cc_aurora_canvas');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };

        window.addEventListener('resize', resize);
        resize();

        const draw = () => {
            const width = canvas.width;
            const height = canvas.height;

            ctx.fillStyle = '#020205';
            ctx.fillRect(0, 0, width, height);

            // Create gradient waves
            for (let i = 0; i < 3; i++) {
                ctx.beginPath();
                let gradient = ctx.createLinearGradient(0, 0, width, 0);

                if (i === 0) {
                    gradient.addColorStop(0, 'rgba(0, 242, 254, 0)');
                    gradient.addColorStop(0.5, 'rgba(0, 242, 254, 0.2)');
                    gradient.addColorStop(1, 'rgba(0, 242, 254, 0)');
                } else if (i === 1) {
                    gradient.addColorStop(0, 'rgba(79, 172, 254, 0)');
                    gradient.addColorStop(0.5, 'rgba(79, 172, 254, 0.2)');
                    gradient.addColorStop(1, 'rgba(79, 172, 254, 0)');
                } else {
                    gradient.addColorStop(0, 'rgba(162, 210, 255, 0)');
                    gradient.addColorStop(0.5, 'rgba(162, 210, 255, 0.1)');
                    gradient.addColorStop(1, 'rgba(162, 210, 255, 0)');
                }

                ctx.fillStyle = gradient;

                for (let x = 0; x <= width; x += 10) {
                    const y = height / 2 +
                        Math.sin(x * 0.005 + this.auroraT + i) * 100 +
                        Math.sin(x * 0.01 - this.auroraT * 0.5) * 50;

                    if (x === 0) ctx.moveTo(x, height);
                    ctx.lineTo(x, y);
                }

                ctx.lineTo(width, height);
                ctx.closePath();
                ctx.fill();
            }

            this.auroraT += 0.01;
            this.animationFrame = requestAnimationFrame(draw);
        };

        draw();
    }

    _stopAuroraAnimation() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    }

    // === DATA LOADING ===

    async _loadProjects() {
        this.state.loading = true;
        try {
            const projects = await this.orm.searchRead(
                "cc.opportunity",
                [],
                [
                    "id", "name", "project_number", "bid_date", "bid_time",
                    "project_type", "project_stage", "estimated_value",
                    "street", "city", "state_id", "zip_code", "county",
                    "owner_name", "architect_name", "gc_name",
                    "state", "document_count", "cc_source_url"
                ],
                { order: "bid_date asc, id desc" }
            );
            this.state.projects = projects;
        } catch (error) {
            console.error("Failed to load projects:", error);
        }
        this.state.loading = false;
    }

    // === FILTERING ===

    get filteredProjects() {
        const query = this.state.searchQuery.toLowerCase().trim();
        if (!query) return this.state.projects;

        return this.state.projects.filter(p => {
            return (
                (p.name || '').toLowerCase().includes(query) ||
                (p.city || '').toLowerCase().includes(query) ||
                (p.state_id || '').toLowerCase().includes(query) ||
                (p.gc_name || '').toLowerCase().includes(query) ||
                (p.owner_name || '').toLowerCase().includes(query) ||
                (p.architect_name || '').toLowerCase().includes(query) ||
                (p.project_number || '').toLowerCase().includes(query)
            );
        });
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    // === PROJECT INTERACTION ===

    toggleProject(projectId) {
        if (this.state.expandedId === projectId) {
            this.state.expandedId = null;
        } else {
            this.state.expandedId = projectId;
        }
    }

    isExpanded(projectId) {
        return this.state.expandedId === projectId;
    }

    // === ACTIONS ===

    async viewDocuments(projectId, ev) {
        ev.stopPropagation();
        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Construction Documents',
            res_model: 'ir.attachment',
            view_mode: 'kanban,list',
            domain: [['res_model', '=', 'cc.opportunity'], ['res_id', '=', projectId]],
            context: { default_res_model: 'cc.opportunity', default_res_id: projectId },
        });
    }

    async fetchData(projectId, ev) {
        ev.stopPropagation();
        await this.orm.call("cc.opportunity", "action_fetch_cc_data", [[projectId]]);
        await this._loadProjects();
    }

    async openForm(projectId, ev) {
        ev.stopPropagation();
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'cc.opportunity',
            res_id: projectId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    // === FORMATTING ===

    formatLocation(project) {
        const parts = [project.city, project.state_id].filter(Boolean);
        return parts.join(', ') || '—';
    }

    formatDate(dateStr) {
        if (!dateStr) return '—';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    formatCurrency(value) {
        if (!value) return '—';
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
    }

    getStatusClass(state) {
        return `cc_status_badge ${state || 'new'}`;
    }

    getStatusLabel(state) {
        const labels = {
            'new': 'New',
            'fetching': 'Fetching...',
            'ready': 'Ready',
            'bidding': 'Bidding',
            'won': 'Won',
            'lost': 'Lost',
        };
        return labels[state] || state;
    }
}

// Register the client action
registry.category("actions").add("cc_ops_dashboard", CCOpsDashboard);

export default CCOpsDashboard;
