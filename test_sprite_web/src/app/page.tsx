"use client";

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import {
    Shield, Zap, Eye, Terminal, Bot, ChevronDown,
    CheckCircle, ArrowRight, Code, Cpu, Lock, Scan
} from 'lucide-react';

// Dynamic imports for 3D components (no SSR)
const Scene3D = dynamic(() => import('@/components/landing/Scene3D'), { ssr: false });
const HoodedFigure = dynamic(() => import('@/components/landing/HoodedFigure'), { ssr: false });

// Typing effect component
function TypeWriter({ text, delay = 50 }: { text: string; delay?: number }) {
    const [displayText, setDisplayText] = useState('');
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        if (currentIndex < text.length) {
            const timer = setTimeout(() => {
                setDisplayText(prev => prev + text[currentIndex]);
                setCurrentIndex(prev => prev + 1);
            }, delay);
            return () => clearTimeout(timer);
        }
    }, [currentIndex, text, delay]);

    return (
        <span>
            {displayText}
            <span className="animate-pulse text-[#00D4AA]">|</span>
        </span>
    );
}

// Animated counter
function AnimatedCounter({ value, suffix = '' }: { value: number; suffix?: string }) {
    const [count, setCount] = useState(0);

    useEffect(() => {
        const duration = 2000;
        const steps = 60;
        const increment = value / steps;
        let current = 0;

        const interval = setInterval(() => {
            current += increment;
            if (current >= value) {
                setCount(value);
                clearInterval(interval);
            } else {
                setCount(Math.floor(current));
            }
        }, duration / steps);

        return () => clearInterval(interval);
    }, [value]);

    return <span>{count}{suffix}</span>;
}

