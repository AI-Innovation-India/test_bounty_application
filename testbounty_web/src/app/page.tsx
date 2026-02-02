"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { ArrowRight, Shield, Zap, Eye, Code, Play, CheckCircle } from "lucide-react";

// Dynamic import for 3D hoodie component
const AnimatedHoodie = dynamic(
    () => import("@/components/landing/AnimatedHoodie"),
    { ssr: false }
);

// Typewriter effect component
function TypeWriter({ texts, speed = 100 }: { texts: string[]; speed?: number }) {
    const [displayText, setDisplayText] = useState("");
    const [textIndex, setTextIndex] = useState(0);
    const [charIndex, setCharIndex] = useState(0);
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        const currentText = texts[textIndex];

        const timeout = setTimeout(() => {
            if (!isDeleting) {
                if (charIndex < currentText.length) {
                    setDisplayText(currentText.slice(0, charIndex + 1));
                    setCharIndex(charIndex + 1);
                } else {
                    setTimeout(() => setIsDeleting(true), 2000);
                }
            } else {
                if (charIndex > 0) {
                    setDisplayText(currentText.slice(0, charIndex - 1));
                    setCharIndex(charIndex - 1);
                } else {
                    setIsDeleting(false);
                    setTextIndex((textIndex + 1) % texts.length);
                }
            }
        }, isDeleting ? speed / 2 : speed);

        return () => clearTimeout(timeout);
    }, [charIndex, isDeleting, textIndex, texts, speed]);

    return (
        <span>
            {displayText}
            <span className="animate-pulse">|</span>
        </span>
    );
}

// Animated counter
function AnimatedCounter({ target, duration = 2000 }: { target: number; duration?: number }) {
    const [count, setCount] = useState(0);

    useEffect(() => {
        let start = 0;
        const increment = target / (duration / 16);

        const timer = setInterval(() => {
            start += increment;
            if (start >= target) {
                setCount(target);
                clearInterval(timer);
            } else {
                setCount(Math.floor(start));
            }
        }, 16);

        return () => clearInterval(timer);
    }, [target, duration]);

    return <span>{count.toLocaleString()}</span>;
}

