"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { listTestSuites, createTestSuite, updateTestSuite, deleteTestSuite, runTestSuite, listRuns, TestSuite, Run } from "@/lib/api";
import {
    FileText, Plus, X, Trash2, Play, Clock, CheckCircle,
    XCircle, MoreVertical, Edit2, Calendar, Loader2, ExternalLink
} from "lucide-react";

export default function TestListsPage() {
    const router = useRouter();
    const [suites, setSuites] = useState<TestSuite[]>([]);
    const [runs, setRuns] = useState<Run[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [creating, setCreating] = useState(false);
    const [runningSuiteId, setRunningSuiteId] = useState<string | null>(null);
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

    // Form state
    const [formName, setFormName] = useState("");
    const [formDescription, setFormDescription] = useState("");
    const [formSchedule, setFormSchedule] = useState("");
    const [selectedTests, setSelectedTests] = useState<string[]>([]);
    const [editingSuiteId, setEditingSuiteId] = useState<string | null>(null);

    // Menu state
    const [openMenuId, setOpenMenuId] = useState<string | null>(null);

    useEffect(() => {
        loadData();
    }, []);

    // Auto-hide toast
    useEffect(() => {
        if (toast) {
            const timer = setTimeout(() => setToast(null), 4000);
            return () => clearTimeout(timer);
        }
    }, [toast]);

    const loadData = async () => {
        try {
            const [suitesData, runsData] = await Promise.all([
                listTestSuites(),
                listRuns()
            ]);
            setSuites(suitesData);
            setRuns(runsData.reverse());
        } catch (e) {
            console.error("Failed to load data:", e);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async () => {
        if (!formName.trim()) return;

        setCreating(true);
        try {
            await createTestSuite({
                name: formName,
                description: formDescription,
                tests: selectedTests,
                schedule: formSchedule || undefined
            });
            await loadData();
            setShowCreateModal(false);
            resetForm();
            setToast({ message: "Test suite created successfully!", type: "success" });
        } catch (e) {
            console.error("Failed to create suite:", e);
            setToast({ message: "Failed to create test suite", type: "error" });
        } finally {
            setCreating(false);
        }
    };

    const handleEdit = async () => {
        if (!formName.trim() || !editingSuiteId) return;

        setCreating(true);
        try {
            await updateTestSuite(editingSuiteId, {
                name: formName,
                description: formDescription,
                tests: selectedTests,
                schedule: formSchedule || undefined
            });
            await loadData();
            setShowEditModal(false);
            resetForm();
            setToast({ message: "Test suite updated successfully!", type: "success" });
        } catch (e) {
            console.error("Failed to update suite:", e);
            setToast({ message: "Failed to update test suite", type: "error" });
        } finally {
            setCreating(false);
        }
    };

    const openEditModal = (suite: TestSuite) => {
        setEditingSuiteId(suite.id);
        setFormName(suite.name);
        setFormDescription(suite.description || "");
        setFormSchedule(suite.schedule || "");
        setSelectedTests(suite.tests || []);
        setShowEditModal(true);
        setOpenMenuId(null);
    };

    const handleDelete = async (suiteId: string) => {
        if (!confirm("Are you sure you want to delete this test suite?")) return;

        try {
            await deleteTestSuite(suiteId);
            await loadData();
            setToast({ message: "Test suite deleted", type: "success" });
        } catch (e) {
            console.error("Failed to delete suite:", e);
            setToast({ message: "Failed to delete test suite", type: "error" });
        }
        setOpenMenuId(null);
    };

    const handleRun = async (suiteId: string, suiteName: string) => {
        setRunningSuiteId(suiteId);
        try {
            const result = await runTestSuite(suiteId);
            await loadData();
            setToast({
                message: `Running "${suiteName}" with ${result.tests_count} tests. View in All Tests.`,
                type: "success"
            });
        } catch (e) {
            console.error("Failed to run suite:", e);
            setToast({ message: "Failed to run test suite", type: "error" });
        } finally {
            setRunningSuiteId(null);
        }
        setOpenMenuId(null);
    };

    const resetForm = () => {
        setFormName("");
        setFormDescription("");
        setFormSchedule("");
        setSelectedTests([]);
        setEditingSuiteId(null);
    };

    const toggleTestSelection = (runId: string) => {
        setSelectedTests(prev =>
            prev.includes(runId)
                ? prev.filter(id => id !== runId)
                : [...prev, runId]
        );
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'passed': return 'text-[#00D4AA] bg-[#00D4AA]/10 border-[#00D4AA]/20';
            case 'failed': return 'text-red-400 bg-red-500/10 border-red-500/20';
            case 'running': return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
            default: return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
        }
    };

    return (
        <div className="flex min-h-screen bg-[#0E0E0E] text-slate-200 font-sans selection:bg-[#00D4AA]/30">
            <Sidebar />

            <main className="flex-1 ml-64 p-8">
                <header className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                        <span className="text-slate-300">TestBounty</span>
                        <span>/</span>
                        <span className="text-white">Test Suites</span>
                    </div>
                </header>

                <div className="max-w-5xl mx-auto">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h1 className="text-2xl font-semibold text-white">Test Suites</h1>
                            <p className="text-sm text-slate-400 mt-1">Group tests together and run them as a suite</p>
                        </div>
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-transform hover:scale-105"
                        >
                            <Plus size={16} /> Create New Suite
                        </button>
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-20">
                            <Loader2 className="animate-spin text-[#00D4AA]" size={32} />
                        </div>
                    ) : suites.length === 0 ? (
                        <div className="bg-[#121214] border border-white/5 rounded-xl p-12 flex flex-col items-center justify-center text-center min-h-[400px]">
                            <div className="w-16 h-16 bg-white/5 rounded-2xl flex items-center justify-center mb-6 text-slate-500">
                                <FileText size={32} />
                            </div>
                            <h3 className="text-xl text-white font-medium mb-2">No Test Suites Created</h3>
                            <p className="text-slate-400 max-w-md mb-8">
                                Group your tests into suites to run them together or organize them by feature.
                            </p>
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-6 py-3 rounded-lg text-sm font-semibold flex items-center gap-2"
                            >
                                <Plus size={16} /> Create Your First Suite
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {suites.map((suite) => (
                                <div
                                    key={suite.id}
                                    className="bg-[#121214] border border-white/5 rounded-xl p-6 hover:border-white/10 transition-colors"
                                >
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-3 mb-2">
                                                <h3 className="text-lg font-semibold text-white">{suite.name}</h3>
                                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${getStatusColor(suite.status)}`}>
                                                    {suite.status}
                                                </span>
                                            </div>
                                            <p className="text-sm text-slate-400 mb-4">
                                                {suite.description || "No description"}
                                            </p>
                                            <div className="flex items-center gap-6 text-xs text-slate-500">
                                                <span className="flex items-center gap-1">
                                                    <FileText size={12} />
                                                    {suite.tests.length} tests
                                                </span>
                                                {suite.schedule && (
                                                    <span className="flex items-center gap-1">
                                                        <Calendar size={12} />
                                                        {suite.schedule}
                                                    </span>
                                                )}
                                                {suite.last_run && (
                                                    <span className="flex items-center gap-1">
                                                        <Clock size={12} />
                                                        Last run: {new Date(suite.last_run).toLocaleDateString()}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => handleRun(suite.id, suite.name)}
                                                disabled={runningSuiteId === suite.id}
                                                className="bg-[#00D4AA]/10 hover:bg-[#00D4AA]/20 disabled:opacity-50 text-[#00D4AA] px-4 py-2 rounded-lg text-xs font-medium flex items-center gap-2 transition-colors"
                                            >
                                                {runningSuiteId === suite.id ? (
                                                    <>
                                                        <Loader2 size={14} className="animate-spin" /> Running...
                                                    </>
                                                ) : (
                                                    <>
                                                        <Play size={14} /> Run Suite
                                                    </>
                                                )}
                                            </button>
                                            <div className="relative">
                                                <button
                                                    onClick={() => setOpenMenuId(openMenuId === suite.id ? null : suite.id)}
                                                    className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
                                                >
                                                    <MoreVertical size={16} />
                                                </button>
                                                {openMenuId === suite.id && (
                                                    <div className="absolute right-0 top-full mt-1 bg-[#1A1A1D] border border-white/10 rounded-lg shadow-xl z-10 min-w-[140px] py-1">
                                                        <button
                                                            onClick={() => openEditModal(suite)}
                                                            className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-white/5 flex items-center gap-2"
                                                        >
                                                            <Edit2 size={14} /> Edit
                                                        </button>
                                                        <button
                                                            onClick={() => router.push('/testing')}
                                                            className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-white/5 flex items-center gap-2"
                                                        >
                                                            <ExternalLink size={14} /> View Tests
                                                        </button>
                                                        <button
                                                            onClick={() => handleDelete(suite.id)}
                                                            className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                                                        >
                                                            <Trash2 size={14} /> Delete
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </main>

            {/* Toast Notification */}
            {toast && (
                <div className={`fixed bottom-6 right-6 z-50 px-6 py-4 rounded-xl shadow-2xl flex items-center gap-3 animate-in slide-in-from-bottom-4 ${
                    toast.type === 'success'
                        ? 'bg-[#00D4AA]/20 border border-[#00D4AA]/30 text-[#00D4AA]'
                        : 'bg-red-500/20 border border-red-500/30 text-red-400'
                }`}>
                    {toast.type === 'success' ? <CheckCircle size={20} /> : <XCircle size={20} />}
                    <span className="text-sm font-medium">{toast.message}</span>
                    {toast.type === 'success' && toast.message.includes('Running') && (
                        <button
                            onClick={() => router.push('/testing')}
                            className="ml-2 text-white underline text-sm hover:text-[#00D4AA]"
                        >
                            View Tests
                        </button>
                    )}
                </div>
            )}

            {/* Create Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="bg-[#121214] border border-white/10 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
                        <div className="flex items-center justify-between p-6 border-b border-white/5">
                            <h2 className="text-xl font-semibold text-white">Create Test Suite</h2>
                            <button
                                onClick={() => { setShowCreateModal(false); resetForm(); }}
                                className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <div className="p-6 space-y-6 overflow-y-auto max-h-[60vh]">
                            {/* Name */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Suite Name *</label>
                                <input
                                    type="text"
                                    value={formName}
                                    onChange={(e) => setFormName(e.target.value)}
                                    placeholder="e.g., Login Flow Tests"
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50"
                                />
                            </div>

                            {/* Description */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
                                <textarea
                                    value={formDescription}
                                    onChange={(e) => setFormDescription(e.target.value)}
                                    placeholder="Describe what this suite tests..."
                                    rows={3}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50 resize-none"
                                />
                            </div>

                            {/* Schedule */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Schedule (Optional)</label>
                                <select
                                    value={formSchedule}
                                    onChange={(e) => setFormSchedule(e.target.value)}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#00D4AA]/50"
                                >
                                    <option value="">No schedule (manual only)</option>
                                    <option value="hourly">Every hour</option>
                                    <option value="daily">Daily</option>
                                    <option value="weekly">Weekly</option>
                                </select>
                            </div>

                            {/* Select Tests */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Select Tests ({selectedTests.length} selected)
                                </label>
                                <div className="bg-black/40 border border-white/10 rounded-lg max-h-[200px] overflow-y-auto">
                                    {runs.length === 0 ? (
                                        <div className="p-4 text-center text-slate-500 text-sm">
                                            No completed test runs available. Create tests first in "All Tests".
                                        </div>
                                    ) : (
                                        runs.filter(r => r.status === 'completed').map((run) => (
                                            <label
                                                key={run.id}
                                                className="flex items-center gap-3 p-3 hover:bg-white/5 cursor-pointer border-b border-white/5 last:border-0"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selectedTests.includes(run.id)}
                                                    onChange={() => toggleTestSelection(run.id)}
                                                    className="w-4 h-4 rounded border-white/20 bg-black/40 text-[#00D4AA] focus:ring-[#00D4AA]/50"
                                                />
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-sm text-white truncate">
                                                        {run.test_name || run.api_name || "Untitled Test"}
                                                    </div>
                                                    <div className="text-xs text-slate-500 truncate">
                                                        {run.target_url || run.project_path}
                                                    </div>
                                                </div>
                                                {run.status === 'completed' && (
                                                    <CheckCircle size={14} className="text-[#00D4AA] shrink-0" />
                                                )}
                                            </label>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center justify-end gap-3 p-6 border-t border-white/5">
                            <button
                                onClick={() => { setShowCreateModal(false); resetForm(); }}
                                className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreate}
                                disabled={!formName.trim() || creating}
                                className="bg-[#00D4AA] hover:bg-[#00C099] disabled:bg-slate-700 disabled:text-slate-500 text-black px-6 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-colors"
                            >
                                {creating ? (
                                    <>
                                        <Loader2 size={16} className="animate-spin" />
                                        Creating...
                                    </>
                                ) : (
                                    <>
                                        <Plus size={16} />
                                        Create Suite
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Edit Modal */}
            {showEditModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="bg-[#121214] border border-white/10 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
                        <div className="flex items-center justify-between p-6 border-b border-white/5">
                            <h2 className="text-xl font-semibold text-white">Edit Test Suite</h2>
                            <button
                                onClick={() => { setShowEditModal(false); resetForm(); }}
                                className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <div className="p-6 space-y-6 overflow-y-auto max-h-[60vh]">
                            {/* Name */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Suite Name *</label>
                                <input
                                    type="text"
                                    value={formName}
                                    onChange={(e) => setFormName(e.target.value)}
                                    placeholder="e.g., Login Flow Tests"
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50"
                                />
                            </div>

                            {/* Description */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
                                <textarea
                                    value={formDescription}
                                    onChange={(e) => setFormDescription(e.target.value)}
                                    placeholder="Describe what this suite tests..."
                                    rows={3}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50 resize-none"
                                />
                            </div>

                            {/* Schedule */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Schedule (Optional)</label>
                                <select
                                    value={formSchedule}
                                    onChange={(e) => setFormSchedule(e.target.value)}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#00D4AA]/50"
                                >
                                    <option value="">No schedule (manual only)</option>
                                    <option value="hourly">Every hour</option>
                                    <option value="daily">Daily</option>
                                    <option value="weekly">Weekly</option>
                                </select>
                            </div>

                            {/* Select Tests */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Select Tests ({selectedTests.length} selected)
                                </label>
                                <div className="bg-black/40 border border-white/10 rounded-lg max-h-[200px] overflow-y-auto">
                                    {runs.length === 0 ? (
                                        <div className="p-4 text-center text-slate-500 text-sm">
                                            No completed test runs available
                                        </div>
                                    ) : (
                                        runs.filter(r => r.status === 'completed').map((run) => (
                                            <label
                                                key={run.id}
                                                className="flex items-center gap-3 p-3 hover:bg-white/5 cursor-pointer border-b border-white/5 last:border-0"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={selectedTests.includes(run.id)}
                                                    onChange={() => toggleTestSelection(run.id)}
                                                    className="w-4 h-4 rounded border-white/20 bg-black/40 text-[#00D4AA] focus:ring-[#00D4AA]/50"
                                                />
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-sm text-white truncate">
                                                        {run.test_name || run.api_name || "Untitled Test"}
                                                    </div>
                                                    <div className="text-xs text-slate-500 truncate">
                                                        {run.target_url || run.project_path}
                                                    </div>
                                                </div>
                                                {run.status === 'completed' && (
                                                    <CheckCircle size={14} className="text-[#00D4AA] shrink-0" />
                                                )}
                                            </label>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center justify-end gap-3 p-6 border-t border-white/5">
                            <button
                                onClick={() => { setShowEditModal(false); resetForm(); }}
                                className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleEdit}
                                disabled={!formName.trim() || creating}
                                className="bg-[#00D4AA] hover:bg-[#00C099] disabled:bg-slate-700 disabled:text-slate-500 text-black px-6 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-colors"
                            >
                                {creating ? (
                                    <>
                                        <Loader2 size={16} className="animate-spin" />
                                        Saving...
                                    </>
                                ) : (
                                    <>
                                        <CheckCircle size={16} />
                                        Save Changes
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
