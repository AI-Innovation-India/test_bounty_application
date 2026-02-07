"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { listRuns, Run, deleteRun, deleteAllRuns, getReportDownloadUrl } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import {
    Search, Filter, Plus, MoreVertical,
    CheckCircle, XCircle, Clock, ArrowRight,
    ChevronLeft, ChevronRight, Trash2, Download
} from "lucide-react";

export default function AllTestsPage() {
    const [runs, setRuns] = useState<Run[]>([]);
    const [loading, setLoading] = useState(true);
    const [openMenuId, setOpenMenuId] = useState<string | null>(null);
    const [deleting, setDeleting] = useState<string | null>(null);
    const [selectedRuns, setSelectedRuns] = useState<Set<string>>(new Set());
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        loadRuns();
    }, []);

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setOpenMenuId(null);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const loadRuns = async () => {
        try {
            const data = await listRuns();
            setRuns(data.reverse());
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (runId: string) => {
        if (!confirm("Are you sure you want to delete this test run?")) return;
        setDeleting(runId);
        try {
            await deleteRun(runId);
            setRuns(runs.filter(r => r.id !== runId));
        } catch (e) {
            console.error("Failed to delete:", e);
            alert("Failed to delete the run");
        } finally {
            setDeleting(null);
            setOpenMenuId(null);
        }
    };

    const toggleSelectAll = () => {
        if (selectedRuns.size === runs.length) {
            setSelectedRuns(new Set());
        } else {
            setSelectedRuns(new Set(runs.map(r => r.id)));
        }
    };

    const toggleSelectRun = (runId: string) => {
        const newSelected = new Set(selectedRuns);
        if (newSelected.has(runId)) {
            newSelected.delete(runId);
        } else {
            newSelected.add(runId);
        }
        setSelectedRuns(newSelected);
    };

    const handleDeleteAll = async () => {
        const countToDelete = selectedRuns.size > 0 ? selectedRuns.size : runs.length;
        const message = selectedRuns.size > 0
            ? `Are you sure you want to delete ${countToDelete} selected test run(s)?`
            : "Are you sure you want to delete ALL test runs? This action cannot be undone.";

        if (!confirm(message)) return;

        setLoading(true);
        try {
            if (selectedRuns.size > 0) {
                // Delete only selected runs
                await Promise.all(Array.from(selectedRuns).map(id => deleteRun(id)));
                setRuns(runs.filter(r => !selectedRuns.has(r.id)));
                setSelectedRuns(new Set());
            } else {
                // Delete all runs
                await deleteAllRuns();
                setRuns([]);
            }
        } catch (e) {
            console.error("Failed to delete:", e);
            alert("Failed to delete runs");
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadReport = (runId: string) => {
        const url = getReportDownloadUrl(runId);
        window.open(url, "_blank");
        setOpenMenuId(null);
    };

    return (
        <div className="flex min-h-screen bg-[#0E0E0E] text-slate-200 font-sans selection:bg-[#00D4AA]/30">
            <Sidebar />

            <main className="flex-1 ml-64 p-8">
                {/* Header */}
                <header className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                        <span className="text-slate-300">TestBounty</span>
                        <span>/</span>
                        <span className="text-white">All Tests</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <button className="text-sm text-slate-400 hover:text-white">Share Feedback</button>
                        <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center text-xs font-bold">A</div>
                    </div>
                </header>

                {/* Toolbar */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3 flex-1">
                        <div className="relative w-64">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
                            <input
                                type="text"
                                placeholder="Search"
                                className="w-full bg-[#121214] border border-white/5 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-[#00D4AA]/50"
                            />
                        </div>
                        <button className="flex items-center gap-2 px-3 py-2 bg-[#121214] border border-white/5 rounded-lg text-sm text-slate-300 hover:bg-white/5">
                            <Filter size={16} /> Filter
                        </button>
                        <div className="text-sm text-slate-500 ml-4">
                            Sort: <span className="text-white">Created At</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        {runs.length > 0 && (
                            <button
                                onClick={handleDeleteAll}
                                className="bg-red-500/10 hover:bg-red-500/20 text-red-400 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 border border-red-500/20 transition-colors"
                            >
                                <Trash2 size={16} />
                                {selectedRuns.size > 0 ? `Delete Selected (${selectedRuns.size})` : 'Delete All'}
                            </button>
                        )}
                        <Link href="/">
                            <button className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-transform hover:scale-105">
                                <Plus size={16} className="fill-black" /> Create Tests
                            </button>
                        </Link>
                    </div>
                </div>

                {/* Table */}
                <div className="bg-[#121214] border border-white/5 rounded-xl overflow-hidden">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-[#0F0F11] border-b border-white/5 text-slate-500 font-medium">
                            <tr>
                                <th className="px-6 py-4 w-12">
                                    <input
                                        type="checkbox"
                                        checked={runs.length > 0 && selectedRuns.size === runs.length}
                                        onChange={toggleSelectAll}
                                        className="rounded border-slate-700 bg-transparent cursor-pointer"
                                    />
                                </th>
                                <th className="px-6 py-4">Test Name</th>
                                <th className="px-6 py-4">Type</th>
                                <th className="px-6 py-4">Latest Status</th>
                                <th className="px-6 py-4">Category</th>
                                <th className="px-6 py-4">Created At</th>
                                <th className="px-6 py-4 w-12"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {runs.map((run) => (
                                <tr key={run.id} className="group hover:bg-white/[0.02] transition-colors">
                                    <td className="px-6 py-4">
                                        <input
                                            type="checkbox"
                                            checked={selectedRuns.has(run.id)}
                                            onChange={() => toggleSelectRun(run.id)}
                                            className="rounded border-slate-700 bg-transparent cursor-pointer"
                                        />
                                    </td>
                                    <td className="px-6 py-4">
                                        <Link href={`/run/${run.id}`} className="block">
                                            <div className="font-medium text-white mb-1 group-hover:text-[#00D4AA] transition-colors truncate max-w-xs">
                                                {run.test_name || run.api_name || run.project_path}
                                            </div>
                                            <div className="text-xs text-slate-500 truncate max-w-xs">
                                                {run.target_url || run.project_path}
                                            </div>
                                        </Link>
                                    </td>
                                    <td className="px-6 py-4 text-slate-400">
                                        {run.target_url ? "Backend" : "Frontend"}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className={`flex items-center gap-2 px-2 py-1 rounded w-fit text-xs font-medium uppercase ${run.status === 'completed' ? 'bg-[#00D4AA]/10 text-[#00D4AA]' :
                                            run.status === 'failed' ? 'bg-red-500/10 text-red-500' :
                                                'bg-blue-500/10 text-blue-400'
                                            }`}>
                                            {run.status === 'completed' ? <CheckCircle size={12} /> :
                                                run.status === 'failed' ? <XCircle size={12} /> : <Clock size={12} />}
                                            {run.status === 'completed' ? 'Pass' : run.status}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-slate-400">UI</td>
                                    <td className="px-6 py-4 text-slate-500 font-mono text-xs">
                                        {(() => {
                                            try {
                                                const dateStr = run.created_at || new Date().toISOString();
                                                // Check if it's a UUID (legacy bad data)
                                                if (dateStr.includes('-') && dateStr.split('-').length === 5 && !dateStr.includes('T')) {
                                                    return "Just now";
                                                }
                                                return new Date(dateStr).toISOString().split('T')[0];
                                            } catch (e) {
                                                return "Just now";
                                            }
                                        })()}
                                    </td>
                                    <td className="px-6 py-4 text-right relative">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setOpenMenuId(openMenuId === run.id ? null : run.id);
                                            }}
                                            className="text-slate-500 hover:text-white p-1 rounded hover:bg-white/5"
                                        >
                                            <MoreVertical size={16} />
                                        </button>
                                        {openMenuId === run.id && (
                                            <div
                                                ref={menuRef}
                                                className="absolute right-0 top-full mt-1 bg-[#1a1a1d] border border-white/10 rounded-lg shadow-xl z-50 py-1 min-w-[160px]"
                                            >
                                                <button
                                                    onClick={() => handleDownloadReport(run.id)}
                                                    className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-white/5 flex items-center gap-2"
                                                >
                                                    <Download size={14} />
                                                    Download Report
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(run.id)}
                                                    disabled={deleting === run.id}
                                                    className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2 disabled:opacity-50"
                                                >
                                                    <Trash2 size={14} />
                                                    {deleting === run.id ? "Deleting..." : "Delete"}
                                                </button>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            ))}

                            {runs.length === 0 && !loading && (
                                <tr>
                                    <td colSpan={7} className="text-center py-12 text-slate-500">
                                        No tests found. Create one to get started.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>

                    {/* Footer / Pagination */}
                    <div className="px-6 py-4 border-t border-white/5 flex items-center justify-between text-xs text-slate-500">
                        <div>Row per page: <span className="text-white font-medium">25</span></div>
                        <div className="flex items-center gap-2">
                            <button className="p-1 hover:text-white"><ChevronLeft size={16} /></button>
                            <button className="w-6 h-6 bg-[#00D4AA] text-black font-bold rounded flex items-center justify-center">1</button>
                            <button className="p-1 hover:text-white"><ChevronRight size={16} /></button>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
