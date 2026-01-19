/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Auto Time Tracker Component
 * 
 * Monitors which project/opportunity the user is viewing and automatically
 * switches their time tracking to that record.
 * 
 * Features:
 * - 30 second debounce to prevent micro-punches
 * - Only tracks project.project and crm.lead models
 * - Respects per-employee auto_time_tracking setting
 */
class AutoTimeTracker extends Component {
    static template = "patriot_timeclock.AutoTimeTracker";

    setup() {
        this.orm = useService("orm");
        this.router = useService("router");
        this.notification = useService("notification");

        this.state = useState({
            currentModel: null,
            currentRecordId: null,
            isTracking: false,
        });

        this.debounceTimer = null;
        this.DEBOUNCE_MS = 30000; // 30 seconds

        // Track supported models
        this.trackableModels = ['project.project', 'crm.lead'];

        onMounted(() => {
            this.startListening();
        });

        onWillUnmount(() => {
            this.stopListening();
        });
    }

    startListening() {
        // Listen for URL changes (route changes)
        this._onHashChange = this.onHashChange.bind(this);
        window.addEventListener('hashchange', this._onHashChange);

        // Also check current URL on mount
        this.checkCurrentUrl();
    }

    stopListening() {
        window.removeEventListener('hashchange', this._onHashChange);
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
    }

    onHashChange() {
        this.checkCurrentUrl();
    }

    checkCurrentUrl() {
        // Parse the current URL to detect model and record
        const hash = window.location.hash;

        // Look for patterns like #model=project.project&id=123 or action URLs
        const modelMatch = hash.match(/model=([^&]+)/);
        const idMatch = hash.match(/[&?]id=(\d+)/);

        if (modelMatch && idMatch) {
            const model = modelMatch[1];
            const recordId = parseInt(idMatch[1], 10);

            if (this.trackableModels.includes(model)) {
                this.scheduleSwitch(model, recordId);
            }
        }
    }

    scheduleSwitch(model, recordId) {
        // Don't schedule if we're already on this record
        if (this.state.currentModel === model && this.state.currentRecordId === recordId) {
            return;
        }

        // Clear any pending switch
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Schedule the switch after debounce period
        this.debounceTimer = setTimeout(() => {
            this.executeSwitch(model, recordId);
        }, this.DEBOUNCE_MS);
    }

    async executeSwitch(model, recordId) {
        try {
            const result = await this.orm.call(
                'ps.time.punch',
                'auto_switch_to_record',
                [model, recordId]
            );

            if (result.success) {
                this.state.currentModel = model;
                this.state.currentRecordId = recordId;
                this.state.isTracking = true;

                if (result.action === 'switched') {
                    this.notification.add(
                        `Time tracking switched to viewed record`,
                        { type: 'info', sticky: false }
                    );
                } else if (result.action === 'started') {
                    this.notification.add(
                        `Auto time tracking started`,
                        { type: 'success', sticky: false }
                    );
                }
                // 'already_on_record' - no notification needed
            }
            // If not success, silently ignore (disabled or no employee)
        } catch (error) {
            console.error('Auto time tracking error:', error);
        }
    }
}

AutoTimeTracker.template = owl.xml`
    <div class="o_auto_time_tracker" style="display: none;">
        <!-- Hidden component, just runs in background -->
    </div>
`;

// Register as a systray item so it's always loaded
registry.category("systray").add("AutoTimeTracker", {
    Component: AutoTimeTracker,
    sequence: 1000, // Load early
});

export default AutoTimeTracker;
