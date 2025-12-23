/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

/**
 * PDF Viewer Component v2.0 - Complete Overhaul
 * 
 * Features:
 * - Glassmorphism UI matching CC Ops Dashboard
 * - Drag-drop split view panels
 * - Lasso bookmark tool (polygon selection)
 * - Sign type management
 * - Text search within document
 * - Proper PDF rendering with fit-to-width
 */
export class PDFViewer extends Component {
    static template = "patriot_cc_ops.PDFViewer";
    static props = {
        ...standardActionServiceProps,
        attachmentId: { type: Number, optional: true },
        opportunityId: { type: Number, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        // Get params from action
        const actionParams = this.props.action?.params || {};
        this.opportunityId = actionParams.opportunityId || this.props.opportunityId;
        this.initialAttachmentId = actionParams.attachmentId || this.props.attachmentId;
        this.goToPage = actionParams.goToPage || null;

        this.state = useState({
            // Theme
            theme: "aurora-theme", // or "" for light

            // PDF state
            pdfDoc: null,
            currentPage: 1,
            totalPages: 0,
            scale: 1.0,
            zoomPercent: "100%",
            isLoading: true,
            error: null,

            // View state
            isFullscreen: false,
            isSplitView: false,

            // Split view panels
            leftPanel: {
                attachment: null,
                pdfDoc: null,
                currentPage: 1,
                totalPages: 0,
            },
            rightPanel: {
                attachment: null,
                pdfDoc: null,
                currentPage: 1,
                totalPages: 0,
            },
            dragOverLeft: false,
            dragOverRight: false,

            // Attachments
            attachments: [],
            selectedAttachment: null,
            filterText: "",
            filteredAttachments: [],

            // Search
            searchText: "",
            searchResults: [],
            currentSearchIndex: 0,

            // Lasso/Bookmark
            isLassoMode: false,
            lassoPoints: [],
            isDrawingLasso: false,
            bookmarks: [],
            showBookmarkMenu: false,
            bookmarkMenuX: 0,
            bookmarkMenuY: 0,
            selectedBookmark: null,
            selectedBookmarkId: null,

            // Sign Types
            signTypes: [],
            showSignTypeModal: false,
            editingSignType: null,
            signTypeForm: {
                name: "",
                description: "",
                quantity: 1,
                dimensions: "",
                material: "",
                mounting: "",
                notes: "",
            },

            // Pending bookmark (lasso just completed, waiting for sign type assignment)
            pendingBookmark: null,
        });

        // Canvas refs
        this.canvasRef = useRef("pdfCanvas");
        this.containerRef = useRef("viewerContainer");
        this.contentAreaRef = useRef("contentArea");
        this.canvasContainerRef = useRef("canvasContainer");
        this.lassoCanvasRef = useRef("lassoCanvas");
        this.bookmarkOverlayRef = useRef("bookmarkOverlay");
        this.leftCanvasRef = useRef("leftCanvas");
        this.rightCanvasRef = useRef("rightCanvas");

        // PDF.js library
        this.pdfjsLib = null;

        // Render queue for smooth updates
        this.renderTask = null;

        // ResizeObserver for proper canvas sizing
        this.resizeObserver = null;
        this._lastContainerWidth = 0;

        onMounted(async () => {
            // Wait for DOM to be fully ready before measuring
            await new Promise(resolve => setTimeout(resolve, 150));

            // Set up ResizeObserver for responsive canvas sizing
            if (this.contentAreaRef.el) {
                // Force initial measurement
                this._lastContainerWidth = this.contentAreaRef.el.clientWidth - 80;
                if (this._lastContainerWidth < 400) {
                    this._lastContainerWidth = 900; // Sensible default for construction drawings
                }

                this.resizeObserver = new ResizeObserver((entries) => {
                    for (const entry of entries) {
                        const newWidth = entry.contentRect.width - 80;
                        if (Math.abs(newWidth - this._lastContainerWidth) > 50 && newWidth > 100) {
                            this._lastContainerWidth = newWidth;
                            if (this.state.pdfDoc && !this.state.isLoading) {
                                this.renderPage(this.state.currentPage);
                            }
                        }
                    }
                });
                this.resizeObserver.observe(this.contentAreaRef.el);
            } else {
                // Fallback if contentAreaRef not available
                this._lastContainerWidth = 900;
            }

            await this.loadPDFJS();
            if (this.opportunityId) {
                await this.loadAttachments();
                await this.loadSignTypes();
            }
        });

        onPatched(() => {
            // Re-render bookmarks when state changes
            if (this.state.pdfDoc && !this.state.isLoading) {
                this.renderBookmarks();
            }
        });

        // Store bound reference for cleanup
        this._boundDocClick = this.handleDocumentClick.bind(this);
        this._boundKeyDown = this.handleKeyDown.bind(this);
        document.addEventListener("click", this._boundDocClick);
        document.addEventListener("keydown", this._boundKeyDown);

        onWillUnmount(() => {
            // Remove global event listeners to prevent memory leak
            document.removeEventListener("click", this._boundDocClick);
            document.removeEventListener("keydown", this._boundKeyDown);

            // Stop ResizeObserver
            if (this.resizeObserver) {
                this.resizeObserver.disconnect();
            }

            if (this.renderTask) {
                this.renderTask.cancel?.();
            }
            if (this.state.pdfDoc) {
                try {
                    this.state.pdfDoc.destroy?.();
                } catch (e) {
                    // Ignore destroy errors on unmount
                }
            }
        });
    }

    // Keyboard navigation handler
    handleKeyDown(ev) {
        // Only handle if not in an input field
        if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA') {
            return;
        }

        switch (ev.key) {
            case 'ArrowLeft':
            case 'ArrowUp':
                ev.preventDefault();
                this.prevPage();
                break;
            case 'ArrowRight':
            case 'ArrowDown':
                ev.preventDefault();
                this.nextPage();
                break;
            case '+':
            case '=':
                ev.preventDefault();
                this.zoomIn();
                break;
            case '-':
                ev.preventDefault();
                this.zoomOut();
                break;
            case 'Escape':
                if (this.state.isLassoMode) {
                    this.state.isLassoMode = false;
                    this.state.lassoPoints = [];
                    this.clearLassoCanvas();
                }
                if (this.state.showSignTypeModal) {
                    this.closeSignTypeModal();
                }
                break;
        }
    }