export default function LandingPage() {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        setIsVisible(true);
    }, []);

    return (
        <div className="min-h-screen bg-[#0a0a0b] text-white overflow-x-hidden">
            {/* Navigation */}
            <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-black/30 border-b border-white/5">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#00D4AA] to-emerald-600 flex items-center justify-center font-black text-black text-sm">
                            TB
                        </div>
                        <span className="font-bold text-xl tracking-tight">TestBounty</span>
                    </div>
                    <div className="hidden md:flex items-center gap-8">
                        <a href="#features" className="text-sm text-slate-400 hover:text-white transition-colors">Features</a>
                        <a href="#how-it-works" className="text-sm text-slate-400 hover:text-white transition-colors">How it Works</a>
                        <a href="#pricing" className="text-sm text-slate-400 hover:text-white transition-colors">Pricing</a>
                    </div>
                    <div className="flex items-center gap-4">
                        <Link
                            href="/dashboard"
                            className="text-sm text-slate-400 hover:text-white transition-colors"
                        >
                            Sign In
                        </Link>
                        <Link
                            href="/dashboard"
                            className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-5 py-2.5 rounded-lg text-sm font-semibold transition-all hover:scale-105"
                        >
                            Get Started
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative min-h-screen flex items-center">
                {/* Animated Hoodie Background */}
                <div className="absolute inset-0 z-0">
                    <AnimatedHoodie />
                </div>

                {/* Gradient overlays */}
                <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/40 to-transparent z-10" />
                <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0b] via-transparent to-transparent z-10" />

                {/* Content */}
                <div className="relative z-20 max-w-7xl mx-auto px-6 pt-32 pb-20">
                    <div className="max-w-2xl">
                        <div
                            className={`transition-all duration-1000 ${isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"
                                }`}
                        >
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#00D4AA]/10 border border-[#00D4AA]/20 mb-8">
                                <span className="w-2 h-2 bg-[#00D4AA] rounded-full animate-pulse" />
                                <span className="text-sm text-[#00D4AA] font-medium">AI-Powered Testing Platform</span>
                            </div>

                            <h1 className="text-5xl md:text-7xl font-black leading-tight mb-6">
                                <span className="text-white">Hunt Bugs.</span>
                                <br />
                                <span className="bg-gradient-to-r from-[#00D4AA] to-emerald-400 bg-clip-text text-transparent">
                                    Claim Bounties.
                                </span>
                            </h1>

                            <p className="text-xl text-slate-400 mb-4 leading-relaxed">
                                Autonomous AI that writes, executes, and debugs your tests.
                            </p>

                            <div className="text-lg text-slate-300 mb-8 h-8">
                                <TypeWriter
                                    texts={[
                                        "Zero-code test automation",
                                        "Self-healing test scripts",
                                        "AI-powered bug detection",
                                        "Visual regression testing"
                                    ]}
                                    speed={80}
                                />
                            </div>

                            <div className="flex flex-col sm:flex-row gap-4 mb-12">
                                <Link
                                    href="/dashboard"
                                    className="group bg-[#00D4AA] hover:bg-[#00C099] text-black px-8 py-4 rounded-xl text-base font-bold transition-all hover:scale-105 flex items-center justify-center gap-3"
                                >
                                    Start Testing Free
                                    <ArrowRight className="group-hover:translate-x-1 transition-transform" size={20} />
                                </Link>
                                <a
                                    href="#demo"
                                    className="group bg-white/5 hover:bg-white/10 border border-white/10 text-white px-8 py-4 rounded-xl text-base font-semibold transition-all flex items-center justify-center gap-3"
                                >
                                    <Play size={20} className="text-[#00D4AA]" />
                                    Watch Demo
                                </a>
                            </div>

                            {/* Stats */}
                            <div className="grid grid-cols-3 gap-8 pt-8 border-t border-white/10">
                                <div>
                                    <div className="text-3xl font-bold text-white">
                                        <AnimatedCounter target={10000} />+
                                    </div>
                                    <div className="text-sm text-slate-500">Tests Generated</div>
                                </div>
                                <div>
                                    <div className="text-3xl font-bold text-white">
                                        <AnimatedCounter target={500} />+
                                    </div>
                                    <div className="text-sm text-slate-500">Bugs Found</div>
                                </div>
                                <div>
                                    <div className="text-3xl font-bold text-white">99%</div>
                                    <div className="text-sm text-slate-500">Accuracy Rate</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Scroll indicator */}
                <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-20 animate-bounce">
                    <div className="w-6 h-10 rounded-full border-2 border-white/20 flex items-start justify-center p-2">
                        <div className="w-1 h-2 bg-white/40 rounded-full animate-scroll" />
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section id="features" className="py-32 relative">
                <div className="absolute inset-0 bg-gradient-to-b from-[#0a0a0b] via-[#0f0f11] to-[#0a0a0b]" />

                <div className="relative max-w-7xl mx-auto px-6">
                    <div className="text-center mb-20">
                        <h2 className="text-4xl md:text-5xl font-bold mb-6">
                            Autonomous Testing,{" "}
                            <span className="bg-gradient-to-r from-[#00D4AA] to-emerald-400 bg-clip-text text-transparent">
                                Reimagined
                            </span>
                        </h2>
                        <p className="text-xl text-slate-400 max-w-2xl mx-auto">
                            Let AI handle the tedious work while you focus on building great products.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {[
                            {
                                icon: <Shield size={28} />,
                                title: "Security Testing",
                                description: "OWASP Top 10 coverage including SQL injection, XSS, and CSRF detection."
                            },
                            {
                                icon: <Zap size={28} />,
                                title: "Self-Healing Scripts",
                                description: "AI automatically fixes broken selectors and adapts to UI changes."
                            },
                            {
                                icon: <Eye size={28} />,
                                title: "Visual Regression",
                                description: "Pixel-perfect screenshot comparison to catch visual bugs."
                            },
                            {
                                icon: <Code size={28} />,
                                title: "Code Generation",
                                description: "Generates production-ready Playwright test scripts automatically."
                            },
                            {
                                icon: <Play size={28} />,
                                title: "Video Recording",
                                description: "Full video capture of every test run for easy debugging."
                            },
                            {
                                icon: <CheckCircle size={28} />,
                                title: "Smart Reports",
                                description: "Detailed HTML reports with actionable insights and metrics."
                            }
                        ].map((feature, index) => (
                            <div
                                key={index}
                                className="group bg-[#121214] border border-white/5 rounded-2xl p-8 hover:border-[#00D4AA]/30 transition-all duration-300 hover:-translate-y-2"
                            >
                                <div className="w-14 h-14 bg-[#00D4AA]/10 rounded-xl flex items-center justify-center text-[#00D4AA] mb-6 group-hover:scale-110 transition-transform">
                                    {feature.icon}
                                </div>
                                <h3 className="text-xl font-semibold text-white mb-3">{feature.title}</h3>
                                <p className="text-slate-400 leading-relaxed">{feature.description}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* How it Works */}
            <section id="how-it-works" className="py-32 relative overflow-hidden">
                <div className="absolute inset-0 bg-[#0f0f11]" />

                <div className="relative max-w-7xl mx-auto px-6">
                    <div className="text-center mb-20">
                        <h2 className="text-4xl md:text-5xl font-bold mb-6">
                            How{" "}
                            <span className="bg-gradient-to-r from-[#00D4AA] to-emerald-400 bg-clip-text text-transparent">
                                TestBounty
                            </span>{" "}
                            Works
                        </h2>
                        <p className="text-xl text-slate-400 max-w-2xl mx-auto">
                            From URL to comprehensive test coverage in minutes.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-12">
                        {[
                            {
                                step: "01",
                                title: "Enter Your URL",
                                description: "Just paste your application URL and let TestBounty analyze your app's structure and user flows."
                            },
                            {
                                step: "02",
                                title: "AI Generates Tests",
                                description: "Our AI creates comprehensive test scenarios covering functional, edge cases, and security testing."
                            },
                            {
                                step: "03",
                                title: "Review & Execute",
                                description: "Watch tests run in real-time with video recording, then review detailed reports and fix bugs."
                            }
                        ].map((item, index) => (
                            <div key={index} className="relative">
                                <div className="text-8xl font-black text-[#00D4AA]/5 absolute -top-6 -left-4">
                                    {item.step}
                                </div>
                                <div className="relative">
                                    <div className="w-12 h-12 bg-[#00D4AA] rounded-xl flex items-center justify-center text-black font-bold text-lg mb-6">
                                        {item.step}
                                    </div>
                                    <h3 className="text-2xl font-semibold text-white mb-4">{item.title}</h3>
                                    <p className="text-slate-400 leading-relaxed">{item.description}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-32 relative">
                <div className="absolute inset-0 bg-gradient-to-b from-[#0f0f11] to-[#0a0a0b]" />
                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiMwMEQ0QUEiIGZpbGwtb3BhY2l0eT0iMC4wMiI+PGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIvPjwvZz48L2c+PC9zdmc+')] opacity-50" />

                <div className="relative max-w-4xl mx-auto px-6 text-center">
                    <h2 className="text-4xl md:text-6xl font-bold mb-6">
                        Ready to{" "}
                        <span className="bg-gradient-to-r from-[#00D4AA] to-emerald-400 bg-clip-text text-transparent">
                            Hunt Bugs
                        </span>
                        ?
                    </h2>
                    <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto">
                        Join thousands of developers who trust TestBounty for their QA automation.
                        Start testing in under 60 seconds.
                    </p>
                    <Link
                        href="/dashboard"
                        className="inline-flex items-center gap-3 bg-[#00D4AA] hover:bg-[#00C099] text-black px-10 py-5 rounded-xl text-lg font-bold transition-all hover:scale-105"
                    >
                        Get Started for Free
                        <ArrowRight size={24} />
                    </Link>
                    <p className="text-sm text-slate-500 mt-6">No credit card required</p>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-white/5 py-12">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00D4AA] to-emerald-600 flex items-center justify-center font-bold text-black text-xs">
                                TB
                            </div>
                            <span className="font-semibold">TestBounty</span>
                        </div>
                        <div className="text-sm text-slate-500">
                            © 2026 TestBounty. All rights reserved.
                        </div>
                    </div>
                </div>
            </footer>

            {/* Custom styles */}
            <style jsx>{`
                @keyframes scroll {
                    0%, 100% { transform: translateY(0); opacity: 1; }
                    50% { transform: translateY(4px); opacity: 0.5; }
                }
                .animate-scroll {
                    animation: scroll 1.5s ease-in-out infinite;
                }
            `}</style>
        </div>
    );
}
