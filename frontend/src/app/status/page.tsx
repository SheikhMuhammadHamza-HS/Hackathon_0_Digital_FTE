"use client";

import { 
  RefreshCcw, 
  Cpu, 
  Database, 
  HardDrive,
  Loader2,
  AlertTriangle,
  CheckCircle2
} from "lucide-react";
import { useState, useEffect } from "react";
import { fetchSystemMetrics } from "@/services/api";
import { cn } from "@/lib/utils";

export default function CloudStatusPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = async (isRefresh = false) => {
    if (!isRefresh) setLoading(true);
    try {
      const metrics = await fetchSystemMetrics();
      setData(metrics.system_metrics || {});
      setError(null);
    } catch (err: any) {
      console.error("Metrics load error:", err);
      setError("Backend connection failed.");
    } finally {
      if (!isRefresh) setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
    const interval = setInterval(() => loadMetrics(true), 15000);
    return () => clearInterval(interval);
  }, []);

  const cpu = data?.cpu || { percent: 0 };
  const memory = data?.memory || { percent: 0, used: 0, total: 0 };
  const disk = data?.disk || {};
  const diskPath = Object.keys(disk)[0] || "/";
  const diskUsage = disk[diskPath] || { percent: 0, used: 0, total: 0 };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Cloud Status</h1>
          <p className="text-zinc-500 mt-1">Infrastructure Real-time Monitoring</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => loadMetrics()}
            className="p-2 hover:bg-zinc-800 rounded-md transition-colors text-zinc-400 active:scale-95"
          >
            <RefreshCcw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>
          <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-500 px-4 py-2 rounded-full border border-emerald-500/20 text-sm font-medium">
            <CheckCircle2 className="w-4 h-4" />
            Oracle VM Live
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-amber-500/10 border border-amber-500/20 text-amber-500 p-4 rounded-xl text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="p-20 flex justify-center">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
      ) : (
        <>
          {/* Usage Widgets */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <UsageCard 
              title="CPU Usage" 
              value={`${cpu.percent}%`} 
              percentage={cpu.percent} 
              icon={Cpu} 
              details={`${data?.cpu?.cores || 2} Cores @ ${data?.cpu?.frequency || 2.4}GHz`}
            />
            <UsageCard 
              title="Memory" 
              value={`${(memory.used / 1024 / 1024 / 1024).toFixed(1)} / ${(memory.total / 1024 / 1024 / 1024).toFixed(1)} GB`} 
              percentage={memory.percent} 
              icon={Database} 
              details={`Available: ${(memory.available / 1024 / 1024 / 1024).toFixed(1)} GB`}
            />
            <UsageCard 
              title="Disk" 
              value={`${(diskUsage.used / 1024 / 1024 / 1024).toFixed(1)} / ${(diskUsage.total / 1024 / 1024 / 1024).toFixed(1)} GB`} 
              percentage={diskUsage.percent} 
              icon={HardDrive} 
              details={`Mount: ${diskPath}`}
            />
          </div>

          {/* Detailed Processes / Metrics */}
          <div className="bg-[#111113] border border-zinc-800/50 rounded-xl p-6 shadow-2xl">
            <h3 className="text-xl font-bold mb-6 text-zinc-200 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
              Resource Distribution
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-4">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">System Uptime</span>
                  <span className="text-zinc-300 font-mono">24d 12h 45m</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">Load Average (1/5/15)</span>
                  <span className="text-zinc-300 font-mono">
                    {data?.load?.join(" ") || "0.05 0.12 0.08"}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">Active Processes</span>
                  <span className="text-zinc-300 font-mono">{data?.processes || 0}</span>
                </div>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-zinc-600 mb-2 uppercase tracking-widest font-bold">Network Interfaces</p>
                {data?.network && Object.entries(data.network).map(([name, net]: any) => (
                  <div key={name} className="flex justify-between items-center py-2 border-b border-zinc-800/30 last:border-0">
                    <span className="text-sm text-zinc-400">{name}</span>
                    <div className="flex gap-4 text-[10px] font-mono">
                      <span className="text-emerald-500">↑ {(net.bytes_sent / 1024 / 1024).toFixed(1)}MB</span>
                      <span className="text-indigo-500">↓ {(net.bytes_recv / 1024 / 1024).toFixed(1)}MB</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function UsageCard({ title, value, percentage, icon: Icon, details }: { title: string, value: string, percentage: number, icon: React.ElementType, details?: string }) {
  return (
    <div className="bg-[#111113] border border-zinc-800/50 rounded-xl p-6 space-y-4 hover:border-indigo-500/30 transition-all group shadow-lg overflow-hidden relative">
      <div className="absolute top-0 right-0 p-8 bg-indigo-500/5 rounded-full -mr-6 -mt-6 group-hover:bg-indigo-500/10 transition-colors" />
      <div className="flex items-center justify-between relative z-10">
        <h4 className="text-zinc-400 text-sm font-medium">{title}</h4>
        <Icon className="w-4 h-4 text-zinc-500 group-hover:text-indigo-400 transition-colors" />
      </div>
      <div className="relative z-10">
        <p className="text-3xl font-bold tracking-tight text-zinc-100">{value}</p>
        <div className="mt-4 h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
          <div 
            className="h-full bg-indigo-500 glow-purple transition-all duration-1000 ease-out" 
            style={{ width: `${Math.min(100, percentage)}%` }} 
          />
        </div>
        {details && <p className="mt-3 text-[10px] text-zinc-600 font-mono">{details}</p>}
      </div>
    </div>
  );
}
