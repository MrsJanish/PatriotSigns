/** @odoo-module **/

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

/**
 * Sign Tally - Compact popup for counting signs
 * 
 * Simple +/- counter for each sign type
 * Quick add modal with minimal fields
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
            // Data
            signTypes: [],
            opportunity: null,
            attachments: [],
            isLoading: true,

            // Quick Add Modal
            showAddModal: false,
            newSignType: {
                name: "",
                dimensions: "",
                notes: "",
            },

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
            // Load opportunity info
            if (this.opportunityId) {
                const opps = await this.orm.read("cc.opportunity", [this.opportunityId], ["name", "document_ids"]);
                if (opps.length > 0) {
                    this.state.opportunity = opps[0];

                    // Load attachments
                    if (opps[0].document_ids?.length > 0) {
                        const attachments = await this.orm.read("ir.attachment", opps[0].document_ids, ["name", "mimetype", "file_size"]);
                        this.state.attachments = attachments.filter(a =>
                            a.mimetype === "application/pdf" || a.name?.toLowerCase().endsWith(".pdf")
                        );
                    }
                }

                // Load sign types
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
            ["name", "quantity", "dimensions", "material", "mounting", "notes"],
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

    // ==================== Quick Add Modal ====================

    openAddModal() {
        this.state.newSignType = { name: "", dimensions: "", notes: "" };
        this.state.showAddModal = true;
    }

    closeAddModal() {
        this.state.showAddModal = false;
    }

    onNewNameInput(ev) {
        this.state.newSignType.name = ev.target.value;
    }

    onNewDimensionsInput(ev) {
        this.state.newSignType.dimensions = ev.target.value;
    }

    onNewNotesInput(ev) {
        this.state.newSignType.notes = ev.target.value;
    }

    async saveNewSignType() {
        if (!this.state.newSignType.name) {
            this.notification.add("Please enter a Sign ID", { type: "warning" });
            return;
        }

        try {
            await this.orm.create("cc.sign.type", {
                name: this.state.newSignType.name,
                dimensions: this.state.newSignType.dimensions,
                notes: this.state.newSignType.notes,
                quantity: 1,
                opportunity_id: this.opportunityId,
            });

            this.notification.add(`Added "${this.state.newSignType.name}"`, { type: "success" });
            this.closeAddModal();
            await this.loadSignTypes();
        } catch (error) {
            console.error("Failed to create sign type:", error);
            this.notification.add("Failed to add sign type", { type: "danger" });
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

    onEditDimensionsInput(ev) {
        this.state.editingSignType.dimensions = ev.target.value;
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
        if (!this.state.editingSignType.name) {
            this.notification.add("Please enter a Sign ID", { type: "warning" });
            return;
        }

        try {
            await this.orm.write("cc.sign.type", [this.state.editingSignType.id], {
                name: this.state.editingSignType.name,
                dimensions: this.state.editingSignType.dimensions,
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
        // Open each PDF attachment in new tab
        for (const att of this.state.attachments) {
            const url = `/web/content/${att.id}?download=true`;
            window.open(url, "_blank");
        }
    }

    async exportToExcel() {
        if (!this.opportunityId) return;

        // Trigger the export action on the opportunity
        window.location.href = `/web/content/cc.opportunity/${this.opportunityId}/export_sign_schedule`;
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

// Register as action
registry.category("actions").add("cc_ops_sign_tally", SignTally);
