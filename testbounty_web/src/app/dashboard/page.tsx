"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { listRuns, Run } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import {
  Plus, CheckCircle, XCircle, Clock,
  MoreVertical, ChevronRight, FileText,
  Bot, Search, Shield, Zap, Terminal, BarChart
} from "lucide-react";

export default function Dashboard() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRuns();
  }, []);

  const loadRuns = async () => {
    try {
      const data = await listRuns();
      // Sort by created_at desc
      setRuns(data.reverse());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const agents = [
    {
      name: "Code Analyst",
      description: "Deep scans your repository or live URL to understand structure and tech stack.",
      icon: <Search className="text-sky-400" size={24} />,
      color: "bg-sky-500/10 border-sky-500/20"
    },
    {
      name: "Test Architect",
      description: "Generates comprehensive PRDs and plans test coverage for frontend & backend.",
      icon: <FileText className="text-purple-400" size={24} />,
      color: "bg-purple-500/10 border-purple-500/20"
    },
    {
      name: "Execution Engine",
      description: "Writes and runs code-based tests autonomously, handling setup and teardown.",
      icon: <Terminal className="text-[#00D4AA]" size={24} />,
      color: "bg-[#00D4AA]/10 border-[#00D4AA]/20"
    },
    {
      name: "Self-Healer",
      description: "Detects failures and attempts to rewrite test code to fix broken paths.",
      icon: <Shield className="text-emerald-400" size={24} />,
      color: "bg-emerald-500/10 border-emerald-500/20"
    }
  ];

  return (
    <div className="flex min-h-screen bg-[#0E0E0E] text-slate-200 font-sans selection:bg-[#00D4AA]/30">
      <Sidebar />

      <main className="flex-1 ml-64 p-8">
        {/* Top Banner */}
        <div className="bg-[#121214] border border-white/5 rounded-2xl p-8 mb-8 relative overflow-hidden group">
          <div className="relative z-10 max-w-3xl">
            <h1 className="text-4xl font-bold text-white mb-4 tracking-tight">
              Orchestrate Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00D4AA] to-emerald-500">Quality Assurance</span>
            </h1>
            <p className="text-slate-400 mb-8 max-w-xl text-lg leading-relaxed">
              Deploy a fleet of specialized AI agents to analyze, plan, and execute end-to-end testing for your applications. Autonomous, reliable, and incredibly fast.
            </p>
            <div className="flex items-center gap-4">
              <Link href="/create">
                <button className="bg-[#00D4AA] hover:bg-[#00C099] text-black px-6 py-3 rounded-xl text-sm font-bold flex items-center gap-2 transition-all transform hover:scale-105 shadow-lg shadow-[#00D4AA]/20">
                  <Bot size={18} />
                  Start New Run
                </button>
              </Link>

              <Link href="/create">
                <button className="bg-white/5 hover:bg-white/10 border border-white/10 text-white px-6 py-3 rounded-xl text-sm font-medium transition-all hover:border-white/20">
                  Test Deployed App
                </button>
              </Link>

              <Link href="/docs">
                <button className="bg-white/5 hover:bg-white/10 border border-white/10 text-white px-6 py-3 rounded-xl text-sm font-medium transition-all hover:border-white/20">
                  View Docs
                </button>
              </Link>
            </div>
          </div>
          {/* Decorative visual */}
          <div className="absolute top-0 right-0 h-full w-1/2 bg-gradient-to-l from-emerald-900/10 to-transparent pointer-events-none"></div>
          <div className="absolute -right-20 -top-20 w-96 h-96 bg-[#00D4AA]/10 rounded-full blur-3xl pointer-events-none group-hover:bg-[#00D4AA]/15 transition-all duration-1000"></div>
        </div>

        {/* Agents Grid */}
        <div className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Active Agents</h2>
            <Link href="/agents" className="text-xs text-[#00D4AA] hover:text-white transition-colors">View All Capabilities</Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {agents.map((agent) => (
              <div key={agent.name} className={`p-4 rounded-xl border ${agent.color} bg-[#121214] hover:bg-[#1A1A1D] transition-all cursor-default`}>
                <div className="mb-3 w-10 h-10 rounded-lg bg-black/40 flex items-center justify-center">
                  {agent.icon}
                </div>
                <h3 className="text-white font-medium mb-1">{agent.name}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{agent.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* Recent Created Tests */}
          <div className="xl:col-span-2 space-y-4">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Recent Executions</h2>
            <div className="bg-[#121214] border border-white/5 rounded-xl overflow-hidden min-h-[300px] hover:border-white/10 transition-colors">
              <table className="w-full text-left text-sm">
                <thead className="bg-[#0F0F11] border-b border-white/5 text-slate-500 font-medium">
                  <tr>
                    <th className="px-6 py-4">Run Name</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Timeline</th>
                    <th className="px-6 py-4"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {runs.slice(0, 5).map((run) => (
                    <tr key={run.id} className="group hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4">
                        <Link href={`/run/${run.id}`} className="block">
                          <div className="font-medium text-white mb-1 group-hover:text-[#00D4AA] transition-colors truncate max-w-xs">
                            {run.test_name || run.api_name || "Untitled Test"}
                          </div>
                          <div className="text-xs text-slate-500 truncate max-w-xs flex items-center gap-1">
                            <Zap size={10} />
                            {run.target_url || run.project_path}
                          </div>
                        </Link>
                      </td>
                      <td className="px-6 py-4">
                        <div className={`flex items-center gap-2 px-2.5 py-1 rounded-full w-fit text-xs font-semibold ${run.status === 'completed' ? 'bg-[#00D4AA]/10 text-[#00D4AA] border border-[#00D4AA]/20' :
                          run.status === 'failed' ? 'bg-red-500/10 text-red-500 border border-red-500/20' :
                            'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                          }`}>
                          {run.status === 'completed' ? <CheckCircle size={12} /> :
                            run.status === 'failed' ? <XCircle size={12} /> : <Clock size={12} />}
                          <span className="capitalize">{run.status}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-500 font-mono text-xs">
                        {(() => {
                          try {
                            const dateStr = run.created_at || new Date().toISOString();
                            if (dateStr.includes('-') && dateStr.split('-').length === 5 && !dateStr.includes('T')) {
                              return "Just now";
                            }
                            return new Date(dateStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                          } catch {
                            return "Just now";
                          }
                        })()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link href={`/run/${run.id}`}>
                          <button className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors">
                            <ChevronRight size={16} />
                          </button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                  {runs.length === 0 && !loading && (
                    <tr>
                      <td colSpan={4} className="text-center py-16 text-slate-500">
                        <div className="flex flex-col items-center gap-2">
                          <Bot size={32} className="text-slate-700" />
                          <p>No runs detected. Start your first agent run above.</p>
                        </div>
                      </td>
                    </tr>
                  )}
                  {loading && (
                    <tr>
                      <td colSpan={4} className="text-center py-12">
                        <Clock className="animate-spin text-[#00D4AA] mx-auto" size={24} />
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Column: API Keys, Plan, etc. */}
          <div className="space-y-6">
            {/* Test Lists */}
            <div className="space-y-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Test Libraries</h2>
              <div className="bg-[#121214] border border-white/5 rounded-xl p-8 flex flex-col items-center justify-center text-center hover:border-white/10 transition-colors">
                <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center mb-4 text-slate-500">
                  <FileText size={24} />
                </div>
                <h3 className="text-white font-medium mb-1">Organize Your Suites</h3>
                <p className="text-xs text-slate-500 mb-6 max-w-[200px]">Create reusable test lists and schedule them for periodic execution.</p>
                <Link href="/test-lists" className="w-full">
                  <button className="w-full bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 px-4 py-2.5 rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-2">
                    <Plus size={14} /> Create New List
                  </button>
                </Link>
              </div>
            </div>

            {/* My Plan */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Usage</h2>
                <button className="text-[10px] font-bold text-[#00D4AA] uppercase tracking-wide border border-[#00D4AA]/30 px-2 py-0.5 rounded hover:bg-[#00D4AA]/10 transition-colors">Upgrade</button>
              </div>

              <div className="bg-[#121214] border border-white/5 rounded-xl p-6 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-20 text-[#00D4AA]">
                  <BarChart size={48} />
                </div>
                <div className="flex items-center justify-between mb-2 relative z-10">
                  <div className="text-white font-medium">Pro Plan</div>
                  <div className="text-xs text-slate-400">84% Used</div>
                </div>
                <div className="h-2 bg-slate-800 rounded-full overflow-hidden mb-2 relative z-10">
                  <div className="h-full w-[84%] bg-gradient-to-r from-[#00D4AA] to-emerald-500"></div>
                </div>
                <div className="text-xs text-slate-500 relative z-10">
                  420 / 500 Credits
                </div>
              </div>
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
