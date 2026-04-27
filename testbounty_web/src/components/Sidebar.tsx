"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard, Brain, List, Activity, Settings,
    User, Trash2, Target, PlayCircle, Bot
} from "lucide-react";
import { deleteAllRuns } from "@/lib/api";

export default function Sidebar() {
    const pathname = usePathname();

    const isActive = (path: string) => {
        if (path === "/" && pathname === "/") return true;
        if (path !== "/" && pathname.startsWith(path)) return true;
        return false;
    };

    const handleDeleteAll = async () => {
        if (!confirm("Delete ALL test runs? This cannot be undone.")) return;
        try {
            await deleteAllRuns();
            window.location.reload();
        } catch (e) {
            alert("Failed to delete all runs");
        }
    };

    return (
        <aside className="w-60 border-r border-white/5 bg-[#0A0A0B] flex flex-col fixed h-full z-20">
            {/* Logo */}
            <div className="p-5 flex items-center gap-3 border-b border-white/5">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00D4AA] to-emerald-600 flex items-center justify-center font-bold text-black text-xs shrink-0">
                    TB
                </div>
                <div>
                    <span className="font-bold tracking-tight text-white text-sm">TestBounty</span>
                    <div className="text-xs text-slate-600">AI Testing Platform</div>
                </div>
            </div>

            <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">

                {/* Overview */}
                <div>
                    <div className="text-xs font-semibold text-slate-600 mb-1.5 px-2 tracking-widest uppercase">Overview</div>
                    <NavItem icon={<LayoutDashboard size={16} />} label="Dashboard" href="/" active={isActive("/")} />
                </div>

                {/* AI Testing */}
                <div>
                    <div className="text-xs font-semibold text-slate-600 mb-1.5 px-2 tracking-widest uppercase">AI Testing</div>
                    <NavItem
                        icon={<Bot size={16} />}
                        label="Autonomous"
                        href="/autonomous"
                        active={isActive("/autonomous")}
                        badge="NEW"
                    />
                    <NavItem
                        icon={<Brain size={16} />}
                        label="Scenarios"
                        href="/scenarios"
                        active={isActive("/scenarios")}
                        badge="AI"
                    />
                    <NavItem icon={<PlayCircle size={16} />} label="Test Runs" href="/testing" active={isActive("/testing")} />
                    {isActive("/testing") && (
                        <button
                            onClick={handleDeleteAll}
                            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 w-full mt-1 border border-red-500/20 transition-colors"
                        >
                            <Trash2 size={14} />
                            Delete All Runs
                        </button>
                    )}
                </div>

                {/* Automation */}
                <div>
                    <div className="text-xs font-semibold text-slate-600 mb-1.5 px-2 tracking-widest uppercase">Automation</div>
                    <NavItem icon={<Target size={16} />} label="Test Suites" href="/test-lists" active={isActive("/test-lists")} />
                    <NavItem icon={<Activity size={16} />} label="Monitoring" href="/monitoring" active={isActive("/monitoring")} />
                </div>

                {/* Settings */}
                <div>
                    <div className="text-xs font-semibold text-slate-600 mb-1.5 px-2 tracking-widest uppercase">Settings</div>
                    <NavItem icon={<User size={16} />} label="Profile" href="/profile" active={isActive("/profile")} />
                </div>
            </nav>

            {/* Footer */}
            <div className="p-3 border-t border-white/5">
                <div className="flex items-center gap-3 px-2 py-2">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-slate-700 to-slate-800 border border-slate-700 flex items-center justify-center text-xs text-slate-400 font-bold">
                        U
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-white truncate">AI Agent</div>
                        <div className="text-xs text-slate-600">Free Plan</div>
                    </div>
                </div>
            </div>
        </aside>
    );
}

function NavItem({
    icon, label, href = "#", active = false, badge
}: {
    icon: React.ReactNode;
    label: string;
    href?: string;
    active?: boolean;
    badge?: string;
}) {
    return (
        <Link
            href={href}
            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                    ? "bg-[#00D4AA]/10 text-[#00D4AA]"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
            }`}
        >
            {icon}
            <span className="flex-1">{label}</span>
            {badge && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-[#00D4AA]/15 text-[#00D4AA] font-semibold">
                    {badge}
                </span>
            )}
        </Link>
    );
}
