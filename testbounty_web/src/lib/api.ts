export interface Run {
    id: string;
    project_path: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    steps: string[];
    results?: any;
    report_path?: string;
    error?: string;
    created_at?: string;
    // New metadata, may be absent for legacy runs
    target_url?: string;
    test_name?: string;
    api_name?: string;
    auth_type?: string;
    extra_info?: string;
}

const API_BASE = 'http://localhost:8001/api';

export async function startRun(input: {
    project_path?: string;
    target_url?: string;
    test_name?: string;
    api_name?: string;
    auth_type?: string;
    extra_info?: string;
}): Promise<{ run_id: string }> {
    /* eslint-disable @typescript-eslint/no-explicit-any */
    const res = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
    });
    if (!res.ok) throw new Error('Failed to start run');
    return res.json();
}

export async function getRunStatus(runId: string): Promise<Run> {
    const res = await fetch(`${API_BASE}/run/${runId}`);
    if (!res.ok) throw new Error('Failed to get status');
    return res.json();
}

export async function listRuns(): Promise<Run[]> {
    const res = await fetch(`${API_BASE}/runs`);
    if (!res.ok) throw new Error('Failed to list runs');
    return res.json();
}

/* eslint-disable @typescript-eslint/no-explicit-any */
export async function getRunArtifact(runId: string, filename: string): Promise<any> {
    const res = await fetch(`${API_BASE}/run/${runId}/artifacts/${filename}`);
    if (!res.ok) throw new Error('Artifact not found');
    return res.json();
}

export interface ExecutionProgress {
    status: 'pending' | 'running' | 'completed' | 'error';
    current_test: string | null;
    completed: string[];
    results: Record<string, { status: string; name: string }>;
    current_screenshot: string | null;
}

export function getScreenshotUrl(runId: string, screenshotPath: string): string {
    // Extract just the filename from the path
    const filename = screenshotPath.split('/').pop() || screenshotPath;
    return `${API_BASE}/run/${runId}/screenshot/${filename}`;
}

export function getTestVideoUrl(runId: string, testId: string): string {
    return `${API_BASE}/run/${runId}/test/${testId}/video`;
}

export async function getTestCode(runId: string, testId: string): Promise<{ content: string; test_id: string }> {
    const res = await fetch(`${API_BASE}/run/${runId}/test/${testId}/code`);
    if (!res.ok) throw new Error('Code not found');
    return res.json();
}

export async function getExecutionProgress(runId: string): Promise<ExecutionProgress> {
    const res = await fetch(`${API_BASE}/run/${runId}/progress`);
    if (!res.ok) throw new Error('Failed to get progress');
    return res.json();
}