    handleDocumentClick(ev) {
        if (this.state.showBookmarkMenu) {
            this.state.showBookmarkMenu = false;
        }
    }

    // ==================== PDF.js Loading ====================

    async loadPDFJS() {
        if (window.pdfjsLib) {
            this.pdfjsLib = window.pdfjsLib;
            return true;
        }

        try {
            await this.loadScript("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js");
            window.pdfjsLib.GlobalWorkerOptions.workerSrc =
                "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
            this.pdfjsLib = window.pdfjsLib;
            return true;
        } catch (error) {
            console.error("Failed to load PDF.js:", error);
            this.state.error = "Failed to load PDF viewer library";
            this.state.isLoading = false;
            return false;
        }
    }

    loadScript(src) {
        return new Promise((resolve, reject) => {
            const existing = document.querySelector(`script[src="${src}"]`);
            if (existing) {
                resolve();
                return;
            }
            const script = document.createElement("script");
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    // ==================== Data Loading ====================

    async loadAttachments() {
        try {
            const result = await this.orm.searchRead(
                "ir.attachment",
                [
                    ["res_model", "=", "cc.opportunity"],
                    ["res_id", "=", this.opportunityId],
                    ["mimetype", "=", "application/pdf"],
                ],
                ["id", "name", "file_size"],
                { order: "name asc" }
            );

            this.state.attachments = result;
            this.state.filteredAttachments = result;
            this.state.isLoading = false;

            // Auto-load attachment if specified
            if (result.length > 0) {
                if (this.initialAttachmentId) {
                    const target = result.find(a => a.id === this.initialAttachmentId);
                    if (target) {
                        await this.openAttachment(target);
                        if (this.goToPage) {
                            this.goToPageNumber(this.goToPage);
                        }
                        return;
                    }
                }
                // Otherwise load first
                await this.openAttachment(result[0]);
            }
        } catch (error) {
            console.error("Failed to load attachments:", error);
            this.state.error = "Failed to load documents";
            this.state.isLoading = false;
        }
    }

    async loadSignTypes() {
        try {
            const result = await this.orm.searchRead(
                "cc.sign.type",
                [["opportunity_id", "=", this.opportunityId]],
                ["id", "name", "quantity", "dimensions", "material", "mounting", "notes", "description", "bookmark_count"],
                { order: "name asc" }
            );

            // Assign colors to sign types
            const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4"];
            this.state.signTypes = result.map((st, i) => ({
                ...st,
                color: colors[i % colors.length],
            }));
        } catch (error) {
            console.log("No sign types found or model not ready");
            this.state.signTypes = [];
        }
    }

    async loadBookmarks(attachmentId) {
        try {
            const result = await this.orm.searchRead(
                "cc.sign.bookmark",
                [["attachment_id", "=", attachmentId]],
                ["id", "page_number", "x_position", "y_position", "path_data", "highlight_color", "sign_type_id"]
            );

            this.state.bookmarks = result.map(b => ({
                id: b.id,
                pageNumber: b.page_number,
                x: b.x_position,
                y: b.y_position,
                pathData: b.path_data ? JSON.parse(b.path_data) : null,
                color: b.highlight_color || "#f59e0b",
                signTypeId: b.sign_type_id?.[0],
                signTypeName: b.sign_type_id?.[1],
            }));

            this.renderBookmarks();
        } catch (error) {
            console.log("No bookmarks found");
            this.state.bookmarks = [];
        }
    }

    // ==================== Attachment Handling ====================

    filterAttachments() {
        const filter = this.state.filterText.toLowerCase();
        if (!filter) {
            this.state.filteredAttachments = this.state.attachments;
        } else {
            this.state.filteredAttachments = this.state.attachments.filter(
                a => a.name.toLowerCase().includes(filter)
            );
        }
    }

    onFilterChange(ev) {
        this.state.filterText = ev.target.value;
        this.filterAttachments();
    }

    onAttachmentSelect(ev) {
        const attachmentId = parseInt(ev.target.value, 10);
        if (attachmentId) {
            const att = this.state.attachments.find(a => a.id === attachmentId);
            if (att) this.openAttachment(att);
        }
    }

    async openAttachment(attachment) {
        if (!this.pdfjsLib) {
            console.error("PDF.js not loaded");
            return;
        }

        this.state.selectedAttachment = attachment;
        this.state.isLoading = true;
        this.state.error = null;

        try {
            const response = await this.orm.read("ir.attachment", [attachment.id], ["datas"]);

            if (!response?.[0]?.datas) {
                throw new Error("No PDF data returned");
            }

            const pdfData = atob(response[0].datas);
            const pdfArray = new Uint8Array(pdfData.split("").map(c => c.charCodeAt(0)));

            const loadingTask = this.pdfjsLib.getDocument({ data: pdfArray });
            const pdfDoc = await loadingTask.promise;

            // Cleanup old doc safely (may fail due to PDF.js version conflicts)
            if (this.state.pdfDoc) {
                try {
                    this.state.pdfDoc.destroy();
                } catch (e) {
                    console.log("Could not destroy old PDF (safe to ignore):", e.message);
                }
                this.state.pdfDoc = null;
            }

            this.state.pdfDoc = pdfDoc;
            this.state.totalPages = pdfDoc.numPages;
            this.state.currentPage = 1;
            this.state.isLoading = false;

            // Wait for DOM then render
            await new Promise(resolve => setTimeout(resolve, 50));
            await this.renderPage(1);
            await this.loadBookmarks(attachment.id);

        } catch (error) {
            console.error("Failed to open PDF:", error);
            this.state.error = "Failed to open PDF: " + error.message;
            this.state.isLoading = false;
        }
    }

    // ==================== Rendering ====================

    async renderPage(pageNum, canvas = null, pdfDoc = null, retryCount = 0) {
        const doc = pdfDoc || this.state.pdfDoc;
        if (!doc) {
            console.warn("No PDF document loaded");
            return;
        }

        const canvasEl = canvas || this.canvasRef.el;

        // If canvas not ready, retry up to 5 times
        if (!canvasEl) {
            if (retryCount < 5) {
                console.log(`Canvas not ready, retry ${retryCount + 1}/5...`);
                await new Promise(resolve => setTimeout(resolve, 100));
                return this.renderPage(pageNum, canvas, pdfDoc, retryCount + 1);
            } else {
                console.error("Canvas never became available");
                return;
            }
        }

        try {
            const page = await doc.getPage(pageNum);

            // Get container width using cached value from ResizeObserver
            let containerWidth = this._lastContainerWidth;
            if (!containerWidth || containerWidth < 400) {
                // Fallback measurement
                if (this.contentAreaRef.el) {
                    containerWidth = this.contentAreaRef.el.clientWidth - 80;
                }
                if (!containerWidth || containerWidth < 400) {
                    containerWidth = 900; // Good default for construction drawings
                }
                this._lastContainerWidth = containerWidth;
            }

            // Calculate scale to fit
            const baseViewport = page.getViewport({ scale: 1.0 });
            let scale;

            if (this.state.scale === 1.0) {
                // Auto-fit to width
                scale = Math.min(containerWidth / baseViewport.width, 2.0);
                scale = Math.max(scale, 0.5); // Minimum scale
            } else {
                scale = this.state.scale;
            }

            const viewport = page.getViewport({ scale });

            // Set canvas dimensions
            canvasEl.width = viewport.width;
            canvasEl.height = viewport.height;

            // Also set CSS dimensions to match
            canvasEl.style.width = viewport.width + 'px';
            canvasEl.style.height = viewport.height + 'px';

            const context = canvasEl.getContext("2d");

            // Clear canvas first
            context.clearRect(0, 0, canvasEl.width, canvasEl.height);

            // Cancel any existing render
            if (this.renderTask) {
                try {
                    this.renderTask.cancel();
                } catch (e) {
                    // Ignore cancel errors
                }
            }

            const renderContext = {
                canvasContext: context,
                viewport: viewport
            };

            this.renderTask = page.render(renderContext);
            await this.renderTask.promise;

            // Update scale display
            this.state.scale = scale;
            this.state.zoomPercent = Math.round(scale * 100) + "%";

            // Render overlays
            this.renderBookmarks();
            this.setupLassoCanvas();

        } catch (error) {
            if (error.name !== "RenderingCancelledException") {
                console.error("Failed to render page:", error);
            }
        }
    }

    // ==================== Page Navigation ====================

    prevPage() {
        if (this.state.currentPage > 1) {
            this.state.currentPage--;
            this.renderPage(this.state.currentPage);
        }
    }

    nextPage() {
        if (this.state.currentPage < this.state.totalPages) {
            this.state.currentPage++;
            this.renderPage(this.state.currentPage);
        }
    }

    goToPageNumber(pageNum) {
        if (pageNum >= 1 && pageNum <= this.state.totalPages) {
            this.state.currentPage = pageNum;
            this.renderPage(this.state.currentPage);
        }
    }

    onPageInputChange(ev) {
        const page = parseInt(ev.target.value, 10);
        if (!isNaN(page)) {
            this.goToPageNumber(page);
        }
    }

    // ==================== Zoom ====================

    zoomIn() {
        this.state.scale = Math.min(this.state.scale + 0.25, 4.0);
        this.state.zoomPercent = Math.round(this.state.scale * 100) + "%";
        this.renderPage(this.state.currentPage);
    }

    zoomOut() {
        this.state.scale = Math.max(this.state.scale - 0.25, 0.25);
        this.state.zoomPercent = Math.round(this.state.scale * 100) + "%";
        this.renderPage(this.state.currentPage);
    }

    fitToWidth() {
        this.state.scale = 1.0; // Will auto-calculate in renderPage
        this.renderPage(this.state.currentPage);
    }

    // ==================== View Controls ====================

    toggleFullscreen() {
        const container = this.containerRef.el;
        if (!document.fullscreenElement) {
            container.requestFullscreen?.();
            this.state.isFullscreen = true;
        } else {
            document.exitFullscreen?.();
            this.state.isFullscreen = false;
        }
    }

    toggleSplitView() {
        this.state.isSplitView = !this.state.isSplitView;
        if (!this.state.isSplitView) {
            // Cleanup split panels
            this.state.leftPanel = { attachment: null, pdfDoc: null, currentPage: 1, totalPages: 0 };
            this.state.rightPanel = { attachment: null, pdfDoc: null, currentPage: 1, totalPages: 0 };
        }
    }

    retry() {
        this.state.error = null;
        this.state.isLoading = true;
        if (this.state.selectedAttachment) {
            this.openAttachment(this.state.selectedAttachment);
        } else {
            this.loadAttachments();
        }
    }

    // ==================== Drag & Drop ====================

    onAttachmentItemClick(ev) {
        const id = parseInt(ev.currentTarget.dataset.attachmentId, 10);
        const attachment = this.state.attachments.find(a => a.id === id);
        if (attachment) {
            this.openAttachment(attachment);
        }
    }

    onAttachmentDragStart(ev) {
        const id = parseInt(ev.currentTarget.dataset.attachmentId, 10);
        const attachment = this.state.attachments.find(a => a.id === id);
        if (attachment) {
            ev.dataTransfer.setData("application/json", JSON.stringify(attachment));
            ev.dataTransfer.effectAllowed = "copy";
        }
    }

    onDragStart(ev, attachment) {
        ev.dataTransfer.setData("application/json", JSON.stringify(attachment));
        ev.dataTransfer.effectAllowed = "copy";
    }

    onDragEnd(ev) {
        this.state.dragOverLeft = false;
        this.state.dragOverRight = false;
    }

    onDragOverLeft(ev) {
        ev.preventDefault();
        this.state.dragOverLeft = true;
    }

    onDragLeaveLeft(ev) {
        this.state.dragOverLeft = false;
    }

    async onDropLeft(ev) {
        ev.preventDefault();
        this.state.dragOverLeft = false;

        try {
            const attachment = JSON.parse(ev.dataTransfer.getData("application/json"));
            await this.loadPanelPDF("left", attachment);
        } catch (e) {
            console.error("Drop failed:", e);
        }
    }

    onDragOverRight(ev) {
        ev.preventDefault();
        this.state.dragOverRight = true;
    }

    onDragLeaveRight(ev) {
        this.state.dragOverRight = false;
    }

    async onDropRight(ev) {
        ev.preventDefault();
        this.state.dragOverRight = false;

        try {
            const attachment = JSON.parse(ev.dataTransfer.getData("application/json"));
            await this.loadPanelPDF("right", attachment);
        } catch (e) {
            console.error("Drop failed:", e);
        }
    }

    async loadPanelPDF(panel, attachment) {
        const panelState = panel === "left" ? this.state.leftPanel : this.state.rightPanel;
        const canvasRef = panel === "left" ? this.leftCanvasRef : this.rightCanvasRef;

        try {
            const response = await this.orm.read("ir.attachment", [attachment.id], ["datas"]);
            const pdfData = atob(response[0].datas);
            const pdfArray = new Uint8Array(pdfData.split("").map(c => c.charCodeAt(0)));

            const loadingTask = this.pdfjsLib.getDocument({ data: pdfArray });
            const pdfDoc = await loadingTask.promise;

            panelState.attachment = attachment;
            panelState.pdfDoc = pdfDoc;
            panelState.totalPages = pdfDoc.numPages;
            panelState.currentPage = 1;

            // Wait for DOM
            await new Promise(resolve => setTimeout(resolve, 50));
            await this.renderPage(1, canvasRef.el, pdfDoc);

        } catch (error) {
            console.error("Failed to load panel PDF:", error);
            this.notification.add("Failed to load document", { type: "danger" });
        }
    }

    clearLeftPanel() {
        if (this.state.leftPanel.pdfDoc) {
            this.state.leftPanel.pdfDoc.destroy?.();
        }
        this.state.leftPanel = { attachment: null, pdfDoc: null, currentPage: 1, totalPages: 0 };
    }

    clearRightPanel() {
        if (this.state.rightPanel.pdfDoc) {
            this.state.rightPanel.pdfDoc.destroy?.();
        }
        this.state.rightPanel = { attachment: null, pdfDoc: null, currentPage: 1, totalPages: 0 };
    }

    // ==================== Split Panel Navigation ====================

    prevLeftPage() {
        if (this.state.leftPanel.currentPage > 1) {
            this.state.leftPanel.currentPage--;
            this.renderPage(this.state.leftPanel.currentPage, this.leftCanvasRef.el, this.state.leftPanel.pdfDoc);
        }
    }

    nextLeftPage() {
        if (this.state.leftPanel.currentPage < this.state.leftPanel.totalPages) {
            this.state.leftPanel.currentPage++;
            this.renderPage(this.state.leftPanel.currentPage, this.leftCanvasRef.el, this.state.leftPanel.pdfDoc);
        }
    }

    zoomInLeft() {
        // Re-render at larger scale
        this.renderPanelAtScale("left", 1.25);
    }

    zoomOutLeft() {
        this.renderPanelAtScale("left", 0.8);
    }

    prevRightPage() {
        if (this.state.rightPanel.currentPage > 1) {
            this.state.rightPanel.currentPage--;
            this.renderPage(this.state.rightPanel.currentPage, this.rightCanvasRef.el, this.state.rightPanel.pdfDoc);
        }
    }

    nextRightPage() {
        if (this.state.rightPanel.currentPage < this.state.rightPanel.totalPages) {
            this.state.rightPanel.currentPage++;
            this.renderPage(this.state.rightPanel.currentPage, this.rightCanvasRef.el, this.state.rightPanel.pdfDoc);
        }
    }

    zoomInRight() {
        this.renderPanelAtScale("right", 1.25);
    }

    zoomOutRight() {
        this.renderPanelAtScale("right", 0.8);
    }

    async renderPanelAtScale(panel, scaleFactor) {
        const panelState = panel === "left" ? this.state.leftPanel : this.state.rightPanel;
        const canvasRef = panel === "left" ? this.leftCanvasRef : this.rightCanvasRef;

        if (!panelState.pdfDoc || !canvasRef.el) return;

        try {
            const page = await panelState.pdfDoc.getPage(panelState.currentPage);
            const currentViewport = page.getViewport({ scale: 1.0 });

            // Calculate current scale from canvas
            const currentScale = canvasRef.el.width / currentViewport.width || 1.0;
            const newScale = Math.min(Math.max(currentScale * scaleFactor, 0.25), 4.0);

            const viewport = page.getViewport({ scale: newScale });

            canvasRef.el.width = viewport.width;
            canvasRef.el.height = viewport.height;
            canvasRef.el.style.width = viewport.width + 'px';
            canvasRef.el.style.height = viewport.height + 'px';

            const context = canvasRef.el.getContext("2d");
            context.clearRect(0, 0, canvasRef.el.width, canvasRef.el.height);

            await page.render({
                canvasContext: context,
                viewport: viewport
            }).promise;
        } catch (error) {
            console.error("Zoom failed:", error);
        }
    }

    onDividerMouseDown(ev) {
        // TODO: Implement resizable divider
    }

    // ==================== Text Search ====================

    onSearchInput(ev) {
        this.state.searchText = ev.target.value;
    }

    onSearchKeypress(ev) {
        if (ev.key === "Enter") {
            this.performSearch();
        }
    }

    async performSearch() {
        // TODO: Implement PDF text search using pdf.js text layer
        this.notification.add("Search coming soon!", { type: "info" });
    }

    prevSearchResult() {
        if (this.state.currentSearchIndex > 0) {
            this.state.currentSearchIndex--;
        }
    }

    nextSearchResult() {
        if (this.state.currentSearchIndex < this.state.searchResults.length - 1) {
            this.state.currentSearchIndex++;
        }
    }

    // ==================== Lasso Bookmarks ====================

    toggleLassoMode() {
        this.state.isLassoMode = !this.state.isLassoMode;
        this.state.lassoPoints = [];
        this.state.isDrawingLasso = false;
        this.clearLassoCanvas();
    }

    setupLassoCanvas() {
        const pdfCanvas = this.canvasRef.el;
        const lassoCanvas = this.lassoCanvasRef.el;

        if (pdfCanvas && lassoCanvas) {
            lassoCanvas.width = pdfCanvas.width;
            lassoCanvas.height = pdfCanvas.height;
        }
    }

    clearLassoCanvas() {
        const lassoCanvas = this.lassoCanvasRef.el;
        if (lassoCanvas) {
            const ctx = lassoCanvas.getContext("2d");
            ctx.clearRect(0, 0, lassoCanvas.width, lassoCanvas.height);
        }
    }

    onCanvasMouseDown(ev) {
        if (!this.state.isLassoMode) {
            // Check if clicking on a bookmark to select it
            this.checkBookmarkClick(ev);
            return;
        }

        const canvas = this.canvasRef.el;
        const rect = canvas.getBoundingClientRect();
        const x = (ev.clientX - rect.left) / rect.width;
        const y = (ev.clientY - rect.top) / rect.height;

        // Start drawing lasso
        this.state.isDrawingLasso = true;
        this.state.lassoPoints = [{ x, y }];
    }

    onCanvasMouseMove(ev) {
        if (!this.state.isDrawingLasso) return;

        // Throttle to reduce jankiness (only capture every ~10ms)
        const now = Date.now();
        if (this._lastLassoTime && now - this._lastLassoTime < 10) {
            return;
        }
        this._lastLassoTime = now;

        const canvas = this.canvasRef.el;
        const rect = canvas.getBoundingClientRect();
        const x = (ev.clientX - rect.left) / rect.width;
        const y = (ev.clientY - rect.top) / rect.height;

        this.state.lassoPoints.push({ x, y });
        this.drawLasso();
    }

    onCanvasMouseUp(ev) {
        // Complete lasso on mouse up if we have enough points
        if (this.state.isDrawingLasso && this.state.lassoPoints.length >= 3) {
            this.state.isDrawingLasso = false;
            this.completeLasso();
        }
    }

    onCanvasMouseLeave(ev) {
        // Stop drawing but don't complete - user may return
        // this.state.isDrawingLasso = false;
    }

    onCanvasDblClick(ev) {
        if (!this.state.isLassoMode || this.state.lassoPoints.length < 3) {
            return;
        }

        this.state.isDrawingLasso = false;
        this.completeLasso();
    }

    checkBookmarkClick(ev) {
        const canvas = this.canvasRef.el;
        const rect = canvas.getBoundingClientRect();
        const clickX = (ev.clientX - rect.left) / rect.width;
        const clickY = (ev.clientY - rect.top) / rect.height;

        // First check if clicking on a delete button
        if (this.state.selectedBookmarkId) {
            const selectedBookmark = this.state.bookmarks.find(b => b.id === this.state.selectedBookmarkId);
            if (selectedBookmark && selectedBookmark._deleteBtnX !== undefined) {
                const btnDist = Math.sqrt(
                    Math.pow(clickX - selectedBookmark._deleteBtnX, 2) +
                    Math.pow(clickY - selectedBookmark._deleteBtnY, 2)
                );
                if (btnDist < 0.02) { // ~2% of canvas = button radius
                    this.deleteBookmarkById(this.state.selectedBookmarkId);
                    return;
                }
            }
        }

        // Find if click is inside any bookmark
        const pageBookmarks = this.state.bookmarks.filter(
            b => b.pageNumber === this.state.currentPage
        );

        for (const bookmark of pageBookmarks) {
            if (bookmark.pathData && bookmark.pathData.length > 0) {
                // Check if point is inside polygon
                if (this.isPointInPolygon(clickX, clickY, bookmark.pathData)) {
                    // Toggle selection
                    if (this.state.selectedBookmarkId === bookmark.id) {
                        this.state.selectedBookmarkId = null;
                    } else {
                        this.state.selectedBookmarkId = bookmark.id;
                    }
                    this.renderBookmarks();
                    return;
                }
            } else if (bookmark.x !== undefined && bookmark.y !== undefined) {
                // Legacy point bookmark - check distance
                const dist = Math.sqrt(Math.pow(clickX - bookmark.x, 2) + Math.pow(clickY - bookmark.y, 2));
                if (dist < 0.03) { // ~3% of canvas size
                    if (this.state.selectedBookmarkId === bookmark.id) {
                        this.state.selectedBookmarkId = null;
                    } else {
                        this.state.selectedBookmarkId = bookmark.id;
                    }
                    this.renderBookmarks();
                    return;
                }
            }
        }

        // Click outside bookmarks - deselect
        this.state.selectedBookmarkId = null;
        this.renderBookmarks();
    }

    isPointInPolygon(x, y, polygon) {
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i].x, yi = polygon[i].y;
            const xj = polygon[j].x, yj = polygon[j].y;

            if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
                inside = !inside;
            }
        }
        return inside;
    }

