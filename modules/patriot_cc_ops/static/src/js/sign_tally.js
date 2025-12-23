/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

/**
 * Sign Tally - Full page sign counter with auto-fill
 */
export class SignTally extends Component {
    static template = "patriot_cc_ops.SignTally";
    static props = {
        ...standardActionServiceProps,
        opportunityId: { type: Number, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        const actionParams = this.props.action?.params || {};
        this.opportunityId = actionParams.opportunityId || this.props.opportunityId;

        this.state = useState({
            signTypes: [],
            opportunity: null,
            attachments: [],
            isLoading: true,

            // Add Modal
            showAddModal: false,
            newSignType: {
                name: "",
                length: 0,
                width: 0,
                has_window: false,
                notes: "",
            },
            isAutoFilled: false,

            // Edit Modal
            showEditModal: false,
            editingSignType: null,
        });

        onMounted(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.isLoading = true;
        try {
            if (this.opportunityId) {
                const opps = await this.orm.read("cc.opportunity", [this.opportunityId], ["name", "document_ids"]);
                if (opps.length > 0) {
                    this.state.opportunity = opps[0];

                    if (opps[0].document_ids?.length > 0) {
                        const attachments = await this.orm.read("ir.attachment", opps[0].document_ids, ["name", "mimetype"]);
                        this.state.attachments = attachments.filter(a =>
                            a.mimetype === "application/pdf" || a.name?.toLowerCase().endsWith(".pdf")
                        );
                    }
                }
                await this.loadSignTypes();
            }
        } catch (error) {
            console.error("Failed to load data:", error);
            this.notification.add("Failed to load data", { type: "danger" });
        }
        this.state.isLoading = false;
    }

    async loadSignTypes() {
        const signTypes = await this.orm.searchRead(
            "cc.sign.type",
            [["opportunity_id", "=", this.opportunityId]],
            ["name", "quantity", "length", "width", "dimensions", "has_window", "material", "mounting", "notes"],
            { order: "name ASC" }
        );
        this.state.signTypes = signTypes;
    }

    // ==================== Quantity Controls ====================

    async incrementQuantity(signType) {
        await this.orm.write("cc.sign.type", [signType.id], {
            quantity: (signType.quantity || 0) + 1
        });
        signType.quantity = (signType.quantity || 0) + 1;
    }

    async decrementQuantity(signType) {
        if (signType.quantity > 0) {
            await this.orm.write("cc.sign.type", [signType.id], {
                quantity: signType.quantity - 1
            });
            signType.quantity = signType.quantity - 1;
        }
    }

    // ==================== Add Modal ====================

    openAddModal() {
        this.state.newSignType = { name: "", length: 0, width: 0, has_window: false, notes: "" };
        this.state.isAutoFilled = false;
        this.state.showAddModal = true;
    }

    closeAddModal() {
        this.state.showAddModal = false;
    }

    async onNewNameInput(ev) {
        const name = ev.target.value;
        this.state.newSignType.name = name;

        // Auto-fill: check if this sign type name already exists in the project
        if (name.trim()) {
            const existing = this.state.signTypes.find(st =>
                st.name.toLowerCase() === name.toLowerCase()
            );
            if (existing) {
                this.state.newSignType.length = existing.length || 0;
                this.state.newSignType.width = existing.width || 0;
                this.state.newSignType.has_window = existing.has_window || false;
                this.state.isAutoFilled = true;
            } else {
                this.state.isAutoFilled = false;
            }
        }
    }

    onNewLengthInput(ev) {
        this.state.newSignType.length = parseFloat(ev.target.value) || 0;
    }

    onNewWidthInput(ev) {
        this.state.newSignType.width = parseFloat(ev.target.value) || 0;
    }

    onNewWindowChange(ev) {
        this.state.newSignType.has_window = ev.target.checked;
    }

    onNewNotesInput(ev) {
        this.state.newSignType.notes = ev.target.value;
    }

    async saveNewSignType() {
        if (!this.state.newSignType.name.trim()) {
            this.notification.add("Please enter a Sign ID", { type: "warning" });
            return;
        }

        try {
            await this.orm.create("cc.sign.type", [{
                name: this.state.newSignType.name.trim(),
                length: this.state.newSignType.length,
                width: this.state.newSignType.width,
                has_window: this.state.newSignType.has_window,
                notes: this.state.newSignType.notes,
                quantity: 1,
                opportunity_id: this.opportunityId,
            }]);

            this.notification.add(`Added "${this.state.newSignType.name}"`, { type: "success" });
            this.closeAddModal();
            await this.loadSignTypes();
        } catch (error) {
            console.error("Failed to create sign type:", error);
            this.notification.add("Failed to add sign type: " + (error.message || "Unknown error"), { type: "danger" });
        }
    }

    // ==================== Edit Modal ====================

    openEditModal(signType) {
        this.state.editingSignType = { ...signType };
        this.state.showEditModal = true;
    }

    closeEditModal() {
        this.state.showEditModal = false;
        this.state.editingSignType = null;
    }

    onEditNameInput(ev) {
        this.state.editingSignType.name = ev.target.value;
    }

    onEditLengthInput(ev) {
        this.state.editingSignType.length = parseFloat(ev.target.value) || 0;
    }

    onEditWidthInput(ev) {
        this.state.editingSignType.width = parseFloat(ev.target.value) || 0;
    }

    onEditWindowChange(ev) {
        this.state.editingSignType.has_window = ev.target.checked;
    }

    onEditMaterialInput(ev) {
        this.state.editingSignType.material = ev.target.value;
    }

    onEditMountingInput(ev) {
        this.state.editingSignType.mounting = ev.target.value;
    }

    onEditNotesInput(ev) {
        this.state.editingSignType.notes = ev.target.value;
    }

    async saveEditSignType() {
        if (!this.state.editingSignType.name?.trim()) {
            this.notification.add("Please enter a Sign ID", { type: "warning" });
            return;
        }

        try {
            await this.orm.write("cc.sign.type", [this.state.editingSignType.id], {
                name: this.state.editingSignType.name.trim(),
                length: this.state.editingSignType.length,
                width: this.state.editingSignType.width,
                has_window: this.state.editingSignType.has_window,
                material: this.state.editingSignType.material,
                mounting: this.state.editingSignType.mounting,
                notes: this.state.editingSignType.notes,
            });

            this.notification.add("Sign type updated", { type: "success" });
            this.closeEditModal();
            await this.loadSignTypes();
        } catch (error) {
            console.error("Failed to update:", error);
            this.notification.add("Failed to update", { type: "danger" });
        }
    }

    async deleteSignType() {
        if (!this.state.editingSignType) return;

        try {
            await this.orm.unlink("cc.sign.type", [this.state.editingSignType.id]);
            this.notification.add("Sign type deleted", { type: "success" });
            this.closeEditModal();
            await this.loadSignTypes();
        } catch (error) {
            console.error("Failed to delete:", error);
            this.notification.add("Failed to delete", { type: "danger" });
        }
    }

    // ==================== Actions ====================

    async openDocuments() {
        for (const att of this.state.attachments) {
            const url = `/web/content/${att.id}`;
            window.open(url, "_blank");
        }
    }

    async exportToExcel() {
        if (!this.opportunityId) return;

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cc.opportunity",
            res_id: this.opportunityId,
            views: [[false, "form"]],
            target: "current",
        });
        // Trigger export from the opportunity
        setTimeout(() => {
            window.location.href = `/web/content/cc.opportunity/${this.opportunityId}/export_sign_schedule`;
        }, 100);
    }

    goBack() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cc.opportunity",
            res_id: this.opportunityId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ==================== Computed ====================

    get totalSigns() {
        return this.state.signTypes.reduce((sum, st) => sum + (st.quantity || 0), 0);
    }
}

registry.category("actions").add("cc_ops_sign_tally", SignTally);