export async function deleteRun(runId: string): Promise<{ status: string; run_id: string }> {
    const res = await fetch(`${API_BASE}/run/${runId}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete run');
    return res.json();
}

export async function deleteAllRuns(): Promise<{ status: string; count: number }> {
    const res = await fetch(`${API_BASE}/runs`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete all runs');
    return res.json();
}

export function getReportDownloadUrl(runId: string): string {
    return `${API_BASE}/run/${runId}/report`;
}

// =============================================
// TEST SUITES API
// =============================================

export interface ScenarioRef {
    plan_id: string;
    scenario_id: string;
    scenario_name?: string;
    module?: string;
}

export interface TestSuite {
    id: string;
    name: string;
    description: string;
    suite_type: 'regression' | 'smoke' | 'sanity' | 'custom';
    scenario_refs: ScenarioRef[];
    created_at: string;
    last_run: string | null;
    last_run_id: string | null;
    status: 'idle' | 'running' | 'passed' | 'failed';
    pass_rate: number | null;
}

export async function listTestSuites(): Promise<TestSuite[]> {
    const res = await fetch(`${API_BASE}/test-suites`);
    if (!res.ok) throw new Error('Failed to list test suites');
    return res.json();
}

export async function createTestSuite(data: {
    name: string;
    description?: string;
    suite_type?: string;
    scenario_refs?: ScenarioRef[];
}): Promise<TestSuite> {
    const res = await fetch(`${API_BASE}/test-suites`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create test suite');
    return res.json();
}

export async function getTestSuite(suiteId: string): Promise<TestSuite> {
    const res = await fetch(`${API_BASE}/test-suites/${suiteId}`);
    if (!res.ok) throw new Error('Test suite not found');
    return res.json();
}

export async function updateTestSuite(suiteId: string, data: {
    name?: string;
    description?: string;
    suite_type?: string;
    scenario_refs?: ScenarioRef[];
}): Promise<TestSuite> {
    const res = await fetch(`${API_BASE}/test-suites/${suiteId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update test suite');
    return res.json();
}

export async function addScenariosToSuite(suiteId: string, scenario_refs: ScenarioRef[]): Promise<{ status: string; added: number; total: number }> {
    const res = await fetch(`${API_BASE}/test-suites/${suiteId}/add-scenarios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_refs }),
    });
    if (!res.ok) throw new Error('Failed to add scenarios to suite');
    return res.json();
}

export async function removeScenarioFromSuite(suiteId: string, scenarioId: string): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/test-suites/${suiteId}/scenarios/${scenarioId}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to remove scenario');
    return res.json();
}

export async function deleteTestSuite(suiteId: string): Promise<{ status: string; suite_id: string }> {
    const res = await fetch(`${API_BASE}/test-suites/${suiteId}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete test suite');
    return res.json();
}

export async function runTestSuite(suiteId: string): Promise<{ status: string; suite_id: string; run_ids: string[]; scenarios_count: number }> {
    const res = await fetch(`${API_BASE}/test-suites/${suiteId}/run`, {
        method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to run test suite');
    return res.json();
}

// =============================================
// MONITORS API
// =============================================

export interface Monitor {
    id: string;
    name: string;
    description: string;
    test_suite_id: string | null;
    target_url: string | null;
    schedule: string;
    created_at: string;
    last_run: string | null;
    next_run: string | null;
    status: 'healthy' | 'warning' | 'critical' | 'unknown';
    enabled: boolean;
    success_rate: number;
    run_history: { timestamp: string; status: string; duration: number }[];
}

export async function listMonitors(): Promise<Monitor[]> {
    const res = await fetch(`${API_BASE}/monitors`);
    if (!res.ok) throw new Error('Failed to list monitors');
    return res.json();
}

export async function createMonitor(data: {
    name: string;
    description?: string;
    test_suite_id?: string;
    target_url?: string;
    schedule?: string;
}): Promise<Monitor> {
    const res = await fetch(`${API_BASE}/monitors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create monitor');
    return res.json();
}

export async function getMonitor(monitorId: string): Promise<Monitor> {
    const res = await fetch(`${API_BASE}/monitors/${monitorId}`);
    if (!res.ok) throw new Error('Monitor not found');
    return res.json();
}

export async function updateMonitor(monitorId: string, data: {
    name?: string;
    description?: string;
    schedule?: string;
    enabled?: boolean;
}): Promise<Monitor> {
    const res = await fetch(`${API_BASE}/monitors/${monitorId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update monitor');
    return res.json();
}

export async function deleteMonitor(monitorId: string): Promise<{ status: string; monitor_id: string }> {
    const res = await fetch(`${API_BASE}/monitors/${monitorId}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete monitor');
    return res.json();
}

export async function runMonitorNow(monitorId: string): Promise<{ status: string; monitor_id: string; result: any }> {
    const res = await fetch(`${API_BASE}/monitors/${monitorId}/run`, {
        method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to run monitor');
    return res.json();
}

// =============================================
// EXPLORER & PLANNER API (Scenario Testing)
// =============================================

export interface TestPlan {
    id: string;
    url: string;
    status: 'exploring' | 'planning' | 'ready' | 'failed';
    created_at: string;
    completed_at?: string;
    app_map?: {
        base_url: string;
        total_pages: number;
        pages: any[];
        modules: Record<string, any>;
        auth_pages: string[];
    };
    test_plan?: {
        base_url: string;
        total_scenarios: number;
        modules: Record<string, {
            name: string;
            requires_auth: boolean;
            scenarios: any[];
        }>;
    };
    error?: string;
}

export interface UserRoleKT {
    role: string;
    email?: string;
    password?: string;
    description?: string;
}

export async function exploreUrl(
    url: string,
    maxPages: number = 30,
    appDescription?: string,
    userRoles?: UserRoleKT[],
    keyJourneys?: string[],
): Promise<{ explore_id: string; status: string }> {
    const body: Record<string, unknown> = { url, max_pages: maxPages };
    if (appDescription) body.app_description = appDescription;
    if (userRoles && userRoles.length > 0) body.user_roles = userRoles;
    if (keyJourneys && keyJourneys.length > 0) body.key_journeys = keyJourneys;

    const res = await fetch(`${API_BASE}/explore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('Failed to start exploration');
    return res.json();
}

export async function getPlans(): Promise<TestPlan[]> {
    const res = await fetch(`${API_BASE}/plans`);
    if (!res.ok) throw new Error('Failed to list plans');
    return res.json();
}

export async function getPlan(planId: string): Promise<TestPlan> {
    const res = await fetch(`${API_BASE}/plans/${planId}`);
    if (!res.ok) throw new Error('Plan not found');
    return res.json();
}

export async function deletePlan(planId: string): Promise<{ status: string; plan_id: string }> {
    const res = await fetch(`${API_BASE}/plans/${planId}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete plan');
    return res.json();
}

export async function cancelPlan(planId: string): Promise<{ status: string; plan_id: string }> {
    const res = await fetch(`${API_BASE}/plans/${planId}/cancel`, {
        method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to cancel plan');
    return res.json();
}

export interface TestCredentials {
    username: string;
    password: string;
}

export async function runScenarios(
    planId: string,
    scenarioIds: string[] = [],
    credentials?: TestCredentials
): Promise<{ run_id: string; status: string; scenarios_count: number }> {
    const res = await fetch(`${API_BASE}/plans/${planId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            scenario_ids: scenarioIds,
            ...(credentials ? { test_credentials: credentials } : {}),
        }),
    });
    if (!res.ok) throw new Error('Failed to run scenarios');
    return res.json();
}

export async function runModule(
    planId: string,
    moduleName: string,
    credentials?: TestCredentials
): Promise<{ run_id: string; status: string; scenarios_count: number }> {
    const res = await fetch(`${API_BASE}/plans/${planId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            module: moduleName,
            ...(credentials ? { test_credentials: credentials } : {}),
        }),
    });
    if (!res.ok) throw new Error('Failed to run module');
    return res.json();
}

// =============================================
// SCENARIO RUN VIDEO & CODE API
// =============================================

export function getScenarioVideoUrl(runId: string, scenarioId: string): string {
    return `${API_BASE}/scenario-run/${runId}/video/${scenarioId}`;
}

export function getScenarioVideoFileUrl(runId: string, filename: string): string {
    return `${API_BASE}/scenario-run/${runId}/video-file/${filename}`;
}

export async function listScenarioVideos(runId: string): Promise<{
    videos: { filename: string; scenario_id?: string; url: string; size: number }[];
}> {
    const res = await fetch(`${API_BASE}/scenario-run/${runId}/videos`);
    if (!res.ok) throw new Error('Failed to list videos');
    return res.json();
}

export async function getScenarioCode(
    runId: string,
    scenarioId: string
): Promise<{ scenario_id: string; scenario_name: string; code: string; language: string }> {
    const res = await fetch(`${API_BASE}/scenario-run/${runId}/code/${scenarioId}`);
    if (!res.ok) throw new Error('Failed to get scenario code');
    return res.json();
}

export async function getAllScenarioCode(runId: string): Promise<{
    run_id: string;
    scenarios_count: number;
    code: string;
    language: string;
}> {
    const res = await fetch(`${API_BASE}/scenario-run/${runId}/code`);
    if (!res.ok) throw new Error('Failed to get all scenario code');
    return res.json();
}

// =============================================
// KT MODE 1 — USER STORY IMPORT
// =============================================

export async function importStories(
    planId: string,
    stories: string,
    format: 'plain' | 'gherkin' | 'jira' = 'plain'
): Promise<{ status: string; scenarios_added: number; total_scenarios: number; modules_added: string[] }> {
    const res = await fetch(`${API_BASE}/plans/${planId}/import-stories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stories, format }),
    });
    if (!res.ok) throw new Error('Failed to import stories');
    return res.json();
}

// =============================================
// KT MODE 2 — DOCUMENT UPLOAD
// =============================================

export async function importDocument(
    planId: string,
    file: File
): Promise<{ status: string; filename: string; extracted_chars: number; scenarios_added: number; total_scenarios: number }> {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_BASE}/plans/${planId}/import-doc`, {
        method: 'POST',
        body: form,
    });
    if (!res.ok) throw new Error('Failed to import document');
    return res.json();
}

// =============================================
// KT MODE 3 — AI-GUIDED CHAT
// =============================================

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
}

export interface ChatReply {
    reply: string;
    next_question: string | null;
    knowledge_updated: boolean;
    suggestions: string[];
    turn: number;
}

export async function sendChatMessage(planId: string, message: string): Promise<ChatReply> {
    const res = await fetch(`${API_BASE}/plans/${planId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error('Failed to send chat message');
    return res.json();
}

export async function getChatHistory(planId: string): Promise<{ history: ChatMessage[]; opening: ChatReply | null }> {
    const res = await fetch(`${API_BASE}/plans/${planId}/chat`);
    if (!res.ok) throw new Error('Failed to get chat history');
    return res.json();
}

export async function applyChatKnowledge(planId: string): Promise<{ status: string; total_scenarios: number }> {
    const res = await fetch(`${API_BASE}/plans/${planId}/chat/apply`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to apply chat knowledge');
    return res.json();
}

// =============================================
// KT MODE 4 — SESSION RECORDING
// =============================================

export interface SessionRecord {
    id: string;
    status: 'starting' | 'recording' | 'stopping' | 'analysing' | 'ready' | 'error';
    events_count: number;
    url: string;
    created_at: string;
    stopped_at: string | null;
    error: string | null;
    recording_paused?: boolean;
    app_domain?: string;
}

export async function startSessionRecord(url: string, planId?: string): Promise<{ session_id: string; status: string; url: string }> {
    const res = await fetch(`${API_BASE}/session-record/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, plan_id: planId }),
    });
    if (!res.ok) throw new Error('Failed to start recording');
    return res.json();
}

export async function getSessionRecord(sessionId: string): Promise<SessionRecord> {
    const res = await fetch(`${API_BASE}/session-record/${sessionId}`);
    if (!res.ok) throw new Error('Session not found');
    return res.json();
}

export async function stopSessionRecord(sessionId: string): Promise<{ session_id: string; events_count: number; status: string }> {
    const res = await fetch(`${API_BASE}/session-record/${sessionId}/stop`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to stop recording');
    return res.json();
}

// Skills
export interface SkillInfo {
    file: string;
    name: string;
    domain: string;
    keyword_count: number;
}

export async function listSkills(): Promise<{ skills: SkillInfo[] }> {
    const res = await fetch(`${API_BASE}/skills`);
    if (!res.ok) throw new Error('Failed to fetch skills');
    return res.json();
}

export async function getActiveSkills(planId: string): Promise<{ plan_id: string; domain: string; active_skills: string[] }> {
    const res = await fetch(`${API_BASE}/plans/${planId}/active-skills`);
    if (!res.ok) throw new Error('Failed to fetch active skills');
    return res.json();
}

// =============================================
// MULTI-AGENT SYSTEM API
// =============================================

export interface AgentQuestion {
    id: string;
    agent_id: string;
    module: string;
    question: string;
    context: string;
    options: string[];
    answer: string | null;
    asked_at: string;
    answered_at: string;
    status: 'pending' | 'answered' | 'skipped';
}

export interface ModuleAgent {
    agent_id: string;
    module: string;
    display_name: string;
    status: 'idle' | 'exploring' | 'questioning' | 'generating' | 'ready' | 'running' | 'done' | 'failed';
    plan_id: string;
    base_url: string;
    depends_on: string | null;
    knowledge: {
        module: string;
        base_url: string;
        entry_url: string;
        page_title: string;
        purpose: string;
        key_elements: { selector: string; label: string; type: string; purpose: string }[];
        business_rules: string[];
        valid_data: Record<string, string>;
        invalid_data: Record<string, string>;
        edge_cases: string[];
        security_concerns: string[];
        qa_pairs: Record<string, string>;
    };
    scenarios_count: number;
    scenarios: any[];
    questions: AgentQuestion[];
    pending_questions_count: number;
    results: Record<string, any>;
    created_at: string;
    error: string | null;
}

export async function createPlanAgents(planId: string, modules?: string[]): Promise<{
    status: string; plan_id: string; agents_count: number; agents: ModuleAgent[];
}> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modules: modules || null }),
    });
    if (!res.ok) throw new Error('Failed to create agents');
    return res.json();
}

export async function listPlanAgents(planId: string): Promise<{
    plan_id: string; agents_count: number; agents: ModuleAgent[];
}> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents`);
    if (!res.ok) throw new Error('Failed to list agents');
    return res.json();
}

export async function getPlanAgent(planId: string, module: string): Promise<ModuleAgent> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/${module}`);
    if (!res.ok) throw new Error('Agent not found');
    return res.json();
}

export async function exploreAgentModule(planId: string, module: string): Promise<{ status: string; agent_id: string }> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/${module}/explore`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to start exploration');
    return res.json();
}

export async function answerAgentQuestion(planId: string, module: string, questionId: string, answer: string): Promise<{
    status: string; pending_questions: number; agent_status: string;
}> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/${module}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: questionId, answer }),
    });
    if (!res.ok) throw new Error('Failed to answer question');
    return res.json();
}

