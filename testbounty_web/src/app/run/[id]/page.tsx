"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import {
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    Terminal as TerminalIcon,
    Shield,
    MessageSquare,
    Loader2,
    Send
} from "lucide-react";
import { getRunStatus, getRunArtifact, getExecutionProgress, getScreenshotUrl, getTestVideoUrl, getTestCode, Run, ExecutionProgress } from "@/lib/api";

type TestStatus = "pending" | "running" | "passed" | "failed";

interface TestCase {
    id: string;
    name: string;
    description?: string;
    category?: string;
    priority?: string;
    endpoint?: string;
    method?: string;
}

interface TestResult {
    test_id: string;
    status: TestStatus;
    duration?: number;
    error_message?: string;
    stdout?: string;
}

interface TestPlan {
    type: string;
    scenarios: TestCase[];
}

interface ChatMessage {
    role: "user" | "agent";
    content: string;
    timestamp: number;
}

export default function ExecutionPage() {
    const params = useParams();
    const runId = params?.id as string;
    const [activeTab, setActiveTab] = useState<"terminal" | "chat">("terminal");

    const [run, setRun] = useState<Run | null>(null);
    const [scenarios, setScenarios] = useState<TestCase[]>([]);
    const [results, setResults] = useState<Record<string, TestResult>>({});
    const [currentTest, setCurrentTest] = useState<TestCase | null>(null);
    const [currentlyRunningId, setCurrentlyRunningId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [logs, setLogs] = useState<string[]>([]);

    // Video/Code State
    const [viewMode, setViewMode] = useState<"preview" | "code">("preview");
    const [codeContent, setCodeContent] = useState<string>("");
    const [videoUrl, setVideoUrl] = useState<string | null>(null);
    const [videoLoading, setVideoLoading] = useState<boolean>(false);
    const [videoError, setVideoError] = useState<boolean>(false);
    const [liveScreenshot, setLiveScreenshot] = useState<string | null>(null);
    const [executionProgress, setExecutionProgress] = useState<ExecutionProgress | null>(null);

    // Chat State
    const [chatInput, setChatInput] = useState("");
    const [messages, setMessages] = useState<ChatMessage[]>([
        { role: "agent", content: "I am monitoring the test execution. Use this chat to request fixes or ask about vulnerabilities found.", timestamp: Date.now() }
    ]);
    const [chatLoading, setChatLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, activeTab]);

    const handleSendMessage = async () => {
        if (!chatInput.trim() || chatLoading) return;

        const userMsg: ChatMessage = { role: "user", content: chatInput, timestamp: Date.now() };
        setMessages(prev => [...prev, userMsg]);
        setChatInput("");
        setChatLoading(true);

        try {
            const res = await fetch("http://localhost:8000/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userMsg.content, run_id: runId })
            });
            const data = await res.json();

            const agentMsg: ChatMessage = { role: "agent", content: data.content, timestamp: Date.now() };
            setMessages(prev => [...prev, agentMsg]);
        } catch (e) {
            console.error("Chat error", e);
            setMessages(prev => [...prev, { role: "agent", content: "Error connecting to agent.", timestamp: Date.now() }]);
        } finally {
            setChatLoading(false);
        }
    };

    // Fetch Code and Video for selected test
    useEffect(() => {
        if (!runId || !currentTest) return;

        const loadTestArtifacts = async () => {
            // Set loading state
            setVideoLoading(true);
            setVideoError(false);
            setCodeContent("// Loading test code...");

            // Load test-specific code
            try {
                const code = await getTestCode(runId, currentTest.id);
                if (code.content) setCodeContent(code.content);
            } catch {
                // Fall back to general test code
                try {
                    const code = await getRunArtifact(runId, "test_code");
                    if (code.content) setCodeContent(code.content);
                } catch {
                    setCodeContent("// Code not available for this test");
                }
            }

            // Load test-specific video with cache busting
            const videoPath = getTestVideoUrl(runId, currentTest.id);
            setVideoUrl(`${videoPath}?t=${Date.now()}`);
            setVideoLoading(false);
        };

        loadTestArtifacts();
    }, [runId, currentTest?.id]);

    // Poll for run status and execution progress
    useEffect(() => {
        if (!runId) return;

        let isMounted = true;
        let consecutiveErrors = 0;
        const MAX_ERRORS = 5;
        let isPolling = false; // Prevent overlapping requests

        const fetchRun = async () => {
            if (!isMounted || isPolling) return;
            isPolling = true;

            try {
                const data = await getRunStatus(runId);
                if (!isMounted) {
                    isPolling = false;
                    return;
                }

                consecutiveErrors = 0; // Reset on success
                setRun(data);

                // Fetch artifacts early to show test list during execution
                if (scenarios.length === 0 && (data.status === 'running' || data.status === 'completed')) {
                    await fetchArtifacts(runId);
                }

                // Fetch execution progress for live updates AND completed results
                try {
                    const progress = await getExecutionProgress(runId);
                    if (!isMounted) return;

                    setExecutionProgress(progress);

                    // Update results from progress - always do this
                    if (progress.results) {
                        const newResults: Record<string, TestResult> = {};
                        Object.entries(progress.results).forEach(([testId, result]) => {
                            const resultData = result as { status: string; name?: string; message?: string };
                            newResults[testId] = {
                                test_id: testId,
                                status: resultData.status as TestStatus,
                                stdout: resultData.message || ''
                            };
                        });
                        setResults(newResults);
                    }

                    // Only update running test indicator if still in progress
                    if (data.status === 'running' || data.status === 'pending') {
                        if (progress.current_test) {
                            setCurrentlyRunningId(progress.current_test);
                            const runningTest = scenarios.find(s => s.id === progress.current_test);
                            if (runningTest) setCurrentTest(runningTest);
                        } else {
                            setCurrentlyRunningId(null);
                        }

                        // Update live screenshot with cache-busting
                        if (progress.current_screenshot) {
                            const screenshotUrl = getScreenshotUrl(runId, progress.current_screenshot);
                            setLiveScreenshot(`${screenshotUrl}?t=${Date.now()}`);
                        }
                    }
                } catch {
                    // Progress file may not exist yet - this is normal
                }

                // Parse stdout for logs display
                if (data.results?.stdout) {
                    setLogs(data.results.stdout.split('\n').filter(Boolean));
                } else if (data.steps) {
                    setLogs(data.steps.map(s => `[STEP] ${s}`));
                }

                if (data.status === "completed" || data.status === "failed") {
                    setCurrentlyRunningId(null);
                    setLiveScreenshot(null);
                    await fetchArtifacts(runId);
                }
            } catch (e) {
                consecutiveErrors++;
                if (consecutiveErrors >= MAX_ERRORS) {
                    console.warn("Polling paused after repeated failures - will retry");
                    // Reset after a delay to retry
                    setTimeout(() => { consecutiveErrors = 0; }, 10000);
                }
            } finally {
                isPolling = false;
                if (isMounted) setLoading(false);
            }
        };

        fetchRun();
        // Poll at reasonable rate - not too fast to avoid network spam
        const pollRate = run?.status === 'running' ? 2000 : (run?.status === 'completed' || run?.status === 'failed') ? 10000 : 3000;
        const interval = setInterval(fetchRun, pollRate);

        return () => {
            isMounted = false;
            clearInterval(interval);
        };
    }, [runId, scenarios.length, run?.status]);

    const fetchArtifacts = async (id: string) => {
        try {
            let allScenarios: TestCase[] = [];
            try {
                const bPlan: TestPlan = await getRunArtifact(id, "backend_plan");
                if (bPlan?.scenarios) allScenarios = [...allScenarios, ...bPlan.scenarios];
            } catch { /* Plan may not exist yet */ }

            try {
                const sPlan: TestPlan = await getRunArtifact(id, "security_test_plan");
                if (sPlan?.scenarios) allScenarios = [...allScenarios, ...sPlan.scenarios];
            } catch { /* Security plan may not exist */ }

            setScenarios(allScenarios);

            if (allScenarios.length > 0 && !currentTest) {
                setCurrentTest(allScenarios[0]);
            }
        } catch (e) { /* Ignore artifact fetch errors */ }
    };




    const renderStatusIcon = (status: TestStatus, testId?: string) => {
        // Check if this specific test is currently running
        const isCurrentlyRunning = testId && currentlyRunningId === testId;

        if (isCurrentlyRunning || status === "running") {
            return (
                <div className="relative">
                    <div className="w-3 h-3 bg-amber-400 rounded-full animate-pulse" />
                    <div className="absolute inset-0 w-3 h-3 bg-amber-400 rounded-full animate-ping opacity-75" />
                </div>
            );
        }

        switch (status) {
            case "passed":
                return (
                    <div className="w-3 h-3 bg-[#00D4AA] rounded-full shadow-[0_0_8px_rgba(0,212,170,0.5)]">
                        <CheckCircle2 size={12} className="text-black" />
                    </div>
                );
            case "failed":
                return <div className="w-3 h-3 bg-red-500 rounded-full shadow-[0_0_6px_rgba(239,68,68,0.5)]" />;
            default:
                return <div className="w-3 h-3 bg-slate-700 rounded-full border border-slate-600" />;
        }
    };

    const groupedCases = scenarios.reduce((acc, test) => {
        let cat = test.category || "Other";
        if (cat.includes("Function")) cat = "Functional";
        else if (cat.includes("Edge")) cat = "Edge Case";
        else if (cat.includes("Injection") || cat.includes("Security")) cat = "Security";
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(test);
        return acc;
    }, {} as Record<string, TestCase[]>);

    return (
        <div className="flex min-h-screen bg-[#0E0E0E] text-slate-200 font-sans selection:bg-[#00D4AA]/30 overflow-hidden">
            <Sidebar />

            <main className="flex-1 ml-64 flex flex-col h-screen overflow-hidden">
                <header className="flex-none px-6 py-4 border-b border-white/5 flex items-center justify-between bg-[#0E0E0E] z-10">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 text-sm text-slate-500">
                            <span className="text-slate-300">Run #{runId.slice(0, 6)}</span>
                            <ChevronRight size={14} />
                            <span className="text-white">Execution</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        {(run?.status === 'running' || run?.status === 'pending') ? (
                            <div className="flex items-center gap-4">
                                {scenarios.length > 0 && run?.steps?.includes('execute') && (
                                    <span className="text-xs text-slate-400">
                                        {Math.min(Object.values(results).filter(r => r.status === 'passed' || r.status === 'failed').length, scenarios.length)} / {scenarios.length} tests
                                    </span>
                                )}
                                <span className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
                                    <Loader2 size={12} className="animate-spin" />
                                    {run?.steps?.includes('execute') ? (
                                        currentlyRunningId ? `Running: ${currentlyRunningId}` : 'Executing Tests...'
                                    ) : (
                                        `${run?.steps?.slice(-1)[0] || 'Initializing'}...`
                                    )}
                                </span>
                            </div>
                        ) : (
                            <div className="flex items-center gap-4">
                                {scenarios.length > 0 && (
                                    <span className="text-xs text-slate-400">
                                        {scenarios.length} tests executed
                                    </span>
                                )}
                                <span className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border ${run?.status === 'completed' ? 'bg-[#00D4AA]/10 text-[#00D4AA] border-[#00D4AA]/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                    {run?.status === 'completed' ? <CheckCircle2 size={12} /> : null}
                                    {run?.status === 'completed' ? "Completed" : run?.status}
                                </span>
                            </div>
                        )}
                    </div>
                </header>

                <div className="flex-1 grid grid-cols-12 overflow-hidden">
                    {/* LEFT PANE */}
                    <div className="col-span-3 border-r border-white/5 bg-[#0F0F11] flex flex-col h-full overflow-hidden">
                        <div className="flex-none p-4 border-b border-white/5">
                            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Test Suite</h2>
                            {scenarios.length > 0 && (
                                <p className="text-[10px] text-slate-600 mt-1">{scenarios.length} test cases</p>
                            )}
                        </div>
                        <div className="flex-1 overflow-y-auto p-2 space-y-1 min-h-0 custom-scrollbar">
                            {Object.entries(groupedCases).map(([category, items]) => (
                                items.length > 0 && (
                                    <div key={category} className="mb-2">
                                        <div className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-white/5 rounded cursor-pointer">
                                            <ChevronDown size={14} />
                                            {category} Tests
                                        </div>
                                        <div className="pl-4 space-y-0.5 mt-1">
                                            {items.map(test => {
                                                const res = results[test.id];
                                                const status = res?.status || "pending";
                                                const isRunning = currentlyRunningId === test.id;
                                                return (
                                                    <div
                                                        key={test.id}
                                                        onClick={() => setCurrentTest(test)}
                                                        className={`flex items-center gap-3 px-3 py-2 rounded cursor-pointer text-xs transition-all duration-300 ${isRunning
                                                            ? 'bg-amber-500/10 text-amber-400 border-l-2 border-amber-400'
                                                            : currentTest?.id === test.id
                                                                ? 'bg-[#1A1A1D] text-white'
                                                                : 'text-slate-500 hover:text-slate-300'
                                                            }`}
                                                    >
                                                        {renderStatusIcon(status, test.id)}
                                                        <span className="truncate flex-1">{test.name}</span>
                                                        {isRunning && (
                                                            <span className="text-[10px] text-amber-400 animate-pulse">Running</span>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )
                            ))}
                        </div>
                    </div>

                    {/* CENTER PANE */}
                    <div className="col-span-6 border-r border-white/5 bg-[#0E0E0E] flex flex-col relative h-full overflow-hidden">
                        <div className="flex items-center border-b border-white/5 px-4 h-12 flex-none">
                            <div className="flex gap-4 h-full">
                                <button onClick={() => setViewMode("preview")} className={`text-xs font-medium h-full border-b-2 px-1 transition-colors ${viewMode === 'preview' ? 'border-[#00D4AA] text-white' : 'border-transparent text-slate-500 hover:text-slate-300'}`}>Preview</button>
                                <button onClick={() => setViewMode("code")} className={`text-xs font-medium h-full border-b-2 px-1 transition-colors ${viewMode === 'code' ? 'border-[#00D4AA] text-white' : 'border-transparent text-slate-500 hover:text-slate-300'}`}>Code</button>
                            </div>
                        </div>

                        <div className="flex-1 bg-black/50 p-4 overflow-hidden flex flex-col min-h-0">
                            {viewMode === 'preview' ? (
                                <div className="flex-1 flex items-center justify-center rounded-lg border border-white/5 bg-[#000] overflow-hidden relative min-h-0">
                                    {(run?.status === 'running' || run?.status === 'pending') ? (
                                        <div className="w-full h-full flex flex-col">
                                            {/* Check if we're in test execution phase */}
                                            {run?.steps?.includes('execute') || executionProgress?.status === 'running' ? (
                                                /* Live Screenshot Display - Tests Running */
                                                liveScreenshot ? (
                                                    <div className="flex-1 relative">
                                                        <img
                                                            src={liveScreenshot}
                                                            alt="Live test execution"
                                                            className="w-full h-full object-contain"
                                                            key={liveScreenshot}
                                                        />
                                                        {/* Live Badge */}
                                                        <div className="absolute top-3 left-3 flex items-center gap-2 bg-red-600 px-2 py-1 rounded text-xs font-medium text-white">
                                                            <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                                                            LIVE
                                                        </div>
                                                        {/* Progress Overlay */}
                                                        <div className="absolute top-3 right-3 bg-black/70 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/10">
                                                            <span className="text-xs text-[#00D4AA] font-medium">
                                                                {Object.values(results).filter(r => r.status === 'passed' || r.status === 'failed').length} / {scenarios.length || '?'}
                                                            </span>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="flex-1 flex items-center justify-center">
                                                        <div className="text-center">
                                                            <Loader2 size={32} className="animate-spin text-[#00D4AA] mx-auto mb-4" />
                                                            <p className="text-sm text-slate-400">Starting test execution...</p>
                                                            <p className="text-xs text-slate-600 mt-2">Screenshots will appear here</p>
                                                        </div>
                                                    </div>
                                                )
                                            ) : (
                                                /* Plan Generation Phase */
                                                <div className="flex-1 flex items-center justify-center">
                                                    <div className="text-center">
                                                        <div className="relative w-20 h-20 mx-auto mb-6">
                                                            <div className="absolute inset-0 border-4 border-white/10 rounded-full"></div>
                                                            <div className="absolute inset-0 border-4 border-t-[#00D4AA] rounded-full animate-spin"></div>
                                                        </div>
                                                        <p className="text-lg text-white font-medium mb-2">Analyzing & Generating Plans</p>
                                                        <p className="text-sm text-slate-400">
                                                            {run?.steps?.slice(-1)[0] ? `Current: ${run.steps.slice(-1)[0]}` : 'Initializing...'}
                                                        </p>
                                                        <div className="mt-4 flex items-center justify-center gap-2">
                                                            {['bootstrap', 'analyze', 'prd', 'plans', 'execute'].map((phase, i) => {
                                                                const isComplete = run?.steps?.some(s =>
                                                                    phase === 'plans' ? ['backend_plan', 'frontend_plan', 'security_plan'].includes(s) : s === phase
                                                                );
                                                                const isCurrent = run?.steps?.slice(-1)[0]?.includes(phase) ||
                                                                    (phase === 'plans' && ['backend_plan', 'frontend_plan', 'security_plan', 'join_plans'].some(p => run?.steps?.slice(-1)[0] === p));
                                                                return (
                                                                    <div key={phase} className="flex items-center gap-2">
                                                                        <div className={`w-2 h-2 rounded-full transition-all ${
                                                                            isComplete ? 'bg-[#00D4AA]' : isCurrent ? 'bg-amber-400 animate-pulse' : 'bg-slate-700'
                                                                        }`} />
                                                                        {i < 4 && <div className={`w-6 h-0.5 ${isComplete ? 'bg-[#00D4AA]' : 'bg-slate-700'}`} />}
                                                                    </div>
                                                                );
                                                            })}
                                                        </div>
                                                    </div>
                                                </div>
                                            )}

                                            {/* Current Test Info Bar */}
                                            <div className="flex-none p-3 bg-gradient-to-t from-black/90 to-black/50 border-t border-white/5">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-3">
                                                        {currentlyRunningId ? (
                                                            <>
                                                                <div className="relative">
                                                                    <div className="w-3 h-3 bg-amber-400 rounded-full animate-pulse" />
                                                                    <div className="absolute inset-0 w-3 h-3 bg-amber-400 rounded-full animate-ping opacity-75" />
                                                                </div>
                                                                <div>
                                                                    <p className="text-xs text-amber-400">Executing</p>
                                                                    <p className="text-sm text-white font-medium truncate max-w-xs">
                                                                        {scenarios.find(s => s.id === currentlyRunningId)?.name || currentlyRunningId}
                                                                    </p>
                                                                </div>
                                                            </>
                                                        ) : !run?.steps?.includes('execute') ? (
                                                            <div>
                                                                <p className="text-xs text-slate-500">Phase</p>
                                                                <p className="text-sm text-slate-300 font-medium">
                                                                    {run?.steps?.slice(-1)[0] || 'Initializing'}
                                                                </p>
                                                            </div>
                                                        ) : null}
                                                    </div>
                                                    {/* Progress Bar */}
                                                    <div className="w-32">
                                                        <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                                            <div
                                                                className="h-full bg-gradient-to-r from-[#00D4AA] to-emerald-500 transition-all duration-300"
                                                                style={{
                                                                    width: run?.steps?.includes('execute')
                                                                        ? `${Math.min(scenarios.length > 0 ? ((Object.values(results).filter(r => r.status === 'passed' || r.status === 'failed').length) / scenarios.length) * 100 : 0, 100)}%`
                                                                        : `${Math.min((run?.steps?.length || 0) * 15, 80)}%`
                                                                }}
                                                            />
                                                        </div>
                                                        <p className="text-[10px] text-slate-500 mt-1 text-right">
                                                            {run?.steps?.includes('execute')
                                                                ? `${Math.min(scenarios.length > 0 ? Math.round(((Object.values(results).filter(r => r.status === 'passed' || r.status === 'failed').length) / scenarios.length) * 100) : 0, 100)}%`
                                                                : `${Math.min((run?.steps?.length || 0) * 15, 80)}%`
                                                            }
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ) : videoLoading ? (
                                        <div className="flex flex-col items-center justify-center">
                                            <Loader2 size={32} className="animate-spin text-[#00D4AA] mb-4" />
                                            <p className="text-sm text-slate-400">Loading test preview...</p>
                                        </div>
                                    ) : currentTest && (results[currentTest.id]?.status === 'passed' || results[currentTest.id]?.status === 'failed') ? (
                                        videoUrl && !videoError ? (
                                            <div className="relative w-full h-full flex items-center justify-center">
                                                <video
                                                    key={videoUrl}
                                                    src={videoUrl}
                                                    controls
                                                    className="max-w-full max-h-full object-contain"
                                                    onError={() => setVideoError(true)}
                                                />
                                            </div>
                                        ) : (
                                            <div className="text-center text-slate-500 p-4">
                                                <p>Video not available for this test</p>
                                                <p className="text-xs text-slate-600 mt-2">Test may have been API-only or screenshot-based</p>
                                            </div>
                                        )
                                    ) : (
                                        <div className="flex flex-col items-center justify-center">
                                            <Loader2 size={32} className="animate-spin text-slate-500 mb-4" />
                                            <p className="text-sm text-slate-400">
                                                {currentTest ? `Waiting for "${currentTest.name}" to complete...` : 'Select a test to view preview'}
                                            </p>
                                            <p className="text-xs text-slate-600 mt-2">Preview will appear when test finishes</p>
                                        </div>
                                    )}
                                    {currentTest && (
                                        <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/90 to-transparent pointer-events-none">
                                            <h3 className="text-white font-medium text-sm">{currentTest.name}</h3>
                                            <p className="text-slate-400 text-xs truncate max-w-lg">{currentTest.description}</p>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="flex-1 overflow-auto rounded-lg border border-white/5 bg-[#121214] p-4 min-h-0 w-full">
                                    <pre className="text-[10px] font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">{codeContent || "// Loading code..."}</pre>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* RIGHT PANE: Output & Chat */}
                    <div className="col-span-3 bg-[#0A0A0C] flex flex-col h-full overflow-hidden">
                        <div className="flex items-center border-b border-white/5 flex-none h-12">
                            <button onClick={() => setActiveTab('terminal')} className={`flex-1 py-3 text-xs font-medium uppercase tracking-wider flex items-center justify-center gap-2 ${activeTab === 'terminal' ? 'text-white border-b-2 border-[#00D4AA]' : 'text-slate-500 hover:text-slate-300'}`}><TerminalIcon size={14} /> Output</button>
                            <button onClick={() => setActiveTab('chat')} className={`flex-1 py-3 text-xs font-medium uppercase tracking-wider flex items-center justify-center gap-2 ${activeTab === 'chat' ? 'text-white border-b-2 border-[#00D4AA]' : 'text-slate-500 hover:text-slate-300'}`}><MessageSquare size={14} /> Agent Chat</button>
                        </div>

                        <div className="flex-1 overflow-hidden p-4 font-mono text-xs relative flex flex-col min-h-0">
                            {activeTab === 'terminal' ? (
                                <div className="h-full overflow-y-auto space-y-1 text-slate-400 custom-scrollbar">
                                    <div className="text-slate-500 mb-2"># Execution Logs</div>
                                    {logs.map((line, i) => (
                                        <div key={i} className="break-all border-b border-white/5 pb-1 mb-1">
                                            <span className="text-emerald-500 mr-2">$</span>
                                            {line}
                                        </div>
                                    ))}
                                    {logs.length === 0 && <div className="text-slate-600 italic">Waiting for output...</div>}
                                </div>
                            ) : (
                                <div className="h-full flex flex-col min-h-0">
                                    <div className="flex-1 overflow-y-auto space-y-4 custom-scrollbar pb-4 min-h-0">
                                        {messages.map((msg, idx) => (
                                            <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${msg.role === 'agent' ? 'bg-[#00D4AA]/10' : 'bg-slate-700'}`}>
                                                    {msg.role === 'agent' ? <div className="w-4 h-4 bg-[#00D4AA] rounded-sm" /> : <div className="w-4 h-4 bg-slate-400 rounded-sm" />}
                                                </div>
                                                <div className={`p-3 rounded-lg border max-w-[85%] ${msg.role === 'agent' ? 'bg-[#1A1A1D] border-white/5 text-slate-300 rounded-tl-none' : 'bg-[#00D4AA]/10 border-[#00D4AA]/20 text-white rounded-tr-none'}`}>
                                                    {msg.content}
                                                </div>
                                            </div>
                                        ))}
                                        <div ref={messagesEndRef} />
                                    </div>
                                    <div className="mt-2 pt-3 border-t border-white/5 relative">
                                        <input
                                            type="text"
                                            value={chatInput}
                                            onChange={(e) => setChatInput(e.target.value)}
                                            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                                            disabled={chatLoading}
                                            placeholder="Ask agent..."
                                            className="w-full bg-[#121214] border border-white/10 rounded-lg pl-4 pr-10 py-2.5 text-white focus:outline-none focus:border-[#00D4AA]/50 placeholder:text-slate-600 disabled:opacity-50"
                                        />
                                        <button
                                            onClick={handleSendMessage}
                                            disabled={chatLoading || !chatInput.trim()}
                                            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-[#00D4AA] disabled:opacity-30 transition-colors"
                                        >
                                            {chatLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
}
