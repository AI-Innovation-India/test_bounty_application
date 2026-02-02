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

const API_BASE = 'http://localhost:8000/api';

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

export interface TestSuite {
    id: string;
    name: string;
    description: string;
    tests: string[];
    schedule: string | null;
    created_at: string;
    last_run: string | null;
    status: 'idle' | 'running' | 'passed' | 'failed';
}

export async function listTestSuites(): Promise<TestSuite[]> {
    const res = await fetch(`${API_BASE}/test-suites`);
    if (!res.ok) throw new Error('Failed to list test suites');
    return res.json();
}

export async function createTestSuite(data: {
    name: string;
    description?: string;
    tests?: string[];
    schedule?: string;
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
    tests?: string[];
    schedule?: string;
}): Promise<TestSuite> {
    const res = await fetch(`${API_BASE}/test-suites/${suiteId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update test suite');
    return res.json();
}

export async function deleteTestSuite(suiteId: string): Promise<{ status: string; suite_id: string }> {
    const res = await fetch(`${API_BASE}/test-suites/${suiteId}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete test suite');
    return res.json();
}

export async function runTestSuite(suiteId: string): Promise<{ status: string; suite_id: string; tests_count: number }> {
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
