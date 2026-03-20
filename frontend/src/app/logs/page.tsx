"use client";

import { 
  ScrollText, 
  Search, 
  Filter, 
  Download,
  Info,
  AlertCircle,
  CheckCircle2,
  Loader2,
  AlertTriangle,
  RefreshCcw
} from "lucide-react";
import { useState, useEffect } from "react";
import { fetchAlerts } from "@/services/api";
import { cn } from "@/lib/utils";

export default function LogsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const loadLogs = async () => {
    setLoading(true);
    try {
      const data = await fetchAlerts();
      setLogs(data.alerts || []);
      setError(null);
    } catch (err: any) {
      console.error("Logs load error:", err);
      setError("Backend connection failed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const filteredLogs = logs.filter(log => 
    log.title?.toLowerCase().includes(search.toLowerCase()) ||
    log.description?.toLowerCase().includes(search.toLowerCase()) ||
    log.metric_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System Logs</h1>
          <p className="text-zinc-500 mt-1">Real-time alerts and monitoring history</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={loadLogs}
            className="p-2 hover:bg-zinc-800 rounded-md transition-all duration-200 text-zinc-400 hover:text-indigo-400"
          >
            <RefreshCcw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-md text-sm transition-colors border border-zinc-700/50">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 bg-[#111113] p-4 rounded-xl border border-zinc-800/50">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input 
            type="text" 
            placeholder="Search alerts..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2 pl-10 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition-all"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-400 hover:text-white transition-colors">
          <Filter className="w-4 h-4" />
          Severity
        </button>
      </div>

      {error && (
        <div className="bg-amber-500/10 border border-amber-500/20 text-amber-500 p-4 rounded-xl text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Logs Table */}
      <div className="bg-[#111113] border border-zinc-800/50 rounded-xl overflow-hidden shadow-2xl">
        {loading && logs.length === 0 ? (
          <div className="p-12 flex justify-center">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="text-zinc-500 text-xs uppercase tracking-wider border-b border-zinc-800/50 bg-zinc-900/50 font-bold">
                <th className="px-6 py-4 font-medium">Timestamp</th>
                <th className="px-6 py-4 font-medium">Severity</th>
                <th className="px-6 py-4 font-medium">Category</th>
                <th className="px-6 py-4 font-medium">Alert</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {filteredLogs.length > 0 ? (
                filteredLogs.map((log: any) => (
                  <tr key={log.id} className="hover:bg-indigo-500/5 transition-colors group">
                    <td className="px-6 py-4 text-[12px] font-mono text-zinc-500">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn(
                        "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase",
                        log.severity === "critical" ? "bg-red-500/10 text-red-500 border border-red-500/20" :
                        log.severity === "error" ? "bg-red-400/10 text-red-400 border border-red-400/20" :
                        log.severity === "warning" ? "bg-amber-500/10 text-amber-500 border border-amber-500/20" :
                        "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                      )}>
                        {log.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-zinc-300">{log.metric_name}</td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-sm text-zinc-200 font-medium">{log.title}</span>
                        <span className="text-xs text-zinc-500 group-hover:text-zinc-400 transition-colors">{log.description}</span>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-zinc-600 italic">
                    No alerts found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
