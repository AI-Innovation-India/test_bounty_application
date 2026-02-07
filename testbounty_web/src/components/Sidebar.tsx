"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    Home, List, Activity, Settings,
    User, Zap, LogOut, Trash2, Target
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
        if (!confirm("Are you sure you want to delete ALL test runs? This action cannot be undone.")) return;
        try {
            await deleteAllRuns();
            // Refresh the page to update the list
            window.location.reload();
        } catch (e) {
            console.error("Failed to delete all:", e);
            alert("Failed to delete all runs");
        }
    };

    return (
        <aside className="w-64 border-r border-white/5 bg-[#0A0A0B] flex flex-col fixed h-full z-20">
            <div className="p-6 flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-gradient-to-br from-[#00D4AA] to-emerald-600 flex items-center justify-center font-bold text-black text-xs">
                    TB
                </div>
                <span className="font-bold tracking-tight text-white">TestBounty</span>
            </div>

            <nav className="flex-1 px-4 space-y-8 overflow-y-auto">
                <div>
                    <div className="text-xs font-semibold text-slate-500 mb-2 px-2 tracking-wider">OVERVIEW</div>
                    <NavItem icon={<Home size={18} />} label="Home" href="/" active={isActive("/")} />
                    <NavItem icon={<Activity size={18} />} label="Agents" href="/agents" active={isActive("/agents")} />
                </div>

                <div>
                    <div className="text-xs font-semibold text-slate-500 mb-2 px-2 tracking-wider">TESTING</div>
                    <NavItem icon={<Target size={18} />} label="Scenarios" href="/scenarios" active={isActive("/scenarios")} />
                    <NavItem icon={<Zap size={18} />} label="Create Tests" href="/create" active={isActive("/create")} />
                    <NavItem icon={<List size={18} />} label="All Tests" href="/testing" active={isActive("/testing")} />
                    <NavItem icon={<List size={18} />} label="Test Suites" href="/test-lists" active={isActive("/test-lists")} />
                    <NavItem icon={<Activity size={18} />} label="Monitoring" href="/monitoring" active={isActive("/monitoring")} />
                    {isActive("/testing") && (
                        <button
                            onClick={handleDeleteAll}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-red-400 hover:text-red-300 hover:bg-red-500/10 w-full mt-2 border border-red-500/20"
                        >
                            <Trash2 size={18} />
                            Delete All Tests
                        </button>
                    )}
                </div>

                <div>
                    <div className="text-xs font-semibold text-slate-500 mb-2 px-2 tracking-wider">SETTINGS</div>
                    <NavItem icon={<User size={18} />} label="Profile" href="/profile" active={isActive("/profile")} />
                </div>
            </nav>

            <div className="p-4 border-t border-white/5 bg-[#0F0F11]">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700"></div>
                    <div className="flex-1">
                        <div className="text-sm font-medium text-white">AI Agent</div>
                        <div className="text-xs text-slate-500">Free Plan</div>
                    </div>
                </div>
            </div>
        </aside>
    );
}

function NavItem({ icon, label, href = "#", active = false }: { icon: any, label: string, href?: string, active?: boolean }) {
    return (
        <Link
            href={href}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${active ? 'bg-[#00D4AA]/10 text-[#00D4AA]' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
        >
            {icon}
            {label}
        </Link>
    )
}
