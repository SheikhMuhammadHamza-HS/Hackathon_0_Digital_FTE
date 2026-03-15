"use client";

import { 
  ArrowUpRight, 
  ArrowDownRight, 
  FileText,
  DollarSign,
  Briefcase,
  ExternalLink,
  Loader2,
  AlertTriangle,
  RefreshCcw,
  CheckCircle2
} from "lucide-react";
import { ActivityChart } from "@/components/activity-chart";
import { useState, useEffect } from "react";
import { fetchSubscriptionAudit, fetchBottlenecks } from "@/services/api";
import { cn } from "@/lib/utils";

interface FinanceCardProps {
  title: string;
  value: string;
  change: string;
  trend: "up" | "down";
}

export default function AccountingPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAccountingData = async () => {
    setLoading(true);
    try {
      const audit = await fetchSubscriptionAudit();
      setData(audit);
      setError(null);
    } catch (err: any) {
      console.error("Accounting load error:", err);
      setError("Backend connection failed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAccountingData();
  }, []);

  const totalCost = data?.total_monthly_cost || 0;
  const potentialSavings = data?.potential_savings || 0;
  const subscriptions = data?.subscriptions || [];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight glow-text-purple">Financial Audit</h1>
          <p className="text-zinc-500 mt-1">SaaS Subscriptions & Cost Analysis</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={loadAccountingData}
            className="p-2 hover:bg-zinc-800 rounded-md transition-colors text-zinc-400"
          >
            <RefreshCcw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>
          <div className="flex items-center gap-2 bg-blue-500/10 text-blue-400 px-4 py-2 rounded-full border border-blue-500/20 text-sm font-medium">
            <CheckCircle2 className="w-4 h-4" /> AI Auditor Active
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-amber-500/10 border border-amber-500/20 text-amber-500 p-4 rounded-xl text-sm flex items-center gap-2 font-medium">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="p-20 flex justify-center">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FinanceCard title="Monthly Committed Cost" value={`$${totalCost.toLocaleString()}`} change="+2.4%" trend="up" />
            <FinanceCard title="Potential Savings" value={`$${potentialSavings.toLocaleString()}`} change="7 Actionable" trend="down" />
            <FinanceCard title="Audit Accuracy" value="99.8%" change="+0.1%" trend="up" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 bg-[#111113] border border-zinc-800/50 rounded-2xl p-6 shadow-2xl overflow-hidden relative">
              <div className="absolute top-0 right-0 p-12 bg-indigo-500/5 rounded-full -mr-8 -mt-8" />
              <div className="flex items-center justify-between mb-8 relative z-10">
                <h3 className="font-bold flex items-center gap-2 text-zinc-200 uppercase tracking-widest text-xs">
                  <DollarSign className="w-4 h-4 text-emerald-400" /> Subscription Burn Rate
                </h3>
              </div>
              <div className="relative z-10">
                <ActivityChart />
              </div>
            </div>

            <div className="bg-[#111113] border border-zinc-800/50 rounded-2xl overflow-hidden shadow-2xl flex flex-col">
              <div className="p-6 border-b border-zinc-800/50 bg-zinc-900/30">
                <h3 className="font-bold flex items-center gap-2 text-sm text-zinc-200">
                  <FileText className="w-4 h-4 text-indigo-400" /> Active Subscriptions
                </h3>
              </div>
              <div className="divide-y divide-zinc-800/50 flex-1 overflow-y-auto max-h-[400px]">
                {subscriptions.map((sub: any, idx: number) => (
                  <div key={idx} className="p-4 hover:bg-indigo-500/5 transition-colors cursor-pointer group">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-mono text-zinc-500 uppercase">{sub.billing_cycle || "MONTHLY"}</span>
                      <span className={cn(
                        "text-[9px] font-bold px-1.5 py-0.5 rounded uppercase",
                        sub.usage === "high" ? "bg-emerald-500/10 text-emerald-400" :
                        sub.usage === "low" ? "bg-red-500/10 text-red-400" :
                        "bg-amber-500/10 text-amber-400"
                      )}>
                        {sub.usage} USAGE
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-bold text-zinc-100 group-hover:text-indigo-400 transition-colors">
                        {sub.service}
                      </h4>
                      <span className="text-sm font-mono font-bold text-zinc-200">${sub.cost}</span>
                    </div>
                    {sub.recommendation && (
                       <p className="text-[10px] text-zinc-500 mt-2 italic">“{sub.recommendation}”</p>
                    )}
                  </div>
                ))}
                {subscriptions.length === 0 && (
                  <div className="p-12 text-center text-zinc-600 italic text-sm">
                    No active subscriptions detected
                  </div>
                )}
              </div>
              <div className="p-4 bg-zinc-900/50 border-t border-zinc-800/50">
                <button className="w-full py-2 text-xs font-bold text-zinc-400 hover:text-white flex items-center justify-center gap-2 transition-colors">
                  View Full Audit in Odoo <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function FinanceCard({ title, value, change, trend }: FinanceCardProps) {
  return (
    <div className="bg-[#111113] border border-zinc-800/50 rounded-2xl p-6 hover:border-indigo-500/30 transition-all shadow-xl relative overflow-hidden group">
      <div className="absolute top-0 right-0 p-8 bg-zinc-800/20 rounded-full -mr-4 -mt-4 transition-colors group-hover:bg-indigo-500/10" />
      <p className="text-sm font-semibold text-zinc-500 uppercase tracking-wider relative z-10">{title}</p>
      <div className="flex items-end justify-between mt-4 relative z-10">
        <h3 className="text-3xl font-bold tracking-tight text-white font-mono">{value}</h3>
        <div className={cn(
          "flex items-center gap-1 text-[10px] font-black px-2 py-1 rounded",
          trend === 'up' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
        )}>
          {trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
          {change}
        </div>
      </div>
    </div>
  );
}
