"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import {
    User, Mail, Key, Bell, Shield, Moon, Sun, Save,
    CheckCircle, AlertCircle, Loader2, Settings, Zap, Globe
} from "lucide-react";

export default function ProfilePage() {
    const [saving, setSaving] = useState(false);
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

    // Profile form state
    const [name, setName] = useState("AI Agent");
    const [email, setEmail] = useState("");
    const [apiKey, setApiKey] = useState("");
    const [showApiKey, setShowApiKey] = useState(false);

    // Preferences state
    const [darkMode, setDarkMode] = useState(true);
    const [emailNotifications, setEmailNotifications] = useState(true);
    const [slackNotifications, setSlackNotifications] = useState(false);
    const [autoRunTests, setAutoRunTests] = useState(false);

    // API Configuration
    const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
    const [testTimeout, setTestTimeout] = useState("300");

    const handleSave = async () => {
        setSaving(true);
        // Simulate save
        await new Promise(resolve => setTimeout(resolve, 1000));
        setSaving(false);
        setToast({ message: "Settings saved successfully!", type: "success" });
        setTimeout(() => setToast(null), 3000);
    };

    return (
        <div className="flex min-h-screen bg-[#0E0E0E] text-slate-200 font-sans selection:bg-[#00D4AA]/30">
            <Sidebar />

            <main className="flex-1 ml-64 p-8">
                <header className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                        <span className="text-slate-300">TestBounty</span>
                        <span>/</span>
                        <span className="text-white">Profile</span>
                    </div>
                </header>

                <div className="max-w-3xl mx-auto">
                    <div className="mb-8">
                        <h1 className="text-3xl font-bold text-white mb-2">Profile & Settings</h1>
                        <p className="text-slate-400">
                            Manage your account settings and preferences
                        </p>
                    </div>

                    {/* Profile Section */}
                    <section className="bg-[#121214] border border-white/5 rounded-xl p-6 mb-6">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2 bg-[#00D4AA]/10 rounded-lg text-[#00D4AA]">
                                <User size={20} />
                            </div>
                            <div>
                                <h2 className="text-lg font-semibold text-white">Profile Information</h2>
                                <p className="text-sm text-slate-500">Your account details</p>
                            </div>
                        </div>

                        <div className="space-y-4">
                            {/* Avatar and Name */}
                            <div className="flex items-center gap-4 pb-4 border-b border-white/5">
                                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#00D4AA] to-emerald-600 flex items-center justify-center text-2xl font-bold text-black">
                                    {name.charAt(0).toUpperCase()}
                                </div>
                                <div className="flex-1">
                                    <label className="block text-sm font-medium text-slate-300 mb-1">Display Name</label>
                                    <input
                                        type="text"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-[#00D4AA]/50"
                                    />
                                </div>
                            </div>

                            {/* Email */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">
                                    <Mail size={14} className="inline mr-2" />
                                    Email Address
                                </label>
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="your@email.com"
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50"
                                />
                                <p className="text-xs text-slate-500 mt-1">Used for notifications and alerts</p>
                            </div>
                        </div>
                    </section>

                    {/* API Configuration */}
                    <section className="bg-[#121214] border border-white/5 rounded-xl p-6 mb-6">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400">
                                <Key size={20} />
                            </div>
                            <div>
                                <h2 className="text-lg font-semibold text-white">API Configuration</h2>
                                <p className="text-sm text-slate-500">Configure your API settings</p>
                            </div>
                        </div>

                        <div className="space-y-4">
                            {/* Backend URL */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">
                                    <Globe size={14} className="inline mr-2" />
                                    Backend API URL
                                </label>
                                <input
                                    type="text"
                                    value={backendUrl}
                                    onChange={(e) => setBackendUrl(e.target.value)}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white font-mono text-sm focus:outline-none focus:border-[#00D4AA]/50"
                                />
                            </div>

                            {/* API Key */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">
                                    <Key size={14} className="inline mr-2" />
                                    LLM API Key (Optional)
                                </label>
                                <div className="relative">
                                    <input
                                        type={showApiKey ? "text" : "password"}
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        placeholder="sk-..."
                                        className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white font-mono text-sm placeholder:text-slate-600 focus:outline-none focus:border-[#00D4AA]/50 pr-20"
                                    />
                                    <button
                                        onClick={() => setShowApiKey(!showApiKey)}
                                        className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs text-slate-400 hover:text-white"
                                    >
                                        {showApiKey ? "Hide" : "Show"}
                                    </button>
                                </div>
                                <p className="text-xs text-slate-500 mt-1">Override backend API key for LLM services</p>
                            </div>

                            {/* Test Timeout */}
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-1">
                                    <Zap size={14} className="inline mr-2" />
                                    Test Timeout (seconds)
                                </label>
                                <input
                                    type="number"
                                    value={testTimeout}
                                    onChange={(e) => setTestTimeout(e.target.value)}
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-[#00D4AA]/50"
                                />
                            </div>
                        </div>
                    </section>

                    {/* Notifications */}
                    <section className="bg-[#121214] border border-white/5 rounded-xl p-6 mb-6">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2 bg-amber-500/10 rounded-lg text-amber-400">
                                <Bell size={20} />
                            </div>
                            <div>
                                <h2 className="text-lg font-semibold text-white">Notifications</h2>
                                <p className="text-sm text-slate-500">How you receive alerts</p>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <ToggleSetting
                                label="Email Notifications"
                                description="Receive test results and alerts via email"
                                enabled={emailNotifications}
                                onChange={setEmailNotifications}
                            />
                            <ToggleSetting
                                label="Slack Notifications"
                                description="Send alerts to Slack channel"
                                enabled={slackNotifications}
                                onChange={setSlackNotifications}
                            />
                        </div>
                    </section>

                    {/* Preferences */}
                    <section className="bg-[#121214] border border-white/5 rounded-xl p-6 mb-6">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400">
                                <Settings size={20} />
                            </div>
                            <div>
                                <h2 className="text-lg font-semibold text-white">Preferences</h2>
                                <p className="text-sm text-slate-500">Customize your experience</p>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <ToggleSetting
                                label="Dark Mode"
                                description="Use dark theme (default)"
                                enabled={darkMode}
                                onChange={setDarkMode}
                                icon={darkMode ? <Moon size={16} /> : <Sun size={16} />}
                            />
                            <ToggleSetting
                                label="Auto-run Tests on Schedule"
                                description="Automatically execute scheduled test suites"
                                enabled={autoRunTests}
                                onChange={setAutoRunTests}
                            />
                        </div>
                    </section>

                    {/* Plan Info */}
                    <section className="bg-[#121214] border border-white/5 rounded-xl p-6 mb-6">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2 bg-[#00D4AA]/10 rounded-lg text-[#00D4AA]">
                                <Shield size={20} />
                            </div>
                            <div>
                                <h2 className="text-lg font-semibold text-white">Current Plan</h2>
                                <p className="text-sm text-slate-500">Your subscription details</p>
                            </div>
                        </div>

                        <div className="flex items-center justify-between p-4 bg-black/40 rounded-lg border border-white/5">
                            <div>
                                <div className="flex items-center gap-2">
                                    <span className="text-lg font-semibold text-white">Free Plan</span>
                                    <span className="px-2 py-0.5 bg-slate-700 text-slate-300 text-xs rounded-full">Current</span>
                                </div>
                                <p className="text-sm text-slate-400 mt-1">
                                    Unlimited tests • Basic monitoring • Community support
                                </p>
                            </div>
                            <button className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                                Upgrade
                            </button>
                        </div>
                    </section>

                    {/* Save Button */}
                    <div className="flex justify-end">
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="bg-[#00D4AA] hover:bg-[#00C099] disabled:bg-slate-700 text-black px-6 py-3 rounded-lg text-sm font-semibold flex items-center gap-2 transition-colors"
                        >
                            {saving ? (
                                <>
                                    <Loader2 size={16} className="animate-spin" />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Save size={16} />
                                    Save Changes
                                </>
                            )}
                        </button>
                    </div>
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
        </div>
    );
}

function ToggleSetting({
    label,
    description,
    enabled,
    onChange,
    icon
}: {
    label: string;
    description: string;
    enabled: boolean;
    onChange: (value: boolean) => void;
    icon?: React.ReactNode;
}) {
    return (
        <div className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
            <div className="flex items-center gap-3">
                {icon && <span className="text-slate-400">{icon}</span>}
                <div>
                    <div className="text-sm font-medium text-white">{label}</div>
                    <div className="text-xs text-slate-500">{description}</div>
                </div>
            </div>
            <button
                onClick={() => onChange(!enabled)}
                className={`relative w-11 h-6 rounded-full transition-colors ${
                    enabled ? 'bg-[#00D4AA]' : 'bg-slate-700'
                }`}
            >
                <span
                    className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                        enabled ? 'left-6' : 'left-1'
                    }`}
                />
            </button>
        </div>
    );
}
