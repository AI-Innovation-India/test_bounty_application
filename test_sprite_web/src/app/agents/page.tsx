"use client";

import Sidebar from "@/components/Sidebar";
import Link from "next/link";
import { Search, FileText, Terminal, Shield, CheckCircle, Zap } from "lucide-react";

export default function AgentsPage() {
    const agents = [
        {
            id: "analyst",
            name: "Code Analyst",
            role: "Discovery & Analysis",
            description: "Deep scans your repository or live URL to understand structure, tech stack, and logic flows. It builds a semantic map of your application to guide other agents.",
            technical_capability: "Static AST Analysis (Python/JS) + Dynamic Crawling",
            icon: <Search className="text-sky-400" size={32} />,
            color: "border-sky-500/20 bg-sky-500/5",
            status: "Online"
        },
        {
            id: "architect",
            name: "Test Architect",
            role: "Planning & Strategy",
            description: "Generates standardized PRDs and comprehensive test plans. It determines the optimal coverage strategy for both frontend (E2E) and backend (API) layers.",
            technical_capability: "LLM-based Test Case Generation & PRD Synthesis",
            icon: <FileText className="text-purple-400" size={32} />,
            color: "border-purple-500/20 bg-purple-500/5",
            status: "Online"
        },
        {
            id: "executor",
            name: "Execution Engine",
            role: "Implementation & Runner",
            description: "Writes and runs code-based tests autonomously. It handles environment setup, dependency management, and safe execution of test suites.",
            technical_capability: "Sandboxed PyTest/Playwright Execution",
            icon: <Terminal className="text-[#00D4AA]" size={32} />,
            color: "border-[#00D4AA]/20 bg-[#00D4AA]/5",
            status: "Idle"
        },
        {
            id: "healer",
            name: "Self-Healer",
            role: "Maintenance & Repair",
            description: "Detects test failures, analyzes error logs, and autonomously rewrites test code to fix broken selectors or logic errors.",
            technical_capability: "Error Log Analysis & Iterative Code Patching",
            icon: <Shield className="text-emerald-400" size={32} />,
            color: "border-emerald-500/20 bg-emerald-500/5",
            status: "Online"
        },
        {
            id: "auditor",
            name: "Security Auditor",
            role: "Security & Penetration",
            description: "Performs automated DAST scanning to identify OWASP Top 10 vulnerabilities like SQL injection, XSS, and IDOR.",
            technical_capability: "Payload Fuzzing & Vulnerability Scanning",
            icon: <Shield className="text-red-400" size={32} />,
            color: "border-red-500/20 bg-red-500/5",
            status: "Online"
        }
    ];

    return (
        <div className="flex min-h-screen bg-[#0E0E0E] text-slate-200 font-sans selection:bg-[#00D4AA]/30">
            <Sidebar />
            <main className="flex-1 ml-64 p-8">
                <header className="flex items-center justify-between mb-10">
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                        <span className="text-slate-300">AI Test Studio</span>
                        <span>/</span>
                        <span className="text-white">Agents</span>
                    </div>
                    <Link href="/create">
                        <button className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-colors">
                            <Zap size={16} /> Start Agent Run
                        </button>
                    </Link>
                </header>

                <div className="max-w-5xl mx-auto">
                    <div className="mb-12">
                        <h1 className="text-3xl font-bold text-white mb-4">Agent Fleet Capabilities</h1>
                        <p className="text-slate-400 max-w-3xl text-lg">
                            TestSprite employs a multi-agent architecture where specialized AI agents collaborate to deliver autonomous QA. Here is the current status of your fleet.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 gap-6">
                        {agents.map((agent) => (
                            <div key={agent.id} className={`p-6 rounded-xl border ${agent.color} flex flex-col md:flex-row gap-6 items-start hover:bg-white/[0.02] transition-colors`}>
                                <div className="p-4 rounded-lg bg-[#121214] border border-white/5 shrink-0">
                                    {agent.icon}
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-start justify-between mb-2">
                                        <div>
                                            <h3 className="text-xl font-bold text-white">{agent.name}</h3>
                                            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-1">{agent.role}</div>
                                        </div>
                                        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#121214] border border-white/10">
                                            <div className="w-2 h-2 rounded-full bg-[#00D4AA] animate-pulse"></div>
                                            <span className="text-xs font-medium text-[#00D4AA]">{agent.status}</span>
                                        </div>
                                    </div>
                                    <p className="text-slate-400 mb-4 leading-relaxed">
                                        {agent.description}
                                    </p>
                                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded bg-black/40 border border-white/5 text-xs text-slate-500 font-mono">
                                        <Terminal size={12} />
                                        {agent.technical_capability}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </main>
        </div>
    );
}
