"use client";

import { 
  ArrowUpRight, 
  ArrowDownRight, 
  FileText,
  DollarSign,
  Briefcase,
  ExternalLink
} from "lucide-react";
import { ActivityChart } from "../../components/activity-chart";

interface FinanceCardProps {
  title: string;
  value: string;
  change: string;
  trend: "up" | "down";
}

const invoices = [
  { id: "INV/2026/004", client: "Nexus Labs", amount: "$3,400.00", status: "Paid", date: "Mar 12" },
  { id: "APR/2026/012", client: "Core Systems", amount: "$1,850.00", status: "Pending", date: "Mar 14" },
  { id: "INV/2026/002", client: "SkyNet Org", amount: "$5,100.00", status: "Open", date: "Mar 10" },
];

export default function AccountingPage() {
  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Accounting</h1>
          <p className="text-zinc-500 mt-1">Odoo Integration: Invoices and Financial Reports</p>
        </div>
        <div className="flex items-center gap-2 bg-blue-500/10 text-blue-400 px-4 py-2 rounded-full border border-blue-500/20 text-sm font-medium">
          <Briefcase className="w-4 h-4" /> Odoo: Connected
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <FinanceCard title="Total Revenue" value="$45,200.00" change="+12.5%" trend="up" />
        <FinanceCard title="Pending Value" value="$8,340.00" change="-2.1%" trend="down" />
        <FinanceCard title="Avg. Ticket" value="$2,450.00" change="+5.3%" trend="up" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 bg-[#111113] border border-zinc-800/50 rounded-2xl p-6 glass">
          <div className="flex items-center justify-between mb-8">
            <h3 className="font-bold flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-emerald-400" /> Revenue Stream
            </h3>
            <div className="flex bg-zinc-900 rounded-lg p-1 gap-1">
              <button className="px-3 py-1 text-xs bg-zinc-800 rounded font-medium text-white">Week</button>
              <button className="px-3 py-1 text-xs text-zinc-500 hover:text-zinc-300">Month</button>
            </div>
          </div>
          <ActivityChart />
        </div>

        <div className="bg-[#111113] border border-zinc-800/50 rounded-2xl overflow-hidden glass">
          <div className="p-6 border-b border-zinc-800/50">
            <h3 className="font-bold flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-400" /> Recent Invoices
            </h3>
          </div>
          <div className="divide-y divide-zinc-800/50">
            {invoices.map((inv) => (
              <div key={inv.id} className="p-4 hover:bg-zinc-800/20 transition-colors cursor-pointer group">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono text-zinc-500 uppercase">{inv.id}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                    inv.status === "Paid" ? "bg-emerald-500/10 text-emerald-400" :
                    inv.status === "Open" ? "bg-indigo-500/10 text-indigo-400" :
                    "bg-amber-500/10 text-amber-500"
                  }`}>
                    {inv.status}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-white group-hover:text-indigo-400 transition-colors truncate max-w-[120px]">
                    {inv.client}
                  </h4>
                  <span className="text-sm font-bold text-white">{inv.amount}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="p-4 bg-zinc-900/50 border-t border-zinc-800/50">
            <button className="w-full py-2 text-xs font-bold text-zinc-400 hover:text-white flex items-center justify-center gap-2 transition-colors">
              View All In Odoo <ExternalLink className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function FinanceCard({ title, value, change, trend }: FinanceCardProps) {
  return (
    <div className="bg-[#111113] border border-zinc-800/50 rounded-2xl p-6 glass">
      <p className="text-sm font-medium text-zinc-400">{title}</p>
      <div className="flex items-end justify-between mt-2">
        <h3 className="text-2xl font-bold tracking-tight text-white">{value}</h3>
        <div className={`flex items-center gap-1 text-xs font-bold ${
          trend === 'up' ? 'text-emerald-400' : 'text-red-400'
        }`}>
          {trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
          {change}
        </div>
      </div>
    </div>
  );
}
