"use client";

import { useRef, useEffect } from "react";

export default function AnimatedHoodie() {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Set canvas size
        const resize = () => {
            canvas.width = canvas.offsetWidth * window.devicePixelRatio;
            canvas.height = canvas.offsetHeight * window.devicePixelRatio;
            ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        };
        resize();
        window.addEventListener("resize", resize);

        let animationId: number;
        let time = 0;

        // Particle system for ambient effect
        const particles: { x: number; y: number; vx: number; vy: number; size: number; alpha: number }[] = [];
        for (let i = 0; i < 50; i++) {
            particles.push({
                x: Math.random() * canvas.offsetWidth,
                y: Math.random() * canvas.offsetHeight,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                size: Math.random() * 2 + 1,
                alpha: Math.random() * 0.5 + 0.1
            });
        }

        const animate = () => {
            time += 0.016;
            const width = canvas.offsetWidth;
            const height = canvas.offsetHeight;

            // Clear with gradient background
            const bgGradient = ctx.createRadialGradient(
                width / 2, height / 2, 0,
                width / 2, height / 2, Math.max(width, height) * 0.8
            );
            bgGradient.addColorStop(0, "#1a1a1d");
            bgGradient.addColorStop(0.5, "#0f0f11");
            bgGradient.addColorStop(1, "#050506");
            ctx.fillStyle = bgGradient;
            ctx.fillRect(0, 0, width, height);

            // Update and draw particles
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                if (p.x < 0) p.x = width;
                if (p.x > width) p.x = 0;
                if (p.y < 0) p.y = height;
                if (p.y > height) p.y = 0;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(0, 212, 170, ${p.alpha * 0.3})`;
                ctx.fill();
            });

            // Floating animation
            const floatY = Math.sin(time * 0.8) * 15;
            const floatX = Math.cos(time * 0.5) * 5;

            // Center position
            const centerX = width / 2 + floatX;
            const centerY = height / 2 + floatY;

            // Hoodie dimensions
            const hoodieWidth = Math.min(width * 0.45, 400);
            const hoodieHeight = hoodieWidth * 1.3;

            // Shadow under hoodie
            const shadowGradient = ctx.createRadialGradient(
                centerX, centerY + hoodieHeight * 0.55, 0,
                centerX, centerY + hoodieHeight * 0.55, hoodieWidth * 0.5
            );
            shadowGradient.addColorStop(0, "rgba(0, 0, 0, 0.4)");
            shadowGradient.addColorStop(1, "rgba(0, 0, 0, 0)");
            ctx.fillStyle = shadowGradient;
            ctx.beginPath();
            ctx.ellipse(centerX, centerY + hoodieHeight * 0.55, hoodieWidth * 0.5, hoodieWidth * 0.15, 0, 0, Math.PI * 2);
            ctx.fill();

            // Main hoodie body gradient
            const bodyGradient = ctx.createLinearGradient(
                centerX - hoodieWidth / 2, centerY - hoodieHeight / 2,
                centerX + hoodieWidth / 2, centerY + hoodieHeight / 2
            );
            bodyGradient.addColorStop(0, "#2d2d30");
            bodyGradient.addColorStop(0.3, "#1f1f22");
            bodyGradient.addColorStop(0.7, "#141416");
            bodyGradient.addColorStop(1, "#0a0a0b");

            // Draw hoodie body
            ctx.save();
            ctx.translate(centerX, centerY);

            // Body shape
            ctx.beginPath();
            ctx.moveTo(-hoodieWidth * 0.4, -hoodieHeight * 0.25);
            // Left shoulder curve
            ctx.bezierCurveTo(
                -hoodieWidth * 0.5, -hoodieHeight * 0.2,
                -hoodieWidth * 0.55, -hoodieHeight * 0.1,
                -hoodieWidth * 0.5, hoodieHeight * 0.05
            );
            // Left arm
            ctx.bezierCurveTo(
                -hoodieWidth * 0.6, hoodieHeight * 0.15,
                -hoodieWidth * 0.55, hoodieHeight * 0.35,
                -hoodieWidth * 0.45, hoodieHeight * 0.4
            );
            // Left side to bottom
            ctx.bezierCurveTo(
                -hoodieWidth * 0.4, hoodieHeight * 0.42,
                -hoodieWidth * 0.35, hoodieHeight * 0.45,
                -hoodieWidth * 0.3, hoodieHeight * 0.47
            );
            // Bottom ribbing
            ctx.lineTo(hoodieWidth * 0.3, hoodieHeight * 0.47);
            // Right side
            ctx.bezierCurveTo(
                hoodieWidth * 0.35, hoodieHeight * 0.45,
                hoodieWidth * 0.4, hoodieHeight * 0.42,
                hoodieWidth * 0.45, hoodieHeight * 0.4
            );
            // Right arm
            ctx.bezierCurveTo(
                hoodieWidth * 0.55, hoodieHeight * 0.35,
                hoodieWidth * 0.6, hoodieHeight * 0.15,
                hoodieWidth * 0.5, hoodieHeight * 0.05
            );
            // Right shoulder
            ctx.bezierCurveTo(
                hoodieWidth * 0.55, -hoodieHeight * 0.1,
                hoodieWidth * 0.5, -hoodieHeight * 0.2,
                hoodieWidth * 0.4, -hoodieHeight * 0.25
            );
            // Close at top
            ctx.closePath();

            ctx.fillStyle = bodyGradient;
            ctx.fill();

            // Hood gradient
            const hoodGradient = ctx.createLinearGradient(
                0, -hoodieHeight * 0.5,
                0, -hoodieHeight * 0.15
            );
            hoodGradient.addColorStop(0, "#252528");
            hoodGradient.addColorStop(0.5, "#1a1a1d");
            hoodGradient.addColorStop(1, "#111113");

            // Draw hood
            ctx.beginPath();
            ctx.moveTo(-hoodieWidth * 0.35, -hoodieHeight * 0.25);
            // Hood curve
            ctx.bezierCurveTo(
                -hoodieWidth * 0.4, -hoodieHeight * 0.35,
                -hoodieWidth * 0.35, -hoodieHeight * 0.5,
                0, -hoodieHeight * 0.52
            );
            ctx.bezierCurveTo(
                hoodieWidth * 0.35, -hoodieHeight * 0.5,
                hoodieWidth * 0.4, -hoodieHeight * 0.35,
                hoodieWidth * 0.35, -hoodieHeight * 0.25
            );
            ctx.closePath();
            ctx.fillStyle = hoodGradient;
            ctx.fill();

            // Hood opening (darker inside)
            ctx.beginPath();
            ctx.ellipse(0, -hoodieHeight * 0.32, hoodieWidth * 0.22, hoodieHeight * 0.15, 0, 0, Math.PI * 2);
            const innerGradient = ctx.createRadialGradient(
                0, -hoodieHeight * 0.32, 0,
                0, -hoodieHeight * 0.32, hoodieWidth * 0.22
            );
            innerGradient.addColorStop(0, "#000000");
            innerGradient.addColorStop(0.7, "#0a0a0a");
            innerGradient.addColorStop(1, "#111113");
            ctx.fillStyle = innerGradient;
            ctx.fill();

            // Kangaroo pocket
            ctx.beginPath();
            ctx.moveTo(-hoodieWidth * 0.25, hoodieHeight * 0.15);
            ctx.bezierCurveTo(
                -hoodieWidth * 0.28, hoodieHeight * 0.25,
                -hoodieWidth * 0.25, hoodieHeight * 0.35,
                -hoodieWidth * 0.15, hoodieHeight * 0.38
            );
            ctx.lineTo(hoodieWidth * 0.15, hoodieHeight * 0.38);
            ctx.bezierCurveTo(
                hoodieWidth * 0.25, hoodieHeight * 0.35,
                hoodieWidth * 0.28, hoodieHeight * 0.25,
                hoodieWidth * 0.25, hoodieHeight * 0.15
            );
            ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
            ctx.lineWidth = 2;
            ctx.stroke();

            // Drawstrings
            ctx.strokeStyle = "#1a1a1d";
            ctx.lineWidth = 3;

            // Left drawstring
            ctx.beginPath();
            ctx.moveTo(-hoodieWidth * 0.08, -hoodieHeight * 0.2);
            ctx.bezierCurveTo(
                -hoodieWidth * 0.1, -hoodieHeight * 0.1,
                -hoodieWidth * 0.08, 0,
                -hoodieWidth * 0.1, hoodieHeight * 0.1
            );
            ctx.stroke();

            // Right drawstring
            ctx.beginPath();
            ctx.moveTo(hoodieWidth * 0.08, -hoodieHeight * 0.2);
            ctx.bezierCurveTo(
                hoodieWidth * 0.1, -hoodieHeight * 0.1,
                hoodieWidth * 0.08, 0,
                hoodieWidth * 0.1, hoodieHeight * 0.1
            );
            ctx.stroke();

            // Drawstring tips (metal aglets)
            ctx.fillStyle = "#666666";
            ctx.fillRect(-hoodieWidth * 0.115, hoodieHeight * 0.08, hoodieWidth * 0.03, hoodieHeight * 0.04);
            ctx.fillRect(hoodieWidth * 0.085, hoodieHeight * 0.08, hoodieWidth * 0.03, hoodieHeight * 0.04);

            // Subtle highlight on shoulders
            ctx.beginPath();
            ctx.moveTo(-hoodieWidth * 0.35, -hoodieHeight * 0.22);
            ctx.bezierCurveTo(
                -hoodieWidth * 0.4, -hoodieHeight * 0.18,
                -hoodieWidth * 0.45, -hoodieHeight * 0.1,
                -hoodieWidth * 0.42, 0
            );
            ctx.strokeStyle = "rgba(255, 255, 255, 0.03)";
            ctx.lineWidth = 8;
            ctx.stroke();

            ctx.restore();

            // Ambient glow around hoodie
            const glowGradient = ctx.createRadialGradient(
                centerX, centerY, hoodieWidth * 0.3,
                centerX, centerY, hoodieWidth * 0.8
            );
            glowGradient.addColorStop(0, "rgba(0, 212, 170, 0.02)");
            glowGradient.addColorStop(0.5, "rgba(0, 212, 170, 0.01)");
            glowGradient.addColorStop(1, "rgba(0, 0, 0, 0)");
            ctx.fillStyle = glowGradient;
            ctx.fillRect(0, 0, width, height);

            // Subtle scan lines effect
            ctx.fillStyle = "rgba(255, 255, 255, 0.005)";
            for (let i = 0; i < height; i += 4) {
                ctx.fillRect(0, i, width, 1);
            }

            animationId = requestAnimationFrame(animate);
        };

        animate();

        return () => {
            window.removeEventListener("resize", resize);
            cancelAnimationFrame(animationId);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="w-full h-full"
            style={{ display: "block" }}
        />
    );
}