    drawLasso() {
        const lassoCanvas = this.lassoCanvasRef.el;
        if (!lassoCanvas) return;

        const ctx = lassoCanvas.getContext("2d");
        ctx.clearRect(0, 0, lassoCanvas.width, lassoCanvas.height);

        if (this.state.lassoPoints.length < 2) return;

        ctx.beginPath();
        ctx.moveTo(
            this.state.lassoPoints[0].x * lassoCanvas.width,
            this.state.lassoPoints[0].y * lassoCanvas.height
        );

        for (let i = 1; i < this.state.lassoPoints.length; i++) {
            ctx.lineTo(
                this.state.lassoPoints[i].x * lassoCanvas.width,
                this.state.lassoPoints[i].y * lassoCanvas.height
            );
        }

        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 3;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.stroke();

        // Draw fill with transparency
        ctx.fillStyle = "rgba(245, 158, 11, 0.2)";
        ctx.closePath();
        ctx.fill();
    }

    completeLasso() {
        // Store pending bookmark
        this.state.pendingBookmark = {
            attachmentId: this.state.selectedAttachment.id,
            pageNumber: this.state.currentPage,
            pathData: [...this.state.lassoPoints],
        };

        // Open sign type dialog
        this.openAddSignTypeDialog();
    }

    // ==================== Bookmark Rendering ====================

