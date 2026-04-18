"use client";

import { useState, useEffect, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import {
    api, cancelPlan, getScenarioCode, getAllScenarioCode, listScenarioVideos,
    getScenarioVideoFileUrl, importStories, importDocument,
    sendChatMessage, getChatHistory, applyChatKnowledge,
    startSessionRecord, getSessionRecord, stopSessionRecord,
    getActiveSkills, addScenariosToSuite,
    type ChatMessage, type TestSuite, type ScenarioRef
} from "@/lib/api";
import {
    Search, Play, CheckCircle, XCircle, Clock, ChevronDown, ChevronRight,
    Loader2, Globe, FileCode, Shield, Zap, RefreshCw, Trash2, Eye,
    Video, Code, X, Download, Copy, Brain, Plus, Minus, Users,
    BookOpen, AlertCircle, Lightbulb, ChevronUp, Settings2,
    MessageSquare, Upload, FileText, Send, StopCircle,
    Circle, Mic, Paperclip, CheckSquare, FolderPlus, Layers
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface TestStep { action: string; target: string; value?: string; description: string; }
interface Scenario {
    id: string; name: string; description: string; module: string;
    type: string; priority: string; depends_on: string | null;
    steps: TestStep[]; status: string; source?: string;
}
interface Module { name: string; requires_auth: boolean; scenarios: Scenario[]; }
interface Plan {
    id: string; url: string; status: string; created_at: string; completed_at?: string;
    app_map?: any; app_knowledge?: any; test_plan?: { base_url: string; total_scenarios: number; modules: Record<string, Module>; };
    error?: string; kt_sources?: { type: string; added_at: string; scenarios_added: number }[];
    knowledge_from_cache?: boolean;
}
interface RunResult { id: string; name: string; status: string; steps_completed: string[]; error?: string; }

// KT tab types
type KtTab = "basic" | "stories" | "document" | "chat" | "record";

// ─── Component ────────────────────────────────────────────────────────────────

export default function ScenariosPage() {
    const [plans, setPlans] = useState<Plan[]>([]);
    const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
    const [expandedModules, setExpandedModules] = useState<Set<string>>(new Set());
    const [selectedScenarios, setSelectedScenarios] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(true);
    const [exploring, setExploring] = useState(false);
    const [running, setRunning] = useState(false);
    const [runResults, setRunResults] = useState<Record<string, RunResult>>({});
    const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

    // Explore form
    const [exploreUrl, setExploreUrl] = useState("");
    const [activePlanId, setActivePlanId] = useState<string | null>(null);
    const [exploringStatus, setExploringStatus] = useState("exploring");

    // KT panel
    const [showKtPanel, setShowKtPanel] = useState(false);
    const [ktTab, setKtTab] = useState<KtTab>("basic");

    // Basic KT
    const [appDescription, setAppDescription] = useState("");
    const [userRoles, setUserRoles] = useState<{ role: string; email: string; password: string }[]>([]);
    const [keyJourneys, setKeyJourneys] = useState<string[]>([""]);

    // User Stories KT
    const [storiesText, setStoriesText] = useState("");
    const [storiesFormat, setStoriesFormat] = useState<"plain" | "gherkin" | "jira">("plain");
    const [importingStories, setImportingStories] = useState(false);

    // Document KT
    const [docFile, setDocFile] = useState<File | null>(null);
    const [uploadingDoc, setUploadingDoc] = useState(false);
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Chat KT
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);
    const [chatOpening, setChatOpening] = useState<string | null>(null);
    const [applyingChat, setApplyingChat] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    // Session Recording KT
    const [recordingSessionId, setRecordingSessionId] = useState<string | null>(null);
    const [recordingStatus, setRecordingStatus] = useState<string>("idle");
    const [recordingEvents, setRecordingEvents] = useState(0);
    const [startingRecord, setStartingRecord] = useState(false);
    const [stoppingRecord, setStoppingRecord] = useState(false);

    // Active Skills
    const [activeSkills, setActiveSkills] = useState<string[]>([]);

    // Shadow Mode standalone URL
    const [recordUrl, setRecordUrl] = useState<string>("");

    // Add to Suite modal
    const [suiteModalOpen, setSuiteModalOpen] = useState(false);
    const [suiteModalScenario, setSuiteModalScenario] = useState<{id: string; name: string; module: string} | null>(null);
    const [suites, setSuites] = useState<TestSuite[]>([]);
    const [newSuiteName, setNewSuiteName] = useState("");
    const [newSuiteType, setNewSuiteType] = useState<string>("regression");
    const [addingToSuite, setAddingToSuite] = useState(false);

    // Video & Code Preview
    const [activeRunId, setActiveRunId] = useState<string | null>(null);
    const [videoModalOpen, setVideoModalOpen] = useState(false);
    const [codeModalOpen, setCodeModalOpen] = useState(false);
    const [selectedScenarioForPreview, setSelectedScenarioForPreview] = useState<Scenario | null>(null);
    const [previewCode, setPreviewCode] = useState("");
    const [previewVideos, setPreviewVideos] = useState<{ filename: string; scenario_id?: string; url: string; size: number }[]>([]);
    const [loadingPreview, setLoadingPreview] = useState(false);
    const [expandedScenarios, setExpandedScenarios] = useState<Set<string>>(new Set());

    // ── Bootstrap ─────────────────────────────────────────────────────────────

    useEffect(() => { fetchPlans(); }, []);
    useEffect(() => {
        if (toast) { const t = setTimeout(() => setToast(null), 4000); return () => clearTimeout(t); }
    }, [toast]);
    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMessages]);

    // ── Poll recording events ──────────────────────────────────────────────────
    useEffect(() => {
        if (!recordingSessionId || recordingStatus !== "recording") return;
        const iv = setInterval(async () => {
            try {
                const s = await getSessionRecord(recordingSessionId);
                setRecordingEvents(s.events_count);
                if (s.status !== "recording") { setRecordingStatus(s.status); clearInterval(iv); }
            } catch (_) {}
        }, 1500);
        return () => clearInterval(iv);
    }, [recordingSessionId, recordingStatus]);

    // ── Fetch active skills when selected plan changes ─────────────────────────
    useEffect(() => {
        if (!selectedPlan?.id) { setActiveSkills([]); return; }
        getActiveSkills(selectedPlan.id)
            .then(r => setActiveSkills(r.active_skills || []))
            .catch(() => setActiveSkills([]));
    }, [selectedPlan?.id, selectedPlan?.app_knowledge]);

    // ── Data helpers ──────────────────────────────────────────────────────────

    const fetchPlans = async () => {
        try {
            const data = await api.getPlans();
            setPlans(data);
            if (data.length > 0) {
                const ready = data.find((p: Plan) => p.status === "ready");
                if (ready && !selectedPlan) {
                    setSelectedPlan(ready);
                    if (ready.test_plan?.modules) setExpandedModules(new Set(Object.keys(ready.test_plan.modules)));
                }
            }
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    };

    const reloadPlan = async (planId: string) => {
        const fresh = await api.getPlan(planId);
        setSelectedPlan(fresh);
        setPlans(prev => prev.map(p => p.id === planId ? fresh : p));
    };

    // ── Basic KT helpers ──────────────────────────────────────────────────────

    const addUserRole = () => setUserRoles(p => [...p, { role: "", email: "", password: "" }]);
    const removeUserRole = (i: number) => setUserRoles(p => p.filter((_, x) => x !== i));
    const updateUserRole = (i: number, f: string, v: string) => setUserRoles(p => p.map((r, x) => x === i ? { ...r, [f]: v } : r));
    const addJourney = () => setKeyJourneys(p => [...p, ""]);
    const removeJourney = (i: number) => setKeyJourneys(p => p.filter((_, x) => x !== i));
    const updateJourney = (i: number, v: string) => setKeyJourneys(p => p.map((j, x) => x === i ? v : j));

    // ── Explore ───────────────────────────────────────────────────────────────

    const statusLabels: Record<string, string> = {
        exploring: "Exploring pages and forms...",
        understanding: "Building app knowledge with AI...",
        planning: "Generating context-aware test scenarios...",
        ready: "Done!", failed: "Failed",
    };

    const handleCancelExplore = async () => {
        if (!activePlanId) return;
        try { await cancelPlan(activePlanId); } catch (_) {}
        setExploring(false); setActivePlanId(null);
        setToast({ message: "Exploration cancelled.", type: "error" });
    };

    const handleExplore = async () => {
        if (!exploreUrl.trim()) { setToast({ message: "Please enter a URL", type: "error" }); return; }
        setExploring(true); setExploringStatus("exploring"); setActivePlanId(null);
        try {
            const result = await api.exploreUrl(
                exploreUrl, 30,
                appDescription || undefined,
                userRoles.filter(r => r.role).length > 0 ? userRoles.filter(r => r.role) : undefined,
                keyJourneys.filter(j => j.trim()).length > 0 ? keyJourneys.filter(j => j.trim()) : undefined,
            );
            setActivePlanId(result.explore_id);
            setToast({ message: "Exploration started — AI is learning your app...", type: "success" });
            const startTime = Date.now();
            const iv = setInterval(async () => {
                if (Date.now() - startTime > 5 * 60 * 1000) {
                    clearInterval(iv); setExploring(false); setActivePlanId(null);
                    setToast({ message: "Exploration timed out. Try a smaller site.", type: "error" }); return;
                }
                const plan = await api.getPlan(result.explore_id);
                setExploringStatus(plan.status);
                if (plan.status === "ready") {
                    clearInterval(iv);
                    setSelectedPlan(plan); setActivePlanId(null);
                    setPlans(prev => [...prev.filter(p => p.id !== plan.id), plan]);
                    if (plan.test_plan?.modules) setExpandedModules(new Set(Object.keys(plan.test_plan.modules)));
                    setExploring(false);
                    setShowKtPanel(true); // auto-open KT panel after explore
                    setToast({ message: `Found ${plan.test_plan?.total_scenarios || 0} scenarios! Enhance with KT below.`, type: "success" });
                } else if (plan.status === "failed") {
                    clearInterval(iv); setExploring(false); setActivePlanId(null);
                    setToast({ message: plan.error || "Exploration failed", type: "error" });
                }
            }, 2000);
        } catch (_) { setExploring(false); setToast({ message: "Failed to start exploration", type: "error" }); }
    };

    // ── KT Mode: User Stories ─────────────────────────────────────────────────

    const handleImportStories = async () => {
        if (!selectedPlan || !storiesText.trim()) {
            setToast({ message: "Select a plan and enter user stories", type: "error" }); return;
        }
        setImportingStories(true);
        try {
            const result = await importStories(selectedPlan.id, storiesText, storiesFormat);
            await reloadPlan(selectedPlan.id);
            setToast({ message: `Added ${result.scenarios_added} scenarios from user stories!`, type: "success" });
            setStoriesText("");
        } catch (e) { setToast({ message: "Failed to import stories", type: "error" }); }
        finally { setImportingStories(false); }
    };

    // ── KT Mode: Document Upload ──────────────────────────────────────────────

    const handleDocDrop = (e: React.DragEvent) => {
        e.preventDefault(); setDragOver(false);
        const f = e.dataTransfer.files[0];
        if (f) setDocFile(f);
    };

    const handleDocUpload = async () => {
        if (!selectedPlan || !docFile) {
            setToast({ message: "Select a plan and upload a document", type: "error" }); return;
        }
        setUploadingDoc(true);
        try {
            const result = await importDocument(selectedPlan.id, docFile);
            await reloadPlan(selectedPlan.id);
            setToast({ message: `Extracted ${result.extracted_chars.toLocaleString()} chars → added ${result.scenarios_added} scenarios!`, type: "success" });
            setDocFile(null);
        } catch (e) { setToast({ message: "Failed to import document", type: "error" }); }
        finally { setUploadingDoc(false); }
    };

    // ── KT Mode: Chat ─────────────────────────────────────────────────────────

    const openChat = async () => {
        setKtTab("chat");
        if (!selectedPlan) return;
        if (chatMessages.length === 0) {
            setChatLoading(true);
            try {
                const data = await getChatHistory(selectedPlan.id);
                if (data.history.length > 0) {
                    setChatMessages(data.history);
                } else if (data.opening) {
                    setChatOpening(data.opening.reply);
                }
            } catch (_) {}
            finally { setChatLoading(false); }
        }
    };

    const handleChatSend = async () => {
        if (!selectedPlan || !chatInput.trim() || chatLoading) return;
        const msg = chatInput.trim();
        setChatInput("");
        setChatOpening(null);
        setChatMessages(prev => [...prev, { role: "user", content: msg, timestamp: new Date().toISOString() }]);
        setChatLoading(true);
        try {
            const reply = await sendChatMessage(selectedPlan.id, msg);
            setChatMessages(prev => [...prev, { role: "assistant", content: reply.reply, timestamp: new Date().toISOString() }]);
            if (reply.knowledge_updated) {
                await reloadPlan(selectedPlan.id);
            }
        } catch (_) {}
        finally { setChatLoading(false); }
    };

    const handleApplyChat = async () => {
        if (!selectedPlan) return;
        setApplyingChat(true);
        try {
            const result = await applyChatKnowledge(selectedPlan.id);
            await reloadPlan(selectedPlan.id);
            setToast({ message: `Regenerated ${result.total_scenarios} scenarios using chat knowledge!`, type: "success" });
        } catch (_) { setToast({ message: "Failed to apply chat knowledge", type: "error" }); }
        finally { setApplyingChat(false); }
    };

    // ── KT Mode: Session Recording ────────────────────────────────────────────

    const handleStartRecord = async () => {
        const url = selectedPlan?.url || recordUrl.trim() || exploreUrl;
        if (!url) { setToast({ message: "Enter a URL to record.", type: "error" }); return; }
        setStartingRecord(true);
        try {
            const result = await startSessionRecord(url, selectedPlan?.id);
            setRecordingSessionId(result.session_id);
            setRecordingStatus("recording");
            setRecordingEvents(0);
            setToast({ message: "Browser opened — use the app normally, then click Stop.", type: "success" });
        } catch (_) { setToast({ message: "Failed to start recording. Is backend running?", type: "error" }); }
        finally { setStartingRecord(false); }
    };

    const handleStopRecord = async () => {
        if (!recordingSessionId) return;
        setStoppingRecord(true);
        try {
            const result = await stopSessionRecord(recordingSessionId);
            setRecordingStatus("ready");
            const newPlanId = (result as any).plan_id;
            if (newPlanId) {
                // Reload all plans and select the relevant one
                const updated = await api.getPlans();
                setPlans(updated);
                const target = updated.find((p: any) => p.id === newPlanId);
                if (target) setSelectedPlan(target);
            } else if (selectedPlan) {
                await reloadPlan(selectedPlan.id);
            }
            const count = (result as any).scenarios?.total_scenarios || 0;
            setToast({ message: `Recording analysed — ${count} scenarios created!`, type: "success" });
        } catch (_) { setToast({ message: "Failed to stop recording", type: "error" }); }
        finally { setStoppingRecord(false); setRecordingSessionId(null); }
    };

    // ── Add to Suite ─────────────────────────────────────────────────────────

    const openSuiteModal = async (scenario: {id: string; name: string; module: string}) => {
        setSuiteModalScenario(scenario);
        setSuiteModalOpen(true);
        try { setSuites(await api.listTestSuites()); } catch (_) {}
    };

    const handleAddToSuite = async (suiteId: string) => {
        if (!suiteModalScenario || !selectedPlan) return;
        setAddingToSuite(true);
        try {
            const ref: ScenarioRef = {
                plan_id: selectedPlan.id,
                scenario_id: suiteModalScenario.id,
                scenario_name: suiteModalScenario.name,
                module: suiteModalScenario.module,
            };
            await addScenariosToSuite(suiteId, [ref]);
            setToast({ message: `Added to suite "${suites.find(s => s.id === suiteId)?.name}"`, type: "success" });
            setSuiteModalOpen(false);
        } catch (_) { setToast({ message: "Failed to add to suite", type: "error" }); }
        finally { setAddingToSuite(false); }
    };

    const handleCreateAndAddSuite = async () => {
        if (!newSuiteName.trim() || !suiteModalScenario || !selectedPlan) return;
        setAddingToSuite(true);
        try {
            const ref: ScenarioRef = {
                plan_id: selectedPlan.id,
                scenario_id: suiteModalScenario.id,
                scenario_name: suiteModalScenario.name,
                module: suiteModalScenario.module,
            };
            const suite = await api.createTestSuite({ name: newSuiteName.trim(), suite_type: newSuiteType, scenario_refs: [ref] });
            setToast({ message: `Created suite "${suite.name}" and added scenario`, type: "success" });
            setSuiteModalOpen(false);
            setNewSuiteName("");
        } catch (_) { setToast({ message: "Failed to create suite", type: "error" }); }
        finally { setAddingToSuite(false); }
    };

    // ── Run ───────────────────────────────────────────────────────────────────

    const runSelected = async () => {
        if (!selectedPlan || selectedScenarios.size === 0) {
            setToast({ message: "Select scenarios to run", type: "error" }); return;
        }
        setRunning(true); setRunResults({});
        try {
            const result = await api.runScenarios(selectedPlan.id, Array.from(selectedScenarios));
            setActiveRunId(result.run_id);
            setToast({ message: `Running ${result.scenarios_count} scenarios...`, type: "success" });
            const iv = setInterval(async () => {
                const run = await api.getRunStatus(result.run_id);
                if (run.results) setRunResults(run.results);
                if (run.status === "completed" || run.status === "failed") {
                    clearInterval(iv); setRunning(false);
                    const passed = Object.values(run.results || {}).filter((r: any) => r.status === "passed").length;
                    const total = Object.keys(run.results || {}).length;
                    setToast({ message: `Done: ${passed}/${total} passed`, type: passed === total ? "success" : "error" });
                }
            }, 1500);
        } catch (_) { setRunning(false); setToast({ message: "Failed to run scenarios", type: "error" }); }
    };

    const runModule = async (name: string) => {
        if (!selectedPlan) return;
        setRunning(true); setRunResults({});
        try {
            const result = await api.runModule(selectedPlan.id, name);
            setActiveRunId(result.run_id);
            setToast({ message: `Running ${name}...`, type: "success" });
            const iv = setInterval(async () => {
                const run = await api.getRunStatus(result.run_id);
                if (run.results) setRunResults(run.results);
                if (run.status === "completed" || run.status === "failed") { clearInterval(iv); setRunning(false); }
            }, 1500);
        } catch (_) { setRunning(false); }
    };

    const runAll = async () => {
        if (!selectedPlan) return;
        const all = new Set<string>();
        Object.values(selectedPlan.test_plan?.modules || {}).forEach(m => m.scenarios.forEach(s => all.add(s.id)));
        setSelectedScenarios(all); setRunning(true); setRunResults({});
        try {
            const result = await api.runScenarios(selectedPlan.id, []);
            setActiveRunId(result.run_id);
            setToast({ message: `Running all ${result.scenarios_count} scenarios...`, type: "success" });
            const iv = setInterval(async () => {
                const run = await api.getRunStatus(result.run_id);
                if (run.results) setRunResults(run.results);
                if (run.status === "completed" || run.status === "failed") { clearInterval(iv); setRunning(false); }
            }, 1500);
        } catch (_) { setRunning(false); }
    };

    const deletePlan = async (planId: string) => {
        try {
            await api.deletePlan(planId);
            setPlans(prev => prev.filter(p => p.id !== planId));
            if (selectedPlan?.id === planId) setSelectedPlan(null);
            setToast({ message: "Plan deleted", type: "success" });
        } catch (_) { setToast({ message: "Failed to delete", type: "error" }); }
    };

    // ── UI helpers ────────────────────────────────────────────────────────────

    const toggleModule = (n: string) => setExpandedModules(prev => { const s = new Set(prev); s.has(n) ? s.delete(n) : s.add(n); return s; });
    const toggleScenarioExpansion = (id: string) => setExpandedScenarios(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });
    const toggleScenario = (id: string) => setSelectedScenarios(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });
    const selectAllInModule = (name: string) => {
        const m = selectedPlan?.test_plan?.modules[name]; if (!m) return;
        setSelectedScenarios(prev => { const s = new Set(prev); const all = m.scenarios.every(sc => prev.has(sc.id)); m.scenarios.forEach(sc => all ? s.delete(sc.id) : s.add(sc.id)); return s; });
    };

    const getScenarioStatus = (id: string) => runResults[id]?.status || "pending";
    const getStatusIcon = (s: string) => ({ passed: <CheckCircle size={16} className="text-emerald-400" />, failed: <XCircle size={16} className="text-red-400" />, running: <Loader2 size={16} className="text-blue-400 animate-spin" /> }[s] || <Clock size={16} className="text-slate-500" />);
    const getTypeIcon = (t: string) => ({ security: <Shield size={14} className="text-red-400" />, happy_path: <Zap size={14} className="text-emerald-400" />, error_path: <XCircle size={14} className="text-orange-400" /> }[t] || <FileCode size={14} className="text-slate-400" />);
    const getPriorityColor = (p: string) => ({ high: "text-red-400", medium: "text-yellow-400" }[p] || "text-slate-400");
    const getSourceBadge = (source?: string) => {
        if (!source || source === "auto") return null;
        const map: Record<string, { label: string; color: string }> = {
            user_stories: { label: "User Story", color: "bg-blue-500/10 text-blue-400" },
            document: { label: "Document", color: "bg-purple-500/10 text-purple-400" },
            session_recording: { label: "Recorded", color: "bg-orange-500/10 text-orange-400" },
            gherkin: { label: "Gherkin", color: "bg-cyan-500/10 text-cyan-400" },
        };
        const badge = map[source];
        return badge ? <span className={`text-xs px-2 py-0.5 rounded-full ${badge.color}`}>{badge.label}</span> : null;
    };

    const openVideoPreview = async (scenario: Scenario) => {
        if (!activeRunId) { setToast({ message: "Run tests first to see videos", type: "error" }); return; }
        setSelectedScenarioForPreview(scenario); setLoadingPreview(true); setVideoModalOpen(true);
        try { const r = await listScenarioVideos(activeRunId); setPreviewVideos(r.videos.filter((v: any) => v.scenario_id === scenario.id)); }
        catch (_) { setPreviewVideos([]); } finally { setLoadingPreview(false); }
    };

    const openCodePreview = async (scenario: Scenario) => {
        if (!activeRunId) { setToast({ message: "Run tests first to see code", type: "error" }); return; }
        setSelectedScenarioForPreview(scenario); setLoadingPreview(true); setCodeModalOpen(true);
        try { const r = await getScenarioCode(activeRunId, scenario.id); setPreviewCode(r.code); }
        catch (_) { setPreviewCode("// Failed to load code"); } finally { setLoadingPreview(false); }
    };

    const downloadAllCode = async () => {
        if (!activeRunId) return;
        try {
            const r = await getAllScenarioCode(activeRunId);
            const blob = new Blob([r.code], { type: "text/plain" });
            const url = URL.createObjectURL(blob); const a = document.createElement("a");
            a.href = url; a.download = "test_scenarios.py"; a.click(); URL.revokeObjectURL(url);
            setToast({ message: "Code downloaded!", type: "success" });
        } catch (_) { setToast({ message: "Failed", type: "error" }); }
    };

    const copyCode = async () => {
        try { await navigator.clipboard.writeText(previewCode); setToast({ message: "Copied!", type: "success" }); }
        catch (_) {}
    };

    // ── KT Tabs ───────────────────────────────────────────────────────────────

    const ktTabs: { id: KtTab; label: string; icon: React.ReactNode; desc: string }[] = [
        { id: "basic", label: "Context", icon: <BookOpen size={14} />, desc: "App description & roles" },
        { id: "stories", label: "User Stories", icon: <FileText size={14} />, desc: "Paste Jira / Gherkin" },
        { id: "document", label: "Upload Doc", icon: <Upload size={14} />, desc: "PDF, DOCX, TXT" },
        { id: "chat", label: "AI Chat", icon: <MessageSquare size={14} />, desc: "Guided KT conversation" },
        { id: "record", label: "Record Session", icon: <Mic size={14} />, desc: "Shadow mode recording" },
    ];

    // ─────────────────────────────────────────────────────────────────────────
    // RENDER
    // ─────────────────────────────────────────────────────────────────────────

    return (
        <div className="flex min-h-screen bg-[#0a0a0b]">
            <Sidebar />
            <main className="flex-1 p-8 ml-64">

                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-white">Scenario Testing</h1>
                        <p className="text-slate-400 mt-1">Explore, teach, and run AI-powered test scenarios</p>
                    </div>
                </div>

                {/* ── Explore Box ─────────────────────────────────────────── */}
                <div className="bg-[#121214] border border-white/5 rounded-xl p-6 mb-4">
                    <div className="flex items-center gap-2 mb-4">
                        <Brain size={18} className="text-[#00D4AA]" />
                        <h2 className="text-base font-semibold text-white">Explore Application</h2>
                    </div>
                    <div className="flex gap-3">
                        <input
                            type="url"
                            placeholder="https://yourapp.com"
                            value={exploreUrl}
                            onChange={e => setExploreUrl(e.target.value)}
                            onKeyDown={e => e.key === "Enter" && handleExplore()}
                            className="flex-1 px-4 py-3 bg-[#1a1a1d] border border-white/10 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:border-[#00D4AA]/50"
                        />
                        {exploring ? (
                            <div className="flex gap-2">
                                <button disabled className="px-5 py-3 bg-[#00D4AA]/60 text-black font-semibold rounded-lg flex items-center gap-2 cursor-not-allowed">
                                    <Loader2 size={16} className="animate-spin" />
                                    {statusLabels[exploringStatus] || "Processing..."}
                                </button>
                                <button onClick={handleCancelExplore} className="px-4 py-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg flex items-center gap-2 transition-colors">
                                    <X size={16} /> Cancel
                                </button>
                            </div>
                        ) : (
                            <button onClick={handleExplore} className="px-6 py-3 bg-[#00D4AA] hover:bg-[#00C099] text-black font-semibold rounded-lg transition-colors flex items-center gap-2">
                                <Globe size={16} /> Explore
                            </button>
                        )}
                    </div>
                </div>

                {/* ── Plan Selector (inline, above KT) ───────────────────── */}
                {plans.filter(p => p.status === "ready").length > 0 && (
                    <div className="mb-4 flex items-center gap-3 flex-wrap">
                        <span className="text-xs text-slate-500 shrink-0">Active plan:</span>
                        {plans.filter(p => p.status === "ready").map(plan => (
                            <div
                                key={plan.id}
                                onClick={() => {
                                    setSelectedPlan(plan);
                                    if (plan.test_plan?.modules) setExpandedModules(new Set(Object.keys(plan.test_plan.modules)));
                                    setSelectedScenarios(new Set()); setRunResults({});
                                    setChatMessages([]); setChatOpening(null);
                                }}
                                className={`px-3 py-1.5 rounded-lg border transition-colors flex items-center gap-2 cursor-pointer text-sm ${selectedPlan?.id === plan.id
                                    ? "bg-[#00D4AA]/10 border-[#00D4AA]/50 text-[#00D4AA]"
                                    : "bg-[#121214] border-white/10 text-slate-400 hover:border-white/20 hover:text-white"}`}
                            >
                                <Globe size={13} />
                                {(() => { try { return new URL(plan.url).hostname; } catch { return plan.url.slice(0, 30); } })()}
                                <span className="text-xs opacity-60">({plan.test_plan?.total_scenarios || 0})</span>
                                {selectedPlan?.id === plan.id && <CheckCircle size={13} />}
                                <button onClick={e => { e.stopPropagation(); deletePlan(plan.id); }} className="ml-1 p-0.5 hover:bg-red-500/20 rounded opacity-60 hover:opacity-100">
                                    <Trash2 size={11} className="text-red-400" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {/* ── Knowledge Transfer Panel ─────────────────────────────── */}
                <div className="bg-[#121214] border border-white/5 rounded-xl mb-8 overflow-hidden">
                    {/* Panel Toggle */}
                    <button
                        onClick={() => setShowKtPanel(!showKtPanel)}
                        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
                    >
                        <div className="flex items-center gap-3">
                            <Brain size={16} className="text-[#00D4AA]" />
                            <span className="text-sm font-semibold text-white">Knowledge Transfer (KT)</span>
                            <span className="text-xs text-slate-500">— Teach the AI about your app for smarter tests</span>
                            {selectedPlan?.kt_sources && selectedPlan.kt_sources.length > 0 && (
                                <span className="px-2 py-0.5 text-xs bg-[#00D4AA]/10 text-[#00D4AA] rounded-full">
                                    {selectedPlan.kt_sources.length} source{selectedPlan.kt_sources.length > 1 ? "s" : ""} applied
                                </span>
                            )}
                        </div>
                        {showKtPanel ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
                    </button>

                    {showKtPanel && (
                        <div className="border-t border-white/5">
                            {/* Tab bar */}
                            <div className="flex border-b border-white/5 px-4 gap-1 overflow-x-auto">
                                {ktTabs.map(tab => (
                                    <button
                                        key={tab.id}
                                        onClick={() => { setKtTab(tab.id); if (tab.id === "chat") openChat(); }}
                                        className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${ktTab === tab.id
                                            ? "border-[#00D4AA] text-[#00D4AA]"
                                            : "border-transparent text-slate-400 hover:text-slate-200"
                                        }`}
                                    >
                                        {tab.icon}
                                        {tab.label}
                                    </button>
                                ))}
                            </div>

                            {/* ── Tab: Basic Context ── */}
                            {ktTab === "basic" && (
                                <div className="p-5 space-y-5">
                                    <div className="flex items-start gap-3 p-3 rounded-lg bg-[#00D4AA]/5 border border-[#00D4AA]/15">
                                        <Lightbulb size={15} className="text-[#00D4AA] mt-0.5 shrink-0" />
                                        <p className="text-xs text-slate-400">This context is used <strong className="text-white">during exploration</strong>. Set it before clicking Explore for best results.</p>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-white mb-2">What does this app do?</label>
                                        <textarea
                                            value={appDescription}
                                            onChange={e => setAppDescription(e.target.value)}
                                            placeholder="e.g. A B2B SaaS for project management. Teams create projects, assign tasks, and manage billing. Admins manage team members."
                                            rows={3}
                                            className="w-full px-4 py-3 bg-[#1a1a1d] border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50 resize-none"
                                        />
                                    </div>
                                    <div>
                                        <div className="flex items-center justify-between mb-3">
                                            <label className="text-sm font-medium text-white flex items-center gap-2"><Users size={14} className="text-slate-400" /> User Roles & Credentials</label>
                                            <button onClick={addUserRole} className="text-xs text-[#00D4AA] hover:text-[#00C099] flex items-center gap-1"><Plus size={12} /> Add Role</button>
                                        </div>
                                        {userRoles.length === 0 && <p className="text-xs text-slate-600 italic">No roles — AI will infer them automatically.</p>}
                                        <div className="space-y-2">
                                            {userRoles.map((r, i) => (
                                                <div key={i} className="grid grid-cols-[1fr_2fr_2fr_auto] gap-2">
                                                    <input placeholder="admin / user" value={r.role} onChange={e => updateUserRole(i, "role", e.target.value)} className="px-3 py-2 bg-[#1a1a1d] border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50" />
                                                    <input type="email" placeholder="test@example.com" value={r.email} onChange={e => updateUserRole(i, "email", e.target.value)} className="px-3 py-2 bg-[#1a1a1d] border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50" />
                                                    <input type="password" placeholder="password" value={r.password} onChange={e => updateUserRole(i, "password", e.target.value)} className="px-3 py-2 bg-[#1a1a1d] border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50" />
                                                    <button onClick={() => removeUserRole(i)} className="p-2 hover:bg-red-500/10 rounded text-red-400"><Minus size={14} /></button>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="flex items-center justify-between mb-3">
                                            <label className="text-sm font-medium text-white flex items-center gap-2"><Zap size={14} className="text-slate-400" /> Key User Journeys</label>
                                            <button onClick={addJourney} className="text-xs text-[#00D4AA] hover:text-[#00C099] flex items-center gap-1"><Plus size={12} /> Add</button>
                                        </div>
                                        <div className="space-y-2">
                                            {keyJourneys.map((j, i) => (
                                                <div key={i} className="flex gap-2">
                                                    <input value={j} onChange={e => updateJourney(i, e.target.value)} placeholder={`e.g. User registers → verifies email → creates first project`} className="flex-1 px-3 py-2 bg-[#1a1a1d] border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50" />
                                                    {keyJourneys.length > 1 && <button onClick={() => removeJourney(i)} className="p-2 hover:bg-red-500/10 rounded text-red-400"><Minus size={14} /></button>}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* ── Tab: User Stories ── */}
                            {ktTab === "stories" && (
                                <div className="p-5 space-y-4">
                                    <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/15">
                                        <FileText size={15} className="text-blue-400 mt-0.5 shrink-0" />
                                        <p className="text-xs text-slate-400">Paste user stories, Jira tickets, acceptance criteria, or Gherkin scenarios. AI will convert them into test cases and <strong className="text-white">add them to the selected plan</strong>.</p>
                                    </div>
                                    <div className="flex gap-3">
                                        <label className="text-sm text-slate-400">Format:</label>
                                        {(["plain", "gherkin", "jira"] as const).map(f => (
                                            <label key={f} className="flex items-center gap-1.5 text-sm cursor-pointer">
                                                <input type="radio" name="format" value={f} checked={storiesFormat === f} onChange={() => setStoriesFormat(f)} className="text-[#00D4AA]" />
                                                <span className={storiesFormat === f ? "text-white" : "text-slate-400"}>{f.charAt(0).toUpperCase() + f.slice(1)}</span>
                                            </label>
                                        ))}
                                    </div>
                                    <textarea
                                        value={storiesText}
                                        onChange={e => setStoriesText(e.target.value)}
                                        placeholder={storiesFormat === "gherkin"
                                            ? `Feature: User Authentication\n\nScenario: Valid login\n  Given I am on the login page\n  When I enter valid credentials\n  Then I should be redirected to dashboard`
                                            : storiesFormat === "jira"
                                            ? `As a user I want to login with email and password so that I can access my dashboard\nAs an admin I want to manage user accounts so that I can control access`
                                            : `User can login with email and password\nInvalid password shows error message\nForgot password sends reset email\nAdmin can delete user accounts`
                                        }
                                        rows={10}
                                        className="w-full px-4 py-3 bg-[#1a1a1d] border border-white/10 rounded-lg text-white text-sm font-mono placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50 resize-none"
                                    />
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs text-slate-500">
                                            {selectedPlan ? `Will add to: ${new URL(selectedPlan.url).hostname}` : "Select a plan first"}
                                        </span>
                                        <button
                                            onClick={handleImportStories}
                                            disabled={importingStories || !selectedPlan || !storiesText.trim()}
                                            className="px-5 py-2.5 bg-[#00D4AA] hover:bg-[#00C099] text-black font-semibold rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                                        >
                                            {importingStories ? <><Loader2 size={14} className="animate-spin" /> Parsing...</> : <><CheckSquare size={14} /> Import Stories</>}
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* ── Tab: Document Upload ── */}
                            {ktTab === "document" && (
                                <div className="p-5 space-y-4">
                                    <div className="flex items-start gap-3 p-3 rounded-lg bg-purple-500/5 border border-purple-500/15">
                                        <Upload size={15} className="text-purple-400 mt-0.5 shrink-0" />
                                        <p className="text-xs text-slate-400">Upload a requirements document (PDF, DOCX, TXT, Confluence export). AI will extract testable requirements and generate scenarios.</p>
                                    </div>

                                    {/* Drop Zone */}
                                    <div
                                        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                                        onDragLeave={() => setDragOver(false)}
                                        onDrop={handleDocDrop}
                                        onClick={() => fileInputRef.current?.click()}
                                        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${dragOver ? "border-purple-400 bg-purple-500/5" : docFile ? "border-[#00D4AA]/40 bg-[#00D4AA]/5" : "border-white/10 hover:border-white/20"}`}
                                    >
                                        {docFile ? (
                                            <div className="flex flex-col items-center gap-2">
                                                <FileText size={32} className="text-[#00D4AA]" />
                                                <p className="text-white font-medium">{docFile.name}</p>
                                                <p className="text-sm text-slate-400">{(docFile.size / 1024).toFixed(1)} KB</p>
                                                <button onClick={e => { e.stopPropagation(); setDocFile(null); }} className="text-xs text-red-400 hover:text-red-300 mt-2">Remove</button>
                                            </div>
                                        ) : (
                                            <div className="flex flex-col items-center gap-2">
                                                <Upload size={32} className="text-slate-600" />
                                                <p className="text-white">Drag & drop or click to upload</p>
                                                <p className="text-sm text-slate-400">PDF, DOCX, TXT, HTML — max 10 MB</p>
                                            </div>
                                        )}
                                        <input ref={fileInputRef} type="file" accept=".pdf,.docx,.doc,.txt,.md,.html,.htm" className="hidden" onChange={e => e.target.files?.[0] && setDocFile(e.target.files[0])} />
                                    </div>

                                    <div className="flex items-center justify-between">
                                        <span className="text-xs text-slate-500">{selectedPlan ? `Will add to: ${new URL(selectedPlan.url).hostname}` : "Select a plan first"}</span>
                                        <button
                                            onClick={handleDocUpload}
                                            disabled={uploadingDoc || !selectedPlan || !docFile}
                                            className="px-5 py-2.5 bg-[#00D4AA] hover:bg-[#00C099] text-black font-semibold rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
                                        >
                                            {uploadingDoc ? <><Loader2 size={14} className="animate-spin" /> Parsing...</> : <><Upload size={14} /> Parse Document</>}
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* ── Tab: AI Chat ── */}
                            {ktTab === "chat" && (
                                <div className="flex flex-col h-[460px]">
                                    {/* Messages */}
                                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                                        {!selectedPlan ? (
                                            <div className="flex flex-col items-center justify-center h-full gap-4">
                                                <Brain size={32} className="text-slate-600" />
                                                <p className="text-slate-400 text-sm font-medium">Select a plan to start chatting</p>
                                                {plans.filter(p => p.status === "ready").length > 0 ? (
                                                    <div className="flex flex-wrap gap-2 justify-center">
                                                        {plans.filter(p => p.status === "ready").map(plan => (
                                                            <button
                                                                key={plan.id}
                                                                onClick={() => {
                                                                    setSelectedPlan(plan);
                                                                    if (plan.test_plan?.modules) setExpandedModules(new Set(Object.keys(plan.test_plan.modules)));
                                                                    openChat();
                                                                }}
                                                                className="px-4 py-2 bg-[#1a1a1d] border border-white/10 hover:border-[#00D4AA]/50 rounded-lg text-sm text-slate-300 hover:text-white transition-colors flex items-center gap-2"
                                                            >
                                                                <Globe size={14} className="text-[#00D4AA]" />
                                                                {(() => { try { return new URL(plan.url).hostname; } catch { return plan.url.slice(0, 30); } })()}
                                                                <span className="text-xs text-slate-500">({plan.test_plan?.total_scenarios || 0})</span>
                                                            </button>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <p className="text-slate-500 text-xs">Enter a URL above and click Explore first.</p>
                                                )}
                                            </div>
                                        ) : chatLoading && chatMessages.length === 0 ? (
                                            <div className="flex items-center justify-center h-full"><Loader2 size={24} className="text-[#00D4AA] animate-spin" /></div>
                                        ) : (
                                            <>
                                                {/* Opening message */}
                                                {chatOpening && chatMessages.length === 0 && (
                                                    <div className="flex gap-3">
                                                        <div className="w-8 h-8 rounded-full bg-[#00D4AA]/10 border border-[#00D4AA]/20 flex items-center justify-center shrink-0">
                                                            <Brain size={14} className="text-[#00D4AA]" />
                                                        </div>
                                                        <div className="flex-1 bg-[#1a1a1d] rounded-xl p-4">
                                                            <p className="text-sm text-slate-300 whitespace-pre-line leading-relaxed">{chatOpening}</p>
                                                        </div>
                                                    </div>
                                                )}
                                                {chatMessages.map((msg, i) => (
                                                    <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                                                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === "user" ? "bg-slate-700" : "bg-[#00D4AA]/10 border border-[#00D4AA]/20"}`}>
                                                            {msg.role === "user" ? <span className="text-xs text-white font-bold">U</span> : <Brain size={14} className="text-[#00D4AA]" />}
                                                        </div>
                                                        <div className={`max-w-[80%] rounded-xl p-3 ${msg.role === "user" ? "bg-[#00D4AA]/10 border border-[#00D4AA]/20" : "bg-[#1a1a1d]"}`}>
                                                            <p className="text-sm text-slate-300 whitespace-pre-line leading-relaxed">{msg.content}</p>
                                                        </div>
                                                    </div>
                                                ))}
                                                {chatLoading && (
                                                    <div className="flex gap-3">
                                                        <div className="w-8 h-8 rounded-full bg-[#00D4AA]/10 border border-[#00D4AA]/20 flex items-center justify-center">
                                                            <Brain size={14} className="text-[#00D4AA]" />
                                                        </div>
                                                        <div className="bg-[#1a1a1d] rounded-xl p-4 flex items-center gap-2">
                                                            <Loader2 size={14} className="text-[#00D4AA] animate-spin" />
                                                            <span className="text-sm text-slate-400">Thinking...</span>
                                                        </div>
                                                    </div>
                                                )}
                                                <div ref={chatEndRef} />
                                            </>
                                        )}
                                    </div>

                                    {/* Apply & Input */}
                                    {selectedPlan && (
                                        <>
                                            {chatMessages.length >= 4 && (
                                                <div className="px-4 pb-2">
                                                    <button
                                                        onClick={handleApplyChat}
                                                        disabled={applyingChat}
                                                        className="w-full py-2 bg-[#00D4AA]/10 hover:bg-[#00D4AA]/20 border border-[#00D4AA]/30 text-[#00D4AA] text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                                                    >
                                                        {applyingChat ? <><Loader2 size={14} className="animate-spin" /> Regenerating scenarios...</> : <><Zap size={14} /> Apply Knowledge → Regenerate Tests</>}
                                                    </button>
                                                </div>
                                            )}
                                            <div className="p-4 border-t border-white/5 flex gap-3">
                                                <input
                                                    value={chatInput}
                                                    onChange={e => setChatInput(e.target.value)}
                                                    onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleChatSend()}
                                                    placeholder="Tell the AI about your app..."
                                                    className="flex-1 px-4 py-2.5 bg-[#1a1a1d] border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50"
                                                />
                                                <button onClick={handleChatSend} disabled={chatLoading || !chatInput.trim()} className="px-4 py-2.5 bg-[#00D4AA] hover:bg-[#00C099] text-black rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2">
                                                    <Send size={14} />
                                                </button>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            {/* ── Tab: Session Recording ── */}
                            {ktTab === "record" && (
                                <div className="p-5 space-y-5">
                                    <div className="flex items-start gap-3 p-3 rounded-lg bg-orange-500/5 border border-orange-500/15">
                                        <Mic size={15} className="text-orange-400 mt-0.5 shrink-0" />
                                        <p className="text-xs text-slate-400">
                                            <strong className="text-white">Shadow Mode</strong> — Opens a real visible browser. Use the app normally for a few minutes, then click Stop. AI converts your actions into test scenarios automatically.
                                        </p>
                                    </div>

                                    {recordingStatus === "idle" || recordingStatus === "ready" ? (
                                        <div className="space-y-5">
                                            {recordingStatus === "ready" && (
                                                <p className="text-emerald-400 text-sm flex items-center gap-2 justify-center">
                                                    <CheckCircle size={16} /> Last session analysed successfully
                                                </p>
                                            )}

                                            {/* URL input — only shown when no plan is selected */}
                                            {!selectedPlan && (
                                                <div>
                                                    <label className="block text-xs font-medium text-slate-400 mb-1.5">URL to record</label>
                                                    <input
                                                        type="url"
                                                        value={recordUrl}
                                                        onChange={e => setRecordUrl(e.target.value)}
                                                        placeholder="https://your-app.com"
                                                        className="w-full px-3 py-2.5 bg-[#1a1a1d] border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-orange-500/50"
                                                    />
                                                    <p className="text-xs text-slate-600 mt-1">Or select a plan above to record that app</p>
                                                </div>
                                            )}

                                            {selectedPlan && (
                                                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-orange-500/8 border border-orange-500/20 text-sm">
                                                    <Globe size={13} className="text-orange-400 shrink-0" />
                                                    <span className="text-slate-300 truncate">{selectedPlan.url}</span>
                                                    <span className="text-xs text-orange-400 ml-auto shrink-0">recording target</span>
                                                </div>
                                            )}

                                            <div className="text-center pt-2">
                                                <button
                                                    onClick={handleStartRecord}
                                                    disabled={startingRecord || (!selectedPlan && !recordUrl.trim())}
                                                    className="px-8 py-3 bg-orange-500 hover:bg-orange-400 text-white font-semibold rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2 mx-auto"
                                                >
                                                    {startingRecord ? <><Loader2 size={16} className="animate-spin" /> Opening browser...</> : <><Mic size={16} /> Start Recording</>}
                                                </button>
                                                <p className="text-xs text-slate-600 mt-3">Opens a real browser — use the app, then click Stop</p>
                                            </div>
                                        </div>
                                    ) : recordingStatus === "recording" ? (
                                        <div className="text-center py-8">
                                            <div className="relative w-20 h-20 mx-auto mb-4">
                                                <div className="w-20 h-20 rounded-full bg-red-500/10 border-2 border-red-500/50 flex items-center justify-center animate-pulse">
                                                    <Circle size={20} className="text-red-400 fill-red-400" />
                                                </div>
                                            </div>
                                            <p className="text-white font-semibold mb-1">Recording in progress</p>
                                            <p className="text-slate-400 text-sm mb-2">Use the browser that just opened normally</p>
                                            <div className="inline-flex items-center gap-2 px-4 py-2 bg-red-500/10 rounded-full mb-6">
                                                <Circle size={8} className="text-red-400 fill-red-400 animate-pulse" />
                                                <span className="text-sm text-red-400 font-mono">{recordingEvents} interactions recorded</span>
                                            </div>
                                            <div className="block">
                                                <button
                                                    onClick={handleStopRecord}
                                                    disabled={stoppingRecord}
                                                    className="px-8 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/40 font-semibold rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2 mx-auto"
                                                >
                                                    {stoppingRecord ? <><Loader2 size={16} className="animate-spin" /> Analysing...</> : <><StopCircle size={16} /> Stop & Analyse</>}
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="flex items-center justify-center py-12">
                                            <Loader2 size={32} className="text-[#00D4AA] animate-spin" />
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* ── Main Content ─────────────────────────────────────────── */}
                {loading || exploring ? (
                    <div className="flex flex-col items-center justify-center py-20">
                        <Loader2 size={32} className="text-[#00D4AA] animate-spin mb-4" />
                        <p className="text-slate-400">{exploring ? (statusLabels[exploringStatus] || "Processing...") : "Loading..."}</p>
                    </div>
                ) : selectedPlan?.test_plan ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                        {/* ── Modules & Scenarios ── */}
                        <div className="lg:col-span-2 space-y-4">
                            {Object.entries(selectedPlan.test_plan.modules).map(([modName, mod]) => (
                                <div key={modName} className="bg-[#121214] border border-white/5 rounded-xl overflow-hidden">
                                    <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-white/5 transition-colors" onClick={() => toggleModule(modName)}>
                                        <div className="flex items-center gap-3">
                                            {expandedModules.has(modName) ? <ChevronDown size={18} className="text-slate-400" /> : <ChevronRight size={18} className="text-slate-400" />}
                                            <h3 className="font-semibold text-white">{mod.name} Module</h3>
                                            {mod.requires_auth && <span className="px-2 py-0.5 text-xs bg-yellow-500/10 text-yellow-400 rounded">Auth</span>}
                                            <span className="text-sm text-slate-500">{mod.scenarios.length} scenarios</span>
                                        </div>
                                        <div className="flex gap-2">
                                            <button onClick={e => { e.stopPropagation(); selectAllInModule(modName); }} className="px-2 py-1 text-xs bg-white/5 hover:bg-white/10 text-slate-300 rounded">
                                                {mod.scenarios.every(s => selectedScenarios.has(s.id)) ? "Deselect All" : "Select All"}
                                            </button>
                                            <button onClick={e => { e.stopPropagation(); runModule(modName); }} disabled={running} className="px-2 py-1 text-xs bg-[#00D4AA]/10 hover:bg-[#00D4AA]/20 text-[#00D4AA] rounded flex items-center gap-1">
                                                <Play size={10} /> Run
                                            </button>
                                        </div>
                                    </div>

                                    {expandedModules.has(modName) && (
                                        <div className="border-t border-white/5">
                                            {mod.scenarios.map(scenario => {
                                                const status = getScenarioStatus(scenario.id);
                                                const isExp = expandedScenarios.has(scenario.id);
                                                return (
                                                    <div key={scenario.id} className="border-b border-white/5 last:border-0">
                                                        <div className={`group flex items-center justify-between p-3 hover:bg-white/5 transition-colors ${selectedScenarios.has(scenario.id) ? "bg-[#00D4AA]/5" : ""}`}>
                                                            <div className="flex items-center gap-3 min-w-0">
                                                                <button onClick={() => toggleScenarioExpansion(scenario.id)} className="p-1 hover:bg-white/10 rounded shrink-0">
                                                                    {isExp ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
                                                                </button>
                                                                <input type="checkbox" checked={selectedScenarios.has(scenario.id)} onChange={() => toggleScenario(scenario.id)} className="w-4 h-4 rounded shrink-0" />
                                                                {getStatusIcon(status)}
                                                                <div className="min-w-0">
                                                                    <div className="flex items-center gap-2 flex-wrap">
                                                                        <span className="text-white font-medium text-sm">{scenario.name}</span>
                                                                        {getTypeIcon(scenario.type)}
                                                                        <span className={`text-xs ${getPriorityColor(scenario.priority)}`}>{scenario.priority}</span>
                                                                        {getSourceBadge(scenario.source)}
                                                                    </div>
                                                                    <p className="text-xs text-slate-500 truncate">{scenario.description}</p>
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-1 shrink-0 ml-2">
                                                                <span className="text-xs text-slate-600">{scenario.steps.length}s</span>
                                                                <button
                                                                    onClick={() => openSuiteModal({ id: scenario.id, name: scenario.name, module: modName })}
                                                                    className="p-1.5 hover:bg-white/10 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                                                                    title="Add to Suite"
                                                                >
                                                                    <FolderPlus size={13} className="text-purple-400" />
                                                                </button>
                                                                {activeRunId && runResults[scenario.id] && (
                                                                    <>
                                                                        <button onClick={() => openVideoPreview(scenario)} className="p-1.5 hover:bg-white/10 rounded" title="Video"><Video size={13} className="text-blue-400" /></button>
                                                                        <button onClick={() => openCodePreview(scenario)} className="p-1.5 hover:bg-white/10 rounded" title="Code"><Code size={13} className="text-emerald-400" /></button>
                                                                    </>
                                                                )}
                                                            </div>
                                                        </div>
                                                        {isExp && (
                                                            <div className="px-4 pb-4 bg-[#0a0a0b]/50">
                                                                <div className="ml-10 space-y-2 pt-2">
                                                                    {scenario.steps.map((step, idx) => (
                                                                        <div key={idx} className="flex items-start gap-3 p-2 bg-white/5 rounded">
                                                                            <span className="text-xs text-slate-500 font-mono mt-0.5 w-4 shrink-0">{idx + 1}.</span>
                                                                            <div>
                                                                                <div className="flex items-center gap-2 mb-0.5">
                                                                                    <span className="text-xs font-bold text-[#00D4AA] uppercase">{step.action}</span>
                                                                                    {step.action === "fill" && step.value && <span className="text-xs text-slate-400">→ {step.value}</span>}
                                                                                </div>
                                                                                <p className="text-sm text-slate-300">{step.description}</p>
                                                                                {step.target && !["navigate", "assert", "wait"].includes(step.action) && (
                                                                                    <p className="text-xs text-slate-600 font-mono mt-0.5">{step.target}</p>
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

                        {/* ── Right Panel ── */}
                        <div className="space-y-4">
                            {/* Run Controls */}
                            <div className="bg-[#121214] border border-white/5 rounded-xl p-5">
                                <h3 className="font-semibold text-white mb-4">Run Tests</h3>
                                <div className="space-y-3">
                                    <button onClick={runSelected} disabled={running || selectedScenarios.size === 0} className="w-full py-3 bg-[#00D4AA] hover:bg-[#00C099] text-black font-semibold rounded-lg disabled:opacity-50 flex items-center justify-center gap-2 transition-colors">
                                        {running ? <><Loader2 size={16} className="animate-spin" /> Running...</> : <><Play size={16} /> Run Selected ({selectedScenarios.size})</>}
                                    </button>
                                    <button onClick={runAll} disabled={running} className="w-full py-3 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-lg disabled:opacity-50 flex items-center justify-center gap-2 transition-colors">
                                        <Zap size={16} /> Run Full E2E
                                    </button>
                                    <button onClick={() => { setSelectedScenarios(new Set()); setRunResults({}); }} className="w-full py-3 bg-white/5 hover:bg-white/10 text-slate-400 rounded-lg flex items-center justify-center gap-2 transition-colors">
                                        <RefreshCw size={16} /> Reset
                                    </button>
                                </div>
                            </div>

                            {/* Results */}
                            {Object.keys(runResults).length > 0 && (
                                <div className="bg-[#121214] border border-white/5 rounded-xl p-5">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="font-semibold text-white">Results</h3>
                                        {activeRunId && (
                                            <button onClick={downloadAllCode} className="px-2 py-1 text-xs bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 rounded flex items-center gap-1">
                                                <Download size={10} /> Code
                                            </button>
                                        )}
                                    </div>
                                    <div className="grid grid-cols-3 gap-3 mb-3">
                                        <div className="text-center p-3 bg-emerald-500/5 rounded-lg">
                                            <div className="text-xl font-bold text-emerald-400">{Object.values(runResults).filter((r: any) => r.status === "passed").length}</div>
                                            <div className="text-xs text-slate-500">Passed</div>
                                        </div>
                                        <div className="text-center p-3 bg-red-500/5 rounded-lg">
                                            <div className="text-xl font-bold text-red-400">{Object.values(runResults).filter((r: any) => r.status === "failed").length}</div>
                                            <div className="text-xs text-slate-500">Failed</div>
                                        </div>
                                        <div className="text-center p-3 bg-white/5 rounded-lg">
                                            <div className="text-xl font-bold text-slate-400">{Object.values(runResults).filter((r: any) => r.status === "running").length}</div>
                                            <div className="text-xs text-slate-500">Running</div>
                                        </div>
                                    </div>
                                    {Object.values(runResults).filter((r: any) => r.status === "failed").length > 0 && (
                                        <div className="mt-3 pt-3 border-t border-white/5 space-y-2">
                                            {Object.values(runResults).filter((r: any) => r.status === "failed").map((r: any) => (
                                                <div key={r.id} className="text-xs bg-red-500/10 p-2 rounded">
                                                    <div className="text-white">{r.name}</div>
                                                    <div className="text-red-400">{r.error}</div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* App Map */}
                            {selectedPlan.app_map && (
                                <div className="bg-[#121214] border border-white/5 rounded-xl p-5">
                                    <h3 className="font-semibold text-white mb-3">App Map</h3>
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between"><span className="text-slate-400">Pages</span><span className="text-white">{selectedPlan.app_map.total_pages}</span></div>
                                        <div className="flex justify-between"><span className="text-slate-400">Auth Pages</span><span className="text-white">{selectedPlan.app_map.auth_pages?.length || 0}</span></div>
                                        <div className="flex justify-between"><span className="text-slate-400">Modules</span><span className="text-white">{Object.keys(selectedPlan.test_plan?.modules || {}).length}</span></div>
                                    </div>
                                </div>
                            )}

                            {/* KT Sources */}
                            {selectedPlan.kt_sources && selectedPlan.kt_sources.length > 0 && (
                                <div className="bg-[#121214] border border-[#00D4AA]/15 rounded-xl p-5">
                                    <h3 className="font-semibold text-white mb-3 flex items-center gap-2"><Brain size={16} className="text-[#00D4AA]" /> Knowledge Sources</h3>
                                    <div className="space-y-2">
                                        {selectedPlan.kt_sources.map((src, i) => (
                                            <div key={i} className="flex items-center justify-between text-sm">
                                                <span className="text-slate-400 capitalize">{src.type.replace("_", " ")}</span>
                                                <span className="text-[#00D4AA]">+{src.scenarios_added} scenarios</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* App Knowledge */}
                            {selectedPlan.app_knowledge && (
                                <div className="bg-[#121214] border border-[#00D4AA]/15 rounded-xl p-5">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="font-semibold text-white flex items-center gap-2">
                                            <Brain size={16} className="text-[#00D4AA]" /> App Knowledge
                                            {(selectedPlan as any).knowledge_from_cache && (
                                                <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">cached</span>
                                            )}
                                        </h3>
                                        <span className={`text-xs px-2 py-0.5 rounded-full ${selectedPlan.app_knowledge.confidence === "high" ? "bg-emerald-500/10 text-emerald-400" : selectedPlan.app_knowledge.confidence === "medium" ? "bg-yellow-500/10 text-yellow-400" : "bg-slate-700 text-slate-400"}`}>
                                            {selectedPlan.app_knowledge.confidence}
                                        </span>
                                    </div>
                                    <span className="text-xs px-3 py-1 rounded-full bg-[#00D4AA]/10 text-[#00D4AA] border border-[#00D4AA]/20">
                                        {selectedPlan.app_knowledge.domain?.replace(/-/g, " ")}
                                    </span>
                                    {selectedPlan.app_knowledge.app_description && (
                                        <p className="text-xs text-slate-400 mt-3 leading-relaxed">{selectedPlan.app_knowledge.app_description}</p>
                                    )}
                                    {selectedPlan.app_knowledge.user_roles?.length > 0 && (
                                        <div className="mt-3">
                                            <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Roles</p>
                                            <div className="flex flex-wrap gap-1">
                                                {selectedPlan.app_knowledge.user_roles.map((r: any, i: number) => (
                                                    <span key={i} className="text-xs px-2 py-0.5 bg-white/5 border border-white/10 rounded-full text-slate-300">{r.role || r}</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    {selectedPlan.app_knowledge.business_rules?.length > 0 && (
                                        <div className="mt-3">
                                            <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Business Rules</p>
                                            <ul className="space-y-1">
                                                {selectedPlan.app_knowledge.business_rules.slice(0, 4).map((rule: string, i: number) => (
                                                    <li key={i} className="text-xs text-slate-500 flex items-start gap-1.5"><span className="text-[#00D4AA] shrink-0">›</span>{rule}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    {selectedPlan.app_knowledge.api_spec && (
                                        <div className="mt-3 pt-3 border-t border-white/5 text-xs text-emerald-400 flex items-center gap-1.5">
                                            <CheckCircle size={11} /> OpenAPI detected ({selectedPlan.app_knowledge.api_spec.endpoints?.length || 0} endpoints)
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Active Skills */}
                            {activeSkills.length > 0 && (
                                <div className="bg-[#121214] border border-purple-500/15 rounded-xl p-5">
                                    <h3 className="font-semibold text-white flex items-center gap-2 mb-3">
                                        <Zap size={15} className="text-purple-400" /> Active Skills
                                        <span className="text-xs text-slate-500 font-normal ml-auto">domain expertise injected</span>
                                    </h3>
                                    <div className="flex flex-col gap-2">
                                        {activeSkills.map((skill, i) => (
                                            <div key={i} className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg bg-purple-500/8 border border-purple-500/20 text-purple-300">
                                                <CheckCircle size={11} className="text-purple-400 shrink-0" />
                                                {skill}
                                            </div>
                                        ))}
                                    </div>
                                    <p className="text-xs text-slate-600 mt-3 leading-relaxed">
                                        These skill files add domain-specific test patterns to every AI generation for this app.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-20 text-center">
                        <Globe size={48} className="text-slate-600 mb-4" />
                        <h3 className="text-xl font-semibold text-white mb-2">No Applications Explored</h3>
                        <p className="text-slate-400">Enter a URL above and click Explore to generate test scenarios</p>
                    </div>
                )}

                {/* Toast */}
                {toast && (
                    <div className={`fixed bottom-6 right-6 px-5 py-3 rounded-lg shadow-xl flex items-center gap-2 z-50 ${toast.type === "success" ? "bg-emerald-600" : "bg-red-600"} text-white`}>
                        {toast.type === "success" ? <CheckCircle size={16} /> : <XCircle size={16} />}
                        {toast.message}
                    </div>
                )}

                {/* Add to Suite Modal */}
                {suiteModalOpen && suiteModalScenario && (
                    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setSuiteModalOpen(false)}>
                        <div className="bg-[#121214] border border-white/10 rounded-xl w-full max-w-md" onClick={e => e.stopPropagation()}>
                            <div className="flex items-center justify-between p-4 border-b border-white/5">
                                <div className="flex items-center gap-2">
                                    <FolderPlus size={16} className="text-purple-400" />
                                    <h3 className="font-semibold text-white">Add to Suite</h3>
                                </div>
                                <button onClick={() => setSuiteModalOpen(false)} className="p-1.5 hover:bg-white/10 rounded"><X size={16} className="text-slate-400" /></button>
                            </div>
                            <div className="p-4 space-y-4">
                                <p className="text-xs text-slate-400">
                                    Adding <span className="text-white font-medium">{suiteModalScenario.name}</span> to a regression suite
                                </p>

                                {/* Existing suites */}
                                {suites.length > 0 && (
                                    <div>
                                        <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Add to existing suite</p>
                                        <div className="space-y-1.5 max-h-48 overflow-y-auto">
                                            {suites.map(suite => (
                                                <button
                                                    key={suite.id}
                                                    onClick={() => handleAddToSuite(suite.id)}
                                                    disabled={addingToSuite}
                                                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition-colors disabled:opacity-50"
                                                >
                                                    <div className="flex items-center gap-2 min-w-0">
                                                        <Layers size={13} className="text-purple-400 shrink-0" />
                                                        <span className="text-sm text-white truncate">{suite.name}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2 shrink-0">
                                                        <span className={`text-xs px-1.5 py-0.5 rounded ${suite.suite_type === 'smoke' ? 'bg-orange-500/15 text-orange-400' : suite.suite_type === 'sanity' ? 'bg-blue-500/15 text-blue-400' : 'bg-purple-500/15 text-purple-400'}`}>
                                                            {suite.suite_type}
                                                        </span>
                                                        <span className="text-xs text-slate-500">{suite.scenario_refs?.length || 0} scenarios</span>
                                                    </div>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Create new suite */}
                                <div className="pt-2 border-t border-white/5">
                                    <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Or create new suite</p>
                                    <input
                                        value={newSuiteName}
                                        onChange={e => setNewSuiteName(e.target.value)}
                                        placeholder="Suite name (e.g. Login Regression)"
                                        className="w-full px-3 py-2 bg-[#1a1a1d] border border-white/10 rounded-lg text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-purple-500/50 mb-2"
                                    />
                                    <div className="flex gap-2 mb-3">
                                        {(["regression", "smoke", "sanity"] as const).map(t => (
                                            <button key={t} onClick={() => setNewSuiteType(t)}
                                                className={`flex-1 py-1.5 text-xs rounded-lg border transition-colors ${newSuiteType === t ? 'bg-purple-500/20 border-purple-500/40 text-purple-300' : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10'}`}>
                                                {t}
                                            </button>
                                        ))}
                                    </div>
                                    <button
                                        onClick={handleCreateAndAddSuite}
                                        disabled={!newSuiteName.trim() || addingToSuite}
                                        className="w-full py-2 bg-purple-500 hover:bg-purple-400 text-white font-medium rounded-lg text-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                                    >
                                        {addingToSuite ? <><Loader2 size={14} className="animate-spin" /> Creating...</> : <><Plus size={14} /> Create Suite & Add</>}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Video Modal */}
                {videoModalOpen && (
                    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setVideoModalOpen(false)}>
                        <div className="bg-[#121214] border border-white/10 rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden" onClick={e => e.stopPropagation()}>
                            <div className="flex items-center justify-between p-4 border-b border-white/5">
                                <div className="flex items-center gap-3"><Video size={18} className="text-blue-400" /><h3 className="font-semibold text-white">Video — {selectedScenarioForPreview?.name}</h3></div>
                                <button onClick={() => setVideoModalOpen(false)} className="p-2 hover:bg-white/10 rounded-lg"><X size={18} className="text-slate-400" /></button>
                            </div>
                            <div className="p-6">
                                {loadingPreview ? <div className="flex items-center justify-center py-12"><Loader2 size={32} className="text-[#00D4AA] animate-spin" /></div>
                                    : previewVideos.length > 0 ? previewVideos.map(v => (
                                        <div key={v.filename} className="rounded-lg overflow-hidden bg-black">
                                            <video controls className="w-full" src={activeRunId ? getScenarioVideoFileUrl(activeRunId, v.filename) : ""} />
                                            <div className="p-2 bg-[#1a1a1d] flex justify-between text-xs text-slate-400">
                                                <span>{v.filename}</span><span>{(v.size / 1024 / 1024).toFixed(2)} MB</span>
                                            </div>
                                        </div>
                                    )) : <div className="text-center py-12 text-slate-400"><Video size={40} className="mx-auto mb-3 text-slate-600" />No videos available</div>
                                }
                            </div>
                        </div>
                    </div>
                )}

                {/* Code Modal */}
                {codeModalOpen && (
                    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setCodeModalOpen(false)}>
                        <div className="bg-[#121214] border border-white/10 rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
                            <div className="flex items-center justify-between p-4 border-b border-white/5">
                                <div className="flex items-center gap-3"><Code size={18} className="text-emerald-400" /><h3 className="font-semibold text-white">Code — {selectedScenarioForPreview?.name}</h3></div>
                                <div className="flex gap-2">
                                    <button onClick={copyCode} className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 text-slate-300 rounded flex items-center gap-1"><Copy size={11} /> Copy</button>
                                    <button onClick={() => setCodeModalOpen(false)} className="p-2 hover:bg-white/10 rounded-lg"><X size={18} className="text-slate-400" /></button>
                                </div>
                            </div>
                            <div className="flex-1 overflow-auto p-4">
                                {loadingPreview ? <div className="flex items-center justify-center py-12"><Loader2 size={32} className="text-[#00D4AA] animate-spin" /></div>
                                    : <pre className="bg-[#0a0a0b] p-4 rounded-lg text-sm text-slate-300 font-mono overflow-x-auto"><code>{previewCode}</code></pre>
                                }
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
