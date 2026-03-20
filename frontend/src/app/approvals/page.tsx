"use client";

import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  ShieldCheck,
  AlertCircle,
  Loader2,
  RefreshCcw,
  AlertTriangle
} from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import { fetchApprovals, approveApproval, rejectApproval } from "@/services/api";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const item = {
  hidden: { y: 20, opacity: 0 },
  show: { y: 0, opacity: 1 }
};

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadApprovals = async () => {
    setLoading(true);
    try {
      const data = await fetchApprovals();
      setApprovals(data.approvals || []);
      setError(null);
    } catch (err: any) {
      console.error("Approvals load error:", err);
      setError("Failed to fetch pending approvals.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / 60000);
      
      if (diffInMinutes < 1) return "Just now";
      if (diffInMinutes < 60) return `${diffInMinutes} mins ago`;
      const diffInHours = Math.floor(diffInMinutes / 60);
      if (diffInHours < 24) return `${diffInHours} hours ago`;
      return date.toLocaleDateString();
    } catch (e) {
      return isoString;
    }
  };

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="p-8 space-y-8 max-w-7xl mx-auto"
    >
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pending Approvals</h1>
          <p className="text-zinc-500 mt-1">Human-in-the-loop: Review and authorize AI actions</p>
        </div>
        <button 
          onClick={loadApprovals}
          className="p-2 hover:bg-zinc-800 rounded-md transition-all duration-200 text-zinc-400 hover:text-indigo-400"
        >
          <RefreshCcw className={cn("w-4 h-4", loading && "animate-spin")} />
        </button>
      </motion.div>

      {error && (
        <motion.div variants={item} className="bg-amber-500/10 border border-amber-500/20 text-amber-500 p-4 rounded-xl text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </motion.div>
      )}

      <motion.div variants={item} className="grid grid-cols-1 gap-6">
        {loading && approvals.length === 0 ? (
          <div className="p-12 flex flex-col items-center justify-center gap-4 text-zinc-500">
            <Loader2 className="w-12 h-12 text-indigo-500 animate-spin" />
            <p className="animate-pulse">Fetching AI drafts...</p>
          </div>
        ) : approvals.length > 0 ? (
          approvals.map((app) => (
            <div key={app.id} className="bg-[#111113] border border-zinc-800/50 rounded-2xl p-6 hover:border-indigo-500/30 transition-all group glass">
              <div className="flex flex-col md:flex-row md:items-center gap-6">
                <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-500/10 text-indigo-400 shrink-0 glow-purple border border-indigo-500/20">
                  <ShieldCheck className="w-7 h-7" />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                      {app.type}
                    </span>
                    <span className={cn(
                      "text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded border",
                      app.priority === "High" ? "bg-red-500/10 text-red-500 border-red-500/20" :
                      app.priority === "Medium" ? "bg-amber-500/10 text-amber-500 border-amber-500/20" :
                      "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                    )}>
                      {app.priority} Priority
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white group-hover:text-indigo-400 transition-colors">
                    {app.title}
                  </h3>
                  <p className="text-sm text-zinc-400 mt-1 mb-4 truncate">{app.description}</p>
                  <div className="flex items-center gap-4 text-[11px] text-zinc-500 font-medium">
                    <div className="flex items-center gap-1.5"><Clock className="w-3 h-3" /> {formatTime(app.time)}</div>
                    <div className="flex items-center gap-1.5"><AlertCircle className="w-3 h-3" /> ID: {app.id}</div>
                  </div>
                </div>

                <div className="flex flex-row md:flex-col gap-3 shrink-0">
                  <button
                    disabled={actionLoading === app.id}
                    onClick={async () => {
                      setActionLoading(app.id);
                      try {
                        await approveApproval(app.id);
                        setApprovals(prev => prev.filter(a => a.id !== app.id));
                      } catch (err: any) {
                        alert("Approve failed: " + (err.message || "Unknown error"));
                      } finally {
                        setActionLoading(null);
                      }
                    }}
                    className="flex items-center justify-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all hover:scale-[1.02] active:scale-95 glow-purple disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {actionLoading === app.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Approve
                  </button>
                  <button
                    disabled={actionLoading === app.id}
                    onClick={async () => {
                      setActionLoading(app.id);
                      try {
                        await rejectApproval(app.id);
                        setApprovals(prev => prev.filter(a => a.id !== app.id));
                      } catch (err: any) {
                        alert("Reject failed: " + (err.message || "Unknown error"));
                      } finally {
                        setActionLoading(null);
                      }
                    }}
                    className="flex items-center justify-center gap-2 px-6 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-sm font-semibold transition-all hover:scale-[1.02] active:scale-95 border border-zinc-700/50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <XCircle className="w-4 h-4" /> Reject
                  </button>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="bg-[#111113] border border-zinc-800/50 rounded-2xl p-12 text-center text-zinc-500 italic">
            No pending AI actions to review.
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}