    renderBookmarks() {
        const canvas = this.canvasRef.el;
        const overlay = this.bookmarkOverlayRef.el;

        if (!canvas || !overlay) return;

        overlay.width = canvas.width;
        overlay.height = canvas.height;

        const ctx = overlay.getContext("2d");
        ctx.clearRect(0, 0, overlay.width, overlay.height);

        // Filter bookmarks for current page
        const pageBookmarks = this.state.bookmarks.filter(
            b => b.pageNumber === this.state.currentPage
        );

        for (const bookmark of pageBookmarks) {
            if (bookmark.pathData && bookmark.pathData.length > 0) {
                // Draw lasso polygon
                ctx.beginPath();
                ctx.moveTo(
                    bookmark.pathData[0].x * overlay.width,
                    bookmark.pathData[0].y * overlay.height
                );

                for (let i = 1; i < bookmark.pathData.length; i++) {
                    ctx.lineTo(
                        bookmark.pathData[i].x * overlay.width,
                        bookmark.pathData[i].y * overlay.height
                    );
                }

                ctx.closePath();
                ctx.fillStyle = bookmark.color + "33"; // 20% opacity
                ctx.fill();
                ctx.strokeStyle = bookmark.color;
                ctx.lineWidth = 2;
                ctx.stroke();

            } else if (bookmark.x !== undefined && bookmark.y !== undefined) {
                // Legacy point bookmark - draw circle
                const x = bookmark.x * overlay.width;
                const y = bookmark.y * overlay.height;

                ctx.beginPath();
                ctx.arc(x, y, 20, 0, 2 * Math.PI);
                ctx.fillStyle = bookmark.color + "66";
                ctx.fill();
                ctx.strokeStyle = bookmark.color;
                ctx.lineWidth = 3;
                ctx.stroke();
            }

            // Draw X delete button if this bookmark is selected
            if (this.state.selectedBookmarkId === bookmark.id) {
                let btnX, btnY;

                if (bookmark.pathData && bookmark.pathData.length > 0) {
                    // Find top-right corner of bounding box
                    const maxX = Math.max(...bookmark.pathData.map(p => p.x));
                    const minY = Math.min(...bookmark.pathData.map(p => p.y));
                    btnX = maxX * overlay.width + 5;
                    btnY = minY * overlay.height - 5;
                } else {
                    btnX = bookmark.x * overlay.width + 20;
                    btnY = bookmark.y * overlay.height - 20;
                }

                // Draw delete button
                const btnRadius = 14;
                ctx.beginPath();
                ctx.arc(btnX, btnY, btnRadius, 0, 2 * Math.PI);
                ctx.fillStyle = "#ef4444";
                ctx.fill();
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 2;
                ctx.stroke();

                // Draw X
                ctx.beginPath();
                ctx.moveTo(btnX - 5, btnY - 5);
                ctx.lineTo(btnX + 5, btnY + 5);
                ctx.moveTo(btnX + 5, btnY - 5);
                ctx.lineTo(btnX - 5, btnY + 5);
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 2;
                ctx.stroke();

                // Store button position for click detection
                bookmark._deleteBtnX = btnX / overlay.width;
                bookmark._deleteBtnY = btnY / overlay.height;
            }
        }
    }

