"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import {
    Activity, Clock, ShieldCheck, PlayCircle, Plus, X, Trash2, MoreVertical,
    Edit2, Loader2, AlertCircle, CheckCircle, HelpCircle, ExternalLink
} from "lucide-react";
import { listMonitors, createMonitor, updateMonitor, deleteMonitor, runMonitorNow, listTestSuites, Monitor, TestSuite } from "@/lib/api";

export default function MonitoringPage() {
    const [monitors, setMonitors] = useState<Monitor[]>([]);
    const [suites, setSuites] = useState<TestSuite[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [showHelpModal, setShowHelpModal] = useState(false);
    const [creating, setCreating] = useState(false);
    const [runningMonitor, setRunningMonitor] = useState<string | null>(null);
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

    // Form state
    const [formName, setFormName] = useState("");
    const [formDescription, setFormDescription] = useState("");
    const [formSchedule, setFormSchedule] = useState("hourly");
    const [formTargetUrl, setFormTargetUrl] = useState("");
    const [formTestSuiteId, setFormTestSuiteId] = useState("");
    const [editingMonitorId, setEditingMonitorId] = useState<string | null>(null);

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
            const [monitorsData, suitesData] = await Promise.all([
                listMonitors(),
                listTestSuites()
            ]);
            setMonitors(monitorsData);
            setSuites(suitesData);
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
            await createMonitor({
                name: formName,
                description: formDescription,
                schedule: formSchedule || "hourly",
                target_url: formTargetUrl || undefined,
                test_suite_id: formTestSuiteId || undefined
            });
            await loadData();
            setShowCreateModal(false);
            resetForm();
            setToast({ message: "Monitor created successfully!", type: "success" });
        } catch (e) {
            console.error("Failed to create monitor:", e);
            setToast({ message: "Failed to create monitor", type: "error" });
        } finally {
            setCreating(false);
        }
    };

    const handleEdit = async () => {
        if (!formName.trim() || !editingMonitorId) return;

        setCreating(true);
        try {
            await updateMonitor(editingMonitorId, {
                name: formName,
                description: formDescription,
                schedule: formSchedule
            });
            await loadData();
            setShowEditModal(false);
            resetForm();
            setToast({ message: "Monitor updated successfully!", type: "success" });
        } catch (e) {
            console.error("Failed to update monitor:", e);
            setToast({ message: "Failed to update monitor", type: "error" });
        } finally {
            setCreating(false);
        }
    };

    const openEditModal = (monitor: Monitor) => {
        setEditingMonitorId(monitor.id);
        setFormName(monitor.name);
        setFormDescription(monitor.description || "");
        setFormSchedule(monitor.schedule || "hourly");
        setFormTargetUrl(monitor.target_url || "");
        setFormTestSuiteId(monitor.test_suite_id || "");
        setShowEditModal(true);
        setOpenMenuId(null);
    };

    const handleDelete = async (monitorId: string) => {
        if (!confirm("Are you sure you want to delete this monitor?")) return;

        try {
            await deleteMonitor(monitorId);
            await loadData();
            setToast({ message: "Monitor deleted", type: "success" });
        } catch (e) {
            console.error("Failed to delete monitor:", e);
            setToast({ message: "Failed to delete monitor", type: "error" });
        }
        setOpenMenuId(null);
    };

    const handleRunNow = async (monitorId: string, monitorName: string) => {
        setRunningMonitor(monitorId);
        try {
            await runMonitorNow(monitorId);
            await loadData();
            setToast({ message: `"${monitorName}" check completed!`, type: "success" });
        } catch (e) {
            console.error("Failed to run monitor:", e);
            setToast({ message: "Failed to run monitor", type: "error" });
        } finally {
            setRunningMonitor(null);
        }
        setOpenMenuId(null);
    };

    const resetForm = () => {
        setFormName("");
        setFormDescription("");
        setFormSchedule("hourly");
        setFormTargetUrl("");
        setFormTestSuiteId("");
        setEditingMonitorId(null);
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'healthy': return 'text-[#00D4AA] bg-[#00D4AA]/10 border-[#00D4AA]/20';
            case 'warning': return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
            case 'critical': return 'text-red-400 bg-red-500/10 border-red-500/20';
            default: return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'healthy': return <CheckCircle size={24} />;
            case 'warning': return <AlertCircle size={24} />;
            case 'critical': return <AlertCircle size={24} />;
            default: return <Activity size={24} />;
        }
    };

    const activeMonitors = monitors.filter(m => m.enabled).length;
    const healthyMonitors = monitors.filter(m => m.status === 'healthy').length;
    const avgSuccessRate = monitors.length > 0
        ? Math.round(monitors.reduce((acc, m) => acc + m.success_rate, 0) / monitors.length)
        : 0;

    return (
        <div className="flex min-h-screen bg-[#0E0E0E] text-slate-200 font-sans selection:bg-[#00D4AA]/30">
            <Sidebar />

            <main className="flex-1 ml-64 p-8">
                <header className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                        <span className="text-slate-300">TestBounty</span>
                        <span>/</span>
                        <span className="text-white">Monitoring</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setShowHelpModal(true)}
                            className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
                            title="How monitoring works"
                        >
                            <HelpCircle size={20} />
                        </button>
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-colors"
                        >
                            <Plus size={16} /> New Monitor
                        </button>
                    </div>
                </header>

                <div className="max-w-6xl mx-auto">
                    <div className="mb-8">
                        <h1 className="text-3xl font-bold text-white mb-2">Continuous Monitoring</h1>
                        <p className="text-slate-400 max-w-2xl">
                            Automate your quality assurance by scheduling tests to run periodically.
                            Detect regressions and downtime before your users do.
                        </p>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                        <div className="bg-[#121214] border border-white/5 rounded-xl p-5">
                            <div className="text-slate-500 text-xs uppercase font-medium mb-1">Active Monitors</div>
                            <div className="text-2xl font-bold text-white">{activeMonitors}</div>
                            <div className="text-xs text-[#00D4AA] mt-1 flex items-center gap-1">
                                <Activity size={12} /> {activeMonitors > 0 ? 'Running on schedule' : 'No active monitors'}
                            </div>
                        </div>
                        <div className="bg-[#121214] border border-white/5 rounded-xl p-5">
                            <div className="text-slate-500 text-xs uppercase font-medium mb-1">Health Status</div>
                            <div className="text-2xl font-bold text-white">
                                {monitors.length > 0 ? `${healthyMonitors}/${monitors.length}` : '-'}
                            </div>
                            <div className="text-xs text-slate-400 mt-1">
                                {healthyMonitors === monitors.length && monitors.length > 0
                                    ? 'All monitors healthy'
                                    : monitors.length > 0
                                        ? `${monitors.length - healthyMonitors} monitors need attention`
                                        : 'No monitors configured'
                                }
                            </div>
                        </div>
                        <div className="bg-[#121214] border border-white/5 rounded-xl p-5">
                            <div className="text-slate-500 text-xs uppercase font-medium mb-1">Avg Success Rate</div>
                            <div className="text-2xl font-bold text-white">{avgSuccessRate}%</div>
                            <div className="text-xs text-slate-400 mt-1">Across all monitors</div>
                        </div>
                    </div>

                    {/* Monitors List */}
                    {loading ? (
                        <div className="flex items-center justify-center py-20">
                            <Loader2 className="animate-spin text-[#00D4AA]" size={32} />
                        </div>
                    ) : monitors.length === 0 ? (
                        <div className="bg-[#121214] border border-white/5 rounded-xl p-12 flex flex-col items-center justify-center text-center min-h-[400px]">
                            <div className="w-16 h-16 bg-white/5 rounded-2xl flex items-center justify-center mb-6 text-slate-500">
                                <Activity size={32} />
                            </div>
                            <h3 className="text-xl text-white font-medium mb-2">No Monitors Configured</h3>
                            <p className="text-slate-400 max-w-md mb-8">
                                Set up continuous monitoring to automatically run tests on a schedule
                                and get alerted when issues occur.
                            </p>
                            <div className="flex gap-4">
                                <button
                                    onClick={() => setShowHelpModal(true)}
                                    className="bg-white/5 hover:bg-white/10 text-white px-4 py-3 rounded-lg text-sm font-medium flex items-center gap-2"
                                >
                                    <HelpCircle size={16} /> How it works
                                </button>
                                <button
                                    onClick={() => setShowCreateModal(true)}
                                    className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-6 py-3 rounded-lg text-sm font-semibold flex items-center gap-2"
                                >
                                    <Plus size={16} /> Create Your First Monitor
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider mb-4">Scheduled Jobs</h2>

                            {monitors.map((monitor) => (
                                <div
                                    key={monitor.id}
                                    className="bg-[#121214] border border-white/5 rounded-xl p-6 flex items-center justify-between hover:border-white/10 transition-colors group"
                                >
                                    <div className="flex items-start gap-4">
                                        <div className={`p-3 rounded-lg transition-transform group-hover:scale-105 ${
                                            monitor.status === 'healthy' ? 'bg-[#00D4AA]/10 text-[#00D4AA]' :
                                            monitor.status === 'warning' ? 'bg-amber-500/10 text-amber-400' :
                                            monitor.status === 'critical' ? 'bg-red-500/10 text-red-400' :
                                            'bg-slate-500/10 text-slate-400'
                                        }`}>
                                            {getStatusIcon(monitor.status)}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-3 mb-1">
                                                <h3 className="text-lg font-semibold text-white">{monitor.name}</h3>
                                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${getStatusColor(monitor.status)}`}>
                                                    {monitor.status}
                                                </span>
                                                {!monitor.enabled && (
                                                    <span className="px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-400 text-[10px] font-bold uppercase border border-slate-500/20">
                                                        Disabled
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-sm text-slate-400 mb-2">
                                                {monitor.description || `Scheduled to run ${monitor.schedule}`}
                                            </p>
                                            <div className="flex items-center gap-4 text-xs text-slate-500 font-mono flex-wrap">
                                                <span className="flex items-center gap-1">
                                                    <Clock size={12} />
                                                    Schedule: {monitor.schedule}
                                                </span>
                                                {monitor.target_url && (
                                                    <>
                                                        <span>|</span>
                                                        <span className="flex items-center gap-1 text-blue-400">
                                                            <ExternalLink size={12} />
                                                            {monitor.target_url}
                                                        </span>
                                                    </>
                                                )}
                                                <span>|</span>
                                                <span>Success Rate: {monitor.success_rate}%</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={() => handleRunNow(monitor.id, monitor.name)}
                                            disabled={runningMonitor === monitor.id}
                                            className="bg-white/5 hover:bg-white/10 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-xs font-medium flex items-center gap-2 transition-colors"
                                        >
                                            {runningMonitor === monitor.id ? (
                                                <>
                                                    <Loader2 size={14} className="animate-spin" /> Running...
                                                </>
                                            ) : (
                                                <>
                                                    <PlayCircle size={14} /> Run Now
                                                </>
                                            )}
                                        </button>
                                        <div className="relative">
                                            <button
                                                onClick={() => setOpenMenuId(openMenuId === monitor.id ? null : monitor.id)}
                                                className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
                                            >
                                                <MoreVertical size={16} />
                                            </button>
                                            {openMenuId === monitor.id && (
                                                <div className="absolute right-0 top-full mt-1 bg-[#1A1A1D] border border-white/10 rounded-lg shadow-xl z-10 min-w-[140px] py-1">
                                                    <button
                                                        onClick={() => openEditModal(monitor)}
                                                        className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-white/5 flex items-center gap-2"
                                                    >
                                                        <Edit2 size={14} /> Edit
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(monitor.id)}
                                                        className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                                                    >
                                                        <Trash2 size={14} /> Delete
                                                    </button>
                                                </div>
                                            )}
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
                <div className={`fixed bottom-6 right-6 z-50 px-6 py-4 rounded-xl shadow-2xl flex items-center gap-3 ${
                    toast.type === 'success'
                        ? 'bg-[#00D4AA]/20 border border-[#00D4AA]/30 text-[#00D4AA]'
                        : 'bg-red-500/20 border border-red-500/30 text-red-400'
                }`}>
                    {toast.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
                    <span className="text-sm font-medium">{toast.message}</span>
                </div>
            )}

            {/* Help Modal */}
            {showHelpModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="bg-[#121214] border border-white/10 rounded-2xl w-full max-w-xl max-h-[90vh] overflow-hidden">
                        <div className="flex items-center justify-between p-6 border-b border-white/5">
                            <h2 className="text-xl font-semibold text-white">How Monitoring Works</h2>
                            <button
                                onClick={() => setShowHelpModal(false)}
                                className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <div className="p-6 space-y-6 overflow-y-auto max-h-[60vh]">
                            <div className="space-y-4">
                                <div className="flex gap-4">
                                    <div className="w-8 h-8 bg-[#00D4AA]/10 rounded-lg flex items-center justify-center text-[#00D4AA] shrink-0">
                                        1
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-white mb-1">Create a Monitor</h3>
                                        <p className="text-sm text-slate-400">
                                            Set up a monitor with a name, optional target URL, and schedule frequency.
                                            You can also link it to an existing test suite.
                                        </p>
                                    </div>
                                </div>

                                <div className="flex gap-4">
                                    <div className="w-8 h-8 bg-[#00D4AA]/10 rounded-lg flex items-center justify-center text-[#00D4AA] shrink-0">
                                        2
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-white mb-1">Automatic Checks</h3>
                                        <p className="text-sm text-slate-400">
                                            The monitor runs automatically based on your schedule (every 5 min, hourly, daily, etc.).
                                            It checks the URL's availability or runs linked test suite.
                                        </p>
                                    </div>
                                </div>

                                <div className="flex gap-4">
                                    <div className="w-8 h-8 bg-[#00D4AA]/10 rounded-lg flex items-center justify-center text-[#00D4AA] shrink-0">
                                        3
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-white mb-1">Health Status</h3>
                                        <p className="text-sm text-slate-400">
                                            Monitor status updates based on results:
                                        </p>
                                        <ul className="text-sm text-slate-400 mt-2 space-y-1">
                                            <li className="flex items-center gap-2">
                                                <span className="w-2 h-2 bg-[#00D4AA] rounded-full"></span>
                                                <span><strong className="text-[#00D4AA]">Healthy</strong> - All checks passing</span>
                                            </li>
                                            <li className="flex items-center gap-2">
                                                <span className="w-2 h-2 bg-amber-400 rounded-full"></span>
                                                <span><strong className="text-amber-400">Warning</strong> - Some failures detected</span>
                                            </li>
                                            <li className="flex items-center gap-2">
                                                <span className="w-2 h-2 bg-red-400 rounded-full"></span>
                                                <span><strong className="text-red-400">Critical</strong> - Repeated failures</span>
                                            </li>
                                        </ul>
                                    </div>
                                </div>

                                <div className="flex gap-4">
                                    <div className="w-8 h-8 bg-[#00D4AA]/10 rounded-lg flex items-center justify-center text-[#00D4AA] shrink-0">
                                        4
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-white mb-1">Get Alerted</h3>
                                        <p className="text-sm text-slate-400">
                                            Configure notifications in your Profile to receive alerts via email or Slack
                                            when monitors detect issues.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                                <p className="text-sm text-blue-400">
                                    <strong>Tip:</strong> Link monitors to test suites for comprehensive testing,
                                    or just use a URL for simple uptime monitoring.
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center justify-end gap-3 p-6 border-t border-white/5">
                            <button
                                onClick={() => setShowHelpModal(false)}
                                className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-6 py-2 rounded-lg text-sm font-semibold"
                            >
                                Got it!
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Create Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="bg-[#121214] border border-white/10 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-hidden">
                        <div className="flex items-center justify-between p-6 border-b border-white/5">
                            <h2 className="text-xl font-semibold text-white">Create Monitor</h2>
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
                                <label className="block text-sm font-medium text-slate-300 mb-2">Monitor Name *</label>
                                <input
                                    type="text"
                                    value={formName}
                                    onChange={(e) => setFormName(e.target.value)}
                                    placeholder="e.g., Login Health Check"
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50"
                                />
                            </div>

                            {/* Description */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
                                <textarea
                                    value={formDescription}
                                    onChange={(e) => setFormDescription(e.target.value)}
                                    placeholder="What does this monitor check?"
                                    rows={2}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50 resize-none"
                                />
                            </div>

                            {/* Target URL */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Target URL (Optional)
                                    <span className="text-slate-500 font-normal ml-2">- for uptime monitoring</span>
                                </label>
                                <input
                                    type="text"
                                    value={formTargetUrl}
                                    onChange={(e) => setFormTargetUrl(e.target.value)}
                                    placeholder="https://your-app.com"
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50"
                                />
                                <p className="text-xs text-slate-500 mt-1">We'll check if this URL responds successfully</p>
                            </div>

                            {/* Test Suite */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Link to Test Suite (Optional)
                                    <span className="text-slate-500 font-normal ml-2">- for comprehensive testing</span>
                                </label>
                                <select
                                    value={formTestSuiteId}
                                    onChange={(e) => setFormTestSuiteId(e.target.value)}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#00D4AA]/50"
                                >
                                    <option value="">No linked suite</option>
                                    {suites.map(suite => (
                                        <option key={suite.id} value={suite.id}>{suite.name} ({suite.tests.length} tests)</option>
                                    ))}
                                </select>
                                <p className="text-xs text-slate-500 mt-1">Run all tests in the suite on schedule</p>
                            </div>

                            {/* Schedule */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Schedule</label>
                                <select
                                    value={formSchedule}
                                    onChange={(e) => setFormSchedule(e.target.value)}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#00D4AA]/50"
                                >
                                    <option value="every_5_minutes">Every 5 minutes</option>
                                    <option value="every_15_minutes">Every 15 minutes</option>
                                    <option value="every_30_minutes">Every 30 minutes</option>
                                    <option value="hourly">Every hour</option>
                                    <option value="daily">Daily</option>
                                </select>
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
                                        Create Monitor
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
                    <div className="bg-[#121214] border border-white/10 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-hidden">
                        <div className="flex items-center justify-between p-6 border-b border-white/5">
                            <h2 className="text-xl font-semibold text-white">Edit Monitor</h2>
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
                                <label className="block text-sm font-medium text-slate-300 mb-2">Monitor Name *</label>
                                <input
                                    type="text"
                                    value={formName}
                                    onChange={(e) => setFormName(e.target.value)}
                                    placeholder="e.g., Login Health Check"
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50"
                                />
                            </div>

                            {/* Description */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
                                <textarea
                                    value={formDescription}
                                    onChange={(e) => setFormDescription(e.target.value)}
                                    placeholder="What does this monitor check?"
                                    rows={2}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50 resize-none"
                                />
                            </div>

                            {/* Schedule */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Schedule</label>
                                <select
                                    value={formSchedule}
                                    onChange={(e) => setFormSchedule(e.target.value)}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#00D4AA]/50"
                                >
                                    <option value="every_5_minutes">Every 5 minutes</option>
                                    <option value="every_15_minutes">Every 15 minutes</option>
                                    <option value="every_30_minutes">Every 30 minutes</option>
                                    <option value="hourly">Every hour</option>
                                    <option value="daily">Daily</option>
                                </select>
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
