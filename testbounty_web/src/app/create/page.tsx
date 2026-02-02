"use client";

import { useState, useEffect } from "react";
import { startRun, getRunStatus, getRunArtifact, Run } from "@/lib/api";
import {
    Play,
    Globe,
    Clock,
    ChevronRight,
    FileText,
    ShieldCheck,
    Folder,
    Upload,
    CheckCircle2,
    Database,
    Server,
    Search,
    ChevronDown,
    ChevronUp,
    MoreVertical
} from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { useRouter } from "next/navigation";

export type Step = 1 | 2 | 3 | 4 | 5;

export interface BackendTestCase {
    id: string;
    name: string;
    endpoint?: string;
    method?: string;
    priority?: "High" | "Medium" | "Low" | "Critical";
    description?: string;
    category?: string;
}

export interface BackendPlan {
    type: string;
    scenarios: BackendTestCase[];
}

export default function CreateTestsPage() {
    const router = useRouter();

    // Wizard state
    const [step, setStep] = useState<Step>(1);

    // Step 1 – basic test info
    const [testName, setTestName] = useState("Login Test");

    // Step 2 – API / target configuration
    const [testType, setTestType] = useState<"url" | "local">("url");
    const [apiName, setApiName] = useState("");
    const [url, setUrl] = useState("https://api.example.com/v1/users/12345");
    const [projectPath, setProjectPath] = useState("d:/game_development/test_sprite_agent");
    const [authType, setAuthType] = useState("none");
    const [extraInfo, setExtraInfo] = useState("");

    // Credentials for login testing
    const [testUsername, setTestUsername] = useState("");
    const [testPassword, setTestPassword] = useState("");

    // Run + plan state
    const [runId, setRunId] = useState<string | null>(null);
    const [run, setRun] = useState<Run | null>(null);
    const [backendPlan, setBackendPlan] = useState<BackendPlan | null>(null);
    const [securityPlan, setSecurityPlan] = useState<BackendPlan | null>(null);

    // Selection State
    const [selectedTests, setSelectedTests] = useState<Set<string>>(new Set());

    // UI Loading states
    const [loading, setLoading] = useState(false);
    const [planLoading, setPlanLoading] = useState(false);
    const [progress, setProgress] = useState(0);

    // Accordion state for Step 5
    const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
        "Functional Tests": true,
        "Edge Case Tests": true,
        "Security Tests": true,
        "Other": true
    });

    const toggleCategory = (cat: string) => {
        setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
    };

    const handleSelectAll = () => {
        const allScenarios = [...(backendPlan?.scenarios || []), ...(securityPlan?.scenarios || [])];
        const allIds = allScenarios.map(s => s.id);

        if (selectedTests.size === allIds.length) {
            setSelectedTests(new Set());
        } else {
            setSelectedTests(new Set(allIds));
        }
    };

    const toggleTest = (id: string) => {
        const newSet = new Set(selectedTests);
        if (newSet.has(id)) newSet.delete(id);
        else newSet.add(id);
        setSelectedTests(newSet);
    };

    const startBackendRun = async () => {
        setLoading(true);
        try {
            const payload: any = {
                test_name: testName,
                api_name: apiName,
                auth_type: authType,
                extra_info: extraInfo,
                // Include test credentials if provided
                test_credentials: testUsername && testPassword ? {
                    username: testUsername,
                    password: testPassword
                } : null
            };

            if (testType === "url") {
                payload.target_url = url;
            } else {
                payload.project_path = projectPath;
            }

            const res = await startRun(payload);
            setRunId(res.run_id);
            // Redirect immediately to execution page to see live progress
            router.push(`/run/${res.run_id}`);
        } catch (e) {
            console.error(e);
            alert("Failed to start run");
            setLoading(false);
        }
    };

    // Polling for run status and plans
    useEffect(() => {
        if (!runId || step !== 3) return;

        const interval = setInterval(async () => {
            try {
                const data = await getRunStatus(runId);
                setRun(data);

                if (data.status === "completed") {
                    setProgress(100);
                    // Load plans
                    if (!backendPlan) {
                        setPlanLoading(true);
                        try {
                            // Try fetching both, ignore if one fails but ideally both exist
                            const bPlan: BackendPlan = await getRunArtifact(runId, "backend_plan");
                            setBackendPlan(bPlan);

                            // Initialize selection with all functional tests
                            if (bPlan?.scenarios) {
                                setSelectedTests(new Set(bPlan.scenarios.map(s => s.id)));
                            }

                            try {
                                const sPlan: BackendPlan = await getRunArtifact(runId, "security_test_plan");
                                setSecurityPlan(sPlan);
                                // Add security tests to selection
                                if (sPlan?.scenarios) {
                                    setSelectedTests(prev => {
                                        const next = new Set(prev);
                                        sPlan.scenarios.forEach(s => next.add(s.id));
                                        return next;
                                    });
                                }
                            } catch (err) {
                                console.log("Security plan not found or failed to load", err);
                            }

                        } catch (e) {
                            console.error("Failed to load backend plan", e);
                        } finally {
                            setPlanLoading(false);
                        }
                    }

                    // Auto advance to summary after a short delay
                    if (step === 3) {
                        setTimeout(() => setStep(4), 1000);
                    }
                } else {
                    setProgress(prev => Math.min(prev + 10, 90));
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [runId, step, backendPlan]);


    const renderStepper = () => (
        <div className="flex items-center gap-4 text-sm text-slate-500 mb-8">
            <span className={`flex items-center gap-2 ${step === 1 ? "text-white font-medium" : ""}`}>
                <span className={`flex items-center justify-center w-5 h-5 rounded text-xs font-bold ${step >= 1 ? "bg-[#121214] border border-white/20 text-white" : "border border-slate-700"}`}>1</span>
                Test Info
            </span>
            <ChevronRight size={12} />

            <span className={`flex items-center gap-2 ${step === 2 ? "text-white font-medium" : ""}`}>
                <span className={`flex items-center justify-center w-5 h-5 rounded text-xs font-bold ${step >= 2 ? "bg-[#121214] border border-white/20 text-white" : "border border-slate-700"}`}>2</span>
                Input API & Target
            </span>
            <ChevronRight size={12} />

            <span className={`flex items-center gap-2 ${step === 3 ? "text-white font-medium" : ""}`}>
                <span className={`flex items-center justify-center w-5 h-5 rounded text-xs font-bold ${step >= 3 ? "bg-[#121214] border border-white/20 text-white" : "border border-slate-700"}`}>3</span>
                Generating Plans
            </span>
            <ChevronRight size={12} />

            <span className={`flex items-center gap-2 ${step === 4 ? "text-white font-medium" : ""}`}>
                <span className={`flex items-center justify-center w-5 h-5 rounded text-xs font-bold ${step >= 4 ? "bg-[#121214] border border-white/20 text-white" : "border border-slate-700"}`}>4</span>
                Review Test Plan
            </span>
            <ChevronRight size={12} />

            <span className={`flex items-center gap-2 ${step === 5 ? "text-white font-medium" : ""}`}>
                <span className={`flex items-center justify-center w-5 h-5 rounded text-xs font-bold ${step >= 5 ? "bg-[#121214] border border-white/20 text-white" : "border border-slate-700"}`}>5</span>
                Select Test Cases
            </span>
        </div>
    );

    // Helpers for counts
    const totalBackend = backendPlan?.scenarios?.length ?? 0;
    const totalSecurity = securityPlan?.scenarios?.length ?? 0;
    const totalTestCases = totalBackend + totalSecurity;

    const functionalCount = backendPlan?.scenarios?.filter(s => s.category?.includes("Function"))?.length ?? 0;
    const edgeCount = backendPlan?.scenarios?.filter(s => s.category?.includes("Edge"))?.length ?? 0;
    const securityCount = totalSecurity;

    return (
        <div className="flex h-screen bg-black text-slate-300 font-sans selection:bg-[#00D4AA] selection:text-black">
            <Sidebar />

            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                <header className="h-16 border-b border-white/10 flex items-center justify-between px-8 bg-[#0a0a0c]">
                    <div className="flex items-center gap-4">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00D4AA] to-emerald-600 flex items-center justify-center shadow-lg shadow-[#00D4AA]/20">
                            <Play size={16} className="text-white fill-white" />
                        </div>
                        <div>
                            <h1 className="text-white font-medium">Create New Test</h1>
                            <div className="text-xs text-slate-500">Configure and launch a new test run</div>
                        </div>
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto p-8">
                    <div className="max-w-4xl mx-auto">
                        {renderStepper()}

                        {/* STEP 1: Basic Info */}
                        {step === 1 && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-white">Test Name</label>
                                        <input
                                            type="text"
                                            value={testName}
                                            onChange={(e) => setTestName(e.target.value)}
                                            className="w-full bg-[#121214] border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#00D4AA] transition-colors"
                                            placeholder="e.g. User Login Flow"
                                        />
                                    </div>

                                    <div className="pt-4">
                                        <button
                                            onClick={() => setStep(2)}
                                            className="bg-[#00D4AA] text-black font-medium px-6 py-3 rounded-lg hover:bg-[#00D4AA]/90 transition-all flex items-center gap-2"
                                        >
                                            Next Step
                                            <ChevronRight size={16} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* STEP 2: Input API / Target */}
                        {step === 2 && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <div className="p-4 rounded-lg bg-[#121214] border border-white/10 mb-6">
                                    <div className="flex items-center gap-8">
                                        <label className="flex items-center gap-3 cursor-pointer group">
                                            <input
                                                type="radio"
                                                name="testType"
                                                checked={testType === "url"}
                                                onChange={() => setTestType("url")}
                                                className="w-4 h-4 text-[#00D4AA] bg-transparent border-slate-600 focus:ring-[#00D4AA] focus:ring-offset-0"
                                            />
                                            <div className="group-hover:text-white transition-colors">
                                                <div className="font-medium">Public URL</div>
                                                <div className="text-xs text-slate-500">Test a publicly accessible API endpoint</div>
                                            </div>
                                        </label>

                                        <label className="flex items-center gap-3 cursor-pointer group">
                                            <input
                                                type="radio"
                                                name="testType"
                                                checked={testType === "local"}
                                                onChange={() => setTestType("local")}
                                                className="w-4 h-4 text-[#00D4AA] bg-transparent border-slate-600 focus:ring-[#00D4AA] focus:ring-offset-0"
                                            />
                                            <div className="group-hover:text-white transition-colors">
                                                <div className="font-medium">Local Project</div>
                                                <div className="text-xs text-slate-500">Analyze source code from disk</div>
                                            </div>
                                        </label>
                                    </div>
                                </div>

                                {testType === "url" ? (
                                    <div className="space-y-4">
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium text-white">Entry Point URL</label>
                                            <div className="relative">
                                                <Globe size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                                                <input
                                                    type="text"
                                                    value={url}
                                                    onChange={(e) => setUrl(e.target.value)}
                                                    className="w-full bg-[#121214] border border-white/10 rounded-lg pl-12 pr-4 py-3 text-white focus:outline-none focus:border-[#00D4AA] transition-colors font-mono"
                                                    placeholder="https://api.example.com/v1"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium text-white">Project Path</label>
                                            <div className="relative">
                                                <Folder size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
                                                <input
                                                    type="text"
                                                    value={projectPath}
                                                    onChange={(e) => setProjectPath(e.target.value)}
                                                    className="w-full bg-[#121214] border border-white/10 rounded-lg pl-12 pr-4 py-3 text-white focus:outline-none focus:border-[#00D4AA] transition-colors font-mono"
                                                    placeholder="C:/Projects/MyApp"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Additional common fields */}
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-white">API Name / Context</label>
                                    <input
                                        type="text"
                                        value={apiName}
                                        onChange={(e) => setApiName(e.target.value)}
                                        className="w-full bg-[#121214] border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#00D4AA] transition-colors"
                                        placeholder="User Service API"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-white">Additional Instructions</label>
                                    <textarea
                                        value={extraInfo}
                                        onChange={(e) => setExtraInfo(e.target.value)}
                                        className="w-full bg-[#121214] border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#00D4AA] transition-colors min-h-[100px]"
                                        placeholder="Any specific flows to test? e.g. 'Register a new user then delete it'"
                                    />
                                </div>

                                {/* Test Credentials Section */}
                                <div className="mt-6 p-4 rounded-lg bg-amber-500/5 border border-amber-500/20">
                                    <div className="flex items-center gap-2 mb-3">
                                        <ShieldCheck size={16} className="text-amber-400" />
                                        <span className="text-sm font-medium text-amber-400">Test Credentials (Optional)</span>
                                    </div>
                                    <p className="text-xs text-slate-500 mb-4">
                                        If the site has login functionality, provide valid credentials for positive test cases.
                                        These will be used to verify successful login flows.
                                    </p>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <label className="text-xs text-slate-400">Username / Email</label>
                                            <input
                                                type="text"
                                                value={testUsername}
                                                onChange={(e) => setTestUsername(e.target.value)}
                                                className="w-full bg-[#121214] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-amber-400 transition-colors"
                                                placeholder="test@example.com"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs text-slate-400">Password</label>
                                            <input
                                                type="password"
                                                value={testPassword}
                                                onChange={(e) => setTestPassword(e.target.value)}
                                                className="w-full bg-[#121214] border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-amber-400 transition-colors"
                                                placeholder="••••••••"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="pt-4 flex items-center gap-4">
                                    <button
                                        onClick={() => setStep(1)}
                                        className="text-slate-400 hover:text-white px-6 py-3 transition-colors"
                                    >
                                        Back
                                    </button>
                                    <button
                                        onClick={startBackendRun}
                                        disabled={loading}
                                        className="bg-[#00D4AA] text-black font-medium px-6 py-3 rounded-lg hover:bg-[#00D4AA]/90 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {loading ? "Initializing..." : "Generate Test Plan"}
                                        {!loading && <Play size={16} fill="currentColor" />}
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* STEP 3: Loading / Progress */}
                        {step === 3 && (
                            <div className="flex flex-col items-center justify-center py-20 space-y-8 animate-in fade-in duration-500">
                                <div className="relative w-24 h-24">
                                    <div className="absolute inset-0 border-4 border-white/10 rounded-full"></div>
                                    <div className="absolute inset-0 border-4 border-t-[#00D4AA] rounded-full animate-spin"></div>
                                    <div className="absolute inset-0 flex items-center justify-center font-mono font-bold text-xl text-[#00D4AA]">
                                        {progress}%
                                    </div>
                                </div>
                                <div className="text-center space-y-2">
                                    <h3 className="text-xl font-medium text-white">Analyzing & Generating Plans</h3>
                                    <p className="text-slate-500 max-w-md">
                                        TestSprite is analyzing your target... {run?.steps?.slice(-1)[0] || "Initializing"}
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* STEP 4: Summary / Review */}
                        {step === 4 && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <div className="bg-[#121214] border border-white/10 rounded-xl overflow-hidden">
                                    <div className="p-6 border-b border-white/10 flex items-center justify-between bg-gradient-to-r from-[#00D4AA]/5 to-transparent">
                                        <div>
                                            <h2 className="text-lg font-medium text-white mb-1">Test Plan Generated</h2>
                                            <div className="text-sm text-slate-400 flex items-center gap-2">
                                                <Clock size={12} />
                                                Run ID: {runId?.substring(0, 8)}...
                                            </div>
                                        </div>
                                        <div className="h-10 w-10 rounded-full bg-[#00D4AA]/10 flex items-center justify-center text-[#00D4AA]">
                                            <CheckCircle2 size={20} />
                                        </div>
                                    </div>

                                    <div className="divide-y divide-white/5">
                                        <div className="grid grid-cols-2 px-6 py-4 hover:bg-white/[0.02]">
                                            <div className="text-white">Target</div>
                                            <div className="text-slate-400 font-mono text-sm truncate">{testType === "url" ? url : projectPath}</div>
                                        </div>
                                        <div className="grid grid-cols-2 px-6 py-4 hover:bg-white/[0.02]">
                                            <div className="text-white">Total Scenarios</div>
                                            <div className="text-[#00D4AA] font-bold">{totalTestCases}</div>
                                        </div>
                                        <div className="grid grid-cols-2 px-6 py-4 hover:bg-white/[0.02]">
                                            <div className="text-white">Test Categories</div>
                                            <div className="text-white">
                                                <div className="mb-0.5">{functionalCount > 0 ? `${functionalCount} Functional Tests` : "-"}</div>
                                                <div className="mb-0.5 text-slate-400">{edgeCount > 0 ? `${edgeCount} Edge Case Tests` : ""}</div>
                                                <div className="text-red-400">{securityCount > 0 ? `${securityCount} Security Tests` : ""}</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="pt-4 flex items-center justify-end gap-4">
                                    <button
                                        onClick={() => setStep(2)}
                                        className="text-slate-400 hover:text-white px-6 py-3 transition-colors"
                                    >
                                        Back
                                    </button>
                                    <button
                                        onClick={() => setStep(5)}
                                        className="bg-[#00D4AA] text-black font-medium px-6 py-3 rounded-lg hover:bg-[#00D4AA]/90 transition-all flex items-center gap-2"
                                    >
                                        Review Test Cases
                                        <ChevronRight size={16} />
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* STEP 5: Selection / Accordion */}
                        {step === 5 && (
                            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 h-full flex flex-col">
                                <div className="flex items-center justify-between">
                                    <h2 className="text-xl font-medium text-white">Select Scenarios to Execute</h2>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={handleSelectAll}
                                            className="px-4 py-2 rounded border border-white/10 text-sm hover:bg-white/5 disabled:opacity-50"
                                        >
                                            {selectedTests.size > 0 && selectedTests.size === totalTestCases ? "Deselect All" : "Select All"}
                                        </button>
                                        <input type="text" placeholder="Search" className="bg-[#121214] border border-white/10 rounded px-3 py-2 text-sm focus:border-[#00D4AA] outline-none" />
                                    </div>
                                </div>

                                <div className="space-y-3 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                                    {/* Logic to merge and group */}
                                    {(() => {
                                        const allScenarios = [...(backendPlan?.scenarios || []), ...(securityPlan?.scenarios || [])];
                                        if (allScenarios.length === 0) {
                                            return <div className="text-slate-500 p-8 text-center border border-white/5 rounded-lg">No test cases generated.</div>;
                                        }

                                        const grouped = allScenarios.reduce((acc, scenario) => {
                                            const cat = scenario.category || "Other";
                                            let displayCat = "Other";
                                            // Handle various category label styles
                                            if (cat.includes("Edge") || scenario.priority === "Low") displayCat = "Edge Case Tests";
                                            else if (cat.includes("Function") || cat === "Happy Path") displayCat = "Functional Tests";
                                            else if (cat.includes("Injection") || cat.includes("XSS") || cat === "Security" || scenario.priority === "Critical") displayCat = "Security Tests";
                                            else displayCat = cat;

                                            if (!acc[displayCat]) acc[displayCat] = [];
                                            acc[displayCat].push(scenario);
                                            return acc;
                                        }, {} as Record<string, BackendTestCase[]>);

                                        return Object.entries(grouped).map(([category, scenarios]) => (
                                            <div key={category} className="border border-white/10 rounded-lg overflow-hidden bg-[#0a0a0c]">
                                                <button
                                                    onClick={() => toggleCategory(category)}
                                                    className="w-full flex items-center justify-between px-6 py-3 bg-[#121214] hover:bg-white/5 transition-colors"
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <div className={`w-4 h-4 rounded border flex items-center justify-center ${expandedCategories[category] ? 'bg-[#00D4AA] border-[#00D4AA]' : 'border-slate-600'}`}>
                                                            <CheckCircle2 size={10} className="text-black" />
                                                        </div>
                                                        <span className={`text-xs font-medium uppercase tracking-wider px-2 py-0.5 rounded ${category.includes('Edge') ? 'text-sky-400 bg-sky-500/10' :
                                                            category.includes('Security') ? 'text-red-400 bg-red-500/10' :
                                                                'text-[#00D4AA] bg-[#00D4AA]/10'
                                                            }`}>
                                                            {category}
                                                        </span>
                                                    </div>
                                                    {expandedCategories[category] ? <ChevronUp size={16} className="text-slate-500" /> : <ChevronDown size={16} className="text-slate-500" />}
                                                </button>

                                                {expandedCategories[category] && (
                                                    <div className="divide-y divide-white/5">
                                                        {scenarios.map(sc => (
                                                            <div
                                                                key={sc.id}
                                                                className="p-4 hover:bg-white/[0.02] flex items-start gap-3 pl-12 group cursor-pointer"
                                                                onClick={() => toggleTest(sc.id)}
                                                            >
                                                                <div className={`mt-1 w-4 h-4 rounded border flex items-center justify-center transition-colors ${selectedTests.has(sc.id) ? 'bg-[#00D4AA] border-[#00D4AA]' : 'border-slate-600 group-hover:border-[#00D4AA]'}`}>
                                                                    {selectedTests.has(sc.id) && <CheckCircle2 size={12} className="text-black" />}
                                                                </div>
                                                                <div className="flex-1">
                                                                    <div className="flex items-center justify-between">
                                                                        <div className="font-medium text-slate-200">{sc.name}</div>
                                                                        <div className={`text-[10px] px-1.5 py-0.5 rounded border ${sc.priority === 'High' || sc.priority === 'Critical' ? 'border-red-500/30 text-red-400' :
                                                                            sc.priority === 'Medium' ? 'border-amber-500/30 text-amber-400' :
                                                                                'border-slate-700 text-slate-500'
                                                                            }`}>
                                                                            {sc.priority || 'Normal'}
                                                                        </div>
                                                                    </div>
                                                                    <div className="text-sm text-slate-500 mt-1 line-clamp-2">{sc.description}</div>
                                                                    {sc.endpoint && (
                                                                        <div className="flex items-center gap-2 mt-2">
                                                                            <span className="text-xs font-mono bg-white/5 px-1.5 py-0.5 rounded text-indigo-300">{sc.method || 'GET'}</span>
                                                                            <span className="text-xs font-mono text-slate-600">{sc.endpoint}</span>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ));
                                    })()}
                                </div>

                                <div className="pt-4 border-t border-white/10 flex items-center justify-end gap-4">
                                    <button
                                        onClick={() => setStep(4)}
                                        className="text-slate-400 hover:text-white px-6 py-3 transition-colors"
                                    >
                                        Back
                                    </button>
                                    <button
                                        onClick={() => router.push(`/run/${runId}`)} // Navigate to Execution
                                        className="bg-[#00D4AA] text-black font-medium px-8 py-4 rounded-lg hover:bg-[#00D4AA]/90 transition-all flex items-center gap-2 shadow-lg shadow-[#00D4AA]/20"
                                    >
                                        {selectedTests.size > 0 ? `Execute ${selectedTests.size} Tests` : "Execute Tests"}
                                        <Play size={16} fill="currentColor" />
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </main>
            </div>
        </div>
    );
}