    async deleteBookmarkById(bookmarkId) {
        try {
            await this.orm.unlink("cc.sign.bookmark", [bookmarkId]);
            this.notification.add("Bookmark deleted", { type: "success" });
            this.state.selectedBookmarkId = null;
            await this.loadBookmarks(this.state.selectedAttachment.id);
            await this.loadSignTypes();
        } catch (error) {
            console.error("Failed to delete bookmark:", error);
            this.notification.add("Failed to delete", { type: "danger" });
        }
    }

    // ==================== Sign Types ====================

    openAddSignTypeDialog() {
        this.state.editingSignType = null;
        this.state.signTypeForm = {
            name: "",
            description: "",
            quantity: 1,
            dimensions: "",
            material: "",
            mounting: "",
            notes: "",
        };
        this.state.showSignTypeModal = true;
    }

    editSignType(signType) {
        this.state.editingSignType = signType;
        this.state.signTypeForm = {
            name: signType.name || "",
            description: signType.description || "",
            quantity: signType.quantity || 1,
            dimensions: signType.dimensions || "",
            material: signType.material || "",
            mounting: signType.mounting || "",
            notes: signType.notes || "",
        };
        this.state.showSignTypeModal = true;
    }

    closeSignTypeModal() {
        this.state.showSignTypeModal = false;
        this.state.editingSignType = null;
        this.state.pendingBookmark = null;
        this.state.lassoPoints = [];
        this.clearLassoCanvas();
    }

