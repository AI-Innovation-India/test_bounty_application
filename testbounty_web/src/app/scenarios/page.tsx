"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import {
    api, getScenarioCode, getAllScenarioCode, listScenarioVideos,
    getScenarioVideoFileUrl
} from "@/lib/api";
import {
    Search, Play, CheckCircle, XCircle, Clock, ChevronDown, ChevronRight,
    Loader2, Globe, FileCode, Shield, Zap, RefreshCw, Trash2, Eye,
    Video, Code, X, Download, Copy
} from "lucide-react";

interface TestStep {
    action: string;
    target: string;
    value?: string;
    description: string;
}

interface Scenario {
    id: string;
    name: string;
    description: string;
    module: string;
    type: string;
    priority: string;
    depends_on: string | null;
    steps: TestStep[];
    status: string;
}

interface Module {
    name: string;
    requires_auth: boolean;
    scenarios: Scenario[];
}

interface Plan {
    id: string;
    url: string;
    status: string;
    created_at: string;
    completed_at?: string;
    app_map?: any;
    test_plan?: {
        base_url: string;
        total_scenarios: number;
        modules: Record<string, Module>;
    };
    error?: string;
}

interface RunResult {
    id: string;
    name: string;
    status: string;
    steps_completed: string[];
    error?: string;
}

