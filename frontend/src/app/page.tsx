"use client";

import { useRouter } from "next/navigation";
import { 
  Mail, 
  MessageSquare, 
  AlertTriangle, 
  FileText, 
  CheckCircle2, 
  RefreshCcw,
  Loader2,
  AlertCircle
} from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { StatCard } from "@/components/stat-card";
import { ActivityChart } from "@/components/activity-chart";
import { useState, useEffect } from "react";
import { fetchDashboard, fetchHealth } from "@/services/api";

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
  const [data, setData] = useState<any>(null);
  const [health, setHealth] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  const loadData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const [dbData, healthData] = await Promise.all([
        fetchDashboard(),
        fetchHealth()
      ]);
      setData(dbData);
      setHealth(Array.isArray(healthData) ? healthData : []);
      setError(null);
    } catch (err: any) {
      console.error("Dashboard load error:", err);
      // Fallback to local data if backend is not available for development demo
      setError("Backend connection failed. Using demo data.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    // Check if user is authenticated
    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    if (!token) {
      router.push("/login");
      return;
    }

    loadData();
    const interval = setInterval(() => loadData(true), 30000); // Auto refresh every 30s
    return () => clearInterval(interval);
  }, [router]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  const systemStatus = data?.health_status || "HEALTHY";
  const metrics = data?.system_metrics || {};

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
          <button 
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="p-2 hover:bg-zinc-800 rounded-md transition-all duration-200 text-zinc-400 hover:text-indigo-400 active:scale-95 disabled:opacity-50"
          >
            <RefreshCcw className={cn("w-4 h-4", refreshing && "animate-spin")} />
          </button>
          <div className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-medium transition-all duration-300",
            systemStatus === "healthy" || systemStatus === "HEALTHY" 
              ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20 shadow-[0_0_15px_-5px_rgba(16,185,129,0.3)]"
              : "bg-red-500/10 text-red-500 border-red-500/20 shadow-[0_0_15px_-5px_rgba(239,68,68,0.3)]"
          )}>
            {systemStatus === "healthy" || systemStatus === "HEALTHY" ? (
              <CheckCircle2 className="w-4 h-4" />
            ) : (
              <AlertCircle className="w-4 h-4" />
            )}
            {systemStatus === "healthy" || systemStatus === "HEALTHY" ? "Systems Operational" : "System Degraded"}
          </div>
        </div>
      </motion.div>

      {error && (
        <motion.div variants={item} className="bg-amber-500/10 border border-amber-500/20 text-amber-500 p-4 rounded-xl text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </motion.div>
      )}

      {/* Stats Grid */}
      <motion.div variants={item} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Emails in Queue"
          value={data?.derived_metrics?.queued_emails || "0"}
          subtitle="Needs_Action/Email/"
          icon={Mail}
          variant="purple"
        />
        <StatCard 
          title="WhatsApp Messages"
          value={data?.derived_metrics?.whatsapp_messages || "0"}
          subtitle="Needs_Action/WhatsApp/"
          icon={MessageSquare}
          variant="purple"
        />
        <StatCard 
          title="Active Alerts"
          value={data?.active_alerts?.toString() || "0"}
          subtitle={data?.active_alerts > 0 ? "Check system logs" : "All clear"}
          icon={AlertTriangle}
          variant="orange"
        />
        <StatCard 
          title="CPU Usage"
          value={`${metrics.cpu?.percent || 0}%`}
          subtitle={`RAM: ${metrics.memory?.percent || 0}%`}
          icon={RefreshCcw}
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

        {/* System Health */}
        <div className="bg-[#111113] border border-zinc-800/50 rounded-xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-zinc-300">Service Status</h3>
          </div>
          <div className="space-y-4">
            {health.length > 0 ? (
              health.map((check: any) => (
                <div key={check.name} className="flex items-center justify-between py-1 border-b border-zinc-800/30 last:border-0 pb-2">
                  <span className="text-sm text-zinc-400">{check.name}</span>
                  <span className={`text-[10px] font-bold px-2 py-1 rounded-sm uppercase tracking-wider ${
                    check.status === "healthy" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                    check.status === "unhealthy" ? "bg-red-500/10 text-red-500 border border-red-500/20" :
                    "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                  }`}>
                    {check.status}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-zinc-600 italic">No health data available</p>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