    // Event handlers for sign type buttons (from data attributes)
    onGoToSignType(ev) {
        const id = parseInt(ev.currentTarget.dataset.signTypeId, 10);
        const signType = this.state.signTypes.find(s => s.id === id);
        if (signType) {
            this.goToSignType(signType);
        }
    }

    onEditSignType(ev) {
        const id = parseInt(ev.currentTarget.dataset.signTypeId, 10);
        const signType = this.state.signTypes.find(s => s.id === id);
        if (signType) {
            this.editSignType(signType);
        }
    }

    // Form input handlers
    onFormNameInput(ev) {
        this.state.signTypeForm.name = ev.target.value;
    }

    onFormDescriptionInput(ev) {
        this.state.signTypeForm.description = ev.target.value;
    }

    onFormQuantityInput(ev) {
        this.state.signTypeForm.quantity = parseInt(ev.target.value, 10) || 1;
    }

    onFormDimensionsInput(ev) {
        this.state.signTypeForm.dimensions = ev.target.value;
    }

    onFormMaterialInput(ev) {
        this.state.signTypeForm.material = ev.target.value;
    }

    onFormMountingInput(ev) {
        this.state.signTypeForm.mounting = ev.target.value;
    }

    onFormNotesInput(ev) {
        this.state.signTypeForm.notes = ev.target.value;
    }

