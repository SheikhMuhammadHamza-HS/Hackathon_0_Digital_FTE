"use client";

import { 
  Mail, 
  MessageSquare, 
  AlertTriangle, 
  FileText, 
  CheckCircle2, 
  RefreshCcw 
} from "lucide-react";
import { motion } from "framer-motion";
import { StatCard } from "@/components/stat-card";
import { ActivityChart } from "@/components/activity-chart";
import { useState, useEffect } from "react";

const systemRows = [
  { name: "Cloud VM", status: "ONLINE", type: "success" },
  { name: "Gmail Watcher", status: "ACTIVE", type: "success" },
  { name: "WhatsApp Watcher", status: "ACTIVE", type: "success" },
  { name: "Odoo MCP", status: "OFFLINE", type: "error" },
  { name: "Email MCP", status: "PORT 3005", type: "info" },
  { name: "Social MCP", status: "PORT 3007", type: "info" },
];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const item = {
  hidden: { y: 20, opacity: 0 },
  show: { y: 0, opacity: 1 }
};

export default function Dashboard() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setMounted(true);
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  if (!mounted) return null;

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="p-8 space-y-8 max-w-7xl mx-auto"
    >
      {/* Header */}
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight glow-text-purple">Dashboard</h1>
          <p className="text-zinc-500 mt-1">Your AI Employee Command Center</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="p-2 hover:bg-zinc-800 rounded-md transition-all duration-200 text-zinc-400 hover:text-indigo-400 active:scale-95">
            <RefreshCcw className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-500 px-4 py-2 rounded-full border border-emerald-500/20 text-sm font-medium shadow-[0_0_15px_-5px_rgba(16,185,129,0.3)]">
            <CheckCircle2 className="w-4 h-4" />
            All Systems Online
          </div>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Emails in Queue"
          value="0"
          subtitle="Needs_Action/Email/"
          icon={Mail}
          variant="purple"
        />
        <StatCard 
          title="WhatsApp Messages"
          value="0"
          subtitle="Needs_Action/WhatsApp/"
          icon={MessageSquare}
          variant="purple"
        />
        <StatCard 
          title="Pending Approvals"
          value="0"
          subtitle="All clear"
          icon={AlertTriangle}
          variant="orange"
        />
        <StatCard 
          title="Odoo Draft Invoices"
          value="0"
          subtitle="Odoo offline"
          icon={FileText}
          variant="green"
        />
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Activity Chart */}
        <div className="lg:col-span-2 bg-[#111113] border border-zinc-800/50 rounded-xl p-6 shadow-xl">
          <div className="flex items-center gap-2 mb-6 text-zinc-300 font-medium">
            <RefreshCcw className="w-4 h-4 text-indigo-400 animate-spin-slow" />
            Activity Overview (7 days)
          </div>
          <ActivityChart />
        </div>

        {/* System Status */}
        <div className="bg-[#111113] border border-zinc-800/50 rounded-xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-zinc-300">System Status</h3>
          </div>
          <div className="space-y-4">
            {systemRows.map((row) => (
              <div key={row.name} className="flex items-center justify-between py-1 border-b border-zinc-800/30 last:border-0 pb-2">
                <span className="text-sm text-zinc-400">{row.name}</span>
                <span className={`text-[10px] font-bold px-2 py-1 rounded-sm uppercase tracking-wider ${
                  row.type === "success" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                  row.type === "error" ? "bg-red-500/10 text-red-500 border border-red-500/20" :
                  "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                }`}>
                  {row.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
