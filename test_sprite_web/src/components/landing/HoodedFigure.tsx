"use client";

import { useRef, useEffect } from 'react';

export default function HoodedFigure() {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Set canvas size
        const resize = () => {
            canvas.width = canvas.offsetWidth * 2;
            canvas.height = canvas.offsetHeight * 2;
            ctx.scale(2, 2);
        };
        resize();
        window.addEventListener('resize', resize);

        let animationId: number;
        let time = 0;

        const draw = () => {
            const w = canvas.offsetWidth;
            const h = canvas.offsetHeight;

            // Clear
            ctx.clearRect(0, 0, w, h);

            // Center point
            const cx = w / 2;
            const cy = h / 2;

            // Glowing aura behind the figure
            const auraGradient = ctx.createRadialGradient(cx, cy - 50, 0, cx, cy - 50, 300);
            auraGradient.addColorStop(0, 'rgba(0, 212, 170, 0.15)');
            auraGradient.addColorStop(0.5, 'rgba(0, 212, 170, 0.05)');
            auraGradient.addColorStop(1, 'rgba(0, 212, 170, 0)');
            ctx.fillStyle = auraGradient;
            ctx.beginPath();
            ctx.arc(cx, cy - 50, 300, 0, Math.PI * 2);
            ctx.fill();

            // Hood outer shape
            ctx.save();
            ctx.translate(cx, cy);

            // Hood silhouette - dark mysterious figure
            const hoodGradient = ctx.createLinearGradient(0, -200, 0, 250);
            hoodGradient.addColorStop(0, '#0a0a0a');
            hoodGradient.addColorStop(0.3, '#050505');
            hoodGradient.addColorStop(1, '#000000');

            ctx.fillStyle = hoodGradient;
            ctx.beginPath();

            // Hood top curve
            ctx.moveTo(-120, 50);
            ctx.bezierCurveTo(-150, -50, -100, -180, 0, -200);
            ctx.bezierCurveTo(100, -180, 150, -50, 120, 50);

            // Shoulders and body
            ctx.bezierCurveTo(180, 100, 200, 200, 180, 350);
            ctx.lineTo(-180, 350);
            ctx.bezierCurveTo(-200, 200, -180, 100, -120, 50);
            ctx.closePath();
            ctx.fill();

            // Hood inner shadow (creates depth)
            const innerGradient = ctx.createRadialGradient(0, -50, 0, 0, -50, 150);
            innerGradient.addColorStop(0, 'rgba(0, 0, 0, 0.9)');
            innerGradient.addColorStop(0.5, 'rgba(5, 5, 5, 0.7)');
            innerGradient.addColorStop(1, 'rgba(10, 10, 10, 0)');

            ctx.fillStyle = innerGradient;
            ctx.beginPath();
            ctx.ellipse(0, -30, 80, 100, 0, 0, Math.PI * 2);
            ctx.fill();

            // Face shadow area (deep void)
            const faceGradient = ctx.createRadialGradient(0, -20, 0, 0, -20, 70);
            faceGradient.addColorStop(0, '#000000');
            faceGradient.addColorStop(0.7, 'rgba(0, 0, 0, 0.9)');
            faceGradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

            ctx.fillStyle = faceGradient;
            ctx.beginPath();
            ctx.ellipse(0, -20, 60, 80, 0, 0, Math.PI * 2);
            ctx.fill();

            // Glowing eyes effect (subtle, mysterious)
            const eyeGlow = Math.sin(time * 2) * 0.3 + 0.7;

            // Left eye glow
            const leftEyeGradient = ctx.createRadialGradient(-20, -30, 0, -20, -30, 15);
            leftEyeGradient.addColorStop(0, `rgba(0, 212, 170, ${eyeGlow * 0.8})`);
            leftEyeGradient.addColorStop(0.5, `rgba(0, 212, 170, ${eyeGlow * 0.3})`);
            leftEyeGradient.addColorStop(1, 'rgba(0, 212, 170, 0)');
            ctx.fillStyle = leftEyeGradient;
            ctx.beginPath();
            ctx.arc(-20, -30, 15, 0, Math.PI * 2);
            ctx.fill();

            // Left eye core
            ctx.fillStyle = `rgba(0, 212, 170, ${eyeGlow})`;
            ctx.beginPath();
            ctx.arc(-20, -30, 3, 0, Math.PI * 2);
            ctx.fill();

            // Right eye glow
            const rightEyeGradient = ctx.createRadialGradient(20, -30, 0, 20, -30, 15);
            rightEyeGradient.addColorStop(0, `rgba(0, 212, 170, ${eyeGlow * 0.8})`);
            rightEyeGradient.addColorStop(0.5, `rgba(0, 212, 170, ${eyeGlow * 0.3})`);
            rightEyeGradient.addColorStop(1, 'rgba(0, 212, 170, 0)');
            ctx.fillStyle = rightEyeGradient;
            ctx.beginPath();
            ctx.arc(20, -30, 15, 0, Math.PI * 2);
            ctx.fill();

            // Right eye core
            ctx.fillStyle = `rgba(0, 212, 170, ${eyeGlow})`;
            ctx.beginPath();
            ctx.arc(20, -30, 3, 0, Math.PI * 2);
            ctx.fill();

            // Hood edge highlight (rim light effect)
            ctx.strokeStyle = 'rgba(0, 212, 170, 0.2)';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(-110, 40);
            ctx.bezierCurveTo(-140, -40, -90, -170, 0, -190);
            ctx.bezierCurveTo(90, -170, 140, -40, 110, 40);
            ctx.stroke();

            // Digital particles floating around
            for (let i = 0; i < 20; i++) {
                const angle = (i / 20) * Math.PI * 2 + time * 0.5;
                const radius = 150 + Math.sin(time + i) * 30;
                const px = Math.cos(angle) * radius;
                const py = Math.sin(angle) * radius * 0.5 - 50;
                const size = 2 + Math.sin(time * 2 + i) * 1;
                const alpha = 0.3 + Math.sin(time + i * 0.5) * 0.2;

                ctx.fillStyle = `rgba(0, 212, 170, ${alpha})`;
                ctx.beginPath();
                ctx.arc(px, py, size, 0, Math.PI * 2);
                ctx.fill();
            }

            // Binary/code rain effect on sides
            ctx.font = '10px monospace';
            ctx.fillStyle = 'rgba(0, 212, 170, 0.15)';
            for (let i = 0; i < 15; i++) {
                const x = -200 + (i % 3) * 15;
                const y = ((time * 50 + i * 40) % 400) - 200;
                ctx.fillText(Math.random() > 0.5 ? '1' : '0', x, y);
            }
            for (let i = 0; i < 15; i++) {
                const x = 170 + (i % 3) * 15;
                const y = ((time * 50 + i * 40) % 400) - 200;
                ctx.fillText(Math.random() > 0.5 ? '1' : '0', x, y);
            }

            ctx.restore();

            time += 0.016;
            animationId = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            window.removeEventListener('resize', resize);
            cancelAnimationFrame(animationId);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="w-full h-full"
            style={{ maxWidth: '600px', maxHeight: '700px' }}
        />
    );
}