    updateSignTypeForm(field, value) {
        this.state.signTypeForm[field] = value;
    }

    async saveSignType() {
        const form = this.state.signTypeForm;

        if (!form.name) {
            this.notification.add("Please enter a sign type ID", { type: "warning" });
            return;
        }

        try {
            let signTypeId;

            if (this.state.editingSignType) {
                // Update existing
                await this.orm.write("cc.sign.type", [this.state.editingSignType.id], {
                    name: form.name,
                    description: form.description,
                    quantity: form.quantity,
                    dimensions: form.dimensions,
                    material: form.material,
                    mounting: form.mounting,
                    notes: form.notes,
                });
                signTypeId = this.state.editingSignType.id;
            } else {
                // Create new
                signTypeId = await this.orm.create("cc.sign.type", {
                    name: form.name,
                    description: form.description,
                    quantity: form.quantity,
                    dimensions: form.dimensions,
                    material: form.material,
                    mounting: form.mounting,
                    notes: form.notes,
                    opportunity_id: this.opportunityId,
                });
            }

            // If there's a pending bookmark, create it
            if (this.state.pendingBookmark) {
                const pb = this.state.pendingBookmark;

                // Calculate center point from path
                const centerX = pb.pathData.reduce((sum, p) => sum + p.x, 0) / pb.pathData.length;
                const centerY = pb.pathData.reduce((sum, p) => sum + p.y, 0) / pb.pathData.length;

                await this.orm.create("cc.sign.bookmark", {
                    sign_type_id: signTypeId,
                    attachment_id: pb.attachmentId,
                    page_number: pb.pageNumber,
                    x_position: centerX,
                    y_position: centerY,
                    path_data: JSON.stringify(pb.pathData),
                    highlight_color: "#f59e0b",
                });
            }

            this.notification.add(`Sign type "${form.name}" saved!`, { type: "success" });

            // Refresh data
            await this.loadSignTypes();
            if (this.state.selectedAttachment) {
                await this.loadBookmarks(this.state.selectedAttachment.id);
            }

            this.closeSignTypeModal();
            this.state.isLassoMode = false;

        } catch (error) {
            console.error("Failed to save sign type:", error);
            this.notification.add("Failed to save: " + error.message, { type: "danger" });
        }
    }

