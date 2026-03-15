"use client";

import { 
  RefreshCcw, 
  Cpu, 
  Database, 
  HardDrive
} from "lucide-react";

interface UsageCardProps {
  title: string;
  value: string;
  percentage: number;
  icon: React.ElementType;
}

const processes = [
  { name: "cloud-orchestrator", status: "online", cpu: "0.1%", memory: "45 MB", restarts: 0 },
  { name: "health-monitor", status: "online", cpu: "0.0%", memory: "38 MB", restarts: 0 },
  { name: "sync-manager", status: "online", cpu: "0.0%", memory: "41 MB", restarts: 0 },
];

export default function CloudStatusPage() {
  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Cloud Status</h1>
          <p className="text-zinc-500 mt-1">Oracle VM: 80.225.222.19</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="p-2 hover:bg-zinc-800 rounded-md transition-colors text-zinc-400">
            <RefreshCcw className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-500 px-4 py-2 rounded-full border border-emerald-500/20 text-sm font-medium">
            <CheckCircleIcon className="w-4 h-4" />
            All Online
          </div>
        </div>
      </div>

      {/* Usage Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <UsageCard 
          title="CPU Usage" 
          value="12%" 
          percentage={12} 
          icon={Cpu} 
        />
        <UsageCard 
          title="Memory" 
          value="680/1024 MB" 
          percentage={66} 
          icon={Database} 
        />
        <UsageCard 
          title="Disk" 
          value="4.2/50 GB" 
          percentage={8} 
          icon={HardDrive} 
        />
      </div>

      {/* PM2 Processes */}
      <div className="bg-[#111113] border border-zinc-800/50 rounded-xl p-6">
        <h3 className="text-xl font-bold mb-6">PM2 Processes</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-zinc-500 text-xs uppercase tracking-wider border-b border-zinc-800/50">
                <th className="pb-4 font-medium">Name</th>
                <th className="pb-4 font-medium">Status</th>
                <th className="pb-4 font-medium">CPU</th>
                <th className="pb-4 font-medium">Memory</th>
                <th className="pb-4 font-medium">Restarts</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {processes.map((proc) => (
                <tr key={proc.name} className="text-sm">
                  <td className="py-4 font-medium text-zinc-300">{proc.name}</td>
                  <td className="py-4">
                    <span className="inline-flex items-center gap-1.5 bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded text-[10px] font-bold uppercase">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      {proc.status}
                    </span>
                  </td>
                  <td className="py-4 text-zinc-400">{proc.cpu}</td>
                  <td className="py-4 text-zinc-400">{proc.memory}</td>
                  <td className="py-4 text-zinc-400">{proc.restarts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function UsageCard({ title, value, percentage, icon: Icon }: { title: string, value: string, percentage: number, icon: React.ElementType }) {
  return (
    <div className="bg-[#111113] border border-zinc-800/50 rounded-xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-zinc-400 text-sm font-medium">{title}</h4>
        <Icon className="w-4 h-4 text-zinc-500" />
      </div>
      <div>
        <p className="text-3xl font-bold tracking-tight">{value}</p>
        <div className="mt-4 h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
          <div 
            className="h-full bg-indigo-500 glow-purple transition-all duration-500" 
            style={{ width: `${percentage}%` }} 
          />
        </div>
      </div>
    </div>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg 
      className={className} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    >
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}
