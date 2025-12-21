/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * PDF Viewer Component - Provides in-browser PDF viewing with:
 * - Split-view panels (legend + drawings)
 * - Zoom controls
 * - Page navigation
 * - Click-to-bookmark functionality
 * - Fullscreen mode
 */
export class PDFViewer extends Component {
    static template = "patriot_cc_ops.PDFViewer";
    static props = {
        attachmentId: { type: Number, optional: true },
        opportunityId: { type: Number, optional: true },
        onBookmarkCreate: { type: Function, optional: true },
    };

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
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

            // Panel states (for split view)
            leftPanel: {
                attachmentId: null,
                pdfDoc: null,
                currentPage: 1,
                totalPages: 0,
            },
            rightPanel: {
                attachmentId: null,
                pdfDoc: null,
                currentPage: 1,
                totalPages: 0,
            },

            // Attachments list
            attachments: [],
            selectedAttachment: null,

            // Filtering
            filterText: "",
            filteredAttachments: [],

            // Bookmarks on current page
            bookmarks: [],

            // Bookmark creation mode
            isBookmarkMode: false,
        });

        this.canvasRef = useRef("pdfCanvas");
        this.containerRef = useRef("viewerContainer");
        this.leftCanvasRef = useRef("leftCanvas");
        this.rightCanvasRef = useRef("rightCanvas");

        // PDF.js library - loaded from CDN
        this.pdfjsLib = null;

        onMounted(() => {
            this.loadPDFJS();
            if (this.props.opportunityId) {
                this.loadAttachments();
            }
        });

        onWillUnmount(() => {
            // Cleanup
            if (this.state.pdfDoc) {
                this.state.pdfDoc.destroy?.();
            }
        });
    }

    async loadPDFJS() {
        // Load PDF.js from CDN if not already loaded
        if (window.pdfjsLib) {
            this.pdfjsLib = window.pdfjsLib;
            return;
        }

        try {
            // Load PDF.js script
            await this.loadScript("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js");

            // Set worker
            window.pdfjsLib.GlobalWorkerOptions.workerSrc =
                "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

            this.pdfjsLib = window.pdfjsLib;
            console.log("PDF.js loaded successfully");
        } catch (error) {
            console.error("Failed to load PDF.js:", error);
            this.state.error = "Failed to load PDF viewer library";
        }
    }

    loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async loadAttachments() {
        try {
            const result = await this.rpc("/web/dataset/call_kw", {
                model: "ir.attachment",
                method: "search_read",
                args: [],
                kwargs: {
                    domain: [
                        ["res_model", "=", "cc.opportunity"],
                        ["res_id", "=", this.props.opportunityId],
                        ["mimetype", "=", "application/pdf"],
                    ],
                    fields: ["id", "name", "datas", "file_size"],
                    order: "name asc",
                }
            });

            this.state.attachments = result;
            this.state.filteredAttachments = result;
            this.state.isLoading = false;

            // Auto-load first attachment if available
            if (result.length > 0 && this.props.attachmentId) {
                const target = result.find(a => a.id === this.props.attachmentId);
                if (target) {
                    this.openAttachment(target);
                }
            } else if (result.length > 0) {
                this.openAttachment(result[0]);
            }
        } catch (error) {
            console.error("Failed to load attachments:", error);
            this.state.error = "Failed to load documents";
            this.state.isLoading = false;
        }
    }

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

    // Handler for dropdown attachment selection
    onAttachmentSelect(ev) {
        const attachmentId = parseInt(ev.target.value, 10);
        if (attachmentId) {
            const att = this.state.attachments.find(a => a.id === attachmentId);
            if (att) {
                this.openAttachment(att);
            }
        }
    }

    // Handler for sidebar attachment click
    onSidebarAttachmentClick(ev) {
        const attachmentId = parseInt(ev.currentTarget.dataset.id, 10);
        if (attachmentId) {
            const att = this.state.attachments.find(a => a.id === attachmentId);
            if (att) {
                this.openAttachment(att);
            }
        }
    }

    async openAttachment(attachment) {
        if (!this.pdfjsLib) {
            console.error("PDF.js not loaded yet");
            return;
        }

        this.state.selectedAttachment = attachment;
        this.state.isLoading = true;
        this.state.error = null;

        try {
            // Fetch PDF data
            const response = await this.rpc("/web/dataset/call_kw", {
                model: "ir.attachment",
                method: "read",
                args: [[attachment.id], ["datas"]],
                kwargs: {}
            });

            if (!response || !response[0] || !response[0].datas) {
                throw new Error("No PDF data returned");
            }

            // Decode base64
            const pdfData = atob(response[0].datas);
            const pdfArray = new Uint8Array(pdfData.split("").map(c => c.charCodeAt(0)));

            // Load PDF
            const loadingTask = this.pdfjsLib.getDocument({ data: pdfArray });
            const pdfDoc = await loadingTask.promise;

            this.state.pdfDoc = pdfDoc;
            this.state.totalPages = pdfDoc.numPages;
            this.state.currentPage = 1;
            this.state.isLoading = false;

            // Render first page
            await this.renderPage(1);

            // Load bookmarks for this attachment
            await this.loadBookmarks(attachment.id);

        } catch (error) {
            console.error("Failed to open PDF:", error);
            this.state.error = "Failed to open PDF: " + error.message;
            this.state.isLoading = false;
        }
    }

    async renderPage(pageNum, canvas = null) {
        if (!this.state.pdfDoc) return;

        try {
            const page = await this.state.pdfDoc.getPage(pageNum);
            const viewport = page.getViewport({ scale: this.state.scale });

            const canvasEl = canvas || this.canvasRef.el;
            if (!canvasEl) return;

            const context = canvasEl.getContext("2d");
            canvasEl.height = viewport.height;
            canvasEl.width = viewport.width;

            const renderContext = {
                canvasContext: context,
                viewport: viewport
            };

            await page.render(renderContext).promise;

            // Re-render bookmarks overlay
            this.renderBookmarks();

        } catch (error) {
            console.error("Failed to render page:", error);
        }
    }

    // Page navigation
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

    goToPage(pageNum) {
        if (pageNum >= 1 && pageNum <= this.state.totalPages) {
            this.state.currentPage = pageNum;
            this.renderPage(this.state.currentPage);
        }
    }

    onPageInputChange(ev) {
        const page = parseInt(ev.target.value, 10);
        if (!isNaN(page)) {
            this.goToPage(page);
        }
    }

    // Zoom controls
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

    resetZoom() {
        this.state.scale = 1.0;
        this.state.zoomPercent = "100%";
        this.renderPage(this.state.currentPage);
    }

    // Fullscreen
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

    // Split view
    toggleSplitView() {
        this.state.isSplitView = !this.state.isSplitView;
    }

    // Bookmark mode
    toggleBookmarkMode() {
        this.state.isBookmarkMode = !this.state.isBookmarkMode;
    }

    // Handle canvas click for bookmarking
    onCanvasClick(ev) {
        if (!this.state.isBookmarkMode) return;

        const canvas = ev.target;
        const rect = canvas.getBoundingClientRect();
        const x = (ev.clientX - rect.left) / rect.width;
        const y = (ev.clientY - rect.top) / rect.height;

        // Trigger bookmark creation
        if (this.props.onBookmarkCreate) {
            this.props.onBookmarkCreate({
                attachmentId: this.state.selectedAttachment.id,
                pageNumber: this.state.currentPage,
                xPosition: x,
                yPosition: y,
            });
        } else {
            // Default: open bookmark dialog
            this.createBookmarkAt(x, y);
        }
    }

    async createBookmarkAt(x, y) {
        // Will be handled by parent component or action
        this.notification.add("Bookmark created! Assign it to a Sign Type.", {
            type: "success",
        });

        // Add temporary visual marker
        this.state.bookmarks.push({
            x, y,
            pageNumber: this.state.currentPage,
            color: "#FFFF00",
            temp: true,
        });
        this.renderBookmarks();
    }

    async loadBookmarks(attachmentId) {
        // Load existing bookmarks from database
        try {
            const result = await this.rpc("/web/dataset/call_kw", {
                model: "cc.sign.bookmark",
                method: "search_read",
                args: [],
                kwargs: {
                    domain: [["attachment_id", "=", attachmentId]],
                    fields: ["id", "page_number", "x_position", "y_position", "highlight_color", "sign_type_id"],
                }
            });
            this.state.bookmarks = result.map(b => ({
                id: b.id,
                pageNumber: b.page_number,
                x: b.x_position,
                y: b.y_position,
                color: b.highlight_color || "#FFFF00",
                signTypeId: b.sign_type_id?.[0],
                signTypeName: b.sign_type_id?.[1],
            }));

            this.renderBookmarks();
        } catch (error) {
            // Model may not exist yet
            console.log("No bookmarks model or no bookmarks found");
            this.state.bookmarks = [];
        }
    }

    renderBookmarks() {
        // Render bookmark highlights on current page
        const canvas = this.canvasRef.el;
        if (!canvas) return;

        // Get overlay canvas or create one
        let overlay = canvas.parentElement.querySelector(".bookmark-overlay");
        if (!overlay) {
            overlay = document.createElement("canvas");
            overlay.className = "bookmark-overlay";
            overlay.style.position = "absolute";
            overlay.style.top = "0";
            overlay.style.left = "0";
            overlay.style.pointerEvents = "none";
            canvas.parentElement.style.position = "relative";
            canvas.parentElement.appendChild(overlay);
        }

        overlay.width = canvas.width;
        overlay.height = canvas.height;

        const ctx = overlay.getContext("2d");
        ctx.clearRect(0, 0, overlay.width, overlay.height);

        // Draw bookmarks for current page
        const pageBookmarks = this.state.bookmarks.filter(
            b => b.pageNumber === this.state.currentPage
        );

        for (const bookmark of pageBookmarks) {
            const x = bookmark.x * overlay.width;
            const y = bookmark.y * overlay.height;

            // Draw highlight circle
            ctx.beginPath();
            ctx.arc(x, y, 20, 0, 2 * Math.PI);
            ctx.fillStyle = bookmark.color + "66"; // Semi-transparent
            ctx.fill();
            ctx.strokeStyle = bookmark.color;
            ctx.lineWidth = 3;
            ctx.stroke();
        }
    }

    // Format file size for display
    formatSize(bytes) {
        if (!bytes) return "0 B";
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(1) + " " + sizes[i];
    }
}

// Register as action
registry.category("actions").add("cc_ops_pdf_viewer", PDFViewer);