    async goToSignType(signType) {
        // Find first bookmark for this sign type
        try {
            const bookmarks = await this.orm.searchRead(
                "cc.sign.bookmark",
                [["sign_type_id", "=", signType.id]],
                ["attachment_id", "page_number"],
                { limit: 1 }
            );

            if (bookmarks.length > 0) {
                const bookmark = bookmarks[0];
                const attachment = this.state.attachments.find(a => a.id === bookmark.attachment_id[0]);

                if (attachment) {
                    await this.openAttachment(attachment);
                    this.goToPageNumber(bookmark.page_number);
                }
            } else {
                this.notification.add("No bookmarks found for this sign type", { type: "info" });
            }
        } catch (error) {
            console.error("Failed to navigate:", error);
        }
    }

    // ==================== Bookmark Context Menu ====================

    onBookmarkRightClick(ev, bookmark) {
        ev.preventDefault();
        this.state.selectedBookmark = bookmark;
        this.state.bookmarkMenuX = ev.clientX;
        this.state.bookmarkMenuY = ev.clientY;
        this.state.showBookmarkMenu = true;
    }

    async deleteSelectedBookmark() {
        if (!this.state.selectedBookmark) return;

        try {
            await this.orm.unlink("cc.sign.bookmark", [this.state.selectedBookmark.id]);
            this.notification.add("Bookmark deleted", { type: "success" });

            // Refresh
            await this.loadBookmarks(this.state.selectedAttachment.id);
            await this.loadSignTypes();
        } catch (error) {
            console.error("Failed to delete bookmark:", error);
            this.notification.add("Failed to delete", { type: "danger" });
        }

        this.state.showBookmarkMenu = false;
        this.state.selectedBookmark = null;
    }

    editSelectedBookmark() {
        // TODO: Open edit dialog for bookmark
        this.state.showBookmarkMenu = false;
    }

    // ==================== Utilities ====================

    formatSize(bytes) {
        if (!bytes) return "0 B";
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(1) + " " + sizes[i];
    }
}

// Register as action
registry.category("actions").add("cc_ops_pdf_viewer", PDFViewer);