export async function skipAgentQuestion(planId: string, module: string, questionId: string): Promise<{
    status: string; pending_questions: number; agent_status: string;
}> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/${module}/skip`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: questionId }),
    });
    if (!res.ok) throw new Error('Failed to skip question');
    return res.json();
}

export async function generateAgentScenarios(planId: string, module: string): Promise<{
    status: string; module: string; scenarios_count: number; scenarios: any[];
}> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/${module}/generate`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to generate scenarios');
    return res.json();
}

export async function generateAllAgentScenarios(planId: string): Promise<{
    status: string; plan_id: string; results: Record<string, { status: string; count?: number; error?: string }>;
}> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/generate-all`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to generate all scenarios');
    return res.json();
}

export async function mergeAgentScenarios(planId: string): Promise<{
    status: string; plan_id: string; scenarios_added: number; total_scenarios: number;
}> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/merge`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to merge scenarios');
    return res.json();
}

export async function runAgentScenarios(planId: string, credentials?: TestCredentials): Promise<{
    run_id: string; status: string; scenarios_count: number;
}> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            ...(credentials ? { test_credentials: credentials } : {}),
        }),
    });
    if (!res.ok) throw new Error('Failed to run agent scenarios');
    return res.json();
}

export async function feedAgentKnowledge(
    planId: string,
    module: string,
    text: string,
    source: string = 'manual',
): Promise<{ status: string; module: string; extracted: any; total_rules: number; total_edge_cases: number }> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/${module}/feed-knowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, source }),
    });
    if (!res.ok) throw new Error('Failed to feed agent knowledge');
    return res.json();
}

