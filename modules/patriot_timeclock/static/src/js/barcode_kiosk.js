/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Barcode Time Clock Kiosk
 * 
 * Simple single-scan: employee scans project barcode from their phone.
 * System knows who they are from their Odoo login.
 */
class BarcodeKiosk extends Component {
    static template = "patriot_timeclock.BarcodeKiosk";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            mode: 'ready', // ready, success, error
            currentProject: null,
            message: 'Scan PROJECT barcode',
            subMessage: '',
            barcodeBuffer: '',
        });

        this.resetTimeout = null;

        onMounted(() => {
            this.startListening();
            this.loadCurrentStatus();
        });

        onWillUnmount(() => {
            this.stopListening();
        });
    }

    async loadCurrentStatus() {
        // Check if user is currently clocked in somewhere
        try {
            const punches = await this.orm.searchRead(
                'ps.time.punch',
                [['user_id', '=', this.env.services.user.userId], ['state', '=', 'active']],
                ['project_id', 'punch_in'],
                { limit: 1 }
            );

            if (punches.length > 0) {
                const punch = punches[0];
                this.state.currentProject = punch.project_id ? punch.project_id[1] : null;
                this.state.subMessage = `Currently: ${this.state.currentProject || 'Unknown project'}`;
            }
        } catch (e) {
            console.log('Could not load current status');
        }
    }

    startListening() {
        this._onKeyDown = this.onKeyDown.bind(this);
        document.addEventListener('keydown', this._onKeyDown);

        this._bufferClear = setInterval(() => {
            if (this.state.barcodeBuffer && Date.now() - this._lastKeyTime > 100) {
                this.state.barcodeBuffer = '';
            }
        }, 200);

        this._lastKeyTime = Date.now();
    }

    stopListening() {
        document.removeEventListener('keydown', this._onKeyDown);
        if (this._bufferClear) clearInterval(this._bufferClear);
        if (this.resetTimeout) clearTimeout(this.resetTimeout);
    }

    onKeyDown(event) {
        this._lastKeyTime = Date.now();

        if (event.key === 'Enter') {
            if (this.state.barcodeBuffer.length > 0) {
                this.processBarcode(this.state.barcodeBuffer);
                this.state.barcodeBuffer = '';
            }
            event.preventDefault();
            return;
        }

        if (event.key.length === 1) {
            this.state.barcodeBuffer += event.key;
            event.preventDefault();
        }
    }

    async processBarcode(barcode) {
        try {
            const result = await this.orm.call(
                'ps.time.punch',
                'barcode_scan_project',
                [barcode]
            );

            if (result.success) {
                this.state.mode = 'success';
                this.state.currentProject = result.project_name;

                if (result.action === 'switched') {
                    this.state.message = `✅ Switched to ${result.project_name}`;
                    this.state.subMessage = `From: ${result.previous_project}`;
                } else if (result.action === 'already_clocked_in') {
                    this.state.message = `Already on ${result.project_name}`;
                    this.state.subMessage = '';
                } else {
                    this.state.message = `✅ Clocked into ${result.project_name}`;
                    this.state.subMessage = '';
                }

                this.playSound('success');
            } else {
                this.state.mode = 'error';
                this.state.message = `❌ ${result.message}`;
                this.state.subMessage = '';
                this.playSound('error');
            }

            this.scheduleReset(3000);

        } catch (error) {
            this.state.mode = 'error';
            this.state.message = '❌ Error processing barcode';
            this.state.subMessage = '';
            this.playSound('error');
            this.scheduleReset(3000);
            console.error(error);
        }
    }

    scheduleReset(ms) {
        if (this.resetTimeout) clearTimeout(this.resetTimeout);
        this.resetTimeout = setTimeout(() => this.reset(), ms);
    }

    reset() {
        this.state.mode = 'ready';
        this.state.message = 'Scan PROJECT barcode';
        this.state.subMessage = this.state.currentProject
            ? `Currently: ${this.state.currentProject}`
            : '';
    }

    playSound(type) {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = type === 'success' ? 800 : 300;
            gain.gain.value = 0.3;
            osc.start();
            osc.stop(ctx.currentTime + 0.15);
        } catch (e) { }
    }
}

BarcodeKiosk.template = owl.xml`
<div class="barcode-kiosk" t-att-class="state.mode">
    <div class="kiosk-header">
        <h1>🏭 OMEGA TIME CLOCK</h1>
    </div>
    
    <div class="kiosk-body">
        <div class="kiosk-message" t-esc="state.message"/>
        <div class="kiosk-sub" t-if="state.subMessage" t-esc="state.subMessage"/>
    </div>
    
    <div class="kiosk-footer">
        <div class="kiosk-time" t-esc="new Date().toLocaleTimeString()"/>
    </div>
</div>
`;

BarcodeKiosk.props = {};

registry.category("actions").add("barcode_kiosk", BarcodeKiosk);

export default BarcodeKiosk;
