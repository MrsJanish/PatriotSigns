/**
 * My Work Dashboard JavaScript
 * Handles task switching, clock out, QR scanning, and real-time timer updates.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        initMyWorkDashboard();
    });

    function initMyWorkDashboard() {
        // Task item click handlers
        document.querySelectorAll('.task-item').forEach(function (item) {
            item.addEventListener('click', function (e) {
                e.preventDefault();
                const taskId = this.dataset.taskId;
                switchToTask(taskId);
            });
        });

        // Mark Complete button
        const markCompleteBtn = document.querySelector('.btn-mark-complete');
        if (markCompleteBtn) {
            markCompleteBtn.addEventListener('click', function () {
                const taskId = this.dataset.taskId;
                markTaskComplete(taskId);
            });
        }

        // Clock Out button
        const clockOutBtn = document.querySelector('.btn-clock-out');
        if (clockOutBtn) {
            clockOutBtn.addEventListener('click', function () {
                clockOut();
            });
        }

        // Refresh button
        const refreshBtn = document.querySelector('.btn-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function () {
                location.reload();
            });
        }

        // QR Scanner button
        const scanQrBtn = document.querySelector('.btn-scan-qr');
        if (scanQrBtn) {
            scanQrBtn.addEventListener('click', function () {
                openQrScanner();
            });
        }

        // Start timer update
        startTimerUpdate();
    }

    function showLoading() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.classList.remove('d-none');
        }
    }

    function hideLoading() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.classList.add('d-none');
        }
    }

    function showToast(message, type) {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed top-0 start-50 translate-middle-x mt-3`;
        toast.style.zIndex = '10000';
        toast.innerHTML = message;
        document.body.appendChild(toast);
        setTimeout(function () {
            toast.remove();
        }, 3000);
    }

    function switchToTask(taskId) {
        showLoading();

        fetch(`/my-work/switch-task/${taskId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.result && data.result.success) {
                    showToast(`Switched to: ${data.result.task_name}`, 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    showToast(data.result?.error || 'Failed to switch task', 'danger');
                }
            })
            .catch(error => {
                hideLoading();
                showToast('Network error', 'danger');
                console.error('Error:', error);
            });
    }

    function markTaskComplete(taskId) {
        if (!confirm('Mark this task as complete?')) {
            return;
        }

        showLoading();

        fetch(`/my-work/mark-complete/${taskId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.result && data.result.success) {
                    showToast('Task marked complete!', 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    showToast(data.result?.error || 'Failed to complete task', 'danger');
                }
            })
            .catch(error => {
                hideLoading();
                showToast('Network error', 'danger');
                console.error('Error:', error);
            });
    }

    function clockOut() {
        if (!confirm('Clock out now?')) {
            return;
        }

        showLoading();

        fetch('/my-work/clock-out', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.result && data.result.success) {
                    showToast('Clocked out!', 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    showToast(data.result?.error || 'Failed to clock out', 'danger');
                }
            })
            .catch(error => {
                hideLoading();
                showToast('Network error', 'danger');
                console.error('Error:', error);
            });
    }

    function openQrScanner() {
        const modal = new bootstrap.Modal(document.getElementById('qrScannerModal'));
        modal.show();

        // Initialize QR scanner if html5-qrcode is available
        if (typeof Html5Qrcode !== 'undefined') {
            const html5QrCode = new Html5Qrcode("qr-reader");

            html5QrCode.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: 250 },
                function (decodedText) {
                    html5QrCode.stop();
                    modal.hide();
                    handleQrScan(decodedText);
                },
                function (errorMessage) {
                    // Scan error - ignore, keep scanning
                }
            );

            // Stop scanner when modal closes
            document.getElementById('qrScannerModal').addEventListener('hidden.bs.modal', function () {
                html5QrCode.stop().catch(err => { });
            });
        } else {
            document.getElementById('qr-reader-results').innerHTML =
                '<p class="text-danger">QR scanner library not loaded</p>' +
                '<input type="text" class="form-control" id="manual-barcode" placeholder="Enter barcode manually">' +
                '<button class="btn btn-primary mt-2" onclick="handleManualBarcode()">Submit</button>';
        }
    }

    function handleQrScan(barcode) {
        showLoading();

        fetch('/my-work/scan-qr', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ barcode: barcode })
        })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.result && data.result.success) {
                    showToast(`Switched to: ${data.result.task_name}`, 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    showToast(data.result?.error || 'Task not found', 'danger');
                }
            })
            .catch(error => {
                hideLoading();
                showToast('Network error', 'danger');
                console.error('Error:', error);
            });
    }

    // Manual barcode entry fallback
    window.handleManualBarcode = function () {
        const barcode = document.getElementById('manual-barcode').value;
        if (barcode) {
            bootstrap.Modal.getInstance(document.getElementById('qrScannerModal')).hide();
            handleQrScan(barcode);
        }
    };

    function startTimerUpdate() {
        const timerDisplay = document.querySelector('.timer-display');
        if (!timerDisplay) return;

        const startTime = timerDisplay.dataset.start;
        if (!startTime) return;

        const start = new Date(startTime);

        function updateTimer() {
            const now = new Date();
            const diff = now - start;

            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

            timerDisplay.textContent = `${hours}h ${minutes}m`;
        }

        updateTimer();
        setInterval(updateTimer, 60000); // Update every minute
    }
})();