export async function feedAllAgents(
    planId: string,
    text: string,
    source: string = 'user_story',
): Promise<{ status: string; routed_to: Array<{ module: string; display_name: string; rules_added: number; edges_added: number }> }> {
    const res = await fetch(`${API_BASE}/plans/${planId}/agents/feed-all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, source }),
    });
    if (!res.ok) throw new Error('Failed to feed agents');
    return res.json();
}

// Unified API object for easier imports
export const api = {
    // Runs
    startRun,
    getRunStatus,
    listRuns,
    getRunArtifact,
    getExecutionProgress,
    deleteRun,
    deleteAllRuns,
    getScreenshotUrl,
    getTestVideoUrl,
    getTestCode,
    getReportDownloadUrl,

    // Test Suites
    listTestSuites,
    createTestSuite,
    getTestSuite,
    updateTestSuite,
    addScenariosToSuite,
    removeScenarioFromSuite,
    deleteTestSuite,
    runTestSuite,

    // Monitors
    listMonitors,
    createMonitor,
    getMonitor,
    updateMonitor,
    deleteMonitor,
    runMonitorNow,

    // Explorer & Planner (Knowledge-aware)
    exploreUrl,
    getPlans,
    getPlan,
    deletePlan,
    cancelPlan,
    runScenarios,
    runModule,

    // KT Modes
    importStories,
    importDocument,
    sendChatMessage,
    getChatHistory,
    applyChatKnowledge,
    startSessionRecord,
    getSessionRecord,
    stopSessionRecord,

    // Skills
    listSkills,
    getActiveSkills,

    // Multi-Agent System
    createPlanAgents,
    listPlanAgents,
    getPlanAgent,
    exploreAgentModule,
    answerAgentQuestion,
    skipAgentQuestion,
    generateAgentScenarios,
    generateAllAgentScenarios,
    mergeAgentScenarios,
    runAgentScenarios,
    feedAgentKnowledge,
    feedAllAgents,

    // Autonomous Explorer
    startAutonomousSession,
    getAutonomousStatus,
    answerAutonomousQuestion,
    deleteAutonomousSession,
};

// ── Autonomous Explorer ────────────────────────────────────────────────────────

export const WS_BASE = 'ws://localhost:8001';

export async function startAutonomousSession(url: string, maxPages = 25): Promise<{ session_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/autonomous/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, max_pages: maxPages }),
    });
    if (!res.ok) throw new Error('Failed to start autonomous session');
    return res.json();
}

export async function getAutonomousStatus(sessionId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/autonomous/${sessionId}/status`);
    if (!res.ok) throw new Error('Session not found');
    return res.json();
}

export async function answerAutonomousQuestion(sessionId: string, answer: string): Promise<void> {
    await fetch(`${API_BASE}/autonomous/${sessionId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer }),
    });
}

export async function deleteAutonomousSession(sessionId: string): Promise<void> {
    await fetch(`${API_BASE}/autonomous/${sessionId}`, { method: 'DELETE' });
}

export async function getAutonomousScenarios(sessionId: string): Promise<{
    scenarios: any[];
    total: number;
    by_feature: Record<string, any[]>;
}> {
    const res = await fetch(`${API_BASE}/autonomous/${sessionId}/scenarios`);
    if (!res.ok) throw new Error('Failed to fetch scenarios');
    return res.json();
}

export async function saveAutonomousScenarios(
    sessionId: string,
    suiteName?: string,
): Promise<{ plan_id: string; suite_id: string | null; scenarios: number }> {
    const res = await fetch(`${API_BASE}/autonomous/${sessionId}/save-scenarios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suite_name: suiteName }),
    });
    if (!res.ok) throw new Error('Failed to save scenarios');
    return res.json();
}
