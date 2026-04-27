"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import {
    startAutonomousSession, answerAutonomousQuestion,
    deleteAutonomousSession, saveAutonomousScenarios, WS_BASE,
} from "@/lib/api";
import {
    Globe, Play, Square, Brain, CheckCircle, XCircle, AlertCircle,
    Loader2, ChevronDown, ChevronRight, Image, Link2, Type,
    Eye, Zap, Shield, Search, BarChart3, Bell, Settings2,
    ShoppingCart, Map, MessageSquare, Users, Bot, Sparkles,
    X, Send, RefreshCw, FlaskConical, Save, ExternalLink,
    ListChecks, ChevronUp,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface AgentState {
    name: string;
    display: string;
    icon: string;
    role: string;
    status: "idle" | "running" | "waiting_answer" | "done" | "error";
    findings_count: number;
    findings: string[];
    current_task: string;
}

interface SessionEvent {
    id: string;
    type: "progress" | "screenshot" | "finding" | "warning" | "error"
        | "question" | "agent_start" | "done" | "analysis_complete" | "ping";
    agent: string;
    icon: string;
    message: string;
    data: any;
    screenshot?: string;
    timestamp: string;
    agents_snapshot?: AgentState[];
}

interface PendingQuestion {
    agent: string;
    question: string;
    options: string[];
}

// ── Constants ──────────────────────────────────────────────────────────────────

const AGENT_ICON_MAP: Record<string, React.ReactNode> = {
    orchestrator:    <Brain size={14} className="text-[#00D4AA]" />,
    landing_page:    <Globe size={14} className="text-blue-400" />,
    authentication:  <Shield size={14} className="text-yellow-400" />,
    dashboard:       <BarChart3 size={14} className="text-purple-400" />,
    user_profile:    <Users size={14} className="text-pink-400" />,
    products:        <ShoppingCart size={14} className="text-orange-400" />,
    orders:          <ShoppingCart size={14} className="text-amber-400" />,
    reports:         <BarChart3 size={14} className="text-emerald-400" />,
    alerts:          <Bell size={14} className="text-red-400" />,
    admin:           <Settings2 size={14} className="text-slate-400" />,
    tracking:        <Map size={14} className="text-cyan-400" />,
    support:         <MessageSquare size={14} className="text-indigo-400" />,
    general:         <Search size={14} className="text-slate-400" />,
};

const STATUS_COLOR: Record<string, string> = {
    idle:           "bg-slate-500/15 text-slate-400",
    running:        "bg-blue-500/15 text-blue-400",
    waiting_answer: "bg-yellow-500/15 text-yellow-400",
    done:           "bg-emerald-500/15 text-emerald-400",
    error:          "bg-red-500/15 text-red-400",
};

const EVENT_COLOR: Record<string, string> = {
    progress:    "text-slate-400",
    screenshot:  "text-blue-400",
    finding:     "text-emerald-400",
    warning:     "text-yellow-400",
    error:       "text-red-400",
    agent_start: "text-indigo-400",
    question:    "text-yellow-300",
    done:        "text-[#00D4AA]",
};

// ── Component ──────────────────────────────────────────────────────────────────

export default function AutonomousPage() {
    const [url, setUrl] = useState("");
    const [maxPages, setMaxPages] = useState(20);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [status, setStatus] = useState<string>("idle");
    const [agents, setAgents] = useState<AgentState[]>([]);
    const [events, setEvents] = useState<SessionEvent[]>([]);
    const [screenshot, setScreenshot] = useState<string | null>(null);
    const [pendingQuestion, setPendingQuestion] = useState<PendingQuestion | null>(null);
    const [customAnswer, setCustomAnswer] = useState("");
    const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());
    const [summary, setSummary] = useState<any>(null);
    const [wsConnected, setWsConnected] = useState(false);
    const [generatedScenarios, setGeneratedScenarios] = useState<Record<string, any[]>>({});
    const [expandedScenario, setExpandedScenario] = useState<string | null>(null);
    const [savingSuite, setSavingSuite] = useState(false);
    const [savedSuite, setSavedSuite] = useState<{ planId: string; suiteId: string | null } | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const eventLogRef = useRef<HTMLDivElement>(null);
    const sessionIdRef = useRef<string | null>(null);

    // Auto-scroll event log
    useEffect(() => {
        if (eventLogRef.current) {
            eventLogRef.current.scrollTop = eventLogRef.current.scrollHeight;
        }
    }, [events]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            wsRef.current?.close();
        };
    }, []);

    // ── WebSocket connection ───────────────────────────────────────────────────

    const connectWs = useCallback((sid: string) => {
        const ws = new WebSocket(`${WS_BASE}/ws/autonomous/${sid}`);
        wsRef.current = ws;

        ws.onopen = () => setWsConnected(true);
        ws.onclose = () => {
            setWsConnected(false);
            // Attempt reconnect if session still running
            if (sessionIdRef.current === sid) {
                setTimeout(() => {
                    if (sessionIdRef.current === sid) connectWs(sid);
                }, 2000);
            }
        };

        ws.onmessage = (e) => {
            try {
                const event: SessionEvent = JSON.parse(e.data);
                if (event.type === "ping") return;

                setEvents(prev => {
                    // Deduplicate by id
                    if (prev.some(x => x.id === event.id)) return prev;
                    return [...prev, event];
                });

                // Update agents snapshot
                if (event.agents_snapshot?.length) {
                    setAgents(event.agents_snapshot);
                }

                // Accumulate generated scenarios from finding events
                if (event.type === "finding" && event.data?.scenario_id && event.data?.steps) {
                    const feature = event.agent || "general";
                    setGeneratedScenarios(prev => {
                        const next = { ...prev };
                        if (!next[feature]) next[feature] = [];
                        // Avoid duplicates
                        if (!next[feature].some((s: any) => s.id === event.data.scenario_id)) {
                            next[feature] = [...next[feature], {
                                id:     event.data.scenario_id,
                                name:   event.message,
                                passed: event.data.passed,
                                total:  event.data.total,
                                steps:  event.data.steps,
                            }];
                        }
                        return next;
                    });
                }

                // Update screenshot
                if (event.screenshot) {
                    setScreenshot(event.screenshot);
                }

                // Question
                if (event.type === "question") {
                    setPendingQuestion({
                        agent: event.agent,
                        question: event.message,
                        options: event.data?.options || [],
                    });
                    setStatus("waiting_answer");
                }

                // Analysis complete — browser stays open, show summary
                if (event.type === "analysis_complete") {
                    setStatus("analysis_done");
                    if (event.data) setSummary(event.data);
                }

                // Done (browser closed)
                if (event.type === "done") {
                    setStatus("done");
                    sessionIdRef.current = null;
                }

                if (event.type === "error") setStatus("error");
            } catch (_) {}
        };
    }, []);

    // ── Handlers ──────────────────────────────────────────────────────────────

    const handleStart = async () => {
        if (!url.trim()) return;
        setEvents([]);
        setAgents([]);
        setScreenshot(null);
        setPendingQuestion(null);
        setSummary(null);
        setGeneratedScenarios({});
        setSavedSuite(null);
        setExpandedScenario(null);
        setStatus("starting");

        try {
            const res = await startAutonomousSession(url.trim(), maxPages);
            setSessionId(res.session_id);
            sessionIdRef.current = res.session_id;
            setStatus("running");
            connectWs(res.session_id);
        } catch (_) {
            setStatus("error");
        }
    };

    const handleStop = async () => {
        wsRef.current?.close();
        wsRef.current = null;
        if (sessionId) await deleteAutonomousSession(sessionId).catch(() => {});
        sessionIdRef.current = null;
        setSessionId(null);
        setStatus("idle");
        setWsConnected(false);
    };

    const sendAnswer = async (answer: string) => {
        setPendingQuestion(null);
        setCustomAnswer("");
        setStatus("running");
        if (sessionId) {
            // Send via WebSocket if connected
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: "answer", answer }));
            } else {
                await answerAutonomousQuestion(sessionId, answer).catch(() => {});
            }
        }
    };

    const handleSaveSuite = async () => {
        if (!sessionId) return;
        setSavingSuite(true);
        try {
            const domain = url.replace(/^https?:\/\//, "").split("/")[0];
            const suiteName = `Autonomous — ${domain}`;
            const res = await saveAutonomousScenarios(sessionId, suiteName);
            setSavedSuite({ planId: res.plan_id, suiteId: res.suite_id });
        } catch (_) {
            alert("Failed to save scenarios");
        } finally {
            setSavingSuite(false);
        }
    };

    const totalScenarios = Object.values(generatedScenarios).reduce((n, arr) => n + arr.length, 0);
    const isActive = status === "running" || status === "starting" || status === "waiting_answer";
    const isSessionOpen = isActive || status === "analysis_done";

    // ── Render ─────────────────────────────────────────────────────────────────

    return (
        <div className="flex min-h-screen bg-[#0a0a0b]">
            <Sidebar />
            <main className="flex-1 ml-64 flex flex-col">

                {/* ── AI Running overlay border ─────────────────────────────── */}
                {isActive && (
                    <div className="fixed inset-0 ml-64 pointer-events-none z-10">
                        <div className="absolute inset-0 border-2 border-[#00D4AA]/30 rounded-none animate-pulse" />
                        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-[#00D4AA] to-transparent animate-[scan_3s_ease-in-out_infinite]" />
                    </div>
                )}

                <div className="p-8 flex-1 flex flex-col gap-6">

                    {/* ── Header ───────────────────────────────────────────── */}
                    <div className="flex items-start justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                                <Bot size={24} className="text-[#00D4AA]" />
                                Autonomous Testing
                            </h1>
                            <p className="text-slate-400 mt-1 text-sm">
                                Provide any URL — AI agents launch a real browser, map every feature,
                                validate the UI, and build comprehensive test coverage automatically.
                            </p>
                        </div>
                        {isActive && (
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#00D4AA]/10 border border-[#00D4AA]/30">
                                <span className="w-2 h-2 rounded-full bg-[#00D4AA] animate-pulse" />
                                <span className="text-xs font-semibold text-[#00D4AA]">
                                    {status === "waiting_answer" ? "Waiting for your answer" : "AI Agents Running"}
                                </span>
                                {wsConnected && (
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 ml-1" title="Live" />
                                )}
                            </div>
                        )}
                        {status === "analysis_done" && (
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30">
                                <CheckCircle size={14} className="text-emerald-400" />
                                <span className="text-xs font-semibold text-emerald-400">Analysis Complete</span>
                                <span className="text-xs text-slate-500">Browser open · click Stop to close</span>
                            </div>
                        )}
                    </div>

                    {/* ── URL Input ─────────────────────────────────────────── */}
                    <div className="bg-[#121214] border border-white/5 rounded-xl p-5">
                        <div className="flex gap-3">
                            <div className="flex-1 flex gap-2">
                                <input
                                    type="url"
                                    value={url}
                                    onChange={e => setUrl(e.target.value)}
                                    onKeyDown={e => e.key === "Enter" && !isSessionOpen && handleStart()}
                                    placeholder="https://any-web-application.com"
                                    disabled={isSessionOpen}
                                    className="flex-1 px-4 py-3 bg-[#1a1a1d] border border-white/10 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:border-[#00D4AA]/50 disabled:opacity-50"
                                />
                                <div className="flex items-center gap-2 px-3 bg-[#1a1a1d] border border-white/10 rounded-lg">
                                    <span className="text-xs text-slate-500 whitespace-nowrap">Max pages</span>
                                    <input
                                        type="number"
                                        value={maxPages}
                                        onChange={e => setMaxPages(Math.max(5, Math.min(50, +e.target.value)))}
                                        disabled={isSessionOpen}
                                        className="w-12 bg-transparent text-white text-sm text-center focus:outline-none disabled:opacity-50"
                                        min={5} max={50}
                                    />
                                </div>
                            </div>
                            {isSessionOpen ? (
                                <button
                                    onClick={handleStop}
                                    className={`px-6 py-3 font-semibold rounded-lg transition-colors flex items-center gap-2 ${
                                        status === "analysis_done"
                                            ? "bg-slate-700/50 hover:bg-slate-700 text-slate-300 border border-slate-600/50"
                                            : "bg-red-500/15 hover:bg-red-500/25 text-red-400 border border-red-500/30"
                                    }`}
                                >
                                    <Square size={16} /> {status === "analysis_done" ? "Close Browser" : "Stop"}
                                </button>
                            ) : (
                                <button
                                    onClick={handleStart}
                                    disabled={!url.trim()}
                                    className="px-6 py-3 bg-[#00D4AA] hover:bg-[#00C099] text-black font-semibold rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                                >
                                    <Play size={16} /> Launch Agents
                                </button>
                            )}
                        </div>

                        {/* How it works */}
                        {status === "idle" && (
                            <div className="mt-4 grid grid-cols-4 gap-3">
                                {[
                                    { icon: <Globe size={14} />, label: "Launches browser", desc: "Real Chromium, fully visible" },
                                    { icon: <Search size={14} />, label: "Maps everything", desc: "Every link, form & button" },
                                    { icon: <Users size={14} />, label: "Assigns agents", desc: "One AI per feature" },
                                    { icon: <Sparkles size={14} />, label: "Generates tests", desc: "Ready to run E2E suite" },
                                ].map((step, i) => (
                                    <div key={i} className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg bg-white/3 border border-white/5">
                                        <span className="text-[#00D4AA] mt-0.5 shrink-0">{step.icon}</span>
                                        <div>
                                            <p className="text-xs font-medium text-white">{step.label}</p>
                                            <p className="text-xs text-slate-500">{step.desc}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* ── Question Modal ────────────────────────────────────── */}
                    {pendingQuestion && (
                        <div className="bg-yellow-500/8 border-2 border-yellow-500/40 rounded-xl p-5 animate-in fade-in">
                            <div className="flex items-start gap-3">
                                <div className="w-9 h-9 rounded-full bg-yellow-500/15 border border-yellow-500/30 flex items-center justify-center shrink-0 mt-0.5">
                                    <AlertCircle size={16} className="text-yellow-400" />
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs font-semibold text-yellow-400 uppercase tracking-wide">
                                            {pendingQuestion.agent.replace("_", " ")} Agent
                                        </span>
                                        <span className="text-xs text-slate-500">needs your input to continue</span>
                                    </div>
                                    <p className="text-white font-medium mb-3">{pendingQuestion.question}</p>

                                    {pendingQuestion.options.length > 0 && (
                                        <div className="flex flex-wrap gap-2 mb-3">
                                            {pendingQuestion.options.map((opt, i) => (
                                                <button
                                                    key={i}
                                                    onClick={() => sendAnswer(opt)}
                                                    className="px-4 py-2 bg-yellow-500/10 hover:bg-yellow-500/20 border border-yellow-500/30 hover:border-yellow-500/50 text-yellow-300 hover:text-yellow-200 text-sm font-medium rounded-lg transition-colors"
                                                >
                                                    {opt}
                                                </button>
                                            ))}
                                        </div>
                                    )}

                                    <div className="flex gap-2">
                                        <input
                                            value={customAnswer}
                                            onChange={e => setCustomAnswer(e.target.value)}
                                            onKeyDown={e => e.key === "Enter" && customAnswer.trim() && sendAnswer(customAnswer.trim())}
                                            placeholder="Or type a custom answer…"
                                            className="flex-1 px-3 py-2 bg-[#1a1a1d] border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-yellow-500/40"
                                        />
                                        <button
                                            onClick={() => customAnswer.trim() && sendAnswer(customAnswer.trim())}
                                            disabled={!customAnswer.trim()}
                                            className="px-4 py-2 bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-300 rounded-lg transition-colors disabled:opacity-40 flex items-center gap-1.5"
                                        >
                                            <Send size={14} /> Send
                                        </button>
                                        <button
                                            onClick={() => sendAnswer("skip")}
                                            className="px-3 py-2 bg-white/5 hover:bg-white/10 text-slate-400 rounded-lg transition-colors text-sm"
                                        >
                                            Skip
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* ── Main 3-column layout ─────────────────────────────── */}
                    {(isSessionOpen || status === "done" || status === "error" || agents.length > 0) && (
                        <div className="grid grid-cols-[1fr_320px_300px] gap-5 flex-1">

                            {/* ── Col 1: Live Screenshot ─────────────────────── */}
                            <div className="bg-[#121214] border border-white/5 rounded-xl overflow-hidden flex flex-col">
                                <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
                                    <div className="flex items-center gap-2">
                                        <Eye size={14} className="text-blue-400" />
                                        <span className="text-sm font-semibold text-white">Live View</span>
                                        <span className="text-xs text-slate-500">— what AI currently sees</span>
                                    </div>
                                    {isActive && (
                                        <span className="flex items-center gap-1.5 text-xs text-[#00D4AA]">
                                            <span className="w-1.5 h-1.5 rounded-full bg-[#00D4AA] animate-pulse" />
                                            Live
                                        </span>
                                    )}
                                </div>
                                <div className="flex-1 flex items-center justify-center bg-[#0a0a0b] min-h-[400px] relative">
                                    {screenshot ? (
                                        <img
                                            src={`data:image/jpeg;base64,${screenshot}`}
                                            alt="Live browser view"
                                            className="w-full h-full object-contain"
                                            onError={e => {
                                                // Try PNG fallback
                                                (e.target as HTMLImageElement).src = `data:image/png;base64,${screenshot}`;
                                            }}
                                        />
                                    ) : (
                                        <div className="flex flex-col items-center gap-3 text-slate-600">
                                            {isActive ? (
                                                <>
                                                    <Loader2 size={32} className="animate-spin text-[#00D4AA]" />
                                                    <span className="text-sm text-slate-500">Waiting for browser…</span>
                                                </>
                                            ) : (
                                                <>
                                                    <Globe size={40} />
                                                    <span className="text-sm">Screenshots appear here</span>
                                                </>
                                            )}
                                        </div>
                                    )}
                                    {/* Scanning animation overlay */}
                                    {isActive && screenshot && (
                                        <div className="absolute inset-0 pointer-events-none">
                                            <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#00D4AA]/40 animate-[scan_2s_ease-in-out_infinite]" />
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* ── Col 2: Agent Cards ─────────────────────────── */}
                            <div className="bg-[#121214] border border-white/5 rounded-xl overflow-hidden flex flex-col">
                                <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Users size={14} className="text-indigo-400" />
                                        <span className="text-sm font-semibold text-white">Agent Team</span>
                                    </div>
                                    <span className="text-xs text-slate-500">{agents.length} agent{agents.length !== 1 ? "s" : ""}</span>
                                </div>

                                <div className="flex-1 overflow-y-auto p-3 space-y-2">
                                    {agents.length === 0 && isActive && (
                                        <div className="flex flex-col items-center justify-center py-10 gap-3">
                                            <Loader2 size={24} className="animate-spin text-indigo-400" />
                                            <p className="text-xs text-slate-500">Spawning agents…</p>
                                        </div>
                                    )}

                                    {agents.map(agent => {
                                        const isExp = expandedAgents.has(agent.name);
                                        const icon = AGENT_ICON_MAP[agent.name] || <Bot size={14} className="text-slate-400" />;
                                        return (
                                            <div
                                                key={agent.name}
                                                className={`border rounded-xl overflow-hidden transition-colors ${
                                                    agent.status === "waiting_answer"
                                                        ? "border-yellow-500/40 bg-yellow-500/3"
                                                        : agent.status === "done"
                                                        ? "border-emerald-500/20 bg-emerald-500/3"
                                                        : agent.status === "running"
                                                        ? "border-blue-500/20 bg-blue-500/3"
                                                        : "border-white/8 bg-[#0f0f11]"
                                                }`}
                                            >
                                                <div
                                                    className="flex items-center gap-2.5 p-2.5 cursor-pointer hover:bg-white/5"
                                                    onClick={() => setExpandedAgents(prev => {
                                                        const s = new Set(prev);
                                                        s.has(agent.name) ? s.delete(agent.name) : s.add(agent.name);
                                                        return s;
                                                    })}
                                                >
                                                    {isExp
                                                        ? <ChevronDown size={12} className="text-slate-500 shrink-0" />
                                                        : <ChevronRight size={12} className="text-slate-500 shrink-0" />}
                                                    <span className="text-base">{agent.icon}</span>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-1.5">
                                                            <span className="text-xs font-semibold text-white truncate">{agent.display}</span>
                                                            {agent.status === "running" && (
                                                                <Loader2 size={10} className="text-blue-400 animate-spin shrink-0" />
                                                            )}
                                                        </div>
                                                        <p className="text-xs text-slate-500 truncate">{agent.current_task}</p>
                                                    </div>
                                                    <span className={`text-xs px-1.5 py-0.5 rounded-full shrink-0 ${STATUS_COLOR[agent.status] || STATUS_COLOR.idle}`}>
                                                        {agent.status === "waiting_answer" ? "⏳" : agent.status}
                                                    </span>
                                                </div>

                                                {isExp && (
                                                    <div className="border-t border-white/5 px-3 pb-3 pt-2 space-y-1.5">
                                                        <p className="text-xs text-slate-500 italic">{agent.role}</p>
                                                        {agent.findings_count > 0 && (
                                                            <p className="text-xs text-emerald-400">
                                                                {agent.findings_count} finding{agent.findings_count !== 1 ? "s" : ""}
                                                            </p>
                                                        )}
                                                        {agent.findings.slice(0, 4).map((f, i) => (
                                                            <p key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                                                                <span className="text-[#00D4AA] shrink-0 mt-0.5">›</span>
                                                                <span className="line-clamp-2">{f}</span>
                                                            </p>
                                                        ))}
                                                        {agent.findings.length > 4 && (
                                                            <p className="text-xs text-slate-600">+{agent.findings.length - 4} more</p>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}

                                    {/* Done/analysis_done summary */}
                                    {(status === "done" || status === "analysis_done") && summary && (
                                        <div className="mt-2 p-3 rounded-xl bg-[#00D4AA]/8 border border-[#00D4AA]/20 space-y-1.5">
                                            <p className="text-xs font-semibold text-[#00D4AA] flex items-center gap-1.5">
                                                <CheckCircle size={12} /> Analysis Complete
                                            </p>
                                            {[
                                                ["Pages explored",     summary.pages_explored],
                                                ["Features found",     summary.features_found],
                                                ["Agents deployed",    summary.agents_deployed],
                                                ["Test scenarios",     summary.scenarios_generated ?? totalScenarios],
                                                ["Issues found",       summary.total_issues],
                                            ].map(([label, val]) => (
                                                <div key={label as string} className="flex justify-between text-xs">
                                                    <span className="text-slate-400">{label}</span>
                                                    <span className={`font-medium ${label === "Test scenarios" ? "text-violet-400" : "text-white"}`}>
                                                        {val}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* ── Col 3: Event Log ───────────────────────────── */}
                            <div className="bg-[#121214] border border-white/5 rounded-xl overflow-hidden flex flex-col">
                                <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Zap size={14} className="text-yellow-400" />
                                        <span className="text-sm font-semibold text-white">Activity</span>
                                    </div>
                                    <span className="text-xs text-slate-500">{events.filter(e => e.type !== "ping").length} events</span>
                                </div>

                                <div
                                    ref={eventLogRef}
                                    className="flex-1 overflow-y-auto p-3 space-y-1.5 font-mono text-xs min-h-[400px] max-h-[600px]"
                                >
                                    {events.filter(e => e.type !== "ping").map(event => (
                                        <div key={event.id} className="flex items-start gap-2">
                                            <span className="text-slate-600 shrink-0 mt-0.5">
                                                {new Date(event.timestamp).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"})}
                                            </span>
                                            <div className="min-w-0 flex-1">
                                                <span className={`font-medium ${EVENT_COLOR[event.type] || "text-slate-400"}`}>
                                                    [{event.agent?.replace("_", " ")}]
                                                </span>{" "}
                                                <span className="text-slate-300 break-words">{event.message}</span>
                                                {event.type === "warning" && (
                                                    <AlertCircle size={10} className="inline ml-1 text-yellow-400" />
                                                )}
                                                {event.type === "finding" && (
                                                    <CheckCircle size={10} className="inline ml-1 text-emerald-400" />
                                                )}
                                            </div>
                                        </div>
                                    ))}

                                    {isActive && (
                                        <div className="flex items-center gap-2 text-slate-600">
                                            <Loader2 size={10} className="animate-spin" />
                                            <span>running…</span>
                                        </div>
                                    )}
                                    {status === "analysis_done" && (
                                        <div className="flex items-center gap-2 text-emerald-500 mt-1">
                                            <CheckCircle size={10} />
                                            <span>Analysis complete — browser open for inspection</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* ── Findings panel (issues from landing page, warnings) ── */}
                    {(status === "done" || status === "analysis_done" || (events.some(e => e.type === "finding" || e.type === "warning"))) && (
                        <div className="bg-[#121214] border border-white/5 rounded-xl p-5">
                            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                                <AlertCircle size={14} className="text-yellow-400" />
                                Issues & Findings
                            </h3>
                            <div className="grid grid-cols-2 gap-2">
                                {events
                                    .filter(e => e.type === "warning" || (e.type === "finding" && e.data?.issues?.length > 0))
                                    .slice(-20)
                                    .map(e => (
                                        <div
                                            key={e.id}
                                            className={`flex items-start gap-2 px-3 py-2 rounded-lg text-xs ${
                                                e.type === "warning"
                                                    ? "bg-yellow-500/8 border border-yellow-500/15 text-yellow-300"
                                                    : "bg-emerald-500/8 border border-emerald-500/15 text-emerald-300"
                                            }`}
                                        >
                                            {e.type === "warning"
                                                ? <AlertCircle size={11} className="shrink-0 mt-0.5" />
                                                : <CheckCircle size={11} className="shrink-0 mt-0.5" />}
                                            <span className="line-clamp-2">{e.message}</span>
                                        </div>
                                    ))}
                                {events.filter(e => e.type === "warning").length === 0 && (status === "done" || status === "analysis_done") && (
                                    <p className="text-xs text-slate-500 col-span-2">No issues detected.</p>
                                )}
                            </div>
                        </div>
                    )}

                    {/* ── Generated Test Cases panel ───────────────────────── */}
                    {totalScenarios > 0 && (
                        <div className="bg-[#121214] border border-white/5 rounded-xl overflow-hidden">
                            {/* Header */}
                            <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
                                <div className="flex items-center gap-2">
                                    <FlaskConical size={15} className="text-violet-400" />
                                    <span className="text-sm font-semibold text-white">
                                        Generated Test Cases
                                    </span>
                                    <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-400 font-semibold">
                                        {totalScenarios} scenarios
                                    </span>
                                </div>
                                <div className="flex items-center gap-2">
                                    {savedSuite ? (
                                        <div className="flex items-center gap-1.5 text-xs text-emerald-400 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                                            <CheckCircle size={12} />
                                            Saved to Test Suites
                                        </div>
                                    ) : (
                                        <button
                                            onClick={handleSaveSuite}
                                            disabled={savingSuite}
                                            className="flex items-center gap-2 px-4 py-2 bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/30 text-violet-300 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                                        >
                                            {savingSuite ? (
                                                <Loader2 size={12} className="animate-spin" />
                                            ) : (
                                                <Save size={12} />
                                            )}
                                            {savingSuite ? "Saving…" : "Save to Test Suites"}
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* Feature groups */}
                            <div className="divide-y divide-white/5">
                                {Object.entries(generatedScenarios).map(([feature, scenarios]) => (
                                    <div key={feature} className="p-4">
                                        {/* Feature label */}
                                        <div className="flex items-center gap-2 mb-3">
                                            <span className="text-sm">
                                                {AGENT_ICON_MAP[feature] || <Bot size={14} className="text-slate-400" />}
                                            </span>
                                            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                                                {feature.replace(/_/g, " ")}
                                            </span>
                                            <span className="text-xs text-slate-600">
                                                {scenarios.length} scenario{scenarios.length !== 1 ? "s" : ""}
                                            </span>
                                        </div>

                                        {/* Scenario cards */}
                                        <div className="space-y-2">
                                            {scenarios.map((sc: any) => {
                                                const isExp = expandedScenario === sc.id;
                                                const pct   = sc.total > 0 ? Math.round((sc.passed / sc.total) * 100) : 0;
                                                const allPass = sc.passed === sc.total && sc.total > 0;
                                                return (
                                                    <div
                                                        key={sc.id}
                                                        className={`border rounded-lg overflow-hidden ${
                                                            allPass
                                                                ? "border-emerald-500/20 bg-emerald-500/3"
                                                                : sc.passed > 0
                                                                ? "border-yellow-500/20 bg-yellow-500/3"
                                                                : "border-white/8 bg-[#0f0f11]"
                                                        }`}
                                                    >
                                                        {/* Row */}
                                                        <div
                                                            className="flex items-center gap-3 px-3 py-2.5 cursor-pointer hover:bg-white/5"
                                                            onClick={() => setExpandedScenario(isExp ? null : sc.id)}
                                                        >
                                                            {isExp
                                                                ? <ChevronUp size={12} className="text-slate-500 shrink-0" />
                                                                : <ChevronDown size={12} className="text-slate-500 shrink-0" />}

                                                            <ListChecks size={13} className={allPass ? "text-emerald-400" : "text-slate-500"} />

                                                            <span className="flex-1 text-xs font-medium text-white truncate">
                                                                {sc.name.replace(/^\[AUTO\]\s*/, "")}
                                                            </span>

                                                            {/* Pass rate bar */}
                                                            <div className="flex items-center gap-2 shrink-0">
                                                                <div className="w-16 h-1.5 rounded-full bg-white/10 overflow-hidden">
                                                                    <div
                                                                        className={`h-full rounded-full transition-all ${allPass ? "bg-emerald-400" : "bg-yellow-400"}`}
                                                                        style={{ width: `${pct}%` }}
                                                                    />
                                                                </div>
                                                                <span className={`text-xs font-medium ${allPass ? "text-emerald-400" : "text-yellow-400"}`}>
                                                                    {sc.passed}/{sc.total}
                                                                </span>
                                                            </div>
                                                        </div>

                                                        {/* Steps expansion */}
                                                        {isExp && sc.steps?.length > 0 && (
                                                            <div className="border-t border-white/5 px-3 pb-3 pt-2 space-y-1">
                                                                {sc.steps.map((step: any, i: number) => (
                                                                    <div key={i} className="flex items-start gap-2 text-xs">
                                                                        <span className={`mt-0.5 shrink-0 font-mono px-1.5 py-0.5 rounded text-[10px] ${
                                                                            step.action === "click"          ? "bg-blue-500/15 text-blue-400" :
                                                                            step.action === "fill"           ? "bg-orange-500/15 text-orange-400" :
                                                                            step.action === "assert_visible" ? "bg-emerald-500/15 text-emerald-400" :
                                                                            step.action === "assert_text"    ? "bg-teal-500/15 text-teal-400" :
                                                                            step.action === "navigate"       ? "bg-indigo-500/15 text-indigo-400" :
                                                                            "bg-slate-500/15 text-slate-400"
                                                                        }`}>
                                                                            {step.action}
                                                                        </span>
                                                                        <span className="text-slate-400 flex-1">
                                                                            {step.description}
                                                                        </span>
                                                                        {step.value && (
                                                                            <span className="text-slate-600 font-mono">= "{step.value}"</span>
                                                                        )}
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Footer hint */}
                            {savedSuite && (
                                <div className="px-5 py-3 border-t border-white/5 flex items-center justify-between">
                                    <span className="text-xs text-slate-500">
                                        Plan ID: <span className="font-mono text-slate-400">{savedSuite.planId}</span>
                                    </span>
                                    <a
                                        href="/test-lists"
                                        className="flex items-center gap-1.5 text-xs text-violet-400 hover:text-violet-300 transition-colors"
                                    >
                                        Open in Test Suites <ExternalLink size={11} />
                                    </a>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ── Empty state ───────────────────────────────────────── */}
                    {status === "idle" && (
                        <div className="flex-1 flex flex-col items-center justify-center py-16 text-center">
                            <div className="w-20 h-20 rounded-2xl bg-[#00D4AA]/10 border border-[#00D4AA]/20 flex items-center justify-center mb-5">
                                <Bot size={36} className="text-[#00D4AA]" />
                            </div>
                            <h2 className="text-xl font-bold text-white mb-2">Ready to Explore Any App</h2>
                            <p className="text-slate-400 max-w-md text-sm leading-relaxed">
                                Enter any URL above. AI agents will launch a visible browser, crawl every page,
                                validate the UI, detect issues, and automatically assign specialist agents —
                                one per feature — just like a QA team lead distributing work.
                            </p>
                            <div className="mt-6 flex flex-wrap justify-center gap-2">
                                {["🏠 Landing Page", "🔐 Authentication", "📊 Dashboard", "📦 Products", "📈 Reports", "⚙️ Admin"].map(f => (
                                    <span key={f} className="px-3 py-1.5 text-xs bg-white/5 border border-white/10 rounded-full text-slate-400">{f}</span>
                                ))}
                            </div>
                        </div>
                    )}

                </div>
            </main>

            <style jsx global>{`
                @keyframes scan {
                    0%   { transform: translateY(0); opacity: 1; }
                    50%  { opacity: 0.4; }
                    100% { transform: translateY(100vh); opacity: 0; }
                }
            `}</style>
        </div>
    );
}
