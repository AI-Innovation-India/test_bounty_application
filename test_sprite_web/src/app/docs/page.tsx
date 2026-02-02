"use client";

import Sidebar from "@/components/Sidebar";
import { Book, FileText, Code, Terminal } from "lucide-react";

export default function DocsPage() {
    const sections = [
        {
            title: "Getting Started",
            icon: <Book className="text-[#00D4AA]" size={24} />,
            items: ["Installation", "Configuration", "First Test Run"]
        },
        {
            title: "Core Concepts",
            icon: <Code className="text-purple-400" size={24} />,
            items: ["Agents", "Workflows", "Test Plans", "Reporting"]
        },
        {
            title: "API Reference",
            icon: <Terminal className="text-sky-400" size={24} />,
            items: ["Endpoints", "Authentication", "Rate Limits"]
        },
        {
            title: "Guides",
            icon: <FileText className="text-amber-400" size={24} />,
            items: ["Best Practices", "CI/CD Integration", "Troubleshooting"]
        }
    ];

    return (
        <div className="flex min-h-screen bg-[#0E0E0E] text-slate-200 font-sans selection:bg-[#00D4AA]/30">
            <Sidebar />

            <main className="flex-1 ml-64 p-8">
                <header className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                        <span className="text-slate-300">AI Test Studio</span>
                        <span>/</span>
                        <span className="text-white">Documentation</span>
                    </div>
                </header>

                <div className="max-w-5xl mx-auto">
                    <div className="mb-10 text-center">
                        <h1 className="text-3xl font-bold text-white mb-4">Documentation</h1>
                        <p className="text-slate-400 max-w-2xl mx-auto">
                            Everything you need to know about using AI Test Studio to automate your quality assurance workflows.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {sections.map((section, idx) => (
                            <div key={idx} className="bg-[#121214] border border-white/5 rounded-xl p-6 hover:border-white/10 transition-colors group">
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="p-3 bg-white/5 rounded-lg group-hover:bg-white/10 transition-colors">
                                        {section.icon}
                                    </div>
                                    <h2 className="text-lg font-semibold text-white">{section.title}</h2>
                                </div>
                                <ul className="space-y-2 pl-4 border-l border-white/5">
                                    {section.items.map((item, itemIdx) => (
                                        <li key={itemIdx}>
                                            <button className="text-sm text-slate-400 hover:text-[#00D4AA] transition-colors text-left w-full block py-1">
                                                {item}
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>
                </div>
            </main>
        </div>
    );
}
