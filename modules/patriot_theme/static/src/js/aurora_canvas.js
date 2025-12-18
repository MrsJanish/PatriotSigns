/** @odoo-module **/

import { Component, onMounted, useRef } from "@odoo/owl";

export class AuroraCanvas extends Component {
    setup() {
        this.canvasRef = useRef("auroraCanvas");
        this.t = 0;

        onMounted(() => {
            if (this.canvasRef.el) {
                this.resize();
                window.addEventListener('resize', () => this.resize());
                this.draw();
            }
        });
    }

    resize() {
        if (!this.canvasRef.el) return;
        this.width = this.canvasRef.el.width = window.innerWidth;
        this.height = this.canvasRef.el.height = window.innerHeight;
    }

    draw() {
        if (!this.canvasRef.el) return;
        const ctx = this.canvasRef.el.getContext('2d');
        const width = this.width;
        const height = this.height;

        // Dark Background (Deep Space)
        ctx.fillStyle = '#020205';
        ctx.fillRect(0, 0, width, height);

        // Render Waves
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

            // Mathematical Sine Wave Logic from User File
            for (let x = 0; x <= width; x += 10) {
                const y = height / 2 +
                    Math.sin(x * 0.005 + this.t + i) * 100 +
                    Math.sin(x * 0.01 - this.t * 0.5) * 50;

                if (x === 0) ctx.moveTo(x, height);
                ctx.lineTo(x, y);
            }

            ctx.lineTo(width, height);
            ctx.closePath();
            ctx.fill();
        }

        this.t += 0.01;
        requestAnimationFrame(() => this.draw());
    }
}

AuroraCanvas.template = "patriot_theme.AuroraCanvas";