export default function ScenariosPage() {
    const [plans, setPlans] = useState<Plan[]>([]);
    const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
    const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set());
    const [selectedScenarios, setSelectedScenarios] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(true);
    const [exploring, setExploring] = useState(false);
    const [running, setRunning] = useState(false);
    const [runResults, setRunResults] = useState<Record<string, RunResult>>({});

    // Explore form
    const [exploreUrl, setExploreUrl] = useState("");

    // Toast
    const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

    // Video & Code Preview
    const [activeRunId, setActiveRunId] = useState<string | null>(null);
    const [videoModalOpen, setVideoModalOpen] = useState(false);
    const [codeModalOpen, setCodeModalOpen] = useState(false);
    const [selectedScenarioForPreview, setSelectedScenarioForPreview] = useState<Scenario | null>(null);
    const [previewCode, setPreviewCode] = useState<string>("");
    const [previewVideos, setPreviewVideos] = useState<{ filename: string; url: string; size: number }[]>([]);
    const [loadingPreview, setLoadingPreview] = useState(false);

    // Expanded scenarios (to show steps)
    const [expandedScenarios, setExpandedScenarios] = useState<Set<string>>(new Set());

    useEffect(() => {
        fetchPlans();
    }, []);

    useEffect(() => {
        if (toast) {
            const timer = setTimeout(() => setToast(null), 3000);
            return () => clearTimeout(timer);
        }
    }, [toast]);

    const fetchPlans = async () => {
        try {
            const data = await api.getPlans();
            setPlans(data);
            if (data.length > 0 && !selectedPlan) {
                const readyPlan = data.find((p: Plan) => p.status === "ready");
                if (readyPlan) {
                    setSelectedPlan(readyPlan);
                    // Expand all modules by default
                    if (readyPlan.test_plan?.modules) {
                        setExpandedModules(new Set(Object.keys(readyPlan.test_plan.modules)));
                    }
                }
            }
        } catch (error) {
            console.error("Failed to fetch plans:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleExplore = async () => {
        if (!exploreUrl.trim()) {
            setToast({ message: "Please enter a URL", type: "error" });
            return;
        }

        setExploring(true);
        try {
            const result = await api.exploreUrl(exploreUrl);
            setToast({ message: "Exploration started! This may take a minute...", type: "success" });

            // Poll for completion
            const pollInterval = setInterval(async () => {
                const plan = await api.getPlan(result.explore_id);
                if (plan.status === "ready") {
                    clearInterval(pollInterval);
                    setSelectedPlan(plan);
                    setPlans(prev => [...prev.filter(p => p.id !== plan.id), plan]);
                    if (plan.test_plan?.modules) {
                        setExpandedModules(new Set(Object.keys(plan.test_plan.modules)));
                    }
                    setExploring(false);
                    setExploreUrl("");
                    setToast({ message: `Found ${plan.test_plan?.total_scenarios || 0} test scenarios!`, type: "success" });
                } else if (plan.status === "failed") {
                    clearInterval(pollInterval);
                    setExploring(false);
                    setToast({ message: plan.error || "Exploration failed", type: "error" });
                }
            }, 2000);

        } catch (error) {
            setExploring(false);
            setToast({ message: "Failed to start exploration", type: "error" });
        }
    };

    const toggleModule = (moduleName: string) => {
        setExpandedModules(prev => {
            const next = new Set(prev);
            if (next.has(moduleName)) {
                next.delete(moduleName);
            } else {
                next.add(moduleName);
            }
            return next;
        });
    };

    const toggleScenarioExpansion = (scenarioId: string) => {
        setExpandedScenarios(prev => {
            const next = new Set(prev);
            if (next.has(scenarioId)) {
                next.delete(scenarioId);
            } else {
                next.add(scenarioId);
            }
            return next;
        });
    };

    const toggleScenario = (scenarioId: string) => {
        setSelectedScenarios(prev => {
            const next = new Set(prev);
            if (next.has(scenarioId)) {
                next.delete(scenarioId);
            } else {
                next.add(scenarioId);
            }
            return next;
        });
    };

    const selectAllInModule = (moduleName: string) => {
        const module = selectedPlan?.test_plan?.modules[moduleName];
        if (!module) return;

        setSelectedScenarios(prev => {
            const next = new Set(prev);
            const allSelected = module.scenarios.every(s => prev.has(s.id));

            if (allSelected) {
                // Deselect all
                module.scenarios.forEach(s => next.delete(s.id));
            } else {
                // Select all
                module.scenarios.forEach(s => next.add(s.id));
            }
            return next;
        });
    };

    const runSelected = async () => {
        if (!selectedPlan || selectedScenarios.size === 0) {
            setToast({ message: "Please select scenarios to run", type: "error" });
            return;
        }

        setRunning(true);
        setRunResults({});

        try {
            const result = await api.runScenarios(selectedPlan.id, Array.from(selectedScenarios));
            setActiveRunId(result.run_id);
            setToast({ message: `Running ${result.scenarios_count} scenarios...`, type: "success" });

            // Poll for results
            const pollInterval = setInterval(async () => {
                const runStatus = await api.getRunStatus(result.run_id);

                if (runStatus.results) {
                    setRunResults(runStatus.results);
                }

                if (runStatus.status === "completed" || runStatus.status === "failed") {
                    clearInterval(pollInterval);
                    setRunning(false);

                    const passed = Object.values(runStatus.results || {}).filter((r: any) => r.status === "passed").length;
                    const total = Object.keys(runStatus.results || {}).length;
                    setToast({
                        message: `Completed: ${passed}/${total} passed`,
                        type: passed === total ? "success" : "error"
                    });
                }
            }, 1500);

        } catch (error) {
            setRunning(false);
            setToast({ message: "Failed to run scenarios", type: "error" });
        }
    };

    const runModule = async (moduleName: string) => {
        if (!selectedPlan) return;

        setRunning(true);
        setRunResults({});

        try {
            const result = await api.runModule(selectedPlan.id, moduleName);
            setActiveRunId(result.run_id);
            setToast({ message: `Running ${moduleName} module...`, type: "success" });

            // Poll for results
            const pollInterval = setInterval(async () => {
                const runStatus = await api.getRunStatus(result.run_id);

                if (runStatus.results) {
                    setRunResults(runStatus.results);
                }

                if (runStatus.status === "completed" || runStatus.status === "failed") {
                    clearInterval(pollInterval);
                    setRunning(false);
                }
            }, 1500);

        } catch (error) {
            setRunning(false);
            setToast({ message: "Failed to run module", type: "error" });
        }
    };

    const runAllScenarios = async () => {
        if (!selectedPlan) return;

        // Select all scenarios
        const allIds = new Set<string>();
        Object.values(selectedPlan.test_plan?.modules || {}).forEach(module => {
            module.scenarios.forEach(s => allIds.add(s.id));
        });
        setSelectedScenarios(allIds);

        setRunning(true);
        setRunResults({});

        try {
            const result = await api.runScenarios(selectedPlan.id, []);
            setActiveRunId(result.run_id);
            setToast({ message: `Running all ${result.scenarios_count} scenarios...`, type: "success" });

            // Poll for results
            const pollInterval = setInterval(async () => {
                const runStatus = await api.getRunStatus(result.run_id);

                if (runStatus.results) {
                    setRunResults(runStatus.results);
                }

                if (runStatus.status === "completed" || runStatus.status === "failed") {
                    clearInterval(pollInterval);
                    setRunning(false);
                }
            }, 1500);

        } catch (error) {
            setRunning(false);
            setToast({ message: "Failed to run scenarios", type: "error" });
        }
    };

    const deletePlan = async (planId: string) => {
        try {
            await api.deletePlan(planId);
            setPlans(prev => prev.filter(p => p.id !== planId));
            if (selectedPlan?.id === planId) {
                setSelectedPlan(null);
            }
            setToast({ message: "Plan deleted", type: "success" });
        } catch (error) {
            setToast({ message: "Failed to delete plan", type: "error" });
        }
    };

    const getScenarioStatus = (scenarioId: string): string => {
        if (runResults[scenarioId]) {
            return runResults[scenarioId].status;
        }
        return "pending";
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "passed":
                return <CheckCircle size={16} className="text-emerald-400" />;
            case "failed":
                return <XCircle size={16} className="text-red-400" />;
            case "running":
                return <Loader2 size={16} className="text-blue-400 animate-spin" />;
            default:
                return <Clock size={16} className="text-slate-500" />;
        }
    };

    const getTypeIcon = (type: string) => {
        switch (type) {
            case "security":
                return <Shield size={14} className="text-red-400" />;
            case "happy_path":
                return <Zap size={14} className="text-emerald-400" />;
            case "error_path":
                return <XCircle size={14} className="text-orange-400" />;
            default:
                return <FileCode size={14} className="text-slate-400" />;
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case "high":
                return "text-red-400";
            case "medium":
                return "text-yellow-400";
            default:
                return "text-slate-400";
        }
    };

    // Open video preview modal
    const openVideoPreview = async (scenario: Scenario) => {
        if (!activeRunId) {
            setToast({ message: "Run tests first to see video recordings", type: "error" });
            return;
        }

        setSelectedScenarioForPreview(scenario);
        setLoadingPreview(true);
        setVideoModalOpen(true);

        try {
            const result = await listScenarioVideos(activeRunId);
            setPreviewVideos(result.videos);
        } catch (error) {
            console.error("Failed to load videos:", error);
            setPreviewVideos([]);
        } finally {
            setLoadingPreview(false);
        }
    };

    // Open code preview modal
    const openCodePreview = async (scenario: Scenario) => {
        if (!activeRunId) {
            setToast({ message: "Run tests first to see generated code", type: "error" });
            return;
        }

        setSelectedScenarioForPreview(scenario);
        setLoadingPreview(true);
        setCodeModalOpen(true);

        try {
            const result = await getScenarioCode(activeRunId, scenario.id);
            setPreviewCode(result.code);
        } catch (error) {
            console.error("Failed to load code:", error);
            setPreviewCode("// Failed to load code");
        } finally {
            setLoadingPreview(false);
        }
    };

    // Download all code
    const downloadAllCode = async () => {
        if (!activeRunId) return;

        try {
            const result = await getAllScenarioCode(activeRunId);
            const blob = new Blob([result.code], { type: "text/plain" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "test_scenarios.py";
            a.click();
            URL.revokeObjectURL(url);
            setToast({ message: "Code downloaded!", type: "success" });
        } catch (error) {
            setToast({ message: "Failed to download code", type: "error" });
        }
    };

    // Copy code to clipboard
    const copyCode = async () => {
        try {
            await navigator.clipboard.writeText(previewCode);
            setToast({ message: "Code copied to clipboard!", type: "success" });
        } catch (error) {
            setToast({ message: "Failed to copy code", type: "error" });
        }
    };

    return (
        <div className="flex min-h-screen bg-[#0a0a0b]">
            <Sidebar />

            <main className="flex-1 p-8 ml-64">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-white">Scenario Testing</h1>
                        <p className="text-slate-400 mt-1">Explore, plan, and run modular test scenarios</p>
                    </div>
                </div>

                {/* Explore URL */}
                <div className="bg-[#121214] border border-white/5 rounded-xl p-6 mb-8">
                    <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <Search size={20} className="text-[#00D4AA]" />
                        Explore New Application
                    </h2>
                    <div className="flex gap-4">
                        <div className="flex-1">
                            <input
                                type="url"
                                placeholder="Enter URL to explore (e.g., https://myapp.com)"
                                value={exploreUrl}
                                onChange={(e) => setExploreUrl(e.target.value)}
                                className="w-full px-4 py-3 bg-[#1a1a1d] border border-white/10 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:border-[#00D4AA]/50"
                            />
                        </div>
                        <button
                            onClick={handleExplore}
                            disabled={exploring}
                            className="px-6 py-3 bg-[#00D4AA] hover:bg-[#00C099] text-black font-semibold rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                        >
                            {exploring ? (
                                <>
                                    <Loader2 size={18} className="animate-spin" />
                                    Exploring...
                                </>
                            ) : (
                                <>
                                    <Globe size={18} />
                                    Explore
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* Plan Selector */}
                {plans.length > 0 && (
                    <div className="mb-6">
                        <div className="flex items-center gap-4 flex-wrap">
                            {plans.filter(p => p.status === "ready").map(plan => (
                                <div
                                    key={plan.id}
                                    onClick={() => {
                                        setSelectedPlan(plan);
                                        if (plan.test_plan?.modules) {
                                            setExpandedModules(new Set(Object.keys(plan.test_plan.modules)));
                                        }
                                        setSelectedScenarios(new Set());
                                        setRunResults({});
                                    }}
                                    className={`px-4 py-2 rounded-lg border transition-colors flex items-center gap-2 cursor-pointer ${selectedPlan?.id === plan.id
                                            ? "bg-[#00D4AA]/10 border-[#00D4AA]/50 text-[#00D4AA]"
                                            : "bg-[#121214] border-white/10 text-slate-400 hover:border-white/20"
                                        }`}
                                >
                                    <Globe size={16} />
                                    {new URL(plan.url).hostname}
                                    <span className="text-xs text-slate-500">
                                        ({plan.test_plan?.total_scenarios || 0} scenarios)
                                    </span>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            deletePlan(plan.id);
                                        }}
                                        className="ml-2 p-1 hover:bg-red-500/20 rounded"
                                    >
                                        <Trash2 size={14} className="text-red-400" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Main Content */}
                {loading || exploring ? (
                    <div className="flex flex-col items-center justify-center py-20">
                        <Loader2 size={32} className="text-[#00D4AA] animate-spin mb-4" />
                        <p className="text-slate-400">
                            {exploring ? "Exploring application and generating test scenarios..." : "Loading..."}
                        </p>
                    </div>
                ) : selectedPlan && selectedPlan.test_plan ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Modules & Scenarios */}
                        <div className="lg:col-span-2 space-y-4">
                            {Object.entries(selectedPlan.test_plan.modules).map(([moduleName, module]) => (
                                <div key={moduleName} className="bg-[#121214] border border-white/5 rounded-xl overflow-hidden">
                                    {/* Module Header */}
                                    <div
                                        className="flex items-center justify-between p-4 cursor-pointer hover:bg-white/5 transition-colors"
                                        onClick={() => toggleModule(moduleName)}
                                    >
                                        <div className="flex items-center gap-3">
                                            {expandedModules.has(moduleName) ? (
                                                <ChevronDown size={20} className="text-slate-400" />
                                            ) : (
                                                <ChevronRight size={20} className="text-slate-400" />
                                            )}
                                            <h3 className="text-lg font-semibold text-white">{module.name} Module</h3>
                                            {module.requires_auth && (
                                                <span className="px-2 py-0.5 text-xs bg-yellow-500/10 text-yellow-400 rounded">
                                                    Requires Auth
                                                </span>
                                            )}
                                            <span className="text-sm text-slate-500">
                                                {module.scenarios.length} scenarios
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    selectAllInModule(moduleName);
                                                }}
                                                className="px-3 py-1 text-xs bg-white/5 hover:bg-white/10 text-slate-300 rounded transition-colors"
                                            >
                                                {module.scenarios.every(s => selectedScenarios.has(s.id)) ? "Deselect All" : "Select All"}
                                            </button>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    runModule(moduleName);
                                                }}
                                                disabled={running}
                                                className="px-3 py-1 text-xs bg-[#00D4AA]/10 hover:bg-[#00D4AA]/20 text-[#00D4AA] rounded transition-colors flex items-center gap-1"
                                            >
                                                <Play size={12} />
                                                Run Module
                                            </button>
                                        </div>
                                    </div>

                                    {/* Scenarios List */}
                                    {expandedModules.has(moduleName) && (
                                        <div className="border-t border-white/5">
                                            {module.scenarios.map(scenario => {
                                                const status = getScenarioStatus(scenario.id);
                                                const isExpanded = expandedScenarios.has(scenario.id);
                                                return (
                                                    <div key={scenario.id} className="border-b border-white/5 last:border-0">
                                                        <div
                                                            className={`flex items-center justify-between p-4 hover:bg-white/5 transition-colors ${selectedScenarios.has(scenario.id) ? "bg-[#00D4AA]/5" : ""
                                                                }`}
                                                        >
                                                            <div className="flex items-center gap-3">
                                                                <button
                                                                    onClick={() => toggleScenarioExpansion(scenario.id)}
                                                                    className="p-1 hover:bg-white/10 rounded transition-colors"
                                                                >
                                                                    {isExpanded ? (
                                                                        <ChevronDown size={16} className="text-slate-400" />
                                                                    ) : (
                                                                        <ChevronRight size={16} className="text-slate-400" />
                                                                    )}
                                                                </button>
                                                                <input
                                                                    type="checkbox"
                                                                    checked={selectedScenarios.has(scenario.id)}
                                                                    onChange={() => toggleScenario(scenario.id)}
                                                                    className="w-4 h-4 rounded border-white/20 bg-transparent text-[#00D4AA] focus:ring-[#00D4AA]/50"
                                                                />
                                                                {getStatusIcon(status)}
                                                                <div>
                                                                    <div className="flex items-center gap-2">
                                                                        <span className="text-white font-medium">{scenario.name}</span>
                                                                        {getTypeIcon(scenario.type)}
                                                                        <span className={`text-xs ${getPriorityColor(scenario.priority)}`}>
                                                                            {scenario.priority}
                                                                        </span>
                                                                    </div>
                                                                    <p className="text-sm text-slate-500">{scenario.description}</p>
                                                                    {scenario.depends_on && (
                                                                        <span className="text-xs text-slate-600">
                                                                            Depends on: {scenario.depends_on}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-xs text-slate-500">
                                                                    {scenario.steps.length} steps
                                                                </span>
                                                                {runResults[scenario.id]?.error && (
                                                                    <span className="text-xs text-red-400 max-w-xs truncate">
                                                                        {runResults[scenario.id].error}
                                                                    </span>
                                                                )}
                                                                {/* Video & Code Preview Buttons */}
                                                                {activeRunId && runResults[scenario.id] && (
                                                                    <div className="flex items-center gap-1 ml-2">
                                                                        <button
                                                                            onClick={(e) => {
                                                                                e.stopPropagation();
                                                                                openVideoPreview(scenario);
                                                                            }}
                                                                            className="p-1.5 hover:bg-white/10 rounded transition-colors"
                                                                            title="View Video"
                                                                        >
                                                                            <Video size={14} className="text-blue-400" />
                                                                        </button>
                                                                        <button
                                                                            onClick={(e) => {
                                                                                e.stopPropagation();
                                                                                openCodePreview(scenario);
                                                                            }}
                                                                            className="p-1.5 hover:bg-white/10 rounded transition-colors"
                                                                            title="View Code"
                                                                        >
                                                                            <Code size={14} className="text-emerald-400" />
                                                                        </button>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>

                                                        {/* Expanded Steps View */}
                                                        {isExpanded && (
                                                            <div className="px-4 pb-4 bg-[#0a0a0b]/50">
                                                                <div className="ml-12 space-y-2">
                                                                    <p className="text-xs font-semibold text-slate-400 uppercase mb-3">Test Steps:</p>
                                                                    {scenario.steps.map((step, idx) => (
                                                                        <div key={idx} className="flex items-start gap-3 p-2 bg-white/5 rounded">
                                                                            <span className="text-xs text-slate-500 font-mono mt-0.5">{idx + 1}.</span>
                                                                            <div className="flex-1">
                                                                                <div className="flex items-center gap-2 mb-1">
                                                                                    <span className="text-xs font-semibold text-[#00D4AA] uppercase">{step.action}</span>
                                                                                    {step.action === 'fill' && step.value && (
                                                                                        <span className="text-xs text-slate-400">→ {step.value}</span>
                                                                                    )}
                                                                                </div>
                                                                                <p className="text-sm text-slate-300">{step.description}</p>
                                                                                {step.target && step.action !== 'navigate' && step.action !== 'assert' && (
                                                                                    <p className="text-xs text-slate-500 font-mono mt-1">Selector: {step.target}</p>
                                                                                )}
                                                                            </div>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>

                        {/* Actions Panel */}
                        <div className="space-y-4">
                            {/* Run Controls */}
                            <div className="bg-[#121214] border border-white/5 rounded-xl p-6">
                                <h3 className="text-lg font-semibold text-white mb-4">Run Tests</h3>

                                <div className="space-y-3">
                                    <button
                                        onClick={runSelected}
                                        disabled={running || selectedScenarios.size === 0}
                                        className="w-full px-4 py-3 bg-[#00D4AA] hover:bg-[#00C099] text-black font-semibold rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                                    >
                                        {running ? (
                                            <>
                                                <Loader2 size={18} className="animate-spin" />
                                                Running...
                                            </>
                                        ) : (
                                            <>
                                                <Play size={18} />
                                                Run Selected ({selectedScenarios.size})
                                            </>
                                        )}
                                    </button>

                                    <button
                                        onClick={runAllScenarios}
                                        disabled={running}
                                        className="w-full px-4 py-3 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                                    >
                                        <Zap size={18} />
                                        Run Full E2E
                                    </button>

                                    <button
                                        onClick={() => {
                                            setSelectedScenarios(new Set());
                                            setRunResults({});
                                        }}
                                        className="w-full px-4 py-3 bg-white/5 hover:bg-white/10 text-slate-400 rounded-lg transition-colors flex items-center justify-center gap-2"
                                    >
                                        <RefreshCw size={18} />
                                        Reset
                                    </button>
                                </div>
                            </div>

                            {/* Results Summary */}
                            {Object.keys(runResults).length > 0 && (
                                <div className="bg-[#121214] border border-white/5 rounded-xl p-6">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-lg font-semibold text-white">Results</h3>
                                        {activeRunId && (
                                            <button
                                                onClick={downloadAllCode}
                                                className="px-3 py-1.5 text-xs bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 rounded transition-colors flex items-center gap-1"
                                            >
                                                <Download size={12} />
                                                Download Code
                                            </button>
                                        )}
                                    </div>

                                    <div className="grid grid-cols-3 gap-4 mb-4">
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-emerald-400">
                                                {Object.values(runResults).filter(r => r.status === "passed").length}
                                            </div>
                                            <div className="text-xs text-slate-500">Passed</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-red-400">
                                                {Object.values(runResults).filter(r => r.status === "failed").length}
                                            </div>
                                            <div className="text-xs text-slate-500">Failed</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-slate-400">
                                                {Object.values(runResults).filter(r => r.status === "running").length}
                                            </div>
                                            <div className="text-xs text-slate-500">Running</div>
                                        </div>
                                    </div>

                                    {/* Failed Tests */}
                                    {Object.values(runResults).filter(r => r.status === "failed").length > 0 && (
                                        <div className="mt-4 pt-4 border-t border-white/5">
                                            <h4 className="text-sm font-medium text-red-400 mb-2">Failed Tests</h4>
                                            <div className="space-y-2">
                                                {Object.values(runResults)
                                                    .filter(r => r.status === "failed")
                                                    .map(r => (
                                                        <div key={r.id} className="text-xs bg-red-500/10 p-2 rounded">
                                                            <div className="text-white">{r.name}</div>
                                                            <div className="text-red-400">{r.error}</div>
                                                        </div>
                                                    ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* App Map Info */}
                            {selectedPlan.app_map && (
                                <div className="bg-[#121214] border border-white/5 rounded-xl p-6">
                                    <h3 className="text-lg font-semibold text-white mb-4">App Map</h3>
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-slate-400">Pages Found</span>
                                            <span className="text-white">{selectedPlan.app_map.total_pages}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-slate-400">Auth Pages</span>
                                            <span className="text-white">{selectedPlan.app_map.auth_pages?.length || 0}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-slate-400">Modules</span>
                                            <span className="text-white">{Object.keys(selectedPlan.test_plan?.modules || {}).length}</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-20 text-center">
                        <Globe size={48} className="text-slate-600 mb-4" />
                        <h3 className="text-xl font-semibold text-white mb-2">No Applications Explored</h3>
                        <p className="text-slate-400 mb-6">
                            Enter a URL above to explore and generate test scenarios
                        </p>
                    </div>
                )}

                {/* Toast */}
                {toast && (
                    <div className={`fixed bottom-6 right-6 px-6 py-3 rounded-lg shadow-lg flex items-center gap-2 ${toast.type === "success" ? "bg-emerald-500" : "bg-red-500"
                        } text-white`}>
                        {toast.type === "success" ? <CheckCircle size={18} /> : <XCircle size={18} />}
                        {toast.message}
                    </div>
                )}

                {/* Video Preview Modal */}
                {videoModalOpen && (
                    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setVideoModalOpen(false)}>
                        <div className="bg-[#121214] border border-white/10 rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-between p-4 border-b border-white/5">
                                <div className="flex items-center gap-3">
                                    <Video size={20} className="text-blue-400" />
                                    <h3 className="text-lg font-semibold text-white">
                                        Video Recording
                                        {selectedScenarioForPreview && (
                                            <span className="text-slate-400 font-normal ml-2">
                                                - {selectedScenarioForPreview.name}
                                            </span>
                                        )}
                                    </h3>
                                </div>
                                <button
                                    onClick={() => setVideoModalOpen(false)}
                                    className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                                >
                                    <X size={20} className="text-slate-400" />
                                </button>
                            </div>
                            <div className="p-6">
                                {loadingPreview ? (
                                    <div className="flex items-center justify-center py-12">
                                        <Loader2 size={32} className="text-[#00D4AA] animate-spin" />
                                    </div>
                                ) : previewVideos.length > 0 ? (
                                    <div className="space-y-4">
                                        {previewVideos.map((video, index) => (
                                            <div key={video.filename} className="bg-black rounded-lg overflow-hidden">
                                                <video
                                                    controls
                                                    className="w-full"
                                                    src={activeRunId ? getScenarioVideoFileUrl(activeRunId, video.filename) : ""}
                                                >
                                                    Your browser does not support the video tag.
                                                </video>
                                                <div className="p-2 bg-[#1a1a1d] flex items-center justify-between">
                                                    <span className="text-xs text-slate-400">{video.filename}</span>
                                                    <span className="text-xs text-slate-500">{(video.size / 1024 / 1024).toFixed(2)} MB</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center justify-center py-12 text-center">
                                        <Video size={48} className="text-slate-600 mb-4" />
                                        <p className="text-slate-400">No video recordings available</p>
                                        <p className="text-sm text-slate-500 mt-1">
                                            Videos are recorded during test execution
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Code Preview Modal */}
                {codeModalOpen && (
                    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setCodeModalOpen(false)}>
                        <div className="bg-[#121214] border border-white/10 rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-between p-4 border-b border-white/5">
                                <div className="flex items-center gap-3">
                                    <Code size={20} className="text-emerald-400" />
                                    <h3 className="text-lg font-semibold text-white">
                                        Generated Playwright Code
                                        {selectedScenarioForPreview && (
                                            <span className="text-slate-400 font-normal ml-2">
                                                - {selectedScenarioForPreview.name}
                                            </span>
                                        )}
                                    </h3>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={copyCode}
                                        className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 text-slate-300 rounded transition-colors flex items-center gap-1"
                                    >
                                        <Copy size={12} />
                                        Copy
                                    </button>
                                    <button
                                        onClick={() => setCodeModalOpen(false)}
                                        className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                                    >
                                        <X size={20} className="text-slate-400" />
                                    </button>
                                </div>
                            </div>
                            <div className="flex-1 overflow-auto p-4">
                                {loadingPreview ? (
                                    <div className="flex items-center justify-center py-12">
                                        <Loader2 size={32} className="text-[#00D4AA] animate-spin" />
                                    </div>
                                ) : (
                                    <pre className="bg-[#0a0a0b] p-4 rounded-lg text-sm text-slate-300 font-mono overflow-x-auto">
                                        <code>{previewCode}</code>
                                    </pre>
                                )}
                            </div>
                            <div className="p-4 border-t border-white/5 bg-[#0f0f11]">
                                <p className="text-xs text-slate-500">
                                    This code can be used with Playwright and pytest. Install with: <code className="bg-white/5 px-1 rounded">pip install playwright pytest-playwright</code>
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