// Feature card
function FeatureCard({ icon: Icon, title, description, delay }: {
    icon: React.ElementType;
    title: string;
    description: string;
    delay: number;
}) {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => setVisible(true), delay);
        return () => clearTimeout(timer);
    }, [delay]);

    return (
        <div className={`group relative bg-black/40 backdrop-blur-sm border border-white/5 rounded-2xl p-6 transition-all duration-500 hover:border-[#00D4AA]/30 hover:bg-[#00D4AA]/5 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
            <div className="absolute inset-0 bg-gradient-to-br from-[#00D4AA]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
            <div className="relative z-10">
                <div className="w-12 h-12 rounded-xl bg-[#00D4AA]/10 flex items-center justify-center mb-4 group-hover:bg-[#00D4AA]/20 transition-colors">
                    <Icon className="text-[#00D4AA]" size={24} />
                </div>
                <h3 className="text-white font-semibold text-lg mb-2">{title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{description}</p>
            </div>
        </div>
    );
}

export default function LandingPage() {
    const [loaded, setLoaded] = useState(false);
    const [scrollY, setScrollY] = useState(0);

    useEffect(() => {
        setLoaded(true);
        const handleScroll = () => setScrollY(window.scrollY);
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <div className="min-h-screen bg-black text-white overflow-x-hidden">
            {/* 3D Background */}
            <div className="fixed inset-0 z-0">
                <Suspense fallback={null}>
                    <Scene3D />
                </Suspense>
            </div>

            {/* Gradient overlays */}
            <div className="fixed inset-0 z-[1] pointer-events-none">
                <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black" />
                <div className="absolute inset-0 bg-gradient-to-r from-black/50 via-transparent to-black/50" />
            </div>

            {/* Scanlines effect */}
            <div className="fixed inset-0 z-[2] pointer-events-none opacity-20"
                style={{
                    backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.3) 2px, rgba(0,0,0,0.3) 4px)'
                }}
            />

            {/* Navigation */}
            <nav className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 relative">
                            <svg viewBox="0 0 40 40" className="w-full h-full">
                                <polygon points="20,2 38,11 38,29 20,38 2,29 2,11" stroke="#00D4AA" strokeWidth="1.5" fill="none" />
                                <circle cx="20" cy="20" r="6" fill="#00D4AA" />
                            </svg>
                        </div>
                        <span className="font-bold text-xl tracking-tight">TESTSPRITE</span>
                        <span className="text-[8px] font-medium tracking-widest text-[#00D4AA] bg-[#00D4AA]/10 px-2 py-0.5 rounded border border-[#00D4AA]/30">
                            AUTONOMOUS
                        </span>
                    </div>
                    <div className="hidden md:flex items-center gap-8">
                        <a href="#features" className="text-sm text-slate-400 hover:text-white transition-colors">Features</a>
                        <a href="#how-it-works" className="text-sm text-slate-400 hover:text-white transition-colors">How It Works</a>
                        <a href="#pricing" className="text-sm text-slate-400 hover:text-white transition-colors">Pricing</a>
                        <Link href="/dashboard" className="text-sm bg-[#00D4AA] text-black px-5 py-2 rounded-lg font-semibold hover:bg-[#00C099] transition-colors">
                            Launch Console
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative z-10 min-h-screen flex items-center justify-center px-6 pt-20">
                <div className="max-w-7xl mx-auto w-full grid lg:grid-cols-2 gap-12 items-center">
                    {/* Left: Text content */}
                    <div className={`space-y-8 transition-all duration-1000 ${loaded ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-12'}`}>
                        {/* Status badge */}
                        <div className="flex items-center gap-2">
                            <span className="w-2 h-2 bg-[#00D4AA] rounded-full animate-pulse shadow-lg shadow-[#00D4AA]/50" />
                            <span className="text-xs font-medium tracking-widest text-[#00D4AA] uppercase">System Online</span>
                        </div>

                        {/* Main headline */}
                        <h1 className="text-5xl md:text-7xl font-bold leading-tight">
                            <span className="text-slate-500">The</span>{' '}
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00D4AA] via-emerald-400 to-cyan-400">
                                Autonomous
                            </span>
                            <br />
                            <span className="text-white">Testing Agent</span>
                        </h1>

                        {/* Subtitle with typing effect */}
                        <div className="text-xl text-slate-400 max-w-lg font-light">
                            <TypeWriter text="AI that infiltrates your app. Discovers vulnerabilities. Writes tests. Self-heals." delay={30} />
                        </div>

                        {/* CTA buttons */}
                        <div className="flex flex-wrap gap-4 pt-4">
                            <Link href="/create" className="group relative bg-[#00D4AA] text-black px-8 py-4 rounded-xl font-bold text-sm flex items-center gap-2 overflow-hidden hover:shadow-lg hover:shadow-[#00D4AA]/30 transition-all">
                                <Bot size={18} />
                                <span>Deploy Agent</span>
                                <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                            </Link>
                            <Link href="/dashboard" className="bg-white/5 backdrop-blur-sm border border-white/10 text-white px-8 py-4 rounded-xl font-semibold text-sm hover:bg-white/10 hover:border-white/20 transition-all">
                                View Dashboard
                            </Link>
                        </div>

                        {/* Stats */}
                        <div className="flex gap-8 pt-8 border-t border-white/10">
                            <div>
                                <div className="text-3xl font-bold text-[#00D4AA]">
                                    <AnimatedCounter value={99} suffix="%" />
                                </div>
                                <div className="text-xs text-slate-500 uppercase tracking-wider">Accuracy</div>
                            </div>
                            <div>
                                <div className="text-3xl font-bold text-[#00D4AA]">
                                    <AnimatedCounter value={10} suffix="x" />
                                </div>
                                <div className="text-xs text-slate-500 uppercase tracking-wider">Faster</div>
                            </div>
                            <div>
                                <div className="text-3xl font-bold text-[#00D4AA]">
                                    <AnimatedCounter value={24} suffix="/7" />
                                </div>
                                <div className="text-xs text-slate-500 uppercase tracking-wider">Monitoring</div>
                            </div>
                        </div>
                    </div>

                    {/* Right: Hooded Figure */}
                    <div className={`relative flex items-center justify-center transition-all duration-1000 delay-300 ${loaded ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-12'}`}>
                        <div className="relative w-full max-w-lg aspect-square">
                            {/* Glow effect behind */}
                            <div className="absolute inset-0 bg-[#00D4AA]/10 rounded-full blur-[100px] animate-pulse" />

                            {/* Hooded figure */}
                            <Suspense fallback={<div className="w-full h-full animate-pulse bg-white/5 rounded-full" />}>
                                <HoodedFigure />
                            </Suspense>

                            {/* Floating badges */}
                            <div className="absolute top-10 -left-4 bg-black/80 backdrop-blur-sm border border-[#00D4AA]/30 rounded-lg px-3 py-2 animate-float">
                                <div className="flex items-center gap-2">
                                    <Scan size={14} className="text-[#00D4AA]" />
                                    <span className="text-xs text-slate-300">Scanning...</span>
                                </div>
                            </div>
                            <div className="absolute bottom-20 -right-4 bg-black/80 backdrop-blur-sm border border-emerald-500/30 rounded-lg px-3 py-2 animate-float-delayed">
                                <div className="flex items-center gap-2">
                                    <CheckCircle size={14} className="text-emerald-400" />
                                    <span className="text-xs text-slate-300">47 Tests Passed</span>
                                </div>
                            </div>
                            <div className="absolute top-1/2 -right-8 bg-black/80 backdrop-blur-sm border border-purple-500/30 rounded-lg px-3 py-2 animate-float">
                                <div className="flex items-center gap-2">
                                    <Lock size={14} className="text-purple-400" />
                                    <span className="text-xs text-slate-300">0 Vulnerabilities</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Scroll indicator */}
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 animate-bounce">
                    <span className="text-xs text-slate-500 uppercase tracking-widest">Scroll</span>
                    <ChevronDown size={20} className="text-[#00D4AA]" />
                </div>
            </section>

            {/* Features Section */}
            <section id="features" className="relative z-10 py-32 px-6">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl md:text-5xl font-bold mb-4">
                            <span className="text-slate-500">Powered by</span>{' '}
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00D4AA] to-emerald-400">
                                AI Agents
                            </span>
                        </h2>
                        <p className="text-slate-400 max-w-2xl mx-auto">
                            A fleet of specialized agents work together to analyze, plan, execute, and heal your test suite.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <FeatureCard
                            icon={Eye}
                            title="Deep Analysis"
                            description="AI crawls your entire application, mapping endpoints, forms, and user flows automatically."
                            delay={100}
                        />
                        <FeatureCard
                            icon={Code}
                            title="Auto Generation"
                            description="Generates comprehensive test suites covering edge cases, security, and performance."
                            delay={200}
                        />
                        <FeatureCard
                            icon={Terminal}
                            title="Live Execution"
                            description="Runs tests in real browsers with video recording and detailed logging."
                            delay={300}
                        />
                        <FeatureCard
                            icon={Shield}
                            title="Self-Healing"
                            description="Detects broken tests and automatically rewrites them to match UI changes."
                            delay={400}
                        />
                    </div>
                </div>
            </section>

            {/* How It Works Section */}
            <section id="how-it-works" className="relative z-10 py-32 px-6 bg-gradient-to-b from-transparent via-[#00D4AA]/5 to-transparent">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl md:text-5xl font-bold mb-4">
                            <span className="text-white">How It</span>{' '}
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00D4AA] to-cyan-400">
                                Works
                            </span>
                        </h2>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8">
                        {[
                            { step: '01', title: 'Point to Your App', description: 'Enter your URL or connect your repository. The agent begins reconnaissance.', icon: Scan },
                            { step: '02', title: 'AI Generates Tests', description: 'Autonomous agents analyze your app and generate comprehensive test scenarios.', icon: Cpu },
                            { step: '03', title: 'Execute & Monitor', description: 'Watch tests run in real-time with video playback and detailed reports.', icon: Zap },
                        ].map((item, i) => (
                            <div key={i} className="relative group">
                                <div className="absolute -inset-px bg-gradient-to-b from-[#00D4AA]/20 to-transparent rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
                                <div className="relative bg-black/60 backdrop-blur-sm border border-white/5 rounded-2xl p-8 h-full group-hover:border-[#00D4AA]/30 transition-colors">
                                    <div className="text-6xl font-bold text-[#00D4AA]/20 mb-4">{item.step}</div>
                                    <item.icon className="text-[#00D4AA] mb-4" size={32} />
                                    <h3 className="text-xl font-semibold text-white mb-2">{item.title}</h3>
                                    <p className="text-slate-400">{item.description}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="relative z-10 py-32 px-6">
                <div className="max-w-4xl mx-auto text-center">
                    <h2 className="text-4xl md:text-6xl font-bold mb-6">
                        Ready to <span className="text-[#00D4AA]">Deploy</span>?
                    </h2>
                    <p className="text-xl text-slate-400 mb-10">
                        Start testing your application in under 60 seconds.
                    </p>
                    <Link href="/create" className="inline-flex items-center gap-3 bg-[#00D4AA] text-black px-10 py-5 rounded-xl font-bold text-lg hover:shadow-lg hover:shadow-[#00D4AA]/30 transition-all hover:scale-105">
                        <Bot size={24} />
                        Launch TestSprite
                        <ArrowRight size={20} />
                    </Link>
                </div>
            </section>

            {/* Footer */}
            <footer className="relative z-10 border-t border-white/5 py-12 px-6">
                <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8">
                            <svg viewBox="0 0 40 40" className="w-full h-full">
                                <polygon points="20,2 38,11 38,29 20,38 2,29 2,11" stroke="#00D4AA" strokeWidth="1.5" fill="none" />
                                <circle cx="20" cy="20" r="6" fill="#00D4AA" />
                            </svg>
                        </div>
                        <span className="font-semibold">TESTSPRITE</span>
                    </div>
                    <div className="text-sm text-slate-500">
                        Autonomous AI Testing Platform
                    </div>
                    <div className="flex items-center gap-6 text-sm text-slate-500">
                        <a href="#" className="hover:text-white transition-colors">Docs</a>
                        <a href="#" className="hover:text-white transition-colors">GitHub</a>
                        <a href="#" className="hover:text-white transition-colors">Support</a>
                    </div>
                </div>
            </footer>

            {/* Custom styles */}
            <style jsx>{`
                @keyframes float {
                    0%, 100% { transform: translateY(0px); }
                    50% { transform: translateY(-10px); }
                }
                .animate-float {
                    animation: float 3s ease-in-out infinite;
                }
                .animate-float-delayed {
                    animation: float 3s ease-in-out infinite 1.5s;
                }
            `}</style>
        </div>
    );
}
