"use client";

import Link from "next/link";
import { ArrowRight, Shield, Zap, Eye, Code, Play, BarChart3, Bug, Target, CheckCircle } from "lucide-react";

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-[#0a0a0b] text-white">
            {/* Navigation */}
            <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0a0a0b]/90 backdrop-blur-sm border-b border-white/5">
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
                    </div>
                    <div className="flex items-center gap-4">
                        <Link
                            href="/testing"
                            className="text-sm text-slate-400 hover:text-white transition-colors"
                        >
                            Sign In
                        </Link>
                        <Link
                            href="/create"
                            className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-5 py-2.5 rounded-lg text-sm font-semibold transition-colors"
                        >
                            Get Started
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="pt-32 pb-20 px-6">
                <div className="max-w-7xl mx-auto">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        {/* Left content */}
                        <div>
                            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#00D4AA]/10 border border-[#00D4AA]/20 mb-8">
                                <span className="w-2 h-2 bg-[#00D4AA] rounded-full" />
                                <span className="text-sm text-[#00D4AA] font-medium">AI-Powered Testing Platform</span>
                            </div>

                            <h1 className="text-5xl md:text-6xl font-black leading-tight mb-6">
                                <span className="text-white">Hunt Bugs.</span>
                                <br />
                                <span className="text-[#00D4AA]">Claim Bounties.</span>
                            </h1>

                            <p className="text-xl text-slate-400 mb-8 leading-relaxed max-w-lg">
                                Autonomous AI that writes, executes, and debugs your tests. Ship with confidence.
                            </p>

                            <div className="flex flex-col sm:flex-row gap-4 mb-12">
                                <Link
                                    href="/create"
                                    className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-8 py-4 rounded-xl text-base font-bold transition-colors flex items-center justify-center gap-3"
                                >
                                    Start Testing Free
                                    <ArrowRight size={20} />
                                </Link>
                                <Link
                                    href="/testing"
                                    className="bg-white/5 hover:bg-white/10 border border-white/10 text-white px-8 py-4 rounded-xl text-base font-semibold transition-colors flex items-center justify-center gap-3"
                                >
                                    <Play size={20} className="text-[#00D4AA]" />
                                    View Tests
                                </Link>
                            </div>

                            {/* Stats */}
                            <div className="grid grid-cols-3 gap-8 pt-8 border-t border-white/10">
                                <div>
                                    <div className="text-3xl font-bold text-white">10K+</div>
                                    <div className="text-sm text-slate-500">Tests Generated</div>
                                </div>
                                <div>
                                    <div className="text-3xl font-bold text-white">500+</div>
                                    <div className="text-sm text-slate-500">Bugs Found</div>
                                </div>
                                <div>
                                    <div className="text-3xl font-bold text-white">99%</div>
                                    <div className="text-sm text-slate-500">Accuracy</div>
                                </div>
                            </div>
                        </div>

                        {/* Right - Terminal illustration */}
                        <div className="hidden lg:block">
                            <div className="bg-[#121214] border border-white/10 rounded-2xl p-6 shadow-2xl relative">
                                {/* Terminal header */}
                                <div className="flex items-center gap-2 mb-4">
                                    <div className="w-3 h-3 rounded-full bg-red-500" />
                                    <div className="w-3 h-3 rounded-full bg-yellow-500" />
                                    <div className="w-3 h-3 rounded-full bg-green-500" />
                                    <span className="ml-3 text-xs text-slate-500">testbounty-agent</span>
                                </div>

                                {/* Terminal content */}
                                <div className="font-mono text-sm space-y-3">
                                    <div className="flex items-center gap-2">
                                        <span className="text-[#00D4AA]">$</span>
                                        <span className="text-slate-300">testbounty run --url https://myapp.com</span>
                                    </div>
                                    <div className="text-slate-500 text-xs pl-4">Analyzing application structure...</div>
                                    <div className="text-slate-500 text-xs pl-4">Generating test scenarios...</div>
                                    <div className="flex items-center gap-2 text-emerald-400 pl-4">
                                        <CheckCircle size={14} />
                                        <span>12 test cases generated</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-emerald-400 pl-4">
                                        <CheckCircle size={14} />
                                        <span>Running automated tests...</span>
                                    </div>
                                    <div className="mt-4 pt-4 border-t border-white/5">
                                        <div className="flex items-center justify-between text-xs mb-2">
                                            <span className="text-slate-400">Tests: 12</span>
                                            <span className="text-emerald-400">Passed: 10</span>
                                            <span className="text-red-400">Failed: 2</span>
                                        </div>
                                        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                            <div className="h-full bg-[#00D4AA] rounded-full w-4/5" />
                                        </div>
                                    </div>
                                </div>

                                {/* Floating badges */}
                                <div className="absolute -top-3 -right-3 bg-[#00D4AA] text-black px-3 py-1.5 rounded-lg text-xs font-bold shadow-lg flex items-center gap-1">
                                    <Bug size={14} />
                                    2 Bugs Found!
                                </div>
                                <div className="absolute -bottom-3 -left-3 bg-[#1a1a1d] border border-white/10 px-3 py-1.5 rounded-lg text-xs shadow-lg flex items-center gap-1">
                                    <Target size={14} className="text-[#00D4AA]" />
                                    <span className="text-slate-300">Coverage: 94%</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section id="features" className="py-20 px-6 bg-[#0f0f11]">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-bold mb-4">
                            Autonomous Testing, <span className="text-[#00D4AA]">Reimagined</span>
                        </h2>
                        <p className="text-lg text-slate-400 max-w-2xl mx-auto">
                            Let AI handle the tedious work while you focus on building great products.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {[
                            { icon: Shield, title: "Security Testing", desc: "OWASP Top 10 coverage including SQL injection, XSS, and CSRF detection." },
                            { icon: Zap, title: "Self-Healing Scripts", desc: "AI automatically fixes broken selectors and adapts to UI changes." },
                            { icon: Eye, title: "Visual Regression", desc: "Pixel-perfect screenshot comparison to catch visual bugs." },
                            { icon: Code, title: "Code Generation", desc: "Generates production-ready Playwright test scripts automatically." },
                            { icon: Play, title: "Video Recording", desc: "Full video capture of every test run for easy debugging." },
                            { icon: BarChart3, title: "Smart Reports", desc: "Detailed HTML reports with actionable insights and metrics." }
                        ].map((feature, i) => (
                            <div key={i} className="bg-[#121214] border border-white/5 rounded-xl p-6 hover:border-[#00D4AA]/30 transition-colors">
                                <div className="w-12 h-12 bg-[#00D4AA]/10 rounded-lg flex items-center justify-center text-[#00D4AA] mb-4">
                                    <feature.icon size={24} />
                                </div>
                                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                                <p className="text-slate-400 text-sm leading-relaxed">{feature.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* How it Works */}
            <section id="how-it-works" className="py-20 px-6">
                <div className="max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-bold mb-4">
                            How <span className="text-[#00D4AA]">TestBounty</span> Works
                        </h2>
                        <p className="text-lg text-slate-400">
                            From URL to comprehensive test coverage in minutes.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8">
                        {[
                            { step: "01", title: "Enter Your URL", desc: "Paste your application URL and let TestBounty analyze your app." },
                            { step: "02", title: "AI Generates Tests", desc: "Our AI creates test scenarios covering functional and security testing." },
                            { step: "03", title: "Review & Execute", desc: "Watch tests run in real-time, then review detailed reports." }
                        ].map((item, i) => (
                            <div key={i} className="text-center">
                                <div className="w-14 h-14 bg-[#00D4AA] rounded-xl flex items-center justify-center text-black font-bold text-xl mx-auto mb-4">
                                    {item.step}
                                </div>
                                <h3 className="text-xl font-semibold text-white mb-2">{item.title}</h3>
                                <p className="text-slate-400">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20 px-6 bg-[#0f0f11]">
                <div className="max-w-3xl mx-auto text-center">
                    <h2 className="text-4xl font-bold mb-4">
                        Ready to <span className="text-[#00D4AA]">Hunt Bugs</span>?
                    </h2>
                    <p className="text-lg text-slate-400 mb-8">
                        Start testing in under 60 seconds. No credit card required.
                    </p>
                    <Link
                        href="/create"
                        className="inline-flex items-center gap-3 bg-[#00D4AA] hover:bg-[#00C099] text-black px-10 py-4 rounded-xl text-lg font-bold transition-colors"
                    >
                        Get Started for Free
                        <ArrowRight size={24} />
                    </Link>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-white/5 py-8 px-6">
                <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00D4AA] to-emerald-600 flex items-center justify-center font-bold text-black text-xs">
                            TB
                        </div>
                        <span className="font-semibold">TestBounty</span>
                    </div>
                    <div className="flex items-center gap-6 text-sm text-slate-500">
                        <Link href="/testing" className="hover:text-white transition-colors">All Tests</Link>
                        <Link href="/create" className="hover:text-white transition-colors">Create Test</Link>
                        <Link href="/monitoring" className="hover:text-white transition-colors">Monitoring</Link>
                    </div>
                    <div className="text-sm text-slate-500">
                        2026 TestBounty
                    </div>
                </div>
            </footer>
        </div>
    );
}
